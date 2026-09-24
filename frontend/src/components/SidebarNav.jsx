import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, BarChart2, FileText, Brain, Settings, LogOut,
  Shield, Database, MessageSquare, ClipboardCheck, ChevronLeft,
  ChevronRight, Moon, Sun, Menu, X, TrendingUp, Search, Home,
  Building2, Users, BookOpen, ChevronDown,
} from 'lucide-react';
import { useAuth } from '../lib/authContext';
import { useOrg } from '../lib/orgContext';
import { useLang } from '../lib/i18n';
import useIsMobile from '../hooks/useIsMobile';
import { supabase } from '../lib/supabaseClient';

const NAV_ITEMS = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', roles: ['user', 'manager', 'admin'] },
  { to: '/analyst', icon: Brain, label: 'AI Analyst', roles: ['manager', 'admin'] },
  { to: '/reports', icon: FileText, label: 'Reports', roles: ['user', 'manager', 'admin'] },
  { to: '/query', icon: MessageSquare, label: 'Ask Data', roles: ['manager', 'admin'] },
  { to: '/explorer', icon: Database, label: 'Schema', roles: ['manager', 'admin'] },
  { to: '/validation', icon: ClipboardCheck, label: 'Validation', roles: ['manager', 'admin'] },
  { to: '/settings', icon: Settings, label: 'Settings', roles: ['manager', 'admin'] },
];

const ADMIN_ITEMS = [
  { to: '/admin', icon: Shield, label: 'Overview', roles: ['admin'] },
  { to: '/admin/users', icon: Users, label: 'Users', roles: ['admin'] },
  { to: '/admin/departments', icon: Building2, label: 'Departments', roles: ['admin'] },
  { to: '/admin/semantic', icon: BookOpen, label: 'Semantic Layer', roles: ['admin'] },
  { to: '/admin/validation', icon: ClipboardCheck, label: 'Quality Rules', roles: ['admin'] },
  { to: '/admin/templates', icon: FileText, label: 'Templates', roles: ['admin'] },
];

function SidebarNav({ collapsed, onToggle, isMobile: isMob }) {
  const { user, isAdmin, isManager, departmentName } = useAuth();
  const { org } = useOrg();
  const { t } = useLang();
  const navigate = useNavigate();
  const [isDark, setIsDark] = useState(() => localStorage.getItem('ea-theme') !== 'light');

  const userRole = isAdmin ? 'admin' : isManager ? 'manager' : 'user';
  const visibleItems = NAV_ITEMS.filter(item => item.roles.includes(userRole));
  const visibleAdmin = ADMIN_ITEMS.filter(item => item.roles.includes(userRole));

  const handleLogout = async () => {
    try {
      localStorage.removeItem('saas.dashboard.lastSummary.v1');
      localStorage.removeItem('saas.dashboard.lastSummary.v2');
      localStorage.removeItem('saas.dashboard.metricsCache.v1');
      localStorage.removeItem('saas.validation.lastLogs.v1');
      localStorage.removeItem('saas.user.role.v1');
      localStorage.removeItem('dashboard_layout');
    } catch {}
    await supabase.auth.signOut();
    navigate('/login', { replace: true });
  };

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle('light-theme', !next);
    localStorage.setItem('ea-theme', next ? 'dark' : 'light');
  };

  // ─── Mobile: Bottom Tab Bar ────────────────────────────────────────────
  if (isMob) {
    const mobileItems = visibleItems.slice(0, 5); // max 5 tabs
    return (
      <nav style={{
        position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 200,
        background: 'var(--ea-bg-nav)', borderTop: '1px solid var(--ea-border)',
        display: 'flex', justifyContent: 'space-around', alignItems: 'center',
        padding: '6px 0 env(safe-area-inset-bottom, 8px)',
        backdropFilter: 'blur(12px)',
      }}>
        {mobileItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/dashboard'}
            style={({ isActive }) => ({
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
              padding: '4px 12px', borderRadius: 8, textDecoration: 'none',
              color: isActive ? 'var(--ea-primary)' : 'var(--ea-text-muted)',
              fontSize: '0.65rem', fontWeight: isActive ? 600 : 400,
              transition: 'all 0.15s ease',
              background: isActive ? 'var(--ea-primary-bg)' : 'transparent',
            })}
          >
            <item.icon size={20} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    );
  }

  // ─── Desktop: Sidebar ──────────────────────────────────────────────────
  const sidebarWidth = collapsed ? 68 : 240;

  return (
    <>
      {/* Top bar — only theme + logout + user info */}
      <header style={{
        position: 'fixed', top: 0, left: sidebarWidth, right: 0, height: 56, zIndex: 150,
        background: 'var(--ea-bg-nav)', borderBottom: '1px solid var(--ea-border)',
        display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
        padding: '0 24px', gap: 12,
        transition: 'left 0.25s cubic-bezier(0.4,0,0.2,1)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginRight: 'auto' }}>
          {departmentName && (
            <span style={{ fontSize: '0.75rem', color: 'var(--ea-text-muted)', padding: '3px 10px', background: 'var(--ea-bg-card)', borderRadius: 999, border: '1px solid var(--ea-border)' }}>
              {departmentName}
            </span>
          )}
          {isAdmin && (
            <span style={{ fontSize: '0.65rem', color: '#f59e0b', padding: '2px 8px', background: 'rgba(245,158,11,0.12)', borderRadius: 4, fontWeight: 700, letterSpacing: '0.05em' }}>
              ADMIN
            </span>
          )}
        </div>
        <button onClick={toggleTheme} style={{
          background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)',
          borderRadius: 8, padding: '6px 10px', color: 'var(--ea-text-secondary)',
          cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
          fontSize: '0.8rem', transition: 'all 0.15s',
        }}>
          {isDark ? <Sun size={14} /> : <Moon size={14} />}
        </button>
        <button onClick={handleLogout} style={{
          background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)',
          borderRadius: 8, padding: '6px 12px', color: 'var(--ea-text-secondary)',
          cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
          fontSize: '0.8rem', transition: 'all 0.15s',
        }}>
          <LogOut size={14} /> Logout
        </button>
      </header>

      {/* Sidebar */}
      <aside style={{
        position: 'fixed', top: 0, left: 0, bottom: 0, width: sidebarWidth, zIndex: 160,
        background: 'var(--ea-bg-sidebar)', borderRight: '1px solid var(--ea-border)',
        display: 'flex', flexDirection: 'column',
        transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1)',
        overflow: 'hidden',
      }}>
        {/* Brand */}
        <div style={{
          height: 56, display: 'flex', alignItems: 'center', gap: 10,
          padding: collapsed ? '0 18px' : '0 20px',
          borderBottom: '1px solid var(--ea-border)',
          flexShrink: 0,
        }}>
          <img src={org?.logo_url || '/logo.png'} alt="" style={{ width: 28, height: 28, flexShrink: 0 }} />
          {!collapsed && (
            <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--ea-text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {org?.name || 'Smart Analytics'}
            </span>
          )}
        </div>

        {/* Collapse toggle */}
        <button onClick={onToggle} style={{
          position: 'absolute', top: 14, right: -12, zIndex: 10,
          width: 24, height: 24, borderRadius: '50%',
          background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', color: 'var(--ea-text-muted)', fontSize: 10,
          boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
        }}>
          {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
        </button>

        {/* Nav items */}
        <nav style={{ flex: 1, overflowY: 'auto', padding: '12px 8px' }}>
          <div style={{ marginBottom: 20 }}>
            {!collapsed && <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--ea-text-muted)', padding: '0 12px', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Main</div>}
            {visibleItems.map(item => (
              <SidebarLink key={item.to} item={item} collapsed={collapsed} />
            ))}
          </div>

          {visibleAdmin.length > 0 && (
            <div>
              {!collapsed && <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--ea-text-muted)', padding: '0 12px', marginBottom: 6, marginTop: 16, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Admin</div>}
              {visibleAdmin.map(item => (
                <SidebarLink key={item.to} item={item} collapsed={collapsed} />
              ))}
            </div>
          )}
        </nav>

        {/* User info */}
        {!collapsed && (
          <div style={{
            padding: '12px 16px', borderTop: '1px solid var(--ea-border)',
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <div style={{
              width: 32, height: 32, borderRadius: '50%',
              background: 'var(--ea-primary-bg)', color: 'var(--ea-primary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.8rem', fontWeight: 700, flexShrink: 0,
            }}>
              {user?.email?.[0]?.toUpperCase() || 'U'}
            </div>
            <div style={{ overflow: 'hidden' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--ea-text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user?.email?.split('@')[0] || 'User'}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--ea-text-muted)', textTransform: 'capitalize' }}>
                {userRole}
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Spacer */}
      <div style={{ width: sidebarWidth, flexShrink: 0, transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1)' }} />
    </>
  );
}

function SidebarLink({ item, collapsed }) {
  return (
    <NavLink
      to={item.to}
      end={item.to === '/admin'}
      style={({ isActive }) => ({
        display: 'flex', alignItems: 'center', gap: 10,
        padding: collapsed ? '10px 0' : '10px 12px',
        justifyContent: collapsed ? 'center' : 'flex-start',
        borderRadius: 8, textDecoration: 'none', marginBottom: 2,
        color: isActive ? 'var(--ea-primary)' : 'var(--ea-text-secondary)',
        background: isActive ? 'var(--ea-primary-bg)' : 'transparent',
        fontWeight: isActive ? 600 : 400,
        fontSize: '0.85rem',
        transition: 'all 0.15s ease',
        position: 'relative',
      })}
      title={collapsed ? item.label : undefined}
    >
      <item.icon size={18} style={{ flexShrink: 0 }} />
      {!collapsed && <span style={{ whiteSpace: 'nowrap' }}>{item.label}</span>}
    </NavLink>
  );
}

export default SidebarNav;
