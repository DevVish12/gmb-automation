"""Demo data seeding — shared by seed_demo.py (CLI) and POST /api/demo/seed.

Creates one realistic demo client ("Sharma Dental Clinic", Pune) with keywords,
audit, content calendar, queue drafts, reviews, media, competitors and tracker
history. Everything is local DB data only — nothing touches Google.
All data is clearly dummy, for testing/demo only.
"""

import json
from datetime import date, timedelta

from gmb import audit as audit_mod
from gmb import content as content_mod

SLUG = "sharma-dental-clinic"


def reset_demo_data(tracker):
    """Delete the demo client and all its local data (uses the cascade delete)."""
    tracker.delete_client(SLUG)


def seed_demo_data(tracker, posting_cfg) -> dict:
    """Create the demo client + all demo data. Returns a summary dict.

    Raises ValueError if the demo client already exists.
    """
    if tracker.get_client(SLUG):
        raise ValueError("Demo client already exists — use reset first to recreate it.")

    today = date.today()

    # ---------- 1. client ----------
    services = ["Root Canal Treatment", "Teeth Cleaning & Polishing",
                "Dental Braces & Aligners", "Dental Implants",
                "Kids Dentistry", "Teeth Whitening", "Tooth Extraction"]
    tracker.add_client({
        "name": "Sharma Dental Clinic",
        "business_name": "Sharma Dental Clinic",
        "category": "Dental clinic",
        "city": "Pune",
        "phone": "+91 98220 12345",
        "website": "https://sharmadentalclinic.example.com",
        "services": services,
    })

    # ---------- 2. audit (manual mode, realistic imperfect profile) ----------
    profile = {
        "name": "Sharma Dental Clinic",
        "description": "Dental clinic in Kothrud, Pune offering root canal, braces and implants.",
        "primary_category": "Dental clinic",
        "secondary_categories": ["Dental implants provider"],
        "phone": "+91 98220 12345",
        "website": "https://sharmadentalclinic.example.com",
        "city": "Kothrud, Pune",
        "services": ["Root Canal Treatment", "Teeth Cleaning", "Braces"],
        "photos_count": 6,
        "videos_count": 0,
        "posts_last_30d": 1,
        "review_count": 47,
        "rating": 4.4,
        "unanswered_reviews": 5,
        "hours_set": True,
        "nap_name": True,
        "nap_address": False,
        "nap_phone": True,
        "source": "manual (demo)",
    }
    result = audit_mod.run_audit(profile)
    tracker.kv_set(f"audit:{SLUG}", json.dumps(result))

    # ---------- 3. keywords ----------
    keywords = [
        ("dentist in kothrud pune", "primary", "Primary category"),
        ("dental clinic kothrud", "secondary", "Secondary categories"),
        ("root canal treatment pune", "service", "Services section"),
        ("teeth cleaning kothrud", "service", "Services section"),
        ("braces dentist pune", "service", "Services section"),
        ("dental implants pune", "service", "Posts"),
        ("kids dentist kothrud", "service", "Services section"),
        ("tooth pain clinic near me", "intent", "Posts"),
        ("teeth whitening pune", "service", "Posts"),
        ("best dentist in pune", "commercial", "Posts"),
    ]
    for kw, ktype, mapped in keywords:
        tracker.add_keyword(SLUG, kw, ktype, mapped)

    # ---------- 4. calendar ----------
    posting_cfg = posting_cfg or {}
    mix = posting_cfg.get("content_mix") or {}
    post_days = posting_cfg.get("post_days") or ["tuesday", "thursday"]
    client = tracker.get_client(SLUG)
    client["services"] = services
    slots = content_mod.generate_calendar(
        client, today.year, today.month,
        [{"keyword": k} for k, _, _ in keywords], mix, post_days)
    tracker.kv_set(f"caldraft:{SLUG}",
                   json.dumps({"year": today.year, "month": today.month, "slots": slots}))

    # ---------- 5. queue drafts ----------
    drafts = [
        {"post_type": "service", "topic": "Painless Root Canal Treatment",
         "keyword": "root canal treatment pune",
         "summary": "Tooth pain keeping you up at night? Our single-visit rotary root canal treatment is virtually painless. Most patients return to work the same day. Book a consultation at Sharma Dental Clinic, Kothrud.",
         "topic_type": "STANDARD", "cta_type": "CALL", "status": "draft"},
        {"post_type": "educational", "topic": "5 Signs You Need a Dental Checkup",
         "keyword": "dentist in kothrud pune",
         "summary": "Bleeding gums, sensitivity to hot/cold, persistent bad breath, jaw pain, or a chipped tooth — these are your teeth asking for help. Early checkups save money and pain. Visit us in Kothrud, Pune.",
         "topic_type": "STANDARD", "cta_type": "LEARN_MORE", "status": "approved"},
        {"post_type": "offer", "topic": "Festive Offer: Flat 20% Off on Teeth Cleaning",
         "keyword": "teeth cleaning kothrud",
         "summary": "This month only — flat 20% off on professional teeth cleaning & polishing at Sharma Dental Clinic, Kothrud. Limited slots per day. Call to book your session.",
         "topic_type": "OFFER", "cta_type": "CALL", "status": "scheduled",
         "scheduled_date": (today + timedelta(days=3)).isoformat(), "requires_approval": 1},
        {"post_type": "faq", "topic": "Does Teeth Whitening Damage Enamel?",
         "keyword": "teeth whitening pune",
         "summary": "Short answer: no — when done professionally. Our enamel-safe whitening brightens your smile by 3-4 shades in a single sitting. Ask us if whitening suits your teeth.",
         "topic_type": "STANDARD", "cta_type": "LEARN_MORE", "status": "draft"},
        {"post_type": "trust", "topic": "Why Families in Kothrud Trust Our Clinic",
         "keyword": "best dentist in pune",
         "summary": "Sterilized equipment for every patient, transparent pricing shared before treatment, and dentists who explain everything in simple words. That's how we've cared for Kothrud's smiles for 12 years.",
         "topic_type": "STANDARD", "cta_type": "CALL", "status": "approved"},
    ]
    for d in drafts:
        d["client_slug"] = SLUG
        tracker.queue_post(d)

    # ---------- 6. reviews ----------
    reviews = [
        {"reviewer": "Priya Deshmukh", "stars": 5,
         "text": "Completely painless root canal! Dr. Sharma explained everything before starting. Highly recommended clinic in Kothrud.",
         "has_reply": 1, "reply_text": "Thank you so much, Priya! Glad your root canal was comfortable. See you at your 6-month checkup. — Team Sharma Dental",
         "reply_status": "sent", "needs_human": 0},
        {"reviewer": "Rahul Patil", "stars": 5,
         "text": "Got my teeth cleaning done here. Very professional, hygienic setup. Fair pricing too.",
         "has_reply": 0, "needs_human": 0},
        {"reviewer": "Sneha Kulkarni", "stars": 4,
         "text": "Good experience overall for my daughter's braces consultation. Waiting time was a bit long though.",
         "has_reply": 1, "reply_text": "Thanks Sneha! Noted on the waiting time — we've added evening slots for consultations now. — Team Sharma Dental",
         "reply_status": "sent", "needs_human": 0},
        {"reviewer": "Amit Joshi", "stars": 2,
         "text": "Had to wait 45 minutes past my appointment time. Treatment was fine but the delay was frustrating.",
         "has_reply": 0, "needs_human": 1},
        {"reviewer": "Kavita Rao", "stars": 5,
         "text": "Best dental clinic in the area. My implants were done perfectly, zero complications after 6 months.",
         "has_reply": 0, "needs_human": 0},
        {"reviewer": "Vikram Singh", "stars": 3,
         "text": "Decent clinic. Cleaning was good but I found the charges slightly on the higher side.",
         "has_reply": 0, "needs_human": 0},
    ]
    for i, r in enumerate(reviews):
        tracker.save_review({
            "review_name": f"demo_review_{i}", "client_slug": SLUG,
            "reviewer": r["reviewer"], "stars": r["stars"], "text": r["text"],
            "create_time": (today - timedelta(days=len(reviews) - i)).isoformat(),
            "update_time": (today - timedelta(days=len(reviews) - i)).isoformat(),
            "has_reply": r["has_reply"], "reply_text": r.get("reply_text", ""),
            "reply_status": r.get("reply_status", "none"),
            "needs_human": r["needs_human"], "fetched_at": today.isoformat(),
        })

    # ---------- 7. media ----------
    media = [
        {"kind": "photo", "note": "Clinic exterior — morning light", "caption": "Visit us in Kothrud, Pune",
         "status": "planned", "scheduled_date": (today + timedelta(days=2)).isoformat()},
        {"kind": "photo", "note": "Sterilized treatment room", "caption": "Hygiene first, always",
         "status": "planned", "scheduled_date": (today + timedelta(days=5)).isoformat()},
        {"kind": "photo", "note": "Doctor with young patient", "caption": "Gentle dentistry for kids",
         "status": "planned", "scheduled_date": (today + timedelta(days=9)).isoformat()},
        {"kind": "video", "note": "30-sec clinic tour reel", "caption": "Take a quick tour of our clinic",
         "status": "planned", "scheduled_date": (today + timedelta(days=12)).isoformat()},
    ]
    for m in media:
        m["client_slug"] = SLUG
        tracker.add_media(m)

    # ---------- 8. competitors ----------
    competitors = [
        {"name": "SmileCare Dental Studio", "rating": "4.6", "review_count": "212",
         "categories": "Dental clinic, Orthodontist", "posting_freq": "2 posts/week",
         "notes": "Strong on Instagram-style before/after posts. Replies to every review within a day.",
         "source": "manual"},
        {"name": "Perfect Teeth Clinic", "rating": "4.3", "review_count": "158",
         "categories": "Dental clinic", "posting_freq": "1 post/week",
         "notes": "Runs monthly discount offers. Weak review reply rate.",
         "source": "manual"},
        {"name": "BriteSmile Dental", "rating": "4.8", "review_count": "301",
         "categories": "Dental clinic, Cosmetic dentist", "posting_freq": "3 posts/week",
         "notes": "Highest rating in area. Heavy on whitening/implant content. Benchmark to beat.",
         "source": "manual"},
    ]
    for c in competitors:
        c["client_slug"] = SLUG
        tracker.add_competitor(c)

    # ---------- 9. tracker activities ----------
    activities = [
        ("Profile audit completed", "Audit", "Verified"),
        ("Primary keyword mapped to category", "SEO", "Approved"),
        ("Week 1 posts drafted", "Posts", "Ready for QA"),
        ("Offer post approved by client", "Posts", "Approved"),
        ("Festive offer scheduled", "Posts", "Scheduled"),
        ("5 unanswered reviews flagged", "Reviews", "In Progress"),
        ("Clinic photoshoot planned", "Media", "Pending"),
    ]
    for act, area, status in activities:
        tracker.log_activity(SLUG, act, area=area, status=status)

    return {
        "slug": SLUG,
        "name": "Sharma Dental Clinic",
        "audit_score": result.get("score"),
        "keywords": len(keywords),
        "calendar_slots": len(slots),
        "queue_drafts": len(drafts),
        "reviews": len(reviews),
        "media": len(media),
        "competitors": len(competitors),
        "activities": len(activities),
    }
