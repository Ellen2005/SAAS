import React, { useEffect, useState } from 'react';
import { AlertTriangle, BarChart3, ChevronDown, ChevronRight, Database, RefreshCcw, Users } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { apiJson } from '../lib/api';

const AdminDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [data, setData] = useState(null);
  const [scorecard, setScorecard] = useState([]);
  const [expandedDept, setExpandedDept] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState(null);
  const [lineageData, setLineageData] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [summary, validation] = await Promise.all([
          apiJson('/api/admin/summary'),
          apiJson('/api/admin/validation/scorecard'),
        ]);

        setData(summary);
        setScorecard(validation.scorecard || []);

        if (summary.timeline?.length) {
          setSelectedPeriod(summary.timeline[summary.timeline.length - 1]);
        }
      } catch (error) {
        console.error('Failed to load admin dashboard', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const handleSync = async () => {
    if (syncing) return;
    setSyncing(true);
    try {
      await fetch('/api/etl/trigger', { method: 'POST' });
      // Wait a moment then reload data
      setTimeout(() => {
        setLoading(true);
        const loadData = async () => {
          try {
            const [summary, validation] = await Promise.all([
              apiJson('/api/admin/summary'),
              apiJson('/api/admin/validation/scorecard'),
            ]);
            setData(summary);
            setScorecard(validation.scorecard || []);
            if (summary.timeline?.length) {
              setSelectedPeriod(summary.timeline[summary.timeline.length - 1]);
            }
          } catch (error) {
            console.error('Failed to reload admin dashboard', error);
          } finally {
            setLoading(false);
          }
        };
        loadData();
      }, 2000);
    } catch (error) {
      console.error('Sync failed', error);
      setSyncing(false);
    }
  };

  const handleLineage = async (kpiId) => {
    try {
      const result = await apiJson(`/api/admin/lineage/${kpiId}`);
      setLineageData(result);
    } catch (error) {
      console.error('Failed to load lineage', error);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
        <RefreshCcw size={48} style={{ animation: 'spin 1s linear infinite' }} />
        <span style={{ marginLeft: '16px', fontSize: '1.2rem' }}>Loading Admin Dashboard...</span>
      </div>
    );
  }

  const timeline = (data?.timeline || []).map((period) => ({
    period: period.period,
    total_value: period.total_value,
  }));

  return (
    <div style={{ display: 'grid', gap: '24px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <BarChart3 color="var(--primary-color)" /> Executive Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Combined view across {data?.total_departments || 0} departments.
          </p>
        </div>
        <button 
          className="btn btn-primary"
          onClick={handleSync}
          disabled={syncing}
          style={{ display: 'flex', gap: '8px', alignItems: 'center', opacity: syncing ? 0.7 : 1 }}
        >
          <RefreshCcw size={16} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
          {syncing ? 'Syncing...' : 'Sync Now'}
        </button>
      </header>
      <style>{'@keyframes spin{100%{transform:rotate(360deg)}}'}</style>

      <section className="glass-panel">
        <h2 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>Company Revenue Timeline</h2>
        {timeline.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="period" stroke="var(--text-secondary)" fontSize={12} />
              <YAxis stroke="var(--text-secondary)" fontSize={12} />
              <Tooltip
                contentStyle={{ background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '8px' }}
                formatter={(value) => [Number(value).toLocaleString(), 'Revenue']}
              />
              <Bar
                dataKey="total_value"
                fill="var(--primary-color)"
                radius={[4, 4, 0, 0]}
                onClick={(_, index) => setSelectedPeriod(data.timeline[index])}
              />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p style={{ color: 'var(--text-secondary)' }}>No timeline data yet. Run department syncs first.</p>
        )}
      </section>

      {selectedPeriod && (
        <section className="glass-panel">
          <h2 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>Drill-down: {selectedPeriod.period}</h2>
          <div style={{ display: 'grid', gap: '10px' }}>
            {Object.entries(selectedPeriod.department_breakdown || {}).map(([department, value]) => (
              <div key={department} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', borderRadius: '10px', background: 'rgba(255,255,255,0.03)' }}>
                <span>{department}</span>
                <strong>{Number(value).toLocaleString()}</strong>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 style={{ fontSize: '1.1rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Users size={18} /> Department Breakdown
        </h2>
        <div style={{ display: 'grid', gap: '16px' }}>
          {(data?.departments || []).map((department) => (
            <div key={department.department_id} className="glass-panel" style={{ cursor: 'pointer' }}>
              <div
                onClick={() => setExpandedDept(expandedDept === department.department_id ? null : department.department_id)}
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {expandedDept === department.department_id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <h3 style={{ fontSize: '1rem' }}>{department.department_name}</h3>
                  {department.anomaly_count > 0 && (
                    <span style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--status-critical)', padding: '2px 8px', borderRadius: '999px', fontSize: '0.75rem' }}>
                      {department.anomaly_count} anomalies
                    </span>
                  )}
                </div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Last sync: {department.last_sync || 'Never'}</span>
              </div>

              {expandedDept === department.department_id && (
                <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
                  {department.kpis.length > 0 ? (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                      {department.kpis.map((kpi) => (
                        <div
                          key={kpi.id}
                          style={{ padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', cursor: 'pointer' }}
                          onClick={() => handleLineage(kpi.id)}
                        >
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{kpi.kpi_name.replaceAll('_', ' ')}</div>
                          <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{Number(kpi.value).toLocaleString()}</div>
                          <div style={{ fontSize: '0.75rem', color: (kpi.dod_pct || 0) >= 0 ? 'var(--status-normal)' : 'var(--status-critical)' }}>
                            {(kpi.dod_pct || 0) >= 0 ? '▲' : '▼'} {Math.abs(kpi.dod_pct || 0).toFixed(1)}% DoD
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ color: 'var(--text-secondary)' }}>No KPI data yet for this department.</p>
                  )}

                  {department.narrative_preview && (
                    <p style={{ marginTop: '12px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                      {department.narrative_preview}
                    </p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="glass-panel">
        <h2 style={{ fontSize: '1.1rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle size={18} /> Data Quality Scorecard
        </h2>
        <div style={{ display: 'grid', gap: '12px' }}>
          {scorecard.map((item) => (
            <div key={item.department_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
              <span style={{ fontWeight: 600 }}>{item.department_name}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                {Object.entries(item.checks).map(([type, status]) => (
                  <span
                    key={type}
                    style={{
                      padding: '2px 8px',
                      borderRadius: '999px',
                      fontSize: '0.75rem',
                      background: status === 'pass' ? 'rgba(16,185,129,0.15)' : status === 'warning' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                      color: status === 'pass' ? 'var(--status-normal)' : status === 'warning' ? 'var(--status-warning)' : 'var(--status-critical)',
                    }}
                  >
                    {type}: {status}
                  </span>
                ))}
                <strong style={{ color: item.score >= 90 ? 'var(--status-normal)' : item.score >= 70 ? 'var(--status-warning)' : 'var(--status-critical)' }}>
                  {item.score >= 0 ? `${item.score}%` : 'N/A'}
                </strong>
              </div>
            </div>
          ))}
        </div>
      </section>

      {lineageData && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}
          onClick={() => setLineageData(null)}
        >
          <div className="glass-panel" style={{ maxWidth: '760px', width: '92%', maxHeight: '80vh', overflow: 'auto' }} onClick={(event) => event.stopPropagation()}>
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Database size={18} /> Lineage: {lineageData.kpi?.kpi_name?.replaceAll('_', ' ')}
            </h3>

            <div style={{ marginBottom: '16px', padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
              <div><strong>Department:</strong> {lineageData.department_name || 'Unknown'}</div>
              <div><strong>Value:</strong> {Number(lineageData.kpi?.value || 0).toLocaleString()}</div>
              <div><strong>Source Records:</strong> {lineageData.source_record_count}</div>
              <div><strong>Recorded:</strong> {lineageData.kpi?.recorded_at}</div>
            </div>

            {lineageData.source_records?.length > 0 ? (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.84rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                    {Object.keys(lineageData.source_records[0]).map((column) => (
                      <th key={column} style={{ padding: '8px', textAlign: 'left', color: 'var(--text-secondary)' }}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {lineageData.source_records.slice(0, 20).map((record, index) => (
                    <tr key={index} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      {Object.values(record).map((value, valueIndex) => (
                        <td key={valueIndex} style={{ padding: '8px' }}>{String(value).substring(0, 60)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ color: 'var(--text-secondary)' }}>No raw source rows were stored for this KPI yet.</p>
            )}

            <button className="btn btn-outline" style={{ marginTop: '16px' }} onClick={() => setLineageData(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
