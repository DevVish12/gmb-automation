import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { Alert, Badge, ConnDot, EmptyState, Loading, Modal, PageHeader } from '../components/ui'

const emptyForm = { name: '', business_name: '', city: '', phone: '', website: '', category: '', services: '' }

export default function Clients() {
  const [clients, setClients] = useState(null)
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [editing, setEditing] = useState(null)
  const [editForm, setEditForm] = useState({})

  const load = () => api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  useEffect(() => { load() }, [])

  const flash = (fn) => async (...a) => {
    setErr(''); setOk('')
    try { const r = await fn(...a); if (r) setOk(r); load() }
    catch (e) { setErr(e.message) }
  }

  const addClient = flash(async () => {
    if (!form.name.trim()) throw new Error('Client name is required.')
    await api.post('/clients', { ...form, services: form.services.split(',').map((s) => s.trim()).filter(Boolean) })
    setShowAdd(false); setForm(emptyForm)
    return 'Client added.'
  })

  const saveEdit = flash(async () => {
    await api.patch(`/clients/${editing.slug}`, {
      ...editForm,
      services: typeof editForm.services === 'string'
        ? editForm.services.split(',').map((s) => s.trim()).filter(Boolean)
        : editForm.services,
    })
    setEditing(null)
    return 'Client updated.'
  })

  const connect = flash(async (slug) => {
    const d = await api.get(`/connect/${slug}`)
    const w = window.open(d.authorization_url, 'gmb_oauth', 'width=560,height=640')
    if (!w) throw new Error('Popup blocked — please allow popups for this page.')
    await new Promise((resolve) => {
      const h = (e) => { if (e.data === 'gmb-oauth-done') { window.removeEventListener('message', h); resolve() } }
      window.addEventListener('message', h)
      const t = setInterval(() => { if (w.closed) { clearInterval(t); window.removeEventListener('message', h); resolve() } }, 800)
      setTimeout(() => { clearInterval(t); window.removeEventListener('message', h); resolve() }, 120000)
    })
    return 'Google connection attempted — check the status below.'
  })

  const disconnect = flash(async (slug) => {
    await api.post(`/disconnect/${slug}`)
    return 'Disconnected.'
  })

  const removeClient = flash(async (c) => {
    if (!window.confirm(`Delete client "${c.business_name || c.name}"?\n\nThis permanently removes ALL local data: drafts, keywords, reviews, media queue, calendar, audit, reports and activity history.\n\nContent already published to Google is NOT removed — delete that manually from the Business Profile.`)) return null
    if (!window.confirm('Last warning — this cannot be undone. Delete this client?')) return null
    const d = await api.del(`/clients/${c.slug}`)
    const n = Object.entries(d.removed || {}).filter(([, v]) => v > 0).map(([k, v]) => `${v} ${k}`).join(', ')
    return `Client deleted.${n ? ' Removed: ' + n + '.' : ''}`
  })

  const toggleAuto = flash(async (slug, val) => {
    if (val && !window.confirm('Auto-publish means approved posts go live on Google WITHOUT you reviewing each one. Are you sure?')) return null
    await api.post(`/clients/${slug}/autopublish`, { auto_publish: val })
    return val ? 'Auto-publish ON for this client.' : 'Auto-publish OFF.'
  })

  if (!clients) return <Loading />

  return (
    <>
      <PageHeader
        title="Clients"
        subtitle="Every business you manage. Connect each client's Google account once — then audits, posts, reviews and reports can run automatically."
        actions={<button className="btn primary" onClick={() => setShowAdd(true)}>+ Add client</button>}
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      {clients.length === 0 ? (
        <EmptyState title="No clients yet" text="Add your first client to start. Nothing connects to Google until you say so." action={<button className="btn primary" onClick={() => setShowAdd(true)}>+ Add client</button>} />
      ) : (
        <div className="card"><div className="table-wrap"><table>
          <thead><tr><th>Client</th><th>Location</th><th>Google</th><th>Approvals</th><th>Auto-publish</th><th></th></tr></thead>
          <tbody>
            {clients.map((c) => {
              const p = c.pending || {}
              const pend = (p.posts || 0) + (p.replies || 0) + (p.media || 0) + (p.qa || 0)
              return (
                <tr key={c.slug}>
                  <td><strong>{c.business_name || c.name}</strong><br /><span className="muted">{c.category || '—'}</span></td>
                  <td>{c.city || '—'}<br /><span className="muted">{c.phone || ''}</span></td>
                  <td><ConnDot connected={c.connected} /></td>
                  <td>{pend > 0 ? <Badge value={`${pend} waiting`} tone="amber" /> : <span className="muted">none</span>}</td>
                  <td>
                    <label className="checkbox-row">
                      <input type="checkbox" checked={!!c.auto_publish} onChange={(e) => toggleAuto(c.slug, e.target.checked)} />
                      <span className="muted">{c.auto_publish ? 'On' : 'Off'}</span>
                    </label>
                  </td>
                  <td><div className="row-actions">
                    {c.connected
                      ? <button className="btn small" onClick={() => disconnect(c.slug)}>Disconnect</button>
                      : <button className="btn small primary" onClick={() => connect(c.slug)}>Connect Google</button>}
                    <button className="btn small" onClick={() => {
                      setEditing(c)
                      setEditForm({ ...c, services: (c.services || []).join(', ') })
                    }}>Edit</button>
                    <button className="btn small danger" onClick={() => removeClient(c)}>Delete</button>
                  </div></td>
                </tr>
              )
            })}
          </tbody>
        </table></div></div>
      )}

      {showAdd && (
        <Modal title="Add client" onClose={() => setShowAdd(false)}>
          <div className="form-grid">
            <div className="field"><label>Client name *</label><input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Sharma Dental Clinic" /></div>
            <div className="field"><label>Business name</label><input type="text" value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} placeholder="As shown on Google" /></div>
            <div className="field"><label>City</label><input type="text" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
            <div className="field"><label>Phone</label><input type="text" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
            <div className="field"><label>Website</label><input type="text" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} /></div>
            <div className="field"><label>Primary category</label><input type="text" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="e.g. Dental clinic" /></div>
            <div className="field full"><label>Services (comma separated)</label><input type="text" value={form.services} onChange={(e) => setForm({ ...form, services: e.target.value })} placeholder="Root Canal, Braces, Teeth Cleaning" /></div>
          </div>
          <div className="form-actions">
            <button className="btn primary" onClick={addClient}>Add client</button>
            <button className="btn" onClick={() => setShowAdd(false)}>Cancel</button>
          </div>
        </Modal>
      )}

      {editing && (
        <Modal title={`Edit — ${editing.business_name || editing.name}`} onClose={() => setEditing(null)}>
          <div className="form-grid">
            <div className="field"><label>Business name</label><input type="text" value={editForm.business_name || ''} onChange={(e) => setEditForm({ ...editForm, business_name: e.target.value })} /></div>
            <div className="field"><label>Category</label><input type="text" value={editForm.category || ''} onChange={(e) => setEditForm({ ...editForm, category: e.target.value })} /></div>
            <div className="field"><label>City</label><input type="text" value={editForm.city || ''} onChange={(e) => setEditForm({ ...editForm, city: e.target.value })} /></div>
            <div className="field"><label>Phone</label><input type="text" value={editForm.phone || ''} onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} /></div>
            <div className="field"><label>Website</label><input type="text" value={editForm.website || ''} onChange={(e) => setEditForm({ ...editForm, website: e.target.value })} /></div>
            <div className="field"><label>Google Account ID</label><input type="text" value={editForm.account_id || ''} onChange={(e) => setEditForm({ ...editForm, account_id: e.target.value })} /></div>
            <div className="field"><label>Google Location ID</label><input type="text" value={editForm.location_id || ''} onChange={(e) => setEditForm({ ...editForm, location_id: e.target.value })} /><span className="hint">Found after connecting — needed for live publishing.</span></div>
            <div className="field full"><label>Services (comma separated)</label><input type="text" value={editForm.services || ''} onChange={(e) => setEditForm({ ...editForm, services: e.target.value })} /></div>
          </div>
          <div className="form-actions">
            <button className="btn primary" onClick={saveEdit}>Save</button>
            <button className="btn" onClick={() => setEditing(null)}>Cancel</button>
          </div>
        </Modal>
      )}
    </>
  )
}
