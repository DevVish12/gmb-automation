import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, ClientPicker, EmptyState, Loading, PageHeader, useClient } from '../components/ui'

export default function Media() {
  const [clients, setClients] = useState(null)
  const [slug, pick] = useClient(clients || [])
  const [items, setItems] = useState([])
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [form, setForm] = useState({ kind: 'photo', note: '', caption: '', file_url: '', scheduled_date: '' })

  useEffect(() => {
    api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  }, [])

  const load = () => {
    if (!slug) return
    api.get(`/media/${slug}`).then((d) => setItems(d.items)).catch((e) => setErr(e.message))
  }
  useEffect(load, [slug])

  const wrap = (fn) => async (...a) => {
    setErr(''); setOk('')
    try { const r = await fn(...a); if (r) setOk(r); load() }
    catch (e) { setErr(e.message) }
  }

  const add = wrap(async () => {
    if (!form.note.trim()) throw new Error('Give this media a short note/label.')
    await api.post(`/media/${slug}`, form)
    setForm({ kind: 'photo', note: '', caption: '', file_url: '', scheduled_date: '' })
    return 'Added to the upload queue.'
  })

  const publish = wrap(async (id) => {
    if (!window.confirm('Upload this to Google now?')) return null
    const d = await api.post(`/media/${slug}/${id}/publish`)
    if (!d.ok) throw new Error(d.message)
    return d.message || 'Uploaded.'
  })

  if (clients === null && !err) return <Loading />
  if (err) return <><PageHeader title="Photos & Videos" /><Alert kind="error">{err}</Alert></>
  if (!clients.length) return <><PageHeader title="Photos & Videos" /><EmptyState title="No clients yet" text="Add your first client to start using this page." action={<Link to="/clients" className="btn primary">Add client →</Link>} /></>

  return (
    <>
      <PageHeader
        title="Photos & Videos"
        subtitle="Plan the visual content calendar — real business photos and videos keep the profile active and trustworthy."
        actions={<ClientPicker clients={clients} value={slug} onChange={pick} />}
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>
      <Alert kind="info">Google needs a <strong>publicly hosted file URL</strong> for uploads (e.g. an image already on the business website). Direct file upload from your computer isn’t supported by Google’s API.</Alert>

      <div className="card">
        <h3>Queue media</h3>
        <div className="form-grid">
          <div className="field"><label>Type</label>
            <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
              <option value="photo">Photo</option><option value="video">Video</option>
            </select></div>
          <div className="field"><label>Label / note *</label><input type="text" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} placeholder="e.g. Shop front, Team photo" /></div>
          <div className="field"><label>Caption</label><input type="text" value={form.caption} onChange={(e) => setForm({ ...form, caption: e.target.value })} /></div>
          <div className="field"><label>Planned date</label><input type="date" value={form.scheduled_date} onChange={(e) => setForm({ ...form, scheduled_date: e.target.value })} /></div>
          <div className="field full"><label>Public file URL</label><input type="text" value={form.file_url} onChange={(e) => setForm({ ...form, file_url: e.target.value })} placeholder="https://…" /></div>
        </div>
        <div className="form-actions"><button className="btn primary" onClick={add}>Add to queue</button></div>
      </div>

      <div className="card">
        <h3>Upload queue <span className="sub">{items.length} items</span></h3>
        {items.length === 0 ? (
          <EmptyState title="Nothing queued" text="Add photos and videos above to plan the visual calendar." />
        ) : (
          <div className="table-wrap"><table>
            <thead><tr><th>Label</th><th>Type</th><th>Caption</th><th>URL</th><th>Date</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {items.map((m) => (
                <tr key={m.id}>
                  <td><strong>{m.note}</strong></td>
                  <td><Badge value={m.kind} tone="indigo" /></td>
                  <td className="muted">{m.caption || '—'}</td>
                  <td>{m.file_url ? <a href={m.file_url} target="_blank" rel="noreferrer">link</a> : <span className="muted">—</span>}</td>
                  <td>{m.scheduled_date || '—'}</td>
                  <td><Badge value={m.status} /></td>
                  <td>{m.status !== 'published' && <button className="btn small success" onClick={() => publish(m.id)}>Upload</button>}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </div>
    </>
  )
}
