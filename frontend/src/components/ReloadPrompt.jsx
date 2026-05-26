import React, { useEffect, useState } from 'react'
import { Download, RefreshCw, X } from 'lucide-react'

function ReloadPrompt() {
  const [offlineReady, setOfflineReady] = useState(false)
  const [needRefresh, setNeedRefresh] = useState(false)
  const [installPrompt, setInstallPrompt] = useState(null)
  const [updateSW, setUpdateSW] = useState(null)

  useEffect(() => {
    if (import.meta.env.DEV) return undefined

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.ready.then((reg) => {
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                setNeedRefresh(true)
                setUpdateSW(() => () => {
                  newWorker.postMessage({ type: 'SKIP_WAITING' })
                  window.location.reload()
                })
              }
            })
          }
        })
      }).catch(() => {
        // Service worker readiness is best-effort; install prompts still work.
      })
    }

    const handler = (e) => { e.preventDefault(); setInstallPrompt(e) }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  const close = () => { setOfflineReady(false); setNeedRefresh(false) }

  const handleInstall = async () => {
    if (!installPrompt) return
    installPrompt.prompt()
    const { outcome } = await installPrompt.userChoice
    if (outcome === 'accepted') setInstallPrompt(null)
  }

  if (!offlineReady && !needRefresh && !installPrompt) return null

  return (
    <div style={{ position: 'fixed', right: '16px', bottom: '16px', zIndex: 9999 }}>
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px', minWidth: '280px', border: '1px solid var(--primary-color)' }}>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', margin: 0 }}>
          {offlineReady ? 'App ready to work offline' : needRefresh ? 'Update available - reload to apply.' : 'Install SAAS for a better experience'}
        </p>
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
          {installPrompt && !needRefresh && (
            <button className="btn btn-primary" onClick={handleInstall} style={{ padding: '4px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}>
              <Download size={14} /> Install
            </button>
          )}
          {needRefresh && updateSW && (
            <button className="btn btn-primary" onClick={updateSW} style={{ padding: '4px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}>
              <RefreshCw size={14} /> Reload
            </button>
          )}
          <button className="btn btn-outline" onClick={close} style={{ padding: '4px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}>
            <X size={14} /> Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default ReloadPrompt
