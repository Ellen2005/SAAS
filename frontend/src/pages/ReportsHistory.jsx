import React, { useEffect, useState, useCallback } from 'react';
import { FileText, RefreshCcw, ChevronDown, ChevronRight, Edit3, Send, Check, X, Download } from 'lucide-react';
import { apiJson, apiFetch } from '../lib/api';
import { useAuth } from '../lib/authContext';

const ReportsHistory = () => {
  const { user, isManager } = useAuth();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editText, setEditText] = useState('');
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(null);
  const [sentId, setSentId] = useState(null);

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
      alert(`Failed to save: ${err.message}`);
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
      alert(`Download failed: ${err.message}`);
    }
  };

  const handleResend = async (reportId) => {
    setSending(reportId);
    try {
      await apiFetch(`/api/reports/${reportId}/send`, { method: 'POST' });
      setSentId(reportId);
      setTimeout(() => setSentId(null), 3000);
    } catch (err) {
      alert(`Failed to send: ${err.message}`);
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
        <button className="btn btn-outline" onClick={fetchReports} style={{ display: 'flex', gap: '8px' }}>
          <RefreshCcw size={16} /> Refresh
        </button>
      </header>

      {reports.length === 0 ? (
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

                  <div style={{ display: 'flex', gap: '8px', marginLeft: '16px', flexShrink: 0 }}>
                    <button
                      className="btn btn-outline"
                      onClick={() => handleDownload(report.id, report.report_date)}
                      style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}
                      title="Download a printable copy of this report"
                    >
                      <Download size={14} /> Download
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
                      <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.8', color: 'var(--text-primary)', fontSize: '0.95rem' }}>
                        {report.narrative || 'No narrative was generated for this report.'}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ReportsHistory;
