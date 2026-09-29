import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, ConnDot, Loading, PageHeader, Stat } from '../components/ui'

export default function Dashboard() {
  const [status, setStatus] = useState(null)
  const [clients, setClients] = useState([])
  const [activity, setActivity] = useState([])
  const [err, setErr] = useState('')

  useEffect(() => {
    Promise.all([
      api.get('/status').catch((e) => { throw e }),
      api.get('/clients'),
      api.get('/tracker'),
    ]).then(([s, c, t]) => {
      setStatus(s); setClients(c.clients); setActivity(t.activities.slice(0, 8))
    }).catch((e) => setErr(e.message))
  }, [])

  if (err) return <><PageHeader title="Dashboard" /><Alert kind="error">{err}</Alert></>
  if (!status) return <Loading />

  const scheduled = clients.reduce((n, c) => n + (c.scheduled || 0), 0)
  const connected = clients.filter((c) => c.connected).length

  const steps = [
    { label: 'Add your first client', done: clients.length > 0, to: '/clients' },
    { label: 'Run a profile audit', done: activity.some((a) => a.area === 'Audit'), to: '/audit' },
    { label: 'Generate the content calendar', done: activity.some((a) => a.area === 'Posts'), to: '/calendar' },
    { label: 'Connect Google for live publishing', done: connected > 0, to: '/help' },
  ]

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="One place to see every client's Google Business Profile work — what's drafted, what's waiting for approval, and what's live."
      />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Stat label="Clients" value={clients.length} sub={`${connected} Google-connected`} />
        <Stat label="Pending approvals" value={status.pending_total} sub="Posts, replies, QA items" />
        <Stat label="Scheduled posts" value={scheduled} sub="Waiting to publish" />
        <Stat label="Mode" value={status.dry_run ? 'Dry-run' : 'Live'} sub={status.dry_run ? 'Nothing publishes yet' : 'Publishing is active'} />
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h3>Clients</h3>
          {clients.length === 0 ? (
            <p className="muted">No clients yet. <Link to="/clients">Add your first client →</Link></p>
          ) : (
            <div className="table-wrap"><table>
              <thead><tr><th>Client</th><th>Connection</th><th>Drafts</th><th>Scheduled</th></tr></thead>
              <tbody>
                {clients.map((c) => (
                  <tr key={c.slug}>
                    <td><Link to={`/audit?client=${c.slug}`}><strong>{c.business_name || c.name}</strong></Link><br /><span className="muted">{c.city}</span></td>
                    <td><ConnDot connected={c.connected} /></td>
                    <td>{c.drafts || 0}</td>
                    <td>{c.scheduled || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
        </div>
        <div>
          <div className="card">
            <h3>Getting started</h3>
            <ul className="checklist">
              {steps.map((s, i) => (
                <li key={i}>
                  <span className={`check ${s.done ? 'done' : 'todo'}`}>{s.done ? '✓' : ''}</span>
                  <span>{s.done ? s.label : <Link to={s.to}>{s.label} →</Link>}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="card">
            <h3>Recent activity</h3>
            {activity.length === 0
              ? <p className="muted">Nothing logged yet — activity appears here as you work.</p>
              : <ul className="checklist">{activity.map((a) => (
                  <li key={a.id}>
                    <span style={{ flex: 1 }}>{a.activity}<br /><span className="muted">{a.client_slug} · {a.area}</span></span>
                    <Badge value={a.status} />
                  </li>
                ))}</ul>}
          </div>
        </div>
      </div>
    </>
  )
}
