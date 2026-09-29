"""GBP API client — saare official endpoints ek jagah.

APIs (sab google-api-python-client discovery se):
  - mybusinessaccountmanagement v1 : accounts list
  - mybusinessbusinessinformation v1 : locations/categories/attributes CRUD
  - mybusiness v4 (legacy)           : media upload, reviews (list+reply), localPosts
  - businessprofileperformance v1    : daily metrics + monthly search keywords

SAFETY: dry_run=True (default) par koi bhi WRITE call Google ko nahi jayegi —
write methods {"dry_run": True, ...} return karke sirf log karenge.
"""
import logging
from datetime import date

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

log = logging.getLogger("gmb.api")

# Location get/list ke liye standard read mask
DEFAULT_READ_MASK = (
    "name,title,storeCode,phoneNumbers,websiteUri,regularHours,specialHours,"
    "categories,profile,serviceItems,attributes,address,latlng,openInfo,labels"
)

# 10 edits/min per-profile cap — isse zyada kabhi mat bhejo
MIN_SECONDS_BETWEEN_WRITES = 60


class ApiNotApproved(Exception):
    """Quota 0 / 403 — Basic API Access abhi approve nahi hua."""


class GBPClient:
    def __init__(self, creds, dry_run: bool = True):
        self.creds = creds
        self.dry_run = dry_run
        self._acct = self._biz = self._perf = self._v4 = None

    # ---------- lazy service builders ----------
    def _svc(self, name, version):
        return build(name, version, credentials=self.creds, cache_discovery=False)

    @property
    def acct(self):
        if self._acct is None:
            self._acct = self._svc("mybusinessaccountmanagement", "v1")
        return self._acct

    @property
    def biz(self):
        if self._biz is None:
            self._biz = self._svc("mybusinessbusinessinformation", "v1")
        return self._biz

    @property
    def perf(self):
        if self._perf is None:
            self._perf = self._svc("businessprofileperformance", "v1")
        return self._perf

    @property
    def v4(self):
        if self._v4 is None:
            self._v4 = self._svc("mybusiness", "v4")
        return self._v4

    # ---------- helpers ----------
    def _guard(self, action: str):
        """Write se pehle safety check. dry_run par sirf log."""
        if self.dry_run:
            log.warning("[DRY-RUN] write blocked: %s", action)
            return {"dry_run": True, "action": action}

    def _check_http_error(self, e: HttpError):
        status = getattr(e.resp, "status", None)
        if status in (401, 403):
            raise ApiNotApproved(
                "Google ne 403/401 diya — ya to OAuth scope/permission issue hai, "
                "ya Basic API Access abhi approve nahi hua (quota 0). README ka Step 2 dekho."
            )
        raise e

    # ================= ACCOUNTS / LOCATIONS (v1) =================
    def list_accounts(self):
        try:
            return self.acct.accounts().list().execute().get("accounts", [])
        except HttpError as e:
            self._check_http_error(e)

    def list_locations(self, account: str, read_mask: str = DEFAULT_READ_MASK):
        """account = 'accounts/123...'"""
        try:
            return (
                self.biz.accounts()
                .locations()
                .list(parent=account, readMask=read_mask, pageSize=100)
                .execute()
                .get("locations", [])
            )
        except HttpError as e:
            self._check_http_error(e)

    def get_location(self, location_name: str, read_mask: str = DEFAULT_READ_MASK):
        """location_name = 'accounts/123/locations/456'"""
        try:
            return (
                self.biz.locations().get(name=location_name, readMask=read_mask).execute()
            )
        except HttpError as e:
            self._check_http_error(e)

    def patch_location(self, location_name: str, body: dict, update_mask: str):
        """HIGH RISK — category/description change re-verification trigger kar sakta hai.
        Hamesha approval ke baad hi call karo."""
        blocked = self._guard(f"patch_location {location_name} mask={update_mask}")
        if blocked:
            return blocked
        try:
            return (
                self.biz.locations()
                .patch(name=location_name, updateMask=update_mask, body=body)
                .execute()
            )
        except HttpError as e:
            self._check_http_error(e)

    # ================= REVIEWS (v4) =================
    def list_reviews(self, parent: str, page_size: int = 50):
        """parent = 'accounts/123/locations/456'"""
        try:
            return (
                self.v4.accounts()
                .locations()
                .reviews()
                .list(parent=parent, pageSize=page_size)
                .execute()
                .get("reviews", [])
            )
        except HttpError as e:
            self._check_http_error(e)

    def reply_review(self, review_name: str, comment: str):
        blocked = self._guard(f"reply_review {review_name}")
        if blocked:
            return blocked
        try:
            return (
                self.v4.accounts()
                .locations()
                .reviews()
                .reply(name=review_name, body={"comment": comment})
                .execute()
            )
        except HttpError as e:
            self._check_http_error(e)

    def delete_review_reply(self, review_name: str):
        blocked = self._guard(f"delete_review_reply {review_name}")
        if blocked:
            return blocked
        try:
            return (
                self.v4.accounts()
                .locations()
                .reviews()
                .deleteReply(name=review_name)
                .execute()
            )
        except HttpError as e:
            self._check_http_error(e)

    # ================= LOCAL POSTS (v4) =================
    def list_local_posts(self, parent: str, page_size: int = 50):
        try:
            return (
                self.v4.accounts()
                .locations()
                .localPosts()
                .list(parent=parent, pageSize=page_size)
                .execute()
                .get("localPosts", [])
            )
        except HttpError as e:
            self._check_http_error(e)

    def create_local_post(self, parent: str, post: dict):
        """post = {languageCode, summary, topicType, callToAction, event?, offer?, media?}"""
        blocked = self._guard(f"create_local_post under {parent}")
        if blocked:
            return blocked
        try:
            return (
                self.v4.accounts()
                .locations()
                .localPosts()
                .create(parent=parent, body=post)
                .execute()
            )
        except HttpError as e:
            self._check_http_error(e)

    def patch_local_post(self, post_name: str, post: dict, update_mask: str):
        blocked = self._guard(f"patch_local_post {post_name}")
        if blocked:
            return blocked
        try:
            return (
                self.v4.accounts()
                .locations()
                .localPosts()
                .patch(name=post_name, updateMask=update_mask, body=post)
                .execute()
            )
        except HttpError as e:
            self._check_http_error(e)

    def delete_local_post(self, post_name: str):
        blocked = self._guard(f"delete_local_post {post_name}")
        if blocked:
            return blocked
        try:
            return (
                self.v4.accounts().locations().localPosts().delete(name=post_name).execute()
            )
        except HttpError as e:
            self._check_http_error(e)

    # ================= MEDIA (v4) =================
    def list_media(self, parent: str, page_size: int = 50):
        try:
            return (
                self.v4.accounts()
                .locations()
                .media()
                .list(parent=parent, pageSize=page_size)
                .execute()
                .get("mediaItems", [])
            )
        except HttpError as e:
            self._check_http_error(e)

    def create_media(self, parent: str, media: dict):
        """media = {mediaFormat: PHOTO|VIDEO, locationAssociation: {category: ...},
        sourceUrl: 'https://...public-url...' } — file pehle publicly host karo."""
        blocked = self._guard(f"create_media under {parent}")
        if blocked:
            return blocked
        try:
            return (
                self.v4.accounts()
                .locations()
                .media()
                .create(parent=parent, body=media)
                .execute()
            )
        except HttpError as e:
            self._check_http_error(e)

    # ================= PERFORMANCE (v1) =================
    def get_daily_metrics(self, location: str, metrics: list[str],
                          start: date, end: date) -> dict:
        """location = 'locations/456' (accounts/ prefix NAHI).
        metrics e.g. ['BUSINESS_IMPRESSIONS_MOBILE_SEARCH','CALL_CLICKS',
        'WEBSITE_CLICKS','BUSINESS_DIRECTION_REQUESTS']"""
        def d(x: date):
            return {"year": x.year, "month": x.month, "day": x.day}

        try:
            resp = (
                self.perf.locations()
                .fetchMultiDailyMetricsTimeSeries(
                    location=location,
                    dailyMetrics=metrics,
                    dailyRange={"startDate": d(start), "endDate": d(end)},
                )
                .execute()
            )
            return resp
        except HttpError as e:
            self._check_http_error(e)

    def get_search_keywords(self, location: str, page_size: int = 50) -> dict:
        """Monthly search keywords jinke zariye profile mila."""
        try:
            return (
                self.perf.locations()
                .searchkeywords()
                .impressions()
                .monthly()
                .list(parent=location, pageSize=page_size)
                .execute()
            )
        except HttpError as e:
            self._check_http_error(e)
