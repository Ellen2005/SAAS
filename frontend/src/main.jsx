import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Unregister any stale service workers that may be serving a cached blank shell.
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    registrations.forEach((reg) => reg.unregister())
  })
}

// Keepalive ping every 10 minutes — prevents free-tier backend cold-starts.
const BACKEND = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const ping = () => fetch(`${BACKEND}/api/ping`).catch(() => {})
ping()
setInterval(ping, 10 * 60 * 1000)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
