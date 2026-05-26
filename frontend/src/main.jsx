import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Render the app immediately — nothing blocks the first paint
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// After render: clean up stale service workers asynchronously
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.getRegistrations().then((regs) => {
      regs.forEach((reg) => reg.unregister())
    })
  })
}

// Keepalive ping — wakes free-tier backend before user needs it
const BACKEND =
  import.meta.env.VITE_API_URL === ''
    ? ''
    : (import.meta.env.VITE_API_URL || 'http://localhost:8000')
const ping = () => fetch(`${BACKEND}/api/ping`, { method: 'GET' }).catch(() => {})
// Delay first ping by 3s so it doesn't compete with initial page load
setTimeout(ping, 3000)
setInterval(ping, 10 * 60 * 1000)
