import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, ClientPicker, ConnDot, EmptyState, Loading, PageHeader, useClient } from '../components/ui'

function starStr(n) {
  const s = Number(n) || 0
  return '★'.repeat(s) + '☆'.repeat(Math.max(0, 5 - s))
}

export default function Reviews() {
  const [clients, setClients] = useState(null)
  const [slug, pick] = useClient(clients || [])
  const [client, setClient] = useState(null)
  const [revs, setRevs] = useState([])
  const [lastCheck, setLastCheck] = useState('')
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [drafts, setDrafts] = useState({})
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  }, [])

  const load = () => {
    if (!slug) return
    Promise.all([api.get(`/clients/${slug}`), api.get(`/reviews/${slug}`)])
      .then(([c, r]) => {
        setClient(c.client); setRevs(r.reviews); setLastCheck(r.last_check)
        const d = {}
        r.reviews.forEach((x) => { d[x.review_name] = x.reply_text || '' })
        setDrafts(d)
      })
      .catch((e) => setErr(e.message))
  }
  useEffect(load, [slug])

  const check = async () => {
    setErr(''); setOk(''); setBusy(true)
    try {
      await api.post(`/reviews/${slug}/check`)
      setOk('Review check started — new reviews appear below shortly. Refresh in a few seconds.')
      setTimeout(load, 4000)
    } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  const save = async (rname) => {
    setErr(''); setOk('')
    try {
      await api.patch(`/reviews/${slug}`, { review_name: rname, reply_text: drafts[rname] || '' })
      setOk('Reply draft saved.')
      load()
    } catch (e) { setErr(e.message) }
  }

  const send = async (rname) => {
    if (!window.confirm('Send this reply to Google? It will be public, under the business name.')) return
    setErr(''); setOk('')
    try {
      const d = await api.post(`/reviews/${slug}/send`, { review_name: rname, reply_text: drafts[rname] || '' })
      if (!d.ok) throw new Error(d.message)
      setOk(d.message || 'Reply sent.')
      load()
    } catch (e) { setErr(e.message) }
  }

  if (clients === null && !err) return <Loading />
  if (err) return <><PageHeader title="Reviews" /><Alert kind="error">{err}</Alert></>
  if (!clients.length) return <><PageHeader title="Reviews" /><EmptyState title="No clients yet" text="Add your first client to start using this page." action={<Link to="/clients" className="btn primary">Add client →</Link>} /></>

  return (
    <>
      <PageHeader
        title="Reviews"
        subtitle="Every new review in one place. Draft a personal reply, review it, then send — negative reviews are always flagged for your eyes first."
        actions={<>
          <ClientPicker clients={clients} value={slug} onChange={pick} />
          <button className="btn primary" disabled={busy} onClick={check}>{busy ? 'Checking…' : 'Check for new reviews'}</button>
        </>}
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      <div className="card">
        <ConnDot connected={client?.connected} />
        <span className="muted" style={{ marginLeft: 10, fontSize: 13 }}>
          {lastCheck ? `Last checked: ${lastCheck}` : 'Never checked yet.'}
          {!client?.connected && ' Connect Google in Clients to pull reviews automatically.'}
        </span>
      </div>

      {revs.length === 0 ? (
        <EmptyState title="No pending reviews" text="All caught up — or press “Check for new reviews” to pull the latest from Google." />
      ) : (
        revs.map((r) => (
          <div className="card" key={r.review_name}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 6 }}>
              <strong>{r.reviewer || 'Anonymous'}</strong>
              <span className="stars">{starStr(r.stars)}</span>
              {r.needs_human ? <Badge value="Needs human review" tone="red" /> : null}
              <Badge value={r.reply_status === 'sent' ? 'Replied' : 'Awaiting reply'} tone={r.reply_status === 'sent' ? 'green' : 'amber'} />
              <span className="muted" style={{ fontSize: 12.5, marginLeft: 'auto' }}>{r.update_time || r.create_time}</span>
            </div>
            <p style={{ margin: '0 0 12px', fontSize: 13.5 }}>{r.text || <span className="muted">(no text)</span>}</p>
            <div className="field"><label>Your reply</label>
              <textarea rows={3} value={drafts[r.review_name] || ''} onChange={(e) => setDrafts({ ...drafts, [r.review_name]: e.target.value })} placeholder="Write a personal, professional reply…" />
            </div>
            <div className="form-actions" style={{ marginTop: 8 }}>
              <button className="btn" onClick={() => save(r.review_name)}>Save draft</button>
              <button className="btn success" onClick={() => send(r.review_name)}>Send reply</button>
            </div>
          </div>
        ))
      )}
    </>
  )
}
