import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { Alert, Badge, Loading, PageHeader } from '../components/ui'

export default function Admin() {
  const [users, setUsers] = useState(null)
  const [logins, setLogins] = useState([])
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')

  const load = () => {
    api.get('/admin/users').then((d) => setUsers(d.users)).catch((e) => { setErr(e.message); setUsers([]) })
    api.get('/admin/logins').then((d) => setLogins(d.logins)).catch(() => {})
  }
  useEffect(() => { load() }, [])

  const toggle = async (u) => {
    setErr('')
    setOk('')
    try {
      const d = await api.post(`/admin/users/${u.id}/toggle`)
      setOk(`User ${u.email} ${d.is_active ? 'enabled' : 'disabled'}.`)
      load()
    } catch (e) {
      setErr(e.message)
    }
  }

  if (users === null) return <Loading />

  return (
    <>
      <PageHeader
        title="Users & Logins"
        subtitle="Super admin only. See every operator, enable or disable accounts, and track who signed in and when."
      />
      <Alert kind="error">{err}</Alert>
      <Alert kind="success">{ok}</Alert>

      <div className="card"><h3>Operators</h3>
        {users.length === 0 ? (
          <p className="muted">No operators found.</p>
        ) : (
          <div className="table-wrap"><table>
            <thead><tr><th>Email</th><th>Name</th><th>Role</th><th>Status</th><th>Created</th><th></th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td><strong>{u.email}</strong></td>
                  <td>{u.name || '—'}</td>
                  <td>{u.role === 'super_admin' ? <Badge value="Super admin" tone="purple" /> : <span className="muted">Operator</span>}</td>
                  <td>{u.is_active ? <Badge value="Active" tone="green" /> : <Badge value="Disabled" tone="red" />}</td>
                  <td><span className="muted">{u.created_at || '—'}</span></td>
                  <td><button className="btn small" onClick={() => toggle(u)}>{u.is_active ? 'Disable' : 'Enable'}</button></td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </div>

      <div className="card"><h3>Login history</h3>
        {logins.length === 0 ? (
          <p className="muted">No logins recorded yet.</p>
        ) : (
          <div className="table-wrap"><table>
            <thead><tr><th>Email</th><th>Time</th><th>IP address</th></tr></thead>
            <tbody>
              {logins.map((l) => (
                <tr key={l.id}>
                  <td>{l.email}</td>
                  <td><span className="muted">{l.created_at}</span></td>
                  <td><span className="muted">{l.ip || '—'}</span></td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </div>
    </>
  )
}
