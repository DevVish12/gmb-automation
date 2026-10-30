import React, { useEffect, useState } from 'react'
import { BrowserRouter, NavLink, Route, Routes, Link } from 'react-router-dom'
import { api, getMode, setMode } from './api'
import { I } from './components/icons'
import Dashboard from './pages/Dashboard'
import Clients from './pages/Clients'
import Audit from './pages/Audit'
import Keywords from './pages/Keywords'
import Optimizations from './pages/Optimizations'
import Calendar from './pages/Calendar'
import Queue from './pages/Queue'
import Creatives from './pages/Creatives'
import Reviews from './pages/Reviews'
import Media from './pages/Media'
import Competitors from './pages/Competitors'
import Reports from './pages/Reports'
import Tracker from './pages/Tracker'
import Pipeline from './pages/Pipeline'
import Settings from './pages/Settings'
import Help from './pages/Help'
import Login from './pages/Login'
import Admin from './pages/Admin'
import { Loading } from './components/ui'

const NAV = [
  { to: '/', label: 'Dashboard', icon: I.dashboard, end: true },
  { to: '/clients', label: 'Clients', icon: I.clients },
  { section: 'Optimize' },
  { to: '/audit', label: 'Profile Audit', icon: I.audit },
  { to: '/keywords', label: 'Keywords', icon: I.keywords },
  { to: '/optimization', label: 'Optimization', icon: I.audit },
  { section: 'Publish' },
  { to: '/calendar', label: 'Content Calendar', icon: I.calendar },
  { to: '/queue', label: 'Content Queue', icon: I.queue },
  { to: '/creatives', label: 'Creative Briefs', icon: I.media },
  { to: '/reviews', label: 'Reviews', icon: I.reviews },
  { to: '/media', label: 'Photos & Videos', icon: I.media },
  { section: 'Analyze' },
  { to: '/competitors', label: 'Competitors', icon: I.competitors },
  { to: '/reports', label: 'Reports', icon: I.reports },
  { to: '/tracker', label: 'Activity Tracker', icon: I.tracker },
  { to: '/pipeline', label: 'Pipeline', icon: I.tracker },
  { section: 'System' },
  { to: '/settings', label: 'Settings', icon: I.settings },
  { to: '/help', label: 'Help & Setup', icon: I.help },
]

const MenuIcon = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 6h16M4 12h16M4 18h16" />
  </svg>
)

function Shell({ user }) {
  const [status, setStatus] = useState(null)
  const [mode, setModeState] = useState(getMode())
  const [sidebarOpen, setSidebarOpen] = useState(false)
  useEffect(() => {
    api.get('/status').then(setStatus).catch(() => {})
  }, [])
  const dryRun = status ? status.dry_run : true

  const nav = user.role === 'super_admin'
    ? [...NAV, { section: 'Admin' }, { to: '/admin', label: 'Users & Logins', icon: I.settings }]
    : NAV

  const logout = async () => {
    try { await api.post('/auth/logout') } catch (e) {}
    window.location.href = '/'
  }

  const switchMode = (m) => {
    setModeState(m)
    setMode(m)
  }

  const initial = (user.email || '?').trim().charAt(0).toUpperCase()

  return (
    <div className="app">
      <div className={`sidebar-overlay${sidebarOpen ? ' show' : ''}`} onClick={() => setSidebarOpen(false)} />
      <aside className={`sidebar${sidebarOpen ? ' open' : ''}`}>
        <div className="brand">
          <div className="brand-row">
            <span className="logo-mark">G</span>
            <div>
              <h1>GMB Automation</h1>
              <p>Local SEO, on autopilot</p>
            </div>
          </div>
        </div>
        <nav className="nav" onClick={() => setSidebarOpen(false)}>
          {nav.map((n, i) =>
            n.section
              ? <div key={i} className="section-label">{n.section}</div>
              : <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => isActive ? 'active' : ''}>
                  {n.icon}<span>{n.label}</span>
                </NavLink>
          )}
        </nav>
        <div className="sidebar-foot">
          {dryRun ? 'DRY-RUN mode' : 'LIVE mode'} · v1.0
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-btn" aria-label="Open menu" onClick={() => setSidebarOpen(true)}>{MenuIcon}</button>
          </div>
          <div className="topbar-right">
            <div className="seg" role="group" aria-label="View mode">
              <button className={mode === 'live' ? 'active' : ''} onClick={() => switchMode('live')}>Live</button>
              <button className={mode === 'demo' ? 'active' : ''} onClick={() => switchMode('demo')}>Demo</button>
            </div>
            <div className="topbar-divider" />
            <div className="user-chip">
              <span className="avatar">{initial}</span>
              <span className="user-meta">
                <strong>{user.email}</strong>
                <span>{user.role === 'super_admin' ? 'Super admin' : 'Operator'}</span>
              </span>
            </div>
            <button className="btn small" onClick={logout}>Logout</button>
          </div>
        </header>
        {status && dryRun && (
          <div className="dryrun-banner">
            <strong>DRY-RUN MODE</strong>
            <span>Nothing is published to Google yet. Everything works — drafts, calendar, reports — but publishing needs the live setup.</span>
            <Link to="/help">See setup steps →</Link>
          </div>
        )}
        <div className="content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/clients" element={<Clients />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="/keywords" element={<Keywords />} />
            <Route path="/optimization" element={<Optimizations />} />
            <Route path="/calendar" element={<Calendar />} />
            <Route path="/queue" element={<Queue />} />
            <Route path="/creatives" element={<Creatives />} />
            <Route path="/reviews" element={<Reviews />} />
            <Route path="/media" element={<Media />} />
            <Route path="/competitors" element={<Competitors />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/tracker" element={<Tracker />} />
            <Route path="/pipeline" element={<Pipeline />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/help" element={<Help />} />
            <Route path="/admin" element={<Admin />} />
          </Routes>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [user, setUser] = useState(null)
  useEffect(() => {
    api.get('/auth/me').then((d) => setUser(d.authenticated ? d.operator : false)).catch(() => setUser(false))
  }, [])
  return (
    <BrowserRouter>
      {user === null ? <Loading /> : user === false ? <Login /> : <Shell user={user} />}
    </BrowserRouter>
  )
}
