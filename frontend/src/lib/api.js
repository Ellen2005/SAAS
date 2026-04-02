import { supabase } from './supabaseClient'

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function buildHeaders(existingHeaders = {}, includeJson = false) {
  const headers = new Headers(existingHeaders)
  const { data: { session } } = await supabase.auth.getSession()

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
  const headers = await buildHeaders(options.headers, hasJsonBody)
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    try {
      const errorPayload = await response.json()
      message = errorPayload.detail || errorPayload.message || message
    } catch {
      // Ignore JSON parsing failure and keep the fallback message.
    }
    throw new Error(message)
  }

  return response
}

export async function apiJson(path, options = {}) {
  const response = await apiFetch(path, options)
  return response.json()
}
