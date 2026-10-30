"""Master Activity Tracker — SQLite (PDF Sections 8, 12).

Status flow (activities): Pending -> In Progress -> Ready for QA -> Approved
                          -> Scheduled -> Published -> Verified
Har transition validate hota hai — galat jump reject.
"""
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

STATUS_FLOW = ["Pending", "In Progress", "Ready for QA", "Approved",
               "Scheduled", "Published", "Verified"]

# allowed transitions: current -> [next allowed]
TRANSITIONS = {
    "Pending": ["In Progress"],
    "In Progress": ["Ready for QA", "Pending"],
    "Ready for QA": ["Approved", "In Progress"],
    "Approved": ["Scheduled", "In Progress"],
    "Scheduled": ["Published", "Approved"],
    "Published": ["Verified"],
    "Verified": [],
}

POST_STATUS = ["draft", "approved", "scheduled", "published", "failed"]


class Tracker:
    def __init__(self, db_path: str | None = None):
        self.db_path = str(Path(db_path) if db_path else BASE_DIR / "gmb_automation.db")
        self._lock = threading.Lock()
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.db_path, check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c

    def _init(self):
        with self._lock, self._conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS clients(
                slug TEXT PRIMARY KEY, name TEXT, business_name TEXT,
                account_id TEXT, location_id TEXT, category TEXT, city TEXT,
                phone TEXT, website TEXT, services_json TEXT DEFAULT '[]',
                secrets_path TEXT DEFAULT '', auto_publish INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1, connected INTEGER DEFAULT 0,
                created_at TEXT);
            CREATE TABLE IF NOT EXISTS keywords(
                id INTEGER PRIMARY KEY AUTOINCREMENT, client_slug TEXT,
                keyword TEXT, ktype TEXT DEFAULT 'secondary', mapped_to TEXT DEFAULT '',
                volume TEXT DEFAULT '', added_at TEXT);
            CREATE TABLE IF NOT EXISTS posts(
                id INTEGER PRIMARY KEY AUTOINCREMENT, client_slug TEXT,
                scheduled_date TEXT, post_type TEXT, topic TEXT, keyword TEXT,
                summary TEXT, topic_type TEXT, cta_type TEXT, cta_url TEXT,
                status TEXT DEFAULT 'draft', requires_approval INTEGER DEFAULT 0,
                gmb_post_name TEXT DEFAULT '', published_at TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS reviews(
                review_name TEXT PRIMARY KEY, client_slug TEXT, reviewer TEXT,
                stars INTEGER, text TEXT, create_time TEXT, update_time TEXT,
                has_reply INTEGER DEFAULT 0, reply_text TEXT DEFAULT '',
                reply_hash TEXT DEFAULT '', reply_status TEXT DEFAULT 'none',
                needs_human INTEGER DEFAULT 0, fetched_at TEXT);
            CREATE TABLE IF NOT EXISTS media(
                id INTEGER PRIMARY KEY AUTOINCREMENT, client_slug TEXT,
                kind TEXT, note TEXT, caption TEXT, file_url TEXT DEFAULT '',
                status TEXT DEFAULT 'planned', scheduled_date TEXT,
                published_at TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS activities(
                id INTEGER PRIMARY KEY AUTOINCREMENT, client_slug TEXT,
                activity TEXT, area TEXT DEFAULT '', status TEXT DEFAULT 'Pending',
                owner TEXT DEFAULT '', due_date TEXT DEFAULT '', notes TEXT DEFAULT '',
                created_at TEXT, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS competitors(
                id INTEGER PRIMARY KEY AUTOINCREMENT, client_slug TEXT,
                name TEXT, maps_url TEXT DEFAULT '', rating TEXT DEFAULT '',
                review_count TEXT DEFAULT '', categories TEXT DEFAULT '',
                posting_freq TEXT DEFAULT '', notes TEXT DEFAULT '',
                source TEXT DEFAULT 'manual', added_at TEXT);
            CREATE TABLE IF NOT EXISTS reports(
                id INTEGER PRIMARY KEY AUTOINCREMENT, client_slug TEXT,
                period_start TEXT, period_end TEXT, html_path TEXT,
                sources_json TEXT DEFAULT '{}', created_at TEXT);
            CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS operators(
                id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE,
                name TEXT DEFAULT '', password_hash TEXT DEFAULT '',
                role TEXT DEFAULT 'operator', is_active INTEGER DEFAULT 1,
                created_at TEXT);
            CREATE TABLE IF NOT EXISTS login_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT, operator_id INTEGER,
                email TEXT, ip TEXT DEFAULT '', user_agent TEXT DEFAULT '',
                created_at TEXT);
            """)
            # Purani DBs ke liye migration: clients me owner/is_demo columns jodo.
            cols = {r[1] for r in c.execute("PRAGMA table_info(clients)").fetchall()}
            if "owner_id" not in cols:
                c.execute("ALTER TABLE clients ADD COLUMN owner_id INTEGER")
            if "is_demo" not in cols:
                c.execute("ALTER TABLE clients ADD COLUMN is_demo INTEGER DEFAULT 0")
            # Demo client hamesha demo-marked rahe (kabhi delete nahi hota, sirf filter hota hai).
            c.execute("UPDATE clients SET is_demo=1 WHERE slug='sharma-dental-clinic'")

    # ---------- generic ----------
    def now(self):
        return datetime.now().isoformat(timespec="seconds")

    def kv_get(self, key, default=""):
        with self._lock, self._conn() as c:
            r = c.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
            return r["value"] if r else default

    def kv_set(self, key, value):
        with self._lock, self._conn() as c:
            c.execute("INSERT OR REPLACE INTO kv(key,value) VALUES(?,?)", (key, value))

    # ---------- clients ----------
    def add_client(self, data: dict) -> str:
        slug = (data.get("slug") or data["name"]).lower().strip()
        slug = "".join(ch if ch.isalnum() else "-" for ch in slug).strip("-")
        with self._lock, self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO clients
                   (slug,name,business_name,account_id,location_id,category,city,phone,
                    website,services_json,secrets_path,auto_publish,active,connected,
                    owner_id,is_demo,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (slug, data.get("name"), data.get("business_name") or data.get("name"),
                 data.get("account_id", ""), data.get("location_id", ""),
                 data.get("category", ""), data.get("city", ""), data.get("phone", ""),
                 data.get("website", ""), json.dumps(data.get("services") or []),
                 data.get("secrets_path", ""), int(data.get("auto_publish", 0)),
                 1, int(data.get("connected", 0)), data.get("owner_id"),
                 int(data.get("is_demo", 0)), self.now()))
        return slug

    def get_client(self, slug: str) -> dict | None:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM clients WHERE slug=?", (slug,)).fetchone()
            return self._client_dict(r) if r else None

    def get_clients(self, active_only=True) -> list[dict]:
        q = "SELECT * FROM clients" + (" WHERE active=1" if active_only else "") + " ORDER BY name"
        with self._lock, self._conn() as c:
            return [self._client_dict(r) for r in c.execute(q).fetchall()]

    def _client_dict(self, r) -> dict:
        d = dict(r)
        try:
            d["services"] = json.loads(d.get("services_json") or "[]")
        except Exception:
            d["services"] = []
        return d

    def update_client(self, slug: str, **fields):
        allowed = {"name", "business_name", "account_id", "location_id", "category",
                   "city", "phone", "website", "secrets_path", "auto_publish",
                   "active", "connected", "owner_id", "is_demo"}
        sets, vals = [], []
        for k, v in fields.items():
            if k == "services":
                sets.append("services_json=?"); vals.append(json.dumps(v or []))
            elif k in allowed:
                sets.append(f"{k}=?"); vals.append(v)
        if not sets:
            return
        vals.append(slug)
        with self._lock, self._conn() as c:
            c.execute(f"UPDATE clients SET {', '.join(sets)} WHERE slug=?", vals)

    def delete_client(self, slug):
        """Delete a client and ALL its local data. Returns dict of removed counts.
        NOTE: content already published to Google is NOT touched — that must be
        removed manually from the Business Profile."""
        removed = {}
        report_files = []
        with self._lock, self._conn() as c:
            rows = c.execute(
                "SELECT html_path FROM reports WHERE client_slug=?", (slug,)).fetchall()
            report_files = [r["html_path"] for r in rows if r["html_path"]]
            for table in ("keywords", "posts", "reviews", "media", "activities",
                          "competitors", "reports"):
                cur = c.execute(f"DELETE FROM {table} WHERE client_slug=?", (slug,))
                removed[table] = cur.rowcount
            for key in (f"audit:{slug}", f"caldraft:{slug}", f"last_review_check:{slug}"):
                c.execute("DELETE FROM kv WHERE key=?", (key,))
            cur = c.execute("DELETE FROM clients WHERE slug=?", (slug,))
            removed["clients"] = cur.rowcount
        # delete generated report HTML files — only inside the reports/ dir (safety)
        reports_dir = (BASE_DIR / "reports").resolve()
        for hp in report_files:
            try:
                p = Path(hp).resolve()
                if p.is_file() and reports_dir in p.parents:
                    p.unlink()
                    removed["report_files"] = removed.get("report_files", 0) + 1
            except Exception:
                pass
        return removed

    # ---------- keywords ----------
    def add_keyword(self, slug, keyword, ktype="secondary", mapped_to="", volume=""):
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO keywords(client_slug,keyword,ktype,mapped_to,volume,added_at)"
                " VALUES(?,?,?,?,?,?)",
                (slug, keyword, ktype, mapped_to, volume, self.now()))

    def get_keywords(self, slug) -> list[dict]:
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM keywords WHERE client_slug=? ORDER BY added_at", (slug,))]

    def update_keyword(self, kid, **fields):
        allowed = {"keyword", "ktype", "mapped_to", "volume"}
        sets, vals = [], []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k}=?"); vals.append(v)
        if sets:
            vals.append(kid)
            with self._lock, self._conn() as c:
                c.execute(f"UPDATE keywords SET {', '.join(sets)} WHERE id=?", vals)

    def delete_keyword(self, kid):
        with self._lock, self._conn() as c:
            c.execute("DELETE FROM keywords WHERE id=?", (kid,))

    # ---------- posts (content queue) ----------
    def queue_post(self, data: dict) -> int:
        with self._lock, self._conn() as c:
            cur = c.execute(
                """INSERT INTO posts(client_slug,scheduled_date,post_type,topic,keyword,
                   summary,topic_type,cta_type,cta_url,status,requires_approval,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (data["client_slug"], data.get("scheduled_date", ""),
                 data.get("post_type", ""), data.get("topic", ""), data.get("keyword", ""),
                 data.get("summary", ""), data.get("topic_type", "STANDARD"),
                 data.get("cta_type", "LEARN_MORE"), data.get("cta_url", ""),
                 data.get("status", "draft"), int(data.get("requires_approval", 0)),
                 self.now()))
            return cur.lastrowid

    def get_posts(self, slug, status: str | None = None) -> list[dict]:
        q = "SELECT * FROM posts WHERE client_slug=?"
        args: list = [slug]
        if status:
            q += " AND status=?"; args.append(status)
        q += " ORDER BY scheduled_date, id"
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(q, args)]

    def get_due_posts(self) -> list[dict]:
        """scheduled posts jinki date aa gayi."""
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM posts WHERE status='scheduled' AND scheduled_date <= date('now')"
                " ORDER BY scheduled_date")]

    def update_post(self, pid: int, **fields):
        allowed = {"scheduled_date", "post_type", "topic", "keyword", "summary",
                   "topic_type", "cta_type", "cta_url", "status", "requires_approval",
                   "gmb_post_name", "published_at",
                   # PDF Section 4 post fields
                   "intent", "problem", "offer_details", "creative_id"}
        sets, vals = [], []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k}=?"); vals.append(v)
        if sets:
            if fields.get("status") == "published" and "published_at" not in fields:
                sets.append("published_at=?"); vals.append(self.now())
            vals.append(pid)
            with self._lock, self._conn() as c:
                c.execute(f"UPDATE posts SET {', '.join(sets)} WHERE id=?", vals)

    def delete_post(self, pid: int):
        with self._lock, self._conn() as c:
            c.execute("DELETE FROM posts WHERE id=?", (pid,))

    # ---------- reviews ----------
    def save_review(self, rec: dict):
        with self._lock, self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO reviews
                   (review_name,client_slug,reviewer,stars,text,create_time,update_time,
                    has_reply,reply_text,reply_hash,reply_status,needs_human,fetched_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (rec["review_name"], rec["client_slug"], rec.get("reviewer", ""),
                 rec.get("stars", 0), rec.get("text", ""), rec.get("create_time", ""),
                 rec.get("update_time", ""), int(rec.get("has_reply", 0)),
                 rec.get("reply_text", ""), rec.get("reply_hash", ""),
                 rec.get("reply_status", "none"), int(rec.get("needs_human", 0)),
                 self.now()))

    def get_reviews(self, slug, only_pending=True) -> list[dict]:
        q = "SELECT * FROM reviews WHERE client_slug=?"
        if only_pending:
            q += " AND reply_status IN ('none','draft')"
        q += " ORDER BY stars ASC, update_time DESC"
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(q, (slug,))]

    def known_review_names(self, slug) -> set[str]:
        with self._lock, self._conn() as c:
            return {r["review_name"] for r in c.execute(
                "SELECT review_name FROM reviews WHERE client_slug=?", (slug,))}

    def recent_reply_hashes(self, slug, limit=30) -> set[str]:
        with self._lock, self._conn() as c:
            return {r["reply_hash"] for r in c.execute(
                "SELECT reply_hash FROM reviews WHERE client_slug=? AND reply_hash!=''"
                " ORDER BY fetched_at DESC LIMIT ?", (slug, limit))}

    def update_review_reply(self, review_name, **fields):
        allowed = {"reply_text", "reply_hash", "reply_status", "needs_human", "has_reply"}
        sets, vals = [], []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k}=?"); vals.append(v)
        if sets:
            vals.append(review_name)
            with self._lock, self._conn() as c:
                c.execute(f"UPDATE reviews SET {', '.join(sets)} WHERE review_name=?", vals)

    # ---------- media ----------
    def add_media(self, data: dict) -> int:
        with self._lock, self._conn() as c:
            cur = c.execute(
                """INSERT INTO media(client_slug,kind,note,caption,file_url,status,
                   scheduled_date,visual_category,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                (data["client_slug"], data.get("kind", "photo"), data.get("note", ""),
                 data.get("caption", ""), data.get("file_url", ""),
                 data.get("status", "planned"), data.get("scheduled_date", ""),
                 data.get("visual_category", ""), self.now()))
            return cur.lastrowid

    def get_media(self, slug) -> list[dict]:
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM media WHERE client_slug=? ORDER BY scheduled_date", (slug,))]

    def update_media(self, mid: int, **fields):
        allowed = {"kind", "note", "caption", "file_url", "status", "scheduled_date",
                   "published_at", "visual_category"}
        sets, vals = [], []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k}=?"); vals.append(v)
        if sets:
            vals.append(mid)
            with self._lock, self._conn() as c:
                c.execute(f"UPDATE media SET {', '.join(sets)} WHERE id=?", vals)

    # ---------- activities (master tracker) ----------
    def log_activity(self, slug, activity, area="", status="Pending", owner="",
                     due_date="", notes="", keyword="", topic="", copy_text="",
                     creative="", qa_approval="pending", published="", proof="") -> int:
        if status not in STATUS_FLOW:
            status = "Pending"
        with self._lock, self._conn() as c:
            cur = c.execute(
                """INSERT INTO activities(client_slug,activity,area,status,owner,
                   due_date,notes,keyword,topic,copy_text,creative,qa_approval,
                   published,proof,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (slug, activity, area, status, owner, due_date, notes,
                 keyword, topic, copy_text, creative, qa_approval, published, proof,
                 self.now(), self.now()))
            return cur.lastrowid

    def get_activities(self, slug: str | None = None, status: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM activities", []
        wh = []
        if slug:
            wh.append("client_slug=?"); args.append(slug)
        if status:
            wh.append("status=?"); args.append(status)
        if wh:
            q += " WHERE " + " AND ".join(wh)
        q += " ORDER BY updated_at DESC LIMIT 500"
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(q, args)]

    def transition_activity(self, aid: int, new_status: str) -> tuple[bool, str]:
        if new_status not in STATUS_FLOW:
            return False, f"Unknown status: {new_status}"
        with self._lock, self._conn() as c:
            r = c.execute("SELECT status FROM activities WHERE id=?", (aid,)).fetchone()
            if not r:
                return False, "Activity nahi mili"
            cur = r["status"]
            if new_status == cur:
                return True, "No change"
            if new_status not in TRANSITIONS.get(cur, []):
                return False, f"'{cur}' se '{new_status}' jump allowed nahi"
            c.execute("UPDATE activities SET status=?, updated_at=? WHERE id=?",
                      (new_status, self.now(), aid))
            return True, f"{cur} -> {new_status}"

    # ---------- competitors ----------
    def add_competitor(self, data: dict) -> int:
        with self._lock, self._conn() as c:
            cur = c.execute(
                """INSERT INTO competitors(client_slug,name,maps_url,rating,review_count,
                   categories,posting_freq,notes,source,services,offers,post_topics,added_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (data["client_slug"], data.get("name", ""), data.get("maps_url", ""),
                 data.get("rating", ""), data.get("review_count", ""),
                 data.get("categories", ""), data.get("posting_freq", ""),
                 data.get("notes", ""), data.get("source", "manual"),
                 data.get("services", ""), data.get("offers", ""),
                 data.get("post_topics", ""), self.now()))
            return cur.lastrowid

    def get_competitors(self, slug) -> list[dict]:
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM competitors WHERE client_slug=? ORDER BY added_at DESC", (slug,))]

    def delete_competitor(self, cid: int):
        with self._lock, self._conn() as c:
            c.execute("DELETE FROM competitors WHERE id=?", (cid,))

    # ---------- reports ----------
    def save_report(self, slug, period_start, period_end, html_path, sources: dict) -> int:
        with self._lock, self._conn() as c:
            cur = c.execute(
                "INSERT INTO reports(client_slug,period_start,period_end,html_path,sources_json,created_at)"
                " VALUES(?,?,?,?,?,?)",
                (slug, period_start, period_end, html_path,
                 json.dumps(sources), self.now()))
            return cur.lastrowid

    def get_reports(self, slug) -> list[dict]:
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM reports WHERE client_slug=? ORDER BY created_at DESC", (slug,))]

    def claim_unowned_clients(self, operator_id: int):
        """Pehle operator (super admin) ko saare owner-less real clients de do.
        Demo client is_demo=1 hai, isliye isme nahi aata."""
        with self._lock, self._conn() as c:
            c.execute(
                "UPDATE clients SET owner_id=? WHERE owner_id IS NULL AND is_demo=0",
                (operator_id,))

    # ---------- operators (SaaS accounts) ----------
    def create_operator(self, email: str, name: str, password_hash: str, role: str) -> int:
        with self._lock, self._conn() as c:
            cur = c.execute(
                "INSERT INTO operators(email,name,password_hash,role,is_active,created_at)"
                " VALUES(?,?,?,?,1,?)",
                (email, name, password_hash, role, self.now()))
            return cur.lastrowid

    def get_operator_by_email(self, email: str) -> dict | None:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM operators WHERE email=?", (email,)).fetchone()
            return dict(r) if r else None

    def get_operator(self, oid: int) -> dict | None:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM operators WHERE id=?", (oid,)).fetchone()
            return dict(r) if r else None

    def list_operators(self) -> list[dict]:
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT id,email,name,role,is_active,created_at FROM operators ORDER BY id")]

    def set_operator_active(self, oid: int, active: int):
        with self._lock, self._conn() as c:
            c.execute("UPDATE operators SET is_active=? WHERE id=?", (int(active), oid))

    def record_login(self, operator_id: int, email: str, ip: str, user_agent: str):
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO login_history(operator_id,email,ip,user_agent,created_at)"
                " VALUES(?,?,?,?,?)",
                (operator_id, email, ip or "", (user_agent or "")[:200], self.now()))

    def get_login_history(self, limit: int = 200) -> list[dict]:
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM login_history ORDER BY id DESC LIMIT ?", (limit,))]

    # ---------- id lookups (multi-tenancy checks ke liye) ----------
    def get_post(self, pid: int) -> dict | None:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM posts WHERE id=?", (pid,)).fetchone()
            return dict(r) if r else None

    def get_keyword(self, kid: int) -> dict | None:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM keywords WHERE id=?", (kid,)).fetchone()
            return dict(r) if r else None

    def get_competitor(self, cid: int) -> dict | None:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM competitors WHERE id=?", (cid,)).fetchone()
            return dict(r) if r else None

    def get_activity(self, aid: int) -> dict | None:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM activities WHERE id=?", (aid,)).fetchone()
            return dict(r) if r else None

    def get_review(self, review_name: str) -> dict | None:
        with self._lock, self._conn() as c:
            r = c.execute("SELECT * FROM reviews WHERE review_name=?", (review_name,)).fetchone()
            return dict(r) if r else None

    # ---------- dashboard helpers ----------
    def pending_approvals(self, slug: str | None = None) -> dict:
        with self._lock, self._conn() as c:
            def count(q, args=()):
                return c.execute(q, args).fetchone()[0]
            filt = " AND client_slug=?" if slug else ""
            args = (slug,) if slug else ()
            return {
                "posts": count(
                    f"SELECT COUNT(*) FROM posts WHERE status='draft' AND requires_approval=1{filt}", args),
                "replies": count(
                    f"SELECT COUNT(*) FROM reviews WHERE reply_status='draft'{filt}", args),
                "media": count(
                    f"SELECT COUNT(*) FROM media WHERE status='planned'{filt}", args),
                "qa": count(
                    f"SELECT COUNT(*) FROM activities WHERE status='Ready for QA'{filt}", args),
            }
