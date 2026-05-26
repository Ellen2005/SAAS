import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { API_URL } from '../lib/api';

const Unsubscribe = () => {
  const [params] = useSearchParams();
  const email = params.get('email');
  const token = params.get('token');
  const hasValidLink = Boolean(email && token);
  const [status, setStatus] = useState(hasValidLink ? 'loading' : 'error');
  const [message, setMessage] = useState(hasValidLink ? '' : 'Invalid unsubscribe link.');

  useEffect(() => {
    if (!hasValidLink) return;
    fetch(`${API_URL}/api/unsubscribe?email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.status === 'unsubscribed') {
          setStatus('success');
          setMessage(`${email} has been removed from all SAAS notifications.`);
        } else {
          setStatus('error');
          setMessage(data.detail || 'Unable to unsubscribe.');
        }
      })
      .catch(() => {
        setStatus('error');
        setMessage('Network error. Please try again.');
      });
  }, [email, hasValidLink, token]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: 'var(--bg-color)', padding: '20px' }}>
      <div className="glass-panel" style={{ maxWidth: '420px', width: '100%', textAlign: 'center' }}>
        {status === 'loading' && <p style={{ color: 'var(--text-secondary)' }}>Processing...</p>}
        {status === 'success' && (
          <>
            <h2 style={{ color: 'var(--status-normal)', marginBottom: '12px' }}>Unsubscribed</h2>
            <p>{message}</p>
          </>
        )}
        {status === 'error' && (
          <>
            <h2 style={{ color: 'var(--status-critical)', marginBottom: '12px' }}>Error</h2>
            <p>{message}</p>
          </>
        )}
      </div>
    </div>
  );
};

export default Unsubscribe;
