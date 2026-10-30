import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, ClientPicker, EmptyState, Loading, PageHeader, useClient } from '../components/ui'

const TYPES = ['primary', 'secondary', 'service', 'location', 'service-location', 'long-tail', 'intent', 'commercial', 'supporting', 'competitor']

export default function Keywords() {
  const [clients, setClients] = useState(null)
  const [slug, pick] = useClient(clients || [])
  const [kws, setKws] = useState([])
  const [dfsOn, setDfsOn] = useState(false)
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [form, setForm] = useState({ keyword: '', ktype: 'secondary', mapped_to: '', volume: '' })
  const [dfsForm, setDfsForm] = useState({ seed: '', location: '' })
  const [editId, setEditId] = useState(null)
  const [edit, setEdit] = useState({})

  useEffect(() => {
    api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  }, [])

  const load = () => {
    if (!slug) return
    api.get(`/keywords/${slug}`).then((d) => { setKws(d.keywords); setDfsOn(d.dataforseo_on) }).catch((e) => setErr(e.message))
  }
  useEffect(load, [slug])

  const wrap = (fn) => async (...a) => {
    setErr(''); setOk('')
    try { const r = await fn(...a); if (r) setOk(r); load() }
    catch (e) { setErr(e.message) }
  }

  const add = wrap(async () => {
    if (!form.keyword.trim()) throw new Error('Keyword is required.')
    await api.post(`/keywords/${slug}`, form)
    setForm({ keyword: '', ktype: 'secondary', mapped_to: '', volume: '' })
    return 'Keyword added.'
  })

  const saveEdit = wrap(async () => {
    await api.patch(`/keywords/${slug}/${editId}`, edit)
    setEditId(null)
    return 'Keyword updated.'
  })

  const remove = wrap(async (id) => {
    if (!window.confirm('Delete this keyword?')) return null
    await api.del(`/keywords/${slug}/${id}`)
    return 'Deleted.'
  })

  const fetchDfs = wrap(async () => {
    const d = await api.post(`/keywords/${slug}/dataforseo`, dfsForm)
    return `${d.added} keyword ideas added from DataForSEO.`
  })

  if (clients === null && !err) return <Loading />
  if (err) return <><PageHeader title="Keywords" /><Alert kind="error">{err}</Alert></>
  if (!clients.length) return <><PageHeader title="Keywords" /><EmptyState title="No clients yet" text="Add your first client to start using this page." action={<Link to="/clients" className="btn primary">Add client →</Link>} /></>

  return (
    <>
      <PageHeader
        title="Keywords"
        subtitle="What customers actually search for — organized by type and mapped to the services and profile sections they belong to."
        actions={<ClientPicker clients={clients} value={slug} onChange={pick} />}
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      <div className="card">
        <h3>Add keyword</h3>
        <div className="form-grid">
          <div className="field"><label>Keyword *</label><input type="text" value={form.keyword} onChange={(e) => setForm({ ...form, keyword: e.target.value })} placeholder="e.g. dentist in Noida" /></div>
          <div className="field"><label>Type</label><select value={form.ktype} onChange={(e) => setForm({ ...form, ktype: e.target.value })}>{TYPES.map((t) => <option key={t} value={t}>{t}</option>)}</select></div>
          <div className="field"><label>Mapped to</label><input type="text" value={form.mapped_to} onChange={(e) => setForm({ ...form, mapped_to: e.target.value })} placeholder="Service / category / post topic" /></div>
          <div className="field"><label>Search volume</label><input type="text" value={form.volume} onChange={(e) => setForm({ ...form, volume: e.target.value })} placeholder="e.g. 1200" /></div>
        </div>
        <div className="form-actions"><button className="btn primary" onClick={add}>Add keyword</button></div>
      </div>

      <div className="card">
        <h3>Keyword ideas <span className="sub">Powered by DataForSEO — needs API credentials in Settings</span></h3>
        {dfsOn ? (
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'end' }}>
            <div className="field" style={{ margin: 0 }}><label>Seed word</label><input type="text" value={dfsForm.seed} onChange={(e) => setDfsForm({ ...dfsForm, seed: e.target.value })} placeholder="e.g. dental clinic" /></div>
            <div className="field" style={{ margin: 0 }}><label>Location</label><input type="text" value={dfsForm.location} onChange={(e) => setDfsForm({ ...dfsForm, location: e.target.value })} placeholder="e.g. Noida,India" /></div>
            <button className="btn" onClick={fetchDfs}>Fetch ideas</button>
          </div>
        ) : <p className="muted">DataForSEO is not configured — add keywords manually, or set it up in Settings.</p>}
      </div>

      <div className="card">
        <h3>Keyword list <span className="sub">{kws.length} keywords</span></h3>
        {kws.length === 0 ? (
          <EmptyState title="No keywords yet" text="Add keywords above — they feed the content calendar and post topics." />
        ) : (
          <div className="table-wrap"><table>
            <thead><tr><th>Keyword</th><th>Type</th><th>Mapped to</th><th>Volume</th><th></th></tr></thead>
            <tbody>
              {kws.map((k) => (
                <tr key={k.id}>
                  {editId === k.id ? (
                    <>
                      <td><input type="text" value={edit.keyword} onChange={(e) => setEdit({ ...edit, keyword: e.target.value })} /></td>
                      <td><select value={edit.ktype} onChange={(e) => setEdit({ ...edit, ktype: e.target.value })}>{TYPES.map((t) => <option key={t} value={t}>{t}</option>)}</select></td>
                      <td><input type="text" value={edit.mapped_to} onChange={(e) => setEdit({ ...edit, mapped_to: e.target.value })} /></td>
                      <td><input type="text" value={edit.volume} onChange={(e) => setEdit({ ...edit, volume: e.target.value })} /></td>
                      <td><div className="row-actions"><button className="btn small primary" onClick={saveEdit}>Save</button><button className="btn small" onClick={() => setEditId(null)}>Cancel</button></div></td>
                    </>
                  ) : (
                    <>
                      <td><strong>{k.keyword}</strong></td>
                      <td><Badge value={k.ktype} /></td>
                      <td>{k.mapped_to || <span className="muted">—</span>}</td>
                      <td>{k.volume || <span className="muted">—</span>}</td>
                      <td><div className="row-actions"><button className="btn small" onClick={() => { setEditId(k.id); setEdit({ keyword: k.keyword, ktype: k.ktype, mapped_to: k.mapped_to, volume: k.volume }) }}>Edit</button><button className="btn small danger" onClick={() => remove(k.id)}>Delete</button></div></td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </div>
    </>
  )
}
