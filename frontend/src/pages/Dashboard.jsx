import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, ArrowDownRight, ArrowUpRight, RefreshCcw } from 'lucide-react';
import { useAuth } from '../lib/authContext';
import { apiFetch, apiJson } from '../lib/api';
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
  } catch {
    // Ignore when storage is unavailable.
  }
};

const EMPTY_DATA = { kpis: [], anomalies: [], narrative: '', last_refreshed: '', validation: [] };

const Dashboard = () => {
  const { user, isManager } = useAuth();
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Syncing...');
  const [data, setData] = useState(EMPTY_DATA);

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
    if (!isManager || syncing || !user) return;

    setSyncing(true);
    setStatusMessage('Initializing sync...');

    try {
      await apiFetch('/api/etl/trigger', { method: 'POST' });

      for (let attempt = 0; attempt < 30; attempt += 1) {
        if (attempt > 0) {
          await new Promise((resolve) => setTimeout(resolve, 4000));
        }

        try {
          const statusData = await apiJson('/api/etl/status');
          const nextStatus = statusData.status || 'IDLE';

          if (nextStatus === 'IDLE') {
            if (attempt === 0) {
              setStatusMessage('Starting background worker...');
              continue;
            }
            await fetchData();
            setStatusMessage('Sync complete.');
            return;
          }

          setStatusMessage(SYNC_STATUS_LABELS[nextStatus] || 'Processing system intelligence...');

          if (nextStatus === 'VALIDATION_FAILED') {
            await fetchData();
            return;
          }
        } catch (error) {
          console.error('Status check failed', error);
          setStatusMessage('Waiting for sync status...');
        }
      }

      setStatusMessage('Sync timed out. Check backend logs and connection settings.');
    } catch (err) {
      console.error('Sync failed:', err);
      setStatusMessage(err.message || 'Sync failed.');
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
        <RefreshCcw size={48} style={{ animation: 'spin 1s linear infinite' }} />
        <span style={{ marginLeft: '16px', fontSize: '1.2rem' }}>Loading Live Analytics...</span>
        <style>{'@keyframes spin { 100% { transform: rotate(360deg); } }'}</style>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <style>{'@keyframes spin { 100% { transform: rotate(360deg); } }'}</style>
      <header style={{ marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1>Executive Summary</h1>
          <p>Your daily automated insights. Last refreshed: {data.last_refreshed || 'Unknown'}.</p>
        </div>
        {isManager && (
          <button
            className="btn btn-outline"
            onClick={handleSync}
            disabled={syncing}
            style={{ display: 'flex', gap: '8px', opacity: syncing ? 0.6 : 1 }}
          >
            <RefreshCcw size={18} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
            {syncing ? statusMessage : 'Sync Now'}
          </button>
        )}
      </header>

      <ValidationWarnings validations={data.validation || []} />

      <section className="glass-panel" style={{ marginBottom: '32px', borderLeft: '4px solid var(--primary-color)' }}>
        <h2 style={{ fontSize: '1.2rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--primary-color)' }}>*</span> AI Narrative
        </h2>
        <p style={{ fontSize: '1.05rem', lineHeight: '1.6', color: 'var(--text-primary)' }}>
          {data.narrative}
        </p>
      </section>

      <div className="dashboard-grid">
        {data.kpis.map((kpi) => (
          <div key={kpi.id} className="glass-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{kpi.kpi_name.replaceAll('_', ' ')}</span>
              <span className={`badge badge-${kpi.status?.toLowerCase()}`}>{kpi.status}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
              <span style={{ fontSize: '2.5rem', fontWeight: 700, letterSpacing: '-0.03em' }}>{kpi.value.toLocaleString()}</span>
              {kpi.dod_pct !== null && kpi.dod_pct !== undefined && (
                <span
                  style={{
                    color: kpi.dod_pct >= 0 ? 'var(--status-normal)' : 'var(--status-critical)',
                    display: 'flex',
                    alignItems: 'center',
                    fontWeight: '600',
                  }}
                >
                  {kpi.dod_pct >= 0 ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
                  {Math.abs(kpi.dod_pct).toFixed(1)}%
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {data.anomalies.length > 0 && (
        <section className="glass-panel" style={{ borderLeft: '4px solid var(--status-critical)', marginTop: '32px' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--status-critical)', marginBottom: '16px' }}>
            <AlertCircle /> Critical Anomalies Detected (Last 24h)
          </h2>
          <div style={{ display: 'grid', gap: '16px' }}>
            {data.anomalies.map((anomaly) => (
              <div key={anomaly.id} style={{ padding: '16px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: 'var(--radius-md)' }}>
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
