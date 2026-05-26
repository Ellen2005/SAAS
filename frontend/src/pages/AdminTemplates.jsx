import React, { useCallback, useEffect, useState } from 'react';
import { Boxes, Plus, Save, Send } from 'lucide-react';
import { apiFetch, apiJson } from '../lib/api';

const EMPTY_TEMPLATE = {
  name: '',
  config: {
    sync_default: { frequency: 'weekly', time: '06:00' },
    ai_tone: 'insight-driven',
    validation_rules: { null_threshold: 0.1, anomaly_threshold: 0.5, critical_anomaly_zscore: 3.0 },
    email_recipients: [],
    base_definitions: '',
    base_prompt: '',
  },
};

const AdminTemplates = () => {
  const [templates, setTemplates] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [selectedDepartmentId, setSelectedDepartmentId] = useState('');
  const [draft, setDraft] = useState(EMPTY_TEMPLATE);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [templateData, departmentData] = await Promise.all([
        apiJson('/api/templates/instances'),
        apiJson('/api/admin/departments'),
      ]);
      setTemplates(templateData.templates || []);
      setDepartments(departmentData.departments || []);
      if (!selectedTemplateId && templateData.templates?.[0]?.id) {
        setSelectedTemplateId(templateData.templates[0].id);
      }
      if (!selectedDepartmentId && departmentData.departments?.[0]?.id) {
        setSelectedDepartmentId(departmentData.departments[0].id);
      }
    } catch (error) {
      console.error('Failed to load instance templates', error);
    } finally {
      setLoading(false);
    }
  }, [selectedDepartmentId, selectedTemplateId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreate = async () => {
    try {
      await apiFetch('/api/templates/instances', {
        method: 'POST',
        body: JSON.stringify(draft),
      });
      setDraft(EMPTY_TEMPLATE);
      await loadData();
    } catch (error) {
      alert(`Unable to create template: ${error.message}`);
    }
  };

  const handleDeploy = async () => {
    if (!selectedTemplateId || !selectedDepartmentId) return;

    try {
      await apiFetch('/api/templates/deploy', {
        method: 'POST',
        body: JSON.stringify({
          template_id: selectedTemplateId,
          department_id: selectedDepartmentId,
        }),
      });
      alert('Template deployed to department.');
      await loadData();
    } catch (error) {
      alert(`Unable to deploy template: ${error.message}`);
    }
  };

  if (loading) {
    return <p style={{ color: 'var(--text-secondary)' }}>Loading instance templates...</p>;
  }

  return (
    <div style={{ display: 'grid', gap: '24px' }}>
      <header>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Boxes color="var(--primary-color)" /> Instance Templates
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Standardize department startup defaults without taking away local ownership.
        </p>
      </header>

      <section className="glass-panel">
        <h2 style={{ marginBottom: '16px' }}>Deploy Existing Template</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '12px', alignItems: 'end' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Template</label>
            <select value={selectedTemplateId} onChange={(event) => setSelectedTemplateId(event.target.value)}>
              {templates.map((template) => (
                <option key={template.id} value={template.id}>{template.name}</option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Department</label>
            <select value={selectedDepartmentId} onChange={(event) => setSelectedDepartmentId(event.target.value)}>
              {departments.map((department) => (
                <option key={department.id} value={department.id}>{department.name}</option>
              ))}
            </select>
          </div>
          <button className="btn btn-primary" onClick={handleDeploy}>
            <Send size={16} /> Deploy
          </button>
        </div>
      </section>

      <section className="glass-panel">
        <h2 style={{ marginBottom: '16px' }}>Create Template</h2>
        <div className="form-group">
          <label>Template Name</label>
          <input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} placeholder="Standard Department Instance" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div className="form-group">
            <label>Default Frequency</label>
            <select
              value={draft.config.sync_default.frequency}
              onChange={(event) => setDraft({
                ...draft,
                config: {
                  ...draft.config,
                  sync_default: { ...draft.config.sync_default, frequency: event.target.value },
                },
              })}
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
          <div className="form-group">
            <label>Default Time</label>
            <input
              type="time"
              value={draft.config.sync_default.time}
              onChange={(event) => setDraft({
                ...draft,
                config: {
                  ...draft.config,
                  sync_default: { ...draft.config.sync_default, time: event.target.value },
                },
              })}
            />
          </div>
          <div className="form-group">
            <label>AI Tone</label>
            <select
              value={draft.config.ai_tone}
              onChange={(event) => setDraft({
                ...draft,
                config: { ...draft.config, ai_tone: event.target.value },
              })}
            >
              <option value="insight-driven">Insight-driven</option>
              <option value="formal">Formal</option>
            </select>
          </div>
          <div className="form-group">
            <label>Null Threshold</label>
            <input
              type="number"
              step="0.01"
              value={draft.config.validation_rules.null_threshold}
              onChange={(event) => setDraft({
                ...draft,
                config: {
                  ...draft.config,
                  validation_rules: {
                    ...draft.config.validation_rules,
                    null_threshold: Number(event.target.value),
                  },
                },
              })}
            />
          </div>
        </div>

        <div className="form-group">
          <label>Email Recipients</label>
          <textarea
            rows={2}
            value={(draft.config.email_recipients || []).join('\n')}
            onChange={(event) => setDraft({
              ...draft,
              config: {
                ...draft.config,
                email_recipients: event.target.value.split('\n').map((value) => value.trim()).filter(Boolean),
              },
            })}
            placeholder="dept-manager@company.com"
          />
        </div>

        <div className="form-group">
          <label>Base Definitions</label>
          <textarea
            rows={3}
            value={draft.config.base_definitions}
            onChange={(event) => setDraft({
              ...draft,
              config: { ...draft.config, base_definitions: event.target.value },
            })}
            placeholder="Net Revenue = Gross Revenue - Returns - Discounts"
          />
        </div>

        <div className="form-group">
          <label>Base Prompt Template</label>
          <textarea
            rows={4}
            value={draft.config.base_prompt}
            onChange={(event) => setDraft({
              ...draft,
              config: { ...draft.config, base_prompt: event.target.value },
            })}
            placeholder="You are a business analyst for {company_name}..."
          />
        </div>

        <button className="btn btn-primary" onClick={handleCreate}>
          <Plus size={16} /> Create Template
        </button>
      </section>

      <section className="glass-panel">
        <h2 style={{ marginBottom: '16px' }}>Current Templates</h2>
        <div style={{ display: 'grid', gap: '12px' }}>
          {templates.map((template) => (
            <div key={template.id} style={{ padding: '14px', borderRadius: '12px', background: 'rgba(255,255,255,0.03)' }}>
              <div style={{ fontWeight: 600 }}>{template.name}</div>
              <pre style={{ marginTop: '10px', whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
                {JSON.stringify(template.config, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default AdminTemplates;
