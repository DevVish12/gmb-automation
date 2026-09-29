// Tiny fetch wrapper for the Flask JSON API (same origin, /api/*).
async function req(method, path, body) {
  const res = await fetch('/api' + path, {
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
