import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, ClientPicker, EmptyState, Loading, PageHeader, useClient } from '../components/ui'

const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December']

export default function Calendar() {
  const [clients, setClients] = useState(null)
  const [slug, pick] = useClient(clients || [])
  const [slots, setSlots] = useState([])
  const [year, setYear] = useState(new Date().getFullYear())
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  }, [])

  useEffect(() => {
    if (!slug) return
    api.get(`/calendar/${slug}`).then((d) => {
      setSlots(d.slots || [])
      if (d.year) setYear(d.year)
      if (d.month) setMonth(d.month)
    }).catch((e) => setErr(e.message))
  }, [slug])

  const generate = async () => {
    setErr(''); setOk(''); setBusy(true)
    try {
      const d = await api.post(`/calendar/${slug}/generate`, { year: Number(year), month: Number(month) })
      setSlots(d.slots || [])
      setOk(`Calendar generated — ${d.slots.length} post slots for ${MONTHS[month - 1]} ${year}.`)
    } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  const queueAll = async () => {
    setErr(''); setOk('')
    try {
      const d = await api.post(`/calendar/${slug}/queue`)
      setOk(`${d.queued} drafts added to the Content Queue — review and approve them there.`)
    } catch (e) { setErr(e.message) }
  }

  if (clients === null && !err) return <Loading />
  if (err) return <><PageHeader title="Content Calendar" /><Alert kind="error">{err}</Alert></>
  if (!clients.length) return <><PageHeader title="Content Calendar" /><EmptyState title="No clients yet" text="Add your first client to start using this page." action={<Link to="/clients" className="btn primary">Add client →</Link>} /></>

  const weeks = {}
  slots.forEach((s) => {
    const w = s.week || 1
    ;(weeks[w] = weeks[w] || []).push(s)
  })

  return (
    <>
      <PageHeader
        title="Content Calendar"
        subtitle="A month of Google posts, planned in advance — 2 posts per week with a rotating mix of services, education, FAQs, offers and trust-building content."
        actions={<ClientPicker clients={clients} value={slug} onChange={pick} />}
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      <div className="card">
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'end' }}>
          <div className="field" style={{ margin: 0 }}><label>Month</label>
            <select value={month} onChange={(e) => setMonth(e.target.value)}>
              {MONTHS.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
            </select>
          </div>
          <div className="field" style={{ margin: 0 }}><label>Year</label>
            <input type="number" value={year} onChange={(e) => setYear(e.target.value)} style={{ width: 110 }} />
          </div>
          <button className="btn primary" disabled={busy} onClick={generate}>{busy ? 'Generating…' : 'Generate calendar'}</button>
          {slots.length > 0 && <button className="btn" onClick={queueAll}>Queue all as drafts →</button>}
        </div>
      </div>

      {slots.length === 0 ? (
        <EmptyState title="No calendar yet" text="Pick a month and generate — slots are created from your keywords and the weekly content mix." />
      ) : (
        Object.keys(weeks).sort().map((w) => (
          <div className="card" key={w}>
            <h3>Week {w}</h3>
            <div className="table-wrap"><table>
              <thead><tr><th>Date</th><th>Post type</th><th>Topic</th><th>Keyword</th><th>Description</th><th>Creative</th><th>Approval</th><th>Publishing</th></tr></thead>
              <tbody>
                {weeks[w].map((s, i) => (
                  <tr key={i}>
                    <td style={{ whiteSpace: 'nowrap' }}>{s.scheduled_date || s.date || '—'}</td>
                    <td><Badge value={s.post_type} tone="indigo" /></td>
                    <td>{s.topic}</td>
                    <td className="muted">{s.keyword || '—'}</td>
                    <td className="muted">{s.description_status || '—'}</td>
                    <td className="muted">{s.creative_status || '—'}</td>
                    <td><Badge value={s.approval_status || '—'} /></td>
                    <td><Badge value={s.publishing_status || '—'} /></td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </div>
        ))
      )}
    </>
  )
}
