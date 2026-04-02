import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { apiJson } from '../lib/api';

const ValidationHistory = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const VALIDATION_CACHE_KEY = 'saas.validation.lastLogs.v1';

  const readValidationCache = () => {
    try {
      const raw = localStorage.getItem(VALIDATION_CACHE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch {
      return null;
    }
  };

  const writeValidationCache = (payload) => {
    try {
      localStorage.setItem(VALIDATION_CACHE_KEY, JSON.stringify(payload));
    } catch {
      // Ignore when storage is unavailable.
    }
  };

  useEffect(() => {
    const loadLogs = async () => {
      try {
        const data = await apiJson('/api/validation/logs?limit=100');
        setLogs(data.logs || []);
        writeValidationCache(data.logs || []);
      } catch (error) {
        console.error('Failed to load validation logs', error);
        const cached = readValidationCache();
        if (cached) setLogs(cached);
      } finally {
        setLoading(false);
      }
    };

    loadLogs();
  }, []);

  if (loading) {
    return <p style={{ color: 'var(--text-secondary)' }}>Loading validation history...</p>;
  }

  return (
    <div style={{ display: 'grid', gap: '24px' }}>
      <header>
        <h1>Validation History</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Schema, null, and anomaly checks from your governed department syncs.
        </p>
      </header>

      <section className="glass-panel">
        <div style={{ display: 'grid', gap: '12px' }}>
          {logs.map((log) => (
            <div
              key={log.id}
              style={{
                display: 'grid',
                gridTemplateColumns: 'auto 120px 120px 1fr',
                gap: '16px',
                alignItems: 'start',
                padding: '14px 0',
                borderBottom: '1px solid rgba(255,255,255,0.06)',
              }}
            >
              <div style={{ marginTop: '2px' }}>
                {log.status === 'pass' ? (
                  <CheckCircle2 size={18} color="var(--status-normal)" />
                ) : (
                  <AlertTriangle size={18} color={log.status === 'warning' ? 'var(--status-warning)' : 'var(--status-critical)'} />
                )}
              </div>
              <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>{log.check_type}</div>
              <div style={{ textTransform: 'uppercase', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{log.status}</div>
              <div>
                <div style={{ color: 'var(--text-primary)' }}>{log.message}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', marginTop: '4px' }}>
                  {new Date(log.created_at).toLocaleString()}
                </div>
              </div>
            </div>
          ))}

          {logs.length === 0 && (
            <p style={{ color: 'var(--text-secondary)' }}>No validation logs yet. Run a sync to populate this history.</p>
          )}
        </div>
      </section>
    </div>
  );
};

export default ValidationHistory;
