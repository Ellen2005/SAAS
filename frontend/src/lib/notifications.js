import { useState, useCallback, useRef } from 'react';

let _id = 0;

export function useNotifications() {
  const [notifications, setNotifications] = useState([]);
  const timerRef = useRef({});

  const addNotification = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++_id;
    setNotifications((prev) => [...prev, { id, message, type }]);
    if (duration > 0) {
      timerRef.current[id] = setTimeout(() => {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
        delete timerRef.current[id];
      }, duration);
    }
    return id;
  }, []);

  const removeNotification = useCallback((id) => {
    clearTimeout(timerRef.current[id]);
    delete timerRef.current[id];
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const success = useCallback((msg, duration) => addNotification(msg, 'success', duration), [addNotification]);
  const error = useCallback((msg, duration) => addNotification(msg, 'error', duration || 6000), [addNotification]);
  const info = useCallback((msg, duration) => addNotification(msg, 'info', duration), [addNotification]);

  return { notifications, addNotification, removeNotification, success, error, info };
}

export function NotificationToast({ notifications, onRemove }) {
  if (!notifications.length) return null;
  return (
    <div style={{ position: 'fixed', top: 16, right: 16, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 380 }}>
      {notifications.map((n) => (
        <div
          key={n.id}
          style={{
            padding: '12px 16px',
            borderRadius: 8,
            background: n.type === 'success' ? 'rgba(16,185,129,0.15)' : n.type === 'error' ? 'rgba(239,68,68,0.15)' : 'rgba(59,130,246,0.15)',
            border: `1px solid ${n.type === 'success' ? '#10b981' : n.type === 'error' ? '#ef4444' : '#3b82f6'}`,
            color: 'var(--text-primary)',
            fontSize: '0.85rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 12,
            animation: 'slideIn 0.2s ease-out',
          }}
        >
          <span>{n.message}</span>
          <button
            onClick={() => onRemove(n.id)}
            style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: 0, fontSize: '1rem', lineHeight: 1 }}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
