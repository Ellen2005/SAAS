import { supabase } from './supabaseClient'

// Empty VITE_API_URL => same-origin `/api` (Vite dev proxy → backend :8000)
export const API_URL =
  import.meta.env.VITE_API_URL === ''
    ? ''
    : (import.meta.env.VITE_API_URL || 'http://localhost:8000')

// Cache the session in memory so every apiFetch doesn't await getSession()
let _cachedSession = null

supabase.auth.getSession().then(({ data: { session } }) => {
  _cachedSession = session
})

supabase.auth.onAuthStateChange((_event, session) => {
  _cachedSession = session
})

function buildHeaders(existingHeaders = {}, includeJson = false) {
  const headers = new Headers(existingHeaders)
  const session = _cachedSession

  if (includeJson && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`)
  }
  if (session?.user?.id) {
    headers.set('X-User-Id', session.user.id)
  }
  return headers
}

export async function apiFetch(path, options = {}) {
  const hasJsonBody = options.body && typeof options.body === 'string'
  const headers = buildHeaders(options.headers, hasJsonBody)

  const response = await fetch(`${API_URL}${path}`, { ...options, headers })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    try {
      const err = await response.json()
      message = err.detail || err.message || message
    } catch { /* ignore */ }
    throw new Error(message)
  }

  return response
}

export async function apiJson(path, options = {}) {
  const response = await apiFetch(path, options)
  return response.json()
}
