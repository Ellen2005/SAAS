import React, { useCallback, useEffect, useState } from 'react';
import {
  Brain, TrendingUp, Shield, Users, Zap, RefreshCw,
  AlertTriangle, CheckCircle, Info, ChevronDown, ChevronRight,
  BookOpen, Share2, Trash2, BarChart2, Play, Target, History,
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
  const { lang } = useLang();
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
    { id: 'insights', label: 'Augmented Insights', icon: <Zap size={15} /> },
    { id: 'analysis', label: 'Goal Analysis', icon: <BarChart2 size={15} /> },
    { id: 'governance', label: 'Governance', icon: <Shield size={15} /> },
    { id: 'xai', label: 'Explainable AI', icon: <Brain size={15} /> },
    { id: 'collaboration', label: 'Collaboration', icon: <Users size={15} /> },
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
              <h3>No anomalous patterns detected</h3>
              <p style={{ color: 'var(--ea-text-secondary)' }}>
                {insights.message || 'All metrics are within normal ranges. Run a sync to refresh.'}
              </p>
            </div>
          )}
          {(insights?.insights || []).map((ins, i) => {
            const color = SEVERITY_COLOR[ins.severity] || '#3b82f6';
            const isOpen = expandedInsight === i;
            return (
              <div key={i} style={{ ...card, borderLeft: `4px solid ${color}` }}>
                <div
                  onClick={() => setExpandedInsight(isOpen ? null : i)}
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                >
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span style={{ color }}>{INSIGHT_ICON[ins.type] || <Info size={16} />}</span>
                    <div>
                      <div style={{ fontWeight: 600, color: 'var(--ea-text-primary)' }}>{ins.title}</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--ea-text-secondary)', marginTop: 2 }}>
                        <span style={pill(color)}>{ins.type.replace(/_/g, ' ')}</span>
                        {' '}<span style={pill('#6b7280')}>{ins.kpi}</span>
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, color, fontSize: '1.1rem' }}>
                      {typeof ins.value === 'number' ? ins.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : ''}
                    </span>
                    {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </div>
                </div>
                {isOpen && (
                  <div style={{ marginTop: 12, padding: '12px 0 0', borderTop: '1px solid var(--ea-border)' }}>
                    <p style={{ color: 'var(--ea-text-primary)', lineHeight: 1.7 }}>{typeof ins.explanation === 'string' ? ins.explanation : (ins.explanation?.reason || ins.explanation?.text || JSON.stringify(ins.explanation))}</p>
                    {ins.xai_explanation && ins.xai_explanation !== ins.explanation && (
                      <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.9rem', marginTop: 8, fontStyle: 'italic' }}>
                        {ins.xai_explanation}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {insights && (
            <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.8rem', textAlign: 'right' }}>
              Generated at {new Date(insights.generated_at).toLocaleString()}
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
              className="btn btn-primary" 
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
            <div style={card}>
              <h3 style={{ marginTop: 0, color: 'var(--ea-text-primary)' }}>Analysis Result</h3>
              <p style={{ marginBottom: 16, color: 'var(--ea-text-primary)' }}>{analysisResult.summary}</p>
              {analysisResult.chart && (
                <div style={{ marginTop: 16 }}>
                  <ChartRenderer
                    spec={{
                      type: analysisResult.chart.type || 'bar',
                      data: analysisResult.chart.data,
                      title: analysisResult.chart.title,
                      xKey: analysisResult.chart.xKey || 'name',
                      yKey: analysisResult.chart.yKey,
                    }}
                  />
                </div>
              )}
              {analysisResult.sql && (
                <details style={{ marginTop: 16 }}>
                  <summary style={{ cursor: 'pointer', fontWeight: 600, marginBottom: 8, color: 'var(--ea-text-primary)' }}>Generated SQL</summary>
                  <pre style={{ 
                    background: 'var(--ea-bg)', 
                    padding: 12, 
                    borderRadius: 8, 
                    overflow: 'auto',
                    fontSize: '0.85rem',
                    color: 'var(--ea-text-primary)',
                  }}>
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
              className="btn btn-primary"
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
              <button className="btn btn-primary" onClick={sendTeamMessage} disabled={savingSnap || !teamMessage.trim()}>
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