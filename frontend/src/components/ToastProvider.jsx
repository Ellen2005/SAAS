import React, { createContext, useContext, useCallback, useRef, useState } from 'react';

const ToastContext = createContext(null);

let _idCounter = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timersRef = useRef({});

  const removeToast = useCallback((id) => {
    if (timersRef.current[id]) {
      clearTimeout(timersRef.current[id]);
      delete timersRef.current[id];
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++_idCounter;
    setToasts((prev) => [...prev, { id, message, type }]);
    if (duration > 0) {
      timersRef.current[id] = setTimeout(() => removeToast(id), duration);
    }
    return id;
  }, [removeToast]);

  const toast = useCallback((msg, dur) => addToast(msg, 'info', dur), [addToast]);
  toast.success = (msg, dur) => addToast(msg, 'success', dur);
  toast.error = (msg, dur) => addToast(msg, 'error', dur ?? 6000);
  toast.info = (msg, dur) => addToast(msg, 'info', dur);
  toast.warning = (msg, dur) => addToast(msg, 'warning', dur);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      {toasts.length > 0 && (
        <div style={{ position: 'fixed', top: 16, right: 16, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 380, pointerEvents: 'auto' }}>
          {toasts.map((t) => {
            const colors = {
              success: { bg: 'rgba(16,185,129,0.15)', border: '#10b981', text: '#10b981' },
              error:   { bg: 'rgba(239,68,68,0.15)', border: '#ef4444', text: '#ef4444' },
              info:    { bg: 'rgba(59,130,246,0.15)', border: '#3b82f6', text: '#3b82f6' },
              warning: { bg: 'rgba(245,158,11,0.15)', border: '#f59e0b', text: '#f59e0b' },
            }[t.type] || { bg: 'rgba(59,130,246,0.15)', border: '#3b82f6', text: '#3b82f6' };

            return (
              <div
                key={t.id}
                style={{
                  padding: '12px 16px',
                  borderRadius: 8,
                  background: colors.bg,
                  border: `1px solid ${colors.border}`,
                  color: 'var(--text-primary, #f8fafc)',
                  fontSize: '0.85rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 12,
                  boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                  animation: 'slideIn 0.2s ease-out',
                }}
              >
                <span>{t.message}</span>
                <button
                  onClick={() => removeToast(t.id)}
                  style={{ background: 'none', border: 'none', color: colors.text, cursor: 'pointer', padding: 0, fontSize: '1.1rem', lineHeight: 1, opacity: 0.7 }}
                  aria-label="Dismiss"
                >
                  x
                </button>
              </div>
            );
          })}
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within a ToastProvider');
  return ctx;
}
