import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, ArrowDownRight, ArrowUpRight, FileText, RefreshCcw, TrendingUp, Sparkles, Search, BarChart2, Shield, Activity, Download, CheckCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis, LineChart, Line, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { useAuth } from '../lib/authContext';
import { apiFetch, apiJson, API_URL } from '../lib/api';
import { useLang } from '../lib/i18n';
import ValidationWarnings from '../components/ValidationWarnings';
import ChartRenderer from '../components/ChartRenderer';
import MapVisualization from '../components/MapVisualization';
import ErrorBoundary from '../components/ErrorBoundary';
import OnboardingTour from '../components/OnboardingTour';
import DashboardCustomizer from '../components/DashboardCustomizer';
import { useRealTimeData } from '../hooks/useRealTimeData';

const DASHBOARD_CACHE_KEY = 'saas.dashboard.lastSummary.v2';
const METRICS_CACHE_KEY = 'saas.dashboard.metricsCache.v1';

const readCache = (key) => {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
};

const writeCache = (key, payload) => {
  try { localStorage.setItem(key, JSON.stringify(payload)); } catch { /* noop */ }
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

// ─── Reusable Enterprise KPI Card ──────────────────────────────────────────
const MetricCard = ({ label, value, delta, status, icon, color, sparklineData, format, onClick }) => {
  const fmt = format || ((v) => {
    if (v == null) return '—';
    const num = Number(v);
    if (Math.abs(num) >= 1_000_000_000) return `${(num / 1_000_000_000).toFixed(1)}B`;
    if (Math.abs(num) >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (Math.abs(num) >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toLocaleString('fr-FR', { maximumFractionDigits: 0 });
  });
  const deltaDisplay = delta != null && !isNaN(delta) && delta !== 0;
  const statusColor = status === 'CRITICAL' ? '#ef4444' : status === 'WARNING' ? '#f59e0b' : '#10b981';

  return (
    <div 
      className="ea-kpi-card" 
      role="region" 
      aria-label={`KPI Card: ${label}`}
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      <div className="ea-kpi-label">{label}</div>
      <div className="ea-kpi-value">{fmt(value)}</div>
      {deltaDisplay && (
        <span className={`ea-kpi-delta ${delta > 0 ? 'positive' : 'negative'}`}>
          {delta > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
          {Math.abs(delta).toFixed(1)}%
        </span>
      )}
      {sparklineData && sparklineData.length > 1 && (
        <div style={{ height: 32, marginTop: 8 }}>
          <AreaChart width={200} height={32} data={sparklineData.slice(-14).map((p) => ({ t: p.t?.slice(5,10) || '', v: p.value }))}>
            <defs><linearGradient id={`sprk-${label?.replace(/\s/g,'') || 'kpi'}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={statusColor} stopOpacity={0.3} /><stop offset="100%" stopColor={statusColor} stopOpacity={0} /></linearGradient></defs>
            <Area type="monotone" dataKey="v" stroke={statusColor} fill={`url(#sprk-${label?.replace(/\s/g,'') || 'kpi'})`} strokeWidth={1.5} dot={false} />
          </AreaChart>
        </div>
      )}
    </div>
  );
};

// ─── Error Boundary ────────────────────────────────────────────────────────
class DashboardErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error('Dashboard Error:', error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="ea-empty-state">
          <div className="ea-empty-state-icon">
            <AlertCircle size={28} />
          </div>
          <h3 className="ea-empty-state-title">Something went wrong</h3>
          <p className="ea-empty-state-description">
            An unexpected error occurred loading the dashboard. Please try refreshing the page.
          </p>
          <button className="ea-btn ea-btn-primary" onClick={() => { this.setState({ hasError: false }); window.location.reload(); }}>
            Refresh Dashboard
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────
const DashboardSkeleton = () => (
  <div className="ea-content" style={{ maxWidth: 'var(--ea-content-max-width)', margin: '0 auto' }}>
    <div className="ea-skeleton ea-skeleton-title" style={{ width: '200px', marginBottom: '1.5rem' }} />
    <div className="ea-dashboard-grid ea-grid-kpis" style={{ marginBottom: '1.5rem' }}>
      {[1,2,3,4].map(i => <div key={i} className="ea-skeleton ea-skeleton-card" />)}
    </div>
    <div className="ea-skeleton" style={{ height: '200px', borderRadius: 'var(--ea-radius-lg)' }} />
  </div>
);

// ─── Main Dashboard Component ──────────────────────────────────────────────
const Dashboard = () => {
  const { user, isManager } = useAuth();
  const { t } = useLang();
  const navigate = useNavigate();

  const [data, setData] = useState(() => readCache(DASHBOARD_CACHE_KEY) || EMPTY_DATA);
  const [loading, setLoading] = useState(!readCache(DASHBOARD_CACHE_KEY));
  const [syncing, setSyncing] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Syncing...');
  const [forecasts, setForecasts] = useState([]);
  const [widgets, setWidgets] = useState([]);
  const [series, setSeries] = useState({});
  const [activeTab, setActiveTab] = useState('overview');
  const [executiveData, setExecutiveData] = useState(null);
  const [dateRange, setDateRange] = useState('30'); // days
  const [selectedKpi, setSelectedKpi] = useState(null);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [showCustomizer, setShowCustomizer] = useState(false);
  const [dashboardLayout, setDashboardLayout] = useState(null);
  
  // Refs for cleanup and closure safety
  const fetchDataRef = useRef(null);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  // Handle responsive layout
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Real-time data streaming
  useRealTimeData(user?.id, {
    onData: (data) => {
      if (data.type === 'kpi-update') {
        // Refresh dashboard when KPIs update
        fetchDataRef.current?.();
      }
    },
    onError: (err) => {
      console.log('Real-time connection lost, falling back to polling');
    },
  });

  // Keepalive - consume response properly
  useEffect(() => {
    fetch(`${API_URL}/api/ping`)
      .then(res => res.json())
      .catch(() => { /* server might not be running */ });
  }, []);

  const fetchData = useCallback(async () => {
    try {
      if (!user) return;
      const [result, forecastResult, widgetResult] = await Promise.all([
        apiJson('/api/summary'),
        apiJson(`/api/forecasts?days=${dateRange}`),
        apiJson('/api/dashboard/widgets').catch(() => ({ widgets: [] })),
      ]);
      if (!mountedRef.current) return;
      setData(result);
      writeCache(DASHBOARD_CACHE_KEY, result);
      setForecasts(forecastResult.forecasts || []);
      setWidgets(widgetResult.widgets || []);
      const seriesResult = await apiJson(`/api/kpis/series?limit=30&days=${dateRange}`).catch(() => ({ series: {} }));
      if (!mountedRef.current) return;
      setSeries(seriesResult.series || {});
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      if (!mountedRef.current) return;
      const cached = readCache(DASHBOARD_CACHE_KEY);
      if (cached) setData(cached);
      else setData({ ...EMPTY_DATA, narrative: 'Unable to load dashboard data.', last_refreshed: 'Error' });
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [user, dateRange]);
  
  // Store fetchData in ref for polling
  fetchDataRef.current = fetchData;

  useEffect(() => {
    if (user) fetchData();
    return () => { mountedRef.current = false; };
  }, [user, fetchData, dateRange]);

  // Fetch executive data when executive tab is active
  useEffect(() => {
    if (activeTab === 'executive' && user) {
      apiJson('/api/executive/overview')
        .then(data => setExecutiveData(data))
        .catch(() => setExecutiveData(null));
    }
  }, [activeTab, user]);
  
  useEffect(() => {
    document.title = 'Dashboard - Enterprise Analytics Platform';
    return () => { document.title = 'Enterprise Analytics'; };
  }, []);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []);

  // Load saved dashboard layout
  useEffect(() => {
    const saved = localStorage.getItem('dashboard_layout');
    if (saved) {
      try {
        setDashboardLayout(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to parse saved layout:', e);
      }
    }
  }, []);

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

  // ── Optimized widget cards with sparklines (O(n) instead of O(n²)) ──
  const widgetCards = useMemo(() => {
    const kpiMap = new Map();
    data.kpis.forEach(k => {
      const key = (k.kpi_name || '').toLowerCase();
      kpiMap.set(key, k);
      kpiMap.set(key.replace(/_/g, ''), k);
    });
    
    return (widgets || []).map((w) => {
      const wName = (w.name || '').toLowerCase();
      const kpi = kpiMap.get(wName) || kpiMap.get(wName.replace(/_/g, '')) || 
                  data.kpis.find(k => (k.kpi_name || '').toLowerCase().includes(wName));
      const points = series[(kpi?.kpi_name || w.name || '')] || [];
      const last = points[points.length - 1]?.value;
      const prev = points[points.length - 2]?.value;
      const delta = (last != null && prev != null && prev !== 0) ? ((last - prev) / Math.abs(prev)) * 100 : null;
      return { w, kpi, points, last, delta };
    });
  }, [widgets, data.kpis, series]);

  // ── Widget grid (top row) - derived from widgetCards in O(n) ──
  const topMetrics = useMemo(() => {
    return widgetCards.map(({ w, kpi, points, delta }) => {
      const val = kpi?.value ?? points[points.length - 1]?.value;
      return { label: w.display_name_en || w.name, value: val, delta, status: kpi?.status, sparklineData: points, icon: <Activity size={16} /> };
    });
  }, [widgetCards]);

  // ── KPI cards grid ────────────────────────────────────────────
  const kpiCards = useMemo(() => {
    return (data.kpis || []).slice(0, 8).map((k) => ({
      label: k.kpi_name.replaceAll('_', ' '),
      value: k.value,
      delta: k.dod_pct,
      status: k.status,
      sparklineData: series[k.kpi_name] || [],
      kpi_name: k.kpi_name,
    }));
  }, [data.kpis, series]);

  // ── Sync handler with proper cleanup ──────────────────────────
  const handleSync = useCallback(() => {
    if (syncing || !fetchDataRef.current) return;
    setSyncing(true);
    setStatusMessage('Starting sync...');
    
    apiFetch('/api/etl/trigger', { method: 'POST' })
      .then(() => {
        let attempts = 0;
        intervalRef.current = setInterval(() => {
          attempts++;
          apiJson('/api/etl/status')
            .then((s) => {
              if (!mountedRef.current) {
                if (intervalRef.current) clearInterval(intervalRef.current);
                return;
              }
              if (s.status === 'IDLE' || s.status === 'COMPLETED' || attempts > 30) {
                if (intervalRef.current) clearInterval(intervalRef.current);
                intervalRef.current = null;
                if (fetchDataRef.current) fetchDataRef.current();
                setSyncing(false);
                setStatusMessage('Done');
              } else {
                setStatusMessage(SYNC_STATUS_LABELS[s.status] || 'Processing...');
              }
            })
            .catch(() => {
              if (attempts > 30) {
                if (intervalRef.current) clearInterval(intervalRef.current);
                intervalRef.current = null;
                setSyncing(false);
              }
            });
        }, 4000);
      })
      .catch(() => setSyncing(false));
  }, [syncing]);

  // ── Generate Report handler ──────────────────────────────────
  const handleGenerateReport = useCallback(() => {
    if (reporting || !fetchDataRef.current) return;
    setReporting(true);
    setStatusMessage('Generating report...');
    
    apiFetch('/api/reports/generate', { method: 'POST' })
      .then(() => {
        setTimeout(() => {
          if (fetchDataRef.current) fetchDataRef.current();
          setReporting(false);
          setStatusMessage('Report generated');
        }, 3000);
      })
      .catch((err) => {
        console.error('Report generation error:', err);
        setReporting(false);
      });
  }, [reporting]);

  // ── KPI drill-down handler ────────────────────────────────────
  const handleKpiClick = useCallback((kpi) => {
    setSelectedKpi(kpi);
    // Navigate to analytics tab to see detailed view
    setActiveTab('analytics');
  }, []);

  const handleSaveLayout = useCallback((layout) => {
    setDashboardLayout(layout);
    localStorage.setItem('dashboard_layout', JSON.stringify(layout));
  }, []);

  // ── Tab content ───────────────────────────────────────────────
  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <>
            {topMetrics.length > 0 && (
              <section style={{ marginBottom: 24 }}>
                <h3 style={{ fontSize: '0.85rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--ea-text-secondary)', marginBottom: 12 }}>Key Metrics</h3>
                <div className="ea-dashboard-grid ea-grid-kpis">
                  {topMetrics.map((m, i) => <MetricCard key={i} {...m} onClick={() => handleKpiClick(m)} />)}
                </div>
              </section>
            )}

            {kpiCards.length > 0 && (
              <section style={{ marginBottom: 24 }}>
                <div className="ea-dashboard-grid" style={{ gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(220px, 1fr))', gap: 14 }}>
                  {kpiCards.map((k, i) => <MetricCard key={i} {...k} onClick={() => handleKpiClick(k)} />)}
                </div>
              </section>
            )}

            {data.kpi_mode && (
              <section style={{ marginBottom: 20 }}>
                <div className="ea-alert ea-alert-info">
                  <Shield size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                  <div>
                    <strong>Data mode:</strong>{' '}
                    {data.kpi_mode.mode === 'configured' ? 'Admin-defined KPIs' : data.kpi_mode.mode === 'auto' ? 'Auto-discovered' : 'Database overview'}
                    {data.kpi_mode.admin_field_count > 0 && <span> — {data.kpi_mode.mapped_count || 0} of {data.kpi_mode.admin_field_count} mapped</span>}
                  </div>
                </div>
              </section>
            )}

            {data.snapshot_chart && data.kpis.length > 0 && (
              <section className="ea-chart-container" style={{ marginBottom: 24 }}>
                <ChartRenderer spec={data.snapshot_chart} height={Math.min(320, 80 + data.kpis.length * 24)} />
              </section>
            )}
          </>
        );

      case 'analytics':
        return (
          <>
            {/* Selected KPI Detail */}
            {selectedKpi && (
              <section className="ea-card" style={{ marginBottom: 24, borderLeft: '4px solid var(--ea-primary)' }}>
                <div className="ea-card-body">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <BarChart2 size={18} color="var(--ea-primary)" /> {selectedKpi.label} - Detailed View
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(150px, 1fr))', gap: 16 }}>
                    <div className="ea-kpi-card">
                      <div className="ea-kpi-label">Current Value</div>
                      <div className="ea-kpi-value">{typeof selectedKpi.value === 'number' ? selectedKpi.value.toLocaleString() : selectedKpi.value}</div>
                    </div>
                    {selectedKpi.delta != null && (
                      <div className="ea-kpi-card">
                        <div className="ea-kpi-label">Day-over-Day</div>
                        <div className="ea-kpi-value" style={{ color: selectedKpi.delta >= 0 ? '#10b981' : '#ef4444' }}>
                          {selectedKpi.delta >= 0 ? '+' : ''}{selectedKpi.delta.toFixed(1)}%
                        </div>
                      </div>
                    )}
                    <div className="ea-kpi-card">
                      <div className="ea-kpi-label">Status</div>
                      <div className="ea-kpi-value" style={{ color: selectedKpi.status === 'CRITICAL' ? '#ef4444' : selectedKpi.status === 'WARNING' ? '#f59e0b' : '#10b981' }}>
                        {selectedKpi.status}
                      </div>
                    </div>
                  </div>
                  {selectedKpi.sparklineData && selectedKpi.sparklineData.length > 0 && (
                    <div style={{ marginTop: 16, height: 200 }}>
                      <ChartRenderer 
                        spec={{
                          type: 'line',
                          data: selectedKpi.sparklineData.map(p => ({ date: p.t, value: p.value })),
                          title: 'Historical Trend',
                          xKey: 'date',
                          yKey: 'value',
                        }}
                        height={200}
                      />
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* AI Narrative - Clean without asterisks */}
            {data.narrative && (
              <section className="ea-card" style={{ marginBottom: 24, borderLeft: '4px solid var(--ea-primary)' }}>
                <div className="ea-card-body">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Sparkles size={18} color="var(--ea-primary)" /> AI Narrative
                  </h3>
                  <div style={{ fontSize: '1rem', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                    {data.narrative
                      .replace(/\*\*(.*?)\*\*/g, '$1')
                      .replace(/\*(.*?)\*/g, '$1')
                      .replace(/__(.*?)__/g, '$1')
                    }
                  </div>
                </div>
              </section>
            )}

            {/* Map Visualization */}
            <section className="ea-chart-container" style={{ marginBottom: 24 }}>
              <h3 className="ea-chart-title">
                🗺️ Regional Performance
              </h3>
              <p style={{ fontSize: '0.82rem', marginBottom: 16, color: 'var(--ea-text-secondary)' }}>Geographic distribution of key metrics</p>
              <MapVisualization 
                data={[
                  { region_id: 'douala', region_name: 'Douala', value: 4500000 },
                  { region_id: 'yaounde', region_name: 'Yaoundé', value: 3800000 },
                  { region_id: 'bafoussam', region_name: 'Bafoussam', value: 2100000 },
                  { region_id: 'garoua', region_name: 'Garoua', value: 1800000 },
                  { region_id: 'maroua', region_name: 'Maroua', value: 1200000 },
                  { region_id: 'bamenda', region_name: 'Bamenda', value: 1900000 },
                  { region_id: 'ebolowa', region_name: 'Ebolowa', value: 1500000 },
                  { region_id: 'bertoua', region_name: 'Bertoua', value: 1600000 },
                ]}
                onRegionClick={(region) => {
                  alert(`Region: ${region.name}\nValue: ${region.value?.toLocaleString()}\n\nClick OK to see detailed analytics for this region.`);
                }}
                height={350}
              />
            </section>

            {/* Forecasts Chart */}
            {chartData.length > 0 && forecastKpiNames.length > 0 && (
              <section className="ea-chart-container" style={{ marginBottom: 24 }}>
                <h3 className="ea-chart-title">
                  <TrendingUp size={18} style={{ marginRight: 8, verticalAlign: 'middle' }} /> Forecast
                </h3>
                <p style={{ fontSize: '0.82rem', marginBottom: 16, color: 'var(--ea-text-secondary)' }}>Projected values based on historical trends</p>
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                    <defs>{forecastKpiNames.map((n, i) => (<linearGradient key={n} id={`fg-${i}`} x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={KPI_COLORS[i % KPI_COLORS.length]} stopOpacity={0.25} /><stop offset="95%" stopColor={KPI_COLORS[i % KPI_COLORS.length]} stopOpacity={0} /></linearGradient>))}</defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
                    <XAxis dataKey="date" stroke="var(--ea-text-secondary)" fontSize={11} tickFormatter={(v) => v.slice(5)} />
                    <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={70} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
                    <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8, fontSize: '0.82rem' }} formatter={(value, name) => [Number(value).toLocaleString(), name]} labelFormatter={(l) => `Date: ${l}`} />
                    <Legend wrapperStyle={{ fontSize: '0.82rem', paddingTop: 12 }} />
                    {forecastKpiNames.map((n, i) => (<Area key={n} type="monotone" dataKey={n} name={n} stroke={KPI_COLORS[i % KPI_COLORS.length]} fill={`url(#fg-${i})`} strokeWidth={2} dot={{ r: 3 }} connectNulls />))}
                  </AreaChart>
                </ResponsiveContainer>
              </section>
            )}

            {/* Anomalies */}
            {data.anomalies.length > 0 && (
              <section className="ea-card" style={{ borderLeft: '4px solid var(--ea-danger)', marginBottom: 24 }}>
                <div className="ea-card-body">
                  <h3 style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--ea-danger)', marginBottom: 16, fontSize: '1.05rem' }}>
                    <AlertCircle size={18} /> Anomalies Detected
                  </h3>
                  <div style={{ display: 'grid', gap: 10 }}>
                    {data.anomalies.slice(0, 5).map((a) => (
                      <div key={a.id} className="ea-alert ea-alert-danger" style={{ margin: 0 }}>
                        <h4 style={{ margin: 0, fontSize: '0.9rem' }}>{a.kpi_name.replaceAll('_', ' ')}</h4>
                        <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.85rem', margin: '4px 0 0' }}>
                          {a.context?.reason} (Deviation: {a.deviation.toFixed(1)}%)
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            )}

            {/* Validation warnings */}
            {data.validation?.length > 0 && <ValidationWarnings validations={data.validation} />}

            {/* Empty state */}
            {!data.narrative && !chartData.length && !data.anomalies.length && (
              <div className="ea-empty-state">
                <div className="ea-empty-state-icon"><BarChart2 size={28} /></div>
                <h3 className="ea-empty-state-title">No Analytics Yet</h3>
                <p className="ea-empty-state-description">Sync your data to generate analytics and insights.</p>
              </div>
            )}
          </>
        );

      case 'executive':
        return (
          <div className="ea-card" style={{ marginBottom: 24 }}>
            <div className="ea-card-body">
              <h3 style={{ fontSize: '1.1rem', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                📋 Executive Overview
              </h3>
              {executiveData ? (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 24 }}>
                    <div className="ea-kpi-card">
                      <div className="ea-kpi-label">Health Score</div>
                      <div className="ea-kpi-value" style={{ color: executiveData.health_score >= 70 ? '#10b981' : executiveData.health_score >= 50 ? '#f59e0b' : '#ef4444' }}>
                        {executiveData.health_score}/100
                      </div>
                    </div>
                    <div className="ea-kpi-card">
                      <div className="ea-kpi-label">Total KPIs</div>
                      <div className="ea-kpi-value">{executiveData.kpi_count}</div>
                    </div>
                    <div className="ea-kpi-card">
                      <div className="ea-kpi-label">Normal</div>
                      <div className="ea-kpi-value" style={{ color: '#10b981' }}>{executiveData.status_summary?.NORMAL || 0}</div>
                    </div>
                    <div className="ea-kpi-card">
                      <div className="ea-kpi-label">Warnings</div>
                      <div className="ea-kpi-value" style={{ color: '#f59e0b' }}>{executiveData.status_summary?.WARNING || 0}</div>
                    </div>
                    <div className="ea-kpi-card">
                      <div className="ea-kpi-label">Critical</div>
                      <div className="ea-kpi-value" style={{ color: '#ef4444' }}>{executiveData.status_summary?.CRITICAL || 0}</div>
                    </div>
                  </div>

                  {executiveData.risk_indicators && executiveData.risk_indicators.length > 0 && (
                    <section style={{ marginBottom: 20 }}>
                      <h4 style={{ marginBottom: 10, color: 'var(--ea-danger)' }}>⚠️ Risk Indicators</h4>
                      <div style={{ display: 'grid', gap: 8 }}>
                        {executiveData.risk_indicators.map((risk, i) => (
                          <div key={i} className="ea-alert ea-alert-danger" style={{ margin: 0 }}>
                            <strong>{risk.category}:</strong> {risk.indicator}
                            <div style={{ fontSize: '0.82rem', marginTop: 4 }}>Action: {risk.action}</div>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}

                  {executiveData.anomalies && executiveData.anomalies.length > 0 && (
                    <section style={{ marginBottom: 20 }}>
                      <h4 style={{ marginBottom: 10 }}>Recent Anomalies</h4>
                      <div style={{ display: 'grid', gap: 8 }}>
                        {executiveData.anomalies.slice(0, 5).map((a) => (
                          <div key={a.id} className="ea-alert ea-alert-warning" style={{ margin: 0 }}>
                            <strong>{a.kpi_name?.replace(/_/g, ' ')}</strong>
                            <span style={{ marginLeft: 8, color: 'var(--ea-text-secondary)' }}>{a.context?.reason}</span>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}

                  {executiveData.recent_reports && executiveData.recent_reports.length > 0 && (
                    <section>
                      <h4 style={{ marginBottom: 10 }}>Recent Reports</h4>
                      <div style={{ display: 'grid', gap: 6 }}>
                        {executiveData.recent_reports.map((r, i) => (
                          <div key={i} style={{ fontSize: '0.85rem', color: 'var(--ea-text-secondary)' }}>
                            {r.report_date}: {r.narrative?.slice(0, 100)}...
                          </div>
                        ))}
                      </div>
                    </section>
                  )}
                </>
              ) : (
                <div className="ea-empty-state">
                  <div className="ea-empty-state-icon"><BarChart2 size={28} /></div>
                  <h3 className="ea-empty-state-title">No Executive Data</h3>
                  <p className="ea-empty-state-description">Sync your data to generate executive insights.</p>
                </div>
              )}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  if (loading) return <DashboardSkeleton />;

  const hasData = data.kpis.length > 0 || data.narrative;

  return (
    <DashboardErrorBoundary>
      <div className="ea-content" style={{ maxWidth: 'var(--ea-content-max-width)', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ marginBottom: 28, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <h1 style={{ fontSize: isMobile ? '1.3rem' : '1.6rem', margin: 0 }}>Dashboard</h1>
            <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: 'var(--ea-text-secondary)' }}>
              {data.last_refreshed && data.last_refreshed !== 'Never' && data.last_refreshed !== 'ERROR'
                ? `Last updated: ${data.last_refreshed}`
                : 'No report generated yet'}
            </p>
          </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: 4, padding: 4, background: 'var(--ea-bg-hover)', borderRadius: 8, border: '1px solid var(--ea-border)' }}>
            {[
              { value: '7', label: '7D' },
              { value: '30', label: '30D' },
              { value: '90', label: '90D' },
              { value: '365', label: '1Y' },
            ].map((option) => (
              <button
                key={option.value}
                onClick={() => setDateRange(option.value)}
                style={{
                  padding: '6px 12px',
                  borderRadius: 6,
                  border: 'none',
                  cursor: 'pointer',
                  background: dateRange === option.value ? 'var(--ea-primary)' : 'transparent',
                  color: dateRange === option.value ? 'white' : 'var(--ea-text-primary)',
                  fontWeight: 500,
                  fontSize: '0.8rem',
                  transition: 'all 0.2s',
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
          <button className="ea-btn ea-btn-secondary" onClick={() => navigate('/reports')}>
            <FileText size={15} /> Reports
          </button>
            {/* Generate Report Button - Always visible */}
            <button className="ea-btn ea-btn-primary" onClick={handleGenerateReport} disabled={reporting || syncing} style={{ background: 'linear-gradient(135deg, var(--ea-primary), #8b5cf6)' }}>
              <FileText size={15} style={{ animation: reporting ? 'ea-pulse 1s ease-in-out infinite' : 'none' }} />
              {reporting ? 'Generating...' : 'Generate Report'}
            </button>
            {isManager && (
              <>
                <button className="ea-btn ea-btn-secondary" onClick={() => navigate('/query')}>
                  <Search size={15} /> Query
                </button>
                <button className="ea-btn ea-btn-secondary" onClick={() => navigate('/reports/custom')}>
                  <Sparkles size={15} /> Custom Report
                </button>
                <button className="ea-btn ea-btn-secondary" onClick={handleSync} disabled={syncing}>
                  <RefreshCcw size={15} style={{ animation: syncing ? 'ea-spin 1s linear infinite' : 'none' }} />
                  {syncing ? statusMessage : 'Sync Now'}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="ea-tabs">
          {['overview', 'analytics', 'executive'].map((tab) => (
            <button key={tab} className={`ea-tab ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>
              {tab === 'overview' ? '📊 Overview' : tab === 'analytics' ? '🔍 Analytics' : '📋 Executive'}
            </button>
          ))}
          {isManager && (
            <button
              className="ea-tab"
              onClick={() => setShowCustomizer(true)}
              style={{ marginLeft: 'auto' }}
              title="Customize Dashboard"
            >
              ⚙️ Customize
            </button>
          )}
        </div>

        {!hasData && isManager && (
          <div className="ea-empty-state" style={{ marginBottom: 24 }}>
            <div className="ea-empty-state-icon"><FileText size={28} /></div>
            <h3 className="ea-empty-state-title">No Data Yet</h3>
            <p className="ea-empty-state-description">Connect a database and sync to start analyzing.</p>
            <button className="ea-btn ea-btn-primary" onClick={() => navigate('/settings')}>
              Configure Connection
            </button>
          </div>
        )}

        {renderTabContent()}
        
        {/* Onboarding Tour */}
        <OnboardingTour
          onComplete={() => console.log('Onboarding completed')}
          onSkip={() => console.log('Onboarding skipped')}
        />

        {/* Dashboard Customizer */}
        <DashboardCustomizer
          isOpen={showCustomizer}
          onClose={() => setShowCustomizer(false)}
          onSave={handleSaveLayout}
          currentLayout={dashboardLayout}
        />
        
        <style>{`@keyframes ea-spin{100%{transform:rotate(360deg)}}@keyframes ea-pulse{0%,100%{opacity:1}50%{opacity:0.5}}
          @media (max-width: 768px) {
            .ea-dashboard-grid { grid-template-columns: 1fr !important; }
            .ea-tabs { flex-wrap: wrap; }
            .ea-tab { flex: 1; min-width: 80px; font-size: 0.75rem; }
          }`}</style>
      </div>
    </DashboardErrorBoundary>
  );
};

export default Dashboard;