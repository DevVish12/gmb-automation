"""Scheduler — APScheduler jobs (PDF Section 10 pipeline ka repeat hissa).

Jobs:
  - publish_due_posts : scheduled posts jinki date aa gayi -> publish (guarded)
  - check_reviews     : naye reviews poll -> draft replies banao
  - daily_reminder    : pending approvals ka reminder log me

SAFETY (non-negotiable):
  - dry_run=True ho ya client connected na ho -> koi WRITE nahi, sirf log.
  - requires_approval=1 wali post bina 'approved' status ke publish nahi hogi.
  - auto_publish per-client toggle OFF hai by default.
  - Har location par 1 publish/minute se zyada nahi (Google cap: 10 edits/min).
"""
import logging
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger("gmb.scheduler")

_scheduler = None


def _dry_run(cfg) -> bool:
    return bool((cfg.get("safety") or {}).get("dry_run", True))


def _client_api(slug, tracker, cfg):
    """Connected client ke liye GBPClient banao, warna None."""
    from . import auth
    from .api import GBPClient
    client = tracker.get_client(slug)
    if not client or not client.get("location_id"):
        return None, None
    creds = auth.load_credentials(slug)
    if not creds:
        return None, None
    return client, GBPClient(creds, dry_run=_dry_run(cfg))


def _location_parent(client: dict) -> str:
    return f"accounts/{client['account_id']}/locations/{client['location_id']}"


def publish_due_posts(tracker, cfg):
    """Scheduled posts publish karo — saare guards ke saath."""
    dry = _dry_run(cfg)
    due = tracker.get_due_posts()
    if not due:
        return
    last_publish: dict[str, float] = {}
    for p in due:
        slug = p["client_slug"]
        client, api = _client_api(slug, tracker, cfg)
        if not api:
            log.info("[scheduler] skip post %s: client '%s' connected nahi", p["id"], slug)
            continue
        if p.get("requires_approval") and p.get("status") != "approved":
            # status 'scheduled' par hai par approval pending — publish mat karo
            log.info("[scheduler] post %s approval pending — skip", p["id"])
            continue
        if not client.get("auto_publish") and p.get("requires_approval"):
            log.info("[scheduler] post %s: auto_publish OFF — skip", p["id"])
            continue
        # rate limit: 1 publish/min per location
        key = slug
        if time.time() - last_publish.get(key, 0) < 60:
            log.info("[scheduler] post %s: rate limit — agli run me", p["id"])
            continue
        if dry:
            log.warning("[scheduler] DRY-RUN: post %s publish nahi hui (dry_run=true)", p["id"])
            continue
        try:
            payload = {
                "languageCode": "en",
                "summary": p["summary"],
                "topicType": p.get("topic_type") or "STANDARD",
                "callToAction": {"actionType": p.get("cta_type") or "LEARN_MORE"},
            }
            if p.get("cta_url"):
                payload["callToAction"]["url"] = p["cta_url"]
            resp = api.create_local_post(_location_parent(client), payload)
            if resp and not resp.get("dry_run"):
                tracker.update_post(p["id"], status="published",
                                    gmb_post_name=resp.get("name", ""))
                tracker.log_activity(slug, f"Post published: {p.get('topic')}",
                                     area="Posts", status="Published")
                last_publish[key] = time.time()
                log.info("[scheduler] post %s published", p["id"])
        except Exception as e:
            tracker.update_post(p["id"], status="failed")
            tracker.log_activity(slug, f"Post publish FAILED: {p.get('topic')} — {e}",
                                 area="Posts", status="In Progress")
            log.error("[scheduler] post %s fail: %s", p["id"], e)


def check_reviews(tracker, cfg):
    """Har connected client ke naye reviews poll karo + drafts banao."""
    from . import reviews as rev
    for client in tracker.get_clients():
        slug = client["slug"]
        api_client, api = _client_api(slug, tracker, cfg)
        if not api:
            continue
        try:
            known = tracker.known_review_names(slug)
            new = rev.poll_new_reviews(api, _location_parent(client), known)
            for r in new:
                rec = rev.review_record(slug, r)
                draft = rev.draft_reply(r, client, tracker.recent_reply_hashes(slug))
                rec.update({
                    "reply_text": draft["reply_text"],
                    "reply_hash": draft["reply_hash"],
                    "reply_status": "draft",
                    "needs_human": int(draft["needs_human"]),
                })
                tracker.save_review(rec)
                tracker.log_activity(
                    slug, f"Naya review ({draft['stars']}*): reply draft ready",
                    area="Reviews", status="Ready for QA")
            if new:
                log.info("[scheduler] %s: %d naye reviews", slug, len(new))
            tracker.kv_set(f"last_review_check:{slug}", datetime.now().isoformat(timespec="seconds"))
        except Exception as e:
            log.error("[scheduler] review check fail %s: %s", slug, e)


def daily_reminder(tracker, cfg):
    counts = tracker.pending_approvals()
    total = sum(counts.values())
    if total:
        log.warning("[reminder] %d approvals pending: posts=%d replies=%d media=%d qa=%d",
                    total, counts["posts"], counts["replies"], counts["media"], counts["qa"])


def start(tracker, cfg):
    """Scheduler start karo. app.py se ek baar call hota hai."""
    global _scheduler
    if _scheduler:
        return _scheduler
    sched_cfg = cfg.get("scheduler") or {}
    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    _scheduler.add_job(lambda: publish_due_posts(tracker, cfg), "interval",
                       minutes=int(sched_cfg.get("publish_check_minutes", 15)),
                       id="publish_due_posts", max_instances=1)
    _scheduler.add_job(lambda: check_reviews(tracker, cfg), "interval",
                       minutes=int(sched_cfg.get("review_check_minutes", 60)),
                       id="check_reviews", max_instances=1)
    _scheduler.add_job(lambda: daily_reminder(tracker, cfg), "cron",
                       hour=int(sched_cfg.get("reminder_hour", 9)), minute=0,
                       id="daily_reminder")
    _scheduler.start()
    log.info("[scheduler] started (dry_run=%s)", _dry_run(cfg))
    return _scheduler
