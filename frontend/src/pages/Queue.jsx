import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, ClientPicker, EmptyState, Loading, Modal, PageHeader, useClient } from '../components/ui'

const TABS = ['all', 'draft', 'approved', 'scheduled', 'published', 'failed']

export default function Queue() {
  const [clients, setClients] = useState(null)
  const [slug, pick] = useClient(clients || [])
  const [posts, setPosts] = useState([])
  const [creatives, setCreatives] = useState([])
  const [tab, setTab] = useState('all')
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [editing, setEditing] = useState(null)
  const [edit, setEdit] = useState({})
  const [schedId, setSchedId] = useState(null)
  const [schedDate, setSchedDate] = useState('')

  useEffect(() => {
    api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  }, [])

  const load = () => {
    if (!slug) return
    api.get(`/queue/${slug}`).then((d) => setPosts(d.posts)).catch((e) => setErr(e.message))
    api.get(`/creatives/${slug}`).then((d) => setCreatives(d.creatives)).catch(() => {})
  }
  useEffect(load, [slug])

  const wrap = (fn) => async (...a) => {
    setErr(''); setOk('')
    try { const r = await fn(...a); if (r) setOk(r); load() }
    catch (e) { setErr(e.message) }
  }

  const saveEdit = wrap(async () => {
    await api.patch(`/queue/${slug}/${editing.id}`, edit)
    setEditing(null)
    return 'Post updated.'
  })

  const approve = wrap(async (id) => {
    await api.post(`/queue/${slug}/${id}/approve`)
    return 'Approved — ready to schedule.'
  })

  const schedule = wrap(async () => {
    if (!schedDate) throw new Error('Pick a date first.')
    await api.post(`/queue/${slug}/${schedId}/schedule`, { scheduled_date: schedDate })
    setSchedId(null); setSchedDate('')
    return 'Scheduled.'
  })

  const publish = wrap(async (id) => {
    if (!window.confirm('Publish this post to Google now?')) return null
    const d = await api.post(`/queue/${slug}/${id}/publish`)
    if (!d.ok) throw new Error(d.message)
    return d.message || 'Published!'
  })

  const remove = wrap(async (id) => {
    if (!window.confirm('Delete this draft?')) return null
    await api.del(`/queue/${slug}/${id}`)
    return 'Deleted.'
  })

  if (clients === null && !err) return <Loading />
  if (err) return <><PageHeader title="Content Queue" /><Alert kind="error">{err}</Alert></>
  if (!clients.length) return <><PageHeader title="Content Queue" /><EmptyState title="No clients yet" text="Add your first client to start using this page." action={<Link to="/clients" className="btn primary">Add client →</Link>} /></>

  const shown = tab === 'all' ? posts : posts.filter((p) => p.status === tab)
  const counts = {}
  posts.forEach((p) => { counts[p.status] = (counts[p.status] || 0) + 1 })

  return (
    <>
      <PageHeader
        title="Content Queue"
        subtitle="Every post, from draft to published. Nothing goes live on Google without your approval — approve a draft, schedule it, then publish."
        actions={<ClientPicker clients={clients} value={slug} onChange={pick} />}
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t} className={`btn small ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t[0].toUpperCase() + t.slice(1)}{t !== 'all' && counts[t] ? ` (${counts[t]})` : ''}
          </button>
        ))}
      </div>

      {shown.length === 0 ? (
        <EmptyState title={`No ${tab} posts`} text="Generate a content calendar and queue it as drafts to get started." />
      ) : (
        shown.map((p) => (
          <div className="card" key={p.id}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 8 }}>
              <Badge value={p.status} />
              <Badge value={p.post_type} tone="indigo" />
              {p.keyword && <span className="muted" style={{ fontSize: 12.5 }}>keyword: {p.keyword}</span>}
              {p.creative_id > 0 && <span className="muted" style={{ fontSize: 12.5 }}>creative: {(creatives.find((c) => c.id === p.creative_id) || {}).topic || `#${p.creative_id}`}</span>}
              {p.scheduled_date && <span className="muted" style={{ fontSize: 12.5 }}>→ {p.scheduled_date}</span>}
              <div className="row-actions" style={{ marginLeft: 'auto' }}>
                <button className="btn small" onClick={() => { setEditing(p); setEdit({ summary: p.summary, topic: p.topic, cta_url: p.cta_url, topic_type: p.topic_type, cta_type: p.cta_type, intent: p.intent || '', problem: p.problem || '', offer_details: p.offer_details || '', creative_id: p.creative_id || 0 }) }}>Edit</button>
                {p.status === 'draft' && <button className="btn small primary" onClick={() => approve(p.id)}>Approve</button>}
                {(p.status === 'draft' || p.status === 'approved') && <button className="btn small" onClick={() => { setSchedId(p.id); setSchedDate(p.scheduled_date || '') }}>Schedule</button>}
                {(p.status === 'approved' || p.status === 'scheduled') && <button className="btn small success" onClick={() => publish(p.id)}>Publish now</button>}
                {p.status !== 'published' && <button className="btn small danger" onClick={() => remove(p.id)}>Delete</button>}
              </div>
            </div>
            <div style={{ fontWeight: 650, marginBottom: 4 }}>{p.topic}</div>
            <div style={{ fontSize: 13.5, color: '#334155', whiteSpace: 'pre-wrap' }}>{p.summary}</div>
            {p.cta_url && <div style={{ marginTop: 6, fontSize: 12.5 }} className="muted">CTA: {p.cta_type} → {p.cta_url}</div>}
          </div>
        ))
      )}

      {editing && (
        <Modal title="Edit post" onClose={() => setEditing(null)}>
          <div className="field"><label>Topic</label><input type="text" value={edit.topic || ''} onChange={(e) => setEdit({ ...edit, topic: e.target.value })} /></div>
          <div className="field"><label>Search intent</label><input type="text" value={edit.intent || ''} onChange={(e) => setEdit({ ...edit, intent: e.target.value })} placeholder="e.g. book appointment, learn more" /></div>
          <div className="field full"><label>Customer problem</label><input type="text" value={edit.problem || ''} onChange={(e) => setEdit({ ...edit, problem: e.target.value })} placeholder="What problem does this post solve?" /></div>
          <div className="field"><label>Post text</label><textarea rows={6} value={edit.summary || ''} onChange={(e) => setEdit({ ...edit, summary: e.target.value })} /></div>
          <div className="field"><label>Offer details</label><input type="text" value={edit.offer_details || ''} onChange={(e) => setEdit({ ...edit, offer_details: e.target.value })} placeholder="Only for offer posts — confirmed details only" /></div>
          <div className="field"><label>Linked creative</label>
            <select value={edit.creative_id || 0} onChange={(e) => setEdit({ ...edit, creative_id: Number(e.target.value) })}>
              <option value={0}>— none —</option>
              {creatives.map((c) => <option key={c.id} value={c.id}>#{c.id} {c.topic}</option>)}
            </select></div>
          <div className="form-grid">
            <div className="field"><label>Post type</label>
              <select value={edit.topic_type || 'STANDARD'} onChange={(e) => setEdit({ ...edit, topic_type: e.target.value })}>
                {['STANDARD', 'EVENT', 'OFFER', 'ALERT'].map((t) => <option key={t} value={t}>{t}</option>)}
              </select></div>
            <div className="field"><label>Button</label>
              <select value={edit.cta_type || 'LEARN_MORE'} onChange={(e) => setEdit({ ...edit, cta_type: e.target.value })}>
                {['LEARN_MORE', 'BOOK', 'ORDER', 'SHOP', 'SIGN_UP', 'CALL'].map((t) => <option key={t} value={t}>{t}</option>)}
              </select></div>
            <div className="field full"><label>Button link</label><input type="text" value={edit.cta_url || ''} onChange={(e) => setEdit({ ...edit, cta_url: e.target.value })} /></div>
          </div>
          <div className="form-actions">
            <button className="btn primary" onClick={saveEdit}>Save</button>
            <button className="btn" onClick={() => setEditing(null)}>Cancel</button>
          </div>
        </Modal>
      )}

      {schedId && (
        <Modal title="Schedule post" onClose={() => setSchedId(null)}>
          <div className="field"><label>Publish date</label><input type="date" value={schedDate} onChange={(e) => setSchedDate(e.target.value)} /></div>
          <div className="form-actions">
            <button className="btn primary" onClick={schedule}>Schedule</button>
            <button className="btn" onClick={() => setSchedId(null)}>Cancel</button>
          </div>
        </Modal>
      )}
    </>
  )
}
