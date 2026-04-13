import React, { useEffect, useState } from 'react';

export default function InactivityWarning() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const show = () => setVisible(true);
    const hide = () => setVisible(false);
    window.addEventListener('saas:inactivity-warning', show);
    // Any user activity after the warning dismisses it
    window.addEventListener('mousemove', hide, { passive: true });
    window.addEventListener('keydown', hide, { passive: true });
    return () => {
      window.removeEventListener('saas:inactivity-warning', show);
      window.removeEventListener('mousemove', hide);
      window.removeEventListener('keydown', hide);
    };
  }, []);

  if (!visible) return null;

  return (
    <div style={{
      position: 'fixed', bottom: '80px', right: '16px', zIndex: 9998,
      background: 'var(--surface-color)', border: '1px solid var(--status-warning)',
      borderRadius: '12px', padding: '16px 20px', maxWidth: '320px',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
    }}>
      <p style={{ color: 'var(--status-warning)', fontWeight: 600, marginBottom: '4px' }}>
        Session expiring soon
      </p>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
        You will be signed out in 5 minutes due to inactivity. Move your mouse or press a key to stay signed in.
      </p>
    </div>
  );
}
