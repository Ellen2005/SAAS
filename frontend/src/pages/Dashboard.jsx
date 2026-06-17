import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, ArrowDownRight, ArrowUpRight, FileText, RefreshCcw, TrendingUp, Sparkles, Search, BarChart2, Shield, Activity } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis, LineChart, Line, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { useAuth } from '../lib/authContext';
import { apiFetch, apiJson, API_URL } from '../lib/api';
import { useLang } from '../lib/i18n';
import ValidationWarnings from '../components/ValidationWarnings';
import ChartRenderer from '../components/ChartRenderer';

const DASHBOARD_CACHE_KEY = 'saas.dashboard.lastSummary.v2';
const METRICS_CACHE_KEY = 'saas.dashboard.metricsCache.v1';

const readCache = (key) => {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
};

const writeCache = (key, payload) => {
  try { localStorage.setItem(key, JSON.stringify(payload)); } catch { }
};

const EMPTY_DATA = { kpis: [], anomalies: [], narrative: '', last_refreshed: '', validation: [] };

const SYNC_STATUS_LABELS = {
  FETCHING_DATA: 'Fetching data...',
  MAPPING_FIELDS: 'Mapping fields...',
  VALIDATING_DATA: 'Validating...',
  ANALYZING_ANOMALIES: 'Analyzing anomalies...',
  LOADING_DATA: 'Loading data...',
  GENERATING_AI_NARRATIVE: 'Generating narrative...',
  SENDING_EMAILS: 'Sending emails...',
  VALIDATION_FAILED: 'Validation failed',
};

// ─── Reusable Metric Card ───────────────────────────────────────────────────
const MetricCard = ({ label, value, delta, status, icon, color, sparklineData, format }) => {
  const fmt = format || ((v) => {
    if (v == null) return '—';
    const num = Number(v);
    if (Math.abs(num) >= 1_000_000_000) return `${(num / 1_000_000_000).toFixed(1)}B`;
    if (Math.abs(num) >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (Math.abs(num) >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toLocaleString('fr-FR', { maximumFractionDigits: 0 });
  });
  const deltaDisplay = delta != null && !isNaN(delta) && delta !== 0;
  const deltaColor = delta > 0 ? '#38a169' : delta < 0 ? '#e53e3e' : 'var(--text-secondary)';
  const statusColor = status === 'CRITICAL' ? '#e53e3e' : status === 'WARNING' ? '#d69e2e' : '#38a169';
  return (
    <div className="glass-panel" style={{ 
      padding: '16px 18px', 
      display: 'flex', 
      flexDirection: 'column', 
      gap: 6, 
      borderLeft: `3px solid ${statusColor}`,
      minWidth: 0,
      overflow: 'hidden'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <span style={{ 
          fontSize: '0.72rem', 
          fontWeight: 600, 
          textTransform: 'uppercase', 
          letterSpacing: '0.4px', 
          color: 'var(--text-secondary)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis'
        }}>{label}</span>
        {icon && <span style={{ color: 'var(--text-secondary)', opacity: 0.4, flexShrink: 0 }}>{icon}</span>}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap', lineHeight: 1 }}>
        <span style={{ 
          fontSize: '1.6rem', 
          fontWeight: 800, 
          letterSpacing: '-0.02em',
          wordBreak: 'break-all',
          lineHeight: 1.2
        }}>{fmt(value)}</span>
        {deltaDisplay && (
          <span style={{ 
            display: 'inline-flex', 
            alignItems: 'center', 
            gap: 2, 
            color: deltaColor, 
            fontWeight: 600, 
            fontSize: '0.78rem',
            flexShrink: 0
          }}>
            {delta > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
            {Math.abs(delta).toFixed(1)}%
          </span>
        )}
      </div>
      {sparklineData && sparklineData.length > 1 && (
        <div style={{ height: 28, marginTop: 2 }}>
          <AreaChart width={180} height={28} data={sparklineData.slice(-14).map((p) => ({ t: p.t?.slice(5,10) || '', v: p.value }))}>
            <defs><linearGradient id={`sprk-${label.replace(/\s/g,'')}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={statusColor} stopOpacity={0.3} /><stop offset="100%" stopColor={statusColor} stopOpacity={0} /></linearGradient></defs>
            <Area type="monotone" dataKey="v" stroke={statusColor} fill={`url(#sprk-${label.replace(/\s/g,'')})`} strokeWidth={1.5} dot={false} />
          </AreaChart>
        </div>
      )}
    </div>
  );
};

// ─── Main Dashboard Component ───────────────────────────────────────────────
const Dashboard = () => {
  const { user, isManager } = useAuth();
  const { t } = useLang();
  const navigate = useNavigate();

  const [data, setData] = useState(() => readCache(DASHBOARD_CACHE_KEY) || EMPTY_DATA);
  const [loading, setLoading] = useState(!readCache(DASHBOARD_CACHE_KEY));
  const [syncing, setSyncing] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Syncing...');
  const [forecasts, setForecasts] = useState([]);
  const [widgets, setWidgets] = useState([]);
  const [series, setSeries] = useState({});
  const [activeTab, setActiveTab] = useState('overview');

  // Keepalive
  useEffect(() => { fetch(`${API_URL}/api/ping`).catch(() => {}); }, []);

  const fetchData = useCallback(async () => {
    try {
      if (!user) return;
      const [result, forecastResult, widgetResult] = await Promise.all([
        apiJson('/api/summary'),
        apiJson('/api/forecasts'),
        apiJson('/api/dashboard/widgets').catch(() => ({ widgets: [] })),
      ]);
      setData(result);
      writeCache(DASHBOARD_CACHE_KEY, result);
      setForecasts(forecastResult.forecasts || []);
      setWidgets(widgetResult.widgets || []);
      const seriesResult = await apiJson('/api/kpis/series?limit=30').catch(() => ({ series: {} }));
      setSeries(seriesResult.series || {});
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      const cached = readCache(DASHBOARD_CACHE_KEY);
      if (cached) setData(cached);
      else setData({ ...EMPTY_DATA, narrative: 'Unable to load dashboard data.', last_refreshed: 'Error' });
    } finally { setLoading(false); }
  }, [user]);

  useEffect(() => { if (user) fetchData(); }, [user, fetchData]);
  useEffect(() => { document.title = 'Dashboard - SAAS Analytics'; }, []);

  // ── Forecast chart data ───────────────────────────────────────
  const chartData = useMemo(() => {
    if (!forecasts.length) return [];
    const dateMap = {};
    forecasts.forEach((f) => {
      if (!dateMap[f.forecast_date]) dateMap[f.forecast_date] = { date: f.forecast_date };
      dateMap[f.forecast_date][f.kpi_name.replace(/_/g, ' ')] = f.predicted_value;
    });
    return Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date));
  }, [forecasts]);

  const forecastKpiNames = useMemo(() => [...new Set(forecasts.map((f) => f.kpi_name.replace(/_/g, ' ')))], [forecasts]);

  const KPI_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'];

  // ── Widget cards with sparklines ──────────────────────────────
  const widgetCards = useMemo(() => {
    return (widgets || []).map((w) => {
      const kpi = data.kpis.find((k) => (k.kpi_name || '').toLowerCase() === (w.name || '').toLowerCase())
        || data.kpis.find((k) => (k.kpi_name || '').toLowerCase().includes((w.name || '').toLowerCase()));
      const points = series[(kpi?.kpi_name || w.name || '')] || [];
      const last = points[points.length - 1]?.value;
      const prev = points[points.length - 2]?.value;
      const delta = (last != null && prev != null && prev !== 0) ? ((last - prev) / Math.abs(prev)) * 100 : null;
      return { w, kpi, points, last, delta };
    });
  }, [widgets, data.kpis, series]);

  // ── Widget grid (top row) ─────────────────────────────────────
  const topMetrics = useMemo(() => {
    const items = [];
    for (const { w, kpi, points, delta } of widgetCards) {
      const val = kpi?.value ?? widgetCards.find((c) => c.w?.name === w.name)?.last;
      items.push({ label: w.display_name_en || w.name, value: val, delta, status: kpi?.status, sparklineData: points, icon: <Activity size={16} /> });
    }
    return items;
  }, [widgetCards]);

  // ── KPI cards grid ────────────────────────────────────────────
  const kpiCards = useMemo(() => {
    return (data.kpis || []).slice(0, 8).map((k) => ({
      label: k.kpi_name.replaceAll('_', ' '),
      value: k.value,
      delta: k.dod_pct,
      status: k.status,
      sparklineData: series[k.kpi_name] || [],
    }));
  }, [data.kpis, series]);

  // ── Tab content ───────────────────────────────────────────────
  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <>
            {/* Row 1: Top Metric Cards */}
            {topMetrics.length > 0 && (
              <section style={{ marginBottom: 20 }}>
                <h2 style={{ fontSize: '0.85rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-secondary)', marginBottom: 10 }}>Key Metrics</h2>
                <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 14 }}>
                  {topMetrics.map((m, i) => (
                    <MetricCard key={i} {...m} />
                  ))}
                </div>
              </section>
            )}

            {/* Row 2: KPI Cards */}
            {kpiCards.length > 0 && (
              <section style={{ marginBottom: 24 }}>
                <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
                  {kpiCards.map((k, i) => (
                    <MetricCard key={i} {...k} />
                  ))}
                </div>
              </section>
            )}

            {/* Data mode indicator */}
            {data.kpi_mode && (
              <section style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.82rem', color: 'var(--text-secondary)', padding: '8px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: 8, border: '1px solid var(--border-color)' }}>
                  <Shield size={14} />
                  <span>Data mode:</span>
                  <strong style={{ color: 'var(--primary-color)' }}>
                    {data.kpi_mode.mode === 'configured' ? 'Admin-defined KPIs' : data.kpi_mode.mode === 'auto' ? 'Auto-discovered' : 'Database overview'}
                  </strong>
                  {data.kpi_mode.admin_field_count > 0 && <span> — {data.kpi_mode.mapped_count || 0} of {data.kpi_mode.admin_field_count} mapped</span>}
                </div>
              </section>
            )}

            {/* Chart snapshot */}
            {data.snapshot_chart && data.kpis.length > 0 && (
              <section className="glass-panel" style={{ marginBottom: 24 }}>
                <ChartRenderer spec={data.snapshot_chart} height={Math.min(320, 80 + data.kpis.length * 24)} />
              </section>
            )}
          </>
        );

      case 'analytics':
        return (
          <>
            {/* AI Narrative */}
            {data.narrative && (
              <section className="glass-panel" style={{ marginBottom: 24, borderLeft: '4px solid var(--primary-color)' }}>
                <h2 style={{ fontSize: '1.1rem', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Sparkles size={18} color="var(--primary-color)" /> AI Narrative
                </h2>
                <p style={{ fontSize: '1rem', lineHeight: 1.7 }}>{data.narrative}</p>
              </section>
            )}

            {/* Forecast */}
            {chartData.length > 0 && forecastKpiNames.length > 0 && (
              <section className="glass-panel" style={{ marginBottom: 24 }}>
                <h2 style={{ fontSize: '1.1rem', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <TrendingUp size={18} color="var(--primary-color)" /> Forecast
                </h2>
                <p style={{ fontSize: '0.82rem', marginBottom: 16, color: 'var(--text-secondary)' }}>Projected values based on historical trends</p>
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                    <defs>{forecastKpiNames.map((n, i) => (<linearGradient key={n} id={`fg-${i}`} x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={KPI_COLORS[i % KPI_COLORS.length]} stopOpacity={0.25} /><stop offset="95%" stopColor={KPI_COLORS[i % KPI_COLORS.length]} stopOpacity={0} /></linearGradient>))}</defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="date" stroke="var(--text-secondary)" fontSize={11} tickFormatter={(v) => v.slice(5)} />
                    <YAxis stroke="var(--text-secondary)" fontSize={11} width={70} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
                    <Tooltip contentStyle={{ background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: 8, fontSize: '0.82rem' }} formatter={(value, name) => [Number(value).toLocaleString(), name]} labelFormatter={(l) => `Date: ${l}`} />
                    <Legend wrapperStyle={{ fontSize: '0.82rem', paddingTop: 12 }} />
                    {forecastKpiNames.map((n, i) => (<Area key={n} type="monotone" dataKey={n} name={n} stroke={KPI_COLORS[i % KPI_COLORS.length]} fill={`url(#fg-${i})`} strokeWidth={2} dot={{ r: 3 }} connectNulls />))}
                  </AreaChart>
                </ResponsiveContainer>
              </section>
            )}

            {/* Anomalies */}
            {data.anomalies.length > 0 && (
              <section className="glass-panel" style={{ borderLeft: '4px solid #e53e3e', marginBottom: 24 }}>
                <h2 style={{ display: 'flex', alignItems: 'center', gap: 12, color: '#e53e3e', marginBottom: 16, fontSize: '1.05rem' }}>
                  <AlertCircle size={18} /> Anomalies Detected
                </h2>
                <div style={{ display: 'grid', gap: 10 }}>
                  {data.anomalies.slice(0, 5).map((a) => (
                    <div key={a.id} style={{ padding: '12px 16px', background: 'rgba(239,68,68,0.08)', borderRadius: 8 }}>
                      <h4 style={{ marginBottom: 2, fontSize: '0.9rem' }}>{a.kpi_name.replaceAll('_', ' ')}</h4>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>{a.context?.reason} (Deviation: {a.deviation.toFixed(1)}%)</p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Validation */}
            {data.validation?.length > 0 && <ValidationWarnings validations={data.validation} />}

            {/* No data state */}
            {!data.narrative && !chartData.length && !data.anomalies.length && (
              <div className="glass-panel" style={{ textAlign: 'center', padding: 48 }}>
                <BarChart2 size={48} color="var(--text-secondary)" style={{ marginBottom: 16 }} />
                <h3 style={{ marginBottom: 8 }}>No Analytics Yet</h3>
                <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>Sync your data to generate analytics and insights.</p>
              </div>
            )}
          </>
        );

      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
        <RefreshCcw size={32} style={{ animation: 'spin 1s linear infinite', marginRight: 12 }} />
        <style>{'@keyframes spin{100%{transform:rotate(360deg)}}'}</style>
        Loading analytics...
      </div>
    );
  }

  const hasData = data.kpis.length > 0 || data.narrative;

  return (
    <div className="dashboard">
      <style>{'@keyframes spin{100%{transform:rotate(360deg)}}'}</style>

      {/* Header */}
      <header style={{ marginBottom: 28, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: '1.6rem', margin: 0 }}>Dashboard</h1>
          <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {data.last_refreshed && data.last_refreshed !== 'Never'
              ? `Last updated: ${data.last_refreshed}`
              : 'No report generated yet'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button className="btn btn-outline" onClick={() => navigate('/reports')} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <FileText size={15} /> Reports
          </button>
          {isManager && (
            <>
              <button className="btn btn-outline" onClick={() => navigate('/query')} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <Search size={15} /> Query
              </button>
              <button className="btn btn-outline" onClick={() => navigate('/reports/custom')} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <Sparkles size={15} /> Custom Report
              </button>
              <button className="btn btn-primary" onClick={() => { if (!syncing) { setSyncing(true); setStatusMessage('Starting sync...'); apiFetch('/api/etl/trigger', { method: 'POST' }).then(() => { let attempts = 0; const iv = setInterval(() => { attempts++; apiJson('/api/etl/status').then((s) => { if (s.status === 'IDLE' || attempts > 25) { clearInterval(iv); fetchData(); setSyncing(false); setStatusMessage('Done'); } else { setStatusMessage(SYNC_STATUS_LABELS[s.status] || 'Processing...'); } }).catch(() => {}); }, 4000); }).catch(() => setSyncing(false)); } }} disabled={syncing} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <RefreshCcw size={15} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
                {syncing ? statusMessage : 'Sync Now'}
              </button>
            </>
          )}
        </div>
      </header>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24, borderBottom: '1px solid var(--border-color)', paddingBottom: 0 }}>
        {['overview', 'analytics'].map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            style={{ padding: '10px 20px', border: 'none', background: 'transparent', color: activeTab === tab ? 'var(--primary-color)' : 'var(--text-secondary)', fontWeight: activeTab === tab ? 700 : 400, borderBottom: activeTab === tab ? '2px solid var(--primary-color)' : '2px solid transparent', cursor: 'pointer', fontSize: '0.9rem', textTransform: 'capitalize', transition: 'all 0.15s' }}>
            {tab === 'overview' ? '📊 Overview' : '🔍 Analytics'}
          </button>
        ))}
      </div>

      {!hasData && isManager && (
        <div className="glass-panel" style={{ textAlign: 'center', padding: 48, marginBottom: 24 }}>
          <FileText size={48} color="var(--text-secondary)" style={{ marginBottom: 16 }} />
          <h3 style={{ marginBottom: 8 }}>No Data Yet</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>Connect a database and sync to start analyzing.</p>
          <button className="btn btn-primary" onClick={() => navigate('/settings')} style={{ display: 'inline-flex', gap: 8 }}>
            Configure Connection
          </button>
        </div>
      )}

      {renderTabContent()}
    </div>
  );
};

export default Dashboard;