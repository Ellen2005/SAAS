export const readCache = (key) => {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
};

export const writeCache = (key, payload) => {
  try { localStorage.setItem(key, JSON.stringify(payload)); } catch { /* noop */ }
};

export const removeCache = (...keys) => {
  try { keys.forEach((k) => localStorage.removeItem(k)); } catch { /* noop */ }
};

export const DASHBOARD_CACHE_KEY = 'saas.dashboard.lastSummary.v2';
export const METRICS_CACHE_KEY = 'saas.dashboard.metricsCache.v1';
export const VALIDATION_CACHE_KEY = 'saas.validation.lastLogs.v1';
export const ROLE_CACHE_KEY = 'saas.user.role.v1';
export const LAYOUT_CACHE_KEY = 'dashboard_layout';
