import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './styles/enterprise-theme.css'
import App from './App.jsx'

// Render the app immediately — nothing blocks the first paint
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// PWA: service worker is auto-registered by vite-plugin-pwa (injectRegister: 'auto')
// No manual registration needed — workbox handles caching & offline fallback

// Keepalive ping — wakes free-tier backend before user needs it
// Only pings when the page is visible to avoid background battery drain
const BACKEND =
  import.meta.env.VITE_API_URL === ''
    ? ''
    : (import.meta.env.VITE_API_URL || 'http://localhost:8000')

let pingInterval = null

function startPing() {
  if (pingInterval) return
  pingInterval = setInterval(() => {
    fetch(`${BACKEND}/api/ping`, { method: 'GET' }).catch(() => {})
  }, 10 * 60 * 1000)
}

function stopPing() {
  if (pingInterval) {
    clearInterval(pingInterval)
    pingInterval = null
  }
}

// Respect Page Visibility API — don't ping when tab is hidden
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    startPing()
  } else {
    stopPing()
  }
})

// Delay first ping by 3s so it doesn't compete with initial page load
setTimeout(() => {
  if (document.visibilityState === 'visible') {
    startPing()
  }
}, 3000)