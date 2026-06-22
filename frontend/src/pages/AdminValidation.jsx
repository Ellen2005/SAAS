import React, { useState, useEffect } from 'react';
import { AlertTriangle, Filter, Shield, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { apiJson } from '../lib/api';

const AdminValidation = () => {
  const [scorecard, setScorecard] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('');
  const [qualityScore, setQualityScore] = useState(null);
  const [qualityIssues, setQualityIssues] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sc, lg, qs, qi] = await Promise.all([
          apiJson('/api/admin/validation/scorecard'),
          apiJson('/api/admin/validation/logs?limit=100'),
          apiJson('/api/data-quality/score').catch(() => null),
          apiJson('/api/data-quality/issues').catch(() => null),
        ]);
        setScorecard(sc.scorecard || []);
        setLogs(lg.logs || []);
        setQualityScore(qs);
        setQualityIssues(qi);
      } catch (err) { console.error(err); } finally { setLoading(false); }
    };
    fetchData();
  }, []);

  const filteredLogs = logs.filter(log => {
    if (filterType && log.check_type !== filterType) return false;
    return true;
  });

  if (loading) return <p style={{ color: 'var(--ea-text-secondary)' }}>Loading validation data...</p>;

  const gradeColor = qualityScore?.grade >= 'A' ? '#10b981' : qualityScore?.grade >= 'C' ? '#f59e0b' : '#ef4444';

  return (
    <div>
      <header style={{ marginBottom: '32px' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <AlertTriangle color="var(--ea-primary)" /> Data Quality Audit
        </h1>
        <p style={{ color: 'var(--ea-text-secondary)' }}>Cross-department validation scores, data quality metrics, and detailed audit logs.</p>
      </header>

      {/* Data Quality Overview */}
      {qualityScore && (
        <section className="ea-card" style={{ marginBottom: '24px' }}>
          <div className="ea-card-header">
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Shield size={18} color="var(--ea-primary)" /> Data Quality Center
            </h3>
          </div>
          <div className="ea-card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '20px' }}>
              <div className="ea-kpi-card">
                <div className="ea-kpi-label">Overall Quality Score</div>
                <div className="ea-kpi-value" style={{ color: gradeColor }}>{qualityScore.score}/100</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--ea-text-secondary)', marginTop: 4 }}>Grade: {qualityScore.grade}</div>
              </div>
              <div className="ea-kpi-card">
                <div className="ea-kpi-label">Total Checks</div>
                <div className="ea-kpi-value">{qualityScore.checks?.length || 0}</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--ea-text-secondary)', marginTop: 4 }}>Quality dimensions</div>
              </div>
              <div className="ea-kpi-card">
                <div className="ea-kpi-label">Issues Found</div>
                <div className="ea-kpi-value" style={{ color: (qualityIssues?.issue_count || 0) > 0 ? '#f59e0b' : '#10b981' }}>
                  {qualityIssues?.issue_count || 0}
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--ea-text-secondary)', marginTop: 4 }}>Require attention</div>
              </div>
              <div className="ea-kpi-card">
                <div className="ea-kpi-label">Recommendations</div>
                <div className="ea-kpi-value">{qualityScore.recommendations?.length || 0}</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--ea-text-secondary)', marginTop: 4 }}>Action items</div>
              </div>
            </div>

            {/* Quality Checks */}
            {qualityScore.checks?.length > 0 && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '16px' }}>
                {qualityScore.checks.map((check, i) => (
                  <div key={i} style={{
                    padding: '14px',
                    borderRadius: 'var(--ea-radius-md)',
                    background: 'var(--ea-bg)',
                    border: '1px solid var(--ea-border)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      {check.status === 'pass' ? <CheckCircle size={16} style={{ color: 'var(--ea-success)' }} /> :
                       check.status === 'warning' ? <AlertTriangle size={16} style={{ color: 'var(--ea-warning)' }} /> :
                       <XCircle size={16} style={{ color: 'var(--ea-danger)' }} />}
                      <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{check.check}</span>
                    </div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--ea-text-primary)', marginBottom: '4px' }}>
                      {check.score}/{check.max_score}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>{check.message}</div>
                  </div>
                ))}
              </div>
            )}

            {/* Recommendations */}
            {qualityScore.recommendations?.length > 0 && (
              <div>
                <h4 style={{ fontSize: '0.9rem', marginBottom: '10px', color: 'var(--ea-text-primary)' }}>Recommendations</h4>
                {qualityScore.recommendations.map((rec, i) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: '12px',
                    padding: '10px', background: 'var(--ea-bg)', borderRadius: 'var(--ea-radius-md)',
                    marginBottom: '6px', borderLeft: `4px solid ${rec.priority === 'HIGH' ? 'var(--ea-danger)' : 'var(--ea-warning)'}`,
                  }}>
                    <AlertTriangle size={16} style={{ color: rec.priority === 'HIGH' ? 'var(--ea-danger)' : 'var(--ea-warning)' }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{rec.area}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>{rec.action}</div>
                    </div>
                    <span className={`ea-badge ${rec.priority === 'HIGH' ? 'ea-badge-danger' : 'ea-badge-warning'}`}>
                      {rec.priority}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      {/* Scorecard Grid */}
      <section className="ea-card" style={{ marginBottom: '24px' }}>
        <div className="ea-card-header">
          <h2 style={{ fontSize: '1.1rem', margin: 0 }}>Quality Scorecard</h2>
        </div>
        <div className="ea-card-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            {scorecard.map(s => (
              <div key={s.department_id} style={{
                padding: '16px', borderRadius: '12px',
                background: s.score >= 90 ? 'rgba(16,185,129,0.08)' : s.score >= 70 ? 'rgba(245,158,11,0.08)' : 'rgba(239,68,68,0.08)',
                border: `1px solid ${s.score >= 90 ? 'rgba(16,185,129,0.2)' : s.score >= 70 ? 'rgba(245,158,11,0.2)' : 'rgba(239,68,68,0.2)'}`
              }}>
                <div style={{ fontWeight: 600, marginBottom: '8px' }}>{s.department_name}</div>
                <div style={{ fontSize: '2rem', fontWeight: 700, color: s.score >= 90 ? 'var(--ea-success)' : s.score >= 70 ? 'var(--ea-warning)' : 'var(--ea-danger)' }}>
                  {s.score >= 0 ? `${s.score}%` : 'N/A'}
                </div>
                <div style={{ display: 'flex', gap: '6px', marginTop: '8px', flexWrap: 'wrap' }}>
                  {Object.entries(s.checks).map(([type, status]) => (
                    <span key={type} style={{
                      padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem',
                      background: status === 'pass' ? 'rgba(16,185,129,0.15)' : status === 'warning' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                      color: status === 'pass' ? 'var(--ea-success)' : status === 'warning' ? 'var(--ea-warning)' : 'var(--ea-danger)'
                    }}>
                      {type}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Issues Table */}
      {qualityIssues?.issues?.length > 0 && (
        <section className="ea-card" style={{ marginBottom: '24px' }}>
          <div className="ea-card-header">
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Data Quality Issues ({qualityIssues.issue_count})</h3>
          </div>
          <div className="ea-card-body" style={{ overflowX: 'auto' }}>
            <table className="ea-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Field</th>
                  <th>Severity</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {qualityIssues.issues.slice(0, 50).map((issue, i) => (
                  <tr key={i}>
                    <td><span className="ea-badge ea-badge-info">{issue.type}</span></td>
                    <td style={{ fontFamily: 'var(--ea-font-mono)', fontSize: '0.8rem' }}>{issue.field}</td>
                    <td>
                      <span className={`ea-badge ${issue.severity === 'high' ? 'ea-badge-danger' : issue.severity === 'medium' ? 'ea-badge-warning' : 'ea-badge-info'}`}>
                        {issue.severity}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.8rem' }}>{issue.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Audit Log */}
      <section className="ea-card">
        <div className="ea-card-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <h2 style={{ fontSize: '1.1rem', margin: 0 }}>Audit Log</h2>
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
        </div>
        <div className="ea-card-body" style={{ overflowX: 'auto' }}>
          <table className="ea-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Department</th>
                <th>Check</th>
                <th>Status</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.slice(0, 50).map(log => (
                <tr key={log.id}>
                  <td style={{ fontSize: '0.8rem', color: 'var(--ea-text-secondary)' }}>
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td style={{ fontSize: '0.85rem' }}>{log.department_name || '—'}</td>
                  <td style={{ fontSize: '0.85rem' }}>{log.check_type}</td>
                  <td>
                    <span className={`ea-badge ${log.status === 'pass' ? 'ea-badge-success' : log.status === 'warning' ? 'ea-badge-warning' : 'ea-badge-danger'}`}>
                      {log.status}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.85rem', maxWidth: '400px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {log.message}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredLogs.length === 0 && <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.9rem', marginTop: '12px' }}>No validation logs yet.</p>}
        </div>
      </section>
    </div>
  );
};

export default AdminValidation;