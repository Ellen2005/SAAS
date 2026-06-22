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

  // Fetch role from backend — returns the resolved role
  const fetchUserRole = useCallback(async (currentUser): Promise<string> => {
    let resolvedRole = 'manager';
    try {
      const data = await apiJson('/api/users/me');
      resolvedRole = data.role || 'manager';
      setRole(resolvedRole);
      setDepartmentId(data.department_id ?? null);
      setDepartmentName(data.department_name ?? null);
      
      // Also create/update user profile with email if available
      if (currentUser?.email) {
        try {
          await apiJson('/api/users/me/profile', {
            method: 'POST',
            body: JSON.stringify({
              email: currentUser.email,
              display_name: currentUser.email
            })
          });
        } catch (error) {
          // Profile creation is optional, don't fail if it doesn't work
          console.log('Profile creation skipped:', error.message);
        }
      }
      
      // Cache role so next load is instant
      try {
        localStorage.setItem('saas.user.role.v1', JSON.stringify({
          role: resolvedRole,
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
          resolvedRole = parsed.role || 'manager';
          setRole(resolvedRole);
          setDepartmentId(parsed.department_id ?? null);
          setDepartmentName(parsed.department_name ?? null);
          return resolvedRole;
        }
      } catch { /* ignore */ }
      setRole('manager');
    }
    return resolvedRole;
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
          let roleResolved = false;
          let cachedRole = 'manager';
          try {
            const cached = localStorage.getItem('saas.user.role.v1');
            if (cached) {
              const parsed = JSON.parse(cached);
              cachedRole = parsed.role || 'manager';
              setRole(cachedRole);
              setDepartmentId(parsed.department_id ?? null);
              setDepartmentName(parsed.department_name ?? null);
              roleResolved = true;
            }
          } catch { /* ignore */ }
          
          // Always fetch fresh role, but only block UI if no cache
          if (roleResolved) {
            // Cache found — UI can render immediately with correct role
            setLoading(false);
            // Fetch fresh role in background to update if needed (non-blocking)
            fetchUserRole(session.user);
          } else {
            // No cache — fetch role before allowing UI to render
            fetchUserRole(session.user).then(() => {
              setLoading(false);
            }).catch(() => {
              setLoading(false);
            });
          }
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
          }
          // Always refresh role on auth change — block UI until role is resolved
          try {
            await fetchUserRole(session.user);
          } finally {
            setLoading(false);
          }
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
    refreshRole: () => user && fetchUserRole(user),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}
