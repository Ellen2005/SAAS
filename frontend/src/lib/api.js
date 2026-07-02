import { supabase } from './supabaseClient'

export const API_URL =
  import.meta.env.VITE_API_URL === ''
    ? ''
    : (import.meta.env.VITE_API_URL || (import.meta.env.PROD ? 'https://localhost:8000' : 'http://localhost:8000'))

let _isRedirectingToLogin = false

function redirectToLogin() {
  if (_isRedirectingToLogin) return
  _isRedirectingToLogin = true
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
  setTimeout(() => { _isRedirectingToLogin = false }, 2000)
}

export async function getSessionSafe() {
  const { data: { session } } = await supabase.auth.getSession()
  return session
}

async function getAccessToken() {
  let session = await getSessionSafe()
  if (!session) {
    const { data: { session: refreshed } } = await supabase.auth.refreshSession()
    session = refreshed
  }
  return session?.access_token
}

function buildHeaders(existingHeaders = {}, includeJson = false) {
  const headers = new Headers(existingHeaders)
  if (includeJson && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  return headers
}

async function doFetch(path, options = {}, tokenOverride = null) {
  const token = tokenOverride || await getAccessToken()
  const headers = buildHeaders(options.headers, !!(options.body && typeof options.body === 'string'))
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  return fetch(`${API_URL}${path}`, { ...options, headers })
}

export async function apiFetch(path, options = {}) {
  const maxRetries = 2
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    let response
    try {
      response = await doFetch(path, options)
    } catch (err) {
      if (attempt < maxRetries) continue
      throw err
    }

    if (response.status === 401) {
      const { data: { session } } = await supabase.auth.refreshSession()
      if (!session?.access_token) {
        redirectToLogin()
        throw new Error('Session expired. Redirecting to login.')
      }
      // Retry with the freshly refreshed token
      try {
        response = await doFetch(path, options, session.access_token)
      } catch (err) {
        if (attempt < maxRetries) continue
        throw err
      }
      // If still 401 after refresh, give up
      if (response.status === 401) {
        redirectToLogin()
        throw new Error('Session expired. Redirecting to login.')
      }
    }

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

  throw new Error('Max retries exceeded.')
}

export async function apiJson(path, options = {}) {
  const response = await apiFetch(path, options)
  return response.json()
}
