import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertCircle, ArrowUpRight, ArrowDownRight, RefreshCcw } from 'lucide-react';

// MOCK DATA
const mockKpis = [
  { id: 1, name: 'Total Revenue', value: '$142,300', dod: '+6.0%', trend: 'up', status: 'normal' },
  { id: 2, name: 'Inventory Value', value: '$450,000', dod: '-2.1%', trend: 'down', status: 'warning' },
  { id: 3, name: 'Support Tickets', value: '124', dod: '+40%', trend: 'up', status: 'critical' },
  { id: 4, name: 'Active Users', value: '4,200', dod: '+1.5%', trend: 'up', status: 'normal' }
];

const mockChartData = [
  { name: 'Mon', revenue: 135000 },
  { name: 'Tue', revenue: 138000 },
  { name: 'Wed', revenue: 132000 },
  { name: 'Thu', revenue: 141000 },
  { name: 'Fri', revenue: 142300 },
];

const Dashboard = () => {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate < 2s load time from cache
    const timer = setTimeout(() => setLoading(false), 800);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
        <RefreshCcw className="spinning-loader" size={48} style={{ animation: 'spin 1s linear infinite' }} />
        <span style={{ marginLeft: '16px', fontSize: '1.2rem' }}>Loading Cached Analytics...</span>
        <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <header style={{ marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1>Executive Summary</h1>
          <p>Your daily automated insights. Last refreshed: 2:00 AM Local Time.</p>
        </div>
        <button className="btn btn-outline" style={{ display: 'flex', gap: '8px' }}>
          <RefreshCcw size={18} /> Sync Now
        </button>
      </header>

      {/* AI Narrative Section */}
      <section className="glass-panel" style={{ marginBottom: '32px', borderLeft: '4px solid var(--primary-color)' }}>
        <h2 style={{ fontSize: '1.2rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--primary-color)' }}>✧</span> AI Narrative
        </h2>
        <p style={{ fontSize: '1.05rem', lineHeight: '1.6', color: 'var(--text-primary)' }}>
          Today's revenue of $142,300 is 6% above last Monday, driven largely by a 14% volume spike in the North region. 
          Inventory for Product A is trending toward stockout — current stock covers approximately 4 days at current velocity. 
          <strong style={{ color: 'var(--status-critical)', marginLeft: '6px' }}>
            One anomaly detected: Support tickets jumped 40% — may be worth a systems check.
          </strong>
        </p>
      </section>

      {/* KPI Cards Grid */}
      <div className="dashboard-grid">
        {mockKpis.map(kpi => (
          <div key={kpi.id} className="glass-panel" style={{ cursor: 'pointer' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{kpi.name}</span>
              <span className={`badge badge-${kpi.status}`}>{kpi.status}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
              <span style={{ fontSize: '2.5rem', fontWeight: 700, letterSpacing: '-0.03em' }}>{kpi.value}</span>
              <span style={{ 
                color: kpi.status === 'critical' ? 'var(--status-critical)' : 'var(--status-normal)',
                display: 'flex', alignItems: 'center', fontWeight: '600'
              }}>
                {kpi.trend === 'up' ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
                {kpi.dod}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Section */}
      <div className="dashboard-grid" style={{ gridTemplateColumns: '1fr' }}>
        <div className="glass-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px' }}>
            <h2>Revenue Trend (7 Days)</h2>
            <div style={{ display: 'flex', gap: '16px' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
                <span style={{ width: 12, height: 12, borderRadius: '50%', background: 'var(--primary-color)' }}></span>
                Actual
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                <span style={{ width: 12, height: 2, background: 'var(--text-secondary)', borderStyle: 'dashed' }}></span>
                Forecast (Prophet)
              </span>
            </div>
          </div>
          <div style={{ height: 300, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mockChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}} />
                <YAxis stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}} 
                       domain={['dataMin - 5000', 'dataMax + 5000']} 
                       tickFormatter={(val) => `$${val/1000}k`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--surface-hover)', border: 'none', borderRadius: '8px', color: '#fff' }}
                  itemStyle={{ color: 'var(--primary-color)' }}
                />
                <Line type="monotone" dataKey="revenue" stroke="var(--primary-color)" strokeWidth={3} dot={{r: 4, fill: 'var(--primary-color)'}} activeDot={{ r: 8 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Anomalies Section */}
      <section className="glass-panel" style={{ borderLeft: '4px solid var(--status-critical)' }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--status-critical)' }}>
          <AlertCircle /> Critical Anomalies Detected (Last 24h)
        </h2>
        <div style={{ marginTop: '16px', padding: '16px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: 'var(--radius-md)' }}>
          <h4 style={{ color: 'var(--text-primary)', marginBottom: '4px' }}>Support Tickets Spiked</h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            Volume is +40% above the 7-day rolling average for Mondays. Correlated with a 12% drop in order processing speed.
          </p>
          <div style={{ marginTop: '12px' }}>
            <button className="btn btn-outline" style={{ fontSize: '0.8rem', padding: '6px 12px', background: 'transparent', borderColor: 'var(--status-critical)', color: 'var(--status-critical)' }}>
              Mark as Investigating
            </button>
          </div>
        </div>
      </section>

    </div>
  );
};

export default Dashboard;
