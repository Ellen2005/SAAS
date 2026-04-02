/* eslint react-refresh/only-export-components: off */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { supabase } from './supabaseClient';
import { apiJson } from './api';

const AuthContext = createContext(null);
const AUTH_INIT_TIMEOUT_MS = 8000;

function withTimeout(promise, timeoutMs, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`${label} timed out after ${timeoutMs}ms`)), timeoutMs)
    ),
  ]);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [departmentId, setDepartmentId] = useState(null);
  const [departmentName, setDepartmentName] = useState(null);
  const [loading, setLoading] = useState(true);

  const resetAuthState = useCallback(() => {
    // Clear app-specific cached data when the user is signed out.
    // This prevents offline-stored sensitive data from being shown after logout/expiry.
    try {
      localStorage.removeItem('saas.dashboard.lastSummary.v1');
      localStorage.removeItem('saas.validation.lastLogs.v1');
    } catch {
      // Ignore when storage is unavailable.
    }
    setUser(null);
    setRole(null);
    setDepartmentId(null);
    setDepartmentName(null);
  }, []);

  const fetchUserRole = useCallback(async () => {
    try {
      const data = await apiJson('/api/users/me');
      setRole(data.role || 'manager');
      setDepartmentId(data.department_id);
      setDepartmentName(data.department_name);
    } catch (err) {
      console.error("Error fetching user role:", err);
      setRole('manager'); // Default fallback
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const { data: { session } } = await withTimeout(
          supabase.auth.getSession(),
          AUTH_INIT_TIMEOUT_MS,
          'Supabase session lookup'
        );

        if (session?.user) {
          setUser(session.user);
          await fetchUserRole();
        } else {
          resetAuthState();
        }
      } catch (err) {
        console.error('Auth initialisation failed:', err);
        resetAuthState();
      } finally {
        setLoading(false);
      }
    };

    initAuth();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        try {
          if (session?.user) {
            setUser(session.user);
            await fetchUserRole();
          } else {
            resetAuthState();
          }
        } catch (err) {
          console.error('Auth state change handling failed:', err);
          resetAuthState();
        } finally {
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
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
