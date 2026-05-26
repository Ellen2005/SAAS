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
  // Start as false — we resolve from localStorage/session cache immediately
  const [loading, setLoading] = useState(true);
  const resolvedRef = useRef(false);

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

  // Fetch role from backend — non-blocking, runs after UI is already shown
  const fetchUserRole = useCallback(async () => {
    try {
      const data = await apiJson('/api/users/me');
      setRole(data.role || 'manager');
      setDepartmentId(data.department_id ?? null);
      setDepartmentName(data.department_name ?? null);
      // Cache role so next load is instant
      try {
        localStorage.setItem('saas.user.role.v1', JSON.stringify({
          role: data.role || 'manager',
          department_id: data.department_id,
          department_name: data.department_name,
        }));
      } catch { /* ignore */ }
    } catch {
      // Backend unreachable — use cached role if available, else default
      try {
        const cached = localStorage.getItem('saas.user.role.v1');
        if (cached) {
          const parsed = JSON.parse(cached);
          setRole(parsed.role || 'manager');
          setDepartmentId(parsed.department_id ?? null);
          setDepartmentName(parsed.department_name ?? null);
          return;
        }
      } catch { /* ignore */ }
      setRole('manager');
    }
  }, []);

  useEffect(() => {
    // Step 1: Resolve session synchronously from Supabase's local storage cache.
    // This is instant — no network call. We use it to unblock the UI immediately.
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!resolvedRef.current) {
        resolvedRef.current = true;
        if (session?.user) {
          setUser(session.user);
          // Try to restore cached role instantly before the API responds
          try {
            const cached = localStorage.getItem('saas.user.role.v1');
            if (cached) {
              const parsed = JSON.parse(cached);
              setRole(parsed.role || 'manager');
              setDepartmentId(parsed.department_id ?? null);
              setDepartmentName(parsed.department_name ?? null);
            }
          } catch { /* ignore */ }
          setLoading(false);
          // Fetch fresh role in background — does NOT block UI
          fetchUserRole();
        } else {
          resetAuthState();
          setLoading(false);
        }
      }
    }).catch(() => {
      if (!resolvedRef.current) {
        resolvedRef.current = true;
        resetAuthState();
        setLoading(false);
      }
    });

    // Step 2: Listen for subsequent auth changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        if (session?.user) {
          setUser(session.user);
          if (!resolvedRef.current) {
            resolvedRef.current = true;
            setLoading(false);
          }
          // Always refresh role on auth change (non-blocking)
          fetchUserRole();
        } else {
          resetAuthState();
          if (!resolvedRef.current) {
            resolvedRef.current = true;
          }
          setLoading(false);
        }
      }
    );

    return () => subscription?.unsubscribe();
  }, [fetchUserRole, resetAuthState]);

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
    refreshRole: () => user && fetchUserRole(),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}
