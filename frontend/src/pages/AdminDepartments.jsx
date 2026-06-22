import React, { useState, useEffect } from 'react';
import { Building2, Plus, Trash2, RefreshCcw, Clock, Users, Edit3, Grid3x3 } from 'lucide-react';
import { apiFetch, apiJson } from '../lib/api';

const AdminDepartments = () => {
  const [departments, setDepartments] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState(null);
  const [newDept, setNewDept] = useState({ name: '', description: '', heartbeat_schedule: 'daily', heartbeat_time: '06:00' });
  const [editDept, setEditDept] = useState({ template_id: '' });

  const fetchDepartments = async () => {
    try {
      const data = await apiJson('/api/admin/departments');
      setDepartments(data.departments || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTemplates = async () => {
    try {
      const data = await apiJson('/api/admin/semantic/templates');
      setTemplates(data.templates || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => { 
    fetchDepartments();
    fetchTemplates();
  }, []);

  const handleCreate = async () => {
    try {
      await apiFetch('/api/admin/departments', {
        method: 'POST',
        body: JSON.stringify(newDept)
      });
      setShowCreate(false);
      setNewDept({ name: '', description: '', heartbeat_schedule: 'daily', heartbeat_time: '06:00' });
      fetchDepartments();
    } catch (err) { console.error(err); }
  };

  const handleUpdate = async (deptId) => {
    try {
      await apiFetch(`/api/admin/departments/${deptId}`, {
        method: 'PUT',
        body: JSON.stringify(editDept)
      });
      setShowEdit(null);
      setEditDept({ template_id: '' });
      fetchDepartments();
    } catch (err) { console.error(err); }
  };

  const handleDelete = async (deptId) => {
    if (!confirm('Delete this department? Users will be unassigned.')) return;
    try {
      await apiFetch(`/api/admin/departments/${deptId}`, { method: 'DELETE' });
      fetchDepartments();
    } catch (err) { console.error(err); }
  };

  const handleTriggerHeartbeat = async (deptId) => {
    try {
      const data = await apiJson(`/api/admin/heartbeat/trigger/${deptId}`, { method: 'POST' });
      alert(`Triggered ETL for ${data.users_triggered} user(s) in this department.`);
    } catch (err) { console.error(err); }
  };

  if (loading) return <p style={{ color: 'var(--text-secondary)' }}>Loading departments...</p>;

  return (
    <div>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Building2 color="var(--primary-color)" /> Department Management
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>Manage departments, configure heartbeats, and assign users.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)} style={{ display: 'flex', gap: '8px' }}>
          <Plus size={18} /> New Department
        </button>
      </header>

      {/* Create Modal */}
      {showCreate && (
        <div className="glass-panel" style={{ marginBottom: '24px' }}>
          <h3 style={{ marginBottom: '16px' }}>Create Department</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="form-group">
              <label>Name</label>
              <input value={newDept.name} onChange={e => setNewDept({ ...newDept, name: e.target.value })} placeholder="e.g. Sales" />
            </div>
            <div className="form-group">
              <label>Description</label>
              <input value={newDept.description} onChange={e => setNewDept({ ...newDept, description: e.target.value })} placeholder="Optional" />
            </div>
            <div className="form-group">
              <label>Heartbeat Schedule</label>
              <select value={newDept.heartbeat_schedule} onChange={e => setNewDept({ ...newDept, heartbeat_schedule: e.target.value })}>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly (Sunday)</option>
                <option value="monthly">Monthly (1st)</option>
              </select>
            </div>
            <div className="form-group">
              <label>Heartbeat Time</label>
              <input type="time" value={newDept.heartbeat_time} onChange={e => setNewDept({ ...newDept, heartbeat_time: e.target.value })} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <button className="btn btn-outline" onClick={() => setShowCreate(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleCreate}>Create</button>
          </div>
        </div>
      )}

      {/* Assign Semantic Template Modal */}
      {showEdit && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}
          onClick={() => setShowEdit(null)}
        >
          <div className="glass-panel" style={{ maxWidth: '500px', width: '92%' }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Grid3x3 size={18} /> Assign Semantic Template
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Select a semantic template to assign to this department. Users in this department will use this template for their field mappings.
            </p>
            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label>Semantic Template</label>
              <select 
                value={editDept.template_id} 
                onChange={e => setEditDept({ ...editDept, template_id: e.target.value })}
                style={{ width: '100%' }}
              >
                <option value="">-- No template (clear assignment) --</option>
                {templates.map(tpl => (
                  <option key={tpl.id} value={tpl.id}>
                    {tpl.name} {tpl.description ? `- ${tpl.description}` : ''}
                  </option>
                ))}
              </select>
            </div>
            {templates.length === 0 && (
              <p style={{ fontSize: '0.8rem', color: 'var(--status-warning)', marginBottom: '12px' }}>
                No semantic templates found. Create one first in <strong>Admin → Semantic</strong>.
              </p>
            )}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button className="btn btn-outline" onClick={() => setShowEdit(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={() => handleUpdate(showEdit)}>
                Assign Template
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Department Table */}
      <div style={{ display: 'grid', gap: '16px' }}>
        {departments.map(dept => (
          <div key={dept.id} className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ fontSize: '1rem', marginBottom: '4px' }}>{dept.name}</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{dept.description || 'No description'}</p>
              <div style={{ display: 'flex', gap: '16px', marginTop: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Clock size={14} /> {dept.heartbeat_schedule} at {dept.heartbeat_time}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Users size={14} /> {dept.user_count} user(s)
                </span>
                <span>Last sync: {dept.last_sync || 'Never'}</span>
                {dept.instance_template_name && <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--status-normal)', padding: '2px 8px', background: 'rgba(16,185,129,0.1)', borderRadius: '4px' }}>Instance: {dept.instance_template_name}</span>}
                {dept.template_name ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--primary-color)', padding: '2px 8px', background: 'rgba(59,130,246,0.1)', borderRadius: '4px' }}>
                    <Grid3x3 size={12} /> Semantic: {dept.template_name}
                  </span>
                ) : (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--status-warning)', padding: '2px 8px', background: 'rgba(245,158,11,0.1)', borderRadius: '4px' }}>
                    <Grid3x3 size={12} /> No semantic template
                  </span>
                )}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="btn btn-outline" onClick={() => { setShowEdit(dept.id); setEditDept({ template_id: dept.template_id || '' }); }} style={{ padding: '8px', fontSize: '0.8rem' }} title="Assign Semantic Template">
                <Grid3x3 size={16} />
              </button>
              <button className="btn btn-outline" onClick={() => handleTriggerHeartbeat(dept.id)} style={{ padding: '8px', fontSize: '0.8rem' }} title="Trigger ETL">
                <RefreshCcw size={16} />
              </button>
              <button className="btn btn-outline" onClick={() => handleDelete(dept.id)} style={{ padding: '8px', fontSize: '0.8rem', color: 'var(--status-critical)' }} title="Delete">
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
        {departments.length === 0 && <p style={{ color: 'var(--text-secondary)' }}>No departments yet. Create one to get started.</p>}
      </div>
    </div>
  );
};

export default AdminDepartments;
