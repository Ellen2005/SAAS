import { supabase } from './supabaseClient'

export const API_URL =
  import.meta.env.VITE_API_URL === ''
    ? ''
    : (import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000'))

let _isRedirectingToLogin = false
let _tokenRefreshPromise = null

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
  // Deduplicate concurrent token refresh attempts to avoid race conditions
  // when multiple API calls fire in parallel on page load
  let session = await getSessionSafe()
  if (session?.access_token) {
    _tokenRefreshPromise = null
    return session.access_token
  }

  // If a refresh is already in progress, wait for it instead of starting another
  if (_tokenRefreshPromise) {
    try {
      const refreshed = await _tokenRefreshPromise
      return refreshed?.access_token
    } catch {
      return null
    }
  }

  _tokenRefreshPromise = (async () => {
    try {
      const { data: { session: refreshed }, error } = await supabase.auth.refreshSession()
      if (error) throw error
      return refreshed
    } catch (err) {
      console.error('Session refresh failed:', err.message)
      await supabase.auth.signOut()
      redirectToLogin()
      return null
    }
  })()

  try {
    const result = await _tokenRefreshPromise
    return result?.access_token
  } finally {
    _tokenRefreshPromise = null
  }
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
      let session
      try {
        const { data, error } = await supabase.auth.refreshSession()
        if (error) throw error
        session = data.session
      } catch (err) {
        // Invalid/expired refresh token — force re-login
        console.error('Session refresh failed on 401:', err.message)
        await supabase.auth.signOut()
        redirectToLogin()
        throw new Error('Session expired. Redirecting to login.')
      }
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
