import React, { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, AlertTriangle, Shield, FileText, Activity, Brain } from 'lucide-react';
import KpiCard from '../components/KpiCard';
import InsightCard from '../components/InsightCard';
import { apiJson } from '../lib/api';

export default function ExecutiveAnalyticsPage() {
  const [overview, setOverview] = useState(null);
  const [insights, setInsights] = useState(null);
  const [briefing, setBriefing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, ins, br] = await Promise.all([
        apiJson('/api/executive/overview'),
        apiJson('/api/executive/insights'),
        apiJson('/api/executive/briefing'),
      ]);
      setOverview(ov);
      setInsights(ins);
      setBriefing(br);
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
        <div className="ea-skeleton ea-skeleton-title" style={{ width: '40%', marginBottom: '24px' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '24px' }}>
          {[1,2,3,4].map(i => <div key={i} className="ea-skeleton ea-skeleton-card" />)}
        </div>
      </div>
    );
  }

  if (error) {
    return <div className="ea-content"><div className="ea-alert ea-alert-danger">Error: {error}</div></div>;
  }

  if (!overview) return <div className="ea-content"><div className="ea-alert ea-alert-warning">No executive data available.</div></div>;

  const healthColor = overview.health_score >= 80 ? 'positive' : overview.health_score >= 60 ? 'warning' : 'negative';

  return (
    <div className="ea-content">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--ea-text-primary)', margin: 0 }}>Executive Analytics</h1>
          <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.875rem', margin: '4px 0 0' }}>
            Last updated: {new Date(overview.generated_at).toLocaleString('fr-FR')}
          </p>
        </div>
        <button className="ea-btn ea-btn-primary" onClick={fetchAll}>
          <Activity size={16} /> Refresh
        </button>
      </div>

      {/* Health Score + Status Summary */}
      <div className="ea-dashboard-grid ea-grid-kpis" style={{ marginBottom: '24px' }}>
        <KpiCard
          title="Health Score"
          value={overview.health_score}
          format="number"
          status={healthColor}
          subtitle="Overall system health"
          icon={<Shield size={20} />}
        />
        <KpiCard
          title="Total KPIs"
          value={overview.kpi_count}
          format="number"
          status="neutral"
          subtitle="Active metrics"
          icon={<Activity size={20} />}
        />
        <KpiCard
          title="Critical Anomalies"
          value={overview.anomalies?.filter(a => a.severity === 'CRITICAL').length || 0}
          format="number"
          status={overview.anomalies?.some(a => a.severity === 'CRITICAL') ? 'negative' : 'positive'}
          subtitle="Require investigation"
          icon={<AlertTriangle size={20} />}
        />
        <KpiCard
          title="Reports Generated"
          value={overview.recent_reports?.length || 0}
          format="number"
          status="neutral"
          subtitle="Recent briefings"
          icon={<FileText size={20} />}
        />
      </div>

      {/* Status Breakdown */}
      <div className="ea-card" style={{ marginBottom: '24px' }}>
        <div className="ea-card-header">
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Status Breakdown</h3>
        </div>
        <div className="ea-card-body">
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            {Object.entries(overview.status_summary || {}).map(([status, count]) => (
              <div key={status} style={{
                flex: '1 1 120px',
                padding: '16px',
                borderRadius: 'var(--ea-radius-md)',
                background: status === 'NORMAL' ? 'var(--ea-success-bg)' : status === 'WARNING' ? 'var(--ea-warning-bg)' : 'var(--ea-danger-bg)',
                textAlign: 'center',
              }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--ea-text-primary)' }}>{count}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)', textTransform: 'uppercase' }}>{status}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Risk Indicators */}
      {overview.risk_indicators?.length > 0 && (
        <div className="ea-card" style={{ marginBottom: '24px' }}>
          <div className="ea-card-header">
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Risk Indicators</h3>
          </div>
          <div className="ea-card-body">
            {overview.risk_indicators.map((risk, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: '12px',
                padding: '12px', background: 'var(--ea-bg)', borderRadius: 'var(--ea-radius-md)',
                marginBottom: '8px', borderLeft: `4px solid ${risk.level === 'HIGH' ? 'var(--ea-danger)' : 'var(--ea-warning)'}`,
              }}>
                <AlertTriangle size={18} style={{ color: risk.level === 'HIGH' ? 'var(--ea-danger)' : 'var(--ea-warning)' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{risk.category}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>{risk.indicator}</div>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-muted)' }}>{risk.action}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Executive Insights */}
      {insights?.insights?.length > 0 && (
        <div className="ea-card" style={{ marginBottom: '24px' }}>
          <div className="ea-card-header">
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Executive Insights</h3>
          </div>
          <div className="ea-card-body">
            {insights.insights.map((ins, i) => (
              <InsightCard
                key={i}
                title={ins.title}
                description={ins.description}
                type={ins.type}
                metric={ins.metric}
                value={ins.value}
                confidence={ins.priority === 'HIGH' ? 0.9 : ins.priority === 'MEDIUM' ? 0.75 : 0.6}
              />
            ))}
          </div>
        </div>
      )}

      {/* Top KPIs */}
      {overview.kpis?.length > 0 && (
        <div className="ea-card">
          <div className="ea-card-header">
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Top KPIs</h3>
          </div>
          <div className="ea-card-body" style={{ overflowX: 'auto' }}>
            <table className="ea-table">
              <thead>
                <tr>
                  <th>KPI Name</th>
                  <th>Latest Value</th>
                  <th>Status</th>
                  <th>DoD %</th>
                  <th>WoW %</th>
                  <th>Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {overview.kpis.map((kpi, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{kpi.kpi_name}</td>
                    <td>{kpi.latest_value != null ? Number(kpi.latest_value).toLocaleString('fr-FR') : '—'}</td>
                    <td>
                      <span className={`ea-badge ${kpi.latest_status === 'NORMAL' ? 'ea-badge-success' : kpi.latest_status === 'WARNING' ? 'ea-badge-warning' : 'ea-badge-danger'}`}>
                        {kpi.latest_status}
                      </span>
                    </td>
                    <td style={{ color: (kpi.dod_pct || 0) >= 0 ? 'var(--ea-success)' : 'var(--ea-danger)' }}>
                      {(kpi.dod_pct || 0) >= 0 ? '+' : ''}{kpi.dod_pct?.toFixed(1) || '0.0'}%
                    </td>
                    <td style={{ color: (kpi.wow_pct || 0) >= 0 ? 'var(--ea-success)' : 'var(--ea-danger)' }}>
                      {(kpi.wow_pct || 0) >= 0 ? '+' : ''}{kpi.wow_pct?.toFixed(1) || '0.0'}%
                    </td>
                    <td style={{ color: 'var(--ea-text-muted)', fontSize: '0.75rem' }}>
                      {kpi.recorded_at ? new Date(kpi.recorded_at).toLocaleDateString('fr-FR') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}