import React from 'react'
import { Link } from 'react-router-dom'
import { Alert, Badge, PageHeader } from '../components/ui'

const FORM_URL = 'https://support.google.com/business/contact/api_default'

export default function Help() {
  return (
    <>
      <PageHeader
        title="Help & Setup"
        subtitle="Everything you need to know — what works today, and the 4 steps to switch on fully automatic publishing."
      />

      <div className="card">
        <h3>What works right now (manual mode) <span className="sub">No Google approval needed — usable from minute one</span></h3>
        <div className="table-wrap"><table>
          <thead><tr><th>Feature</th><th>Manual mode</th><th>Live mode (after setup)</th></tr></thead>
          <tbody>
            <tr><td><strong>Profile audit</strong></td><td><Badge value="Works" tone="green" /> Fill details manually, get score + prioritized fixes</td><td>One click pulls everything live from Google</td></tr>
            <tr><td><strong>Keywords</strong></td><td><Badge value="Works" tone="green" /> Add + organize manually</td><td>Same, plus DataForSEO keyword ideas</td></tr>
            <tr><td><strong>Content calendar</strong></td><td><Badge value="Works" tone="green" /> Generate monthly plan, queue drafts</td><td>Same</td></tr>
            <tr><td><strong>Post publishing</strong></td><td><Badge value="Copy-paste" tone="amber" /> Drafts prepared here, you post manually on Google</td><td><Badge value="Automatic" tone="green" /> Approved posts publish on schedule</td></tr>
            <tr><td><strong>Review replies</strong></td><td><Badge value="Drafts" tone="amber" /> Reply text prepared here, you paste it on Google</td><td><Badge value="Automatic" tone="green" /> New reviews detected hourly, replies sent after your approval</td></tr>
            <tr><td><strong>Photos / videos</strong></td><td><Badge value="Plan" tone="amber" /> Queue planned here, upload manually</td><td><Badge value="Automatic" tone="green" /> Uploads from public URLs</td></tr>
            <tr><td><strong>Competitors</strong></td><td><Badge value="Works" tone="green" /> Track manually</td><td>Same, plus DataForSEO Maps lookup</td></tr>
            <tr><td><strong>Reports</strong></td><td><Badge value="Works" tone="green" /> Fill numbers manually, compile client-ready report</td><td><Badge value="Automatic" tone="green" /> Performance numbers pulled from Google</td></tr>
          </tbody>
        </table></div>
        <p className="muted" style={{ fontSize: 13, margin: '10px 0 0' }}>
          Bottom line: even today this is a complete content factory + tracker. The live setup below only switches on the <em>automatic</em> publishing.
        </p>
      </div>

      <div className="card">
        <h3>Going live — 4 steps <span className="sub">Do this once. The only slow part is Google's approval (Step 2).</span></h3>
        <ol className="steps">
          <li>
            <h4>Accounts, login &amp; Demo/Live mode</h4>
            <p>Every operator signs up from the login screen — email + password, or Google sign-in. The first account becomes <strong>super admin</strong> (manages users, enables/disables accounts, views login history).</p>
            <p>Top-right <strong>Live / Demo</strong> switch: Live shows only your real clients; Demo also shows the demo client (Sharma Dental Clinic, dummy data — never deleted, just hidden in Live mode).</p>
            <p>Each operator sees only their own clients. The central Google OAuth client and approval belong to this server — operators never set up Cloud projects, APIs, or JSON files.</p>
          </li>
          <li>
            <h4>Create a Google Cloud project &amp; enable the APIs</h4>
            <p>Go to <a href="https://console.cloud.google.com" target="_blank" rel="noreferrer">console.cloud.google.com</a> → create a new project → open <strong>APIs &amp; Services → Library</strong> and enable these 4:</p>
            <ul>
              <li>My Business Account Management API</li>
              <li>My Business Business Information API</li>
              <li>Business Profile Performance API</li>
              <li>My Business Notifications API</li>
            </ul>
            <p className="muted" style={{ fontSize: 13 }}>Note: the legacy v4 API (posts, reviews &amp; media) doesn’t appear in the Library for new projects — it’s granted automatically with the Basic API Access approval in Step 2.</p>
            <p>Takes about 10 minutes.</p>
          </li>
          <li>
            <h4>Apply for Basic API Access <Badge value="Needs Google's approval" tone="amber" /></h4>
            <p>Open <a href={FORM_URL} target="_blank" rel="noreferrer">{FORM_URL}</a> and choose <strong>“Application for Basic API Access”</strong>. <strong>You</strong> (the agency) submit this form — the approval is granted to <strong>your Cloud project</strong>, not to the client. You’ll need:</p>
            <ul>
              <li>Your Google Cloud <strong>project number</strong> (Cloud Console dashboard → Project Info)</li>
              <li>To be signed in with an email that is an <strong>owner or manager</strong> of a Google Business Profile — ask your client to add your email as a <strong>Manager</strong> on their profile (takes them 2 minutes); that’s the client’s only job in this whole process</li>
              <li>That profile must be <strong>verified and active for 60+ days</strong>, with a <strong>live business website</strong></li>
            </ul>
            <p>Approval usually takes <strong>a few days to ~2 weeks</strong>. Until then your API quota is <strong>0</strong> — every call fails, and that’s normal. Google emails you when it’s approved (quota jumps to 300/min).</p>
            <Alert kind="warn">Don’t skip this step — without approval, automatic publishing is impossible, no matter what any tool promises.</Alert>
          </li>
          <li>
            <h4>Create an OAuth client &amp; connect each client</h4>
            <p>In the same Cloud project: <strong>APIs &amp; Services → Credentials → Create Credentials → OAuth client ID</strong> (type: <strong>Web application</strong> for a live site — Desktop app is only for local use). Add the redirect URI <code>/oauth/callback</code> on your live domain. Download the JSON file and save it on the server as <code>client_secrets.json</code> in the app folder — once only, for all clients. No path to paste anywhere.</p>
            <p>Then in this app: <strong>Clients → Add client</strong> → <strong>Connect Google</strong> → sign in with the Google account that manages that business → Allow. Done once per client.</p>
            <p>Tokens are stored only on this machine (in the <code>tokens/</code> folder) — never uploaded anywhere.</p>
          </li>
          <li>
            <h4>Turn dry-run OFF</h4>
            <p>Go to <Link to="/settings">Settings</Link> and switch <strong>dry-run OFF</strong>. From now on:</p>
            <ul>
              <li>Approved + scheduled posts publish to Google automatically (every 15 min check)</li>
              <li>New reviews are detected hourly; your approved replies are sent</li>
              <li>Media uploads go live from their public URLs</li>
            </ul>
            <p>Keep per-client <strong>auto-publish OFF</strong> unless you’re fully comfortable — approval mode means you still review every post before it goes out.</p>
          </li>
        </ol>
      </div>

      <div className="card">
        <h3>Safety notes <span className="sub">Why some things always need your eyes</span></h3>
        <ul style={{ fontSize: 13.5, color: '#334155', paddingLeft: 18, margin: 0 }}>
          <li style={{ marginBottom: 8 }}><strong>Category / profile edits</strong> can trigger Google re-verification and temporarily hide a listing — the platform flags these as high risk and never does them automatically.</li>
          <li style={{ marginBottom: 8 }}><strong>Negative (1–2 star) reviews</strong> are always flagged for human review before any reply goes out.</li>
          <li style={{ marginBottom: 8 }}><strong>Offers, prices and claims</strong> in posts are your responsibility — the platform drafts, you approve.</li>
          <li><strong>Reports never invent numbers.</strong> Every figure is labeled <Badge value="API" tone="green" /> or <Badge value="manual" tone="slate" />.</li>
        </ul>
      </div>

      <div className="card">
        <h3>Daily workflow <span className="sub">The 10-minute routine once live</span></h3>
        <ol style={{ fontSize: 13.5, color: '#334155', paddingLeft: 18, margin: 0 }}>
          <li style={{ marginBottom: 6 }}>Open <strong>Dashboard</strong> — check pending approvals.</li>
          <li style={{ marginBottom: 6 }}>Approve or edit drafts in <strong>Content Queue</strong>, check <strong>Reviews</strong> for new replies to approve.</li>
          <li style={{ marginBottom: 6 }}>Once a month: <strong>Calendar → generate → queue</strong>, then <strong>Reports → compile</strong> and send to the client.</li>
          <li>Everything is logged in the <strong>Activity Tracker</strong> automatically.</li>
        </ol>
      </div>
    </>
  )
}
