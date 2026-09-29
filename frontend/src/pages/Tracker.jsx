import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, ClientPicker, EmptyState, Loading, PageHeader } from '../components/ui'

export default function Tracker() {
  const [clients, setClients] = useState(null)
  const [acts, setActs] = useState([])
  const [statuses, setStatuses] = useState([])
  const [fClient, setFClient] = useState('')
  const [fStatus, setFStatus] = useState('')
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [form, setForm] = useState({ client_slug: '', activity: '', area: '', owner: '', due_date: '', notes: '' })

  useEffect(() => {
    api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  }, [])

  const load = () => {
    const q = `?client_slug=${encodeURIComponent(fClient)}&status=${encodeURIComponent(fStatus)}`
    api.get(`/tracker${q}`).then((d) => { setActs(d.activities); setStatuses(d.statuses) }).catch((e) => setErr(e.message))
  }
  useEffect(load, [fClient, fStatus])

  const wrap = (fn) => async (...a) => {
    setErr(''); setOk('')
    try { const r = await fn(...a); if (r) setOk(r); load() }
    catch (e) { setErr(e.message) }
  }

  const add = wrap(async () => {
    if (!form.activity.trim()) throw new Error('Describe the activity.')
    await api.post('/tracker', { ...form, client_slug: form.client_slug || fClient })
    setForm({ client_slug: '', activity: '', area: '', owner: '', due_date: '', notes: '' })
    return 'Activity logged.'
  })

  const transition = wrap(async (id, status) => {
    const d = await api.post(`/tracker/${id}/transition`, { status })
    if (!d.ok) throw new Error(d.message)
    return d.message
  })

  if (clients === null && !err) return <Loading />
  if (err) return <><PageHeader title="Activity Tracker" /><Alert kind="error">{err}</Alert></>
  if (!clients.length) return <><PageHeader title="Activity Tracker" /><EmptyState title="No clients yet" text="Add your first client to start using this page." action={<Link to="/clients" className="btn primary">Add client →</Link>} /></>

  return (
    <>
      <PageHeader
        title="Activity Tracker"
        subtitle="The master log of everything done for every client. Each item moves through Pending → In Progress → Ready for QA → Approved → Scheduled → Published → Verified — skips are blocked."
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      <div className="card">
        <h3>Log activity</h3>
        <div className="form-grid">
          <div className="field"><label>Client</label>
            <select value={form.client_slug} onChange={(e) => setForm({ ...form, client_slug: e.target.value })}>
              <option value="">—</option>
              {clients.map((c) => <option key={c.slug} value={c.slug}>{c.business_name || c.name}</option>)}
            </select></div>
          <div className="field"><label>Area</label><input type="text" value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })} placeholder="e.g. Posts, Reviews, Audit" /></div>
          <div className="field full"><label>Activity *</label><input type="text" value={form.activity} onChange={(e) => setForm({ ...form, activity: e.target.value })} placeholder="What was done / needs doing" /></div>
          <div className="field"><label>Owner</label><input type="text" value={form.owner} onChange={(e) => setForm({ ...form, owner: e.target.value })} /></div>
          <div className="field"><label>Due date</label><input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} /></div>
          <div className="field full"><label>Notes</label><input type="text" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
        </div>
        <div className="form-actions"><button className="btn primary" onClick={add}>Log activity</button></div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'end', marginBottom: 12 }}>
          <div className="field" style={{ margin: 0 }}><label>Client</label>
            <select value={fClient} onChange={(e) => setFClient(e.target.value)}>
              <option value="">All clients</option>
              {clients.map((c) => <option key={c.slug} value={c.slug}>{c.business_name || c.name}</option>)}
            </select></div>
          <div className="field" style={{ margin: 0 }}><label>Status</label>
            <select value={fStatus} onChange={(e) => setFStatus(e.target.value)}>
              <option value="">All statuses</option>
              {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
            </select></div>
        </div>
        {acts.length === 0 ? (
          <EmptyState title="Nothing logged" text="Activity appears here as you work — or log one manually above." />
        ) : (
          <div className="table-wrap"><table>
            <thead><tr><th>Activity</th><th>Client</th><th>Area</th><th>Owner</th><th>Due</th><th>Status</th><th>Move to</th></tr></thead>
            <tbody>
              {acts.map((a) => (
                <tr key={a.id}>
                  <td><strong>{a.activity}</strong>{a.notes && <><br /><span className="muted">{a.notes}</span></>}</td>
                  <td className="muted">{a.client_slug}</td>
                  <td><Badge value={a.area || '—'} tone={a.area ? 'indigo' : 'slate'} /></td>
                  <td>{a.owner || '—'}</td>
                  <td>{a.due_date || '—'}</td>
                  <td><Badge value={a.status} /></td>
                  <td>
                    <select defaultValue="" onChange={(e) => { if (e.target.value) transition(a.id, e.target.value) }} style={{ minWidth: 130 }}>
                      <option value="">—</option>
                      {statuses.filter((s) => s !== a.status).map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </div>
    </>
  )
}
