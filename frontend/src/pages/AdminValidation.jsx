import React, { useState, useEffect } from 'react';
import { AlertTriangle, Filter } from 'lucide-react';
import { apiJson } from '../lib/api';

const AdminValidation = () => {
  const [scorecard, setScorecard] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sc, lg] = await Promise.all([
          apiJson('/api/admin/validation/scorecard'),
          apiJson('/api/admin/validation/logs?limit=100')
        ]);
        setScorecard(sc.scorecard || []);
        setLogs(lg.logs || []);
      } catch (err) { console.error(err); } finally { setLoading(false); }
    };
    fetchData();
  }, []);

  const filteredLogs = logs.filter(log => {
    if (filterType && log.check_type !== filterType) return false;
    return true;
  });

  if (loading) return <p style={{ color: 'var(--text-secondary)' }}>Loading validation data...</p>;

  return (
    <div>
      <header style={{ marginBottom: '32px' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <AlertTriangle color="var(--primary-color)" /> Data Quality Audit
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>Cross-department validation scores and detailed audit logs.</p>
      </header>

      {/* Scorecard Grid */}
      <section className="glass-panel" style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>Quality Scorecard</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          {scorecard.map(s => (
            <div key={s.department_id} style={{
              padding: '16px', borderRadius: '12px',
              background: s.score >= 90 ? 'rgba(16,185,129,0.08)' : s.score >= 70 ? 'rgba(245,158,11,0.08)' : 'rgba(239,68,68,0.08)',
              border: `1px solid ${s.score >= 90 ? 'rgba(16,185,129,0.2)' : s.score >= 70 ? 'rgba(245,158,11,0.2)' : 'rgba(239,68,68,0.2)'}`
            }}>
              <div style={{ fontWeight: 600, marginBottom: '8px' }}>{s.department_name}</div>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: s.score >= 90 ? 'var(--status-normal)' : s.score >= 70 ? 'var(--status-warning)' : 'var(--status-critical)' }}>
                {s.score >= 0 ? `${s.score}%` : 'N/A'}
              </div>
              <div style={{ display: 'flex', gap: '6px', marginTop: '8px', flexWrap: 'wrap' }}>
                {Object.entries(s.checks).map(([type, status]) => (
                  <span key={type} style={{
                    padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem',
                    background: status === 'pass' ? 'rgba(16,185,129,0.15)' : status === 'warning' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                    color: status === 'pass' ? 'var(--status-normal)' : status === 'warning' ? 'var(--status-warning)' : 'var(--status-critical)'
                  }}>
                    {type}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Audit Log */}
      <section className="glass-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ fontSize: '1.1rem' }}>Audit Log</h2>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <Filter size={16} />
            <select value={filterType} onChange={e => setFilterType(e.target.value)} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
              <option value="">All checks</option>
              <option value="schema">Schema</option>
              <option value="null">Null</option>
              <option value="anomaly">Anomaly</option>
            </select>
          </div>
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <th style={{ padding: '8px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Time</th>
              <th style={{ padding: '8px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Department</th>
              <th style={{ padding: '8px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Check</th>
              <th style={{ padding: '8px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Status</th>
              <th style={{ padding: '8px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Message</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.slice(0, 50).map(log => (
              <tr key={log.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {new Date(log.created_at).toLocaleString()}
                </td>
                <td style={{ padding: '8px', fontSize: '0.85rem' }}>{log.department_name || '—'}</td>
                <td style={{ padding: '8px', fontSize: '0.85rem' }}>{log.check_type}</td>
                <td style={{ padding: '8px' }}>
                  <span style={{
                    padding: '2px 8px', borderRadius: '999px', fontSize: '0.75rem', fontWeight: 600,
                    background: log.status === 'pass' ? 'rgba(16,185,129,0.15)' : log.status === 'warning' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                    color: log.status === 'pass' ? 'var(--status-normal)' : log.status === 'warning' ? 'var(--status-warning)' : 'var(--status-critical)'
                  }}>
                    {log.status}
                  </span>
                </td>
                <td style={{ padding: '8px', fontSize: '0.85rem', maxWidth: '400px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {log.message}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredLogs.length === 0 && <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '12px' }}>No validation logs yet.</p>}
      </section>
    </div>
  );
};

export default AdminValidation;
