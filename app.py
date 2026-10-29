#!/usr/bin/env python3
"""GMB Automation Platform — JSON API backend (port 5003).

React SPA (frontend/dist) is served at / and talks to this backend via fetch('/api/...').
Chalao:  python app.py   ->   http://127.0.0.1:5003
Pehle README.md padho — Google API approval ke bina writes nahi honge (dry-run mode).
"""
import copy
import json
import logging
import os
import threading
from datetime import date
from pathlib import Path

import yaml
from flask import (Flask, jsonify, redirect, request, send_file,
                   send_from_directory, session, url_for)
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token as google_id_token
from google_auth_oauthlib.flow import Flow
from werkzeug.security import check_password_hash, generate_password_hash

from gmb import auth, audit as audit_mod, content as content_mod
from gmb import reviews as reviews_mod, reports as reports_mod
from gmb import scheduler as sched_mod, dataforseo as dfs_mod
from gmb.tracker import Tracker, STATUS_FLOW

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "run.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"),
              logging.StreamHandler()],
)
log = logging.getLogger("gmb.app")

# ---------- config ----------
with open(BASE_DIR / "config.yaml", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)
runtime_cfg = copy.deepcopy(CFG)  # settings page se badal sakta hai


def eff_dry_run() -> bool:
    return tracker.kv_get("dry_run", str(bool((CFG["safety"]).get("dry_run", True)))) == "True"


tracker = Tracker(str(BASE_DIR / CFG["app"].get("db_path", "gmb_automation.db")))

# pehli boot: config se seed clients
if not tracker.get_clients(active_only=False) and CFG.get("clients"):
    for c in CFG["clients"]:
        tracker.add_client(c)
    log.info("seeded %d clients from config", len(CFG["clients"]))

app = Flask(__name__)
app.secret_key = os.environ.get("GMB_SECRET_KEY") or os.urandom(24).hex()

state = {"task": None, "error": ""}


def run_bg(fn, *args, **kwargs):
    def w():
        state["task"] = fn.__name__
        state["error"] = ""
        try:
            fn(*args, **kwargs)
        except Exception as e:
            state["error"] = str(e)
            log.error("bg task fail: %s", e)
        finally:
            state["task"] = None
    threading.Thread(target=w, daemon=True).start()


def jdata():
    return request.get_json(force=True, silent=True) or {}


def err(msg, code=400):
    return jsonify({"ok": False, "error": msg}), code


# ================= OPERATOR AUTH (SaaS) =================
def public_op(op):
    if not op:
        return None
    return {"id": op["id"], "email": op["email"], "name": op.get("name", ""),
            "role": op.get("role", "operator"), "is_active": op.get("is_active", 1),
            "created_at": op.get("created_at", "")}


def current_operator():
    oid = session.get("operator_id")
    if not oid:
        return None
    op = tracker.get_operator(oid)
    if not op or not op.get("is_active"):
        session.clear()
        return None
    return op


def req_mode():
    """UI mode: 'live' (default, sirf real clients) ya 'demo' (demo client bhi dikhe)."""
    try:
        m = request.args.get("mode")
        if m in ("live", "demo"):
            return m
        d = request.get_json(force=True, silent=True) or {}
        if isinstance(d, dict) and d.get("mode") in ("live", "demo"):
            return d["mode"]
    except Exception:
        pass
    return "live"


def can_access_client(c, op):
    """Operator ko ye client dikhe / use kar sake ya nahi."""
    if not c:
        return False
    if c.get("is_demo"):
        # Demo client shared playground hai — sirf demo mode me dikhta hai.
        return req_mode() == "demo"
    if op and op.get("role") == "super_admin":
        return True
    if op and c.get("owner_id") == op["id"]:
        return True
    return False


def visible_clients(op, mode=None):
    """Operator ko dikhne wale clients (list endpoints ke liye)."""
    mode = mode or req_mode()
    out = []
    for c in tracker.get_clients():
        if c.get("is_demo"):
            if mode == "demo":
                out.append(c)
        elif op and op.get("role") == "super_admin":
            out.append(c)
        elif op and c.get("owner_id") == op["id"]:
            out.append(c)
    return out


def get_client_or_404(slug):
    c = tracker.get_client(slug)
    if not c:
        return None
    if not can_access_client(c, current_operator()):
        return None
    c["connected"] = auth.is_connected(slug)
    return c


def _check_slug_access(slug):
    """Id-only routes (post/keyword/competitor/activity) ke liye: slug ka client
    accessible hai to client dict, warna None."""
    c = tracker.get_client(slug)
    if not c or not can_access_client(c, current_operator()):
        return None
    return c


# Login gate: /api/* par session operator chahiye, in public paths ke siwa.
# /api/status public hai (deploy health check isko bina login ke curl karta hai),
# lekin guests ko sirf ok+dry_run milta hai, koi client data nahi.
PUBLIC_API_PATHS = {"/api/health", "/api/status", "/api/auth/me", "/api/auth/login",
                    "/api/auth/register", "/api/auth/google", "/api/auth/logout"}


@app.before_request
def _require_login():
    if request.path.startswith("/api/") and request.path not in PUBLIC_API_PATHS:
        if not current_operator():
            return err("Login required", 401)


def enriched_client(c):
    c["connected"] = auth.is_connected(c["slug"])
    c["pending"] = tracker.pending_approvals(c["slug"])
    c["drafts"] = len(tracker.get_posts(c["slug"], status="draft"))
    c["scheduled"] = len(tracker.get_posts(c["slug"], status="scheduled"))
    return c


def integrations_ctx():
    return {
        "dataforseo": dfs_mod.from_config(runtime_cfg) is not None,
        "dataforseo_key": bool(os.environ.get("DATAFORSEO_LOGIN")),
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
    }


# ================= HEALTH / STATUS =================
@app.route("/api/health")
def api_health():
    return jsonify({"ok": True})


@app.route("/api/status")
def api_status():
    op = current_operator()
    if not op:
        # Deploy health check + public liveness: sirf ok+dry_run, koi client data nahi.
        return jsonify({"ok": True, "dry_run": eff_dry_run()})
    slugs = [c["slug"] for c in visible_clients(op)]
    counts = {"posts": 0, "replies": 0, "media": 0, "qa": 0}
    for s in slugs:
        pc = tracker.pending_approvals(s)
        for k in counts:
            counts[k] += pc.get(k, 0)
    return jsonify({
        "ok": True,
        "dry_run": eff_dry_run(),
        "pending": counts,
        "pending_total": sum(counts.values()),
        "task": state["task"],
        "error": state["error"],
        "integrations": {
            "dataforseo": dfs_mod.from_config(runtime_cfg) is not None,
            "openai": bool(os.environ.get("OPENAI_API_KEY")),
        },
        "posting": (runtime_cfg.get("posting") or {}),
        "scheduler": (runtime_cfg.get("scheduler") or {}),
    })


# ================= CLIENTS =================
@app.route("/api/clients", methods=["GET"])
def api_clients():
    op = current_operator()
    clients = [enriched_client(c) for c in visible_clients(op)]
    return jsonify({"ok": True, "clients": clients})


@app.route("/api/clients", methods=["POST"])
def api_client_add():
    d = jdata()
    name = (d.get("name") or "").strip()
    if not name:
        return err("name khaali hai", 400)
    services = d.get("services", "")
    if isinstance(services, str):
        services = [s.strip() for s in services.split(",") if s.strip()]
    elif isinstance(services, list):
        services = [str(s).strip() for s in services if str(s).strip()]
    else:
        services = []
    slug = tracker.add_client({
        "name": name,
        "business_name": (d.get("business_name") or "").strip(),
        "city": (d.get("city") or "").strip(),
        "phone": (d.get("phone") or "").strip(),
        "website": (d.get("website") or "").strip(),
        "category": (d.get("category") or "").strip(),
        "services": services,
        "secrets_path": (d.get("secrets_path") or "").strip(),
        "owner_id": (current_operator() or {}).get("id"),
    })
    tracker.log_activity(slug, "Client onboarded", area="Onboarding", status="Pending")
    return jsonify({"ok": True, "slug": slug})


@app.route("/api/clients/<slug>", methods=["GET"])
def api_client_get(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    return jsonify({"ok": True, "client": c})


@app.route("/api/clients/<slug>", methods=["PATCH"])
def api_client_update(slug):
    if not get_client_or_404(slug):
        return err("Client nahi mila", 404)
    d = jdata()
    fields = {}
    for k in ("business_name", "account_id", "location_id", "category",
              "city", "phone", "website", "secrets_path"):
        if k in d:
            fields[k] = (d.get(k) or "").strip()
    if "services" in d:
        sv = d.get("services")
        if isinstance(sv, str):
            sv = [s.strip() for s in sv.split(",") if s.strip()]
        elif isinstance(sv, list):
            sv = [str(s).strip() for s in sv if str(s).strip()]
        else:
            sv = []
        fields["services"] = sv
    tracker.update_client(slug, **fields)
    return jsonify({"ok": True})


@app.route("/api/clients/<slug>", methods=["DELETE"])
def api_client_delete(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    op = current_operator()
    if c.get("is_demo") and (not op or op.get("role") != "super_admin"):
        return err("Demo client sirf super admin delete kar sakta hai", 403)
    removed = tracker.delete_client(slug)
    # OAuth token bhi hata do taaki dobara connect kiye bina use na ho
    try:
        p = auth.token_path(slug)
        if p.exists():
            p.unlink()
            removed["oauth_token"] = 1
    except Exception:
        pass
    tracker.log_activity("", f"Client '{c.get('name', slug)}' deleted — local data cleared",
                         area="clients", status="Verified")
    return jsonify({"ok": True, "removed": removed})


@app.route("/api/clients/<slug>/autopublish", methods=["POST"])
def api_client_autopublish(slug):
    if not get_client_or_404(slug):
        return err("Client nahi mila", 404)
    val = 1 if jdata().get("auto_publish") else 0
    tracker.update_client(slug, auto_publish=val)
    if val:
        log.warning("AUTO-PUBLISH ON for %s — user ne warning samajh ke on kiya", slug)
    return jsonify({"ok": True})


# ================= OPERATOR AUTH ROUTES (SaaS) =================
# Google sign-in ke liye alag scopes — GBP wale business.manage flow se alag.
# NOTE: Cloud Console consent screen par ye 3 scopes add hone chahiye, warna
# Google sign-in consent screen par dikhega hi nahi (user-side pending step).
LOGIN_SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile"]


def _set_login_session(op):
    session["operator_id"] = op["id"]
    session["operator_email"] = op["email"]
    session["operator_role"] = op.get("role", "operator")


def _client_ip():
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or ""


@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    d = jdata()
    email = (d.get("email") or "").strip().lower()
    password = d.get("password") or ""
    name = (d.get("name") or "").strip()
    if not email or "@" not in email:
        return err("Valid email chahiye", 400)
    if len(password) < 6:
        return err("Password kam se kam 6 characters ka ho", 400)
    if tracker.get_operator_by_email(email):
        return err("Ye email pehle se registered hai", 400)
    is_first = len(tracker.list_operators()) == 0
    role = "super_admin" if is_first else "operator"
    oid = tracker.create_operator(email, name or email.split("@")[0],
                                  generate_password_hash(password), role)
    if is_first:
        # Pehle se maujood owner-less real clients pehle operator ke ho gaye.
        tracker.claim_unowned_clients(oid)
    op = tracker.get_operator(oid)
    _set_login_session(op)
    # Register karte hi session banta hai — ye bhi ek login event hai.
    tracker.record_login(op["id"], email, _client_ip(),
                         request.headers.get("User-Agent", ""))
    return jsonify({"ok": True, "operator": public_op(op)})


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    d = jdata()
    email = (d.get("email") or "").strip().lower()
    password = d.get("password") or ""
    op = tracker.get_operator_by_email(email)
    if not op or not op.get("password_hash") or not check_password_hash(op["password_hash"], password):
        return err("Email ya password galat hai", 401)
    if not op.get("is_active"):
        return err("Account disabled hai — super admin se sampark karo", 403)
    _set_login_session(op)
    tracker.record_login(op["id"], email, _client_ip(),
                         request.headers.get("User-Agent", ""))
    return jsonify({"ok": True, "operator": public_op(op)})


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/me")
def api_auth_me():
    op = current_operator()
    if not op:
        return jsonify({"ok": True, "authenticated": False, "operator": None})
    return jsonify({"ok": True, "authenticated": True, "operator": public_op(op)})


@app.route("/api/auth/google")
def api_auth_google():
    secrets = resolve_secrets_path({})
    if not secrets or not Path(secrets).exists():
        return err("OAuth client secrets file nahi mili. Server par client_secrets.json rakho "
                   "(app folder me) ya GMB_OAUTH_SECRETS env var set karo.", 400)
    flow = Flow.from_client_secrets_file(
        secrets, scopes=LOGIN_SCOPES,
        redirect_uri=url_for("auth_google_callback", _external=True))
    url, _ = flow.authorization_url(prompt="select_account")
    session["login_flow"] = "1"
    return jsonify({"ok": True, "authorization_url": url})


@app.route("/auth/google/callback")
def auth_google_callback():
    def _fail(msg):
        return (f"<!doctype html><html><head><title>Google sign-in</title></head>"
                f"<body style='font-family:sans-serif;padding:40px'><h2>{msg}</h2>"
                f"<p><a href='/'>Wapas jao</a></p></body></html>")
    if not session.pop("login_flow", None):
        return _fail("Login session expire ho gayi — dobara Sign in dabao.")
    try:
        secrets = resolve_secrets_path({})
        flow = Flow.from_client_secrets_file(
            secrets, scopes=LOGIN_SCOPES,
            redirect_uri=url_for("auth_google_callback", _external=True))
        flow.fetch_token(authorization_response=request.url)
        creds = flow.credentials
        info = None
        if creds.id_token:
            try:
                info = google_id_token.verify_oauth2_token(
                    creds.id_token, GoogleRequest(), creds.client_id)
            except Exception:
                info = None
        if not info:
            import requests as _req
            r = _req.get("https://openidconnect.googleapis.com/v1/userinfo",
                         headers={"Authorization": f"Bearer {creds.token}"}, timeout=15)
            info = r.json() if r.ok else {}
        email = (info.get("email") or "").strip().lower()
        if not email:
            raise ValueError("Google se email nahi mili")
        if info.get("email_verified") in (False, "false"):
            raise ValueError("Google email verified nahi hai")
        op = tracker.get_operator_by_email(email)
        if op is None:
            is_first = len(tracker.list_operators()) == 0
            role = "super_admin" if is_first else "operator"
            oid = tracker.create_operator(email, info.get("name") or email.split("@")[0],
                                          "", role)
            if is_first:
                tracker.claim_unowned_clients(oid)
            op = tracker.get_operator(oid)
        if not op.get("is_active"):
            return _fail("Account disabled hai — super admin se sampark karo.")
        _set_login_session(op)
        tracker.record_login(op["id"], email, _client_ip(),
                             request.headers.get("User-Agent", ""))
        return redirect("/")
    except Exception as e:
        log.error("google login fail: %s", e)
        return _fail(f"Google sign-in fail: {e}")


# ================= SUPER ADMIN =================
@app.route("/api/admin/users")
def api_admin_users():
    op = current_operator()
    if not op or op.get("role") != "super_admin":
        return err("Super admin only", 403)
    return jsonify({"ok": True, "users": [public_op(o) for o in tracker.list_operators()]})


@app.route("/api/admin/users/<int:oid>/toggle", methods=["POST"])
def api_admin_user_toggle(oid):
    op = current_operator()
    if not op or op.get("role") != "super_admin":
        return err("Super admin only", 403)
    if oid == op["id"]:
        return err("Apna khud ka account disable nahi kar sakte", 400)
    target = tracker.get_operator(oid)
    if not target:
        return err("User nahi mila", 404)
    new_state = 0 if target.get("is_active") else 1
    tracker.set_operator_active(oid, new_state)
    return jsonify({"ok": True, "is_active": new_state})


@app.route("/api/admin/logins")
def api_admin_logins():
    op = current_operator()
    if not op or op.get("role") != "super_admin":
        return err("Super admin only", 403)
    return jsonify({"ok": True, "logins": tracker.get_login_history(200)})


# ================= OAUTH =================
def resolve_secrets_path(client):
    """OAuth secrets JSON ka path — server default, har client ke liye same.

    Simplification: operator ko har client me path daalna nahi padta.
    1. GMB_OAUTH_SECRETS env var (agar set hai aur file maujood hai)
    2. App folder me client_secrets.json (server par bas ye ek file rakhni hai)
    3. Fallback: client ki purani saved path (pehle ki settings na toote)
    """
    env_path = os.environ.get("GMB_OAUTH_SECRETS", "").strip()
    if env_path and Path(env_path).exists():
        return env_path
    app_dir_file = Path(__file__).resolve().parent / "client_secrets.json"
    if app_dir_file.exists():
        return str(app_dir_file)
    saved = (client.get("secrets_path") or "").strip()
    if saved and Path(saved).exists():
        return saved
    return env_path or str(app_dir_file)


@app.route("/api/connect/<slug>")
def api_connect(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    secrets = resolve_secrets_path(c)
    if not secrets or not Path(secrets).exists():
        return err("OAuth client secrets file nahi mili. Server par client_secrets.json rakho "
                   "(app folder me) ya GMB_OAUTH_SECRETS env var set karo (README Step 3).")
    redirect_uri = url_for("oauth_callback", _external=True)
    flow = auth.build_flow(secrets, redirect_uri)
    session["oauth_slug"] = slug
    session["oauth_secrets"] = secrets
    return jsonify({"ok": True, "authorization_url": auth.authorization_url(flow, state=slug)})


@app.route("/oauth/callback")
def oauth_callback():
    slug = session.pop("oauth_slug", None)
    secrets = session.pop("oauth_secrets", "")
    msg = "Google connected! You can close this window."
    if not slug:
        msg = "OAuth session expire ho gayi — dobara Connect dabao."
    else:
        try:
            redirect_uri = url_for("oauth_callback", _external=True)
            flow = auth.build_flow(secrets, redirect_uri)
            flow.fetch_token(authorization_response=request.url)
            auth.save_credentials(slug, flow.credentials)
            tracker.update_client(slug, connected=1)
            tracker.log_activity(slug, "Google OAuth connected", area="Onboarding", status="Verified")
        except Exception as e:
            msg = f"OAuth fail: {e}"
            log.error("oauth fail %s: %s", slug, e)
    html = f"""<!doctype html><html><head><title>GMB OAuth</title></head>
<body style="font-family:sans-serif;padding:40px"><h2>{msg}</h2>
<script>window.opener&&window.opener.postMessage('gmb-oauth-done','*');setTimeout(function(){{window.close()}},800);</script>
</body></html>"""
    return html


@app.route("/api/disconnect/<slug>", methods=["POST"])
def api_disconnect(slug):
    if not get_client_or_404(slug):
        return err("Client nahi mila", 404)
    auth.disconnect(slug)
    tracker.update_client(slug, connected=0)
    return jsonify({"ok": True})


@app.route("/api/logs")
def api_logs():
    op = current_operator()
    if not op or op.get("role") != "super_admin":
        return err("Super admin only", 403)
    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()[-150:] if LOG_FILE.exists() else []
    return jsonify({"ok": True, "lines": lines, "task": state["task"], "error": state["error"]})


# ================= AUDIT =================
AUDIT_FIELDS = ["name", "description", "primary_category", "phone", "website", "city",
                "secondary_categories", "services", "photos_count", "videos_count",
                "posts_last_30d", "review_count", "rating", "unanswered_reviews",
                "hours_set", "nap_name", "nap_address", "nap_phone"]


@app.route("/api/audit/<slug>", methods=["GET"])
def api_audit_get(slug):
    if not get_client_or_404(slug):
        return err("Client nahi mila", 404)
    saved = tracker.kv_get(f"audit:{slug}")
    result = json.loads(saved) if saved else None
    return jsonify({"ok": True, "result": result})


@app.route("/api/audit/<slug>", methods=["POST"])
def api_audit_run(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    d = jdata()
    mode = d.get("mode", "manual")
    profile = {}
    if mode == "api" and c["connected"] and c.get("location_id"):
        try:
            from gmb.api import GBPClient
            api = GBPClient(auth.load_credentials(slug), dry_run=True)
            loc_name = f"accounts/{c['account_id']}/locations/{c['location_id']}"
            loc = api.get_location(loc_name)
            profile = audit_mod.profile_from_api_location(loc)
            revs = api.list_reviews(loc_name) or []
            profile["review_count"] = len(revs)
            unans = sum(1 for r in revs if not r.get("reviewReply"))
            profile["unanswered_reviews"] = unans
            ratings = [reviews_mod._star_num(r.get("starRating")) for r in revs]
            ratings = [x for x in ratings if x]
            profile["rating"] = round(sum(ratings) / len(ratings), 1) if ratings else 0
            try:
                posts = api.list_local_posts(loc_name) or []
                from datetime import datetime, timedelta
                recent = 0
                for p in posts:
                    ct = p.get("createTime", "")
                    try:
                        dt = datetime.fromisoformat(ct.replace("Z", "+00:00"))
                        if dt > datetime.now(dt.tzinfo) - timedelta(days=30):
                            recent += 1
                    except Exception:
                        pass
                profile["posts_last_30d"] = recent
            except Exception:
                pass
            profile["source"] = "Google API (live)"
        except Exception as e:
            state["error"] = f"API audit fail: {e}"
            return err(f"API audit fail: {e}")
    else:
        for f in AUDIT_FIELDS:
            v = d.get(f, "")
            profile[f] = v.strip() if isinstance(v, str) else v
        for f in ["secondary_categories", "services"]:
            raw = profile[f]
            if isinstance(raw, list):
                profile[f] = [str(x).strip() for x in raw if str(x).strip()]
            else:
                profile[f] = [x.strip() for x in str(raw or "").split(",") if x.strip()]
        for f in ["photos_count", "videos_count", "posts_last_30d", "review_count", "unanswered_reviews"]:
            try:
                profile[f] = int(profile[f] or 0)
            except Exception:
                profile[f] = 0
        try:
            profile["rating"] = float(profile["rating"] or 0)
        except Exception:
            profile["rating"] = 0
        hs = d.get("hours_set", False)
        profile["hours_set"] = bool(hs) if isinstance(hs, bool) else str(hs).lower() in ("on", "true", "1")
        profile["source"] = "manual entry"
    result = audit_mod.run_audit(profile)
    tracker.kv_set(f"audit:{slug}", json.dumps(result))
    tracker.log_activity(slug, f"Audit run — score {result['score']} ({result['grade']})",
                         area="Audit", status="In Progress",
                         notes=f"{result['high']} high, {result['medium']} medium, {result['low']} low")
    return jsonify({"ok": True, "result": result})


@app.route("/api/audit/<slug>/push", methods=["POST"])
def api_audit_push(slug):
    if not get_client_or_404(slug):
        return err("Client nahi mila", 404)
    saved = tracker.kv_get(f"audit:{slug}")
    if not saved:
        return err("Audit pehle run karo", 400)
    result = json.loads(saved)
    n = 0
    for f in result["findings"]:
        if f["priority"] in ("High", "Medium"):
            tracker.log_activity(slug, f"[{f['priority']}] {f['area']}: {f['issue']}",
                                 area=f["area"], status="Pending", notes=f["action"])
            n += 1
    log.info("audit push %s: %d activities", slug, n)
    return jsonify({"ok": True, "pushed": n})


# ================= KEYWORDS =================
@app.route("/api/keywords/<slug>", methods=["GET"])
def api_keywords_get(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    kws = tracker.get_keywords(slug)
    dfs_on = dfs_mod.from_config(runtime_cfg) is not None
    return jsonify({"ok": True, "keywords": kws, "dataforseo_on": dfs_on})


@app.route("/api/keywords/<slug>", methods=["POST"])
def api_keywords_add(slug):
    if not get_client_or_404(slug):
        return err("Client nahi mila", 404)
    d = jdata()
    if not (d.get("keyword") or "").strip():
        return err("keyword khaali hai", 400)
    tracker.add_keyword(slug, (d.get("keyword") or "").strip(),
                        d.get("ktype", "secondary"),
                        (d.get("mapped_to") or "").strip(),
                        (d.get("volume") or "").strip())
    return jsonify({"ok": True})


@app.route("/api/keywords/<slug>/<int:kid>", methods=["PATCH"])
def api_keyword_update(slug, kid):
    if not _check_slug_access(slug):
        return err("Client nahi mila", 404)
    kw = tracker.get_keyword(kid)
    if not kw or kw.get("client_slug") != slug:
        return err("Keyword nahi mili", 404)
    d = jdata()
    fields = {}
    for k in ("keyword", "ktype", "mapped_to", "volume"):
        if k in d:
            fields[k] = (d.get(k) or "").strip()
    tracker.update_keyword(kid, **fields)
    return jsonify({"ok": True})


@app.route("/api/keywords/<slug>/<int:kid>", methods=["DELETE"])
def api_keyword_delete(slug, kid):
    if not _check_slug_access(slug):
        return err("Client nahi mila", 404)
    kw = tracker.get_keyword(kid)
    if not kw or kw.get("client_slug") != slug:
        return err("Keyword nahi mili", 404)
    tracker.delete_keyword(kid)
    return jsonify({"ok": True})


@app.route("/api/keywords/<slug>/dataforseo", methods=["POST"])
def api_keyword_dataforseo(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    d = jdata()
    try:
        dfs = dfs_mod.from_config(runtime_cfg)
        if not dfs:
            raise dfs_mod.DataForSEOError("DataForSEO enabled nahi hai (Settings dekho).")
        seed = (d.get("seed") or "").strip() or c.get("category") or c.get("name")
        loc = (d.get("location") or "").strip() or f"{c.get('city')},India"
        suggs = dfs.keyword_suggestions(seed, location_name=loc)
        added = 0
        for s in suggs[:30]:
            if s.get("keyword"):
                tracker.add_keyword(slug, s["keyword"], "secondary", "",
                                    str(s.get("volume") or ""))
                added += 1
        log.info("dataforseo: %d keywords added for %s", added, slug)
        return jsonify({"ok": True, "added": added})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ================= CONTENT CALENDAR =================
def _caldraft_load(slug):
    """saved caldraft ko (year, month, slots) me badlo; purana list-format bhi support karo."""
    saved = tracker.kv_get(f"caldraft:{slug}")
    if not saved:
        return date.today().year, date.today().month, []
    try:
        data = json.loads(saved)
    except Exception:
        return date.today().year, date.today().month, []
    if isinstance(data, dict) and "slots" in data:
        return data.get("year") or date.today().year, data.get("month") or date.today().month, data["slots"]
    if isinstance(data, list):
        return date.today().year, date.today().month, data
    return date.today().year, date.today().month, []


@app.route("/api/calendar/<slug>", methods=["GET"])
def api_calendar_get(slug):
    if not get_client_or_404(slug):
        return err("Client nahi mila", 404)
    year, month, slots = _caldraft_load(slug)
    return jsonify({"ok": True, "slots": slots, "year": year, "month": month})


@app.route("/api/calendar/<slug>/generate", methods=["POST"])
def api_calendar_generate(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    d = jdata()
    today = date.today()
    try:
        year = int(d.get("year", today.year))
    except Exception:
        year = today.year
    try:
        month = int(d.get("month", today.month))
    except Exception:
        month = today.month
    kws = tracker.get_keywords(slug)
    mix = (runtime_cfg.get("posting") or {}).get("content_mix", {})
    days = (runtime_cfg.get("posting") or {}).get("post_days", ["tuesday", "thursday"])
    slots = content_mod.generate_calendar(c, year, month, kws, mix, days)
    tracker.kv_set(f"caldraft:{slug}", json.dumps({"year": year, "month": month, "slots": slots}))
    return jsonify({"ok": True, "slots": slots})


@app.route("/api/calendar/<slug>/queue", methods=["POST"])
def api_calendar_queue(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    year, month, slots = _caldraft_load(slug)
    if not slots:
        return err("Pehle calendar generate karo", 400)
    n = 0
    for slot in slots:
        draft = content_mod.draft_post(c, slot)
        draft["client_slug"] = slug
        draft["status"] = "draft"
        tracker.queue_post(draft)
        n += 1
    tracker.log_activity(slug, f"Content calendar queued: {n} drafts", area="Posts",
                         status="In Progress")
    log.info("calendar queue %s: %d drafts", slug, n)
    return jsonify({"ok": True, "queued": n})


# ================= CONTENT QUEUE =================
@app.route("/api/queue/<slug>", methods=["GET"])
def api_queue_get(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    posts = tracker.get_posts(slug)
    return jsonify({"ok": True, "posts": posts})


@app.route("/api/queue/<slug>/<int:pid>", methods=["PATCH"])
def api_queue_update(slug, pid):
    if not _check_slug_access(slug):
        return err("Client nahi mila", 404)
    p = tracker.get_post(pid)
    if not p or p.get("client_slug") != slug:
        return err("Post nahi mili", 404)
    d = jdata()
    fields = {}
    for k in ("summary", "topic", "cta_url", "topic_type", "cta_type"):
        if k in d:
            fields[k] = (d.get(k) or "").strip()
    tracker.update_post(pid, **fields)
    return jsonify({"ok": True})


@app.route("/api/queue/<slug>/<int:pid>/approve", methods=["POST"])
def api_queue_approve(slug, pid):
    if not _check_slug_access(slug):
        return err("Client nahi mila", 404)
    p = tracker.get_post(pid)
    if not p or p.get("client_slug") != slug:
        return err("Post nahi mili", 404)
    tracker.update_post(pid, status="approved")
    tracker.log_activity(slug, f"Post #{pid} approved", area="Posts", status="Approved")
    return jsonify({"ok": True})


@app.route("/api/queue/<slug>/<int:pid>/schedule", methods=["POST"])
def api_queue_schedule(slug, pid):
    if not _check_slug_access(slug):
        return err("Client nahi mila", 404)
    p = tracker.get_post(pid)
    if not p or p.get("client_slug") != slug:
        return err("Post nahi mili", 404)
    d = (jdata().get("scheduled_date") or "").strip()
    if d:
        tracker.update_post(pid, scheduled_date=d, status="scheduled")
        tracker.log_activity(slug, f"Post #{pid} scheduled for {d}", area="Posts",
                             status="Scheduled")
    return jsonify({"ok": True})


@app.route("/api/queue/<slug>/<int:pid>", methods=["DELETE"])
def api_queue_delete(slug, pid):
    if not _check_slug_access(slug):
        return err("Client nahi mila", 404)
    p = tracker.get_post(pid)
    if not p or p.get("client_slug") != slug:
        return err("Post nahi mili", 404)
    tracker.delete_post(pid)
    return jsonify({"ok": True})


def try_publish_post(pid: int, slug: str) -> tuple[bool, str]:
    """Ek post abhi publish karo — saare safety guards ke saath.
    Sirf usi client ke posts me dhoondo (multi-tenancy: dusre operator ka post kabhi nahi)."""
    client = tracker.get_client(slug)
    if not client:
        return False, "Post nahi mili"
    p = None
    for cand in tracker.get_posts(slug):
        if cand["id"] == pid:
            p = cand
            break
    if p is None:
        return False, "Post nahi mili"
    if eff_dry_run():
        return False, "DRY-RUN ON hai — pehle Settings me dry-run OFF karo (API approved hone ke baad)."
    if not auth.is_connected(slug):
        return False, "Client Google se connected nahi hai."
    if p.get("requires_approval") and p.get("status") not in ("approved", "scheduled"):
        return False, "Approval pending hai — pehle Approve karo."
    try:
        from gmb.api import GBPClient
        api = GBPClient(auth.load_credentials(slug), dry_run=False)
        payload = {"languageCode": "en", "summary": p["summary"],
                   "topicType": p.get("topic_type") or "STANDARD",
                   "callToAction": {"actionType": p.get("cta_type") or "LEARN_MORE"}}
        if p.get("cta_url"):
            payload["callToAction"]["url"] = p["cta_url"]
        parent = f"accounts/{client['account_id']}/locations/{client['location_id']}"
        resp = api.create_local_post(parent, payload)
        if resp and resp.get("dry_run"):
            return False, "API dry-run ne block kiya."
        tracker.update_post(pid, status="published", gmb_post_name=resp.get("name", ""))
        tracker.log_activity(slug, f"Post published: {p.get('topic')}", area="Posts",
                             status="Published")
        return True, "Published!"
    except Exception as e:
        tracker.update_post(pid, status="failed")
        return False, f"Publish fail: {e}"


@app.route("/api/queue/<slug>/<int:pid>/publish", methods=["POST"])
def api_queue_publish(slug, pid):
    if not get_client_or_404(slug):
        return err("Client nahi mila", 404)
    ok, msg = try_publish_post(pid, slug)
    return jsonify({"ok": ok, "message": msg})


# ================= REVIEWS =================
@app.route("/api/reviews/<slug>", methods=["GET"])
def api_reviews_get(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    revs = tracker.get_reviews(slug)
    last = tracker.kv_get(f"last_review_check:{slug}")
    return jsonify({"ok": True, "reviews": revs, "last_check": last})


@app.route("/api/reviews/<slug>/check", methods=["POST"])
def api_reviews_check(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    run_bg(sched_mod.check_reviews, tracker, runtime_cfg)
    # single client ke liye turant bhi try karo
    try:
        if auth.is_connected(slug) and c.get("location_id"):
            from gmb.api import GBPClient
            api = GBPClient(auth.load_credentials(slug), dry_run=True)
            parent = f"accounts/{c['account_id']}/locations/{c['location_id']}"
            new = reviews_mod.poll_new_reviews(api, parent, tracker.known_review_names(slug))
            for r in new:
                rec = reviews_mod.review_record(slug, r)
                d = reviews_mod.draft_reply(r, c, tracker.recent_reply_hashes(slug))
                rec.update({"reply_text": d["reply_text"], "reply_hash": d["reply_hash"],
                            "reply_status": "draft", "needs_human": int(d["needs_human"])})
                tracker.save_review(rec)
    except Exception as e:
        state["error"] = f"Review check fail: {e}"
    return jsonify({"ok": True, "message": "Check started"})


@app.route("/api/reviews/<slug>", methods=["PATCH"])
def api_review_save(slug):
    if not _check_slug_access(slug):
        return err("Client nahi mila", 404)
    d = jdata()
    rname = d.get("review_name", "")
    if not rname:
        return err("review_name khaali hai", 400)
    rv = tracker.get_review(rname)
    if not rv or rv.get("client_slug") != slug:
        return err("Review nahi mili", 404)
    tracker.update_review_reply(rname, reply_text=(d.get("reply_text") or "").strip(),
                                reply_status="draft")
    return jsonify({"ok": True})


@app.route("/api/reviews/<slug>/send", methods=["POST"])
def api_review_send(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    d = jdata()
    rname = d.get("review_name", "")
    if eff_dry_run():
        return jsonify({"ok": False,
                        "message": "DRY-RUN ON hai — reply nahi bheja gaya."})
    if not auth.is_connected(slug):
        return jsonify({"ok": False, "message": "Client Google se connected nahi hai."})
    revs = {r["review_name"]: r for r in tracker.get_reviews(slug, only_pending=False)}
    r = revs.get(rname)
    if not r:
        return jsonify({"ok": False, "message": "Review nahi mili."})
    text = (d.get("reply_text") or r.get("reply_text") or "").strip()
    if not text:
        return jsonify({"ok": False, "message": "Reply text khaali hai."})
    try:
        from gmb.api import GBPClient
        api = GBPClient(auth.load_credentials(slug), dry_run=False)
        api.reply_review(rname, text)
        tracker.update_review_reply(rname, reply_text=text, reply_status="sent", has_reply=1)
        tracker.log_activity(slug, f"Review reply sent ({r.get('stars')}*)", area="Reviews",
                             status="Published")
        return jsonify({"ok": True, "message": "Reply sent"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"Reply fail: {e}"})


# ================= MEDIA =================
@app.route("/api/media/<slug>", methods=["GET"])
def api_media_get(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    items = tracker.get_media(slug)
    return jsonify({"ok": True, "items": items})


@app.route("/api/media/<slug>", methods=["POST"])
def api_media_add(slug):
    if not get_client_or_404(slug):
        return err("Client nahi mila", 404)
    d = jdata()
    mid = tracker.add_media({
        "client_slug": slug,
        "kind": d.get("kind", "photo"),
        "note": (d.get("note") or "").strip(),
        "caption": (d.get("caption") or "").strip(),
        "file_url": (d.get("file_url") or "").strip(),
        "scheduled_date": (d.get("scheduled_date") or "").strip(),
    })
    return jsonify({"ok": True, "id": mid})


@app.route("/api/media/<slug>/<int:mid>/publish", methods=["POST"])
def api_media_publish(slug, mid):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    items = {m["id"]: m for m in tracker.get_media(slug)}
    m = items.get(mid)
    if not m or not m.get("file_url"):
        return jsonify({"ok": False,
                        "message": "Pehle publicly-hosted file URL add karo (Google ko direct file upload nahi hota, URL chahiye)."})
    if eff_dry_run():
        return jsonify({"ok": False, "message": "DRY-RUN ON hai — upload nahi hua."})
    if not auth.is_connected(slug):
        return jsonify({"ok": False, "message": "Client Google se connected nahi hai."})
    try:
        from gmb.api import GBPClient
        api = GBPClient(auth.load_credentials(slug), dry_run=False)
        parent = f"accounts/{c['account_id']}/locations/{c['location_id']}"
        api.create_media(parent, {
            "mediaFormat": "VIDEO" if m["kind"] == "video" else "PHOTO",
            "locationAssociation": {"category": "ADDITIONAL"},
            "sourceUrl": m["file_url"],
            "description": m.get("caption", ""),
        })
        tracker.update_media(mid, status="published")
        tracker.log_activity(slug, f"Media uploaded: {m.get('note')}", area="Media",
                             status="Published")
        return jsonify({"ok": True, "message": "Uploaded"})
    except Exception as e:
        return jsonify({"ok": False, "message": f"Upload fail: {e}"})


# ================= COMPETITORS =================
@app.route("/api/competitors/<slug>", methods=["GET"])
def api_competitors_get(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    comps = tracker.get_competitors(slug)
    dfs_on = dfs_mod.from_config(runtime_cfg) is not None
    return jsonify({"ok": True, "competitors": comps, "dataforseo_on": dfs_on})


@app.route("/api/competitors/<slug>", methods=["POST"])
def api_competitors_add(slug):
    if not get_client_or_404(slug):
        return err("Client nahi mila", 404)
    d = jdata()
    cid = tracker.add_competitor({
        "client_slug": slug,
        "name": (d.get("name") or "").strip(),
        "maps_url": (d.get("maps_url") or "").strip(),
        "rating": (d.get("rating") or "").strip(),
        "review_count": (d.get("review_count") or "").strip(),
        "categories": (d.get("categories") or "").strip(),
        "posting_freq": (d.get("posting_freq") or "").strip(),
        "notes": (d.get("notes") or "").strip(),
        "source": "manual",
    })
    return jsonify({"ok": True, "id": cid})


@app.route("/api/competitors/<slug>/<int:cid>", methods=["DELETE"])
def api_competitor_delete(slug, cid):
    if not _check_slug_access(slug):
        return err("Client nahi mila", 404)
    comp = tracker.get_competitor(cid)
    if not comp or comp.get("client_slug") != slug:
        return err("Competitor nahi mila", 404)
    tracker.delete_competitor(cid)
    return jsonify({"ok": True})


@app.route("/api/competitors/<slug>/dataforseo", methods=["POST"])
def api_competitors_dataforseo(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    d = jdata()
    try:
        dfs = dfs_mod.from_config(runtime_cfg)
        if not dfs:
            raise dfs_mod.DataForSEOError("DataForSEO enabled nahi hai (Settings dekho).")
        kw = (d.get("keyword") or "").strip() or c.get("category") or "services"
        loc = (d.get("location") or "").strip() or f"{c.get('city')},India"
        results = dfs.maps_search(kw, location_name=loc)
        added = 0
        for r in results:
            if not r.get("name"):
                continue
            tracker.add_competitor({
                "client_slug": slug, "name": r["name"], "maps_url": r.get("url", ""),
                "rating": str(r.get("rating") or ""), "review_count": str(r.get("review_count") or ""),
                "categories": r.get("categories", ""), "notes": r.get("address", ""),
                "source": "dataforseo",
            })
            added += 1
        log.info("dataforseo: %d competitors saved for %s", added, slug)
        return jsonify({"ok": True, "added": added})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ================= REPORTS =================
PERF_KEYS = ["impressions", "search_views", "maps_views", "website_clicks", "calls", "directions"]
ACT_KEYS = ["posts_published", "graphics_created", "images_uploaded", "videos_uploaded",
            "services_updated", "categories_updated", "reviews_received", "reviews_replied"]


@app.route("/api/reports/<slug>", methods=["GET"])
def api_reports_get(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    reps = tracker.get_reports(slug)
    return jsonify({"ok": True, "reports": reps, "perf_keys": PERF_KEYS, "act_keys": ACT_KEYS})


@app.route("/api/reports/<slug>/compile", methods=["POST"])
def api_reports_compile(slug):
    c = get_client_or_404(slug)
    if not c:
        return err("Client nahi mila", 404)
    d = jdata()
    ps, pe = (d.get("period_start") or ""), (d.get("period_end") or "")
    perf, activity, sources = {}, {}, {}
    use_api = bool(d.get("use_api")) and c["connected"] and c.get("location_id")
    if use_api:
        try:
            from gmb.api import GBPClient
            from datetime import datetime as dt
            api = GBPClient(auth.load_credentials(slug), dry_run=True)
            loc = f"locations/{c['location_id']}"
            s = dt.strptime(ps, "%Y-%m-%d").date()
            e = dt.strptime(pe, "%Y-%m-%d").date()
            resp = api.get_daily_metrics(loc, [
                "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH", "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
                "BUSINESS_IMPRESSIONS_DESKTOP_MAPS", "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
                "WEBSITE_CLICKS", "CALL_CLICKS", "BUSINESS_DIRECTION_REQUESTS"], s, e)
            totals: dict[str, int] = {}
            for series in (resp.get("multiDailyMetricTimeSeries") or []):
                m = series.get("dailyMetric", "")
                for pt in series.get("timeSeries", {}).get("datedValues", []):
                    totals[m] = totals.get(m, 0) + int(pt.get("value") or 0)
            perf = {
                "impressions": sum(v for k, v in totals.items() if "IMPRESSIONS" in k),
                "search_views": sum(v for k, v in totals.items() if "_SEARCH" in k),
                "maps_views": sum(v for k, v in totals.items() if "_MAPS" in k),
                "website_clicks": totals.get("WEBSITE_CLICKS", 0),
                "calls": totals.get("CALL_CLICKS", 0),
                "directions": totals.get("BUSINESS_DIRECTION_REQUESTS", 0),
            }
            sources = {k: "API" for k in perf}
        except Exception as e:
            state["error"] = f"Performance API fail: {e}"
            return err(f"Performance API fail: {e}")
    # manual fields (API values ko override nahi karte — khaali ho to bharo)
    perf_in = d.get("perf") or {}
    for k in PERF_KEYS:
        v = str(perf_in.get(k, "")).strip()
        if v and k not in perf:
            perf[k], sources[k] = v, "manual"
    act_in = d.get("activity") or {}
    for k in ACT_KEYS:
        v = str(act_in.get(k, "")).strip()
        if v:
            activity[k], sources[k] = v, "manual"
    seo_in = d.get("seo") or {}
    seo = {"keywords_targeted": (seo_in.get("keywords_targeted") or "").strip(),
           "new_opportunities": (seo_in.get("new_opportunities") or "").strip(),
           "competitor_notes": (seo_in.get("competitor_notes") or "").strip()}
    np = d.get("next_plan") or {}
    changes = np.get("changes") or []
    if isinstance(changes, str):
        changes = [x.strip() for x in changes.splitlines() if x.strip()]
    else:
        changes = [str(x).strip() for x in changes if str(x).strip()]
    next_plan = {
        "changes": changes,
        "keywords": (np.get("keywords") or "").strip(),
        "services": (np.get("services") or "").strip(),
        "topics": (np.get("topics") or "").strip(),
        "offers": (np.get("offers") or "").strip(),
        "visuals": (np.get("visuals") or "").strip(),
        "optimizations": (np.get("optimizations") or "").strip(),
    }
    md, html_path = reports_mod.compile_report(c, ps, pe, perf, activity, seo,
                                               next_plan, sources)
    rid = tracker.save_report(slug, ps, pe, html_path, sources)
    tracker.log_activity(slug, f"Report compiled ({ps} to {pe})", area="Reporting",
                         status="Verified")
    return jsonify({"ok": True, "id": rid})


@app.route("/api/report/<int:rid>")
def api_report_view(rid):
    op = current_operator()
    for cl in tracker.get_clients():
        # Demo reports shared dummy data hain; real reports sirf owner/super admin ko.
        if not cl.get("is_demo") and not (
                op and (op.get("role") == "super_admin" or cl.get("owner_id") == op["id"])):
            continue
        for r in tracker.get_reports(cl["slug"]):
            if r["id"] == rid:
                return send_file(r["html_path"])
    return jsonify({"ok": False, "error": "Report nahi mili"}), 404


# ================= MASTER TRACKER =================
@app.route("/api/tracker", methods=["GET"])
def api_tracker_get():
    op = current_operator()
    qslug = request.args.get("client_slug") or None
    if qslug:
        if not get_client_or_404(qslug):
            return err("Client nahi mila", 404)
        acts = tracker.get_activities(slug=qslug,
                                      status=request.args.get("status") or None)
    else:
        allowed = {c["slug"] for c in visible_clients(op)}
        acts = [a for a in tracker.get_activities(
                    status=request.args.get("status") or None)
                if not a.get("client_slug") or a["client_slug"] in allowed]
    return jsonify({"ok": True, "activities": acts, "statuses": STATUS_FLOW})


@app.route("/api/tracker", methods=["POST"])
def api_tracker_add():
    d = jdata()
    cslug = d.get("client_slug", "")
    if cslug and not _check_slug_access(cslug):
        return err("Client nahi mila", 404)
    aid = tracker.log_activity(d.get("client_slug", ""),
                               (d.get("activity") or "").strip(),
                               area=(d.get("area") or "").strip(),
                               status="Pending",
                               owner=(d.get("owner") or "").strip(),
                               due_date=(d.get("due_date") or "").strip(),
                               notes=(d.get("notes") or "").strip())
    return jsonify({"ok": True, "id": aid})


@app.route("/api/tracker/<int:aid>/transition", methods=["POST"])
def api_tracker_transition(aid):
    act = tracker.get_activity(aid)
    if not act:
        return jsonify({"ok": False, "message": "Activity nahi mili"})
    if act.get("client_slug") and not _check_slug_access(act["client_slug"]):
        return err("Client nahi mila", 404)
    ok, msg = tracker.transition_activity(aid, jdata().get("status", ""))
    return jsonify({"ok": ok, "message": msg})


# ================= SETTINGS =================
@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    op = current_operator()
    clients = visible_clients(op, mode="live")
    summary = []
    for c in clients:
        summary.append({
            "slug": c["slug"],
            "name": c.get("name"),
            "auto_publish": c.get("auto_publish", 0),
            "connected": auth.is_connected(c["slug"]),
        })
    return jsonify({
        "ok": True,
        "dry_run": eff_dry_run(),
        "integrations": integrations_ctx(),
        "clients": summary,
    })


@app.route("/api/settings", methods=["POST"])
def api_settings_set():
    # Production safety: do not allow dashboard settings to disable dry-run.
    tracker.kv_set("dry_run", "True")
    log.warning("dry_run forced to True by production safety guard")
    return jsonify({"ok": True, "dry_run": True})


@app.route("/api/demo/seed", methods=["POST"])
def api_demo_seed():
    """Settings page ka 'Add demo client' button — local demo data banata hai.
    Google ko kuch nahi bhejta, sirf local DB me dummy records."""
    from gmb import seed as seed_mod
    d = jdata()
    try:
        if d.get("reset"):
            seed_mod.reset_demo_data(tracker)
        summary = seed_mod.seed_demo_data(tracker, runtime_cfg.get("posting", {}) or {})
        tracker.log_activity(summary["slug"], "Demo data seeded from Settings",
                             area="System", status="Verified")
        return jsonify({"ok": True, **summary})
    except ValueError as e:
        return err(str(e), 400)
    except Exception as e:
        log.exception("demo seed failed")
        return err(f"Seed failed: {e}", 500)


# ================= SPA SERVING (sab /api routes ke baad) =================
DIST = BASE_DIR / "frontend" / "dist"


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    if path.startswith("api/"):
        return jsonify({"ok": False, "error": "unknown endpoint"}), 404
    f = DIST / path if path else None
    if f and f.is_file():
        return send_from_directory(str(DIST), path)
    idx = DIST / "index.html"
    if idx.exists():
        return send_from_directory(str(DIST), "index.html")
    return jsonify({"ok": False, "error": "frontend not built yet — run: cd frontend && npm install && npm run build"}), 503


# ================= MAIN =================
# Gunicorn/Render jaise WSGI server import par chalate hain (__main__ nahi chalta),
# isliye scheduler env flag se start hota hai. Local `python app.py` me __main__ wala rasta same hai.
if os.environ.get("START_SCHEDULER") == "1" and os.environ.get("ENABLE_GMB_SCHEDULER") == "1":
    sched_mod.start(tracker, runtime_cfg)

if __name__ == "__main__":
    sched_mod.start(tracker, runtime_cfg)
    port = int(os.environ.get("PORT") or (CFG.get("app") or {}).get("port", 5003))
    host = (CFG.get("app") or {}).get("host", "127.0.0.1")
    print(f"UI kholo: http://{host}:{port}")
    if eff_dry_run():
        print("MODE: DRY-RUN — Google par kuch publish nahi hoga (Settings me badlo, API approval ke baad).")
    app.run(host=host, port=port, debug=False, use_reloader=False)
