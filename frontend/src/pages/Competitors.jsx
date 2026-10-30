import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, ClientPicker, EmptyState, Loading, PageHeader, useClient } from '../components/ui'

export default function Competitors() {
  const [clients, setClients] = useState(null)
  const [slug, pick] = useClient(clients || [])
  const [comps, setComps] = useState([])
  const [dfsOn, setDfsOn] = useState(false)
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [form, setForm] = useState({ name: '', maps_url: '', rating: '', review_count: '', categories: '', posting_freq: '', notes: '', services: '', offers: '', post_topics: '' })
  const [dfsForm, setDfsForm] = useState({ keyword: '', location: '' })

  useEffect(() => {
    api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  }, [])

  const load = () => {
    if (!slug) return
    api.get(`/competitors/${slug}`).then((d) => { setComps(d.competitors); setDfsOn(d.dataforseo_on) }).catch((e) => setErr(e.message))
  }
  useEffect(load, [slug])

  const wrap = (fn) => async (...a) => {
    setErr(''); setOk('')
    try { const r = await fn(...a); if (r) setOk(r); load() }
    catch (e) { setErr(e.message) }
  }

  const add = wrap(async () => {
    if (!form.name.trim()) throw new Error('Competitor name is required.')
    await api.post(`/competitors/${slug}`, form)
    setForm({ name: '', maps_url: '', rating: '', review_count: '', categories: '', posting_freq: '', notes: '', services: '', offers: '', post_topics: '' })
    return 'Competitor added.'
  })

  const remove = wrap(async (id) => {
    if (!window.confirm('Remove this competitor?')) return null
    await api.del(`/competitors/${slug}/${id}`)
    return 'Removed.'
  })

  const fetchDfs = wrap(async () => {
    const d = await api.post(`/competitors/${slug}/dataforseo`, dfsForm)
    return `${d.added} competitors found via DataForSEO.`
  })

  if (clients === null && !err) return <Loading />
  if (err) return <><PageHeader title="Competitors" /><Alert kind="error">{err}</Alert></>
  if (!clients.length) return <><PageHeader title="Competitors" /><EmptyState title="No clients yet" text="Add your first client to start using this page." action={<Link to="/clients" className="btn primary">Add client →</Link>} /></>

  return (
    <>
      <PageHeader
        title="Competitors"
        subtitle="Watch what nearby competitors do — their categories, review growth, posting rhythm — and spot what your client is missing."
        actions={<ClientPicker clients={clients} value={slug} onChange={pick} />}
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      <div className="card">
        <h3>Find competitors <span className="sub">DataForSEO Maps lookup — needs API credentials</span></h3>
        {dfsOn ? (
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'end' }}>
            <div className="field" style={{ margin: 0 }}><label>Keyword</label><input type="text" value={dfsForm.keyword} onChange={(e) => setDfsForm({ ...dfsForm, keyword: e.target.value })} placeholder="e.g. dental clinic" /></div>
            <div className="field" style={{ margin: 0 }}><label>Location</label><input type="text" value={dfsForm.location} onChange={(e) => setDfsForm({ ...dfsForm, location: e.target.value })} placeholder="e.g. Noida,India" /></div>
            <button className="btn" onClick={fetchDfs}>Look up</button>
          </div>
        ) : <p className="muted">DataForSEO is not configured — track competitors manually below, or set it up in Settings.</p>}
      </div>

      <div className="card">
        <h3>Add competitor manually</h3>
        <div className="form-grid">
          <div className="field"><label>Name *</label><input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
          <div className="field"><label>Google Maps URL</label><input type="text" value={form.maps_url} onChange={(e) => setForm({ ...form, maps_url: e.target.value })} /></div>
          <div className="field"><label>Rating</label><input type="text" value={form.rating} onChange={(e) => setForm({ ...form, rating: e.target.value })} placeholder="e.g. 4.6" /></div>
          <div className="field"><label>Review count</label><input type="text" value={form.review_count} onChange={(e) => setForm({ ...form, review_count: e.target.value })} /></div>
          <div className="field"><label>Categories</label><input type="text" value={form.categories} onChange={(e) => setForm({ ...form, categories: e.target.value })} /></div>
          <div className="field"><label>Posting frequency</label><input type="text" value={form.posting_freq} onChange={(e) => setForm({ ...form, posting_freq: e.target.value })} placeholder="e.g. 2x per week" /></div>
          <div className="field"><label>Services</label><input type="text" value={form.services} onChange={(e) => setForm({ ...form, services: e.target.value })} /></div>
          <div className="field"><label>Offers</label><input type="text" value={form.offers} onChange={(e) => setForm({ ...form, offers: e.target.value })} /></div>
          <div className="field"><label>Post topics</label><input type="text" value={form.post_topics} onChange={(e) => setForm({ ...form, post_topics: e.target.value })} /></div>
          <div className="field full"><label>Notes — what are they doing better?</label><textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
        </div>
        <div className="form-actions"><button className="btn primary" onClick={add}>Add competitor</button></div>
      </div>

      <div className="card">
        <h3>Tracked competitors <span className="sub">{comps.length}</span></h3>
        {comps.length === 0 ? (
          <EmptyState title="No competitors tracked" text="Add them manually or look them up with DataForSEO." />
        ) : (
          <div className="table-wrap"><table>
            <thead><tr><th>Name</th><th>Rating</th><th>Reviews</th><th>Categories</th><th>Posting</th><th>Services</th><th>Offers</th><th>Post topics</th><th>Notes</th><th>Source</th><th></th></tr></thead>
            <tbody>
              {comps.map((c) => (
                <tr key={c.id}>
                  <td><strong>{c.maps_url ? <a href={c.maps_url} target="_blank" rel="noreferrer">{c.name}</a> : c.name}</strong></td>
                  <td>{c.rating || '—'}</td>
                  <td>{c.review_count || '—'}</td>
                  <td className="muted">{c.categories || '—'}</td>
                  <td className="muted">{c.posting_freq || '—'}</td>
                  <td className="muted">{c.services || '—'}</td>
                  <td className="muted">{c.offers || '—'}</td>
                  <td className="muted">{c.post_topics || '—'}</td>
                  <td className="muted">{c.notes || '—'}</td>
                  <td><Badge value={c.source} /></td>
                  <td><button className="btn small danger" onClick={() => remove(c.id)}>Remove</button></td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </div>
    </>
  )
}
