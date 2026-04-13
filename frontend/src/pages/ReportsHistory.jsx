import React, { useEffect, useState, useCallback } from 'react';
import { FileText, RefreshCcw, ChevronDown, ChevronRight } from 'lucide-react';
import { apiJson } from '../lib/api';
import { useAuth } from '../lib/authContext';

const ReportsHistory = () => {
  const { user } = useAuth();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  const fetchReports = useCallback(async () => {
    if (!user) return;
    try {
      const data = await apiJson('/api/reports/history');
      setReports(data.reports || []);
    } catch {
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { fetchReports(); }, [fetchReports]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
        <RefreshCcw size={32} style={{ animation: 'spin 1s linear infinite', marginRight: '12px' }} />
        <style>{'@keyframes spin{100%{transform:rotate(360deg)}}'}</style>
        Loading report history...
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gap: '24px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <FileText color="var(--primary-color)" /> Report History
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Every AI-generated report your department has produced. Click any report to read the full narrative.
          </p>
        </div>
        <button className="btn btn-outline" onClick={fetchReports} style={{ display: 'flex', gap: '8px' }}>
          <RefreshCcw size={16} /> Refresh
        </button>
      </header>

      {reports.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '48px' }}>
          <FileText size={48} color="var(--text-secondary)" style={{ marginBottom: '16px' }} />
          <h3 style={{ marginBottom: '8px' }}>No reports yet</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            Go to the Dashboard and click <strong>Sync Now</strong> to generate your first report.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '12px' }}>
          {reports.map((report) => (
            <div key={report.id} className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
              <button
                onClick={() => setExpanded(expanded === report.id ? null : report.id)}
                style={{
                  width: '100%', background: 'none', border: 'none', cursor: 'pointer',
                  padding: '20px 24px', display: 'flex', justifyContent: 'space-between',
                  alignItems: 'center', color: 'var(--text-primary)', textAlign: 'left',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  {expanded === report.id ? <ChevronDown size={18} color="var(--primary-color)" /> : <ChevronRight size={18} color="var(--text-secondary)" />}
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '1rem' }}>
                      Report — {report.report_date}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      {report.narrative ? report.narrative.slice(0, 100) + (report.narrative.length > 100 ? '…' : '') : 'No narrative'}
                    </div>
                  </div>
                </div>
                <span style={{
                  fontSize: '0.75rem', padding: '3px 10px', borderRadius: '999px',
                  background: 'rgba(59,130,246,0.12)', color: 'var(--primary-color)', whiteSpace: 'nowrap',
                }}>
                  {report.report_date}
                </span>
              </button>

              {expanded === report.id && (
                <div style={{ padding: '0 24px 24px', borderTop: '1px solid var(--border-color)' }}>
                  <h3 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', margin: '16px 0 8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Full AI Narrative
                  </h3>
                  <p style={{ lineHeight: '1.7', color: 'var(--text-primary)', fontSize: '1rem' }}>
                    {report.narrative || 'No narrative was generated for this report.'}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ReportsHistory;
