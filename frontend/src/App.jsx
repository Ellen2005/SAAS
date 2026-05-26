import React, { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import { LogOut, Shield, Brain } from 'lucide-react';
import { supabase } from './lib/supabaseClient';
import { AuthProvider, useAuth } from './lib/authContext.jsx';
import { LangProvider, useLang } from './lib/i18n.jsx';
import { useInactivityTimeout } from './hooks/useInactivityTimeout';

import Landing from './pages/Landing';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ReloadPrompt from './components/ReloadPrompt';
import OfflineBanner from './components/OfflineBanner';
import InactivityWarning from './components/InactivityWarning';
import AssistantBot from './components/AssistantBot';

const Settings = lazy(() => import('./pages/Settings'));
const ValidationHistory = lazy(() => import('./pages/ValidationHistory'));
const ReportsHistory = lazy(() => import('./pages/ReportsHistory'));
const Unsubscribe = lazy(() => import('./pages/Unsubscribe'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const AdminDepartments = lazy(() => import('./pages/AdminDepartments'));
const AdminSemantic = lazy(() => import('./pages/AdminSemantic'));
const AdminValidation = lazy(() => import('./pages/AdminValidation'));
const AdminUsers = lazy(() => import('./pages/AdminUsers'));
const AdminTemplates = lazy(() => import('./pages/AdminTemplates'));
const RoleGuard = lazy(() => import('./components/RoleGuard'));
const NLQPage = lazy(() => import('./pages/NLQPage'));
const CustomReportPage = lazy(() => import('./pages/CustomReportPage'));
const SchemaExplorer = lazy(() => import('./pages/SchemaExplorer'));
const AIAnalystPage = lazy(() => import('./pages/AIAnalystPage'));

const PageLoader = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
    <div style={{ width: '32px', height: '32px', border: '3px solid var(--border-color)', borderTopColor: 'var(--primary-color)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
    <style>{'@keyframes spin{to{transform:rotate(360deg)}}'}</style>
  </div>
);

function AdminSubNav() {
  const location = useLocation();
  const { t } = useLang();
  if (!location.pathname.startsWith('/admin')) return null;

  const links = [
    { to: '/admin', label: t('admin_overview') },
    { to: '/admin/departments', label: t('admin_departments') },
    { to: '/admin/semantic', label: t('admin_semantic') },
    { to: '/admin/validation', label: t('admin_quality') },
    { to: '/admin/users', label: t('admin_users') },
    { to: '/admin/templates', label: t('admin_templates') },
  ];

  return (
    <div style={{ display: 'flex', gap: '4px', marginBottom: '24px', padding: '4px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid var(--border-color)', flexWrap: 'wrap' }}>
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

function AppShell() {
  const { user, departmentName, loading, isAdmin, isManager } = useAuth();
  const { t } = useLang();
  useInactivityTimeout(!!user);

  const handleLogout = async () => {
    try {
      localStorage.removeItem('saas.dashboard.lastSummary.v1');
      localStorage.removeItem('saas.validation.lastLogs.v1');
      localStorage.removeItem('saas.user.role.v1');
    } catch { /* ignore */ }
    await supabase.auth.signOut();
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'var(--bg-color)', gap: '16px' }}>
        <img src="/logo.png" alt="SAAS" style={{ width: '56px', height: '56px', opacity: 0.9 }} />
        <div style={{ width: '32px', height: '32px', border: '3px solid var(--border-color)', borderTopColor: 'var(--primary-color)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
        <style>{'@keyframes spin{to{transform:rotate(360deg)}}'}</style>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/" element={user ? <Navigate to="/dashboard" replace /> : <Landing />} />
      <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <Login />} />
      <Route path="/unsubscribe" element={<Suspense fallback={<PageLoader />}><Unsubscribe /></Suspense>} />

      <Route
        path="/*"
        element={
          !user ? <Navigate to="/login" replace /> : (
            <div className="app-container">
              <nav className="navbar">
                <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <img src="/logo.png" alt="SAAS" style={{ width: '32px', height: '32px' }} />
                  <h2 style={{ letterSpacing: '-0.05em' }}>SAAS</h2>
                  {departmentName && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', padding: '2px 8px', background: 'rgba(255,255,255,0.05)', borderRadius: '999px' }}>
                      {departmentName}
                    </span>
                  )}
                  {isAdmin && (
                    <span style={{ fontSize: '0.65rem', color: '#f59e0b', padding: '2px 6px', background: 'rgba(245,158,11,0.15)', borderRadius: '4px', fontWeight: 600 }}>
                      ADMIN
                    </span>
                  )}
                </div>
                <div className="nav-links" style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '2px' }}>
                  {isAdmin && (
                    <NavLink to="/admin" className={({ isActive }) => isActive ? 'active' : ''} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Shield size={14} /> {t('nav_admin')}
                    </NavLink>
                  )}
                  <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'active' : ''}>{t('nav_dashboard')}</NavLink>
                  <NavLink to="/reports" className={({ isActive }) => isActive ? 'active' : ''}>{t('nav_reports')}</NavLink>
                  {isManager && (
                    <>
                      <NavLink to="/analyst" className={({ isActive }) => isActive ? 'active' : ''} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                        <Brain size={13} /> AI Analyst
                      </NavLink>
                      <NavLink to="/explorer" className={({ isActive }) => isActive ? 'active' : ''}>Schema</NavLink>
                      <NavLink to="/query" className={({ isActive }) => isActive ? 'active' : ''}>{t('nlq_title')}</NavLink>
                      <NavLink to="/validation" className={({ isActive }) => isActive ? 'active' : ''}>{t('nav_validation')}</NavLink>
                      <NavLink to="/settings" className={({ isActive }) => isActive ? 'active' : ''}>{t('nav_settings')}</NavLink>
                    </>
                  )}
                  <button onClick={handleLogout} className="btn btn-outline" style={{ padding: '8px 12px', marginLeft: '16px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}>
                    <LogOut size={14} /> {t('nav_logout')}
                  </button>
                </div>
              </nav>

              <main style={{ padding: '32px', maxWidth: '1440px', margin: '0 auto' }}>
                {isAdmin && <AdminSubNav />}
                <Suspense fallback={<PageLoader />}>
                  <Routes>
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/reports" element={<ReportsHistory />} />
                    <Route path="/reports/custom" element={
                      <RoleGuard allowedRoles={['manager', 'admin']}><CustomReportPage /></RoleGuard>
                    } />
                    <Route path="/analyst" element={
                      <RoleGuard allowedRoles={['manager', 'admin']}><AIAnalystPage /></RoleGuard>
                    } />
                    <Route path="/query" element={
                      <RoleGuard allowedRoles={['manager', 'admin']}><NLQPage /></RoleGuard>
                    } />
                    <Route path="/validation" element={
                      <RoleGuard allowedRoles={['manager']} fallback="/dashboard"><ValidationHistory /></RoleGuard>
                    } />
                    <Route path="/settings" element={
                      <RoleGuard allowedRoles={['manager']} fallback="/dashboard"><Settings /></RoleGuard>
                    } />
                    <Route path="/explorer" element={
                      <RoleGuard allowedRoles={['manager', 'admin']}><SchemaExplorer /></RoleGuard>
                    } />
                    <Route path="/admin" element={
                      <RoleGuard allowedRoles={['admin']}><AdminDashboard /></RoleGuard>
                    } />
                    <Route path="/admin/departments" element={
                      <RoleGuard allowedRoles={['admin']}><AdminDepartments /></RoleGuard>
                    } />
                    <Route path="/admin/semantic" element={
                      <RoleGuard allowedRoles={['admin']}><AdminSemantic /></RoleGuard>
                    } />
                    <Route path="/admin/validation" element={
                      <RoleGuard allowedRoles={['admin']}><AdminValidation /></RoleGuard>
                    } />
                    <Route path="/admin/users" element={
                      <RoleGuard allowedRoles={['admin']}><AdminUsers /></RoleGuard>
                    } />
                    <Route path="/admin/templates" element={
                      <RoleGuard allowedRoles={['admin']}><AdminTemplates /></RoleGuard>
                    } />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </Suspense>
              </main>
            </div>
          )
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <LangProvider>
      <AuthProvider>
        <Router>
          <ReloadPrompt />
          <OfflineBanner />
          <InactivityWarning />
          <AssistantBot />
          <AppShell />
        </Router>
      </AuthProvider>
    </LangProvider>
  );
}

export default App;
