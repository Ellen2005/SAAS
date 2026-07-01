import React, { useEffect, useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, XCircle, FileText, RefreshCw, TrendingUp, MessageSquare } from 'lucide-react';
import { apiJson } from '../lib/api';
import KpiCard from '../components/KpiCard';

export default function DataQualityPage() {
  const [score, setScore] = useState(null);
  const [issues, setIssues] = useState(null);
  const [report, setReport] = useState(null);
  const [aiFeedback, setAiFeedback] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [scRes, isRes, rpRes] = await Promise.all([
        apiJson('/api/data-quality/score'),
        apiJson('/api/data-quality/issues'),
        apiJson('/api/data-quality/report'),
      ]);
      setScore(scRes);
      setIssues(isRes);
      setReport(rpRes);

      // Load AI feedback summary (non-blocking, admin-only)
      apiJson('/api/admin/ai/feedback/summary?days=30').then(setAiFeedback).catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  if (loading) {
    return (
      <div className="ea-content">
        <div className="ea-skeleton ea-skeleton-title" style={{ width: '30%', marginBottom: '24px' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '24px' }}>
          {[1,2,3,4].map(i => <div key={i} className="ea-skeleton ea-skeleton-card" />)}
        </div>
      </div>
    );
  }

  if (error) {
    return <div className="ea-content"><div className="ea-alert ea-alert-danger">Error: {error}</div></div>;
  }

  if (!score) return <div className="ea-content"><div className="ea-alert ea-alert-warning">No data quality information available.</div></div>;

  const gradeColor = score.score >= 90 ? 'positive' : score.score >= 70 ? 'warning' : 'negative';

  return (
    <div className="ea-content">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--ea-text-primary)', margin: 0 }}>Data Quality Center</h1>
          <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.875rem', margin: '4px 0 0' }}>
            Last updated: {new Date(score.generated_at).toLocaleString('fr-FR')}
          </p>
        </div>
        <button className="ea-btn ea-btn-primary" onClick={fetchAll}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {/* Overall Score */}
      <div className="ea-dashboard-grid ea-grid-kpis" style={{ marginBottom: '24px' }}>
        <KpiCard
          title="Overall Quality Score"
          value={score.score}
          format="number"
          status={gradeColor}
          subtitle={`Grade: ${score.grade}`}
          icon={<Shield size={20} />}
        />
        <KpiCard
          title="Total Checks"
          value={score.checks?.length || 0}
          format="number"
          status="neutral"
          subtitle="Quality dimensions"
          icon={<FileText size={20} />}
        />
        <KpiCard
          title="Issues Found"
          value={issues?.issue_count || 0}
          format="number"
          status={(issues?.issue_count || 0) > 0 ? 'warning' : 'positive'}
          subtitle="Require attention"
          icon={<AlertTriangle size={20} />}
        />
        <KpiCard
          title="Recommendations"
          value={score.recommendations?.length || 0}
          format="number"
          status="neutral"
          subtitle="Action items"
          icon={<CheckCircle size={20} />}
        />
      </div>

      {/* Quality Checks */}
      <div className="ea-card" style={{ marginBottom: '24px' }}>
        <div className="ea-card-header">
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Quality Checks</h3>
        </div>
        <div className="ea-card-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            {(score.checks || []).map((check, i) => (
              <div key={i} style={{
                padding: '16px',
                borderRadius: 'var(--ea-radius-md)',
                background: 'var(--ea-bg)',
                border: '1px solid var(--ea-border)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  {check.status === 'pass' ? <CheckCircle size={16} style={{ color: 'var(--ea-success)' }} /> :
                   check.status === 'warning' ? <AlertTriangle size={16} style={{ color: 'var(--ea-warning)' }} /> :
                   <XCircle size={16} style={{ color: 'var(--ea-danger)' }} />}
                  <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{check.check}</span>
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--ea-text-primary)', marginBottom: '4px' }}>
                  {check.score}/{check.max_score}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>{check.message}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recommendations */}
      {score.recommendations?.length > 0 && (
        <div className="ea-card" style={{ marginBottom: '24px' }}>
          <div className="ea-card-header">
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Recommendations</h3>
          </div>
          <div className="ea-card-body">
            {score.recommendations.map((rec, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: '12px',
                padding: '12px', background: 'var(--ea-bg)', borderRadius: 'var(--ea-radius-md)',
                marginBottom: '8px', borderLeft: `4px solid ${rec.priority === 'HIGH' ? 'var(--ea-danger)' : 'var(--ea-warning)'}`,
              }}>
                <AlertTriangle size={18} style={{ color: rec.priority === 'HIGH' ? 'var(--ea-danger)' : 'var(--ea-warning)' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{rec.area}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>{rec.action}</div>
                </div>
                <span className={`ea-badge ${rec.priority === 'HIGH' ? 'ea-badge-danger' : 'ea-badge-warning'}`}>
                  {rec.priority}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Issues Table */}
      {issues?.issues?.length > 0 && (
        <div className="ea-card">
          <div className="ea-card-header">
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Data Quality Issues ({issues.issue_count})</h3>
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
                {issues.issues.slice(0, 50).map((issue, i) => (
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
        </div>
      )}

      {/* AI Feedback Summary (Enterprise) */}
      {aiFeedback && aiFeedback.total_feedback > 0 && (
        <div className="ea-card" style={{ marginTop: '24px' }}>
          <div className="ea-card-header">
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <MessageSquare size={16} /> AI Response Quality (Last 30 Days)
            </h3>
          </div>
          <div className="ea-card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', marginBottom: '16px' }}>
              <div style={{ padding: '14px', background: 'var(--ea-bg)', borderRadius: 'var(--ea-radius-md)', border: '1px solid var(--ea-border)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>Total Feedback</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{aiFeedback.total_feedback}</div>
              </div>
              <div style={{ padding: '14px', background: 'var(--ea-bg)', borderRadius: 'var(--ea-radius-md)', border: '1px solid var(--ea-border)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>Avg Rating</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{aiFeedback.avg_rating}/5</div>
              </div>
              <div style={{ padding: '14px', background: 'var(--ea-bg)', borderRadius: 'var(--ea-radius-md)', border: '1px solid var(--ea-border)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>Satisfaction</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: aiFeedback.satisfaction_rate >= 70 ? 'var(--ea-success)' : 'var(--ea-warning)' }}>
                  {aiFeedback.satisfaction_rate}%
                </div>
              </div>
              <div style={{ padding: '14px', background: 'var(--ea-bg)', borderRadius: 'var(--ea-radius-md)', border: '1px solid var(--ea-border)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>Thumbs Up / Down</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>
                  <span style={{ color: 'var(--ea-success)' }}>{aiFeedback.thumbs_up}</span>
                  {' / '}
                  <span style={{ color: 'var(--ea-danger)' }}>{aiFeedback.thumbs_down}</span>
                </div>
              </div>
            </div>

            {aiFeedback.by_category && Object.keys(aiFeedback.by_category).length > 0 && (
              <div>
                <h4 style={{ fontSize: '0.85rem', marginBottom: '8px', color: 'var(--ea-text-secondary)' }}>By Category</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px' }}>
                  {Object.entries(aiFeedback.by_category).map(([cat, stats]) => (
                    <div key={cat} style={{ padding: '10px', background: 'var(--ea-bg)', borderRadius: 'var(--ea-radius-md)', border: '1px solid var(--ea-border)', textAlign: 'center' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)', textTransform: 'capitalize' }}>{cat}</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{stats.avg_rating}/5</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--ea-text-secondary)' }}>{stats.count} responses</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {aiFeedback.recent_comments?.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <h4 style={{ fontSize: '0.85rem', marginBottom: '8px', color: 'var(--ea-text-secondary)' }}>Recent Feedback</h4>
                <div style={{ display: 'grid', gap: '8px' }}>
                  {aiFeedback.recent_comments.slice(0, 5).map((fb, i) => (
                    <div key={i} style={{ padding: '10px', background: 'var(--ea-bg)', borderRadius: 'var(--ea-radius-md)', borderLeft: `3px solid ${fb.rating >= 4 ? 'var(--ea-success)' : fb.rating <= 2 ? 'var(--ea-danger)' : 'var(--ea-warning)'}` }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>
                        {'⭐'.repeat(fb.rating)} {fb.category && `• ${fb.category}`}
                      </div>
                      <div style={{ fontSize: '0.8rem', marginTop: '4px' }}>{fb.comment}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}