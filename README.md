# GMB Automation Platform

Google Business Profile (GBP) post-onboarding workflow ka automation — audit → keywords → optimize → posts → reviews → media → competitors → track → report. PDF workflow (Sections 1–12) ka 1:1 implementation.

**UI:** modern React dashboard (Vite SPA) + Flask JSON API backend. `python app.py` → http://127.0.0.1:5003 — ek hi command me dono chalte hain, koi extra step nahi.

**Pages:** Dashboard · Clients · Profile Audit · Keywords · Content Calendar · Content Queue (approval workflow) · Reviews · Photos & Videos · Competitors · Reports · Activity Tracker · Settings · **Help & Setup** (live jaane ke 4 steps, simple bhasha me)

## ⚠️ Sabse pehle — Google API approval (bina iske writes nahi honge)

GBP API **access-gated** hai. Sirf API enable karne se kaam nahi chalega — naya project **quota 0** par start hota hai, har call 403/429 dega jab tak Google approve na kare.

**Step 1 — Google Cloud project banao**
1. [Google Cloud Console](https://console.cloud.google.com) me naya project banao (project **number** note karo — dashboard par dikhta hai, ID nahi).
2. Ye 5 APIs enable karo (APIs & Services → Library):
   - `My Business Account Management API`
   - `My Business Business Information API`
   - `Business Profile Performance API`
   - `My Business Notifications API`
   - `Google My Business API` (legacy v4 — isme Media, Reviews, LocalPosts hain)
   
   Ya terminal se:
   ```bash
   gcloud services enable mybusinessaccountmanagement.googleapis.com \
     mybusinessbusinessinformation.googleapis.com \
     businessprofileperformance.googleapis.com \
     mybusinessnotifications.googleapis.com \
     mybusiness.googleapis.com --project=YOUR_PROJECT_ID
   ```

**Step 2 — Basic API Access ke liye apply karo** ⬅️ sabse important
1. Form kholo: https://support.google.com/business/contact/api_default
2. Dropdown me **"Application for Basic API Access"** select karo.
3. Project number + owner/manager wala email do.
4. **Prerequisites (nahi to reject hoga):**
   - Ek **verified Google Business Profile jo 60+ din purana** ho
   - Us business ki **live website**
   - Profile complete aur up-to-date ho
5. Approval me **kuch din se ~2 hafte** lagte hain. Confirm email ayega; Cloud Console → Quotas me **0 QPM → 300 QPM** dikhega tab samjho approve hua.

**Step 3 — OAuth client banao**
1. Cloud Console → APIs & Services → Credentials → Create Credentials → **OAuth client ID** → type **Desktop app**.
2. Download JSON karo (yeh `client_secrets.json` hai) — ise apne system par kahin safe rakho.
3. Consent screen par scope add karo: `https://www.googleapis.com/auth/business.manage`
4. Redirect URI add karo (Web application type ho to): `http://127.0.0.1:5003/oauth/callback`
   - Desktop-app type me redirect URI ki zarurat nahi padti; OAuth callback isi app me handle hota hai.

**Step 4 — Client connect karo**
1. UI me Clients → client add karo → OAuth secrets JSON ka path save karo → **🔗 Google se Connect** dabao.
2. Browser me Google login + "business.manage" permission allow karo.
3. Token `tokens/<client-slug>.json` me save hoga (gitignored — kisi ko mat bhejo).
4. Connect ke baad client ke **account_id / location_id** bharo (pehli baar khaali the to).

## Bina API approval ke — manual mode

Approval aane tak sab kuch kaam karta hai, sirf Google par publish nahi hota:
- **Audit** — manual form se profile data bharke audit chalao
- **Keywords** — manually add + mapping karo
- **Calendar** — mahine ka content calendar generate karo
- **Content Queue** — drafts banao, approve karo, schedule karo (publish baad me)
- **Tracker / Reports** — activities aur reports manual numbers se
- Jab approval aa jaye → Settings me **dry-run OFF** → drafts publish karo.

## Safety defaults (badalne se pehle do baar socho)

| Setting | Default | Matlab |
|---|---|---|
| `safety.dry_run` | `true` | ON = scheduler/UI Google par **kuch nahi** bhejega |
| `require_approval_posts` | `true` | Post publish se pehle approval mandatory |
| `require_approval_replies` | `true` | Review reply se pehle approval mandatory |
| `require_approval_media` | `true` | Media upload se pehle approval mandatory |
| `require_approval_profile_edits` | `true` | Category/description change = **HIGH RISK** (Google re-verification trigger ho sakta hai) — hamesha explicit approval |
| per-client `auto_publish` | `false` | ON karne par approved+scheduled posts auto-publish honge (warning ke saath) |

- Review replies Google par **public** hote hain — bhejne se pehle draft padh lo.
- 1–2★ reviews hamesha **human review** flag ke saath aate hain.
- Post drafts me **prices/offers kabhi invent nahi hote** — offer posts me `[OFFER DETAILS PENDING]` placeholder rehta hai.
- Rate limit: har profile par **1 publish/minute** se zyada nahi (Google cap: 10 edits/min).

## Setup

```bash
cd gmb-automation
python3 -m venv .venv && source .venv/bin/activate   # recommended
pip install -r requirements.txt
python app.py
```

Kholo: **http://127.0.0.1:5003**

Bas — frontend pehle se `frontend/dist/` me built hai, Flask use serve karta hai. `templates/` wala purana UI hata diya gaya hai.

### Frontend dobara build karna (sirf UI change karne par)

```bash
cd frontend
npm install     # pehli baar
npm run build   # -> frontend/dist (Flask yahin se serve karta hai)
```

Build ke baad `python app.py` restart karo. `frontend/dist/` repo me committed hai taaki bina npm ke bhi demo chale.

### Demo data (tool test karne ke liye)

```bash
python seed_demo.py            # dummy demo client banata hai: "Sharma Dental Clinic"
python seed_demo.py --reset    # purana demo data hata ke dobara banata hai
```

App **band** karke chalana (dono same DB likhte hain). Fir `python app.py` start karo —
audit (score 61, 7 findings), 10 keywords, 9 calendar slots, 5 queue drafts
(draft/approved/scheduled), 6 reviews (ek 2-star human-review ke liye flagged),
4 media items, 3 competitors aur tracker history — sab kuch test karne ke liye
ready milega. Ye saara data dummy hai, sirf testing/demo ke liye.

**UI se bhi kar sakte ho:** Settings → Demo data → **Add demo client**
(terminal ki zaroorat nahi). Reset demo data se dobara fresh ban jata hai.

### Live demo deploy (free — Render.com)

Client ko dikhane ke liye public URL chahiye to Render ke free tier par deploy karo:

1. Is folder ka code apne **GitHub** repo me push karo (`.gitignore` already set hai — tokens/DB push nahi honge).
2. [render.com](https://render.com) par free account banao → **New → Blueprint** → apna repo select karo (`render.yaml` auto-detect hogi).
3. Plan **Free** rakho → **Apply** dabao. 2-3 minute me live URL mil jayegi, jaise `https://gmb-automation-demo.onrender.com`.

**Free tier ki 2 baatein yaad rakho:**
- 15 minute idle rehne par server so jata hai — pehla load ~1 minute lega, uske baad fast.
- Redeploy/restart par demo database reset ho jayegi — **Settings → Add demo client** dabate hi sab wapas aa jata hai (10 second ka kaam).

## Roz ka workflow

1. **Clients** — naya client add + Google connect
2. **Audit** — live/manual audit → findings → "📌 Tracker me activities banao"
3. **Keywords** — keywords add + service/category mapping (DataForSEO optional)
4. **Calendar** — mahine ka calendar generate → drafts queue me
5. **Content Queue** — drafts edit → approve → schedule (scheduler auto-publish karega, ya Publish now)
6. **Reviews** — naye reviews check → draft replies edit → Approve & Send
7. **Media** — photo/video queue (public URL chahiye) → upload
8. **Competitors** — manual ya DataForSEO se track karo
9. **Reports** — period select → Performance API/manual numbers → HTML report
10. **Tracker** — saari activities ek jagah, status flow ke saath

## Files

| File | Kaam |
|---|---|
| `app.py` | Flask **JSON API** backend (`/api/*`) + React SPA serve karta hai (port 5003) |
| `frontend/` | React (Vite) dashboard source — `src/pages/`, `src/components/`, `src/api.js` |
| `frontend/dist/` | Built UI (committed) — Flask ise serve karta hai |
| `gmb/auth.py` | OAuth flow + token refresh (per-client) |
| `gmb/api.py` | GBP API client — accounts, locations, reviews, posts, media, performance |
| `gmb/audit.py` | Audit checks → Current Status → Issue → Action → Priority |
| `gmb/content.py` | Calendar generator + post drafts (template-based; optional OpenAI enhance) |
| `gmb/reviews.py` | Review polling + personalized reply drafts (no repeats) |
| `gmb/scheduler.py` | APScheduler — auto-publish, review checks, reminders (dry-run aware) |
| `gmb/tracker.py` | SQLite master tracker (status flow enforced) |
| `gmb/reports.py` | Report compiler → HTML (sirf real data, source labels ke saath) |
| `gmb/dataforseo.py` | Optional: Maps competitor data + keyword suggestions |
| `config.yaml` | Posting mix, safety toggles, scheduler intervals |
| `tokens/` | Per-client OAuth tokens (gitignored — **kabhi share mat karo**) |
| `gmb_automation.db` | Saara data (gitignored) |
| `reports/` | Generated HTML reports |

## API overview (React UI inhi ko call karti hai)

Sab `/api/*` par, JSON in/out. Error hamesha `{"ok":false,"error":"..."}`.

| Area | Endpoints |
|---|---|
| System | `GET /api/health`, `GET /api/status` (dry-run, pending counts, integrations), `GET /api/logs` |
| Clients | `GET/POST /api/clients`, `GET/PATCH /api/clients/:slug`, `POST /api/clients/:slug/autopublish`, `GET /api/connect/:slug` (OAuth URL), `POST /api/disconnect/:slug` |
| Audit | `GET/POST /api/audit/:slug` (`mode: manual\|api`), `POST /api/audit/:slug/push` |
| Keywords | `GET/POST /api/keywords/:slug`, `PATCH/DELETE /api/keywords/:slug/:kid`, `POST /api/keywords/:slug/dataforseo` |
| Calendar | `GET /api/calendar/:slug`, `POST /api/calendar/:slug/generate`, `POST /api/calendar/:slug/queue` |
| Queue | `GET /api/queue/:slug`, `PATCH /api/queue/:slug/:pid`, `POST .../approve`, `POST .../schedule`, `POST .../publish`, `DELETE .../:pid` |
| Reviews | `GET /api/reviews/:slug`, `POST /api/reviews/:slug/check`, `PATCH /api/reviews/:slug` (save draft), `POST /api/reviews/:slug/send` |
| Media | `GET/POST /api/media/:slug`, `POST /api/media/:slug/:mid/publish` |
| Competitors | `GET/POST /api/competitors/:slug`, `DELETE /api/competitors/:slug/:cid`, `POST /api/competitors/:slug/dataforseo` |
| Reports | `GET /api/reports/:slug`, `POST /api/reports/:slug/compile`, `GET /api/report/:rid` (HTML) |
| Tracker | `GET /api/tracker`, `POST /api/tracker`, `POST /api/tracker/:aid/transition` |
| Settings | `GET/POST /api/settings` |

## Optional integrations

```bash
export DATAFORSEO_LOGIN="..." DATAFORSEO_PASSWORD="..."  # competitor Maps data + keyword ideas
export OPENAI_API_KEY="..."                              # post drafts polish (config me openai.enabled: true)
```

## Notes / limits

- **Q&A API** Google ne Nov 2025 me band kar diya — is tool me Q&A feature nahi hai.
- **Post view counts** (Sep 2026 me dashboard me aaye) abhi API me nahi hain — reports me nahi ayenge.
- Competitor profiles ka **koi official API nahi** — DataForSEO (paid, per-lookup) ya manual entry.
- Google page/API design badalta rehta hai — koi endpoint fail ho to `gmb/api.py` ke method names Google ke [REST reference](https://developers.google.com/my-business/reference/rest/v1/accounts.locations.localPosts) se match karo.
