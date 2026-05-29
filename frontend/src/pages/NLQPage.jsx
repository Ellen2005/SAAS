import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Database, MessageSquare, Plus, Send, Table, BarChart2 } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { useLang } from '../lib/i18n';
import ChartRenderer from '../components/ChartRenderer';

const CHAT_KEY = 'saas.nlq.conversations.v2';

const makeConversation = () => ({
  id: crypto.randomUUID?.() || String(Date.now()),
  title: 'New conversation',
  messages: [],
  createdAt: new Date().toISOString(),
});

const readConversations = () => {
  try {
    const raw = localStorage.getItem(CHAT_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return Array.isArray(parsed) && parsed.length ? parsed : [makeConversation()];
  } catch {
    return [makeConversation()];
  }
};

const writeConversations = (items) => {
  try {
    localStorage.setItem(CHAT_KEY, JSON.stringify(items));
  } catch {
    // Chat history is a convenience cache; ignore storage failures.
  }
};

const ResultTable = ({ result }) => {
  const rows = result?.rows || [];
  const columns = result?.columns || Object.keys(rows[0] || {});
  if (!rows.length) return <p style={{ color: 'var(--text-secondary)', margin: 0 }}>No rows returned.</p>;

  return (
    <div style={{ overflowX: 'auto', marginTop: 12 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
            {columns.map((col) => (
              <th key={col} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-secondary)', fontWeight: 600, whiteSpace: 'nowrap' }}>
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              {columns.map((col) => (
                <td key={col} style={{ padding: '8px 12px', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {row[col] === null ? <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>null</span> : String(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const AssistantMessage = ({ message }) => {
  const result = message.result || {};
  return (
    <div style={{ display: 'grid', gap: 10 }}>
      {result.error ? (
        <div style={{ display: 'flex', gap: 10, color: 'var(--status-critical)' }}>
          <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 2 }} />
          <div>{result.error}</div>
        </div>
      ) : (
        <>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
            {result.answer || 'I ran the query against your connected database.'}
          </div>
          {result.sql && (
            <details open style={{ background: 'rgba(0,0,0,0.22)', borderRadius: 8, padding: 12 }}>
              <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)', fontSize: '0.82rem', marginBottom: 8 }}>
                Generated SQL
              </summary>
              <pre style={{ margin: 0, overflowX: 'auto', whiteSpace: 'pre-wrap', color: '#a5f3fc', fontSize: '0.84rem' }}>
                {result.sql}
              </pre>
            </details>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            <Table size={15} color="var(--primary-color)" />
            {(result.row_count ?? result.rows?.length ?? 0).toLocaleString()} rows
          </div>
          {result.chart && (
            <div className="glass-panel" style={{ padding: 16, marginTop: 8 }}>
              <ChartRenderer spec={result.chart} height={300} />
            </div>
          )}
          <ResultTable result={result} />
        </>
      )}
    </div>
  );
};

const NLQPage = () => {
  const { t } = useLang();
  const [conversations, setConversations] = useState(readConversations);
  const [activeId, setActiveId] = useState(() => conversations[0]?.id);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [chartType, setChartType] = useState('bar');
  const [customChart, setCustomChart] = useState(null);
  const [chartLoading, setChartLoading] = useState(false);

  const active = useMemo(
    () => conversations.find((item) => item.id === activeId) || conversations[0],
    [activeId, conversations],
  );

  useEffect(() => {
    writeConversations(conversations);
  }, [conversations]);

  const updateActive = (updater) => {
    setConversations((items) => items.map((item) => (
      item.id === active.id ? updater(item) : item
    )));
  };

  const startNewConversation = () => {
    const next = makeConversation();
    setConversations((items) => [next, ...items]);
    setActiveId(next.id);
    setQuestion('');
  };

  const handleRun = async () => {
    const prompt = question.trim();
    if (!prompt || loading || !active) return;

    const userMessage = { id: `${Date.now()}-user`, role: 'user', content: prompt };
    updateActive((item) => ({
      ...item,
      title: item.messages.length ? item.title : prompt.slice(0, 60),
      messages: [...item.messages, userMessage],
    }));
    setQuestion('');
    setLoading(true);

    try {
      const resp = await apiFetch('/api/nlq', {
        method: 'POST',
        body: JSON.stringify({ question: prompt }),
      });
      const data = await resp.json();
      updateActive((item) => ({
        ...item,
        messages: [...item.messages, { id: `${Date.now()}-assistant`, role: 'assistant', result: data }],
      }));
    } catch (err) {
      updateActive((item) => ({
        ...item,
        messages: [...item.messages, { id: `${Date.now()}-assistant`, role: 'assistant', result: { error: err.message, rows: [] } }],
      }));
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleRun();
    }
  };

  const handleCustomChart = async () => {
    const prompt = question.trim();
    if (!prompt || chartLoading) return;
    setChartLoading(true);
    setCustomChart(null);
    try {
      const resp = await apiFetch('/api/charts/custom', {
        method: 'POST',
        body: JSON.stringify({ instruction: prompt, chart_type: chartType }),
      });
      const data = await resp.json();
      setCustomChart(data);
    } catch (err) {
      setCustomChart({ error: err.message });
    } finally {
      setChartLoading(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '260px minmax(0, 1fr)', gap: 20, minHeight: '70vh' }}>
      <aside className="glass-panel" style={{ padding: 14, alignSelf: 'start', position: 'sticky', top: 16 }}>
        <button className="btn btn-primary" onClick={startNewConversation} style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: 8 }}>
          <Plus size={16} /> New conversation
        </button>
        <div style={{ display: 'grid', gap: 6, marginTop: 14 }}>
          {conversations.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveId(item.id)}
              style={{
                textAlign: 'left',
                padding: '10px 12px',
                borderRadius: 8,
                border: '1px solid var(--border-color)',
                background: item.id === active?.id ? 'rgba(59,130,246,0.18)' : 'rgba(255,255,255,0.03)',
                color: 'var(--text-primary)',
                cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 600, fontSize: '0.86rem' }}>
                <MessageSquare size={14} /> {item.title}
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginTop: 4 }}>
                {item.messages.length} messages
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main style={{ display: 'grid', gap: 18, alignContent: 'start' }}>
        <header>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
            <Database color="var(--primary-color)" /> {t('nlq_title')}
          </h1>
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
            Chat with your connected database. The assistant shows the SQL it ran, the result rows, and guidance when you need help exploring.
          </p>
        </header>

        <section className="glass-panel" style={{ display: 'grid', gap: 14, minHeight: 360 }}>
          {active?.messages.length ? (
            active.messages.map((message) => (
              <div
                key={message.id}
                style={{
                  justifySelf: message.role === 'user' ? 'end' : 'start',
                  maxWidth: message.role === 'user' ? '75%' : '100%',
                  width: message.role === 'assistant' ? '100%' : 'auto',
                }}
              >
                <div
                  style={{
                    background: message.role === 'user' ? 'var(--primary-color)' : 'rgba(255,255,255,0.04)',
                    border: message.role === 'user' ? 'none' : '1px solid var(--border-color)',
                    color: message.role === 'user' ? 'white' : 'var(--text-primary)',
                    borderRadius: 10,
                    padding: '12px 14px',
                  }}
                >
                  {message.role === 'user' ? message.content : <AssistantMessage message={message} />}
                </div>
              </div>
            ))
          ) : (
            <div style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              Start by asking: <b>list all tables</b>, <b>how many tables do I have?</b>, <b>describe rnc_database</b>, or <b>show rows from rnc_database</b>.
            </div>
          )}
          {loading && <div style={{ color: 'var(--text-secondary)' }}>Thinking and querying...</div>}
        </section>

        <section className="glass-panel" style={{ padding: 14 }}>
          <textarea
            rows={4}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKey}
            placeholder={t('nlq_placeholder')}
            style={{ resize: 'vertical', fontSize: '1rem', width: '100%', minHeight: 120 }}
          />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', marginTop: 12 }}>
            <button className="btn btn-primary" onClick={handleRun} disabled={loading || !question.trim()} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <Send size={16} /> {loading ? t('nlq_running') : 'Send Query'}
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 260 }}>
              <label htmlFor="chart-type" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
                Chart type:
              </label>
              <select
                id="chart-type"
                value={chartType}
                onChange={(e) => setChartType(e.target.value)}
                style={{ minWidth: 160, padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border-color)', background: 'var(--surface-color)', color: 'var(--text-primary)' }}
              >
                <option value="none">No chart</option>
                <option value="bar">Bar chart</option>
                <option value="line">Line chart</option>
                <option value="pie">Pie chart</option>
                <option value="area">Area chart</option>
              </select>
            </div>
            <button className="btn btn-outline" onClick={handleCustomChart} disabled={chartLoading || !question.trim() || chartType === 'none'} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <BarChart2 size={16} /> {chartLoading ? 'Building chart...' : 'Build chart'}
            </button>
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 10 }}>
            Enter sends the query, Shift+Enter adds a new line. Choose a chart type only if you want a chart.
          </div>
          {customChart?.error && <p style={{ color: 'var(--status-critical)', fontSize: '0.85rem', marginTop: 10 }}>{customChart.error}</p>}
          {customChart?.chart && <ChartRenderer spec={customChart.chart} height={320} />}
        </section>
      </main>
    </div>
  );
};

export default NLQPage;
