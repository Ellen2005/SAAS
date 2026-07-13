/**
 * Shared utility for invalidating dashboard cache and triggering refresh.
 * Used by Settings, Schema Explorer, Analysis, and Dashboard pages.
 */
export function invalidateDashboardCache() {
  try {
    localStorage.removeItem('saas.dashboard.lastSummary.v2');
    localStorage.removeItem('saas.dashboard.metricsCache.v1');
  } catch { /* noop */ }
  window.dispatchEvent(new CustomEvent('dashboard:refresh'));
}
