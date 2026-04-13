import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, ArrowDownRight, ArrowUpRight, FileText, RefreshCcw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/authContext';
import { apiFetch, apiJson, API_URL } from '../lib/api';
import ValidationWarnings from '../components/ValidationWarnings';

const SYNC_STATUS_LABELS = {
  FETCHING_DATA: 'Step 1/6: Deep Extraction...',
  MAPPING_FIELDS: 'Step 2/6: Applying Semantic Mappings...',
  VALIDATING_DATA: 'Step 3/6: Running Quality Checks...',
  ANALYZING_ANOMALIES: 'Step 4/6: ML Pattern Matching...',
  LOADING_DATA: 'Step 5/6: Storing Results...',
  GENERATING_AI_NARRATIVE: 'Step 6/6: AI Strategic Writing...',
  SENDING_EMAILS: 'Finalizing Briefings...',
  VALIDATION_FAILED: 'Validation failed. Refreshing results...',
};

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
  } catch {}
};

const EMPTY_DATA = { kpis: [], anomalies: [], narrative: '', last_refreshed: '', validation: [] };

const Dashboard = () => {
  const { user, isManager } = useAuth();
  const navigate = useNavigate();

  // Load cache immediately — no spinner on open
  const [data, setData] = useState(() => readDashboardCache() || EMPTY_DATA);
  const [loading, setLoading] = useState(!readDashboardCache());
  const [syncing, setSyncing] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Syncing...');

  // Keepalive ping — wakes up free-tier backend before user needs it
  useEffect(() => {
    fetch(`${API_URL}/api/ping`).catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    try {
      if (!user) return;
      const result = await apiJson('/api/summary');
      setData(result);
      writeDashboardCache(result);
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
          <h1>Executive Summary</h1>
          <p>
            {data.last_refreshed && data.last_refreshed !== 'Never'
              ? `Last report: ${data.last_refreshed}`
              : 'No report generated yet.'}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {/* Every logged-in user can see report history */}
          <button
            className="btn btn-outline"
            onClick={() => navigate('/reports')}
            style={{ display: 'flex', gap: '8px', alignItems: 'center' }}
          >
            <FileText size={16} /> Report History
          </button>

          {/* Generate Report — managers and admins */}
          {isManager && (
            <button
              className="btn btn-primary"
              onClick={handleSync}
              disabled={syncing}
              style={{ display: 'flex', gap: '8px', alignItems: 'center', opacity: syncing ? 0.7 : 1 }}
            >
              <RefreshCcw size={16} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
              {syncing ? statusMessage : 'Generate Report'}
            </button>
          )}
        </div>
      </header>

      {!hasData && (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '48px', marginBottom: '32px' }}>
          <FileText size={48} color="var(--text-secondary)" style={{ marginBottom: '16px' }} />
          <h3 style={{ marginBottom: '8px' }}>No report yet</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
            Click <strong>Generate Report</strong> to run the full analytics pipeline — it extracts your data,
            computes KPIs, detects anomalies, and writes an AI narrative. Takes about 30–60 seconds.
          </p>
          {isManager && (
            <button className="btn btn-primary" onClick={handleSync} disabled={syncing} style={{ display: 'inline-flex', gap: '8px' }}>
              <RefreshCcw size={16} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
              {syncing ? statusMessage : 'Generate First Report'}
            </button>
          )}
        </div>
      )}

      <ValidationWarnings validations={data.validation || []} />

      {data.narrative && (
        <section className="glass-panel" style={{ marginBottom: '32px', borderLeft: '4px solid var(--primary-color)' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--primary-color)' }}>✦</span> AI Narrative
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

      {data.anomalies.length > 0 && (
        <section className="glass-panel" style={{ borderLeft: '4px solid var(--status-critical)', marginTop: '32px' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--status-critical)', marginBottom: '16px' }}>
            <AlertCircle /> Critical Anomalies Detected
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
