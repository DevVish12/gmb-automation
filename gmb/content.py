"""Content calendar + post drafts (PDF Sections 4, 5, 6).

Template/rule-based hai — koi API key nahi chahiye.
OPENAI_API_KEY env var set ho aur config me openai.enabled=true ho to
drafts ko enhance kiya jata hai (optional).

RULE: prices/offers kabhi invent nahi honge. Offer posts me placeholder
rehenga aur requires_approval=True rahega.
"""
import calendar
import os
import random
from datetime import date

import requests

POST_TYPES = [
    "service-focused", "educational", "location-keyword", "faq",
    "trust-benefit", "offer", "seasonal", "product", "event",
    "problem-solution",
]

# topicType mapping (GBP API)
TOPIC_TYPE = {
    "service-focused": "STANDARD",
    "educational": "STANDARD",
    "location-keyword": "STANDARD",
    "faq": "STANDARD",
    "trust-benefit": "STANDARD",
    "offer": "OFFER",
    "seasonal": "STANDARD",
    "product": "STANDARD",
    "event": "EVENT",
    "problem-solution": "STANDARD",
}

WEEKDAY = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_TEMPLATES = {
    "service-focused": [
        "{service} — {business} me expert care ke saath. {city} me {service} ke liye aaj hi sampark karein.",
        "Kya aapko {service} ki zarurat hai? {business} ({city}) me professional {service} — quality aur bharose ke saath.",
    ],
    "educational": [
        "{service} ke baare me aksar poochha jaane wala sawal: ye kab zaruri hota hai? {business} batata hai — "
        "agar aap {city} me hain to sahi samay par sahi guidance lena sabse important hai.",
        "{service} lene se pehle kin baaton ka dhyan rakhein? {business} ki quick guide — "
        "sahi provider chunein, transparent process mangein.",
    ],
    "location-keyword": [
        "{city} me best {service}? {business} — local experts, genuine reviews, transparent process.",
        "{service} in {city} — {business} par bharosa karein. Aaj hi visit ya call karke appointment lein.",
    ],
    "faq": [
        "FAQ: '{service} me kitna samay lagta hai?' — {business} ka jawab: har case alag hota hai, "
        "pehli consultation me hum aapko clear timeline dete hain. {city} me poochhein — hum jawab denge.",
        "FAQ: 'Kya {service} ke liye appointment zaruri hai?' — {business} ({city}) me walk-in aur appointment "
        "dono options hain. Call karke slot confirm kar lein.",
    ],
    "trust-benefit": [
        "{business} ko {city} ke customers kyon pasand karte hain? Transparent process, experienced team, "
        "aur har step par clear communication — {service} me bharosa hi sab kuch hai.",
        "Certified process. Genuine reviews. Local presence. {business} — {city} me {service} ka bharosemand naam.",
    ],
    "offer": [
        "[OFFER DETAILS PENDING — client se confirm karke likhein] {business} ({city}) me {service} par special offer! "
        "Limited time — details ke liye call karein.",
    ],
    "seasonal": [
        "Is season me {service} ki demand badh jaati hai — {business} ({city}) me pehle se plan karein aur "
        "bheed se bachein. Aaj hi sampark karein.",
    ],
    "product": [
        "Naya {service} package ab {business} ({city}) me uplabdh — details ke liye profile par visit karein ya call karein.",
    ],
    "event": [
        "[EVENT DETAILS PENDING] {business} ({city}) me upcoming event — {service} se judi jaankari. "
        "Date/time confirm hote hi update karenge.",
    ],
    "problem-solution": [
        "{service} me aksar ye problem hoti hai: sahi provider chunna mushkil lagta hai. "
        "{business} ({city}) ka solution — clear process, transparent pricing aur experienced team.",
        "Kya {service} ko lekar confused hain? {business} pehle aapki problem samajhta hai, "
        "phir step-by-step solution deta hai — {city} me aaj hi baat karein.",
    ],
}

_CTA = {
    "service-focused": ("LEARN_MORE", "website"),
    "educational": ("LEARN_MORE", "website"),
    "location-keyword": ("CALL", "phone"),
    "faq": ("CALL", "phone"),
    "trust-benefit": ("LEARN_MORE", "website"),
    "offer": ("LEARN_MORE", "website"),
    "seasonal": ("CALL", "phone"),
    "product": ("LEARN_MORE", "website"),
    "event": ("SIGN_UP", "website"),
    "problem-solution": ("LEARN_MORE", "website"),
}


def generate_calendar(client: dict, year: int, month: int,
                      keywords: list[dict], mix: dict, post_days: list[str]) -> list[dict]:
    """Mahine ka content calendar banao (PDF Section 6).

    Har hafte mix[weekN] ke 2 post types, post_days (e.g. Tue/Thu) par.
    Services aur keywords rotate hote hain — repeat nahi.
    """
    services = client.get("services") or ["our services"]
    kws = [k["keyword"] for k in keywords] or [client.get("primary_keyword") or client.get("category") or "services"]
    business = client.get("business_name") or client.get("name", "Our Business")
    city = client.get("city") or "your city"

    day_nums = sorted(WEEKDAY[d.lower()] for d in post_days)
    cal = calendar.monthcalendar(year, month)
    slots = []
    svc_i = kw_i = 0
    for week_no in range(1, 6):
        week_types = mix.get(f"week{week_no}") or mix.get("week1")
        if not week_types:
            continue
        week_dates = [d for d in cal[week_no - 1] if d != 0]
        chosen = [d for wd in day_nums for d in week_dates
                  if date(year, month, d).weekday() == wd]
        for i, day in enumerate(chosen[: len(week_types)]):
            ptype = week_types[i % len(week_types)]
            service = services[svc_i % len(services)]; svc_i += 1
            kw = kws[kw_i % len(kws)]; kw_i += 1
            headline = _TEMPLATES[ptype][random.randrange(len(_TEMPLATES[ptype]))].format(
                business=business, service=service, city=city)
            slots.append({
                "date": date(year, month, day).isoformat(),
                "post_type": ptype,
                "topic": f"{service} — {ptype}",
                "keyword": kw,
                "service": service,
                "headline": headline,
                "requires_approval": ptype in ("offer", "event"),
            })
    return slots


def draft_post(client: dict, slot: dict, cta_url_override: str = "") -> dict:
    """Calendar slot se GBP post draft banao."""
    ptype = slot["post_type"]
    cta_type, cta_target = _CTA.get(ptype, ("LEARN_MORE", "website"))
    business = client.get("business_name") or client.get("name", "")
    city = client.get("city") or ""
    service = slot.get("service", "")

    body = slot.get("headline", "")
    # thoda structure: headline + service context + CTA line
    summary = body
    if ptype not in ("offer", "event"):
        summary += f"\n\n{business} — {city} me {service} ke liye trusted choice."

    url = cta_url_override or (client.get("website") if cta_target == "website" else "")
    if cta_type == "CALL":
        url = ""  # CALL par URL nahi lagta
    call_to_action = {"actionType": cta_type}
    if url:
        call_to_action["url"] = url

    post = {
        "languageCode": "en",
        "summary": summary.strip(),
        "topicType": TOPIC_TYPE.get(ptype, "STANDARD"),
        "callToAction": call_to_action,
    }
    draft = {
        "scheduled_date": slot.get("date"),
        "post_type": ptype,
        "topic": slot.get("topic"),
        "keyword": slot.get("keyword"),
        "summary": post["summary"],
        "topic_type": post["topicType"],
        "cta_type": cta_type,
        "cta_url": url,
        "requires_approval": bool(slot.get("requires_approval")),
        "api_payload": post,
    }
    if _openai_enabled():
        draft["summary"] = enhance_with_openai(draft["summary"])
        draft["api_payload"]["summary"] = draft["summary"]
    return draft


def _openai_enabled() -> bool:
    try:
        import yaml  # lazy
        return bool(os.environ.get("OPENAI_API_KEY"))
    except Exception:
        return False


def enhance_with_openai(text: str) -> str:
    """Optional: draft ko OpenAI se polish karo. Key nahi to text as-is."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return text
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system",
                     "content": "You polish Google Business Profile posts. Keep it short (under 300 chars), "
                                "natural, no keyword stuffing, no invented prices/offers/stats. "
                                "Return only the polished post text."},
                    {"role": "user", "content": text},
                ],
                "max_tokens": 200,
            },
            timeout=30,
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return text
