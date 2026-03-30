import React, { useState, useEffect } from 'react';
import { Database, Bell, Save, CheckCircle, RefreshCw, Info } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

const Settings = () => {
  const [dbStatus, setDbStatus] = useState('untested');
  const [theme, setTheme] = useState(localStorage.getItem('saas-theme') || 'dark');
  const [syncTime, setSyncTime] = useState(localStorage.getItem('saas-sync-time') || '02:00');
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState(null);
  
  // Form State
  const [dbType, setDbType] = useState('postgresql');
  const [host, setHost] = useState('');
  const [port, setPort] = useState('5432');
  const [dbName, setDbName] = useState('');
  const [dbUser, setDbUser] = useState('');
  const [dbPass, setDbPass] = useState('');

  useEffect(() => {
    const fetchUserAndSettings = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        setUser(session.user);
        
        // Fetch existing connection
        const { data, error } = await supabase
          .from('database_connections')
          .select('*')
          .eq('user_id', session.user.id)
          .single();
        
        if (data) {
          setDbType(data.db_type);
          setHost(data.host);
          setPort(data.port.toString());
          setDbName(data.db_name);
          // Note: We don't fetch password/credentials for security, 
          // usually they are just re-entered or left blank to keep current
        }
      }
    };
    fetchUserAndSettings();
  }, []);

  const handleSyncTimeChange = (e) => {
    const newTime = e.target.value;
    setSyncTime(newTime);
    localStorage.setItem('saas-sync-time', newTime);
    console.log(`[API] Rescheduling nightly sync to ${newTime}`);
  };

  const toggleTheme = (newTheme) => {
    setTheme(newTheme);
    localStorage.setItem('saas-theme', newTheme);
    if (newTheme === 'light') {
      document.documentElement.classList.add('light-theme');
    } else {
      document.documentElement.classList.remove('light-theme');
    }
  };

  const handleSaveSettings = async () => {
    if (!user) return;
    setLoading(true);
    
    // Construct credentials blob (Postgres URL format)
    const credentials = `postgresql://${dbUser}:${dbPass}@${host}:${port}/${dbName}`;
    
    const { error } = await supabase
      .from('database_connections')
      .upsert({
        user_id: user.id,
        db_type: dbType,
        host,
        port: parseInt(port),
        db_name: dbName,
        credentials: credentials,
        read_only: true
      }, { onConflict: 'user_id' });

    if (error) {
      alert(`Error saving settings: ${error.message}`);
    } else {
      setDbStatus('success');
      setTimeout(() => setDbStatus('untested'), 3000);
    }
    setLoading(false);
  };

  const handleTriggerManualRefresh = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/etl/trigger?user_id=${user.id}`, {
        method: 'POST'
      });
      const data = await response.json();
      alert("Manual ETL batch triggered successfully! Your dashboard will update in a few moments.");
    } catch (err) {
      alert(`Failed to trigger ETL: ${err.message}`);
    }
    setLoading(false);
  };

  const testConnection = async (e) => {
    e.preventDefault();
    setDbStatus('testing');
    
    // Construct credentials blob (Postgres URL format)
    const credentials = `postgresql://${dbUser}:${dbPass}@${host}:${port}/${dbName}`;
    
    try {
      const response = await fetch('http://localhost:8000/api/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credentials })
      });
      const data = await response.json();
      
      if (data.status === 'success') {
        setDbStatus('success');
      } else {
        setDbStatus('error');
        alert(`Connection test failed: ${data.message}`);
      }
    } catch (err) {
      setDbStatus('error');
      alert(`Network error testing connection: ${err.message}`);
    }
  };

  return (
    <div className="settings dashboard-grid" style={{ gridTemplateColumns: '1fr 1fr', alignItems: 'start' }}>
      
      {/* Database Settings Section */}
      <section className="glass-panel">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
          <Database color="var(--primary-color)" /> Database Connection
        </h2>
        
        <div style={{ background: 'rgba(79, 70, 229, 0.1)', padding: '15px', borderRadius: '8px', marginBottom: '20px', fontSize: '0.85rem', borderLeft: '4px solid var(--primary-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '5px', fontWeight: 'bold' }}>
            <Info size={16} /> Connection Tip
          </div>
          To connect another Supabase DB (like <strong>Analytix360</strong>), go to your Supabase Project Settings &gt; Database &gt; Connection String and copy the <strong>URI</strong>.
        </div>

        <form onSubmit={testConnection}>
          <div className="form-group">
            <label>Database Type</label>
            <select value={dbType} onChange={(e) => setDbType(e.target.value)}>
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL / MariaDB</option>
              <option value="sqlite">SQLite</option>
              <option value="sqlserver">Microsoft SQL Server</option>
            </select>
          </div>
          
          <div className="form-group">
            <label>Host URL or IP</label>
            <input 
              type="text" 
              placeholder="e.g. db.jtbyxbdkhmbzivzuaekz.supabase.co" 
              value={host}
              onChange={(e) => setHost(e.target.value)}
            />
          </div>
          
          <div style={{ display: 'flex', gap: '16px' }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Port</label>
              <input 
                type="number" 
                placeholder="5432" 
                value={port}
                onChange={(e) => setPort(e.target.value)}
              />
            </div>
            <div className="form-group" style={{ flex: 2 }}>
              <label>Database Name</label>
              <input 
                type="text" 
                placeholder="e.g. postgres" 
                value={dbName}
                onChange={(e) => setDbName(e.target.value)}
              />
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '16px' }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>User</label>
              <input 
                type="text" 
                placeholder="postgres" 
                value={dbUser}
                onChange={(e) => setDbUser(e.target.value)}
              />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Password</label>
              <input 
                type="password" 
                placeholder="••••••••" 
                value={dbPass}
                onChange={(e) => setDbPass(e.target.value)}
              />
            </div>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '16px' }}>
            <button type="submit" className="btn btn-outline" style={{ display: 'flex', gap: '8px' }}>
              Test Connection
            </button>
            <button 
              type="button" 
              className="btn btn-primary" 
              style={{ display: 'flex', gap: '8px' }}
              onClick={handleSaveSettings}
              disabled={loading}
            >
              <Save size={18} /> {loading ? 'Saving...' : 'Save credentials'}
            </button>
          </div>
          
          {dbStatus === 'testing' && (
            <div style={{ marginTop: '16px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Testing connection to host...</div>
          )}
          {dbStatus === 'success' && (
            <div style={{ marginTop: '16px', color: 'var(--status-normal)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle size={16} /> Settings saved and connection verified!
            </div>
          )}
        </form>
      </section>

      {/* Notification Preferences Section */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <section className="glass-panel">
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
            <Bell color="var(--primary-color)" /> Notification Preferences
          </h2>
          
          <div className="form-group">
            <label>Daily Briefing Delivery Time</label>
            <select defaultValue="07:00">
              <option value="06:00">6:00 AM Local Time</option>
              <option value="07:00">7:00 AM Local Time</option>
              <option value="08:00">8:00 AM Local Time</option>
              <option value="09:00">9:00 AM Local Time</option>
            </select>
          </div>
          
          <div className="form-group">
            <label>Additional Email Recipients</label>
            <textarea 
              rows={3} 
              placeholder="Enter one email per line (e.g. vp@company.com)"
              defaultValue=""
            ></textarea>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>These users will receive the daily AI briefing.</span>
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
            <button className="btn btn-primary">Update Preferences</button>
          </div>
        </section>

        {/* Sync Controls */}
        <section className="glass-panel">
          <h3 style={{ marginBottom: '16px' }}>System Controls</h3>
          <div className="form-group">
            <label>Automated Sync Time (Nightly)</label>
            <input 
              type="time" 
              value={syncTime} 
              onChange={handleSyncTimeChange}
              style={{ padding: '8px 12px' }}
            />
          </div>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            The ETL pipeline will process your data at this time every night.
          </p>
          <button 
            className="btn btn-outline" 
            style={{width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px'}}
            onClick={handleTriggerManualRefresh}
            disabled={loading}
          >
            <RefreshCw size={18} className={loading ? 'spin' : ''} />
            {loading ? 'Processing...' : 'Trigger Manual Refresh Batch'}
          </button>
        </section>

        {/* Appearance Settings Section */}
        <section className="glass-panel" style={{ marginBottom: '50px' }}>
          <h3 style={{ marginBottom: '16px' }}>App Appearance</h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Toggle between Dark Mode (Default) and Light Mode.
          </p>
          <div style={{ display: 'flex', gap: '16px' }}>
            <button 
              type="button" 
              className={`btn ${theme === 'dark' ? 'btn-primary' : 'btn-outline'}`}
              style={{ flex: 1 }}
              onClick={() => toggleTheme('dark')}
            >
              Dark Mode
            </button>
            <button 
              type="button" 
              className={`btn ${theme === 'light' ? 'btn-primary' : 'btn-outline'}`}
              style={{ flex: 1 }}
              onClick={() => toggleTheme('light')}
            >
              Light Mode
            </button>
          </div>
        </section>
      </div>

    </div>
  );
};

export default Settings;
