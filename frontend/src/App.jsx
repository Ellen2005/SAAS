import React, { lazy, Suspense, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './lib/authContext.jsx';
import { OrgProvider, useOrg } from './lib/orgContext.jsx';
import { LangProvider, useLang } from './lib/i18n.jsx';
import { useInactivityTimeout } from './hooks/useInactivityTimeout';
import useIsMobile from './hooks/useIsMobile';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/ToastProvider';
import SidebarNav from './components/SidebarNav';

import Landing from './pages/Landing';
import Login from './pages/Login';
import ReloadPrompt from './components/ReloadPrompt';
import OfflineBanner from './components/OfflineBanner';
import InactivityWarning from './components/InactivityWarning';
import AssistantBot from './components/AssistantBot';

const Dashboard = lazy(() => import('./pages/Dashboard'));
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
const ExecutiveAnalyticsPage = lazy(() => import('./pages/ExecutiveAnalyticsPage'));
const DataQualityPage = lazy(() => import('./pages/DataQualityPage'));

const PageLoader = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
    <div style={{ width: '32px', height: '32px', border: '3px solid var(--border-color)', borderTopColor: 'var(--primary-color)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
  </div>
);


function AppShell() {
  const { user, loading } = useAuth();
  const isMobile = useIsMobile();
  useInactivityTimeout(!!user);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'var(--bg-color)', gap: '16px' }}>
        <img src="/logo.png" alt="Smart Analytics" style={{ width: '56px', height: '56px', opacity: 0.9 }} />
        <div style={{ width: '32px', height: '32px', border: '3px solid var(--border-color)', borderTopColor: 'var(--primary-color)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
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
            <div style={{ display: 'flex', minHeight: '100vh' }}>
              <SidebarNav
                collapsed={sidebarCollapsed}
                onToggle={() => setSidebarCollapsed(c => !c)}
                isMobile={isMobile}
              />
              <main style={{
                flex: 1,
                padding: isMobile ? '16px 16px 80px' : '24px 32px',
                maxWidth: '1440px',
                marginLeft: isMobile ? 0 : undefined,
                overflowX: 'hidden',
              }}>
                <ErrorBoundary>
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
                        <RoleGuard allowedRoles={['manager', 'admin']} fallback="/dashboard"><ValidationHistory /></RoleGuard>
                      } />
                      <Route path="/settings" element={
                        <RoleGuard allowedRoles={['manager', 'admin']} fallback="/dashboard"><Settings /></RoleGuard>
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
                      <Route path="/executive" element={
                        <RoleGuard allowedRoles={['manager', 'admin']}><ExecutiveAnalyticsPage /></RoleGuard>
                      } />
                      <Route path="/data-quality" element={
                        <RoleGuard allowedRoles={['manager', 'admin']}><DataQualityPage /></RoleGuard>
                      } />
                      <Route path="*" element={<Navigate to="/dashboard" replace />} />
                    </Routes>
                  </Suspense>
                </ErrorBoundary>
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
        <OrgProvider>
          <ToastProvider>
            <Router>
              <ReloadPrompt />
              <OfflineBanner />
              <InactivityWarning />
              <AssistantBot />
              <AppShell />
            </Router>
          </ToastProvider>
        </OrgProvider>
      </AuthProvider>
    </LangProvider>
  );
}

export default App;
