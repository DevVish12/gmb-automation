"""Reports compiler (PDF Section 9).

compile_report -> markdown + HTML file.
RULE: sirf real data — API ya manual entry. Missing values '— (no data)'.
Har number ke saath source label (API / manual).
"""
import html
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def _v(value, source=""):
    if value in (None, "", []):
        return "— (no data)"
    return f"{value}" + (f" <span class='src'>[{source}]</span>" if source else "")


def compile_report(client: dict, period_start: str, period_end: str,
                   perf: dict, activity: dict, seo: dict,
                   next_plan: dict, sources: dict) -> tuple[str, str]:
    """Returns (markdown, html). perf/activity/seo/next_plan me sirf real numbers."""
    bname = client.get("business_name") or client.get("name", "")
    md = []
    md.append(f"# GMB Performance Report — {bname}")
    md.append(f"**Period:** {period_start} to {period_end}")
    md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md.append("")
    md.append("## 1. Profile Performance")
    for label, key in [("Profile views (impressions)", "impressions"),
                       ("Search views", "search_views"), ("Maps views", "maps_views"),
                       ("Website clicks", "website_clicks"), ("Calls", "calls"),
                       ("Direction requests", "directions")]:
        md.append(f"- {label}: {perf.get(key, '— (no data)')} {src(sources, key)}")
    md.append("")
    md.append("## 2. GMB Activity (is period me)")
    for label, key in [("Posts published", "posts_published"),
                       ("Graphics created", "graphics_created"),
                       ("Images uploaded", "images_uploaded"),
                       ("Videos uploaded", "videos_uploaded"),
                       ("Services added/optimized", "services_updated"),
                       ("Categories optimized", "categories_updated"),
                       ("Reviews received", "reviews_received"),
                       ("Reviews responded", "reviews_replied")]:
        md.append(f"- {label}: {activity.get(key, '— (no data)')} {src(sources, key)}")
    md.append("")
    md.append("## 3. SEO Activity")
    md.append(f"- Keywords targeted: {seo.get('keywords_targeted', '— (no data)')} {src(sources, 'keywords_targeted')}")
    md.append(f"- New keyword opportunities: {seo.get('new_opportunities', '— (no data)')}")
    md.append(f"- Competitor observations: {seo.get('competitor_notes', '— (no data)')}")
    md.append("")
    md.append("## 4. Key Changes")
    for line in next_plan.get("changes", []) or ["— (no data)"]:
        md.append(f"- {line}")
    md.append("")
    md.append("## 5. Next Period Plan")
    for label, key in [("Keywords to target", "keywords"), ("Services to promote", "services"),
                       ("Content topics", "topics"), ("Offers/promotions", "offers"),
                       ("Visual content needed", "visuals"), ("Profile optimization tasks", "optimizations")]:
        md.append(f"- {label}: {(next_plan.get(key) or ['— (no data)']) if isinstance(next_plan.get(key), list) else next_plan.get(key, '— (no data)')}")
    markdown = "\n".join(md)

    body = html.escape(markdown).replace("\n", "<br>")
    # thodi basic formatting: headings
    html_doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>GMB Report — {html.escape(bname)}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:800px;margin:0 auto;padding:24px}}
.src{{color:#888;font-size:11px}}h1{{font-size:20px}}</style></head>
<body><pre style="white-space:pre-wrap;font-family:inherit">{body}</pre></body></html>"""

    fname = f"report_{client.get('slug','client')}_{period_start}_{period_end}.html".replace("/", "-")
    path = REPORTS_DIR / fname
    path.write_text(html_doc, encoding="utf-8")
    return markdown, str(path)


def src(sources: dict, key: str) -> str:
    s = (sources or {}).get(key, "")
    return f"[{s}]" if s else ""
