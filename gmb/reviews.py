"""Review management (PDF Section 2.5).

- poll_new_reviews: API se naye reviews lao, DB me save karo
- draft_reply: personalized reply draft — kabhi identical repeat nahi
- 1-2 star reviews hamesha needs_human=True (approval mandatory)
"""
import hashlib
import re
from datetime import datetime

# Star-wise template rotation — {name}, {business}, {service_hint} placeholders
_TEMPLATES = {
    5: [
        "Thank you so much, {name}! {service_hint}We're glad you had a great experience at {business}.",
        "{name}, thanks for the wonderful review! {service_hint}Looking forward to serving you again at {business}.",
        "We really appreciate your kind words, {name}! {service_hint}— Team {business}",
        "{name}, thank you for choosing {business}! {service_hint}Your feedback means a lot to us.",
    ],
    4: [
        "Thank you, {name}! {service_hint}We're happy you had a good experience at {business} — we'll keep improving.",
        "{name}, thanks for your review! {service_hint}We appreciate your feedback and hope to earn that 5th star next time at {business}.",
        "Thanks {name}! {service_hint}Glad {business} could help — see you again soon.",
    ],
    3: [
        "Thank you for your honest feedback, {name}. {service_hint}We'd love to understand how we can do better at {business} — please reach out to us directly.",
        "{name}, thanks for reviewing {business}. {service_hint}Your experience matters to us; we've noted your feedback and will work on it.",
    ],
    2: [
        "We're sorry your experience wasn't up to the mark, {name}. {service_hint}Please contact us directly so we can make this right — Team {business}.",
    ],
    1: [
        "We're truly sorry to hear this, {name}. {service_hint}This is not the experience we want at {business}. "
        "Please reach out to us directly so we can resolve this for you.",
    ],
}


def _service_hint(review_text: str, services: list[str]) -> str:
    """Review text me koi service mention hui ho to usey naturally jodo."""
    text = (review_text or "").lower()
    for s in services or []:
        if s and len(s) > 3 and s.lower() in text:
            return f"Glad our {s} met your expectations. "
    return ""


def draft_reply(review: dict, client: dict, recent_reply_hashes: set[str] | None = None) -> dict:
    """Ek personalized reply draft banao. Kabhi identical reply repeat nahi hoga."""
    stars = _star_num(review.get("starRating", 5))
    if not stars:
        stars = 5
    stars = max(1, min(5, stars))
    name = (review.get("reviewer") or {}).get("displayName") or "there"
    first = name.split()[0]
    business = client.get("business_name") or client.get("name", "")
    hint = _service_hint(review.get("comment", ""), client.get("services") or [])

    variants = _TEMPLATES.get(stars, _TEMPLATES[5])
    recent = recent_reply_hashes or set()
    chosen = None
    for v in variants:
        text = v.format(name=first, business=business, service_hint=hint)
        h = hashlib.md5(text.encode()).hexdigest()
        if h not in recent:
            chosen = (text, h)
            break
    if chosen is None:  # sab variants use ho chuke — pehle wale ko tweak karke lo
        text = variants[0].format(name=first, business=business, service_hint=hint)
        text += " We value every customer's feedback."
        h = hashlib.md5((text + str(datetime.now())).encode()).hexdigest()
        chosen = (text, h)

    needs_human = stars <= 2
    return {
        "reply_text": chosen[0],
        "reply_hash": chosen[1],
        "stars": stars,
        "needs_human": needs_human,
        "reason": "Low rating — human review required" if needs_human else "",
    }


def poll_new_reviews(api_client, parent: str, known_names: set[str]) -> list[dict]:
    """API se reviews lao, sirf naye return karo."""
    reviews = api_client.list_reviews(parent) or []
    return [r for r in reviews if r.get("name") not in known_names]


def review_record(client_slug: str, r: dict) -> dict:
    reviewer = r.get("reviewer") or {}
    return {
        "review_name": r.get("name"),
        "client_slug": client_slug,
        "reviewer": reviewer.get("displayName", ""),
        "stars": _star_num(r.get("starRating")),
        "text": r.get("comment", ""),
        "create_time": r.get("createTime", ""),
        "update_time": r.get("updateTime", ""),
        "has_reply": bool(r.get("reviewReply")),
    }


def _star_num(s) -> int:
    m = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
    if isinstance(s, str):
        return m.get(s.upper(), 0)
    try:
        return int(s)
    except Exception:
        return 0
