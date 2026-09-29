import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, ClientPicker, ConnDot, EmptyState, Loading, Modal, PageHeader, useClient } from '../components/ui'

const FIELDS = [
  ['name', 'Business name', 'text'],
  ['description', 'Business description', 'textarea'],
  ['primary_category', 'Primary category', 'text'],
  ['secondary_categories', 'Secondary categories (comma separated)', 'text'],
  ['phone', 'Phone', 'text'],
  ['website', 'Website', 'text'],
  ['city', 'City', 'text'],
  ['services', 'Services (comma separated)', 'text'],
  ['photos_count', 'Photos on profile', 'number'],
  ['videos_count', 'Videos on profile', 'number'],
  ['posts_last_30d', 'Posts in last 30 days', 'number'],
  ['review_count', 'Total reviews', 'number'],
  ['rating', 'Average rating (0–5)', 'number'],
  ['unanswered_reviews', 'Unanswered reviews', 'number'],
  ['hours_set', 'Opening hours set', 'checkbox'],
  ['nap_name', 'Name matches everywhere (NAP)', 'checkbox'],
  ['nap_address', 'Address matches everywhere (NAP)', 'checkbox'],
  ['nap_phone', 'Phone matches everywhere (NAP)', 'checkbox'],
]

function scoreColor(score) {
  if (score >= 75) return { bg: '#dcfce7', fg: '#15803d' }
  if (score >= 50) return { bg: '#fef3c7', fg: '#b45309' }
  return { bg: '#fee2e2', fg: '#b91c1c' }
}

export default function Audit() {
  const [clients, setClients] = useState(null)
  const [slug, pick] = useClient(clients || [])
  const [client, setClient] = useState(null)
  const [result, setResult] = useState(null)
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({})
  const [running, setRunning] = useState(false)

  useEffect(() => {
    api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  }, [])

  useEffect(() => {
    if (!slug) return
    setErr(''); setOk(''); setResult(null)
    Promise.all([api.get(`/clients/${slug}`), api.get(`/audit/${slug}`)])
      .then(([c, a]) => { setClient(c.client); setResult(a.result) })
      .catch((e) => setErr(e.message))
  }, [slug])

  const runManual = async () => {
    setErr(''); setOk(''); setRunning(true)
    try {
      const body = { mode: 'manual' }
      FIELDS.forEach(([k, , t]) => {
        body[k] = t === 'checkbox' ? !!form[k] : (form[k] || '')
      })
      const d = await api.post(`/audit/${slug}`, body)
      setResult(d.result); setShowForm(false)
      setOk('Audit complete.')
    } catch (e) { setErr(e.message) }
    setRunning(false)
  }

  const runApi = async () => {
    setErr(''); setOk(''); setRunning(true)
    try {
      const d = await api.post(`/audit/${slug}`, { mode: 'api' })
      setResult(d.result); setShowForm(false)
      setOk('Audit complete — data pulled live from Google.')
    } catch (e) { setErr(e.message) }
    setRunning(false)
  }

  const push = async () => {
    setErr(''); setOk('')
    try {
      const d = await api.post(`/audit/${slug}/push`)
      setOk(`${d.pushed} High/Medium findings pushed to the Activity Tracker.`)
    } catch (e) { setErr(e.message) }
  }

  if (clients === null && !err) return <Loading />
  if (err) return <><PageHeader title="Profile Audit" /><Alert kind="error">{err}</Alert></>
  if (!clients.length) return <><PageHeader title="Profile Audit" /><EmptyState title="No clients yet" text="Add your first client to start using this page." action={<Link to="/clients" className="btn primary">Add client →</Link>} /></>

  const groups = result ? ['High', 'Medium', 'Low'].map((p) => ({
    p, items: (result.findings || []).filter((f) => f.priority === p),
  })) : []

  return (
    <>
      <PageHeader
        title="Profile Audit"
        subtitle="A complete health check of the Google Business Profile — what’s fine, what’s broken, and exactly what to fix, in priority order."
        actions={<ClientPicker clients={clients} value={slug} onChange={pick} />}
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      <div className="card">
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div><strong>{client?.business_name || client?.name}</strong> <ConnDot connected={client?.connected} /></div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            <button className="btn primary" onClick={() => setShowForm(true)}>Run audit</button>
            {result && <button className="btn" onClick={push}>Push findings to tracker</button>}
          </div>
        </div>
        <p className="muted" style={{ margin: '8px 0 0', fontSize: 13 }}>
          Fill the profile details manually, or — if the client is Google-connected — pull everything live from Google with one click.
        </p>
      </div>

      {!result ? (
        <EmptyState title="No audit yet" text="Run an audit to see the profile's health score and prioritized fixes." action={<button className="btn primary" onClick={() => setShowForm(true)}>Run audit</button>} />
      ) : (
        <>
          <div className="card">
            <div style={{ display: 'flex', gap: 18, alignItems: 'center', flexWrap: 'wrap' }}>
              <div className="score-ring" style={{ background: scoreColor(result.score).bg, color: scoreColor(result.score).fg }}>
                {result.score}<small>/ 100</small>
              </div>
              <div>
                <h3 style={{ margin: '0 0 4px' }}>Grade: {result.grade} <span className="muted" style={{ fontWeight: 400 }}>· source: {result.source || (result.findings?.[0]?.source) || 'manual entry'}</span></h3>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <Badge value={`${result.high} High`} tone="red" />
                  <Badge value={`${result.medium} Medium`} tone="amber" />
                  <Badge value={`${result.low} Low`} tone="slate" />
                </div>
              </div>
            </div>
          </div>
          {groups.map((g) => g.items.length > 0 && (
            <div className="card" key={g.p}>
              <h3>{g.p} priority <span className="sub">{g.items.length} item{g.items.length > 1 ? 's' : ''}</span></h3>
              {g.items.map((f, i) => (
                <div className="finding" key={i}>
                  <div className="f-head"><Badge value={f.priority} /><strong>{f.area}</strong></div>
                  <div className="f-body">
                    <div><span className="lbl">Now — </span>{f.current_status}</div>
                    <div><span className="lbl">Issue — </span>{f.issue}</div>
                    <div><span className="lbl">Fix — </span>{f.action}</div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </>
      )}

      {showForm && (
        <Modal title="Run profile audit" onClose={() => setShowForm(false)} wide>
          {client?.connected && client?.location_id && (
            <div style={{ marginBottom: 14 }}>
              <button className="btn success" disabled={running} onClick={runApi}>
                {running ? 'Pulling…' : 'Pull live data from Google'}
              </button>
              <p className="muted" style={{ fontSize: 12.5, margin: '6px 0 0' }}>Uses the connected Google account — no typing needed.</p>
              <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '14px 0' }} />
              <p className="muted" style={{ fontSize: 13 }}><strong>Or</strong> fill manually:</p>
            </div>
          )}
          <div className="form-grid">
            {FIELDS.map(([k, label, t]) => (
              <div className={`field ${t === 'textarea' ? 'full' : ''}`} key={k}>
                {t === 'checkbox' ? (
                  <label className="checkbox-row"><input type="checkbox" checked={!!form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.checked })} />{label}</label>
                ) : (
                  <>
                    <label>{label}</label>
                    {t === 'textarea'
                      ? <textarea value={form[k] || ''} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
                      : <input type={t} value={form[k] || ''} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />}
                  </>
                )}
              </div>
            ))}
          </div>
          <div className="form-actions">
            <button className="btn primary" disabled={running} onClick={runManual}>{running ? 'Running…' : 'Run audit'}</button>
            <button className="btn" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </Modal>
      )}
    </>
  )
}
