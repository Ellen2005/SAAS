import React, { useEffect, useState } from 'react'
import { useRegisterSW } from 'virtual:pwa-register/react'
import { Download, RefreshCw, X } from 'lucide-react'

function ReloadPrompt() {
  const [installPrompt, setInstallPrompt] = useState(null);

  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegistered(r) {
      console.log('SW Registered: ' + r)
    },
    onRegisterError(error) {
      console.log('SW registration error', error)
    },
  })

  useEffect(() => {
    const handler = (e) => {
      e.preventDefault();
      setInstallPrompt(e);
    };

    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const close = () => {
    setOfflineReady(false)
    setNeedRefresh(false)
  }

  const handleInstall = async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    const { outcome } = await installPrompt.userChoice;
    if (outcome === 'accepted') {
      setInstallPrompt(null);
    }
  };

  if (!offlineReady && !needRefresh && !installPrompt) return null;

  return (
    <div className="pwa-toast-container">
      <div className="pwa-toast glass-panel">
        <div className="pwa-message">
          {offlineReady ? (
            <span>App ready to work offline</span>
          ) : needRefresh ? (
            <span>New content available, click on reload button to update.</span>
          ) : (
            <span>Install SAAS for a better experience</span>
          )}
        </div>
        <div className="pwa-actions">
          {installPrompt && !needRefresh && !offlineReady && (
            <button className="btn btn-primary btn-sm" onClick={handleInstall}>
              <Download size={14} /> Install
            </button>
          )}
          {needRefresh && (
            <button className="btn btn-primary btn-sm" onClick={() => updateServiceWorker(true)}>
              <RefreshCw size={14} /> Reload
            </button>
          )}
          <button className="btn btn-outline btn-sm" onClick={close}>
            <X size={14} /> Close
          </button>
        </div>
      </div>

      <style>{`
        .pwa-toast-container {
          position: fixed;
          right: 0;
          bottom: 0;
          margin: 16px;
          padding: 12px;
          z-index: 9999;
        }
        .pwa-toast {
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 16px;
          min-width: 300px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.5);
          border: 1px solid var(--primary-color);
          animation: slideIn 0.3s ease-out;
        }
        .pwa-message {
          font-size: 0.9rem;
          color: var(--text-primary);
        }
        .pwa-actions {
          display: flex;
          gap: 8px;
          justify-content: flex-end;
        }
        @keyframes slideIn {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        .btn-sm {
          padding: 4px 12px;
          font-size: 0.8rem;
          display: flex;
          align-items: center;
          gap: 6px;
        }
      `}</style>
    </div>
  )
}

export default ReloadPrompt
