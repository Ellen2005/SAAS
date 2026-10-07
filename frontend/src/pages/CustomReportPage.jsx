import React, { useState, useMemo } from 'react';
import {
  FileText, Sparkles, Save, Check, Plus, Trash2, ChevronDown, ChevronUp,
  LayoutTemplate, Eye, Type, Table2, ListOrdered, FileBarChart, Settings2,
} from 'lucide-react';
import { apiFetch, apiJson, API_URL, getSessionSafe } from '../lib/api';
import { useAuth } from '../lib/authContext';
import { useOrg } from '../lib/orgContext';
import useIsMobile from '../hooks/useIsMobile';

const CONTENT_TYPES = [
  { value: 'narrative', label: 'Narrative' },
  { value: 'table_and_narrative', label: 'Table + Text' },
  { value: 'bullet_points', label: 'Bullet Points' },
];

const CHART_TYPES = [
  { value: 'bar', label: 'Bar Chart' },
  { value: 'line', label: 'Line Chart' },
  { value: 'area', label: 'Area Chart' },
  { value: 'pie', label: 'Pie Chart' },
  { value: 'scatter', label: 'Scatter Plot' },
];

const STANDARD_TEMPLATE = [
  { title: 'Executive Summary', description: 'Concise summary of purpose, key findings, conclusions and recommendations.', content_type: 'narrative' },
  { title: 'Introduction and Background', description: 'Institutional mandate, relevant programs, problem statement, scope and objectives.', content_type: 'narrative' },
  { title: 'Data Sources', description: 'All data sources used: database name, time frame, variables extracted, preprocessing applied.', content_type: 'narrative' },
  { title: 'Methodology', description: 'Statistical methods, tools, key assumptions, data cleaning steps.', content_type: 'narrative' },
  { title: 'Data Quality and Cleaning', description: 'Completeness, accuracy and consistency checks. Validation pass rate summary.', content_type: 'narrative' },
  { title: 'Analysis and Results', description: 'Core KPI findings with tables. Each result explained in plain language with numbered figures.', content_type: 'table_and_narrative' },
  { title: 'Interpretation and Key Findings', description: 'What the numbers mean in context of institutional goals. Trends, comparisons, implications.', content_type: 'narrative' },
  { title: 'Conclusions and Recommendations', description: 'Numbered conclusions answering objectives. Concrete recommendations tied to evidence.', content_type: 'narrative' },
  { title: 'Limitations', description: 'Data gaps, assumptions, unanswered questions.', content_type: 'narrative' },
];

const emptySection = () => ({ title: '', description: '', content_type: 'narrative', _id: Math.random().toString(36).slice(2) });

const CustomReportPage = () => {
  const { isAdmin } = useAuth();
  const { org } = useOrg();
  const isMobile = useIsMobile();

  const [reportTitle, setReportTitle] = useState('');
  const [instruction, setInstruction] = useState('');
  const [scope, setScope] = useState('my_department');
  const [format, setFormat] = useState('narrative');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [chartType, setChartType] = useState('line');
  const [useTemplate, setUseTemplate] = useState(true);
  const [sections, setSections] = useState(() => STANDARD_TEMPLATE.map(s => ({ ...s, _id: Math.random().toString(36).slice(2) })));
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState('configure');

  const loadPreset = () => setSections(STANDARD_TEMPLATE.map(s => ({ ...s, _id: Math.random().toString(36).slice(2) })));
  const addSection = () => setSections(prev => [...prev, emptySection()]);
  const removeSection = (id) => setSections(prev => prev.filter(s => s._id !== id));
  const updateSection = (id, field, value) => setSections(prev => prev.map(s => s._id === id ? { ...s, [field]: value } : s));
  const moveSection = (id, dir) => setSections(prev => {
    const idx = prev.findIndex(s => s._id === id);
    const next = idx + dir;
    if (next < 0 || next >= prev.length) return prev;
    const arr = [...prev];
    [arr[idx], arr[next]] = [arr[next], arr[idx]];
    return arr;
  });

  const validSections = useMemo(() => sections.filter(s => s.title.trim()), [sections]);

  const handleGenerate = async () => {
    if (!instruction.trim()) return;
    setLoading(true);
    setResult(null);
    setSaved(false);
    setActiveTab('result');
    try {
      const body = {
        instruction: reportTitle ? `${reportTitle}. ${instruction}` : instruction,
        report_scope: scope,
        format_type: format,
        date_from: dateFrom || null,
        date_to: dateTo || null,
        chart_type: chartType,
      };
      if (useTemplate && validSections.length > 0) {
        body.report_template = validSections.map(({ title, description, content_type }) => ({ title, description, content_type }));
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
        body: JSON.stringify({ narrative: result.report, instruction: reportTitle || instruction }),
      });
      setSaved(true);
    } catch { /* optional */ } finally { setSaving(false); }
  };

  const handleDownloadPDF = async () => {
    if (!result?.report) return;
    try {
      const token = (await getSessionSafe())?.access_token;
      const res = await fetch(`${API_URL}/api/reports/custom/pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          narrative: result.report,
          title: reportTitle || instruction || 'Custom Report',
        }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(reportTitle || 'custom-report').replace(/[^a-z0-9]+/gi, '_').toLowerCase()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    }
  };

  const inputStyle = {
    width: '100%', padding: '10px 12px', background: 'var(--ea-bg-card)',
    border: '1px solid var(--ea-border)', borderRadius: 8,
    color: 'var(--ea-text-primary)', fontSize: '0.9rem', outline: 'none',
  };
  const labelStyle = {
    display: 'block', fontSize: '0.78rem', fontWeight: 600,
    color: 'var(--ea-text-muted)', marginBottom: 5, textTransform: 'uppercase',
    letterSpacing: '0.04em',
  };

  const TabBtn = ({ tab, icon: Icon, label }) => (
    <button
      onClick={() => setActiveTab(tab)}
      style={{
        display: 'flex', alignItems: 'center', gap: 7, padding: '9px 16px',
        background: activeTab === tab ? 'var(--ea-primary-bg)' : 'transparent',
        color: activeTab === tab ? 'var(--ea-primary)' : 'var(--ea-text-secondary)',
        border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: '0.85rem',
        fontWeight: activeTab === tab ? 600 : 400, transition: 'all 0.15s',
      }}
    >
      <Icon size={15} /> {label}
    </button>
  );

  return (
    <div style={{ maxWidth: 1100 }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '1.5rem', marginBottom: 6 }}>
          <Sparkles color="var(--ea-primary)" size={22} /> Report Builder
        </h1>
        <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.9rem', margin: 0 }}>
          Configure your report, preview the structure, then generate a professional PDF.
        </p>
      </header>

      <div style={{ display: 'flex', gap: 4, marginBottom: 24, background: 'var(--ea-bg-card)', borderRadius: 10, padding: 4, border: '1px solid var(--ea-border)', width: 'fit-content' }}>
        <TabBtn tab="configure" icon={Settings2} label="Configure" />
        <TabBtn tab="preview" icon={Eye} label="Preview" />
        <TabBtn tab="result" icon={FileBarChart} label="Result" />
      </div>

      {/* ═══ CONFIGURE TAB ═══ */}
      {activeTab === 'configure' && (
        <div style={{ display: 'grid', gap: 20 }}>
          <section style={{ background: 'var(--ea-bg-card)', borderRadius: 12, border: '1px solid var(--ea-border)', padding: 24 }}>
            <h2 style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <FileText size={16} color="var(--ea-primary)" /> Report Basics
            </h2>

            <div style={{ marginBottom: 14 }}>
              <label style={labelStyle}>Report Title</label>
              <input style={inputStyle} value={reportTitle} onChange={e => setReportTitle(e.target.value)} placeholder="e.g. Q2 2025 Contribution Collection Analysis" />
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={labelStyle}>What should this report cover?</label>
              <textarea rows={3} style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.6 }} value={instruction} onChange={e => setInstruction(e.target.value)} placeholder="e.g. Analyse contribution trends for Q2 2025, highlight anomalies, compare regional performance, and recommend actions." />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr 1fr', gap: 12 }}>
              <div>
                <label style={labelStyle}>Data Scope</label>
                <select style={inputStyle} value={scope} onChange={e => setScope(e.target.value)}>
                  <option value="my_department">My Department</option>
                  {isAdmin && <option value="all_departments">All Departments</option>}
                </select>
              </div>
              <div>
                <label style={labelStyle}>Format</label>
                <select style={inputStyle} value={format} onChange={e => setFormat(e.target.value)}>
                  <option value="narrative">Narrative</option>
                  <option value="bullet_points">Bullet Points</option>
                  <option value="executive_brief">Executive Brief</option>
                  <option value="table">Table</option>
                  <option value="detailed">Detailed</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Date From</label>
                <input type="date" style={inputStyle} value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
              </div>
              <div>
                <label style={labelStyle}>Date To</label>
                <input type="date" style={inputStyle} value={dateTo} onChange={e => setDateTo(e.target.value)} />
              </div>
            </div>

            <div style={{ marginTop: 14 }}>
              <label style={labelStyle}>Chart Type</label>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {CHART_TYPES.map(ct => (
                  <button
                    key={ct.value}
                    onClick={() => setChartType(ct.value)}
                    style={{
                      padding: '7px 14px', borderRadius: 8, fontSize: '0.82rem',
                      background: chartType === ct.value ? 'var(--ea-primary)' : 'var(--ea-bg)',
                      color: chartType === ct.value ? '#fff' : 'var(--ea-text-secondary)',
                      border: `1px solid ${chartType === ct.value ? 'var(--ea-primary)' : 'var(--ea-border)'}`,
                      cursor: 'pointer', transition: 'all 0.15s',
                    }}
                  >{ct.label}</button>
                ))}
              </div>
            </div>
          </section>

          {/* Template builder */}
          <section style={{ background: 'var(--ea-bg-card)', borderRadius: 12, border: '1px solid var(--ea-border)', padding: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: useTemplate ? 16 : 0 }}>
              <div>
                <h2 style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <LayoutTemplate size={16} color="var(--ea-primary)" /> Report Sections
                </h2>
                <p style={{ fontSize: '0.82rem', color: 'var(--ea-text-muted)', margin: 0 }}>
                  {validSections.length} section{validSections.length !== 1 ? 's' : ''} configured. The AI fills each with your real data.
                </p>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
                <input type="checkbox" checked={useTemplate} onChange={e => setUseTemplate(e.target.checked)} style={{ width: 16, height: 16 }} />
                Use template
              </label>
            </div>

            {useTemplate && (
              <>
                <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
                  <button onClick={loadPreset} className="btn btn-outline" style={{ fontSize: '0.8rem', padding: '7px 14px' }}>
                    <LayoutTemplate size={13} style={{ marginRight: 6 }} /> Standard Template
                  </button>
                  <button onClick={addSection} className="btn btn-outline" style={{ fontSize: '0.8rem', padding: '7px 14px' }}>
                    <Plus size={13} style={{ marginRight: 6 }} /> Add Section
                  </button>
                </div>

                <div style={{ display: 'grid', gap: 8 }}>
                  {sections.map((sec, idx) => (
                    <div key={sec._id} style={{ border: '1px solid var(--ea-border)', borderRadius: 10, padding: '12px 14px', background: 'var(--ea-bg)' }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, paddingTop: 4 }}>
                          <button onClick={() => moveSection(sec._id, -1)} disabled={idx === 0}
                            style={{ background: 'none', border: 'none', cursor: idx === 0 ? 'default' : 'pointer', padding: 2, color: idx === 0 ? 'var(--ea-border)' : 'var(--ea-text-muted)' }}>
                            <ChevronUp size={13} />
                          </button>
                          <button onClick={() => moveSection(sec._id, 1)} disabled={idx === sections.length - 1}
                            style={{ background: 'none', border: 'none', cursor: idx === sections.length - 1 ? 'default' : 'pointer', padding: 2, color: idx === sections.length - 1 ? 'var(--ea-border)' : 'var(--ea-text-muted)' }}>
                            <ChevronDown size={13} />
                          </button>
                        </div>
                        <div style={{ flex: 1, display: 'grid', gap: 6 }}>
                          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '2fr 1fr', gap: 8 }}>
                            <input value={sec.title} onChange={e => updateSection(sec._id, 'title', e.target.value)}
                              placeholder={`Section ${idx + 1} heading`} style={{ ...inputStyle, fontWeight: 600, fontSize: '0.85rem' }} />
                            <select value={sec.content_type} onChange={e => updateSection(sec._id, 'content_type', e.target.value)}
                              style={{ ...inputStyle, fontSize: '0.82rem' }}>
                              {CONTENT_TYPES.map(ct => <option key={ct.value} value={ct.value}>{ct.label}</option>)}
                            </select>
                          </div>
                          <textarea rows={2} value={sec.description} onChange={e => updateSection(sec._id, 'description', e.target.value)}
                            placeholder="What should this section contain? The AI uses this as its instruction."
                            style={{ ...inputStyle, fontSize: '0.82rem', resize: 'vertical' }} />
                        </div>
                        <button onClick={() => removeSection(sec._id)} disabled={sections.length === 1}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: sections.length === 1 ? 'var(--ea-border)' : '#ef4444', paddingTop: 4 }}>
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                <button onClick={addSection} className="btn btn-outline" style={{ marginTop: 10, fontSize: '0.8rem', padding: '7px 14px' }}>
                  <Plus size={13} style={{ marginRight: 6 }} /> Add Another Section
                </button>
              </>
            )}
          </section>

          <button className="btn btn-primary" onClick={handleGenerate} disabled={loading || !instruction.trim()}
            style={{ display: 'flex', gap: 8, justifyContent: 'center', padding: '14px 28px', fontSize: '1rem', width: '100%' }}>
            {loading ? (
              <>
                <div style={{ width: 18, height: 18, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
                Generating Report…
              </>
            ) : <><FileText size={17} /> Generate Professional Report</>}
          </button>
        </div>
      )}

      {/* ═══ PREVIEW TAB ═══ */}
      {activeTab === 'preview' && (
        <div style={{ background: 'var(--ea-bg-card)', borderRadius: 12, border: '1px solid var(--ea-border)', overflow: 'hidden' }}>
          <div style={{ background: 'var(--ea-bg)', padding: '14px 24px', borderBottom: '1px solid var(--ea-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <img src={org?.logo_url || '/logo.png'} alt="" style={{ width: 24, height: 24 }} />
              <div>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--ea-text-primary)' }}>{reportTitle || 'Untitled Report'}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--ea-text-muted)' }}>
                  {org?.name || 'Smart Analytics'} · {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                </div>
              </div>
            </div>
            <span style={{ fontSize: '0.7rem', padding: '3px 10px', borderRadius: 999, background: 'var(--ea-primary-bg)', color: 'var(--ea-primary)', fontWeight: 600 }}>
              {format.replace('_', ' ').toUpperCase()}
            </span>
          </div>

          <div style={{ padding: isMobile ? '24px 16px' : '40px 48px', minHeight: 400 }}>
            <div style={{ textAlign: 'center', marginBottom: 40, paddingBottom: 32, borderBottom: '2px solid var(--ea-border)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>Professional Report</div>
              <h2 style={{ fontSize: isMobile ? '1.4rem' : '2rem', fontWeight: 800, color: 'var(--ea-text-primary)', marginBottom: 8 }}>{reportTitle || 'Untitled Report'}</h2>
              <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.9rem', maxWidth: 500, margin: '0 auto' }}>{instruction || 'No description provided.'}</p>
              <div style={{ display: 'flex', justifyContent: 'center', gap: 24, marginTop: 16, fontSize: '0.78rem', color: 'var(--ea-text-muted)', flexWrap: 'wrap' }}>
                <span>Period: {dateFrom || 'Start'} — {dateTo || 'Present'}</span>
                <span>Scope: {scope.replace('_', ' ')}</span>
                <span>Chart: {chartType}</span>
              </div>
            </div>

            {useTemplate && validSections.length > 0 && (
              <div style={{ marginBottom: 32 }}>
                <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--ea-text-primary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Table of Contents</h3>
                <div style={{ display: 'grid', gap: 6 }}>
                  {validSections.map((sec, i) => (
                    <div key={sec._id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', background: 'var(--ea-bg)', borderRadius: 8, fontSize: '0.85rem' }}>
                      <span style={{ color: 'var(--ea-primary)', fontWeight: 700, width: 24, flexShrink: 0 }}>{String(i + 1).padStart(2, '0')}</span>
                      <span style={{ color: 'var(--ea-text-primary)', fontWeight: 500, flex: 1 }}>{sec.title}</span>
                      <span style={{ fontSize: '0.7rem', color: 'var(--ea-text-muted)', padding: '2px 8px', background: 'var(--ea-bg-card)', borderRadius: 4 }}>
                        {CONTENT_TYPES.find(c => c.value === sec.content_type)?.label || 'Narrative'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {useTemplate && validSections.length > 0 && (
              <div style={{ display: 'grid', gap: 16 }}>
                {validSections.map((sec, i) => (
                  <div key={sec._id} style={{ border: '1px dashed var(--ea-border)', borderRadius: 10, padding: 20, background: 'rgba(255,255,255,0.01)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--ea-primary)', background: 'var(--ea-primary-bg)', padding: '2px 8px', borderRadius: 4 }}>§{i + 1}</span>
                      <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--ea-text-primary)', margin: 0 }}>{sec.title}</h4>
                    </div>
                    <p style={{ fontSize: '0.82rem', color: 'var(--ea-text-muted)', lineHeight: 1.6, margin: 0 }}>{sec.description || 'No description provided.'}</p>
                    {sec.content_type === 'table_and_narrative' && (
                      <div style={{ marginTop: 10, fontSize: '0.75rem', color: 'var(--ea-text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Table2 size={13} /> Will include data table + interpretation
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {!useTemplate && (
              <div style={{ textAlign: 'center', padding: 40, color: 'var(--ea-text-muted)' }}>
                <LayoutTemplate size={40} style={{ marginBottom: 12, opacity: 0.3 }} />
                <p>Template disabled. The AI will structure the report automatically.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══ RESULT TAB ═══ */}
      {activeTab === 'result' && (
        <div>
          {loading && (
            <div style={{ background: 'var(--ea-bg-card)', borderRadius: 12, border: '1px solid var(--ea-border)', padding: 60, textAlign: 'center' }}>
              <div style={{ width: 36, height: 36, border: '3px solid var(--ea-border)', borderTopColor: 'var(--ea-primary)', borderRadius: '50%', animation: 'spin 0.7s linear infinite', margin: '0 auto 16px' }} />
              <p style={{ fontSize: '0.95rem', color: 'var(--ea-text-secondary)' }}>Generating your report…</p>
              <p style={{ fontSize: '0.8rem', color: 'var(--ea-text-muted)' }}>AI is analyzing data and filling each section.</p>
            </div>
          )}

          {!loading && result?.error && (
            <div style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 12, padding: 24 }}>
              <p style={{ color: '#f87171', margin: 0 }}>Error: {result.error}</p>
            </div>
          )}

          {!loading && result?.report && (
            <div style={{ background: 'var(--ea-bg-card)', borderRadius: 12, border: '1px solid var(--ea-border)', overflow: 'hidden' }}>
              <div style={{ padding: '14px 24px', borderBottom: '1px solid var(--ea-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
                <div>
                  <h3 style={{ fontSize: '1rem', margin: 0 }}>Generated Report</h3>
                  <div style={{ fontSize: '0.78rem', color: 'var(--ea-text-muted)', display: 'flex', gap: 10, marginTop: 3 }}>
                    <span>{result.kpi_count ?? 0} KPIs</span>
                    <span>·</span>
                    <span>{result.anomaly_count ?? 0} anomalies</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button className="btn btn-outline" onClick={handleSave} disabled={saving || saved}
                    style={{ padding: '7px 14px', fontSize: '0.8rem', display: 'flex', gap: 6 }}>
                    {saved ? <><Check size={14} /> Saved</> : <><Save size={14} /> Save</>}
                  </button>
                  <button className="btn btn-primary" onClick={handleDownloadPDF}
                    style={{ padding: '7px 14px', fontSize: '0.8rem', display: 'flex', gap: 6 }}>
                    <FileText size={14} /> Download PDF
                  </button>
                </div>
              </div>
              <div style={{ padding: 24, whiteSpace: 'pre-wrap', lineHeight: 1.85, color: 'var(--ea-text-primary)', fontSize: '0.92rem' }}>
                {result.report}
              </div>
            </div>
          )}

          {!loading && !result && (
            <div style={{ background: 'var(--ea-bg-card)', borderRadius: 12, border: '1px solid var(--ea-border)', padding: 60, textAlign: 'center' }}>
              <FileBarChart size={40} style={{ color: 'var(--ea-text-muted)', opacity: 0.3, marginBottom: 12 }} />
              <p style={{ color: 'var(--ea-text-muted)' }}>No report generated yet. Go to Configure and click Generate.</p>
            </div>
          )}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default CustomReportPage;
