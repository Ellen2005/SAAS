/* eslint react-refresh/only-export-components: off */
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { supabase } from './supabaseClient';
import { apiJson } from './api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [departmentId, setDepartmentId] = useState(null);
  const [departmentName, setDepartmentName] = useState(null);
  const [loading, setLoading] = useState(true);
  const initRef = useRef(false);

  const clearCache = useCallback(() => {
    try {
      localStorage.removeItem('saas.dashboard.lastSummary.v1');
      localStorage.removeItem('saas.validation.lastLogs.v1');
      localStorage.removeItem('saas.user.role.v1');
    } catch { /* ignore */ }
  }, []);

  const resetAuthState = useCallback(() => {
    clearCache();
    setUser(null);
    setRole(null);
    setDepartmentId(null);
    setDepartmentName(null);
  }, [clearCache]);

  const fetchUserRole = useCallback(async (currentUser) => {
    let resolvedRole = 'viewer';
    try {
      const data = await apiJson('/api/users/me');
      resolvedRole = data.role || 'viewer';
      setRole(resolvedRole);
      setDepartmentId(data.department_id ?? null);
      setDepartmentName(data.department_name ?? null);
      
      if (currentUser?.email) {
        apiJson('/api/users/me/profile', {
          method: 'POST',
          body: JSON.stringify({ email: currentUser.email, display_name: currentUser.email })
        }).catch(() => {});
      }
      
      try {
        localStorage.setItem('saas.user.role.v1', JSON.stringify({
          role: resolvedRole,
          department_id: data.department_id,
          department_name: data.department_name,
        }));
      } catch { /* ignore */ }
    } catch (err) {
      // If the API call fails (e.g. 401, network error), use cached role
      // but NEVER let this throw — it would trigger redirectToLogin
      try {
        const cached = localStorage.getItem('saas.user.role.v1');
        if (cached) {
          const parsed = JSON.parse(cached);
          resolvedRole = parsed.role || 'viewer';
          setRole(resolvedRole);
          setDepartmentId(parsed.department_id ?? null);
          setDepartmentName(parsed.department_name ?? null);
          return resolvedRole;
        }
      } catch { /* ignore */ }
      // If API failed and no cache, still set a role so the user isn't stuck
      // Use 'manager' as default if there's a session (prevents lockdown)
      setRole('manager');
    }
    return resolvedRole;
  }, []);

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    // Force UI to unblock after 5 seconds max (prevents infinite loading)
    const forceUnblock = setTimeout(() => {
      setLoading(false);
    }, 5000);

    // Restore cached role immediately - default to 'manager' if user has session
    // This prevents flashing viewer-only nav while backend resolves
    let roleFromCache = null;
    try {
      const cached = localStorage.getItem('saas.user.role.v1');
      if (cached) {
        const parsed = JSON.parse(cached);
        roleFromCache = parsed.role || 'viewer';
        setRole(roleFromCache);
        setDepartmentId(parsed.department_id ?? null);
        setDepartmentName(parsed.department_name ?? null);
      }
    } catch { /* ignore */ }

    supabase.auth.getSession()
      .then(({ data: { session } }) => {
        if (session?.user) {
          setUser(session.user);
          // Fetch fresh role in background - don't block UI
          fetchUserRole(session.user).catch(() => {});
        } else {
          resetAuthState();
        }
      })
      .catch(() => {
        resetAuthState();
      })
      .finally(() => {
        clearTimeout(forceUnblock);
        setLoading(false);
      });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (session?.user) {
          setUser(session.user);
          // Fire and forget — never block the auth state change callback
          fetchUserRole(session.user).catch(() => {});
        } else {
          resetAuthState();
        }
      }
    );

    return () => {
      clearTimeout(forceUnblock);
      subscription?.unsubscribe();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const value = {
    user,
    role,
    departmentId,
    departmentName,
    loading,
    isAdmin: role === 'admin',
    isManager: role === 'manager',
    isViewer: role === 'viewer',
    isManagerOrAbove: role === 'admin' || role === 'manager',
    refreshRole: () => user && fetchUserRole(user),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}
