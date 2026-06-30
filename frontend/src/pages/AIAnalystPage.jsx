import React, { useCallback, useEffect, useState } from 'react';
import {
  Brain, TrendingUp, Shield, Users, Zap, RefreshCw,
  AlertTriangle, CheckCircle, Info, ChevronDown, ChevronRight,
  BookOpen, Share2, Trash2, BarChart2, Play, Target, History,
  Eye, FileSearch, Lightbulb, TrendingDown, ShieldAlert,
  CalendarClock, ArrowRight, AlertCircle,
} from 'lucide-react';
import { apiJson, apiFetch } from '../lib/api';
import { useAuth } from '../lib/authContext';
import { useLang } from '../lib/i18n';
import ChartRenderer from '../components/ChartRenderer';

const card = {
  background: 'var(--ea-bg-card)',
  border: '1px solid var(--ea-border)',
  borderRadius: 14,
  padding: 20,
};

const pill = (color = '#3b82f6') => ({
  fontSize: '0.7rem', padding: '2px 8px', borderRadius: 999,
  background: `${color}22`, color, fontWeight: 600,
  letterSpacing: 0.3, textTransform: 'uppercase',
  display: 'inline-block',
});

const SEVERITY_COLOR = { warning: '#f59e0b', info: '#3b82f6', critical: '#ef4444' };
const INSIGHT_ICON = {
  trend_shift: <TrendingUp size={16} />,
  correlation: <BarChart2 size={16} />,
  concentration_risk: <AlertTriangle size={16} />,
  data_freshness: <Info size={16} />,
};

function GradeRing({ grade, score }) {
  const color = score >= 90 ? '#10b981' : score >= 75 ? '#3b82f6' : score >= 60 ? '#f59e0b' : '#ef4444';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <div style={{
        width: 80, height: 80, borderRadius: '50%',
        border: `6px solid ${color}`, display: 'flex',
        flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        background: 'var(--ea-bg-card)',
      }}>
        <span style={{ fontSize: '1.6rem', fontWeight: 700, color }}>{grade}</span>
      </div>
      <span style={{ fontSize: '0.85rem', color: 'var(--ea-text-secondary)' }}>{score}/100</span>
    </div>
  );
}

function DimensionBar({ label, value }) {
  const color = value >= 80 ? '#10b981' : value >= 60 ? '#f59e0b' : '#ef4444';
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: '0.85rem' }}>
        <span style={{ textTransform: 'capitalize' }}>{label}</span>
        <span style={{ color, fontWeight: 600 }}>{value}%</span>
      </div>
      <div style={{ height: 6, borderRadius: 3, background: 'var(--ea-bg-hover)' }}>
        <div style={{ height: '100%', width: `${value}%`, borderRadius: 3, background: color, transition: 'width 0.6s ease' }} />
      </div>
    </div>
  );
}

export default function AIAnalystPage() {
  const { isManager } = useAuth();
  const { lang, t } = useLang();
  const [tab, setTab] = useState('insights');
  const [loading, setLoading] = useState(false);
  const [fullResult, setFullResult] = useState(null);
  const [insights, setInsights] = useState(null);
  const [governance, setGovernance] = useState(null);
  const [explanations, setExplanations] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [snapshotTitle, setSnapshotTitle] = useState('');
  const [snapshotContent, setSnapshotContent] = useState('');
  const [teamMessage, setTeamMessage] = useState('');
  const [savingSnap, setSavingSnap] = useState(false);
  const [expandedInsight, setExpandedInsight] = useState(null);
  const [runningFull, setRunningFull] = useState(false);
  const [error, setError] = useState(null);

  // Analysis tab state
  const [goal, setGoal] = useState('');
  const [formula, setFormula] = useState('');
  const [presets, setPresets] = useState([]);
  const [runs, setRuns] = useState([]);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState('');

  const loadInsights = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ins, gov, xai, snaps] = await Promise.all([
        apiJson('/api/analyst/insights'),
        apiJson('/api/analyst/governance'),
        apiJson('/api/analyst/explain/all'),
        apiJson('/api/analyst/snapshots'),
      ]);
      setInsights(ins);
      setGovernance(gov);
      setExplanations(xai);
      setSnapshots(snaps.snapshots || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAnalysisMeta = useCallback(async () => {
    try {
      const [presetRes, runsRes] = await Promise.all([
        apiJson(`/api/analysis/presets?lang=${lang}`),
        apiJson('/api/analysis/runs'),
      ]);
      setPresets(presetRes.presets || []);
      setRuns(runsRes.runs || []);
    } catch (e) {
      console.error(e);
    }
  }, [lang]);

  useEffect(() => { 
    loadInsights(); 
    loadAnalysisMeta();
  }, [loadInsights, loadAnalysisMeta]);

  const runFullAnalysis = async () => {
    setRunningFull(true);
    setError(null);
    try {
      const result = await apiJson('/api/analyst/run-full', { method: 'POST' });
      setFullResult(result);
      // Refresh all panels
      await loadInsights();
    } catch (e) {
      setError(e.message);
    } finally {
      setRunningFull(false);
    }
  };

  const saveSnapshot = async () => {
    if (!snapshotTitle.trim() || !snapshotContent.trim()) return;
    setSavingSnap(true);
    try {
      await apiFetch('/api/analyst/snapshots', {
        method: 'POST',
        body: JSON.stringify({ title: snapshotTitle, content: snapshotContent, insight_type: 'manual' }),
      });
      setSnapshotTitle('');
      setSnapshotContent('');
      const snaps = await apiJson('/api/analyst/snapshots');
      setSnapshots(snaps.snapshots || []);
    } catch (e) {
      alert(e.message);
    } finally {
      setSavingSnap(false);
    }
  };

  const sendTeamMessage = async () => {
    if (!teamMessage.trim()) return;
    setSavingSnap(true);
    try {
      await apiFetch('/api/analyst/snapshots', {
        method: 'POST',
        body: JSON.stringify({
          title: 'Team message',
          content: teamMessage,
          insight_type: 'message',
        }),
      });
      setTeamMessage('');
      const snaps = await apiJson('/api/analyst/snapshots');
      setSnapshots(snaps.snapshots || []);
    } catch (e) {
      alert(e.message);
    } finally {
      setSavingSnap(false);
    }
  };

  const deleteSnapshot = async (id) => {
    try {
      await apiFetch(`/api/analyst/snapshots/${id}`, { method: 'DELETE' });
      setSnapshots((prev) => prev.filter((s) => s.id !== id));
    } catch (e) {
      alert(e.message);
    }
  };

  const runAnalysis = async (presetSlug = null) => {
    setAnalysisLoading(true);
    setAnalysisError('');
    setAnalysisResult(null);
    try {
      const body = {
        goal_text: goal || (presetSlug ? '' : 'Institutional KPI summary'),
        preset_slug: presetSlug || undefined,
        formula: formula.trim() || undefined,
      };
      const res = await apiJson('/api/analysis/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      setAnalysisResult(res);
      loadAnalysisMeta();
    } catch (e) {
      setAnalysisError(e.message || 'Analysis failed');
    } finally {
      setAnalysisLoading(false);
    }
  };

  const TABS = [
    { id: 'insights', label: t('analyst_insights') || 'AI Insights', icon: <Zap size={15} /> },
    { id: 'analysis', label: t('analyst_goal_analysis') || 'Goal Analysis', icon: <BarChart2 size={15} /> },
    { id: 'governance', label: t('analyst_governance') || 'Governance', icon: <Shield size={15} /> },
    { id: 'xai', label: t('analyst_xai') || 'Explainable AI', icon: <Brain size={15} /> },
    { id: 'collaboration', label: t('analyst_collaboration') || 'Collaboration', icon: <Users size={15} /> },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ margin: 0, display: 'flex', gap: 10, alignItems: 'center' }}>
            <Brain size={28} color="var(--ea-primary)" /> AI Analyst
          </h1>
          <p style={{ color: 'var(--ea-text-secondary)', marginTop: 4 }}>
            Autonomous analytics — proactive insights, governance scoring, explainable AI, and team collaboration.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="ea-btn ea-btn-secondary" onClick={loadInsights} disabled={loading}>
            <RefreshCw size={14} style={loading ? { animation: 'spin 1s linear infinite' } : null} /> Refresh
          </button>
          {isManager && (
            <button className="ea-btn ea-btn-primary" onClick={runFullAnalysis} disabled={runningFull}>
              <Brain size={14} style={runningFull ? { animation: 'spin 1s linear infinite' } : null} />
              {runningFull ? 'Analysing…' : 'Run Full Analysis'}
            </button>
          )}
        </div>
      </header>

      <style>{'@keyframes spin{100%{transform:rotate(360deg)}}'}</style>

      {error && (
        <div style={{ ...card, borderColor: '#ef4444', color: 'var(--ea-danger)', display: 'flex', gap: 8 }}>
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      {fullResult?.status === 'no_data' && (
        <div style={{ ...card, borderColor: '#f59e0b', color: 'var(--ea-warning)' }}>
          No data yet — go to Dashboard and click Generate Report first.
        </div>
      )}

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 4, padding: 4, background: 'var(--ea-bg-hover)', borderRadius: 12, border: '1px solid var(--ea-border)', flexWrap: 'wrap' }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: tab === t.id ? 'var(--ea-primary)' : 'transparent',
              color: tab === t.id ? 'white' : 'var(--ea-text-primary)',
              fontWeight: 500, fontSize: '0.85rem', display: 'flex', gap: 6, alignItems: 'center',
              transition: 'all 0.2s',
            }}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ── Augmented Insights ── */}
      {tab === 'insights' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {loading && <p style={{ color: 'var(--ea-text-secondary)' }}>Loading insights…</p>}
          {insights && insights.insights?.length === 0 && (
            <div style={{ ...card, textAlign: 'center', padding: 40 }}>
              <CheckCircle size={40} color="#10b981" style={{ marginBottom: 12 }} />
              <h3>All Clear</h3>
              <p style={{ color: 'var(--ea-text-secondary)' }}>
                {insights.message || 'No unusual patterns detected. All metrics are within normal range.'}
              </p>
            </div>
          )}
          {/* Summary bar */}
          {insights?.insights?.length > 0 && (
            <div style={{ ...card, display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap', padding: '14px 20px' }}>
              <span style={{ fontWeight: 600, color: 'var(--ea-text-primary)' }}>{insights.insights.length} insight{insights.insights.length > 1 ? 's' : ''}</span>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {['critical', 'warning', 'info'].map(sev => {
                  const count = insights.insights.filter(i => i.severity === sev).length;
                  if (count === 0) return null;
                  return (
                    <span key={sev} style={pill(SEVERITY_COLOR[sev])}>
                      {count} {sev}
                    </span>
                  );
                })}
              </div>
            </div>
          )}
          {(insights?.insights || []).map((ins, i) => {
            const color = SEVERITY_COLOR[ins.severity] || '#3b82f6';
            const isOpen = expandedInsight === i;
            const isActionable = /consider|recommend|should|investigate|review|ensure|monitor|check|verify/i.test(
              typeof ins.explanation === 'string' ? ins.explanation : JSON.stringify(ins.explanation)
            );
            return (
              <div key={i} style={{ ...card, borderLeft: `4px solid ${color}`, padding: '14px 18px' }}>
                <div
                  onClick={() => setExpandedInsight(isOpen ? null : i)}
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                >
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center', flex: 1 }}>
                    <span style={{ color, flexShrink: 0 }}>{INSIGHT_ICON[ins.type] || <Info size={16} />}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, color: 'var(--ea-text-primary)', fontSize: '0.92rem' }}>{ins.title}</div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--ea-text-secondary)', marginTop: 3, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        <span style={pill(color)}>{ins.type.replace(/_/g, ' ')}</span>
                        {ins.kpi && <span style={pill('#6b7280')}>{ins.kpi?.replace(/_/g, ' ')}</span>}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                    {typeof ins.value === 'number' && (
                      <span style={{ fontWeight: 700, color, fontSize: '1.05rem' }}>
                        {ins.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                      </span>
                    )}
                    {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </div>
                </div>
                {isOpen && (
                  <div style={{ marginTop: 12, padding: '12px 0 0', borderTop: '1px solid var(--ea-border)' }}>
                    <p style={{ color: 'var(--ea-text-primary)', lineHeight: 1.7, margin: 0 }}>
                      {typeof ins.explanation === 'string' ? ins.explanation : (ins.explanation?.reason || ins.explanation?.text || JSON.stringify(ins.explanation))}
                    </p>
                    {isActionable && (
                      <div style={{ marginTop: 10, padding: '8px 12px', background: 'rgba(16,185,129,0.06)', borderRadius: 8, fontSize: '0.82rem', color: '#10b981', fontWeight: 500 }}>
                        ✓ This insight suggests an action you can take
                      </div>
                    )}
                    {ins.xai_explanation && ins.xai_explanation !== ins.explanation && (
                      <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.85rem', marginTop: 8, fontStyle: 'italic' }}>
                        {ins.xai_explanation}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {insights && insights.generated_at && (
            <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.78rem', textAlign: 'right' }}>
              Last updated: {new Date(insights.generated_at).toLocaleString()}
            </p>
          )}
        </div>
      )}

      {/* ── Goal Analysis ── */}
      {tab === 'analysis' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={card}>
            <h3 style={{ marginTop: 0, display: 'flex', gap: 8, alignItems: 'center', color: 'var(--ea-text-primary)' }}>
              <Target size={16} /> Goal-Driven Analysis
            </h3>
            <p style={{ color: 'var(--ea-text-secondary)', marginBottom: 16 }}>
              Describe what you want to analyze and let AI generate the appropriate queries and insights.
            </p>
            
            <div className="form-group">
              <label>Analysis Goal</label>
              <textarea
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="e.g., Show contribution collection rates by region for the last 6 months"
                rows={3}
              />
            </div>
            
            <div className="form-group">
              <label>Custom Formula (Optional)</label>
              <input
                type="text"
                value={formula}
                onChange={(e) => setFormula(e.target.value)}
                placeholder="e.g., (paid_contributions / total_contributions) * 100"
              />
            </div>
            
            <button 
              className="ea-btn ea-btn-primary" 
              disabled={analysisLoading} 
              onClick={() => runAnalysis()}
            >
              <Play size={14} /> {analysisLoading ? 'Analyzing...' : 'Run Analysis'}
            </button>
            
            {analysisError && (
              <div style={{ color: '#ef4444', marginTop: 12, padding: 12, background: 'rgba(239,68,68,0.1)', borderRadius: 8 }}>
                {analysisError}
              </div>
            )}
          </div>

          {/* Analysis Presets */}
          <div style={card}>
            <h3 style={{ marginTop: 0, color: 'var(--ea-text-primary)' }}>Quick Analysis Presets</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
              {presets.map((p) => (
                <button
                  key={p.slug || p.id}
                  type="button"
                  style={{
                    ...card,
                    textAlign: 'left',
                    cursor: 'pointer',
                    border: '1px solid var(--ea-border)',
                    background: 'var(--ea-bg-card)',
                    transition: 'all 0.2s',
                  }}
                  onClick={() => {
                    setGoal(p.default_goal_text || '');
                    runAnalysis(p.slug);
                  }}
                >
                  <div style={{ fontWeight: 600, color: 'var(--ea-text-primary)', marginBottom: 6 }}>{p.title}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--ea-text-secondary)' }}>{p.category}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Analysis Result */}
          {analysisResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* ── Overview ── */}
              {analysisResult.explanation?.overview && (
                <div style={{ ...card, background: 'var(--ea-primary-bg)', borderLeft: '4px solid var(--ea-primary)', padding: '16px 20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <Eye size={16} color="var(--ea-primary)" />
                    <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--ea-primary)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Overview</span>
                  </div>
                  <p style={{ margin: 0, color: 'var(--ea-text-primary)', lineHeight: 1.7, fontSize: '0.92rem' }}>
                    {analysisResult.explanation.overview}
                  </p>
                  {analysisResult.explanation.what_this_means && analysisResult.explanation.what_this_means !== analysisResult.explanation.overview && (
                    <p style={{ margin: '8px 0 0', color: 'var(--ea-text-secondary)', fontSize: '0.85rem', fontStyle: 'italic' }}>
                      {analysisResult.explanation.what_this_means}
                    </p>
                  )}
                </div>
              )}

              {/* ── Tables Explored ── */}
              {analysisResult.explanation?.tables_explored && (
                <details open style={{ ...card, borderLeft: '4px solid #06b6d4' }}>
                  <summary style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, color: 'var(--ea-text-primary)', fontSize: '0.9rem' }}>
                    <FileSearch size={15} color="#06b6d4" /> Data Sources & Tables Explored
                  </summary>
                  <p style={{ margin: '10px 0 0', color: 'var(--ea-text-primary)', lineHeight: 1.6, fontSize: '0.88rem' }}>
                    {analysisResult.explanation.tables_explored}
                  </p>
                </details>
              )}

              {/* ── KPI Cards from data ── */}
              {analysisResult.chart?.data?.length > 0 && (() => {
                const rows = analysisResult.chart.data;
                const yKey = analysisResult.chart.yKey;
                const xKey = analysisResult.chart.xKey || 'name';
                if (!yKey) return null;
                const values = rows.map(d => Number(d[yKey])).filter(v => !isNaN(v));
                if (values.length === 0) return null;
                const sum = values.reduce((a, b) => a + b, 0);
                const avg = sum / values.length;
                const max = Math.max(...values);
                const min = Math.min(...values);
                const maxItem = rows.find(d => Number(d[yKey]) === max);
                const minItem = rows.find(d => Number(d[yKey]) === min);
                return (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
                    {[
                      { label: 'Total', value: sum.toLocaleString(undefined, { maximumFractionDigits: 0 }), color: '#3b82f6' },
                      { label: 'Average', value: avg.toLocaleString(undefined, { maximumFractionDigits: 1 }), color: '#8b5cf6' },
                      { label: 'Highest', value: max.toLocaleString(undefined, { maximumFractionDigits: 0 }), sub: maxItem ? maxItem[xKey] : '', color: '#10b981' },
                      { label: 'Lowest', value: min.toLocaleString(undefined, { maximumFractionDigits: 0 }), sub: minItem ? minItem[xKey] : '', color: '#f59e0b' },
                      { label: 'Records', value: values.length, color: '#6b7280' },
                    ].map((kpi, i) => (
                      <div key={i} style={{ ...card, textAlign: 'center', padding: 14 }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>{kpi.label}</div>
                        <div style={{ fontSize: '1.3rem', fontWeight: 700, color: kpi.color }}>{kpi.value}</div>
                        {kpi.sub && <div style={{ fontSize: '0.72rem', color: 'var(--ea-text-secondary)', marginTop: 2 }}>{kpi.sub}</div>}
                      </div>
                    ))}
                  </div>
                );
              })()}

              {/* ── Chart ── */}
              {analysisResult.chart && (
                <div style={card}>
                  <ChartRenderer
                    spec={{
                      type: analysisResult.chart.type || 'bar',
                      data: analysisResult.chart.data,
                      title: analysisResult.chart.title,
                      xKey: analysisResult.chart.xKey || 'name',
                      yKey: analysisResult.chart.yKey,
                    }}
                  />
                  {analysisResult.chart.data?.length > 1 && (() => {
                    const yKey = analysisResult.chart.yKey;
                    if (!yKey) return null;
                    const values = analysisResult.chart.data.map(d => Number(d[yKey])).filter(v => !isNaN(v));
                    const max = Math.max(...values);
                    const min = Math.min(...values);
                    if (min > 0 && max / min > 3) {
                      return (
                        <div style={{ marginTop: 10, padding: '8px 12px', background: 'rgba(245,158,11,0.08)', borderRadius: 8, fontSize: '0.82rem', color: '#f59e0b' }}>
                          ⚠ High variability — the highest value is {((max / min)).toFixed(1)}× the lowest. Review the causes of this gap.
                        </div>
                      );
                    }
                    return null;
                  })()}
                </div>
              )}

              {/* ── Observations ── */}
              {analysisResult.explanation?.observations?.length > 0 && (
                <details open style={{ ...card, borderLeft: '4px solid #8b5cf6' }}>
                  <summary style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, color: 'var(--ea-text-primary)', fontSize: '0.9rem' }}>
                    <Eye size={15} color="#8b5cf6" /> Observations ({analysisResult.explanation.observations.length})
                  </summary>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
                    {analysisResult.explanation.observations.map((obs, i) => (
                      <div key={i} style={{
                        padding: '10px 14px', background: 'var(--ea-bg-hover)',
                        borderRadius: 8, borderLeft: '3px solid #8b5cf6',
                        fontSize: '0.88rem', color: 'var(--ea-text-primary)', lineHeight: 1.6,
                      }}>
                        {typeof obs === 'string' ? obs : obs.text || JSON.stringify(obs)}
                      </div>
                    ))}
                  </div>
                </details>
              )}

              {/* ── Insights ── */}
              {analysisResult.explanation?.insights?.length > 0 && (
                <details open style={{ ...card, borderLeft: '4px solid #10b981' }}>
                  <summary style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, color: 'var(--ea-text-primary)', fontSize: '0.9rem' }}>
                    <Lightbulb size={15} color="#10b981" /> Insights ({analysisResult.explanation.insights.length})
                  </summary>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
                    {analysisResult.explanation.insights.map((ins, i) => (
                      <div key={i} style={{
                        padding: '10px 14px', background: 'rgba(16,185,129,0.06)',
                        borderRadius: 8, borderLeft: '3px solid #10b981',
                        fontSize: '0.88rem', color: 'var(--ea-text-primary)', lineHeight: 1.6,
                      }}>
                        {typeof ins === 'string' ? ins : ins.text || JSON.stringify(ins)}
                      </div>
                    ))}
                  </div>
                </details>
              )}

              {/* ── Forecasts ── */}
              {analysisResult.explanation?.forecasts && (
                <details open style={{ ...card, borderLeft: '4px solid #f59e0b' }}>
                  <summary style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, color: 'var(--ea-text-primary)', fontSize: '0.9rem' }}>
                    <CalendarClock size={15} color="#f59e0b" /> Forecast & Projections
                  </summary>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
                    {analysisResult.explanation.forecasts.projection && (
                      <div style={{ padding: '10px 14px', background: 'var(--ea-bg-hover)', borderRadius: 8, fontSize: '0.88rem', lineHeight: 1.6 }}>
                        <span style={{ fontWeight: 600, color: 'var(--ea-text-primary)' }}>Projection: </span>
                        <span style={{ color: 'var(--ea-text-primary)' }}>{analysisResult.explanation.forecasts.projection}</span>
                      </div>
                    )}
                    {analysisResult.explanation.forecasts.scenario_best && (
                      <div style={{ padding: '10px 14px', background: 'rgba(16,185,129,0.06)', borderRadius: 8, fontSize: '0.88rem', lineHeight: 1.6 }}>
                        <span style={{ fontWeight: 600, color: '#10b981' }}>Best Case: </span>
                        <span style={{ color: 'var(--ea-text-primary)' }}>{analysisResult.explanation.forecasts.scenario_best}</span>
                      </div>
                    )}
                    {analysisResult.explanation.forecasts.scenario_worst && (
                      <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.06)', borderRadius: 8, fontSize: '0.88rem', lineHeight: 1.6 }}>
                        <span style={{ fontWeight: 600, color: '#ef4444' }}>Worst Case: </span>
                        <span style={{ color: 'var(--ea-text-primary)' }}>{analysisResult.explanation.forecasts.scenario_worst}</span>
                      </div>
                    )}
                    {analysisResult.explanation.forecasts.trigger && (
                      <div style={{ padding: '10px 14px', background: 'rgba(139,92,246,0.06)', borderRadius: 8, fontSize: '0.88rem', lineHeight: 1.6 }}>
                        <span style={{ fontWeight: 600, color: '#8b5cf6' }}>Trigger to Change: </span>
                        <span style={{ color: 'var(--ea-text-primary)' }}>{analysisResult.explanation.forecasts.trigger}</span>
                      </div>
                    )}
                  </div>
                </details>
              )}

              {/* ── Risk Analysis ── */}
              {analysisResult.explanation?.risk_analysis?.length > 0 && (
                <details open style={{ ...card, borderLeft: '4px solid #ef4444' }}>
                  <summary style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, color: 'var(--ea-text-primary)', fontSize: '0.9rem' }}>
                    <ShieldAlert size={15} color="#ef4444" /> Risk Analysis ({analysisResult.explanation.risk_analysis.length})
                  </summary>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
                    {analysisResult.explanation.risk_analysis.map((risk, i) => {
                      const severity = risk.severity || 'medium';
                      const sevColor = severity === 'high' ? '#ef4444' : severity === 'medium' ? '#f59e0b' : '#10b981';
                      return (
                        <div key={i} style={{
                          padding: '10px 14px', background: `${sevColor}08`,
                          borderRadius: 8, borderLeft: `3px solid ${sevColor}`,
                          fontSize: '0.88rem', lineHeight: 1.6,
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                            <span style={{ fontSize: '0.7rem', fontWeight: 600, color: sevColor, textTransform: 'uppercase', padding: '2px 6px', background: `${sevColor}15`, borderRadius: 4 }}>
                              {severity}
                            </span>
                            <span style={{ fontWeight: 600, color: 'var(--ea-text-primary)' }}>
                              {risk.risk || risk.title || 'Risk identified'}
                            </span>
                          </div>
                          {risk.impact && (
                            <div style={{ color: 'var(--ea-text-secondary)', fontSize: '0.85rem' }}>
                              Impact: {risk.impact}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </details>
              )}

              {/* ── Recommendations ── */}
              {analysisResult.explanation?.recommendations?.length > 0 && (
                <details open style={{ ...card, borderLeft: '4px solid #06b6d4' }}>
                  <summary style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, color: 'var(--ea-text-primary)', fontSize: '0.9rem' }}>
                    <ArrowRight size={15} color="#06b6d4" /> Recommendations ({analysisResult.explanation.recommendations.length})
                  </summary>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
                    {analysisResult.explanation.recommendations.map((rec, i) => {
                      const priority = rec.priority || 'medium';
                      const pColor = priority === 'high' ? '#ef4444' : priority === 'medium' ? '#f59e0b' : '#10b981';
                      return (
                        <div key={i} style={{
                          padding: '12px 16px', background: 'var(--ea-bg-hover)',
                          borderRadius: 8, borderLeft: `3px solid ${pColor}`,
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                            <span style={{
                              fontSize: '0.68rem', fontWeight: 600, color: pColor,
                              textTransform: 'uppercase', padding: '2px 8px',
                              background: `${pColor}12`, borderRadius: 4,
                            }}>
                              {priority} priority
                            </span>
                            {rec.timeline && (
                              <span style={{ fontSize: '0.72rem', color: 'var(--ea-text-secondary)' }}>
                                {rec.timeline}
                              </span>
                            )}
                          </div>
                          <div style={{ fontWeight: 600, color: 'var(--ea-text-primary)', fontSize: '0.9rem', marginBottom: 4 }}>
                            {rec.action}
                          </div>
                          {rec.expected_impact && (
                            <div style={{ fontSize: '0.82rem', color: 'var(--ea-text-secondary)' }}>
                              Expected impact: {rec.expected_impact}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </details>
              )}

              {/* ── Limitations & Assumptions ── */}
              {(analysisResult.explanation?.limitations?.length > 0 || analysisResult.explanation?.assumptions?.length > 0) && (
                <details style={card}>
                  <summary style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, color: 'var(--ea-text-primary)', fontSize: '0.9rem' }}>
                    <Info size={15} /> Assumptions & Limitations
                  </summary>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 12 }}>
                    {analysisResult.explanation.assumptions?.length > 0 && (
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--ea-text-secondary)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.3 }}>Assumptions</div>
                        <ul style={{ margin: 0, paddingLeft: 16, fontSize: '0.85rem', color: 'var(--ea-text-primary)', lineHeight: 1.7 }}>
                          {analysisResult.explanation.assumptions.map((a, i) => <li key={i}>{a}</li>)}
                        </ul>
                      </div>
                    )}
                    {analysisResult.explanation.limitations?.length > 0 && (
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--ea-text-secondary)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.3 }}>Limitations</div>
                        <ul style={{ margin: 0, paddingLeft: 16, fontSize: '0.85rem', color: 'var(--ea-text-primary)', lineHeight: 1.7 }}>
                          {analysisResult.explanation.limitations.map((l, i) => <li key={i}>{l}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                </details>
              )}

              {/* ── Data Table (collapsed) ── */}
              <details style={card}>
                <summary style={{ cursor: 'pointer', fontWeight: 600, color: 'var(--ea-text-primary)', fontSize: '0.9rem' }}>
                  View Raw Data ({analysisResult.rows?.length || analysisResult.chart?.data?.length || 0} rows)
                </summary>
                {analysisResult.chart?.data?.length > 0 && (
                  <div style={{ marginTop: 12, overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                      <thead>
                        <tr>
                          {Object.keys(analysisResult.chart.data[0]).map(k => (
                            <th key={k} style={{ textAlign: 'left', padding: '6px 10px', borderBottom: '2px solid var(--ea-border)', color: 'var(--ea-text-secondary)', fontWeight: 600, textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: 0.3 }}>{k.replace(/_/g, ' ')}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {analysisResult.chart.data.slice(0, 50).map((row, i) => (
                          <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'var(--ea-bg-hover)' }}>
                            {Object.values(row).map((v, j) => (
                              <td key={j} style={{ padding: '5px 10px', borderBottom: '1px solid var(--ea-border)', color: 'var(--ea-text-primary)' }}>
                                {typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(v ?? '')}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </details>

              {/* ── SQL (collapsed) ── */}
              {analysisResult.sql && (
                <details style={card}>
                  <summary style={{ cursor: 'pointer', fontWeight: 600, color: 'var(--ea-text-primary)', fontSize: '0.9rem' }}>
                    Generated SQL
                  </summary>
                  <pre style={{ marginTop: 10, background: 'var(--ea-bg)', padding: 12, borderRadius: 8, overflow: 'auto', fontSize: '0.82rem', color: 'var(--ea-text-primary)' }}>
                    {analysisResult.sql}
                  </pre>
                </details>
              )}
            </div>
          )}

          {/* Analysis History */}
          <div style={card}>
            <h3 style={{ marginTop: 0, display: 'flex', gap: 8, alignItems: 'center', color: 'var(--ea-text-primary)' }}>
              <History size={16} /> Recent Analysis Runs
            </h3>
            {runs.length === 0 ? (
              <p style={{ color: 'var(--ea-text-secondary)' }}>No analysis history yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {runs.slice(0, 10).map((r) => (
                  <div key={r.id} style={{ 
                    padding: 12, 
                    background: 'var(--ea-bg)', 
                    borderRadius: 8, 
                    border: '1px solid var(--ea-border)' 
                  }}>
                    <div style={{ fontWeight: 500, color: 'var(--ea-text-primary)', marginBottom: 4 }}>
                      {r.goal_text?.slice(0, 120)}{r.goal_text?.length > 120 ? '...' : ''}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--ea-text-secondary)', display: 'flex', gap: 12 }}>
                      <span style={pill(r.status === 'completed' ? '#10b981' : '#ef4444')}>{r.status}</span>
                      <span>{new Date(r.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Governance ── */}
      {tab === 'governance' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {loading && <p style={{ color: 'var(--ea-text-secondary)' }}>Computing governance score…</p>}
          {governance && (
            <>
              <div style={{ ...card, display: 'flex', gap: 32, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <GradeRing grade={governance.grade} score={governance.overall} />
                <div style={{ flex: 1, minWidth: 240 }}>
                  <h3 style={{ marginTop: 0, marginBottom: 16, color: 'var(--ea-text-primary)' }}>Governance Health Score</h3>
                  {Object.entries(governance.dimensions || {}).map(([dim, val]) => (
                    <DimensionBar key={dim} label={dim} value={val} />
                  ))}
                </div>
              </div>
              <div style={card}>
                <h3 style={{ marginTop: 0, display: 'flex', gap: 8, alignItems: 'center', color: 'var(--ea-text-primary)' }}>
                  <BookOpen size={16} /> Recommendations
                </h3>
                <ul style={{ paddingLeft: 20, margin: 0 }}>
                  {(governance.recommendations || []).map((rec, i) => {
                    const rendered =
                      typeof rec === 'string' || typeof rec === 'number'
                        ? rec
                        : (rec?.priority && rec?.area && rec?.action)
                          ? `${rec.priority}: ${rec.area} — ${rec.action}`
                          : JSON.stringify(rec);
                    return (
                      <li key={i} style={{ marginBottom: 8, color: 'var(--ea-text-primary)', lineHeight: 1.6 }}>
                        {rendered}
                      </li>
                    );
                  })}
                </ul>
                <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.8rem', marginTop: 12 }}>
                  Computed at {new Date(governance.computed_at).toLocaleString()}
                </p>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Explainable AI ── */}
      {tab === 'xai' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {loading && <p style={{ color: 'var(--ea-text-secondary)' }}>Generating explanations…</p>}
          {explanations && (
            <>
              {explanations.kpi_explanations?.length > 0 && (
                <div style={card}>
                  <h3 style={{ marginTop: 0, color: 'var(--ea-text-primary)' }}>KPI Explanations</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {explanations.kpi_explanations.map((e) => (
                      <div key={e.id} style={{ padding: 14, background: 'var(--ea-primary-bg)', borderRadius: 10, borderLeft: '3px solid #3b82f6' }}>
                        <div style={{ fontWeight: 600, marginBottom: 6, textTransform: 'capitalize', color: 'var(--ea-text-primary)' }}>
                          {e.kpi_name?.replace(/_/g, ' ')}
                        </div>
                        <p style={{ color: 'var(--ea-text-primary)', lineHeight: 1.7, margin: 0 }}>{e.explanation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {explanations.anomaly_explanations?.length > 0 && (
                <div style={card}>
                  <h3 style={{ marginTop: 0, color: 'var(--ea-text-primary)' }}>Anomaly Explanations</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {explanations.anomaly_explanations.map((e) => (
                      <div key={e.id} style={{ padding: 14, background: 'rgba(239,68,68,0.06)', borderRadius: 10, borderLeft: '3px solid #ef4444' }}>
                        <div style={{ fontWeight: 600, marginBottom: 6, textTransform: 'capitalize', color: 'var(--ea-text-primary)' }}>
                          {e.kpi_name?.replace(/_/g, ' ')}
                        </div>
                        <p style={{ color: 'var(--ea-text-primary)', lineHeight: 1.7, margin: 0 }}>{e.explanation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {!explanations.kpi_explanations?.length && !explanations.anomaly_explanations?.length && (
                <div style={{ ...card, textAlign: 'center', padding: 40 }}>
                  <Brain size={40} color="var(--ea-text-secondary)" style={{ marginBottom: 12 }} />
                  <p style={{ color: 'var(--ea-text-secondary)' }}>No data to explain yet. Run a sync first.</p>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Collaboration ── */}
      {tab === 'collaboration' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Save new snapshot */}
          <div style={card}>
            <h3 style={{ marginTop: 0, display: 'flex', gap: 8, alignItems: 'center', color: 'var(--ea-text-primary)' }}>
              <Share2 size={16} /> Save Insight Snapshot
            </h3>
            <p style={{ color: 'var(--ea-text-secondary)', marginBottom: 16 }}>
              Capture and share a key finding with your team.
            </p>
            <div className="form-group">
              <label>Title</label>
              <input
                value={snapshotTitle}
                onChange={(e) => setSnapshotTitle(e.target.value)}
                placeholder="e.g. Revenue spike on May 15 — investigate"
              />
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea
                rows={4}
                value={snapshotContent}
                onChange={(e) => setSnapshotContent(e.target.value)}
                placeholder="Describe the finding, context, and recommended action…"
              />
            </div>
            <button
              className="ea-btn ea-btn-primary"
              onClick={saveSnapshot}
              disabled={savingSnap || !snapshotTitle.trim() || !snapshotContent.trim()}
            >
              <Share2 size={14} /> {savingSnap ? 'Saving…' : 'Save Snapshot'}
            </button>
          </div>

          <div style={card}>
            <h3 style={{ marginTop: 0, display: 'flex', gap: 8, alignItems: 'center', color: 'var(--ea-text-primary)' }}>
              <Users size={16} /> Team Messages
            </h3>
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
              <textarea
                rows={3}
                value={teamMessage}
                onChange={(e) => setTeamMessage(e.target.value)}
                placeholder="Ask for review, leave context, or coordinate follow-up..."
                style={{ flex: 1 }}
              />
              <button className="ea-btn ea-btn-primary" onClick={sendTeamMessage} disabled={savingSnap || !teamMessage.trim()}>
                <Share2 size={14} /> Send
              </button>
            </div>
            <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
              {[...snapshots.filter((s) => s.insight_type === 'message')].reverse().slice(0, 6).map((s) => (
                <div key={s.id} style={{ padding: 12, background: 'var(--ea-bg)', borderRadius: 8, border: '1px solid var(--ea-border)' }}>
                  <p style={{ margin: 0, lineHeight: 1.6, color: 'var(--ea-text-primary)' }}>{s.content}</p>
                  <span style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>{new Date(s.created_at).toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Existing snapshots */}
          <div style={card}>
            <h3 style={{ marginTop: 0, color: 'var(--ea-text-primary)' }}>Team Insight Snapshots ({snapshots.filter((s) => s.insight_type !== 'message').length})</h3>
            {snapshots.filter((s) => s.insight_type !== 'message').length === 0 ? (
              <p style={{ color: 'var(--ea-text-secondary)' }}>No snapshots yet. Save your first insight above.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {[...snapshots.filter((s) => s.insight_type !== 'message')].reverse().map((s) => (
                  <div key={s.id} style={{ padding: 14, background: 'var(--ea-bg)', borderRadius: 10, border: '1px solid var(--ea-border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--ea-text-primary)', marginBottom: 4 }}>{s.title}</div>
                        <p style={{ color: 'var(--ea-text-primary)', lineHeight: 1.6, margin: 0 }}>{s.content}</p>
                        <div style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
                          <span style={pill('#6b7280')}>{s.insight_type}</span>
                          {s.kpi_name && <span style={pill('#3b82f6')}>{s.kpi_name}</span>}
                          <span style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>
                            {new Date(s.created_at).toLocaleString()}
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={() => deleteSnapshot(s.id)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ea-text-secondary)', padding: 4 }}
                        title="Delete snapshot"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}