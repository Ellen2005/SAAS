import React, { useEffect, useRef, useState } from 'react';
import { Bot, X, Send, Minimize2, Maximize2, RefreshCw } from 'lucide-react';
import { apiFetch } from '../lib/api';

const STORAGE_KEY = 'saas.assistant.history.v1';

const loadHistory = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

const saveHistory = (msgs) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs.slice(-30)));
  } catch {}
};

const SUGGESTIONS = [
  'How do I connect my database?',
  'What does the Dashboard show?',
  'How do I generate a report?',
  'What is Schema Explorer?',
  'How do I set up KPI mappings?',
];

export default function AssistantBot() {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [messages, setMessages] = useState(loadHistory);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [includeData, setIncludeData] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, open]);

  useEffect(() => {
    saveHistory(messages);
  }, [messages]);

  const send = async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput('');

    const userMsg = { role: 'user', content: msg };
    const next = [...messages, userMsg];
    setMessages(next);
    setLoading(true);

    try {
      const resp = await apiFetch('/api/assistant/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: msg,
          history: next.slice(-6).map((m) => ({ role: m.role, content: m.content })),
          include_data_context: includeData,
        }),
      });
      const data = await resp.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }]);
    } catch {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: 'Connection error — please check the backend is running.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const width = expanded ? 480 : 360;
  const height = expanded ? 600 : 440;

  return (
    <>
      {/* Floating trigger button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          title="AI Assistant"
          style={{
            position: 'fixed', bottom: 28, right: 28, zIndex: 9999,
            width: 52, height: 52, borderRadius: '50%',
            background: 'var(--primary-color)',
            border: 'none', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 20px rgba(79,70,229,0.5)',
            transition: 'transform 0.2s',
          }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.1)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
        >
          <Bot size={24} color="white" />
        </button>
      )}

      {/* Chat window */}
      {open && (
        <div style={{
          position: 'fixed', bottom: 28, right: 28, zIndex: 9999,
          width, height,
          background: 'var(--surface-color)',
          border: '1px solid var(--border-color)',
          borderRadius: 16,
          display: 'flex', flexDirection: 'column',
          boxShadow: '0 8px 40px rgba(0,0,0,0.5)',
          overflow: 'hidden',
          transition: 'width 0.2s, height 0.2s',
        }}>
          {/* Header */}
          <div style={{
            padding: '12px 16px',
            background: 'var(--primary-color)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Bot size={18} color="white" />
              <span style={{ color: 'white', fontWeight: 600, fontSize: '0.9rem' }}>SAAS Assistant</span>
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                onClick={() => { setMessages([]); localStorage.removeItem(STORAGE_KEY); }}
                title="Clear chat"
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(255,255,255,0.7)', padding: 4 }}
              >
                <RefreshCw size={14} />
              </button>
              <button
                onClick={() => setExpanded((v) => !v)}
                title={expanded ? 'Shrink' : 'Expand'}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(255,255,255,0.7)', padding: 4 }}
              >
                {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
              </button>
              <button
                onClick={() => setOpen(false)}
                title="Close"
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(255,255,255,0.7)', padding: 4 }}
              >
                <X size={14} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {messages.length === 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>
                  Hi! I can help you use this app, explain features, or answer questions about your data.
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4 }}>
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      style={{
                        textAlign: 'left', padding: '7px 10px', borderRadius: 8,
                        border: '1px solid var(--border-color)',
                        background: 'rgba(255,255,255,0.03)',
                        color: 'var(--text-secondary)', fontSize: '0.8rem',
                        cursor: 'pointer',
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div
                key={i}
                style={{
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '85%',
                }}
              >
                <div style={{
                  padding: '9px 12px',
                  borderRadius: m.role === 'user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
                  background: m.role === 'user' ? 'var(--primary-color)' : 'rgba(255,255,255,0.06)',
                  border: m.role === 'user' ? 'none' : '1px solid var(--border-color)',
                  color: m.role === 'user' ? 'white' : 'var(--text-primary)',
                  fontSize: '0.85rem',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                }}>
                  {m.content}
                </div>
              </div>
            ))}

            {loading && (
              <div style={{ alignSelf: 'flex-start' }}>
                <div style={{
                  padding: '9px 14px', borderRadius: '12px 12px 12px 4px',
                  background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border-color)',
                  color: 'var(--text-secondary)', fontSize: '0.82rem',
                }}>
                  Thinking…
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Data context toggle */}
          <div style={{ padding: '4px 14px', borderTop: '1px solid var(--border-color)', flexShrink: 0 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={includeData}
                onChange={(e) => setIncludeData(e.target.checked)}
                style={{ accentColor: 'var(--primary-color)' }}
              />
              Include my current data context
            </label>
          </div>

          {/* Input */}
          <div style={{ padding: '10px 12px', borderTop: '1px solid var(--border-color)', display: 'flex', gap: 8, flexShrink: 0 }}>
            <textarea
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask anything about the app…"
              style={{
                flex: 1, resize: 'none', fontSize: '0.85rem',
                padding: '8px 10px', borderRadius: 8,
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)',
              }}
            />
            <button
              onClick={() => send()}
              disabled={loading || !input.trim()}
              style={{
                background: 'var(--primary-color)', border: 'none',
                borderRadius: 8, padding: '0 12px', cursor: 'pointer',
                opacity: loading || !input.trim() ? 0.5 : 1,
              }}
            >
              <Send size={16} color="white" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
