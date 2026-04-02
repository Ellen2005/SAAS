import React, { useState, useEffect } from 'react';
import { Users as UsersIcon, Trash2 } from 'lucide-react';
import { apiFetch, apiJson } from '../lib/api';

const AdminUsers = () => {
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editRole, setEditRole] = useState(null); // { userId, role, departmentId }

  const fetchData = async () => {
    try {
      const [u, d] = await Promise.all([
        apiJson('/api/admin/users'),
        apiJson('/api/admin/departments')
      ]);
      setUsers(u.users || []);
      setDepartments(d.departments || []);
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const handleSaveRole = async () => {
    if (!editRole) return;
    try {
      await apiFetch(`/api/admin/users/${editRole.userId}/role`, {
        method: 'POST',
        body: JSON.stringify({ role: editRole.role, department_id: editRole.departmentId })
      });
      setEditRole(null);
      fetchData();
    } catch (err) { console.error(err); }
  };

  const handleRemoveRole = async (userId) => {
    if (!confirm('Remove all roles for this user?')) return;
    try {
      await apiFetch(`/api/admin/users/${userId}/role`, { method: 'DELETE' });
      fetchData();
    } catch (err) { console.error(err); }
  };

  if (loading) return <p style={{ color: 'var(--text-secondary)' }}>Loading users...</p>;

  return (
    <div>
      <header style={{ marginBottom: '32px' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <UsersIcon color="var(--primary-color)" /> User & Role Management
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>Assign roles and departments to users across the system.</p>
      </header>

      <div className="glass-panel">
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>User</th>
              <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Role</th>
              <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Department</th>
              <th style={{ padding: '12px', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.role_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '12px', fontFamily: 'monospace', fontSize: '0.8rem' }}>
                  {u.email || `${u.user_id.substring(0, 12)}...`}
                </td>
                <td style={{ padding: '12px' }}>
                  {editRole?.userId === u.user_id ? (
                    <select value={editRole.role} onChange={e => setEditRole({ ...editRole, role: e.target.value })} style={{ padding: '4px 8px', fontSize: '0.8rem' }}>
                      <option value="admin">Admin</option>
                      <option value="manager">Manager</option>
                      <option value="viewer">Viewer</option>
                    </select>
                  ) : (
                    <span style={{
                      padding: '4px 10px', borderRadius: '999px', fontSize: '0.75rem', fontWeight: 600,
                      background: u.role === 'admin' ? 'rgba(245,158,11,0.15)' : u.role === 'manager' ? 'rgba(59,130,246,0.15)' : 'rgba(148,163,184,0.15)',
                      color: u.role === 'admin' ? '#f59e0b' : u.role === 'manager' ? 'var(--primary-color)' : 'var(--text-secondary)'
                    }}>
                      {u.role}
                    </span>
                  )}
                </td>
                <td style={{ padding: '12px' }}>
                  {editRole?.userId === u.user_id ? (
                    <select value={editRole.departmentId || ''} onChange={e => setEditRole({ ...editRole, departmentId: e.target.value || null })} style={{ padding: '4px 8px', fontSize: '0.8rem' }}>
                      <option value="">None</option>
                      {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                    </select>
                  ) : (
                    u.department_name || <span style={{ color: 'var(--text-secondary)' }}>—</span>
                  )}
                </td>
                <td style={{ padding: '12px' }}>
                  {editRole?.userId === u.user_id ? (
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button className="btn btn-primary" onClick={handleSaveRole} style={{ padding: '4px 12px', fontSize: '0.8rem' }}>Save</button>
                      <button className="btn btn-outline" onClick={() => setEditRole(null)} style={{ padding: '4px 12px', fontSize: '0.8rem' }}>Cancel</button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button className="btn btn-outline" onClick={() => setEditRole({ userId: u.user_id, role: u.role, departmentId: u.department_id })} style={{ padding: '4px 12px', fontSize: '0.8rem' }}>Edit</button>
                      <button onClick={() => handleRemoveRole(u.user_id)} style={{ background: 'none', border: 'none', color: 'var(--status-critical)', cursor: 'pointer' }}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && <p style={{ color: 'var(--text-secondary)', padding: '16px' }}>No users found. Run the migration bootstrap functions first.</p>}
      </div>
    </div>
  );
};

export default AdminUsers;
