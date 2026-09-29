import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, Loading, PageHeader } from '../components/ui'

export default function Settings() {
  const [s, setS] = useState(null)
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')

  const load = () => api.get('/settings').then(setS).catch((e) => setErr(e.message))
  useEffect(() => { load() }, [])

  const setDryRun = async (val) => {
    setErr(''); setOk('')
    try {
      if (!val && !window.confirm('Turn OFF dry-run? From now on, approved posts, review replies and media uploads will go LIVE to Google. Only do this after the live setup is complete (see Help & Setup).')) return
      await api.post('/settings', { dry_run: val })
      setOk(val ? 'Dry-run ON — nothing will publish to Google.' : 'Dry-run OFF — publishing is LIVE.')
      load()
    } catch (e) { setErr(e.message) }
  }

  const toggleAuto = async (c, val) => {
    setErr(''); setOk('')
    try {
      if (val && !window.confirm(`Auto-publish for ${c.name}? Approved posts go live WITHOUT per-post review.`)) return
      await api.post(`/clients/${c.slug}/autopublish`, { auto_publish: val })
      setOk(val ? `Auto-publish ON for ${c.name}.` : `Auto-publish OFF for ${c.name}.`)
      load()
    } catch (e) { setErr(e.message) }
  }

  const seedDemo = async (reset) => {
    setErr(''); setOk('')
    try {
      if (reset && !window.confirm('Reset demo data? The demo client and ALL its local data will be deleted and recreated fresh.')) return
      const r = await api.post('/demo/seed', reset ? { reset: true } : {})
      setOk(`Demo client "${r.name}" ready — ${r.keywords} keywords, ${r.queue_drafts} drafts, ${r.reviews} reviews, audit score ${r.audit_score}. Open the Clients page to explore.`)
      load()
    } catch (e) { setErr(e.message) }
  }

  if (!s) return <Loading />

  const ig = s.integrations || {}

  return (
    <>
      <PageHeader
        title="Settings"
        subtitle="Safety switches and integrations. When in doubt, leave dry-run ON — it's the seatbelt."
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      <div className="card">
        <h3>Safety <span className="sub">These protect your clients' public Google profiles</span></h3>
        <label className="checkbox-row" style={{ fontSize: 15, fontWeight: 600 }}>
          <input type="checkbox" checked={s.dry_run} onChange={(e) => setDryRun(e.target.checked)} style={{ width: 20, height: 20 }} />
          Dry-run mode {s.dry_run ? <Badge value="ON" tone="amber" /> : <Badge value="OFF — LIVE" tone="red" />}
        </label>
        <p className="muted" style={{ fontSize: 13, margin: '8px 0 0' }}>
          {s.dry_run
            ? 'ON: the platform prepares everything — drafts, schedules, reply text — but never touches Google. Safe for demos and testing.'
            : 'OFF: approved posts, review replies and media uploads publish to Google for real. Keep this ON until the live setup (Help & Setup) is fully complete.'}
        </p>
      </div>

      <div className="card">
        <h3>Integrations</h3>
        <div className="table-wrap"><table>
          <thead><tr><th>Integration</th><th>Status</th><th>What it enables</th></tr></thead>
          <tbody>
            <tr>
              <td><strong>Google Business Profile API</strong></td>
              <td>{s.dry_run ? <Badge value="Dry-run" tone="amber" /> : <Badge value="Live" tone="green" />}</td>
              <td className="muted">Publishing posts, review replies, photo uploads, live audits &amp; performance data. Needs the <Link to="/help">live setup</Link>.</td>
            </tr>
            <tr>
              <td><strong>DataForSEO</strong></td>
              <td>{ig.dataforseo ? <Badge value="Configured" tone="green" /> : <Badge value="Not configured" tone="slate" />}</td>
              <td className="muted">Keyword ideas and competitor Maps lookup. Set <code>DATAFORSEO_LOGIN</code> / <code>DATAFORSEO_PASSWORD</code> env vars, then restart.</td>
            </tr>
            <tr>
              <td><strong>OpenAI</strong></td>
              <td>{ig.openai ? <Badge value="Configured" tone="green" /> : <Badge value="Not configured" tone="slate" />}</td>
              <td className="muted">Polishes AI-generated post drafts. Set the <code>OPENAI_API_KEY</code> env var, then restart. Optional.</td>
            </tr>
          </tbody>
        </table></div>
      </div>

      <div className="card">
        <h3>Demo data <span className="sub">For testing &amp; client demos — purely local, never touches Google</span></h3>
        <p className="muted" style={{ fontSize: 13, margin: '0 0 12px' }}>
          Creates a realistic demo client (<strong>Sharma Dental Clinic</strong>, Pune) with audit, keywords,
          content calendar, queue drafts, reviews, media, competitors and tracker history — so every page
          has something to show. All data is clearly dummy.
        </p>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button className="btn primary" onClick={() => seedDemo(false)}>Add demo client</button>
          <button className="btn" onClick={() => seedDemo(true)}>Reset demo data</button>
        </div>
      </div>

      <div className="card">
        <h3>Per-client auto-publish <span className="sub">Default OFF — only enable when you fully trust the flow for that client</span></h3>
        <div className="table-wrap"><table>
          <thead><tr><th>Client</th><th>Google</th><th>Auto-publish</th></tr></thead>
          <tbody>
            {(s.clients || []).map((c) => (
              <tr key={c.slug}>
                <td><strong>{c.name}</strong></td>
                <td>{c.connected ? <Badge value="Connected" tone="green" /> : <Badge value="Not connected" tone="slate" />}</td>
                <td>
                  <label className="checkbox-row">
                    <input type="checkbox" checked={!!c.auto_publish} onChange={(e) => toggleAuto(c, e.target.checked)} />
                    <span className="muted">{c.auto_publish ? 'On — posts go live automatically' : 'Off — every post needs approval'}</span>
                  </label>
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </div>
    </>
  )
}
