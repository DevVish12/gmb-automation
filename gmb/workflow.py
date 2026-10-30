"""Workflow additions (PDF Sections 2.2/2.3/2.4, 5, 10, 12).

- Profile Optimization records: category / service / description proposals.
  Tool live profile khud kabhi nahi badalta — human approval ke baad
  operator Google par manually apply karta hai (profile edits par
  re-verification risk hota hai, isliye ye step hamesha human-checked).
- Creative briefs + QA checklist (Section 5).
- Master tracker extra columns (Section 12) + post extra fields (Section 4).
- Pipeline progression view (Section 10) — stages real data se derive hote hain.

SAFETY: is module me koi Google write nahi hai. Publishing, approval-gating
aur dry-run logic bilkul nahi chheda gaya.
"""
import json
import sqlite3
import threading
from datetime import datetime

_LOCK = threading.Lock()

# Section 5 — Creative QA checklist (document ke 12 points, exact)
QA_ITEMS = [
    ("business_name", "Correct business name"),
    ("logo", "Correct logo"),
    ("phone", "Correct phone number"),
    ("offer", "Correct offer"),
    ("spelling", "Correct spelling"),
    ("keyword", "Correct keyword"),
    ("location", "Correct location"),
    ("misleading", "No misleading information"),
    ("readable", "Text is readable"),
    ("not_crowded", "Design is not overcrowded"),
    ("brand", "Brand identity maintained"),
    ("different", "Sufficiently different from previous posts"),
]

# Section 3 — visual content categories
VISUAL_CATEGORIES = [
    "exterior", "interior", "service", "product", "work",
    "equipment", "facilities", "team", "completed",
    "before-after", "short-video", "service-visual",
]

OPT_TYPES = ["category", "service", "description"]
OPT_STATUSES = ["proposed", "approved", "applied", "rejected"]
OPT_PRIORITIES = ["High", "Medium", "Low"]


def _conn(db_path):
    c = sqlite3.connect(db_path, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def _now():
    return datetime.now().isoformat(timespec="seconds")


def ensure_schema(db_path):
    """Nayi tables + purani tables par doc wale columns (idempotent)."""
    with _LOCK, _conn(db_path) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS optimizations(
            id INTEGER PRIMARY KEY AUTOINCREMENT, client_slug TEXT,
            opt_type TEXT, item_name TEXT, current_value TEXT DEFAULT '',
            proposed_value TEXT DEFAULT '', keywords TEXT DEFAULT '',
            priority TEXT DEFAULT 'Medium', status TEXT DEFAULT 'proposed',
            notes TEXT DEFAULT '', created_at TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS creatives(
            id INTEGER PRIMARY KEY AUTOINCREMENT, client_slug TEXT,
            post_id INTEGER DEFAULT 0, keyword TEXT DEFAULT '',
            topic TEXT DEFAULT '', headline TEXT DEFAULT '',
            supporting_text TEXT DEFAULT '', cta TEXT DEFAULT '',
            brand_notes TEXT DEFAULT '', visual_concept TEXT DEFAULT '',
            offer_info TEXT DEFAULT '', qa_json TEXT DEFAULT '{}',
            qa_status TEXT DEFAULT 'pending', status TEXT DEFAULT 'draft',
            created_at TEXT, updated_at TEXT);
        """)

        def _cols(table):
            return {r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}

        def _add(table, col, ddl):
            if col not in _cols(table):
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")

        for col, ddl in [("intent", "TEXT DEFAULT ''"),
                         ("problem", "TEXT DEFAULT ''"),
                         ("offer_details", "TEXT DEFAULT ''"),
                         ("creative_id", "INTEGER DEFAULT 0")]:
            _add("posts", col, ddl)
        for col, ddl in [("keyword", "TEXT DEFAULT ''"),
                         ("topic", "TEXT DEFAULT ''"),
                         ("copy_text", "TEXT DEFAULT ''"),
                         ("creative", "TEXT DEFAULT ''"),
                         ("qa_approval", "TEXT DEFAULT 'pending'"),
                         ("published", "TEXT DEFAULT ''"),
                         ("proof", "TEXT DEFAULT ''")]:
            _add("activities", col, ddl)
        for col, ddl in [("services", "TEXT DEFAULT ''"),
                         ("offers", "TEXT DEFAULT ''"),
                         ("post_topics", "TEXT DEFAULT ''")]:
            _add("competitors", col, ddl)
        _add("media", "visual_category", "TEXT DEFAULT ''")


# ---------- optimizations ----------

def add_optimization(db_path, data):
    with _LOCK, _conn(db_path) as c:
        cur = c.execute(
            """INSERT INTO optimizations(client_slug,opt_type,item_name,current_value,
               proposed_value,keywords,priority,status,notes,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (data["client_slug"], data.get("opt_type", "category"),
             data.get("item_name", ""), data.get("current_value", ""),
             data.get("proposed_value", ""), data.get("keywords", ""),
             data.get("priority", "Medium"), data.get("status", "proposed"),
             data.get("notes", ""), _now(), _now()))
        return cur.lastrowid


def get_optimizations(db_path, slug):
    with _LOCK, _conn(db_path) as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM optimizations WHERE client_slug=? ORDER BY id DESC", (slug,))]


def update_optimization(db_path, oid, slug, fields):
    allowed = {"opt_type", "item_name", "current_value", "proposed_value",
               "keywords", "priority", "status", "notes"}
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        return False
    sets.append("updated_at=?")
    vals.append(_now())
    vals += [oid, slug]
    with _LOCK, _conn(db_path) as c:
        cur = c.execute(
            f"UPDATE optimizations SET {', '.join(sets)} WHERE id=? AND client_slug=?", vals)
        return cur.rowcount > 0


def delete_optimization(db_path, oid, slug):
    with _LOCK, _conn(db_path) as c:
        cur = c.execute(
            "DELETE FROM optimizations WHERE id=? AND client_slug=?", (oid, slug))
        return cur.rowcount > 0


# ---------- creatives ----------

def _qa_str(qa):
    if isinstance(qa, dict):
        return json.dumps(qa)
    return qa or "{}"


def add_creative(db_path, data):
    with _LOCK, _conn(db_path) as c:
        cur = c.execute(
            """INSERT INTO creatives(client_slug,post_id,keyword,topic,headline,
               supporting_text,cta,brand_notes,visual_concept,offer_info,qa_json,
               qa_status,status,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data["client_slug"], int(data.get("post_id") or 0),
             data.get("keyword", ""), data.get("topic", ""),
             data.get("headline", ""), data.get("supporting_text", ""),
             data.get("cta", ""), data.get("brand_notes", ""),
             data.get("visual_concept", ""), data.get("offer_info", ""),
             _qa_str(data.get("qa_json")), data.get("qa_status", "pending"),
             data.get("status", "draft"), _now(), _now()))
        return cur.lastrowid


def get_creatives(db_path, slug):
    with _LOCK, _conn(db_path) as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM creatives WHERE client_slug=? ORDER BY id DESC", (slug,))]


def get_creative(db_path, cid, slug):
    with _LOCK, _conn(db_path) as c:
        r = c.execute(
            "SELECT * FROM creatives WHERE id=? AND client_slug=?", (cid, slug)).fetchone()
        return dict(r) if r else None


def update_creative(db_path, cid, slug, fields):
    allowed = {"post_id", "keyword", "topic", "headline", "supporting_text",
               "cta", "brand_notes", "visual_concept", "offer_info",
               "qa_status", "status"}
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k}=?")
            vals.append(v)
    if "qa_json" in fields:
        sets.append("qa_json=?")
        vals.append(_qa_str(fields["qa_json"]))
    if not sets:
        return False
    sets.append("updated_at=?")
    vals.append(_now())
    vals += [cid, slug]
    with _LOCK, _conn(db_path) as c:
        cur = c.execute(
            f"UPDATE creatives SET {', '.join(sets)} WHERE id=? AND client_slug=?", vals)
        return cur.rowcount > 0


def delete_creative(db_path, cid, slug):
    with _LOCK, _conn(db_path) as c:
        cur = c.execute(
            "DELETE FROM creatives WHERE id=? AND client_slug=?", (cid, slug))
        return cur.rowcount > 0


def brief_from_post(post, client):
    """Post ke fields se creative brief banao (Section 5 + 11: brief generation)."""
    cta = post.get("cta_type") or "LEARN_MORE"
    if post.get("cta_url"):
        cta += f" → {post['cta_url']}"
    return {
        "keyword": post.get("keyword") or "",
        "topic": post.get("topic") or "",
        "headline": (post.get("summary") or "")[:120],
        "supporting_text": post.get("summary") or "",
        "cta": cta,
        "brand_notes": client.get("business_name") or client.get("name") or "",
        "visual_concept": f"{post.get('post_type') or 'standard'} post — {post.get('topic') or ''}",
        "offer_info": post.get("offer_details") or "",
    }


# ---------- pipeline (Section 10) ----------

def pipeline_status(tracker, slug, dry_run=False):
    """17 pipeline stages + next cycle — har stage real data se derive hota hai."""
    stages = []

    def add(key, title, state, detail):
        stages.append({"key": key, "title": title, "state": state, "detail": detail})

    add("onboarding", "Client Onboarding", "done", "Client tool me registered hai.")

    saved_audit = tracker.kv_get(f"audit:{slug}")
    if saved_audit:
        try:
            r = json.loads(saved_audit)
            add("audit", "AI-Based GMB Audit", "done",
                f"Score {r.get('score')} ({r.get('grade')}) — "
                f"{r.get('high', 0)} high, {r.get('medium', 0)} medium, {r.get('low', 0)} low findings.")
        except Exception:
            add("audit", "AI-Based GMB Audit", "done", "Audit run ho chuka hai.")
    else:
        add("audit", "AI-Based GMB Audit", "not-started", "Audit abhi run nahi hua.")

    kws = tracker.get_keywords(slug)
    add("keywords", "Keyword Research", "done" if kws else "not-started",
        f"{len(kws)} keywords mapped." if kws else "Keywords abhi add nahi hue.")

    comps = tracker.get_competitors(slug)
    add("competitors", "Competitor Analysis", "done" if comps else "not-started",
        f"{len(comps)} competitors tracked." if comps else "Competitors abhi add nahi hue.")

    opts = get_optimizations(tracker.db_path, slug)

    def _opt_stage(key, title, otype):
        mine = [o for o in opts if o.get("opt_type") == otype]
        done = [o for o in mine if o.get("status") in ("approved", "applied")]
        if done:
            add(key, title, "done", f"{len(done)} approved/applied, {len(mine)} total proposals.")
        elif mine:
            add(key, title, "in-progress", f"{len(mine)} proposals pending review.")
        else:
            add(key, title, "not-started", "Koi proposal abhi nahi hai.")

    _opt_stage("categories", "Primary & Secondary Category Optimization", "category")
    _opt_stage("services", "Services Section Optimization", "service")
    _opt_stage("description", "Business Description Optimization", "description")

    revs = tracker.get_reviews(slug, only_pending=False)
    unans = [r for r in revs if r.get("reply_status") in ("none", "draft")]
    if not revs:
        add("reviews", "Review Management", "not-started", "Reviews abhi fetch nahi hue.")
    elif not unans:
        add("reviews", "Review Management", "done", f"{len(revs)} reviews, sabke jawab ho gaye.")
    else:
        add("reviews", "Review Management", "in-progress", f"{len(unans)} reviews ka jawab pending.")

    media = tracker.get_media(slug)
    pub_media = [m for m in media if m.get("status") == "published"]
    if pub_media:
        add("media", "Images & Videos Upload", "done", f"{len(pub_media)} photos/videos published.")
    elif media:
        add("media", "Images & Videos Upload", "in-progress", f"{len(media)} planned, koi publish nahi.")
    else:
        add("media", "Images & Videos Upload", "not-started", "Koi photo/video plan nahi hai.")

    cal = tracker.kv_get(f"caldraft:{slug}")
    if cal:
        try:
            slots = json.loads(cal).get("slots", [])
            add("planning", "Monthly Content Planning", "done", f"{len(slots)} post slots planned.")
        except Exception:
            add("planning", "Monthly Content Planning", "done", "Calendar generate ho chuka hai.")
    else:
        add("planning", "Monthly Content Planning", "not-started", "Calendar abhi generate nahi hua.")

    posts = tracker.get_posts(slug)
    add("posts", "GMB Post Creation", "done" if posts else "not-started",
        f"{len(posts)} post drafts." if posts else "Koi post draft nahi hai.")

    crs = get_creatives(tracker.db_path, slug)
    add("creatives", "Graphic Creation", "done" if crs else "not-started",
        f"{len(crs)} creative briefs." if crs else "Koi creative brief nahi hai.")

    passed = [x for x in crs if x.get("qa_status") == "passed"]
    if passed:
        add("qa", "Quality Check", "done", f"{len(passed)} creatives QA passed.")
    elif crs:
        add("qa", "Quality Check", "in-progress", "Creatives hain, QA pending hai.")
    else:
        add("qa", "Quality Check", "not-started", "QA karne ke liye koi creative nahi hai.")

    approved = [p for p in posts if p.get("status") in ("approved", "scheduled", "published")]
    pend_appr = [p for p in posts if p.get("requires_approval") and p.get("status") == "draft"]
    if approved:
        add("approval", "Client Approval", "done", f"{len(approved)} posts approved ya aage badh chuke.")
    elif pend_appr:
        add("approval", "Client Approval", "in-progress", f"{len(pend_appr)} posts approval pending.")
    else:
        add("approval", "Client Approval", "not-started", "Koi post approval flow me nahi hai.")

    published = [p for p in posts if p.get("status") == "published"]
    scheduled = [p for p in posts if p.get("status") == "scheduled"]
    if published:
        add("publishing", "GMB Publishing", "done",
            f"{len(published)} posts published."
            + (" (Dry-run ON — live publish ke liye Basic Access approval chahiye.)" if dry_run else ""))
    elif scheduled:
        add("publishing", "GMB Publishing", "in-progress", f"{len(scheduled)} posts scheduled.")
    else:
        add("publishing", "GMB Publishing", "not-started",
            "Koi post publish/schedule nahi hai."
            + (" Dry-run ON hai — live publish ke liye Basic Access approval chahiye." if dry_run else ""))

    acts = tracker.get_activities(slug=slug)
    add("tracking", "Activity & Performance Tracking", "done" if acts else "not-started",
        f"{len(acts)} activities logged." if acts else "Koi activity log nahi hai.")

    reps = tracker.get_reports(slug)
    add("reporting", "Bi-Weekly / Monthly Reporting", "done" if reps else "not-started",
        f"{len(reps)} reports compiled." if reps else "Koi report compile nahi hui.")

    add("next-cycle", "Next Optimization Cycle",
        "in-progress" if reps else "not-started",
        "Report ke baad agla cycle audit se shuru hota hai." if reps
        else "Pehle cycle ki reporting poori hone par agla cycle shuru hoga.")

    done = sum(1 for s in stages if s["state"] == "done")
    return {"stages": stages, "done": done, "total": len(stages)}
