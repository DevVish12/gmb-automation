import React, { useEffect, useState } from 'react'

// ---------- status pill ----------
const TONES = {
  // posts
  draft: 'slate', approved: 'blue', scheduled: 'amber', published: 'green', failed: 'red',
  // activities
  Pending: 'slate', 'In Progress': 'blue', 'Ready for QA': 'purple',
  Approved: 'indigo', Scheduled: 'amber', Published: 'green', Verified: 'green',
  // priorities
  High: 'red', Medium: 'amber', Low: 'slate',
  // reviews
  none: 'slate', sent: 'green',
  // media
  planned: 'slate',
  // misc
  manual: 'slate', API: 'green', dataforseo: 'purple',
}

export function Badge({ value, tone }) {
  if (value === undefined || value === null || value === '') return <span className="muted">—</span>
  return <span className={`badge ${tone || TONES[value] || 'slate'}`}>{value}</span>
}

// ---------- page header ----------
export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="page-head">
      <h2>{title}</h2>
      {subtitle && <p>{subtitle}</p>}
      {actions && <div className="actions">{actions}</div>}
    </div>
  )
}

// ---------- empty state ----------
export function EmptyState({ title, text, action }) {
  return (
    <div className="empty">
      <h4>{title}</h4>
      {text && <p>{text}</p>}
      {action}
    </div>
  )
}

// ---------- modal ----------
export function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    const h = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" style={wide ? { maxWidth: 860 } : undefined} onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        {children}
      </div>
    </div>
  )
}

// ---------- spinner / loading ----------
export function Loading({ text }) {
  return (
    <div className="card" style={{ textAlign: 'center', padding: 40, color: 'var(--muted)' }}>
      <span className="spinner" /> {text || 'Loading…'}
    </div>
  )
}

// ---------- stat card ----------
export function Stat({ label, value, sub }) {
  return (
    <div className="stat">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  )
}

// ---------- alert ----------
export function Alert({ kind, children }) {
  if (!children) return null
  return <div className={`alert ${kind || 'info'}`}>{children}</div>
}

// ---------- client picker (persisted) ----------
export function useClient(clients) {
  const [slug, setSlug] = useState(() => localStorage.getItem('gmb_client') || '')
  useEffect(() => {
    if (!slug && clients.length) {
      setSlug(clients[0].slug)
    } else if (slug && clients.length && !clients.find((c) => c.slug === slug)) {
      setSlug(clients[0].slug)
    }
  }, [clients])
  const pick = (s) => {
    setSlug(s)
    localStorage.setItem('gmb_client', s)
  }
  return [slug, pick]
}

export function ClientPicker({ clients, value, onChange, label }) {
  return (
    <div className="field" style={{ minWidth: 260, marginBottom: 0 }}>
      {label !== false && <label>Client</label>}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {clients.map((c) => (
          <option key={c.slug} value={c.slug}>
            {c.business_name || c.name}{c.connected ? '  ●' : ''}
          </option>
        ))}
      </select>
    </div>
  )
}

// ---------- connection dot ----------
export function ConnDot({ connected }) {
  return connected
    ? <span className="badge green">Google connected</span>
    : <span className="badge slate">Not connected</span>
}
