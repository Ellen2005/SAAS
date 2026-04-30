import React, { useState } from 'react';
import { Search, Play, AlertCircle, Table } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { useLang } from '../lib/i18n';

const NLQPage = () => {
  const { t } = useLang();
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleRun = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const resp = await apiFetch('/api/nlq', {
        method: 'POST',
        body: JSON.stringify({ question }),
      });
      const data = await resp.json();
      setResult(data);
    } catch (err) {
      setResult({ error: err.message, rows: [] });
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleRun();
  };

  return (
    <div style={{ display: 'grid', gap: '24px' }}>
      <header>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Search color="var(--primary-color)" /> {t('nlq_title')}
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Ask questions in plain English or French — the AI generates and runs the query on your connected database.
        </p>
      </header>

      <section className="glass-panel">
        <div className="form-group" style={{ marginBottom: '12px' }}>
          <textarea
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKey}
            placeholder={t('nlq_placeholder')}
            style={{ resize: 'vertical', fontSize: '1rem' }}
          />
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button className="btn btn-primary" onClick={handleRun} disabled={loading || !question.trim()} style={{ display: 'flex', gap: '8px' }}>
            <Play size={16} /> {loading ? t('nlq_running') : t('nlq_btn')}
          </button>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Ctrl+Enter to run</span>
        </div>
      </section>

      {result && (
        <section className="glass-panel">
          {result.error ? (
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', color: 'var(--status-critical)' }}>
              <AlertCircle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <div style={{ fontWeight: 600, marginBottom: '4px' }}>{t('nlq_error')}</div>
                <div style={{ fontSize: '0.9rem' }}>{result.error}</div>
              </div>
            </div>
          ) : (
            <>
              {result.sql && (
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {t('nlq_generated_sql')}
                  </div>
                  <pre style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', fontSize: '0.85rem', overflowX: 'auto', whiteSpace: 'pre-wrap', color: '#a5f3fc' }}>
                    {result.sql}
                  </pre>
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
                <Table size={16} color="var(--primary-color)" />
                <span style={{ fontWeight: 600 }}>{t('nlq_results')}</span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {result.row_count ?? result.rows?.length ?? 0} {t('nlq_rows')}
                </span>
              </div>

              {result.rows?.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)' }}>{t('nlq_no_results')}</p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                        {(result.columns || Object.keys(result.rows[0] || {})).map((col) => (
                          <th key={col} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-secondary)', fontWeight: 600, whiteSpace: 'nowrap' }}>
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.map((row, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                          {(result.columns || Object.keys(row)).map((col) => (
                            <td key={col} style={{ padding: '8px 12px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {row[col] === null ? <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>null</span> : String(row[col])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </section>
      )}
    </div>
  );
};

export default NLQPage;
