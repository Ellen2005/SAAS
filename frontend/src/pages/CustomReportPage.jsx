import React, { useState } from 'react';
import { FileText, Sparkles, Save, Check, Plus, Trash2, ChevronDown, ChevronUp, LayoutTemplate } from 'lucide-react';
import { apiFetch, apiJson } from '../lib/api';
import { useAuth } from '../lib/authContext';

const CONTENT_TYPES = [
  { value: 'narrative', label: 'Narrative paragraphs' },
  { value: 'table_and_narrative', label: 'Table + interpretation' },
  { value: 'bullet_points', label: 'Bullet points' },
];

const CNPS_PRESET = [
  { title: 'Executive Summary', description: 'Concise summary of purpose, key findings, conclusions and recommendations. Self-contained.', content_type: 'narrative' },
  { title: 'Introduction and Background', description: 'CNPS mandate, relevant programs, problem statement, scope and objectives.', content_type: 'narrative' },
  { title: 'Data Sources', description: 'All data sources used: database name, time frame, variables extracted, preprocessing applied.', content_type: 'narrative' },
  { title: 'Methodology', description: 'Statistical methods, tools, key assumptions, data cleaning steps.', content_type: 'narrative' },
  { title: 'Data Quality and Cleaning', description: 'Completeness, accuracy and consistency checks. Validation pass rate summary.', content_type: 'narrative' },
  { title: 'Analysis and Results', description: 'Core KPI findings with tables. Each result explained in plain language with numbered figures.', content_type: 'table_and_narrative' },
  { title: 'Interpretation and Key Findings', description: 'What the numbers mean in context of CNPS goals. Trends, comparisons, implications.', content_type: 'narrative' },
  { title: 'Conclusions and Recommendations', description: 'Numbered conclusions answering objectives. Concrete recommendations tied to evidence.', content_type: 'narrative' },
  { title: 'Limitations', description: 'Data gaps, assumptions, unanswered questions.', content_type: 'narrative' },
];

const emptySection = () => ({ title: '', description: '', content_type: 'narrative', _id: Math.random() });

const CustomReportPage = () => {
  const { isAdmin } = useAuth();

  const [instruction, setInstruction] = useState('');
  const [scope, setScope] = useState('my_department');
  const [format, setFormat] = useState('narrative');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [useTemplate, setUseTemplate] = useState(false);
  const [sections, setSections] = useState([emptySection()]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const loadPreset = () => setSections(CNPS_PRESET.map(s => ({ ...s, _id: Math.random() })));

  const addSection = () => setSections(prev => [...prev, emptySection()]);

  const removeSection = (id) => setSections(prev => prev.filter(s => s._id !== id));

  const updateSection = (id, field, value) =>
    setSections(prev => prev.map(s => s._id === id ? { ...s, [field]: value } : s));

  const moveSection = (id, dir) => {
    setSections(prev => {
      const idx = prev.findIndex(s => s._id === id);
      const next = idx + dir;
      if (next < 0 || next >= prev.length) return prev;
      const arr = [...prev];
      [arr[idx], arr[next]] = [arr[next], arr[idx]];
      return arr;
    });
  };

  const handleGenerate = async () => {
    if (!instruction.trim()) return;
    setLoading(true);
    setResult(null);
    setSaved(false);
    try {
      const body = {
        instruction,
        report_scope: scope,
        format_type: format,
        date_from: dateFrom || null,
        date_to: dateTo || null,
      };
      if (useTemplate && sections.some(s => s.title.trim())) {
        body.report_template = sections
          .filter(s => s.title.trim())
          .map(({ title, description, content_type }) => ({ title, description, content_type }));
      }
      const data = await apiJson('/api/reports/custom', { method: 'POST', body: JSON.stringify(body) });
      setResult(data);
    } catch (err) {
      setResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!result?.report) return;
    setSaving(true);
    try {
      await apiFetch('/api/reports/custom/save', {
        method: 'POST',
        body: JSON.stringify({ narrative: result.report, instruction }),
      });
      setSaved(true);
    } catch { /* save is optional */ } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: 'grid', gap: '24px' }}>
      <header>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Sparkles color="var(--primary-color)" /> Custom Report Builder
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Describe what you need and optionally define the exact sections. The AI searches your data and fills each section with real numbers.
        </p>
      </header>

      {/* ── Main instruction + scope ── */}
      <section className="glass-panel">
        <div className="form-group">
          <label>What should this report cover?</label>
          <textarea
            rows={3}
            value={instruction}
            onChange={e => setInstruction(e.target.value)}
            placeholder="e.g. Analyse contribution trends for Q2 2025, highlight anomalies, and recommend actions for the finance department."
            style={{ resize: 'vertical', fontSize: '1rem' }}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div className="form-group">
            <label>Data scope</label>
            <select value={scope} onChange={e => setScope(e.target.value)}>
              <option value="my_department">My department</option>
              {isAdmin && <option value="all_departments">All departments</option>}
            </select>
          </div>

          <div className="form-group">
            <label>Default format (used when no template)</label>
            <select value={format} onChange={e => setFormat(e.target.value)}>
              <option value="narrative">Narrative</option>
              <option value="bullet_points">Bullet points</option>
              <option value="executive_brief">Executive brief</option>
              <option value="table">Table</option>
              <option value="detailed">Detailed</option>
            </select>
          </div>

          <div className="form-group">
            <label>Date from</label>
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          </div>

          <div className="form-group">
            <label>Date to</label>
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
          </div>
        </div>
      </section>

      {/* ── Template builder toggle ── */}
      <section className="glass-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: useTemplate ? '20px' : 0 }}>
          <div>
            <h2 style={{ fontSize: '1rem', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <LayoutTemplate size={18} color="var(--primary-color)" /> Custom Section Template
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
              Define exactly which sections appear and what goes in each one. The AI fills them with your real data.
            </p>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.9rem' }}>
            <input
              type="checkbox"
              checked={useTemplate}
              onChange={e => setUseTemplate(e.target.checked)}
              style={{ width: '16px', height: '16px' }}
            />
            Use custom template
          </label>
        </div>

        {useTemplate && (
          <>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <button className="btn btn-outline" onClick={loadPreset} style={{ fontSize: '0.82rem', display: 'flex', gap: '6px' }}>
                <LayoutTemplate size={14} /> Load CNPS standard template
              </button>
              <button className="btn btn-outline" onClick={addSection} style={{ fontSize: '0.82rem', display: 'flex', gap: '6px' }}>
                <Plus size={14} /> Add section
              </button>
            </div>

            <div style={{ display: 'grid', gap: '10px' }}>
              {sections.map((sec, idx) => (
                <div key={sec._id} style={{ border: '1px solid var(--border-color)', borderRadius: '8px', padding: '14px 16px', background: 'var(--bg-secondary)' }}>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', paddingTop: '6px' }}>
                      <button onClick={() => moveSection(sec._id, -1)} disabled={idx === 0} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px', color: 'var(--text-secondary)' }}>
                        <ChevronUp size={14} />
                      </button>
                      <button onClick={() => moveSection(sec._id, 1)} disabled={idx === sections.length - 1} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px', color: 'var(--text-secondary)' }}>
                        <ChevronDown size={14} />
                      </button>
                    </div>

                    <div style={{ flex: 1, display: 'grid', gap: '8px' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '8px' }}>
                        <input
                          value={sec.title}
                          onChange={e => updateSection(sec._id, 'title', e.target.value)}
                          placeholder={`Section ${idx + 1} heading (e.g. Executive Summary)`}
                          style={{ fontSize: '0.9rem', fontWeight: 600 }}
                        />
                        <select
                          value={sec.content_type}
                          onChange={e => updateSection(sec._id, 'content_type', e.target.value)}
                          style={{ fontSize: '0.85rem' }}
                        >
                          {CONTENT_TYPES.map(ct => (
                            <option key={ct.value} value={ct.value}>{ct.label}</option>
                          ))}
                        </select>
                      </div>
                      <textarea
                        rows={2}
                        value={sec.description}
                        onChange={e => updateSection(sec._id, 'description', e.target.value)}
                        placeholder="Describe what this section should contain — the AI uses this as its instruction for filling the section with your data."
                        style={{ fontSize: '0.85rem', resize: 'vertical' }}
                      />
                    </div>

                    <button
                      onClick={() => removeSection(sec._id)}
                      disabled={sections.length === 1}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--status-critical)', paddingTop: '4px' }}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <button className="btn btn-outline" onClick={addSection} style={{ marginTop: '12px', fontSize: '0.82rem', display: 'flex', gap: '6px' }}>
              <Plus size={14} /> Add another section
            </button>
          </>
        )}
      </section>

      <button
        className="btn btn-primary"
        onClick={handleGenerate}
        disabled={loading || !instruction.trim()}
        style={{ display: 'flex', gap: '8px', justifyContent: 'center', padding: '12px 24px', fontSize: '1rem' }}
      >
        <FileText size={16} /> {loading ? 'Generating report…' : 'Generate Report'}
      </button>

      {/* ── Result ── */}
      {result && (
        <section className="glass-panel">
          {result.error ? (
            <p style={{ color: 'var(--status-critical)' }}>{result.error}</p>
          ) : (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h2 style={{ fontSize: '1.1rem' }}>Generated Report</h2>
                <div style={{ display: 'flex', gap: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)', alignItems: 'center' }}>
                  <span>{result.kpi_count} KPIs</span>
                  <span>·</span>
                  <span>{result.anomaly_count} anomalies</span>
                  <button
                    className="btn btn-outline"
                    onClick={handleSave}
                    disabled={saving || saved}
                    style={{ padding: '4px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px', marginLeft: '8px' }}
                  >
                    {saved ? <><Check size={14} /> Saved</> : <><Save size={14} /> Save to history</>}
                  </button>
                </div>
              </div>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.9', color: 'var(--text-primary)', fontSize: '0.95rem', fontFamily: 'inherit' }}>
                {result.report}
              </div>
            </>
          )}
        </section>
      )}
    </div>
  );
};

export default CustomReportPage;
