import React, { useState, useEffect } from 'react';
import { Layers, Plus, Trash2 } from 'lucide-react';
import { apiFetch, apiJson } from '../lib/api';

const DATA_TYPES = ['currency', 'string', 'date', 'percent', 'integer', 'float'];

const AdminSemantic = () => {
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [fields, setFields] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateTemplate, setShowCreateTemplate] = useState(false);
  const [showCreateField, setShowCreateField] = useState(false);
  const [newTemplate, setNewTemplate] = useState({ name: '', description: '' });
  const [newField, setNewField] = useState({ global_field_name: '', data_type: 'string', required: false, description: '' });

  const fetchTemplates = async () => {
    try {
      const data = await apiJson('/api/admin/semantic/templates');
      setTemplates(data.templates || []);
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  const fetchFields = async (templateId) => {
    try {
      const data = await apiJson(`/api/admin/semantic/templates/${templateId}/fields`);
      setFields(data.fields || []);
    } catch (err) { console.error(err); }
  };

  useEffect(() => { fetchTemplates(); }, []);

  const handleSelectTemplate = (tpl) => {
    setSelectedTemplate(tpl);
    fetchFields(tpl.id);
  };

  const handleCreateTemplate = async () => {
    try {
      await apiFetch('/api/admin/semantic/templates', {
        method: 'POST',
        body: JSON.stringify(newTemplate)
      });
      setShowCreateTemplate(false);
      setNewTemplate({ name: '', description: '' });
      fetchTemplates();
    } catch (err) { console.error(err); }
  };

  const handleDeleteTemplate = async (id) => {
    if (!confirm('Delete this template and all its fields?')) return;
    try {
      await apiFetch(`/api/admin/semantic/templates/${id}`, { method: 'DELETE' });
      setSelectedTemplate(null);
      fetchTemplates();
    } catch (err) { console.error(err); }
  };

  const handleCreateField = async () => {
    try {
      await apiFetch(`/api/admin/semantic/templates/${selectedTemplate.id}/fields`, {
        method: 'POST',
        body: JSON.stringify(newField)
      });
      setShowCreateField(false);
      setNewField({ global_field_name: '', data_type: 'string', required: false, description: '' });
      fetchFields(selectedTemplate.id);
    } catch (err) { console.error(err); }
  };

  const handleDeleteField = async (fieldId) => {
    try {
      await apiFetch(`/api/admin/semantic/fields/${fieldId}`, { method: 'DELETE' });
      fetchFields(selectedTemplate.id);
    } catch (err) { console.error(err); }
  };

  if (loading) return <p style={{ color: 'var(--text-secondary)' }}>Loading semantic templates...</p>;

  return (
    <div>
      <header style={{ marginBottom: '32px' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Layers color="var(--primary-color)" /> Semantic Layer
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Define KPI metrics for departments. Leave the template empty to let the system auto-discover metrics from each database.
        </p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
        {/* Template List */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '1rem' }}>Templates</h2>
            <button className="btn btn-outline" onClick={() => setShowCreateTemplate(true)} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
              <Plus size={14} />
            </button>
          </div>

          {showCreateTemplate && (
            <div className="glass-panel" style={{ marginBottom: '16px', padding: '16px' }}>
              <input placeholder="Template name" value={newTemplate.name} onChange={e => setNewTemplate({ ...newTemplate, name: e.target.value })} style={{ marginBottom: '8px' }} />
              <input placeholder="Description" value={newTemplate.description} onChange={e => setNewTemplate({ ...newTemplate, description: e.target.value })} style={{ marginBottom: '8px' }} />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn btn-primary" onClick={handleCreateTemplate} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>Create</button>
                <button className="btn btn-outline" onClick={() => setShowCreateTemplate(false)} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>Cancel</button>
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gap: '8px' }}>
            {templates.map(tpl => (
              <div
                key={tpl.id}
                className="glass-panel"
                style={{
                  padding: '12px', cursor: 'pointer',
                  borderColor: selectedTemplate?.id === tpl.id ? 'var(--primary-color)' : 'var(--border-color)'
                }}
                onClick={() => handleSelectTemplate(tpl)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{tpl.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{tpl.field_count} fields, {tpl.department_count} departments</div>
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); handleDeleteTemplate(tpl.id); }} style={{ background: 'none', border: 'none', color: 'var(--status-critical)', cursor: 'pointer' }}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Fields Editor */}
        <div>
          {selectedTemplate ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h2 style={{ fontSize: '1rem' }}>{selectedTemplate.name}</h2>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{selectedTemplate.description}</p>
                </div>
                <button className="btn btn-primary" onClick={() => setShowCreateField(true)} style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}>
                  <Plus size={14} /> Add Field
                </button>
              </div>

              {showCreateField && (
                <div className="glass-panel" style={{ marginBottom: '16px', padding: '16px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                    <input placeholder="Field name (e.g. net_revenue)" value={newField.global_field_name} onChange={e => setNewField({ ...newField, global_field_name: e.target.value })} />
                    <select value={newField.data_type} onChange={e => setNewField({ ...newField, data_type: e.target.value })}>
                      {DATA_TYPES.map(dt => <option key={dt} value={dt}>{dt}</option>)}
                    </select>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
                      <input type="checkbox" checked={newField.required} onChange={e => setNewField({ ...newField, required: e.target.checked })} />
                      Required
                    </label>
                  </div>
                  <input placeholder="Description (optional)" value={newField.description} onChange={e => setNewField({ ...newField, description: e.target.value })} style={{ marginBottom: '12px' }} />
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button className="btn btn-primary" onClick={handleCreateField} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>Add</button>
                    <button className="btn btn-outline" onClick={() => setShowCreateField(false)} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>Cancel</button>
                  </div>
                </div>
              )}

              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <th style={{ padding: '8px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Field Name</th>
                    <th style={{ padding: '8px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Type</th>
                    <th style={{ padding: '8px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Required</th>
                    <th style={{ padding: '8px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Description</th>
                    <th style={{ padding: '8px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {fields.map(f => (
                    <tr key={f.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: '0.85rem' }}>{f.global_field_name}</td>
                      <td style={{ padding: '8px', fontSize: '0.85rem' }}>{f.data_type}</td>
                      <td style={{ padding: '8px' }}>
                        {f.required && <span style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--status-critical)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem' }}>REQ</span>}
                      </td>
                      <td style={{ padding: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{f.description || '—'}</td>
                      <td style={{ padding: '8px' }}>
                        <button onClick={() => handleDeleteField(f.id)} style={{ background: 'none', border: 'none', color: 'var(--status-critical)', cursor: 'pointer' }}>
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {fields.length === 0 && <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '12px' }}>No fields defined yet.</p>}
            </>
          ) : (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '300px', color: 'var(--text-secondary)' }}>
              Select a template to view and edit its fields.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminSemantic;
