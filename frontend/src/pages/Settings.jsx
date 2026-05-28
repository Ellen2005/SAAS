import React, { useEffect, useMemo, useState } from 'react';
import { Bell, CheckCircle, Database, RefreshCw, Save, Workflow, Globe } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';
import { apiFetch, apiJson } from '../lib/api';
import { useAuth } from '../lib/authContext';
import { useNavigate } from 'react-router-dom';
import { useLang } from '../lib/i18n';

const DEFAULT_CONNECTION_OPTIONS = {
  tunnel_token: '',
  ssh_host: '',
  ssh_user: '',
  remote_db_host: '',
  docker_enabled: false,
};

const Settings = () => {
  const { user, departmentName } = useAuth();
  const { t, lang, setLang } = useLang();
  const navigate = useNavigate();
  const [savingConnection, setSavingConnection] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [savingPreferences, setSavingPreferences] = useState(false);
  const [triggeringSync, setTriggeringSync] = useState(false);
  const [dbStatus, setDbStatus] = useState('idle');
  const [connectionMethod, setConnectionMethod] = useState('direct');
  const [connectionOptions, setConnectionOptions] = useState(DEFAULT_CONNECTION_OPTIONS);

  const [dbType, setDbType] = useState('postgresql');
  const [host, setHost] = useState('');
  const [port, setPort] = useState('5432');
  const [dbName, setDbName] = useState('');
  const [dbUser, setDbUser] = useState('');
  const [dbPass, setDbPass] = useState('');
  const [directUri, setDirectUri] = useState('');

  const [aiTone, setAiTone] = useState('insight-driven');
  const [analysisInstruction, setAnalysisInstruction] = useState('');
  const [recipients, setRecipients] = useState('');
  const [syncTime, setSyncTime] = useState('06:00');
  const [syncFreq, setSyncFreq] = useState('weekly');
  const [yearlyDate, setYearlyDate] = useState('01-01');

  const [templateData, setTemplateData] = useState({ template: null, fields: [], mappings: [], department: null });
  const [mappingStatus, setMappingStatus] = useState({ valid: true, missing_required: [], missing_optional: [] });
  const [mappingInputs, setMappingInputs] = useState({});
  const [savingMapId, setSavingMapId] = useState(null);

  const mappedFieldIds = useMemo(
    () => new Map((templateData.mappings || []).map((mapping) => [mapping.template_field_id, mapping])),
    [templateData.mappings]
  );

  const [themeMode, setThemeMode] = useState(() => {
    try {
      return localStorage.getItem('saas.theme') || 'dark';
    } catch {
      return 'dark';
    }
  });

  useEffect(() => {
    try {
      document.documentElement.classList.toggle('light-theme', themeMode === 'light');
      localStorage.setItem('saas.theme', themeMode);
    } catch {
      // Ignore when localStorage is unavailable.
    }
  }, [themeMode]);

  const [accountLoading, setAccountLoading] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [accountMessage, setAccountMessage] = useState(null);

  useEffect(() => {
    const loadSettings = async () => {
      if (!user) return;

      try {
        // Batch all database queries in parallel instead of sequential
        const [connResp, recResp, preferenceData, semanticData, mappingValidation] = await Promise.all([
          supabase.from('database_connections').select('*').eq('user_id', user.id).maybeSingle(),
          supabase.from('notification_recipients').select('email').eq('user_id', user.id),
          apiJson('/api/settings/preferences'),
          apiJson('/api/semantic/my-template'),
          apiJson('/api/semantic/mappings/validate'),
        ]);

        const connectionData = connResp.data;
        const recipientData = recResp.data;

        if (connectionData) {
          setDbType(connectionData.db_type || 'postgresql');
          setHost(connectionData.host || '');
          setPort(String(connectionData.port || '5432'));
          setDbName(connectionData.db_name || '');
          setDirectUri(connectionData.credentials || '');
          setConnectionMethod(connectionData.connection_method || 'direct');
          setConnectionOptions({ ...DEFAULT_CONNECTION_OPTIONS, ...(connectionData.connection_options || {}) });
        }

        setAiTone(preferenceData.ai_tone || 'insight-driven');
        setSyncTime(preferenceData.sync_time || '06:00');
        setSyncFreq(preferenceData.sync_frequency || 'weekly');
        setYearlyDate(preferenceData.yearly_date || '01-01');
        setAnalysisInstruction(preferenceData.analysis_instruction || '');
        setRecipients((recipientData || []).map((row) => row.email).join('\n'));
        setTemplateData(semanticData);
        setMappingStatus(mappingValidation);

        const nextInputs = {};
        (semanticData.fields || []).forEach((field) => {
          const currentMapping = (semanticData.mappings || []).find((mapping) => mapping.template_field_id === field.id);
          nextInputs[field.id] = currentMapping?.local_column_name || '';
        });
        setMappingInputs(nextInputs);

      } catch (error) {
        console.error('Failed to load settings', error);
      }
    };

    loadSettings();
  }, [user]);

  const buildCredentialString = () => {
    if (directUri.trim()) return directUri.trim();
    const user = encodeURIComponent(dbUser.trim());
    const pass = encodeURIComponent(dbPass.trim());
    const hostPart = host.trim();
    const defaultPort = dbType === 'oracle' ? '1521' : '5432';
    const portPart = port.trim() || defaultPort;
    const dbPart = dbName.trim() || (dbType === 'oracle' ? 'orcl' : 'postgres');
    if (dbType === 'mongodb') {
      const auth = user ? `${user}:${pass}@` : '';
      return `mongodb://${auth}${hostPart}:${portPart}/${dbPart}`;
    }
    if (dbType === 'sqlite') {
      return `sqlite:///${dbPart.replace(/^\/+/, '')}`;
    }
    if (dbType === 'mysql') {
      return `mysql+pymysql://${user}:${pass}@${hostPart}:${portPart}/${dbPart}`;
    }
    if (dbType === 'sqlserver') {
      return `mssql+pymssql://${user}:${pass}@${hostPart}:${portPart}/${dbPart}`;
    }
    if (dbType === 'oracle') {
      return `oracle+oracledb://${user}:${pass}@${hostPart}:${portPart}/${dbPart}`;
    }
    return `postgresql+psycopg2://${user}:${pass}@${hostPart}:${portPart}/${dbPart}`;
  };

  const handleSaveConnection = async () => {
    setSavingConnection(true);
    try {
      await apiFetch('/api/settings/connection', {
        method: 'POST',
        body: JSON.stringify({
          db_type: dbType,
          host: host.trim(),
          port: Number(port) || 5432,
          db_name: dbName.trim(),
          credentials: buildCredentialString(),
          connection_method: connectionMethod,
          connection_options: connectionOptions,
        }),
      });
      setDbStatus('saved');
    } catch (error) {
      alert(`Unable to save connection: ${error.message}`);
      setDbStatus('error');
    } finally {
      setSavingConnection(false);
    }
  };

  const handleTestConnection = async (event) => {
    event.preventDefault();
    setDbStatus('testing');
    setTestingConnection(true);
    try {
      const result = await apiJson('/api/test-connection', {
        method: 'POST',
        body: JSON.stringify({
          db_type: dbType,
          credentials: buildCredentialString(),
          connection_method: connectionMethod,
          connection_options: connectionOptions,
          host: host.trim(),
          port: Number(port) || 5432,
          db_name: dbName.trim(),
        }),
      });
      setDbStatus(result.status === 'success' ? 'success' : 'error');
      if (result.status !== 'success') {
        alert(result.message);
      }
    } catch (error) {
      setDbStatus('error');
      alert(`Connection test failed: ${error.message}`);
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSavePreferences = async () => {
    setSavingPreferences(true);
    try {
      await apiFetch('/api/settings/preferences', {
        method: 'POST',
        body: JSON.stringify({
          ai_tone: aiTone,
          sync_time: syncTime,
          sync_frequency: syncFreq,
          yearly_date: yearlyDate,
          analysis_instruction: analysisInstruction,
        }),
      });

      await supabase.from('notification_recipients').delete().eq('user_id', user.id);
      const emails = recipients
        .split('\n')
        .map((email) => email.trim())
        .filter((email) => email.includes('@'));

      if (emails.length > 0) {
        await supabase.from('notification_recipients').insert(
          emails.map((email) => ({ user_id: user.id, email }))
        );
      }

      alert('Governed preferences updated.');
    } catch (error) {
      alert(`Unable to save preferences: ${error.message}`);
    } finally {
      setSavingPreferences(false);
    }
  };

  const handleManualSync = async () => {
    setTriggeringSync(true);
    try {
      await apiFetch('/api/etl/trigger', { method: 'POST' });
      alert('Department sync triggered. Please check the Dashboard for live progress.');
    } catch (error) {
      alert(`Unable to trigger sync: ${error.message}`);
    } finally {
      setTriggeringSync(false);
    }
  };

  const handleSaveMapping = async (fieldId) => {
    const localColumnName = (mappingInputs[fieldId] || '').trim();
    if (!localColumnName) return;

    setSavingMapId(fieldId);
    try {
      await apiFetch('/api/semantic/mappings', {
        method: 'POST',
        body: JSON.stringify({
          template_field_id: fieldId,
          local_column_name: localColumnName,
        }),
      });

      const [semanticData, mappingValidation] = await Promise.all([
        apiJson('/api/semantic/my-template'),
        apiJson('/api/semantic/mappings/validate'),
      ]);
      setTemplateData(semanticData);
      setMappingStatus(mappingValidation);
    } catch (error) {
      alert(`Unable to save mapping: ${error.message}`);
    } finally {
      setSavingMapId(null);
    }
  };

  const handleChangePassword = async () => {
    setAccountMessage(null);

    if (!newPassword || newPassword.length < 6) {
      setAccountMessage({ type: 'error', text: 'Password must be at least 6 characters.' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setAccountMessage({ type: 'error', text: 'Passwords do not match.' });
      return;
    }

    setAccountLoading(true);
    try {
      const { error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) throw error;
      setAccountMessage({ type: 'success', text: 'Password updated successfully.' });
      setNewPassword('');
      setConfirmPassword('');
    } catch (e) {
      setAccountMessage({ type: 'error', text: e.message || 'Unable to update password.' });
    } finally {
      setAccountLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirm('Delete your account? This cannot be undone.')) return;
    setAccountMessage(null);
    setAccountLoading(true);
    try {
      try {
        localStorage.removeItem('saas.dashboard.lastSummary.v1');
        localStorage.removeItem('saas.validation.lastLogs.v1');
      } catch {
        // Ignore when storage is unavailable.
      }
      await apiFetch('/api/account', { method: 'DELETE' });
      await supabase.auth.signOut();
      navigate('/login', { replace: true });
    } catch (e) {
      setAccountMessage({ type: 'error', text: e.message || 'Unable to delete account.' });
    } finally {
      setAccountLoading(false);
    }
  };

  return (
    <div style={{ display: 'grid', gap: '24px' }}>
      <header>
        <h1>{t('settings_title')}</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Governed configuration for {departmentName || templateData.department?.name || 'your department'}.
        </p>
      </header>

      <section className="glass-panel">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <Globe size={20} color="var(--primary-color)" /> {t('settings_language')}
        </h2>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-outline" onClick={() => setLang('en')}
            style={{ borderColor: lang === 'en' ? 'var(--primary-color)' : undefined, color: lang === 'en' ? 'var(--primary-color)' : undefined }}>
            🇬🇧 {t('lang_en')}
          </button>
          <button className="btn btn-outline" onClick={() => setLang('fr')}
            style={{ borderColor: lang === 'fr' ? 'var(--primary-color)' : undefined, color: lang === 'fr' ? 'var(--primary-color)' : undefined }}>
            🇫🇷 {t('lang_fr')}
          </button>
        </div>
      </section>

      <section className="glass-panel">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <Database size={20} color="var(--primary-color)" /> {t('settings_connection')}
        </h2>
        <form onSubmit={handleTestConnection}>
          <div className="form-group">
            <label>{t('settings_connection_method')}</label>
            <select value={connectionMethod} onChange={(event) => setConnectionMethod(event.target.value)}>
              <option value="direct">{t('settings_direct')}</option>
              <option value="cloudflare_tunnel">{t('settings_cloudflare')}</option>
              <option value="ssh_tunnel">{t('settings_ssh')}</option>
              <option value="docker_vpn">{t('settings_docker')}</option>
            </select>
          </div>

          {connectionMethod === 'cloudflare_tunnel' && (
            <div className="form-group">
              <label>Tunnel Token</label>
              <input
                value={connectionOptions.tunnel_token}
                onChange={(event) => setConnectionOptions({ ...connectionOptions, tunnel_token: event.target.value })}
                placeholder="Generated Cloudflare tunnel token"
              />
            </div>
          )}

          {connectionMethod === 'ssh_tunnel' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div className="form-group">
                <label>SSH Host</label>
                <input
                  value={connectionOptions.ssh_host}
                  onChange={(event) => setConnectionOptions({ ...connectionOptions, ssh_host: event.target.value })}
                  placeholder="bastion.company.com"
                />
              </div>
              <div className="form-group">
                <label>SSH User</label>
                <input
                  value={connectionOptions.ssh_user}
                  onChange={(event) => setConnectionOptions({ ...connectionOptions, ssh_user: event.target.value })}
                  placeholder="analytics"
                />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Remote DB Host</label>
                <input
                  value={connectionOptions.remote_db_host}
                  onChange={(event) => setConnectionOptions({ ...connectionOptions, remote_db_host: event.target.value })}
                  placeholder="db.internal"
                />
              </div>
            </div>
          )}

          {connectionMethod === 'docker_vpn' && (
            <div style={{ marginBottom: '16px', padding: '14px 16px', borderRadius: '12px', background: 'rgba(59,130,246,0.08)' }}>
              Docker mode is stored with this department profile so you can deliver the full stack behind VPN later.
            </div>
          )}

          <div className="form-group">
            <label>Direct URI</label>
            <textarea
              value={directUri}
              onChange={(event) => setDirectUri(event.target.value)}
              rows={3}
              placeholder="postgresql://postgres:[password]@db.project.supabase.co:5432/postgres"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="form-group">
              <label>{t('settings_db_type')}</label>
              <select value={dbType} onChange={(event) => setDbType(event.target.value)}>
                <option value="postgresql">PostgreSQL</option>
                <option value="mysql">MySQL</option>
                <option value="oracle">Oracle</option>
                <option value="mongodb">MongoDB</option>
                <option value="sqlite">SQLite</option>
                <option value="sqlserver">SQL Server</option>
              </select>
            </div>
            <div className="form-group">
              <label>Host</label>
              <input value={host} onChange={(event) => setHost(event.target.value)} placeholder="db.company.com" />
            </div>
            <div className="form-group">
              <label>Port</label>
              <input value={port} onChange={(event) => setPort(event.target.value)} placeholder="5432" />
            </div>
            <div className="form-group">
              <label>Database Name</label>
              <input value={dbName} onChange={(event) => setDbName(event.target.value)} placeholder="analytics" />
            </div>
            <div className="form-group">
              <label>User</label>
              <input value={dbUser} onChange={(event) => setDbUser(event.target.value)} placeholder="postgres" />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input type="password" value={dbPass} onChange={(event) => setDbPass(event.target.value)} placeholder="password" />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button className="btn btn-outline" type="submit" disabled={testingConnection}>
              {testingConnection ? 'Testing...' : 'Test Connection'}
            </button>
            <button className="btn btn-primary" type="button" onClick={handleSaveConnection} disabled={savingConnection}>
              <Save size={16} /> {savingConnection ? 'Saving...' : 'Save Connection'}
            </button>
            {dbStatus === 'testing' && <span style={{ color: 'var(--text-secondary)' }}>Checking database reachability...</span>}
            {dbStatus === 'success' && <span style={{ color: 'var(--status-normal)' }}>Connection verified.</span>}
            {dbStatus === 'saved' && <span style={{ color: 'var(--primary-color)' }}>Configuration saved.</span>}
            {dbStatus === 'error' && <span style={{ color: 'var(--status-critical)' }}>Connection failed. Review the values and try again.</span>}
          </div>
        </form>
      </section>

      <section className="glass-panel">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <Workflow size={20} color="var(--primary-color)" /> Semantic Mapping
        </h2>
        <p style={{ marginBottom: '16px' }}>
          Template: <strong>{templateData.template?.name || 'No semantic template assigned yet'}</strong>
        </p>

        {mappingStatus.valid ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: 'var(--status-normal)' }}>
            <CheckCircle size={16} /> Required mappings are complete.
          </div>
        ) : (
          <div style={{ marginBottom: '16px', color: 'var(--status-warning)' }}>
            Missing required mappings: {mappingStatus.missing_required.map((item) => item.name).join(', ')}
          </div>
        )}

        <div style={{ display: 'grid', gap: '12px' }}>
          {(templateData.fields || []).map((field) => {
            const currentMapping = mappedFieldIds.get(field.id);
            return (
              <div
                key={field.id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1.4fr 1fr auto',
                  gap: '12px',
                  alignItems: 'end',
                  padding: '14px',
                  borderRadius: '12px',
                  background: 'rgba(255,255,255,0.03)',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>
                    {field.global_field_name}
                    {field.required && <span style={{ color: 'var(--status-critical)', marginLeft: '6px' }}>*</span>}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{field.description || field.data_type}</div>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Local Column</label>
                  <input
                    value={mappingInputs[field.id] || ''}
                    onChange={(event) => setMappingInputs({ ...mappingInputs, [field.id]: event.target.value })}
                    placeholder={currentMapping?.local_column_name || 'e.g. total_sales'}
                  />
                </div>
                <button type="button" className="btn btn-outline" onClick={() => handleSaveMapping(field.id)} disabled={savingMapId === field.id}>
                  {savingMapId === field.id ? 'Saving...' : currentMapping ? 'Update' : 'Map'}
                </button>
              </div>
            );
          })}
        </div>
      </section>

      <section className="glass-panel">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <Bell size={20} color="var(--primary-color)" /> AI Narrative and Delivery
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div className="form-group">
            <label>AI Tone</label>
            <select value={aiTone} onChange={(event) => setAiTone(event.target.value)}>
              <option value="insight-driven">Insight-driven</option>
              <option value="formal">Formal</option>
            </select>
          </div>
          <div className="form-group">
            <label>Sync Frequency</label>
            <select value={syncFreq} onChange={(event) => setSyncFreq(event.target.value)}>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="yearly">Yearly</option>
            </select>
          </div>
          <div className="form-group">
            <label>Sync Time</label>
            <input type="time" value={syncTime} onChange={(event) => setSyncTime(event.target.value)} />
          </div>
          <div className="form-group">
            <label>Yearly Date</label>
            <input value={yearlyDate} onChange={(event) => setYearlyDate(event.target.value)} placeholder="01-01" />
          </div>
        </div>

        <div className="form-group">
          <label>Analysis Focus</label>
          <textarea
            rows={3}
            value={analysisInstruction}
            onChange={(event) => setAnalysisInstruction(event.target.value)}
            placeholder="Focus on revenue quality, margin risk, and missing data patterns."
          />
        </div>

        <div className="form-group">
          <label>Email Recipients</label>
          <textarea
            rows={3}
            value={recipients}
            onChange={(event) => setRecipients(event.target.value)}
            placeholder="dept-head@company.com"
          />
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button type="button" className="btn btn-primary" onClick={handleSavePreferences} disabled={savingPreferences}>
            <Save size={16} /> {savingPreferences ? 'Saving...' : 'Save Preferences'}
          </button>
          <button type="button" className="btn btn-outline" onClick={handleManualSync} disabled={triggeringSync}>
            <RefreshCw size={16} /> {triggeringSync ? 'Triggering...' : 'Trigger Sync Now'}
          </button>
        </div>
      </section>

      <section className="glass-panel">
        <h2 style={{ marginBottom: '16px' }}>Account Management</h2>

        <div style={{ display: 'grid', gap: '16px' }}>
          <div style={{ padding: '16px', border: '1px solid var(--border-color)', borderRadius: '12px', background: 'rgba(255,255,255,0.03)' }}>
            <h3 style={{ fontSize: '1rem', marginBottom: '12px' }}>Appearance</h3>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setThemeMode('light')}
                disabled={accountLoading}
                style={{ borderColor: themeMode === 'light' ? 'var(--primary-color)' : undefined }}
              >
                Light
              </button>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setThemeMode('dark')}
                disabled={accountLoading}
                style={{ borderColor: themeMode === 'dark' ? 'var(--primary-color)' : undefined }}
              >
                Dark
              </button>
            </div>
          </div>

          <div style={{ padding: '16px', border: '1px solid var(--border-color)', borderRadius: '12px', background: 'rgba(255,255,255,0.03)' }}>
            <h3 style={{ fontSize: '1rem', marginBottom: '12px' }}>Change Password</h3>
            <div style={{ display: 'grid', gap: '12px' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  placeholder="••••••••"
                  disabled={!user || accountLoading}
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Confirm Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  placeholder="••••••••"
                  disabled={!user || accountLoading}
                />
              </div>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                <button className="btn btn-primary" type="button" onClick={handleChangePassword} disabled={!user || accountLoading}>
                  {accountLoading ? 'Updating...' : 'Update Password'}
                </button>
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gap: '12px', padding: '16px', border: '1px solid rgba(239,68,68,0.35)', borderRadius: '12px', background: 'rgba(239,68,68,0.06)' }}>
            <h3 style={{ fontSize: '1rem', color: 'var(--status-critical)' }}>Delete Account</h3>
            <p style={{ color: 'var(--text-secondary)', marginTop: -6 }}>
              Deletes your Supabase user and all governed data tied to your account.
            </p>
            <button
              className="btn btn-outline"
              type="button"
              onClick={handleDeleteAccount}
              disabled={!user || accountLoading}
              style={{ borderColor: 'var(--status-critical)', color: 'var(--status-critical)' }}
            >
              {accountLoading ? 'Deleting...' : 'Delete My Account'}
            </button>
          </div>

          {accountMessage && (
            <div
              style={{
                padding: '12px 14px',
                borderRadius: '12px',
                border: `1px solid ${accountMessage.type === 'success' ? 'rgba(16,185,129,0.35)' : 'rgba(239,68,68,0.35)'}`,
                background: accountMessage.type === 'success' ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)',
                color: accountMessage.type === 'success' ? 'var(--status-normal)' : 'var(--status-critical)',
              }}
            >
              {accountMessage.text}
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

export default Settings;
