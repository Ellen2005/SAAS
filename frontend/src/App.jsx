import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import { Settings as SettingsIcon, LogOut } from 'lucide-react';
import { supabase } from './lib/supabaseClient';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Login from './pages/Login';
import Landing from './pages/Landing';
import './index.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Theme Initialisation
    const savedTheme = localStorage.getItem('saas-theme');
    if (savedTheme === 'light') {
      document.documentElement.classList.add('light-theme');
    }

    // Auth Initialisation
    checkUser();
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setUser(session?.user ?? null);
      }
    );

    return () => subscription?.unsubscribe();
  }, []);

  async function checkUser() {
    const { data: { session } } = await supabase.auth.getSession();
    setUser(session?.user ?? null);
    setLoading(false);
  }

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setUser(null);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'var(--bg-color)', color: 'var(--text-primary)' }}>
        <p>Initialising SAAS...</p>
      </div>
    );
  }

  return (
    <Router>
      <Routes>
        {/* Public Landing Page */}
        <Route path="/" element={user ? <Navigate to="/dashboard" /> : <Landing />} />
        
        {/* Auth Route */}
        <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <Login onLogin={setUser} />} />

        {/* Protected Dashboard Shell */}
        <Route 
          path="/*" 
          element={
            user ? (
              <div className="app-container">
                <nav className="navbar">
                  <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <img src="/logo.png" alt="SAAS logo" style={{ width: '32px', height: '32px' }} />
                    <h2 style={{ letterSpacing: '-0.05em' }}>SAAS</h2>
                  </div>
                  <div className="nav-links" style={{ display: 'flex', alignItems: 'center' }}>
                    <NavLink to="/dashboard" className={({ isActive }) => isActive ? "active" : ""}>
                      Dashboard
                    </NavLink>
                    <NavLink to="/settings" className={({ isActive }) => isActive ? "active" : ""}>
                      Settings
                    </NavLink>
                    <button 
                      onClick={handleLogout} 
                      className="btn btn-outline" 
                      style={{ padding: '8px 12px', marginLeft: '24px', fontSize: '0.8rem', display: 'flex', gap: '6px' }}
                    >
                      <LogOut size={14} /> Log Out
                    </button>
                  </div>
                </nav>
                
                <main style={{ padding: '32px', maxWidth: '1440px', margin: '0 auto' }}>
                  <Routes>
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/settings" element={<Settings />} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </main>
              </div>
            ) : (
              <Navigate to="/login" />
            )
          } 
        />
      </Routes>
    </Router>
  );
}

export default App;


