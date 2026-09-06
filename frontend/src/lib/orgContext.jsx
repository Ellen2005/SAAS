import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { apiJson } from './api';

const OrgContext = createContext({ org: null, loading: true, refresh: () => {} });

export function OrgProvider({ children }) {
  const [org, setOrg] = useState(() => {
    try { return JSON.parse(localStorage.getItem('saas.org.v1') || 'null'); } catch { return null; }
  });
  const [loading, setLoading] = useState(!org);

  const fetchOrg = useCallback(async () => {
    try {
      const data = await apiJson('/api/organizations/me', { safe: true });
      const o = data.organization || data.org || null;
      if (o) {
        setOrg(o);
        try { localStorage.setItem('saas.org.v1', JSON.stringify(o)); } catch {}
        // Apply theme as CSS vars
        if (o.primary_color) document.documentElement.style.setProperty('--org-primary', o.primary_color);
        if (o.secondary_color) document.documentElement.style.setProperty('--org-secondary', o.secondary_color);
      }
    } catch {
      // keep cached org, fallback to env branding
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchOrg(); }, [fetchOrg]);

  return <OrgContext.Provider value={{ org, loading, refresh: fetchOrg }}>{children}</OrgContext.Provider>;
}

export function useOrg() {
  return useContext(OrgContext);
}
