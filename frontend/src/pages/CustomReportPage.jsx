import React, { useState } from 'react';
import { FileText, Sparkles, Save, Check } from 'lucide-react';
import { apiFetch, apiJson } from '../lib/api';
import { useLang } from '../lib/i18n';
import { useAuth } from '../lib/authContext';

const CustomReportPage = () => {
  const { t } = useLang();
  const { isAdmin } = useAuth();

  const [instruction, setInstruction] = useState('');
  const [scope, setScope] = useState('my_department');
  const [format, setFormat] = useState('narrative');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleGenerate = async () => {
    if (!instruction.trim()) return;
    setLoading(true);
    setResult(null);
    setSaved(false);
    try {
      const data = await apiJson('/api/reports/custom', {
        method: 'POST',
        body: JSON.stringify({
          instruction,
          report_scope: scope,
          format_type: format,
          date_from: dateFrom || null,
          date_to: dateTo || null,
        }),
      });
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
    } catch {
      // silently fail — save is optional
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: 'grid', gap: '24px' }}>
      <header>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Sparkles color="var(--primary-color)" /> {t('custom_report_title')}
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Describe what you need — the AI generates a targeted report from your data.
        </p>
      </header>

      <section className="glass-panel">
        <div className="form-group">
          <label>{t('custom_report_instruction')}</label>
          <textarea
            rows={3}
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder={t('custom_report_instruction_placeholder')}
            style={{ resize: 'vertical', fontSize: '1rem' }}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div className="form-group">
            <label>{t('custom_report_scope')}</label>
            <select value={scope} onChange={(e) => setScope(e.target.value)}>
              <option value="my_department">{t('custom_report_scope_mine')}</option>
              {isAdmin && <option value="all_departments">{t('custom_report_scope_all')}</option>}
            </select>
          </div>

          <div className="form-group">
            <label>{t('custom_report_format')}</label>
            <select value={format} onChange={(e) => setFormat(e.target.value)}>
              <option value="narrative">{t('custom_report_format_narrative')}</option>
              <option value="bullet_points">{t('custom_report_format_bullets')}</option>
              <option value="executive_brief">{t('custom_report_format_brief')}</option>
              <option value="table">{t('custom_report_format_table')}</option>
              <option value="detailed">{t('custom_report_format_detailed')}</option>
            </select>
          </div>

          <div className="form-group">
            <label>{t('custom_report_date_from')}</label>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>

          <div className="form-group">
            <label>{t('custom_report_date_to')}</label>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
        </div>

        <button className="btn btn-primary" onClick={handleGenerate} disabled={loading || !instruction.trim()} style={{ display: 'flex', gap: '8px' }}>
          <FileText size={16} /> {loading ? t('custom_report_generating') : t('custom_report_generate')}
        </button>
      </section>

      {result && (
        <section className="glass-panel">
          {result.error ? (
            <p style={{ color: 'var(--status-critical)' }}>{result.error}</p>
          ) : (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h2 style={{ fontSize: '1.1rem' }}>{t('custom_report_result')}</h2>
                <div style={{ display: 'flex', gap: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  <span>{result.kpi_count} KPIs</span>
                  <span>·</span>
                  <span>{result.anomaly_count} anomalies</span>
                  <button className="btn btn-outline" onClick={handleSave} disabled={saving || saved} style={{ padding: '4px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px', marginLeft: '8px' }}>
                    {saved ? <><Check size={14} /> {t('custom_report_saved')}</> : <><Save size={14} /> {t('custom_report_save')}</>}
                  </button>
                </div>
              </div>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.8', color: 'var(--text-primary)', fontSize: '0.95rem' }}>
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
