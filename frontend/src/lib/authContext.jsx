/* eslint react-refresh/only-export-components: off */
import React, { createContext, useContext, useState, useEffect, useCallback, useRef, useMemo } from 'react';
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
      localStorage.removeItem('saas.dashboard.lastSummary.v2');
      localStorage.removeItem('saas.dashboard.metricsCache.v1');
      localStorage.removeItem('saas.validation.lastLogs.v1');
      localStorage.removeItem('saas.user.role.v1');
      localStorage.removeItem('dashboard_layout');
    } catch { /* ignore */ }
  }, []);

  const resetAuthState = useCallback(() => {
    clearCache();
    setUser(null);
    setRole(null);
    setDepartmentId(null);
    setDepartmentName(null);
    setLoading(false);
  }, [clearCache]);

  const fetchUserRole = useCallback(async (currentUser) => {
    let resolvedRole = 'viewer';
    try {
      const data = await apiJson('/api/users/me', { safe: true });
      resolvedRole = data.role || 'viewer';
      setRole(resolvedRole);
      setDepartmentId(data.department_id ?? null);
      setDepartmentName(data.department_name ?? null);

      if (currentUser?.email) {
        apiJson('/api/users/me/profile', {
          method: 'POST',
          body: JSON.stringify({ email: currentUser.email, display_name: currentUser.email }),
          safe: true,
        }).catch((err) => console.warn('Profile sync failed:', err));
      }

      try {
        localStorage.setItem('saas.user.role.v1', JSON.stringify({
          role: resolvedRole,
          department_id: data.department_id,
          department_name: data.department_name,
        }));
      } catch { /* ignore */ }
    } catch {
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
      setRole('viewer');
    }
    return resolvedRole;
  }, []);

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    const forceUnblock = setTimeout(() => setLoading(false), 5000);

    // Restore cached role immediately to avoid nav flash
    try {
      const cached = localStorage.getItem('saas.user.role.v1');
      if (cached) {
        const parsed = JSON.parse(cached);
        setRole(parsed.role || 'viewer');
        setDepartmentId(parsed.department_id ?? null);
        setDepartmentName(parsed.department_name ?? null);
      }
    } catch { /* ignore */ }

    // Register onAuthStateChange BEFORE getSession so no events are missed.
    // This is the fix for the login redirect bug:
    // Previously onAuthStateChange awaited supabase.auth.getUser() before
    // calling setUser(), so user stayed null while the async call was in-flight.
    // The Login page called navigate('/dashboard') but App.jsx bounced it back
    // to /login because user was still null. Now we set user immediately from
    // the session object — Supabase already validated it when issuing the token.
    const authHandledByEvent = { current: false };

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (event === 'SIGNED_OUT') {
          resetAuthState();
          return;
        }
        if (session?.user) {
          authHandledByEvent.current = true;
          setUser(session.user);
          setLoading(false);
          fetchUserRole(session.user).catch(() => {});
        } else {
          resetAuthState();
        }
      }
    );

    // Check for an existing session on mount (page refresh / returning user)
    supabase.auth.getSession()
      .then(async ({ data: { session } }) => {
        if (authHandledByEvent.current) return;

        if (session?.user) {
          // Validate the stored session is still live (catches revoked refresh tokens)
          try {
            const { data: { user: validatedUser }, error } = await supabase.auth.getUser(session.access_token);
            if (error || !validatedUser) throw error || new Error('No user');
            setUser(validatedUser);
          } catch (err) {
            // Distinguish network errors from real auth errors so offline users
            // are not forcibly signed out and can still browse cached data.
            const msg = (err?.message || '').toLowerCase();
            const isNetworkError = !navigator.onLine
              || err?.name === 'TypeError'
              || msg.includes('fetch')
              || msg.includes('network')
              || msg.includes('failed to fetch');

            if (isNetworkError) {
              // Keep the cached session — OfflineBanner will alert the user
              setUser(session.user);
            } else {
              console.warn('Stale session detected, clearing auth state');
              await supabase.auth.signOut();
              resetAuthState();
              clearTimeout(forceUnblock);
              setLoading(false);
              return;
            }
          }
          // Ensure role is loaded even if onAuthStateChange hasn't fired yet (race on cold refresh)
          fetchUserRole(session.user).catch(() => {});
        } else {
          resetAuthState();
        }
      })
      .catch(() => resetAuthState())
      .finally(() => {
        clearTimeout(forceUnblock);
        setLoading(false);
      });

    return () => {
      clearTimeout(forceUnblock);
      subscription?.unsubscribe();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const refreshRole = useCallback(() => {
    if (user) return fetchUserRole(user);
  }, [user, fetchUserRole]);

  const value = useMemo(() => ({
    user,
    role,
    departmentId,
    departmentName,
    loading,
    isAdmin: role === 'admin',
    isManager: role === 'manager',
    isViewer: role === 'viewer',
    isManagerOrAbove: role === 'admin' || role === 'manager',
    refreshRole,
  }), [user, role, departmentId, departmentName, loading, refreshRole]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}