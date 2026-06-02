import React, { useCallback, useEffect, useState } from 'react';
import { Play, History, Target } from 'lucide-react';
import { useLang } from '../lib/i18n';
import { apiJson } from '../lib/api';
import ChartRenderer from '../components/ChartRenderer';

export default function AnalysisPage() {
  const { t, lang } = useLang();
  const [goal, setGoal] = useState('');
  const [formula, setFormula] = useState('');
  const [presets, setPresets] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const loadMeta = useCallback(async () => {
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
    loadMeta();
  }, [loadMeta]);

  const runAnalysis = async (presetSlug = null) => {
    setLoading(true);
    setError('');
    setResult(null);
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
      setResult(res);
      loadMeta();
    } catch (e) {
      setError(e.message || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <header style={{ marginBottom: '28px' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: 0 }}>
          <Target size={28} /> {t('analysis_title')}
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>{t('analysis_subtitle')}</p>
      </header>

      <div className="card" style={{ marginBottom: '24px', padding: '24px' }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: '8px' }}>{t('analysis_goal_label')}</label>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder={t('analysis_goal_placeholder')}
          rows={3}
          style={{ width: '100%', marginBottom: '16px', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-color)', color: 'var(--text-primary)' }}
        />
        <label style={{ display: 'block', fontWeight: 600, marginBottom: '8px' }}>{t('analysis_formula_label')}</label>
        <input
          type="text"
          value={formula}
          onChange={(e) => setFormula(e.target.value)}
          placeholder={t('analysis_formula_placeholder')}
          style={{ width: '100%', marginBottom: '16px', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-color)', color: 'var(--text-primary)' }}
        />
        <button type="button" className="btn btn-primary" disabled={loading} onClick={() => runAnalysis()}>
          <Play size={16} style={{ marginRight: '8px' }} />
          {loading ? t('analysis_running') : t('analysis_run')}
        </button>
        {error && <p style={{ color: '#ef4444', marginTop: '12px' }}>{error}</p>}
      </div>

      <h2 style={{ fontSize: '1.1rem', marginBottom: '12px' }}>{t('analysis_presets')}</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '12px', marginBottom: '28px' }}>
        {presets.map((p) => (
          <button
            key={p.slug || p.id}
            type="button"
            className="card"
            style={{ textAlign: 'left', padding: '16px', cursor: 'pointer' }}
            onClick={() => {
              setGoal(p.default_goal_text || '');
              runAnalysis(p.slug);
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: '6px' }}>{p.title}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{p.category}</div>
          </button>
        ))}
      </div>

      {result && (
        <div className="card" style={{ marginBottom: '24px', padding: '24px' }}>
          <h2>{t('analysis_result')}</h2>
          <p>{result.summary}</p>
          {result.metrics?.explanation && (
            <div style={{ marginTop: '14px', padding: '14px', borderRadius: '10px', border: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.03)' }}>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>What this means</div>
              <div style={{ color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {result.metrics.explanation.what_this_means}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginTop: 12 }}>
                <div>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Assumptions</div>
                  <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--text-secondary)' }}>
                    {(result.metrics.explanation.assumptions || []).map((x) => <li key={x}>{x}</li>)}
                  </ul>
                </div>
                <div>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Limitations</div>
                  <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--text-secondary)' }}>
                    {(result.metrics.explanation.limitations || []).map((x) => <li key={x}>{x}</li>)}
                  </ul>
                </div>
                <div>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Recommended actions</div>
                  <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--text-secondary)' }}>
                    {(result.metrics.explanation.recommended_actions || []).map((x) => <li key={x}>{x}</li>)}
                  </ul>
                </div>
              </div>
            </div>
          )}
          {result.chart && (
            <div style={{ marginTop: '16px' }}>
              <ChartRenderer
                spec={{
                  type: result.chart.type || 'bar',
                  data: result.chart.data,
                  title: result.chart.title,
                  xKey: result.chart.xKey || 'name',
                  yKey: result.chart.yKey,
                }}
              />
            </div>
          )}
          {result.sql && (
            <details style={{ marginTop: '14px' }}>
              <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)' }}>Assumptions & SQL used</summary>
              <pre style={{ marginTop: 10, whiteSpace: 'pre-wrap', background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-color)', padding: 12, borderRadius: 10, overflowX: 'auto' }}>
                {result.sql}
              </pre>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Rows: {result.metrics?.row_count ?? '—'} · Columns: {(result.metrics?.columns || []).join(', ')}
              </div>
            </details>
          )}
          {result.metrics?.details?.top_delinquent_employers?.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h3 style={{ fontSize: '1rem', marginBottom: 10 }}>Top delinquent employers</h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                      {Object.keys(result.metrics.details.top_delinquent_employers[0]).map((k) => (
                        <th key={k} style={{ textAlign: 'left', padding: '8px', color: 'var(--text-secondary)' }}>{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.metrics.details.top_delinquent_employers.map((r, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                        {Object.keys(result.metrics.details.top_delinquent_employers[0]).map((k) => (
                          <td key={k} style={{ padding: '8px' }}>{String(r[k] ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      <h2 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <History size={18} /> {t('analysis_history')}
      </h2>
      {runs.length === 0 ? (
        <p style={{ color: 'var(--text-secondary)' }}>{t('analysis_no_history')}</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {runs.map((r) => (
            <li key={r.id} className="card" style={{ padding: '12px 16px', marginBottom: '8px' }}>
              <div style={{ fontWeight: 500 }}>{r.goal_text?.slice(0, 120)}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {r.status} — {r.created_at?.slice(0, 19)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
