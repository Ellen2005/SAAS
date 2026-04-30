import { useEffect, useRef, useCallback } from 'react';
import { supabase } from '../lib/supabaseClient';

const INACTIVITY_MS = 60 * 60 * 1000;
const WARNING_MS = 55 * 60 * 1000;
const EVENTS = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'click'];

export function useInactivityTimeout(isAuthenticated) {
  const logoutTimer = useRef(null);
  const warnTimer = useRef(null);
  const warnShown = useRef(false);

  const clearTimers = useCallback(() => {
    clearTimeout(logoutTimer.current);
    clearTimeout(warnTimer.current);
  }, []);

  const resetTimers = useCallback(() => {
    if (!isAuthenticated) return;
    clearTimers();
    warnShown.current = false;

    warnTimer.current = setTimeout(() => {
      if (!warnShown.current) {
        warnShown.current = true;
        window.dispatchEvent(new CustomEvent('saas:inactivity-warning'));
      }
    }, WARNING_MS);

    logoutTimer.current = setTimeout(async () => {
      try {
        localStorage.removeItem('saas.dashboard.lastSummary.v1');
        localStorage.removeItem('saas.validation.lastLogs.v1');
      } catch {
        // ignore
      }
      await supabase.auth.signOut();
    }, INACTIVITY_MS);
  }, [isAuthenticated, clearTimers]);

  useEffect(() => {
    if (!isAuthenticated) {
      clearTimers();
      return;
    }
    resetTimers();
    EVENTS.forEach((e) => window.addEventListener(e, resetTimers, { passive: true }));
    return () => {
      clearTimers();
      EVENTS.forEach((e) => window.removeEventListener(e, resetTimers));
    };
  }, [isAuthenticated, resetTimers, clearTimers]);
}
