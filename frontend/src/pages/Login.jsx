import React, { useState } from 'react'
import { api } from '../api'
import { Alert } from '../components/ui'

export default function Login() {
  const [tab, setTab] = useState('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setErr('')
    setBusy(true)
    try {
      if (tab === 'register') {
        await api.post('/auth/register', { name, email, password })
      } else {
        await api.post('/auth/login', { email, password })
      }
      window.location.href = '/'
    } catch (e2) {
      setErr(e2.message)
      setBusy(false)
    }
  }

  const google = async () => {
    setErr('')
    try {
      const d = await api.get('/auth/google')
      window.location.href = d.authorization_url
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <div className="app">
      <div className="main" style={{ margin: '0 auto', maxWidth: 480, padding: 24 }}>
        <div className="brand">
          <h1>GMB Automation</h1>
          <p>Local SEO, on autopilot</p>
        </div>
        <div className="card" style={{ marginTop: 24 }}>
          <h2>{tab === 'register' ? 'Create account' : 'Sign in'}</h2>
          <p className="muted">First account on this server becomes super admin. No limit on accounts.</p>
          <Alert kind="error">{err}</Alert>
          <form onSubmit={submit}>
            <div className="form-grid">
              {tab === 'register' && (
                <div className="field full"><label>Name</label><input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" /></div>
              )}
              <div className="field full"><label>Email</label><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required /></div>
              <div className="field full"><label>Password</label><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Min 6 characters" required /></div>
            </div>
            <div className="form-actions">
              <button className="btn primary" type="submit" disabled={busy}>{busy ? 'Please wait…' : (tab === 'register' ? 'Create account' : 'Sign in')}</button>
            </div>
          </form>
          <div style={{ textAlign: 'center', margin: '12px 0' }} className="muted">— or —</div>
          <button className="btn" style={{ width: '100%' }} onClick={google}>Continue with Google</button>
          <p className="muted" style={{ marginTop: 16 }}>
            {tab === 'register'
              ? <>Already have an account? <a href="#" onClick={(e) => { e.preventDefault(); setTab('login') }}>Sign in</a></>
              : <>No account yet? <a href="#" onClick={(e) => { e.preventDefault(); setTab('register') }}>Create one</a></>}
          </p>
        </div>
      </div>
    </div>
  )
}
