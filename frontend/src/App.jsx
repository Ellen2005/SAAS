import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import { LogOut, Shield } from 'lucide-react';
import { supabase } from './lib/supabaseClient';
import { AuthProvider, useAuth } from './lib/authContext.jsx';
import { useInactivityTimeout } from './hooks/useInactivityTimeout';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Login from './pages/Login';
import Landing from './pages/Landing';
import Unsubscribe from './pages/Unsubscribe';
import AdminDashboard from './pages/AdminDashboard';
import AdminDepartments from './pages/AdminDepartments';
import AdminSemantic from './pages/AdminSemantic';
import AdminValidation from './pages/AdminValidation';
import AdminUsers from './pages/AdminUsers';
import AdminTemplates from './pages/AdminTemplates';
import ValidationHistory from './pages/ValidationHistory';
import RoleGuard from './components/RoleGuard';
import ReloadPrompt from './components/ReloadPrompt';
import OfflineBanner from './components/OfflineBanner';
import InactivityWarning from './components/InactivityWarning';

function AdminSubNav() {
  const location = useLocation();
  if (!location.pathname.startsWith('/admin')) return null;

  const links = [
    { to: '/admin', label: 'Overview' },
    { to: '/admin/departments', label: 'Departments' },
    { to: '/admin/semantic', label: 'Semantic Layer' },
    { to: '/admin/validation', label: 'Data Quality' },
    { to: '/admin/users', label: 'Users' },
    { to: '/admin/templates', label: 'Templates' },
  ];

  return (
    <div style={{
      display: 'flex', gap: '4px', marginBottom: '24px', padding: '4px',
      background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid var(--border-color)'
    }}>
      {links.map(link => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.to === '/admin'}
          style={({ isActive }) => ({
            padding: '8px 16px', borderRadius: '8px', fontSize: '0.85rem',
            textDecoration: 'none', fontWeight: 500,
            background: isActive ? 'var(--primary-color)' : 'transparent',
            color: isActive ? 'white' : 'var(--text-secondary)',
            transition: 'all 0.2s ease',
          })}
        >
          {link.label}
        </NavLink>
      ))}
    </div>
  );
}

function AppContent() {
  const { user, departmentName, loading, isAdmin, isManager } = useAuth();

  // Session inactivity timeout — 60 min idle → auto sign-out, warn at 55 min
  useInactivityTimeout(!!user);

  const handleLogout = async () => {
    try {
      localStorage.removeItem('saas.dashboard.lastSummary.v1');
      localStorage.removeItem('saas.validation.lastLogs.v1');
    } catch {
      // ignore
    }
    await supabase.auth.signOut();
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'var(--bg-color)', color: 'var(--text-primary)' }}>
        <p>Initialising SAAS...</p>
      </div>
    );
  }

  return (
    <Router>
      <ReloadPrompt />
      <OfflineBanner />
      <InactivityWarning />
      <Routes>
        <Route path="/" element={user ? <Navigate to="/dashboard" /> : <Landing />} />
        <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <Login />} />
        {/* Public unsubscribe — no auth required */}
        <Route path="/unsubscribe" element={<Unsubscribe />} />

        <Route
          path="/*"
          element={
            user ? (
              <div className="app-container">
                <nav className="navbar">
                  <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <img src="/logo.png" alt="SAAS logo" style={{ width: '32px', height: '32px' }} />
                    <h2 style={{ letterSpacing: '-0.05em' }}>SAAS</h2>
                    {departmentName && (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: '8px', padding: '2px 8px', background: 'rgba(255,255,255,0.05)', borderRadius: '999px' }}>
                        {departmentName}
                      </span>
                    )}
                    {isAdmin && (
                      <span style={{ fontSize: '0.65rem', color: '#f59e0b', padding: '2px 6px', background: 'rgba(245,158,11,0.15)', borderRadius: '4px', fontWeight: 600 }}>
                        ADMIN
                      </span>
                    )}
                  </div>
                  <div className="nav-links" style={{ display: 'flex', alignItems: 'center' }}>
                    {isAdmin && (
                      <NavLink to="/admin" className={({ isActive }) => isActive ? 'active' : ''} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Shield size={14} /> Admin
                      </NavLink>
                    )}
                    <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'active' : ''}>
                      Dashboard
                    </NavLink>
                    {isManager && (
                      <>
                        <NavLink to="/validation" className={({ isActive }) => isActive ? 'active' : ''}>
                          Validation
                        </NavLink>
                        <NavLink to="/settings" className={({ isActive }) => isActive ? 'active' : ''}>
                          Settings
                        </NavLink>
                      </>
                    )}
                    <button
                      onClick={handleLogout}
                      className="btn btn-outline"
                      style={{ padding: '8px 12px', marginLeft: '24px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}
                    >
                      <LogOut size={14} /> Log Out
                    </button>
                  </div>
                </nav>

                <main style={{ padding: '32px', maxWidth: '1440px', margin: '0 auto' }}>
                  {isAdmin && <AdminSubNav />}
                  <Routes>
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/validation" element={
                      <RoleGuard allowedRoles={['manager']} fallback="/dashboard">
                        <ValidationHistory />
                      </RoleGuard>
                    } />
                    <Route path="/settings" element={
                      <RoleGuard allowedRoles={['manager']} fallback="/dashboard">
                        <Settings />
                      </RoleGuard>
                    } />
                    <Route path="/admin" element={
                      <RoleGuard allowedRoles={['admin']}>
                        <AdminDashboard />
                      </RoleGuard>
                    } />
                    <Route path="/admin/departments" element={
                      <RoleGuard allowedRoles={['admin']}>
                        <AdminDepartments />
                      </RoleGuard>
                    } />
                    <Route path="/admin/semantic" element={
                      <RoleGuard allowedRoles={['admin']}>
                        <AdminSemantic />
                      </RoleGuard>
                    } />
                    <Route path="/admin/validation" element={
                      <RoleGuard allowedRoles={['admin']}>
                        <AdminValidation />
                      </RoleGuard>
                    } />
                    <Route path="/admin/users" element={
                      <RoleGuard allowedRoles={['admin']}>
                        <AdminUsers />
                      </RoleGuard>
                    } />
                    <Route path="/admin/templates" element={
                      <RoleGuard allowedRoles={['admin']}>
                        <AdminTemplates />
                      </RoleGuard>
                    } />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </main>
              </div>
            ) : (
              <Navigate to="/login" />
            )
          }
        />
      </Routes>
    </Router>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
