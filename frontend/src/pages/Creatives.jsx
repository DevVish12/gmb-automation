import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, ClientPicker, EmptyState, Loading, Modal, PageHeader, useClient } from '../components/ui'

const emptyForm = { keyword: '', topic: '', headline: '', supporting_text: '', cta: '', brand_notes: '', visual_concept: '', offer_info: '' }

export default function Creatives() {
  const [clients, setClients] = useState(null)
  const [slug, pick] = useClient(clients || [])
  const [crs, setCrs] = useState([])
  const [qaItems, setQaItems] = useState([])
  const [posts, setPosts] = useState([])
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [fromPost, setFromPost] = useState('')
  const [qa, setQa] = useState({})
  const [editing, setEditing] = useState(null)
  const [edit, setEdit] = useState({})

  useEffect(() => {
    api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  }, [])

  const load = () => {
    if (!slug) return
    api.get(`/creatives/${slug}`).then((d) => {
      setCrs(d.creatives); setQaItems(d.qa_items || [])
      const q = {}
      d.creatives.forEach((c) => { try { q[c.id] = JSON.parse(c.qa_json || '{}') } catch { q[c.id] = {} } })
      setQa(q)
    }).catch((e) => setErr(e.message))
    api.get(`/queue/${slug}`).then((d) => setPosts(d.posts)).catch(() => {})
  }
  useEffect(load, [slug])

  const wrap = (fn) => async (...a) => {
    setErr(''); setOk('')
    try { const r = await fn(...a); if (r) setOk(r); load() }
    catch (e) { setErr(e.message) }
  }

  const add = wrap(async () => {
    if (!form.topic.trim()) throw new Error('Topic is required.')
    await api.post(`/creatives/${slug}`, form)
    setForm(emptyForm)
    return 'Creative brief added.'
  })

  const genFromPost = wrap(async () => {
    if (!fromPost) throw new Error('Pick a post first.')
    const d = await api.post(`/creatives/${slug}/from-post/${fromPost}`)
    setFromPost('')
    return `Brief generated from post and linked (brief #${d.id}).`
  })

  const saveQa = wrap(async (c) => {
    const checks = qa[c.id] || {}
    const passed = qaItems.length > 0 && qaItems.every(([k]) => checks[k])
    await api.patch(`/creatives/${slug}/${c.id}`, { qa_json: checks, qa_status: passed ? 'passed' : 'pending' })
    return passed ? 'QA passed — all 12 checks ticked.' : 'QA saved — some checks still open.'
  })

  const setStatus = wrap(async (c, field, value) => {
    await api.patch(`/creatives/${slug}/${c.id}`, { [field]: value })
    return `${field} → ${value}.`
  })

  const saveEdit = wrap(async () => {
    await api.patch(`/creatives/${slug}/${editing.id}`, edit)
    setEditing(null)
    return 'Brief updated.'
  })

  const remove = wrap(async (id) => {
    if (!window.confirm('Delete this creative brief?')) return null
    await api.del(`/creatives/${slug}/${id}`)
    return 'Deleted.'
  })

  if (clients === null && !err) return <Loading />
  if (err) return <><PageHeader title="Creative Briefs" /><Alert kind="error">{err}</Alert></>
  if (!clients.length) return <><PageHeader title="Creative Briefs" /><EmptyState title="No clients yet" text="Add your first client to start using this page." action={<Link to="/clients" className="btn primary">Add client →</Link>} /></>

  const toggleQa = (cid, key) => setQa({ ...qa, [cid]: { ...(qa[cid] || {}), [key]: !(qa[cid] || {})[key] } })

  return (
    <>
      <PageHeader
        title="Creative Briefs"
        subtitle="Every post graphic starts here — a brief from the post, then the 12-point QA checklist before anything is approved."
        actions={<ClientPicker clients={clients} value={slug} onChange={pick} />}
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      <div className="card">
        <h3>Generate brief from a post</h3>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'end' }}>
          <div className="field" style={{ margin: 0 }}><label>Post</label>
            <select value={fromPost} onChange={(e) => setFromPost(e.target.value)} style={{ minWidth: 280 }}>
              <option value="">— pick a queued post —</option>
              {posts.map((p) => <option key={p.id} value={p.id}>#{p.id} {p.topic}</option>)}
            </select></div>
          <button className="btn primary" onClick={genFromPost}>Generate brief →</button>
        </div>
      </div>

      <div className="card">
        <h3>New brief (manual)</h3>
        <div className="form-grid">
          <div className="field"><label>Target keyword</label><input type="text" value={form.keyword} onChange={(e) => setForm({ ...form, keyword: e.target.value })} /></div>
          <div className="field"><label>Post topic *</label><input type="text" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} /></div>
          <div className="field full"><label>Main headline</label><input type="text" value={form.headline} onChange={(e) => setForm({ ...form, headline: e.target.value })} /></div>
          <div className="field full"><label>Supporting text</label><textarea rows={2} value={form.supporting_text} onChange={(e) => setForm({ ...form, supporting_text: e.target.value })} /></div>
          <div className="field"><label>CTA</label><input type="text" value={form.cta} onChange={(e) => setForm({ ...form, cta: e.target.value })} /></div>
          <div className="field"><label>Business name / logo notes</label><input type="text" value={form.brand_notes} onChange={(e) => setForm({ ...form, brand_notes: e.target.value })} /></div>
          <div className="field full"><label>Visual concept</label><input type="text" value={form.visual_concept} onChange={(e) => setForm({ ...form, visual_concept: e.target.value })} /></div>
          <div className="field full"><label>Offer information</label><input type="text" value={form.offer_info} onChange={(e) => setForm({ ...form, offer_info: e.target.value })} /></div>
        </div>
        <div className="form-actions"><button className="btn primary" onClick={add}>Add brief</button></div>
      </div>

      {crs.length === 0 ? (
        <EmptyState title="No creative briefs" text="Generate one from a queued post, or write one manually above." />
      ) : crs.map((c) => {
        const checks = qa[c.id] || {}
        const done = qaItems.filter(([k]) => checks[k]).length
        return (
          <div className="card" key={c.id}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 8 }}>
              <Badge value={c.qa_status} tone={c.qa_status === 'passed' ? 'green' : 'amber'} />
              <Badge value={c.status} tone="indigo" />
              {c.post_id > 0 && <span className="muted" style={{ fontSize: 12.5 }}>linked post #{c.post_id}</span>}
              <span className="muted" style={{ fontSize: 12.5 }}>QA {done}/{qaItems.length}</span>
              <div className="row-actions" style={{ marginLeft: 'auto' }}>
                <button className="btn small" onClick={() => { setEditing(c); setEdit({ keyword: c.keyword, topic: c.topic, headline: c.headline, supporting_text: c.supporting_text, cta: c.cta, brand_notes: c.brand_notes, visual_concept: c.visual_concept, offer_info: c.offer_info }) }}>Edit</button>
                <button className="btn small danger" onClick={() => remove(c.id)}>Delete</button>
              </div>
            </div>
            <div style={{ fontWeight: 650, marginBottom: 4 }}>{c.topic || '—'}</div>
            {c.headline && <div style={{ fontSize: 13.5, marginBottom: 4 }}>{c.headline}</div>}
            <div className="muted" style={{ fontSize: 12.5 }}>
              {[c.keyword && `keyword: ${c.keyword}`, c.cta && `CTA: ${c.cta}`, c.offer_info && `offer: ${c.offer_info}`].filter(Boolean).join(' · ')}
            </div>
            <h3 style={{ marginTop: 14 }}>QA checklist — all 12 must pass</h3>
            <div className="form-grid">
              {qaItems.map(([key, label]) => (
                <label key={key} className="checkbox-row" style={{ margin: 0 }}>
                  <input type="checkbox" checked={!!checks[key]} onChange={() => toggleQa(c.id, key)} />
                  {label}
                </label>
              ))}
            </div>
            <div className="form-actions">
              <button className="btn primary" onClick={() => saveQa(c)}>Save QA</button>
              <select defaultValue="" onChange={(e) => { if (e.target.value) setStatus(c, 'status', e.target.value) }} style={{ minWidth: 130 }}>
                <option value="">Status…</option>
                {['draft', 'ready', 'used'].filter((s) => s !== c.status).map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
        )
      })}

      {editing && (
        <Modal title="Edit brief" onClose={() => setEditing(null)}>
          <div className="field"><label>Target keyword</label><input type="text" value={edit.keyword || ''} onChange={(e) => setEdit({ ...edit, keyword: e.target.value })} /></div>
          <div className="field"><label>Post topic</label><input type="text" value={edit.topic || ''} onChange={(e) => setEdit({ ...edit, topic: e.target.value })} /></div>
          <div className="field"><label>Main headline</label><input type="text" value={edit.headline || ''} onChange={(e) => setEdit({ ...edit, headline: e.target.value })} /></div>
          <div className="field"><label>Supporting text</label><textarea rows={2} value={edit.supporting_text || ''} onChange={(e) => setEdit({ ...edit, supporting_text: e.target.value })} /></div>
          <div className="field"><label>CTA</label><input type="text" value={edit.cta || ''} onChange={(e) => setEdit({ ...edit, cta: e.target.value })} /></div>
          <div className="field"><label>Business name / logo notes</label><input type="text" value={edit.brand_notes || ''} onChange={(e) => setEdit({ ...edit, brand_notes: e.target.value })} /></div>
          <div className="field"><label>Visual concept</label><input type="text" value={edit.visual_concept || ''} onChange={(e) => setEdit({ ...edit, visual_concept: e.target.value })} /></div>
          <div className="field"><label>Offer information</label><input type="text" value={edit.offer_info || ''} onChange={(e) => setEdit({ ...edit, offer_info: e.target.value })} /></div>
          <div className="form-actions">
            <button className="btn primary" onClick={saveEdit}>Save</button>
            <button className="btn" onClick={() => setEditing(null)}>Cancel</button>
          </div>
        </Modal>
      )}
    </>
  )
}
