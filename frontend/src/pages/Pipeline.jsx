import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Alert, Badge, ClientPicker, EmptyState, Loading, PageHeader, Stat, useClient } from '../components/ui'

const TONE = { done: 'green', 'in-progress': 'amber', 'not-started': 'slate' }
const LABEL = { done: 'Done', 'in-progress': 'In progress', 'not-started': 'Not started' }

export default function Pipeline() {
  const [clients, setClients] = useState(null)
  const [slug, pick] = useClient(clients || [])
  const [pl, setPl] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  }, [])

  useEffect(() => {
    if (!slug) return
    api.get(`/pipeline/${slug}`).then(setPl).catch((e) => setErr(e.message))
  }, [slug])

  if (clients === null && !err) return <Loading />
  if (err) return <><PageHeader title="Pipeline" /><Alert kind="error">{err}</Alert></>
  if (!clients.length) return <><PageHeader title="Pipeline" /><EmptyState title="No clients yet" text="Add your first client to start using this page." action={<Link to="/clients" className="btn primary">Add client →</Link>} /></>

  return (
    <>
      <PageHeader
        title="Pipeline"
        subtitle="The full post-onboarding workflow in order — onboarding to reporting, then the next cycle. Every stage is derived from real work, not typed by hand."
        actions={<ClientPicker clients={clients} value={slug} onChange={pick} />}
      />
      <Alert kind="error">{err}</Alert>

      {pl && (
        <div className="grid cols-3" style={{ marginBottom: 16 }}>
          <Stat label="Stages done" value={`${pl.done}/${pl.total}`} sub="across the whole workflow" />
          <Stat label="In progress" value={pl.stages.filter((s) => s.state === 'in-progress').length} sub="stages with work underway" />
          <Stat label="Not started" value={pl.stages.filter((s) => s.state === 'not-started').length} sub="stages still waiting" />
        </div>
      )}

      <div className="card">
        {!pl ? <Loading /> : pl.stages.length === 0 ? (
          <EmptyState title="No pipeline data" text="Pick a client above." />
        ) : (
          <div className="table-wrap"><table>
            <thead><tr><th>#</th><th>Stage</th><th>Status</th><th>Detail</th></tr></thead>
            <tbody>
              {pl.stages.map((s, i) => (
                <tr key={s.key}>
                  <td className="muted">{i + 1}</td>
                  <td><strong>{s.title}</strong></td>
                  <td><Badge value={LABEL[s.state]} tone={TONE[s.state]} /></td>
                  <td className="muted">{s.detail}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </div>
    </>
  )
}
