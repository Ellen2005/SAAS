import React, { useEffect, useState, useCallback } from 'react';
import { FileText, RefreshCcw, ChevronDown, ChevronRight, Edit3, Send, Check, X, Download, FileSpreadsheet, Trash2 } from 'lucide-react';
import { apiJson, apiFetch, API_URL } from '../lib/api';
import { useAuth } from '../lib/authContext';
import { useToast } from '../components/ToastProvider';
import NarrativeRenderer from '../components/NarrativeRenderer';

const REPORTS_CACHE_KEY = 'saas.reports.cache.v1';

const readReportsCache = () => {
  try {
    const raw = localStorage.getItem(REPORTS_CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
};

const writeReportsCache = (payload) => {
  try { localStorage.setItem(REPORTS_CACHE_KEY, JSON.stringify(payload)); } catch { /* noop */ }
};

const ReportsHistory = () => {
  const { user, isManager } = useAuth();
  const toast = useToast();
  const [tab, setTab] = useState('daily'); // 'daily' | 'professional'
  const [reports, setReports] = useState(() => readReportsCache() || []);
  const [proReports, setProReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [proLoading, setProLoading] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editText, setEditText] = useState('');
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(null);
  const [sentId, setSentId] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null); // reportId pending deletion

  const fetchReports = useCallback(async () => {
    if (!user) return;
    try {
      const data = await apiJson('/api/reports/history');
      setReports(data.reports || []);
      writeReportsCache(data.reports || []);
    } catch {
      const cached = readReportsCache();
      if (cached) setReports(cached);
    } finally {
      setLoading(false);
    }
  }, [user]);

  const fetchProReports = useCallback(async () => {
    if (!user) return;
    setProLoading(true);
    try {
      const data = await apiJson('/api/reports/professional/list');
      setProReports(data.reports || []);
    } catch { /* non-critical */ } finally {
      setProLoading(false);
    }
  }, [user]);

  useEffect(() => { fetchReports(); fetchProReports(); }, [fetchReports, fetchProReports]);

  const handleDeletePro = async (reportId) => {
    setConfirmDelete(reportId);
  };

  const confirmDeletePro = async () => {
    const reportId = confirmDelete;
    setConfirmDelete(null);
    if (!reportId) return;
    try {
      await apiFetch(`/api/reports/professional/${reportId}`, { method: 'DELETE' });
      setProReports(prev => prev.filter(r => r.report_id !== reportId));
    } catch (err) { toast.error(`Delete failed: ${err.message}`); }
  };

  const handleDownloadPro = async (reportId, format) => {
    try {
      const response = await apiFetch(`/api/reports/download/${reportId}?format=${format}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report-${reportId}.${format === 'excel' ? 'xlsx' : 'pdf'}`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (err) { toast.error(`Download failed: ${err.message}`); }
  };

  const handleStartEdit = (report) => {
    setEditingId(report.id);
    setEditText(report.narrative || '');
    setExpanded(report.id);
  };

  const handleSaveEdit = async (reportId) => {
    setSaving(true);
    try {
      await apiFetch(`/api/reports/${reportId}`, {
        method: 'PATCH',
        body: JSON.stringify({ narrative: editText }),
      });
      setReports((prev) => prev.map((r) => r.id === reportId ? { ...r, narrative: editText } : r));
      setEditingId(null);
    } catch (err) {
      toast.error(`Failed to save: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDownload = async (reportId, reportDate) => {
    try {
      const blob = await apiFetch(`/api/reports/${reportId}/download`).then(r => r.blob());
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report-${reportDate}.html`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(`Download failed: ${err.message}`);
    }
  };

  const handleExcelExport = async (reportId) => {
    try {
      const response = await apiFetch(`/api/export/reports/${reportId}/excel`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report-${reportId}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(`Excel export failed: ${err.message}`);
    }
  };

  const handleResend = async (reportId) => {
    setSending(reportId);
    try {
      await apiFetch(`/api/reports/${reportId}/send`, { method: 'POST' });
      setSentId(reportId);
      setTimeout(() => setSentId(null), 3000);
    } catch (err) {
      toast.error(`Failed to send: ${err.message}`);
    } finally {
      setSending(null);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
        <RefreshCcw size={32} style={{ animation: 'spin 1s linear infinite', marginRight: '12px' }} />
        <style>{'@keyframes spin{100%{transform:rotate(360deg)}}'}</style>
        Loading report history...
      </div>
    );
  }

  const tabStyle = (active) => ({
    padding: '8px 20px', border: 'none', cursor: 'pointer', fontWeight: active ? 600 : 400,
    borderBottom: active ? '2px solid var(--primary-color)' : '2px solid transparent',
    background: 'none', color: active ? 'var(--primary-color)' : 'var(--text-secondary)',
    fontSize: '0.95rem',
  });

  return (
    <div style={{ display: 'grid', gap: '24px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <FileText color="var(--primary-color)" /> Report History
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            All AI-generated reports. Click to read, edit the narrative, or resend to email recipients.
          </p>
        </div>
        <button className="btn btn-outline" onClick={() => { fetchReports(); fetchProReports(); }} style={{ display: 'flex', gap: '8px' }}>
          <RefreshCcw size={16} /> Refresh
        </button>
      </header>

      {/* Tabs */}
      <div style={{ borderBottom: '1px solid var(--border-color)', display: 'flex', gap: '0', overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
        <button style={tabStyle(tab === 'daily')} onClick={() => setTab('daily')}>Daily Reports</button>
        <button style={tabStyle(tab === 'professional')} onClick={() => setTab('professional')}>Professional PDF Reports</button>
      </div>

      {/* ── Professional reports tab ── */}
      {tab === 'professional' && (
        proLoading ? (
          <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-secondary)' }}>Loading…</div>
        ) : proReports.length === 0 ? (
          <div className="glass-panel" style={{ textAlign: 'center', padding: '48px' }}>
            <FileText size={48} color="var(--text-secondary)" style={{ marginBottom: '16px' }} />
            <h3 style={{ marginBottom: '8px' }}>No professional reports yet</h3>
            <p style={{ color: 'var(--text-secondary)' }}>
              Use the AI Analyst page to run a goal analysis, then click Generate Report to produce a full PDF.
            </p>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '12px' }}>
            {proReports.map(r => (
              <div key={r.id || r.report_id} className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{r.title || 'Analysis Report'}</div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    {r.report_type} · {r.created_at ? r.created_at.slice(0, 10) : ''}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button className="btn btn-outline" onClick={() => handleDownloadPro(r.id || r.report_id, 'pdf')} style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}>
                    <Download size={14} /> PDF
                  </button>
                  <button className="btn btn-outline" onClick={() => handleDownloadPro(r.id || r.report_id, 'excel')} style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}>
                    <FileSpreadsheet size={14} /> Excel
                  </button>
                  <button className="btn btn-outline" onClick={() => handleDeletePro(r.id || r.report_id)} style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px', color: 'var(--status-critical)' }}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {/* ── Daily reports tab ── */}
      {tab === 'daily' && (reports.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '48px' }}>
          <FileText size={48} color="var(--text-secondary)" style={{ marginBottom: '16px' }} />
          <h3 style={{ marginBottom: '8px' }}>No reports yet</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            Go to the Dashboard and click <strong>Generate Report</strong> to create your first report.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '12px' }}>
          {reports.map((report) => {
            const isExpanded = expanded === report.id;
            const isEditing = editingId === report.id;
            const wasSent = sentId === report.id;

            return (
              <div key={report.id} className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
                {/* Row header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 24px' }}>
                  <button
                    onClick={() => setExpanded(isExpanded ? null : report.id)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '14px', color: 'var(--text-primary)', textAlign: 'left', flex: 1 }}
                  >
                    {isExpanded ? <ChevronDown size={18} color="var(--primary-color)" /> : <ChevronRight size={18} color="var(--text-secondary)" />}
                    <div>
                      <div style={{ fontWeight: 600 }}>Report — {report.report_date}</div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        {report.narrative ? report.narrative.slice(0, 90) + '…' : 'No narrative'}
                      </div>
                    </div>
                  </button>

                  <div style={{ display: 'flex', gap: '8px', marginLeft: '16px', flexShrink: 0, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    <button
                      className="btn btn-outline"
                      onClick={() => handleDownload(report.id, report.report_date)}
                      style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}
                      title="Download as PDF"
                    >
                      <Download size={14} /> PDF
                    </button>
                    <button
                      className="btn btn-outline"
                      onClick={() => handleExcelExport(report.id)}
                      style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}
                      title="Export as Excel"
                    >
                      <FileSpreadsheet size={14} /> Excel
                    </button>
                    {isManager && (
                      <>
                        <button
                          className="btn btn-outline"
                          onClick={() => handleStartEdit(report)}
                          style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}
                          title="Edit narrative before sending"
                        >
                          <Edit3 size={14} /> Edit
                        </button>
                        <button
                          className="btn btn-primary"
                          onClick={() => handleResend(report.id)}
                          disabled={sending === report.id}
                          style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}
                          title="Send this report to email recipients"
                        >
                          {wasSent ? <><Check size={14} /> Sent!</> : sending === report.id ? 'Sending…' : <><Send size={14} /> Send</>}
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Expanded body */}
                {isExpanded && (
                  <div style={{ borderTop: '1px solid var(--border-color)', padding: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <h3 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Full Report Narrative
                      </h3>
                      {isEditing && (
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button className="btn btn-primary" onClick={() => handleSaveEdit(report.id)} disabled={saving} style={{ padding: '5px 14px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}>
                            <Check size={14} /> {saving ? 'Saving…' : 'Save'}
                          </button>
                          <button className="btn btn-outline" onClick={() => setEditingId(null)} style={{ padding: '5px 14px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}>
                            <X size={14} /> Cancel
                          </button>
                        </div>
                      )}
                    </div>

                    {isEditing ? (
                      <>
                        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                          Edit the narrative below. Changes are saved to the report record. Click <strong>Send</strong> after saving to email the updated version.
                        </p>
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          rows={16}
                          style={{ width: '100%', fontFamily: 'inherit', fontSize: '0.95rem', lineHeight: '1.7', resize: 'vertical' }}
                        />
                      </>
                    ) : (
                      <NarrativeRenderer text={report.narrative || 'No narrative was generated for this report.'} />
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ))}

      {confirmDelete && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }} onClick={() => setConfirmDelete(null)}>
          <div className="glass-panel" style={{ maxWidth: '380px', width: '100%', padding: '24px', textAlign: 'center' }}
            onClick={e => e.stopPropagation()}>
            <h3 style={{ marginBottom: '12px' }}>Delete Report?</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '20px' }}>
              This action cannot be undone. The report will be permanently removed.
            </p>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
              <button className="btn btn-outline" onClick={() => setConfirmDelete(null)} style={{ padding: '8px 20px' }}>Cancel</button>
              <button className="btn btn-primary" onClick={confirmDeletePro}
                style={{ padding: '8px 20px', background: 'var(--status-critical)', borderColor: 'var(--status-critical)' }}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportsHistory;
