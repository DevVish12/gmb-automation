"""AI-based GMB audit (PDF Section 1).

run_audit(profile: dict) -> findings list, har finding:
  {area, current_status, issue, action, priority}
Priority: High / Medium / Low. Pure function — API ke bina bhi chalti hai.

profile dict ke expected keys (API ya manual entry se):
  name, description, primary_category, secondary_categories (list),
  services (list), phone, website, hours_set (bool), photos_count,
  videos_count, posts_last_30d (int), review_count, rating (float),
  unanswered_reviews (int), city, nap_name, nap_address, nap_phone
"""
from datetime import datetime

PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def _f(area, current_status, issue, action, priority):
    return {
        "area": area,
        "current_status": current_status,
        "issue": issue,
        "action": action,
        "priority": priority,
    }


def run_audit(p: dict) -> dict:
    p = p or {}
    findings = []

    def val(k, default="—"):
        v = p.get(k, default)
        return default if v in (None, "") else v

    # 1. Business name
    if not p.get("name"):
        findings.append(_f("Profile Completeness", "Business name missing",
                           "Profile ka naam set nahi hai — search me dikhega hi nahi.",
                           "Google Business Profile me sahi business name add karo.", "High"))

    # 2. Description
    desc = (p.get("description") or "").strip()
    if not desc:
        findings.append(_f("Business Description", "Description missing",
                           "Description khaali hai — keywords aur trust signals ka loss.",
                           "150-750 characters ki customer-focused description likho: kya karte ho, "
                           "kiske liye, kaunsa area, differentiators.", "High"))
    elif len(desc) < 120:
        findings.append(_f("Business Description", f"Bahut chhoti ({len(desc)} chars)",
                           "Description me services/keywords/location cover nahi hue.",
                           "Description ko 200+ characters tak badhao, keywords naturally daalo.", "Medium"))

    # 3. Primary category
    if not p.get("primary_category"):
        findings.append(_f("Categories", "Primary category missing",
                           "Primary category ranking ka sabse bada factor hai.",
                           "Core business ko represent karne wali sabse relevant primary category select karo.", "High"))

    # 4. Secondary categories
    secs = p.get("secondary_categories") or []
    if len(secs) < 2:
        findings.append(_f("Categories", f"Sirf {len(secs)} secondary categories",
                           "Genuine services ke liye secondary categories missing.",
                           "Offer ki hui har genuine service ke liye relevant secondary categories add karo "
                           "(keyword ke liye irrelevant category kabhi mat daalo).", "Medium"))

    # 5. Services
    services = p.get("services") or []
    if not services:
        findings.append(_f("Services", "Services section khaali",
                           "Services section se service+location keywords ka mauka miss ho raha hai.",
                           "Saari genuine services add karo, har ek par useful description + natural keywords.", "High"))
    elif len(services) < 5:
        findings.append(_f("Services", f"Sirf {len(services)} services listed",
                           "Competitors zyada services list kar rahe honge.",
                           "Missing genuine services identify karke add karo.", "Medium"))

    # 6. Phone / website
    if not p.get("phone"):
        findings.append(_f("Contact Info", "Phone number missing",
                           "Call button kaam nahi karega — direct lead loss.",
                           "Verified business phone number add karo.", "High"))
    if not p.get("website"):
        findings.append(_f("Contact Info", "Website link missing",
                           "Website clicks track nahi honge, credibility kam.",
                           "Business website ka sahi URL add karo.", "Medium"))

    # 7. Hours
    if not p.get("hours_set"):
        findings.append(_f("Profile Completeness", "Business hours set nahi",
                           "'Hours may differ' jaisa dikhega — customers hesitate karenge.",
                           "Regular hours + special/holiday hours set karo.", "Medium"))

    # 8. Photos / videos
    photos = int(p.get("photos_count") or 0)
    if photos < 10:
        findings.append(_f("Photos & Videos", f"Sirf {photos} photos",
                           "Kam photos = kam trust, kam engagement.",
                           f"Exterior, interior, team, work/process ki {max(10 - photos, 0)}+ real photos upload karo. "
                           "Stock/irrelevant photos avoid karo.", "Medium"))
    if int(p.get("videos_count") or 0) == 0:
        findings.append(_f("Photos & Videos", "Koi video nahi",
                           "Short videos profile ko active aur authentic dikhate hain.",
                           "30-60 sec ki service/process video upload karo.", "Low"))

    # 9. Posts recency
    posts = int(p.get("posts_last_30d") or 0)
    if posts == 0:
        findings.append(_f("Posts", "Pichhle 30 din me 0 posts",
                           "Profile inactive lag raha hai Google ko.",
                           "Content calendar ke hisaab se hafte me 2 posts shuru karo.", "Medium"))

    # 10. Reviews
    rc = int(p.get("review_count") or 0)
    rating = float(p.get("rating") or 0)
    if rc < 10:
        findings.append(_f("Reviews", f"Sirf {rc} reviews",
                           "Kam reviews = kam social proof, kam local ranking.",
                           "Har happy customer se review request ka process banao.", "High"))
    if rating and rating < 4.0:
        findings.append(_f("Reviews", f"Rating {rating} (< 4.0)",
                           "Low rating click-through aur ranking dono girata hai.",
                           "Negative reviews ka pattern nikalo, service issue fix karo, phir naye reviews lao.", "High"))
    unans = int(p.get("unanswered_reviews") or 0)
    if unans > 0:
        findings.append(_f("Reviews", f"{unans} reviews ka jawab nahi diya",
                           "Unanswered reviews customer experience kharab dikhate hain.",
                           "Saare pending reviews ka personalized jawab do (Reviews page se).", "Medium"))

    # 11. NAP consistency
    nap_bits = [p.get("nap_name"), p.get("nap_address"), p.get("nap_phone")]
    if any(not b for b in nap_bits):
        findings.append(_f("NAP Consistency", "Website/profile NAP verify nahi hua",
                           "Name/Address/Phone website se match nahi kar raha ho sakta hai.",
                           "Website, profile aur directories par NAP bilkul identical rakho.", "Medium"))

    # 12. Location relevance
    if not p.get("city"):
        findings.append(_f("Local Relevance", "Service city/area define nahi",
                           "Location keywords map nahi ho payenge.",
                           "Service areas clearly define karo.", "Low"))

    findings.sort(key=lambda f: PRIORITY_ORDER[f["priority"]])
    score = _score(findings)
    return {
        "score": score,
        "grade": _grade(score),
        "total": len(findings),
        "high": sum(1 for f in findings if f["priority"] == "High"),
        "medium": sum(1 for f in findings if f["priority"] == "Medium"),
        "low": sum(1 for f in findings if f["priority"] == "Low"),
        "findings": findings,
        "audited_at": datetime.now().isoformat(timespec="seconds"),
    }


def _score(findings) -> int:
    s = 100
    for f in findings:
        s -= {"High": 12, "Medium": 6, "Low": 3}[f["priority"]]
    return max(0, s)


def _grade(score: int) -> str:
    if score >= 85:
        return "A — Strong"
    if score >= 70:
        return "B — Good"
    if score >= 50:
        return "C — Needs work"
    return "D — Critical gaps"


def profile_from_api_location(loc: dict) -> dict:
    """Business Information API ke location dict ko audit profile dict me badlo."""
    cats = (loc.get("categories") or {})
    services = loc.get("serviceItems") or []
    profile = loc.get("profile") or {}
    phones = loc.get("phoneNumbers") or {}
    return {
        "name": loc.get("title"),
        "description": profile.get("description"),
        "primary_category": (cats.get("primaryCategory") or {}).get("displayName"),
        "secondary_categories": [
            c.get("displayName") for c in (cats.get("additionalCategories") or [])
        ],
        "services": [s.get("displayName") for s in services if isinstance(s, dict)],
        "phone": (phones.get("primaryPhone") if isinstance(phones, dict) else None),
        "website": (loc.get("websiteUri") or None),
        "hours_set": bool(loc.get("regularHours")),
        "city": ((loc.get("address") or {}).get("locality")),
    }
