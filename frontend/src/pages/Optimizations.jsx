import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, ClientPicker, EmptyState, Loading, PageHeader, useClient } from '../components/ui'

const TYPE_LABEL = { category: 'Category', service: 'Service', description: 'Description' }
const STATUSES = ['proposed', 'approved', 'applied', 'rejected']

export default function Optimizations() {
  const [clients, setClients] = useState(null)
  const [slug, pick] = useClient(clients || [])
  const [opts, setOpts] = useState([])
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [form, setForm] = useState({ opt_type: 'category', item_name: '', current_value: '', proposed_value: '', keywords: '', priority: 'Medium', notes: '' })

  useEffect(() => {
    api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  }, [])

  const load = () => {
    if (!slug) return
    api.get(`/optimizations/${slug}`).then((d) => setOpts(d.optimizations)).catch((e) => setErr(e.message))
  }
  useEffect(load, [slug])

  const wrap = (fn) => async (...a) => {
    setErr(''); setOk('')
    try { const r = await fn(...a); if (r) setOk(r); load() }
    catch (e) { setErr(e.message) }
  }

  const add = wrap(async () => {
    if (!form.item_name.trim() || !form.proposed_value.trim()) throw new Error('Item name and proposed value are required.')
    await api.post(`/optimizations/${slug}`, form)
    setForm({ opt_type: 'category', item_name: '', current_value: '', proposed_value: '', keywords: '', priority: 'Medium', notes: '' })
    return 'Optimization proposal added.'
  })

  const setStatus = wrap(async (id, status) => {
    await api.patch(`/optimizations/${slug}/${id}`, { status })
    return `Status → ${status}.`
  })

  const remove = wrap(async (id) => {
    if (!window.confirm('Delete this proposal?')) return null
    await api.del(`/optimizations/${slug}/${id}`)
    return 'Deleted.'
  })

  if (clients === null && !err) return <Loading />
  if (err) return <><PageHeader title="Optimization" /><Alert kind="error">{err}</Alert></>
  if (!clients.length) return <><PageHeader title="Optimization" /><EmptyState title="No clients yet" text="Add your first client to start using this page." action={<Link to="/clients" className="btn primary">Add client →</Link>} /></>

  const groups = ['category', 'service', 'description']

  return (
    <>
      <PageHeader
        title="Optimization"
        subtitle="Category, service and description improvements — proposed here, approved by a human, then applied on Google by hand. The tool never changes the live profile on its own."
        actions={<ClientPicker clients={clients} value={slug} onChange={pick} />}
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      <div className="card">
        <h3>Propose an optimization</h3>
        <div className="form-grid">
          <div className="field"><label>Type</label>
            <select value={form.opt_type} onChange={(e) => setForm({ ...form, opt_type: e.target.value })}>
              {groups.map((t) => <option key={t} value={t}>{TYPE_LABEL[t]}</option>)}
            </select></div>
          <div className="field"><label>Item name *</label><input type="text" value={form.item_name} onChange={(e) => setForm({ ...form, item_name: e.target.value })} placeholder="e.g. Primary category, Root Canal, Business description" /></div>
          <div className="field"><label>Current value</label><input type="text" value={form.current_value} onChange={(e) => setForm({ ...form, current_value: e.target.value })} /></div>
          <div className="field"><label>Proposed value *</label><input type="text" value={form.proposed_value} onChange={(e) => setForm({ ...form, proposed_value: e.target.value })} /></div>
          <div className="field"><label>Keywords</label><input type="text" value={form.keywords} onChange={(e) => setForm({ ...form, keywords: e.target.value })} placeholder="comma separated" /></div>
          <div className="field"><label>Priority</label>
            <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
              {['High', 'Medium', 'Low'].map((p) => <option key={p} value={p}>{p}</option>)}
            </select></div>
          <div className="field full"><label>Notes</label><input type="text" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
        </div>
        <div className="form-actions"><button className="btn primary" onClick={add}>Add proposal</button></div>
      </div>

      {groups.map((t) => {
        const mine = opts.filter((o) => o.opt_type === t)
        return (
          <div className="card" key={t}>
            <h3>{TYPE_LABEL[t]} optimization <span className="sub">{mine.length}</span></h3>
            {mine.length === 0 ? (
              <EmptyState title={`No ${t} proposals`} text="Add one above — every proposal needs human approval before it is applied." />
            ) : (
              <div className="table-wrap"><table>
                <thead><tr><th>Item</th><th>Current</th><th>Proposed</th><th>Keywords</th><th>Priority</th><th>Status</th><th>Move to</th><th></th></tr></thead>
                <tbody>
                  {mine.map((o) => (
                    <tr key={o.id}>
                      <td><strong>{o.item_name}</strong>{o.notes && <><br /><span className="muted">{o.notes}</span></>}</td>
                      <td className="muted">{o.current_value || '—'}</td>
                      <td>{o.proposed_value}</td>
                      <td className="muted">{o.keywords || '—'}</td>
                      <td><Badge value={o.priority} /></td>
                      <td><Badge value={o.status} /></td>
                      <td>
                        <select defaultValue="" onChange={(e) => { if (e.target.value) setStatus(o.id, e.target.value) }} style={{ minWidth: 120 }}>
                          <option value="">—</option>
                          {STATUSES.filter((s) => s !== o.status).map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                      </td>
                      <td><button className="btn small danger" onClick={() => remove(o.id)}>Delete</button></td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            )}
          </div>
        )
      })}
    </>
  )
}
