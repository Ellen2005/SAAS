import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, ArrowDownRight, ArrowUpRight, FileText, RefreshCcw, TrendingUp, Sparkles, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useAuth } from '../lib/authContext';
import { apiFetch, apiJson, API_URL } from '../lib/api';
import { useLang } from '../lib/i18n';
import ValidationWarnings from '../components/ValidationWarnings';
import ChartRenderer from '../components/ChartRenderer';

const DASHBOARD_CACHE_KEY = 'saas.dashboard.lastSummary.v1';

const readDashboardCache = () => {
  try {
    const raw = localStorage.getItem(DASHBOARD_CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const writeDashboardCache = (payload) => {
  try {
    localStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify(payload));
  } catch {
    // Cache writes can fail when storage is disabled or full.
  }
};

const EMPTY_DATA = { kpis: [], anomalies: [], narrative: '', last_refreshed: '', validation: [] };

const Dashboard = () => {
  const { user, isManager } = useAuth();
  const { t } = useLang();
  const navigate = useNavigate();

  const SYNC_STATUS_LABELS = {
    FETCHING_DATA: t('dashboard_sync_step1'),
    MAPPING_FIELDS: t('dashboard_sync_step2'),
    VALIDATING_DATA: t('dashboard_sync_step3'),
    ANALYZING_ANOMALIES: t('dashboard_sync_step4'),
    LOADING_DATA: t('dashboard_sync_step5'),
    GENERATING_AI_NARRATIVE: t('dashboard_sync_step6'),
    SENDING_EMAILS: t('dashboard_sync_email'),
    VALIDATION_FAILED: t('dashboard_sync_failed'),
  };

  // Load cache immediately — no spinner on open
  const [data, setData] = useState(() => readDashboardCache() || EMPTY_DATA);
  const [loading, setLoading] = useState(!readDashboardCache());
  const [syncing, setSyncing] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Syncing...');
  const [forecasts, setForecasts] = useState([]);
  const [schemaSyncing, setSchemaSyncing] = useState(false);
  const [schemaSyncResult, setSchemaSyncResult] = useState(null);

  // Keepalive ping — wakes up free-tier backend before user needs it
  useEffect(() => {
    fetch(`${API_URL}/api/ping`).catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    try {
      if (!user) return;
      const [result, forecastResult] = await Promise.all([
        apiJson('/api/summary'),
        apiJson('/api/forecasts'),
      ]);
      setData(result);
      writeDashboardCache(result);
      setForecasts(forecastResult.forecasts || []);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      const cached = readDashboardCache();
      if (cached) setData(cached);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (user) fetchData();
  }, [user, fetchData]);

  // Build chart series: one line per KPI, merging historical (last 7 days) + forecast (next 7 days)
  const chartData = React.useMemo(() => {
    if (!forecasts.length && !data.kpis.length) return [];

    // Collect all unique dates from forecasts
    const dateSet = new Set(forecasts.map((f) => f.forecast_date));
    const dateMap = {};
    dateSet.forEach((d) => { dateMap[d] = { date: d }; });

    // Fill in predicted values per KPI
    forecasts.forEach((f) => {
      const key = f.kpi_name.replace(/_/g, ' ');
      if (dateMap[f.forecast_date]) {
        dateMap[f.forecast_date][key] = f.predicted_value;
        dateMap[f.forecast_date][`${key}_lower`] = f.lower_bound;
        dateMap[f.forecast_date][`${key}_upper`] = f.upper_bound;
      }
    });

    return Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date));
  }, [forecasts, data.kpis]);

  const forecastKpiNames = React.useMemo(() => {
    return [...new Set(forecasts.map((f) => f.kpi_name.replace(/_/g, ' ')))];
  }, [forecasts]);

  const KPI_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444'];

  const handleSchemaSync = async () => {
    if (schemaSyncing || !user) return;
    setSchemaSyncing(true);
    setSchemaSyncResult(null);
    try {
      const out = await apiJson('/api/introspect/sync-to-kpis', {
        method: 'POST',
        body: JSON.stringify({ refresh: true }),
      });
      setSchemaSyncResult(out);
      await fetchData();
    } catch (err) {
      setSchemaSyncResult({ error: err.message || 'Sync failed.' });
    } finally {
      setSchemaSyncing(false);
    }
  };

  const handleSync = async () => {
    if (syncing || !user) return;
    setSyncing(true);
    setStatusMessage('Initializing sync...');

    try {
      await apiFetch('/api/etl/trigger', { method: 'POST' });

      for (let attempt = 0; attempt < 30; attempt += 1) {
        if (attempt > 0) await new Promise((r) => setTimeout(r, 4000));

        try {
          const statusData = await apiJson('/api/etl/status');
          const nextStatus = statusData.status || 'IDLE';

          if (nextStatus === 'IDLE') {
            if (attempt === 0) { setStatusMessage('Starting background worker...'); continue; }
            await fetchData();
            setStatusMessage('Report generated.');
            return;
          }

          setStatusMessage(SYNC_STATUS_LABELS[nextStatus] || 'Processing...');
          if (nextStatus === 'VALIDATION_FAILED') { await fetchData(); return; }
        } catch {
          setStatusMessage('Waiting for sync status...');
        }
      }
      setStatusMessage('Sync timed out. Check backend logs.');
    } catch (err) {
      setStatusMessage(err.message || 'Sync failed.');
    } finally {
      setSyncing(false);
    }
  };

  const hasData = data.kpis.length > 0 || data.narrative;

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
        <RefreshCcw size={32} style={{ animation: 'spin 1s linear infinite', marginRight: '12px' }} />
        <style>{'@keyframes spin{100%{transform:rotate(360deg)}}'}</style>
        Loading analytics...
      </div>
    );
  }

  return (
    <div className="dashboard">
      <style>{'@keyframes spin{100%{transform:rotate(360deg)}}'}</style>

      <header style={{ marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1>{t('dashboard_title')}</h1>
          <p>
            {data.last_refreshed && data.last_refreshed !== 'Never'
              ? `${t('dashboard_last_report')} ${data.last_refreshed}`
              : t('dashboard_no_report')}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button className="btn btn-outline" onClick={() => navigate('/reports')} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <FileText size={16} /> {t('dashboard_report_history')}
          </button>
          {isManager && (
            <>
              <button className="btn btn-outline" onClick={() => navigate('/query')} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <Search size={16} /> Query
              </button>
              <button className="btn btn-outline" onClick={() => navigate('/reports/custom')} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <Sparkles size={16} /> {t('custom_report_title')}
              </button>
              <button className="btn btn-primary" onClick={handleSchemaSync} disabled={schemaSyncing || syncing} style={{ display: 'flex', gap: '8px', alignItems: 'center', opacity: schemaSyncing ? 0.7 : 1, background: 'linear-gradient(135deg, var(--primary-color) 0%, #4f46e5 100%)', border: 'none' }}>
                <RefreshCcw size={16} style={{ animation: schemaSyncing ? 'spin 1s linear infinite' : 'none' }} />
                {schemaSyncing ? 'Syncing Schema…' : 'Sync Schema'}
              </button>
              <button className="btn btn-outline" onClick={handleSync} disabled={syncing || schemaSyncing} style={{ display: 'flex', gap: '8px', alignItems: 'center', opacity: syncing ? 0.7 : 1 }}>
                <RefreshCcw size={16} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
                {syncing ? statusMessage : t('dashboard_generate')}
              </button>
            </>
          )}
        </div>
      </header>

      {!hasData && (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '48px', marginBottom: '32px' }}>
          <FileText size={48} color="var(--text-secondary)" style={{ marginBottom: '16px' }} />
          <h3 style={{ marginBottom: '8px' }}>{t('dashboard_no_data_title')}</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>{t('dashboard_no_data_desc')}</p>
          {isManager && (
            <button className="btn btn-primary" onClick={handleSync} disabled={syncing} style={{ display: 'inline-flex', gap: '8px' }}>
              <RefreshCcw size={16} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
              {syncing ? statusMessage : t('dashboard_generate')}
            </button>
          )}
        </div>
      )}

      {schemaSyncResult && (
        <div className="glass-panel" style={{
          padding: '16px',
          marginBottom: '24px',
          background: schemaSyncResult.error ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
          border: `1px solid ${schemaSyncResult.error ? 'var(--status-critical)' : 'var(--status-normal)'}`,
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '16px'
        }}>
          <div>
            <strong style={{ color: schemaSyncResult.error ? 'var(--status-critical)' : 'var(--status-normal)', display: 'block', marginBottom: '4px' }}>
              {schemaSyncResult.error ? 'Schema Sync Failed' : 'Schema Sync Successful!'}
            </strong>
            <span style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
              {schemaSyncResult.error
                ? schemaSyncResult.error
                : `Successfully mapped and synced ${schemaSyncResult.synced || 0} KPI(s) from your connected database. (Skipped ${schemaSyncResult.skipped || 0}, Failed ${schemaSyncResult.failed || 0})`}
            </span>
          </div>
          <button className="btn btn-outline" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => setSchemaSyncResult(null)}>
            Dismiss
          </button>
        </div>
      )}

      <ValidationWarnings validations={data.validation || []} />

      {data.kpi_mode && (
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 16 }}>
          Data mode:{' '}
          <strong style={{ color: 'var(--primary-color)' }}>
            {data.kpi_mode.mode === 'configured'
              ? 'Admin-defined KPIs'
              : data.kpi_mode.mode === 'auto'
                ? 'Auto-discovered from your database'
                : 'Database overview'}
          </strong>
          {data.kpi_mode.admin_field_count > 0 && (
            <span> — {data.kpi_mode.mapped_count || 0} of {data.kpi_mode.admin_field_count} KPI fields mapped</span>
          )}
        </p>
      )}

      {data.snapshot_chart && data.kpis.length > 0 && (
        <section className="glass-panel" style={{ marginBottom: '32px' }}>
          <ChartRenderer spec={data.snapshot_chart} height={Math.min(360, 80 + data.kpis.length * 28)} />
        </section>
      )}

      {data.narrative && (
        <section className="glass-panel" style={{ marginBottom: '32px', borderLeft: '4px solid var(--primary-color)' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--primary-color)' }}>✦</span> {t('dashboard_ai_narrative')}
          </h2>
          <p style={{ fontSize: '1.05rem', lineHeight: '1.7', color: 'var(--text-primary)' }}>
            {data.narrative}
          </p>
        </section>
      )}

      {data.kpis.length > 0 && (
        <div className="dashboard-grid">
          {data.kpis.map((kpi) => (
            <div key={kpi.id} className="glass-panel">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{kpi.kpi_name.replaceAll('_', ' ')}</span>
                <span className={`badge badge-${kpi.status?.toLowerCase()}`}>{kpi.status}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
                <span style={{ fontSize: '2.5rem', fontWeight: 700, letterSpacing: '-0.03em' }}>{kpi.value.toLocaleString()}</span>
                {kpi.dod_pct != null && (
                  <span style={{ color: kpi.dod_pct >= 0 ? 'var(--status-normal)' : 'var(--status-critical)', display: 'flex', alignItems: 'center', fontWeight: 600 }}>
                    {kpi.dod_pct >= 0 ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
                    {Math.abs(kpi.dod_pct).toFixed(1)}%
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {data.kpis.length > 0 && chartData.length > 0 && (
        <section className="glass-panel" style={{ marginTop: '32px' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={20} color="var(--primary-color)" /> {t('dashboard_forecast')}
          </h2>
          <p style={{ fontSize: '0.85rem', marginBottom: '20px' }}>{t('dashboard_forecast_desc')}</p>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <defs>
                {forecastKpiNames.map((name, i) => (
                  <linearGradient key={name} id={`grad-${i}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={KPI_COLORS[i % KPI_COLORS.length]} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={KPI_COLORS[i % KPI_COLORS.length]} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey="date"
                stroke="var(--text-secondary)"
                fontSize={11}
                tickFormatter={(v) => v.slice(5)}
              />
              <YAxis stroke="var(--text-secondary)" fontSize={11} width={70}
                tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}
              />
              <Tooltip
                contentStyle={{ background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '8px', fontSize: '0.82rem' }}
                formatter={(value, name) => [Number(value).toLocaleString(), name]}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Legend wrapperStyle={{ fontSize: '0.82rem', paddingTop: '12px' }} />
              {forecastKpiNames.map((name, i) => (
                <Area
                  key={name}
                  type="monotone"
                  dataKey={name}
                  name={name}
                  stroke={KPI_COLORS[i % KPI_COLORS.length]}
                  fill={`url(#grad-${i})`}
                  strokeWidth={2}
                  dot={{ r: 3, fill: KPI_COLORS[i % KPI_COLORS.length] }}
                  activeDot={{ r: 5 }}
                  connectNulls
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </section>
      )}

      {data.anomalies.length > 0 && (
        <section className="glass-panel" style={{ borderLeft: '4px solid var(--status-critical)', marginTop: '32px' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--status-critical)', marginBottom: '16px' }}>
            <AlertCircle /> {t('dashboard_anomalies')}
          </h2>
          <div style={{ display: 'grid', gap: '12px' }}>
            {data.anomalies.map((anomaly) => (
              <div key={anomaly.id} style={{ padding: '16px', background: 'rgba(239,68,68,0.1)', borderRadius: 'var(--radius-md)' }}>
                <h4 style={{ color: 'var(--text-primary)', marginBottom: '4px' }}>{anomaly.kpi_name.replaceAll('_', ' ')} flagged</h4>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
                  {anomaly.context?.reason} (Deviation: {anomaly.deviation.toFixed(1)}%)
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default Dashboard;
