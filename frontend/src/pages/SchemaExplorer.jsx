import React, { useEffect, useMemo, useState } from 'react';
import {
  Database, RefreshCw, Sparkles, Play, ChevronRight, ChevronDown,
  Table as TableIcon, Layers, Hash, Calendar, DollarSign, Link2, AlertCircle,
} from 'lucide-react';
import { apiJson } from '../lib/api';
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, Legend,
} from 'recharts';

const card = {
  background: 'var(--card-bg, rgba(255,255,255,0.04))',
  border: '1px solid var(--border-color, rgba(255,255,255,0.08))',
  borderRadius: 12,
  padding: 20,
};

const pill = (color = 'var(--primary-color, #4f46e5)') => ({
  fontSize: '0.7rem',
  padding: '2px 8px',
  borderRadius: 999,
  background: `${color}22`,
  color,
  fontWeight: 600,
  letterSpacing: 0.3,
  textTransform: 'uppercase',
});

function fmtNum(n) {
  if (n == null) return '—';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

export default function SchemaExplorer() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [schema, setSchema] = useState(null);
  const [analyses, setAnalyses] = useState([]);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [runningId, setRunningId] = useState(null);
  const [expandedTable, setExpandedTable] = useState(null);
  const [filter, setFilter] = useState('');
  const [autoMapResult, setAutoMapResult] = useState(null);
  const [autoMapping, setAutoMapping] = useState(false);
  const [savingMappings, setSavingMappings] = useState(false);

  const loadSchema = async (refresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiJson('/api/introspect/schema', {
        method: 'POST',
        body: JSON.stringify({ refresh, sample_rows: 5, max_tables: 200 }),
      });
      setSchema(data);
      const a = await apiJson('/api/introspect/analyses', { method: 'POST' });
      setAnalyses(a.analyses || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadSchema(false); }, []); // eslint-disable-line

  const runAnalysis = async (a) => {
    setRunningId(a.id);
    setAnalysisResult(null);
    try {
      const result = await apiJson('/api/introspect/run-analysis', {
        method: 'POST',
        body: JSON.stringify(a),
      });
      setAnalysisResult({ spec: a, result });
    } catch (e) {
      setAnalysisResult({ spec: a, result: { error: e.message } });
    } finally {
      setRunningId(null);
    }
  };

  const runAutoMap = async () => {
    setAutoMapping(true);
    setAutoMapResult(null);
    try {
      const data = await apiJson('/api/introspect/auto-map', {
        method: 'POST', body: JSON.stringify({}),
      });
      setAutoMapResult(data);
    } catch (e) {
      setAutoMapResult({ error: e.message });
    } finally {
      setAutoMapping(false);
    }
  };

  const saveMappings = async () => {
    if (!autoMapResult?.suggestions?.length) return;
    setSavingMappings(true);
    try {
      const out = await apiJson('/api/introspect/apply-mappings', {
        method: 'POST',
        body: JSON.stringify({ mappings: autoMapResult.suggestions }),
      });
      alert(`Saved ${out.saved} field mapping(s)${out.errors?.length ? ` with ${out.errors.length} error(s)` : ''}.`);
    } catch (e) {
      alert(e.message);
    } finally {
      setSavingMappings(false);
    }
  };

  const filteredTables = useMemo(() => {
    const tables = schema?.tables || [];
    if (!filter.trim()) return tables;
    const q = filter.toLowerCase();
    return tables.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        (t.qualified_name || '').toLowerCase().includes(q) ||
        (t.classifications || []).some((c) => c.includes(q))
    );
  }, [schema, filter]);

  const tablesByDomain = useMemo(() => {
    const groups = {};
    (filteredTables || []).forEach((t) => {
      const labels = (t.classifications && t.classifications.length) ? t.classifications : ['other'];
      labels.forEach((label) => {
        groups[label] = groups[label] || [];
        groups[label].push(t);
      });
    });
    return groups;
  }, [filteredTables]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ margin: 0, display: 'flex', gap: 10, alignItems: 'center' }}>
            <Database size={28} /> Schema Explorer
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: 4 }}>
            Auto-discovered tables, relationships and ready-to-run analyses from your connected database.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-outline" onClick={() => loadSchema(true)} disabled={loading}>
            <RefreshCw size={14} style={loading ? { animation: 'spin 1s linear infinite' } : null} /> Re-discover
          </button>
          <button className="btn" onClick={runAutoMap} disabled={autoMapping || !schema}>
            <Sparkles size={14} /> {autoMapping ? 'Mapping…' : 'Auto-map fields'}
          </button>
        </div>
      </header>

      {error && (
        <div style={{ ...card, borderColor: '#ef4444', color: '#fca5a5', display: 'flex', gap: 8, alignItems: 'center' }}>
          <AlertCircle size={16} /> {error}
          <span style={{ marginLeft: 'auto', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Configure your database in Settings before running discovery.
          </span>
        </div>
      )}

      {schema && (
        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
          <Stat icon={<Layers size={16} />} label="Tables" value={schema.table_count} />
          <Stat icon={<Database size={16} />} label="Dialect" value={schema.dialect} />
          <Stat icon={<Hash size={16} />} label="Schemas" value={(schema.schemas || []).length} />
          <Stat icon={<Sparkles size={16} />} label="Analyses ready" value={analyses.length} />
        </section>
      )}

      {autoMapResult && (
        <section style={card}>
          <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={18} /> Suggested field mappings
          </h3>
          {autoMapResult.error && <div style={{ color: '#fca5a5' }}>{autoMapResult.error}</div>}
          {autoMapResult.warning && <div style={{ color: '#fbbf24' }}>{autoMapResult.warning}</div>}
          {autoMapResult.suggestions?.length ? (
            <>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                <thead>
                  <tr style={{ textAlign: 'left', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: 8 }}>Semantic field</th>
                    <th style={{ padding: 8 }}>Suggested column</th>
                    <th style={{ padding: 8 }}>Confidence</th>
                    <th style={{ padding: 8 }}>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {autoMapResult.suggestions.map((s, i) => (
                    <tr key={i} style={{ borderTop: '1px solid var(--border-color)' }}>
                      <td style={{ padding: 8, fontWeight: 600 }}>{s.semantic_field}</td>
                      <td style={{ padding: 8, fontFamily: 'monospace' }}>{s.table}.{s.column}</td>
                      <td style={{ padding: 8 }}>
                        <span style={pill(s.confidence > 0.7 ? '#10b981' : '#f59e0b')}>
                          {(s.confidence * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td style={{ padding: 8, color: 'var(--text-secondary)' }}>{s.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
                <button className="btn" onClick={saveMappings} disabled={savingMappings}>
                  {savingMappings ? 'Saving…' : 'Apply all mappings'}
                </button>
              </div>
            </>
          ) : (
            <p style={{ color: 'var(--text-secondary)' }}>No mappings could be suggested. Try expanding your semantic template.</p>
          )}
        </section>
      )}

      {/* ── Suggested analyses ── */}
      {schema && analyses.length > 0 && (
        <section style={card}>
          <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={18} /> Ready-to-run analyses ({analyses.length})
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
            {analyses.map((a) => (
              <div key={a.id} style={{ background: 'rgba(255,255,255,0.02)', padding: 12, borderRadius: 8, border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6 }}>
                  <strong style={{ fontSize: '0.95rem' }}>{a.title}</strong>
                  <span style={pill()}>{a.category}</span>
                </div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '6px 0 10px' }}>
                  {a.description}
                </p>
                <button
                  className="btn btn-outline"
                  onClick={() => runAnalysis(a)}
                  disabled={runningId === a.id}
                  style={{ fontSize: '0.85rem' }}
                >
                  <Play size={12} /> {runningId === a.id ? 'Running…' : 'Run'}
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {analysisResult && (
        <section style={card}>
          <h3 style={{ marginTop: 0 }}>{analysisResult.spec?.title || 'Result'}</h3>
          <AnalysisRenderer result={analysisResult.result} />
        </section>
      )}

      {/* ── Discovered tables ── */}
      {schema && (
        <section style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 12 }}>
            <h3 style={{ margin: 0 }}>Discovered tables</h3>
            <input
              placeholder="Filter tables…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              style={{
                padding: '6px 12px', borderRadius: 8, border: '1px solid var(--border-color)',
                background: 'rgba(0,0,0,0.2)', color: 'inherit', minWidth: 220,
              }}
            />
          </div>

          {Object.entries(tablesByDomain).map(([domain, list]) => (
            <div key={domain} style={{ marginBottom: 18 }}>
              <h4 style={{ margin: '8px 0', textTransform: 'capitalize', color: 'var(--text-secondary)' }}>
                {domain} <span style={{ fontSize: '0.7rem' }}>({list.length})</span>
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 6 }}>
                {list.map((t) => (
                  <TableCard
                    key={t.qualified_name}
                    table={t}
                    expanded={expandedTable === t.qualified_name}
                    onToggle={() => setExpandedTable(expandedTable === t.qualified_name ? null : t.qualified_name)}
                  />
                ))}
              </div>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}

function Stat({ icon, label, value }) {
  return (
    <div style={{ ...card, display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
        {icon} {label}
      </div>
      <div style={{ fontSize: '1.6rem', fontWeight: 600 }}>{value ?? '—'}</div>
    </div>
  );
}

function TableCard({ table, expanded, onToggle }) {
  return (
    <div style={{ border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
      <div
        onClick={onToggle}
        style={{
          padding: 10, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
          background: 'rgba(255,255,255,0.03)',
        }}
      >
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <TableIcon size={14} />
        <strong style={{ fontFamily: 'monospace' }}>{table.qualified_name}</strong>
        {table.is_view && <span style={pill('#06b6d4')}>view</span>}
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          {(table.classifications || []).map((c) => (
            <span key={c} style={pill('#a78bfa')}>{c}</span>
          ))}
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
            {fmtNum(table.row_count)} rows · {table.columns?.length || 0} cols
          </span>
        </span>
      </div>
      {expanded && (
        <div style={{ padding: 12, background: 'rgba(0,0,0,0.18)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ color: 'var(--text-secondary)', textAlign: 'left' }}>
                <th style={{ padding: 6 }}>Column</th>
                <th style={{ padding: 6 }}>Type</th>
                <th style={{ padding: 6 }}>Tags</th>
              </tr>
            </thead>
            <tbody>
              {(table.columns || []).map((c) => (
                <tr key={c.name} style={{ borderTop: '1px solid var(--border-color)' }}>
                  <td style={{ padding: 6, fontFamily: 'monospace' }}>
                    {c.name}{table.primary_keys?.includes(c.name) && (
                      <span style={{ ...pill('#10b981'), marginLeft: 6 }}>PK</span>
                    )}
                  </td>
                  <td style={{ padding: 6, color: 'var(--text-secondary)' }}>{c.type}</td>
                  <td style={{ padding: 6, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {table.amount_columns?.includes(c.name) && (
                      <span style={pill('#fbbf24')}><DollarSign size={10} /> amount</span>
                    )}
                    {table.date_columns?.includes(c.name) && (
                      <span style={pill('#06b6d4')}><Calendar size={10} /> date</span>
                    )}
                    {table.id_columns?.includes(c.name) && (
                      <span style={pill('#a78bfa')}>id</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {table.foreign_keys?.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h5 style={{ margin: '4px 0' }}><Link2 size={12} /> Foreign keys</h5>
              <ul style={{ margin: 0, paddingLeft: 16, color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                {table.foreign_keys.map((fk, i) => (
                  <li key={i}>
                    <code>{(fk.columns || []).join(', ')}</code> →
                    <code> {fk.ref_schema ? `${fk.ref_schema}.` : ''}{fk.ref_table}({(fk.ref_columns || []).join(', ')})</code>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {table.sample_rows?.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h5 style={{ margin: '4px 0' }}>Sample rows</h5>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ borderCollapse: 'collapse', fontSize: '0.78rem', minWidth: '100%' }}>
                  <thead>
                    <tr>
                      {Object.keys(table.sample_rows[0] || {}).map((k) => (
                        <th key={k} style={{ padding: 4, textAlign: 'left', color: 'var(--text-secondary)' }}>{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {table.sample_rows.map((r, i) => (
                      <tr key={i} style={{ borderTop: '1px solid var(--border-color)' }}>
                        {Object.keys(table.sample_rows[0] || {}).map((k) => (
                          <td key={k} style={{ padding: 4, fontFamily: 'monospace', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {String(r[k] ?? '')}
                          </td>
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
    </div>
  );
}

function AnalysisRenderer({ result }) {
  if (!result) return <p>—</p>;
  if (result.error) return <p style={{ color: '#fca5a5' }}>{result.error}</p>;
  if (result.warning) return <p style={{ color: '#fbbf24' }}>{result.warning}</p>;

  const k = result.kind;
  if (k === 'time_series_sum' || k === 'count_over_time') {
    return (
      <>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={result.rows || []}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="bucket" stroke="var(--text-secondary)" />
            <YAxis stroke="var(--text-secondary)" />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="total" stroke="var(--primary-color, #4f46e5)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
        <pre style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--text-secondary)', overflowX: 'auto' }}>{result.sql}</pre>
      </>
    );
  }
  if (k === 'liability_forecast') {
    const merged = [
      ...(result.history || []).map((h) => ({ bucket: h.bucket, history: h.total })),
      ...(result.forecast || []).map((f) => ({ bucket: f.bucket, forecast: f.total })),
    ];
    return (
      <>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={merged}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="bucket" stroke="var(--text-secondary)" />
            <YAxis stroke="var(--text-secondary)" />
            <Tooltip /><Legend />
            <Line type="monotone" dataKey="history" stroke="#10b981" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="forecast" stroke="#f59e0b" strokeDasharray="5 5" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Year-over-year growth: <strong>{((result.growth_yoy || 0) * 100).toFixed(1)}%</strong>
        </p>
      </>
    );
  }
  if (k === 'demographic') {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
        {(result.groups || []).map((g) => (
          <div key={g.column}>
            <h4 style={{ margin: '0 0 6px' }}>{g.column}</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={g.rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="bucket" stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip />
                <Bar dataKey="total" fill="var(--primary-color, #4f46e5)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>
    );
  }
  if (k === 'anomaly_zscore') {
    return (
      <>
        <p style={{ color: 'var(--text-secondary)' }}>
          Mean: <strong>{result.stats?.mean?.toFixed(2)}</strong> · Std: <strong>{result.stats?.stddev?.toFixed(2)}</strong> ·
          Outliers: <strong>{result.stats?.outlier_count}</strong>
        </p>
        <RowsTable rows={result.rows} />
      </>
    );
  }
  if (k === 'overview') return <RowsTable rows={result.rows} cols={result.columns} />;
  if (k === 'missing_recent') return <RowsTable rows={result.rows} />;
  return <pre style={{ fontSize: '0.8rem', overflowX: 'auto' }}>{JSON.stringify(result, null, 2)}</pre>;
}

function RowsTable({ rows, cols }) {
  if (!rows || !rows.length) return <p style={{ color: 'var(--text-secondary)' }}>No rows.</p>;
  const columns = cols || Object.keys(rows[0]);
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', fontSize: '0.85rem', minWidth: '100%' }}>
        <thead>
          <tr style={{ textAlign: 'left', color: 'var(--text-secondary)' }}>
            {columns.map((c) => (<th key={c} style={{ padding: 6 }}>{c}</th>))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} style={{ borderTop: '1px solid var(--border-color)' }}>
              {columns.map((c) => (
                <td key={c} style={{ padding: 6, fontFamily: 'monospace', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {String(r[c] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
