"""DataForSEO hook (optional).

Competitor GBP profiles ka koi official API nahi hai — isliye DataForSEO
(third-party SERP data) ka hook diya hai:
  - Google Maps business search (competitor snapshot: rating, reviews, categories)
  - Keyword suggestions + search volume (keyword research)

Key config me mat likho — env vars: DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD.
Key nahi hai to saare methods clear error dete hain; UI manual-entry mode me chalta hai.
"""
import os

import requests


class DataForSEOError(Exception):
    pass


class DataForSEO:
    BASE = "https://api.dataforseo.com/v3"

    def __init__(self, login: str | None = None, password: str | None = None):
        self.login = login or os.environ.get("DATAFORSEO_LOGIN")
        self.password = password or os.environ.get("DATAFORSEO_PASSWORD")
        if not self.login or not self.password:
            raise DataForSEOError(
                "DataForSEO key set nahi hai. DATAFORSEO_LOGIN aur DATAFORSEO_PASSWORD "
                "env vars set karo, ya manual entry use karo."
            )

    def _post(self, endpoint: str, payload: list[dict]) -> dict:
        try:
            r = requests.post(f"{self.BASE}{endpoint}", auth=(self.login, self.password),
                              json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            raise DataForSEOError(f"DataForSEO request fail: {e}")
        tasks = data.get("tasks") or []
        if not tasks or tasks[0].get("status_code") != 20000:
            msg = (tasks[0].get("status_message") if tasks else data.get("status_message"))
            raise DataForSEOError(f"DataForSEO error: {msg}")
        return tasks[0].get("result") or []

    # ---------- Google Maps: competitor snapshot ----------
    def maps_search(self, keyword: str, location_name: str = "India",
                    language_code: str = "en", depth: int = 20) -> list[dict]:
        """e.g. keyword='dentist', location_name='Noida,Uttar Pradesh,India'"""
        results = self._post("/business_data/google/maps/search/live", [{
            "keyword": keyword, "location_name": location_name,
            "language_code": language_code, "depth": depth,
        }])
        items = (results[0].get("items") if results else []) or []
        out = []
        for it in items:
            out.append({
                "name": it.get("title"),
                "rating": (it.get("rating") or {}).get("value"),
                "review_count": (it.get("rating") or {}).get("votes_count"),
                "categories": ", ".join(it.get("category") or []),
                "address": it.get("address"),
                "phone": it.get("phone"),
                "url": it.get("url"),
            })
        return out

    # ---------- Keyword research ----------
    def keyword_suggestions(self, keyword: str, location_name: str = "India",
                            language_code: str = "en", limit: int = 50) -> list[dict]:
        results = self._post("/dataforseo_labs/google/keyword_suggestions/live", [{
            "keyword": keyword, "location_name": location_name,
            "language_code": language_code, "limit": limit,
            "include_seed_keyword": True,
        }])
        items = (results[0].get("items") if results else []) or []
        return [{
            "keyword": it.get("keyword"),
            "volume": (it.get("keyword_info") or {}).get("search_volume"),
            "competition": (it.get("keyword_info") or {}).get("competition"),
        } for it in items]


def from_config(cfg: dict) -> DataForSEO | None:
    """Config me dataforseo.enabled=true ho to client banao, warna None."""
    if not (cfg.get("dataforseo") or {}).get("enabled"):
        return None
    try:
        return DataForSEO()
    except DataForSEOError:
        return None
