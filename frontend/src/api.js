// Tiny fetch wrapper for the Flask JSON API (same origin, /api/*).
// Har non-auth request par UI mode (live/demo) lagta hai taaki backend demo
// data ko sahi tareeqe se filter kare. Mode localStorage me 'gmb-mode' me save hota hai.
function withMode(p) {
  if (p.startsWith('/auth')) return p
  const mode = localStorage.getItem('gmb-mode') || 'live'
  return p + (p.includes('?') ? '&' : '?') + 'mode=' + mode
}

async function req(method, path, body) {
  const res = await fetch('/api' + withMode(path), {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok || data.ok === false) {
    throw new Error(data.error || data.message || `Request failed (${res.status})`)
  }
  return data
}

export const api = {
  get: (p) => req('GET', p),
  post: (p, b) => req('POST', p, b === undefined ? {} : b),
  patch: (p, b) => req('PATCH', p, b || {}),
  del: (p) => req('DELETE', p),
}

export const reportUrl = (id) => `/api/report/${id}`

export function getMode() {
  return localStorage.getItem('gmb-mode') || 'live'
}

export function setMode(mode) {
  localStorage.setItem('gmb-mode', mode)
  window.location.reload()
}
