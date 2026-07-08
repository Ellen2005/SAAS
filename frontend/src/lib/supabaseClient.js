import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey || supabaseUrl === 'MOCK_URL') {
  console.warn("Supabase credentials missing or set to MOCK_URL. Authentication and live data may not function correctly.");
}

// Generate a stable per-tab ID so multiple tabs can hold independent sessions.
// sessionStorage persists across page refreshes within the same tab but is
// isolated between tabs, which is exactly what we need.
const TAB_ID_KEY = 'saas.tab.id';
let tabId = sessionStorage.getItem(TAB_ID_KEY);
if (!tabId) {
  tabId = Math.random().toString(36).slice(2, 10);
  sessionStorage.setItem(TAB_ID_KEY, tabId);
}

export const supabase = createClient(
  supabaseUrl || 'https://placeholder.supabase.co',
  supabaseAnonKey || 'placeholder-key',
  {
    auth: {
      storageKey: `sb-session-${tabId}`,
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  }
)

