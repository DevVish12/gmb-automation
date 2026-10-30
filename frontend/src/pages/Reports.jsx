import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, reportUrl } from '../api'
import { Alert, Badge, ClientPicker, ConnDot, EmptyState, Loading, PageHeader, Stat, useClient } from '../components/ui'

export default function Reports() {
  const [clients, setClients] = useState(null)
  const [slug, pick] = useClient(clients || [])
  const [client, setClient] = useState(null)
  const [reps, setReps] = useState([])
  const [perfKeys, setPerfKeys] = useState([])
  const [actKeys, setActKeys] = useState([])
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [busy, setBusy] = useState(false)
  const [perfLive, setPerfLive] = useState(null)
  const [f, setF] = useState({
    period_start: '', period_end: '', use_api: false,
    perf: {}, activity: {},
    seo: { keywords_targeted: '', new_opportunities: '', competitor_notes: '' },
    next_plan: { changes: '', keywords: '', services: '', topics: '', offers: '', visuals: '', optimizations: '' },
  })

  useEffect(() => {
    api.get('/clients').then((d) => setClients(d.clients)).catch((e) => setErr(e.message))
  }, [])

  const load = () => {
    if (!slug) return
    Promise.all([api.get(`/clients/${slug}`), api.get(`/reports/${slug}`)])
      .then(([c, r]) => {
        setClient(c.client); setReps(r.reports); setPerfKeys(r.perf_keys); setActKeys(r.act_keys)
        if (c.client?.connected) {
          setPerfLive({ state: 'loading' })
          api.get(`/reports/${slug}/performance`)
            .then((d) => setPerfLive({ state: 'ok', data: d }))
            .catch((e) => setPerfLive({ state: 'error', reason: e.message }))
        } else {
          setPerfLive(null)
        }
      })
      .catch((e) => setErr(e.message))
  }
  useEffect(load, [slug])

  const setP = (k, v) => setF({ ...f, perf: { ...f.perf, [k]: v } })
  const setA = (k, v) => setF({ ...f, activity: { ...f.activity, [k]: v } })
  const setS = (k, v) => setF({ ...f, seo: { ...f.seo, [k]: v } })
  const setN = (k, v) => setF({ ...f, next_plan: { ...f.next_plan, [k]: v } })

  const compile = async () => {
    setErr(''); setOk('')
    if (!f.period_start || !f.period_end) { setErr('Pick a period start and end date.'); return }
    setBusy(true)
    try {
      const d = await api.post(`/reports/${slug}/compile`, {
        period_start: f.period_start,
        period_end: f.period_end,
        use_api: f.use_api,
        perf: f.perf,
        activity: f.activity,
        seo: f.seo,
        next_plan: { ...f.next_plan, changes: f.next_plan.changes.split('\n').map((x) => x.trim()).filter(Boolean) },
      })
      setOk('Report compiled — opening it now.')
      window.open(reportUrl(d.id), '_blank')
      load()
    } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  if (clients === null && !err) return <Loading />
  if (err) return <><PageHeader title="Reports" /><Alert kind="error">{err}</Alert></>
  if (!clients.length) return <><PageHeader title="Reports" /><EmptyState title="No clients yet" text="Add your first client to start using this page." action={<Link to="/clients" className="btn primary">Add client →</Link>} /></>

  const pretty = (k) => k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

  return (
    <>
      <PageHeader
        title="Reports"
        subtitle="Bi-weekly or monthly client reports — profile performance, what was done, and the plan for next period. Numbers come from Google or your manual entry, always labeled."
        actions={<ClientPicker clients={clients} value={slug} onChange={pick} />}
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      {client?.connected && perfLive && (
        <div className="card">
          <h3>Historical performance — live from Google <span className="sub">Purana (old) SEO data, report compile kiye bina</span></h3>
          {perfLive.state === 'loading' && <Loading text="Google se live stats la rahe hain…" />}
          {perfLive.state === 'ok' && (
            <>
              <div className="grid cols-3" style={{ marginBottom: 12 }}>
                <Stat label="Profile views" value={perfLive.data.stats.impressions} sub="Search + Maps" />
                <Stat label="Search views" value={perfLive.data.stats.search_views} sub="Google Search" />
                <Stat label="Maps views" value={perfLive.data.stats.maps_views} sub="Google Maps" />
                <Stat label="Website clicks" value={perfLive.data.stats.website_clicks} sub="Website visits" />
                <Stat label="Calls" value={perfLive.data.stats.calls} sub="Call clicks" />
                <Stat label="Direction requests" value={perfLive.data.stats.directions} sub="Directions" />
              </div>
              <p className="muted">Period: {perfLive.data.period.start} → {perfLive.data.period.end} ({perfLive.data.days} days) · Source: <Badge value="API" /> Live from Google</p>
            </>
          )}
          {perfLive.state === 'error' && (
            <Alert kind="error">Live stats available nahi hain: {perfLive.reason}</Alert>
          )}
        </div>
      )}

      <div className="card">
        <h3>Compile new report</h3>
        <div className="form-grid">
          <div className="field"><label>Period start *</label><input type="date" value={f.period_start} onChange={(e) => setF({ ...f, period_start: e.target.value })} /></div>
          <div className="field"><label>Period end *</label><input type="date" value={f.period_end} onChange={(e) => setF({ ...f, period_end: e.target.value })} /></div>
        </div>
        {client?.connected && (
          <label className="checkbox-row" style={{ margin: '10px 0' }}>
            <input type="checkbox" checked={f.use_api} onChange={(e) => setF({ ...f, use_api: e.target.checked })} />
            Pull performance numbers live from Google <ConnDot connected />
          </label>
        )}
        <h3 style={{ marginTop: 16 }}>Profile performance <span className="sub">Leave blank what you don’t know — blanks stay blank, never guessed</span></h3>
        <div className="form-grid">
          {perfKeys.map((k) => (
            <div className="field" key={k}><label>{pretty(k)}</label><input type="text" value={f.perf[k] || ''} onChange={(e) => setP(k, e.target.value)} /></div>
          ))}
        </div>
        <h3 style={{ marginTop: 16 }}>Activity this period</h3>
        <div className="form-grid">
          {actKeys.map((k) => (
            <div className="field" key={k}><label>{pretty(k)}</label><input type="text" value={f.activity[k] || ''} onChange={(e) => setA(k, e.target.value)} /></div>
          ))}
        </div>
        <h3 style={{ marginTop: 16 }}>SEO notes</h3>
        <div className="form-grid">
          <div className="field"><label>Keywords targeted</label><textarea rows={2} value={f.seo.keywords_targeted} onChange={(e) => setS('keywords_targeted', e.target.value)} /></div>
          <div className="field"><label>New opportunities</label><textarea rows={2} value={f.seo.new_opportunities} onChange={(e) => setS('new_opportunities', e.target.value)} /></div>
          <div className="field full"><label>Competitor observations</label><textarea rows={2} value={f.seo.competitor_notes} onChange={(e) => setS('competitor_notes', e.target.value)} /></div>
        </div>
        <h3 style={{ marginTop: 16 }}>Next period plan</h3>
        <div className="form-grid">
          <div className="field full"><label>What was completed / what changed (one per line)</label><textarea rows={3} value={f.next_plan.changes} onChange={(e) => setN('changes', e.target.value)} /></div>
          <div className="field"><label>Keywords to target</label><input type="text" value={f.next_plan.keywords} onChange={(e) => setN('keywords', e.target.value)} /></div>
          <div className="field"><label>Services to promote</label><input type="text" value={f.next_plan.services} onChange={(e) => setN('services', e.target.value)} /></div>
          <div className="field"><label>Content topics</label><input type="text" value={f.next_plan.topics} onChange={(e) => setN('topics', e.target.value)} /></div>
          <div className="field"><label>Offers / promotions</label><input type="text" value={f.next_plan.offers} onChange={(e) => setN('offers', e.target.value)} /></div>
          <div className="field full"><label>Visual content needed</label><input type="text" value={f.next_plan.visuals} onChange={(e) => setN('visuals', e.target.value)} /></div>
          <div className="field full"><label>Profile optimization tasks</label><input type="text" value={f.next_plan.optimizations} onChange={(e) => setN('optimizations', e.target.value)} /></div>
        </div>
        <div className="form-actions">
          <button className="btn primary" disabled={busy} onClick={compile}>{busy ? 'Compiling…' : 'Compile report'}</button>
        </div>
      </div>

      <div className="card">
        <h3>Past reports <span className="sub">{reps.length}</span></h3>
        {reps.length === 0 ? (
          <EmptyState title="No reports yet" text="Compile your first report above." />
        ) : (
          <div className="table-wrap"><table>
            <thead><tr><th>Period</th><th>Created</th><th>Data sources</th><th></th></tr></thead>
            <tbody>
              {reps.map((r) => (
                <tr key={r.id}>
                  <td><strong>{r.period_start} → {r.period_end}</strong></td>
                  <td className="muted">{r.created_at}</td>
                  <td>{Object.keys(JSON.parse(r.sources_json || '{}')).length > 0
                    ? Object.entries(JSON.parse(r.sources_json || '{}')).slice(0, 4).map(([k, v]) => <span key={k} style={{ marginRight: 4 }}><Badge value={v} /></span>)
                    : <span className="muted">—</span>}</td>
                  <td><a className="btn small" href={reportUrl(r.id)} target="_blank" rel="noreferrer">Open</a></td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </div>
    </>
  )
}
