import React, { useEffect, useState } from 'react';

export default function OfflineBanner() {
  const [offline, setOffline] = useState(() => (typeof navigator !== 'undefined' ? !navigator.onLine : false));

  useEffect(() => {
    const goOffline = () => setOffline(true);
    const goOnline = () => setOffline(false);

    window.addEventListener('offline', goOffline);
    window.addEventListener('online', goOnline);
    return () => {
      window.removeEventListener('offline', goOffline);
      window.removeEventListener('online', goOnline);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 2000,
        padding: '10px 16px',
        textAlign: 'center',
        background: 'rgba(239, 68, 68, 0.10)',
        borderBottom: '1px solid rgba(239, 68, 68, 0.35)',
        color: 'var(--status-critical)',
        backdropFilter: 'blur(6px)',
      }}
    >
      Offline mode: showing cached data (if available).
    </div>
  );
}

