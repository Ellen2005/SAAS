import { supabase } from './supabaseClient'

export const API_URL =
  import.meta.env.VITE_API_URL === ''
    ? ''
    : (import.meta.env.VITE_API_URL || 'http://localhost:5000')

let _sessionPromise = supabase.auth.getSession()
let _cachedSession = null

_sessionPromise.then(({ data: { session } }) => {
  _cachedSession = session
})

supabase.auth.onAuthStateChange((_event, session) => {
  _cachedSession = session
})

export async function getSessionSafe() {
  if (_cachedSession) return _cachedSession
  const { data: { session } } = await _sessionPromise
  _cachedSession = session
  return session
}

function buildHeaders(existingHeaders = {}, includeJson = false) {
  const headers = new Headers(existingHeaders)
  if (includeJson && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (_cachedSession?.access_token) {
    headers.set('Authorization', `Bearer ${_cachedSession.access_token}`)
  }
  return headers
}

export async function apiFetch(path, options = {}) {
  await getSessionSafe()
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
