import React, { useState, useEffect, useRef } from 'react';
import { Activity, LogIn, Lock, User, Eye, EyeOff, UserPlus, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import { useLang } from '../lib/i18n';
import { useAuth } from '../lib/authContext';
import LanguagePicker from '../components/LanguagePicker';

const Login = () => {
  const { t } = useLang();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showLangPicker, setShowLangPicker] = useState(false);
  const [showReset, setShowReset] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetLoading, setResetLoading] = useState(false);
  const [resetMessage, setResetMessage] = useState(null);

  const [fieldErrors, setFieldErrors] = useState({});
  const [touched, setTouched] = useState({});
  const errorIdRef = useRef('login-error');
  const emailValidRef = useRef(false);

  const getPasswordStrength = (pwd) => {
    if (!pwd) return { score: 0, label: '', color: '' };
    let score = 0;
    if (pwd.length >= 8) score++;
    if (pwd.length >= 12) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/[a-z]/.test(pwd)) score++;
    if (/[0-9]/.test(pwd)) score++;
    if (/[^A-Za-z0-9]/.test(pwd)) score++;
    if (score <= 2) return { score: 1, label: 'Weak', color: '#ef4444' };
    if (score <= 4) return { score: 2, label: 'Fair', color: '#f59e0b' };
    return { score: 3, label: 'Strong', color: '#10b981' };
  };

  const validateEmail = (value) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(value);
  };

  const validateField = (field, value) => {
    switch (field) {
      case 'email':
        if (!value) return t('login_email') + ' is required';
        if (!validateEmail(value)) return 'Invalid email format';
        return null;
      case 'password':
        if (!value) return t('login_password') + ' is required';
        if (value.length < 6) return 'Password must be at least 6 characters';
        return null;
      case 'confirmPassword':
        if (!value) return 'Please confirm your password';
        if (value !== password) return 'Passwords do not match';
        return null;
      case 'name':
        if (isSignUp && !value) return t('login_name') + ' is required';
        return null;
      default:
        return null;
    }
  };

  const handleBlur = (field) => {
    setTouched(prev => ({ ...prev, [field]: true }));
    const err = validateField(field, field === 'confirmPassword' ? confirmPassword : 
      field === 'password' ? password : field === 'email' ? email : name);
    setFieldErrors(prev => ({ ...prev, [field]: err }));
  };

  const handleChange = (field, value) => {
    if (field === 'email') {
      setEmail(value);
      emailValidRef.current = validateEmail(value);
    } else if (field === 'password') {
      setPassword(value);
    } else if (field === 'confirmPassword') {
      setConfirmPassword(value);
    } else if (field === 'name') {
      setName(value);
    }
    if (touched[field]) {
      const err = validateField(field, field === 'confirmPassword' ? value : 
        field === 'password' ? value : field === 'email' ? value : name);
      setFieldErrors(prev => ({ ...prev, [field]: err }));
    }
  };

  useEffect(() => {
    if (user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResetMessage(null);

    if (isSignUp && password !== confirmPassword) {
      setError(t('login_confirm_password') + ' mismatch.');
      setLoading(false);
      return;
    }

    if (!import.meta.env.VITE_SUPABASE_URL || import.meta.env.VITE_SUPABASE_URL === 'MOCK_URL') {
      setError('Frontend is in Mock Mode. Please set VITE_SUPABASE_URL in your .env to continue.');
      setLoading(false);
      return;
    }

    try {
      let result;
      if (isSignUp) {
        result = await supabase.auth.signUp({ email, password, options: { data: { name } } });
        if (!result.error) {
          setShowLangPicker(true);
          setLoading(false);
        }
      } else {
        result = await supabase.auth.signInWithPassword({ email, password });
        // Do NOT call navigate() here — onAuthStateChange sets user state
        // immediately now, which triggers the <Navigate to="/dashboard"> in
        // App.jsx. Calling navigate() here as well caused a race where the
        // route guard saw user=null and bounced back to /login.
        // Clear loading so button returns to normal state even if navigation
        // is slightly delayed.
        setLoading(false);
      }
      if (result.error) throw result.error;
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleResetPassword = async () => {
    setResetLoading(true);
    setResetMessage(null);
    try {
      const { error: resetError } = await supabase.auth.resetPasswordForEmail(resetEmail || email, {
        redirectTo: `${window.location.origin}/login`,
      });
      if (resetError) throw resetError;
      setResetMessage(t('login_reset_sent'));
      setShowReset(false);
    } catch (err) {
      setResetMessage(err.message || 'Unable to send reset email.');
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <>
      {showLangPicker && <LanguagePicker onClose={() => setShowLangPicker(false)} />}
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: 'var(--bg-color)', padding: '20px' }}>
        <div className="glass-panel" style={{ width: '100%', maxWidth: '400px', textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', background: 'var(--primary-color)', padding: '12px', borderRadius: '12px', marginBottom: '20px' }}>
            <Activity color="white" size={32} />
          </div>
          <h1 style={{ fontSize: '1.8rem', marginBottom: '10px' }}>
            {isSignUp ? t('signup_title') : t('login_title')}
          </h1>
          <p style={{ marginBottom: '30px' }}>
            {isSignUp ? t('signup_subtitle') : t('login_subtitle')}
          </p>

          {error && (
            <div id={errorIdRef.current} role="alert" style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--status-critical)', padding: '10px', borderRadius: '8px', marginBottom: '20px', fontSize: '0.9rem' }}>
              {error}
            </div>
          )}

          <form onSubmit={handleAuth}>
            {isSignUp && (
              <div className="form-group" style={{ textAlign: 'left' }}>
                <label htmlFor="login-name" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <UserPlus size={16} /> {t('login_name')}
                </label>
                <input id="login-name" name="name" type="text" placeholder="Department or Username" required value={name} onChange={(e) => handleChange('name', e.target.value)} onBlur={() => handleBlur('name')} aria-invalid={touched.name && !!fieldErrors.name} aria-describedby={touched.name && fieldErrors.name ? 'name-error' : undefined} />
                {touched.name && fieldErrors.name && <p id="name-error" role="alert" style={{ color: 'var(--status-critical)', fontSize: '0.8rem', marginTop: '4px' }}>{fieldErrors.name}</p>}
              </div>
            )}

            <div className="form-group" style={{ textAlign: 'left' }}>
              <label htmlFor="login-email" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <User size={16} /> {t('login_email')}
              </label>
              <input id="login-email" name="email" type="email" placeholder="name@company.com" required value={email} onChange={(e) => handleChange('email', e.target.value)} onBlur={() => handleBlur('email')} autoComplete="email" aria-invalid={touched.email && !!fieldErrors.email} aria-describedby={touched.email && fieldErrors.email ? 'email-error' : undefined} />
              {touched.email && fieldErrors.email && <p id="email-error" role="alert" style={{ color: 'var(--status-critical)', fontSize: '0.8rem', marginTop: '4px' }}>{fieldErrors.email}</p>}
            </div>

            <div className="form-group" style={{ textAlign: 'left', position: 'relative' }}>
              <label htmlFor="login-password" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Lock size={16} /> {t('login_password')}
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  required
                  value={password}
                  onChange={(e) => handleChange('password', e.target.value)}
                  onBlur={() => handleBlur('password')}
                  style={{ paddingRight: '45px' }}
                  autoComplete={isSignUp ? 'new-password' : 'current-password'}
                  aria-invalid={touched.password && !!fieldErrors.password}
                  aria-describedby={touched.password && fieldErrors.password ? 'password-error' : undefined}
                />
                <button type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? 'Hide password' : 'Show password'}
                  style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {touched.password && fieldErrors.password && <p id="password-error" role="alert" style={{ color: 'var(--status-critical)', fontSize: '0.8rem', marginTop: '4px' }}>{fieldErrors.password}</p>}
              {isSignUp && password && (() => {
                const strength = getPasswordStrength(password);
                return (
                  <div style={{ marginTop: '6px' }}>
                    <div style={{ display: 'flex', gap: '3px', marginBottom: '4px' }}>
                      {[1, 2, 3].map(i => (
                        <div key={i} style={{ flex: 1, height: '3px', borderRadius: '2px', background: i <= strength.score ? strength.color : 'rgba(255,255,255,0.1)' }} />
                      ))}
                    </div>
                    <span style={{ fontSize: '0.7rem', color: strength.color }}>{strength.label}</span>
                  </div>
                );
              })()}
            </div>

            {!isSignUp && (
              <div style={{ textAlign: 'left', marginTop: '-8px', marginBottom: '10px' }}>
                <button type="button" onClick={() => { setResetEmail(email); setResetMessage(null); setShowReset(true); }}
                  style={{ background: 'none', border: 'none', color: 'var(--primary-color)', fontWeight: 600, cursor: 'pointer', padding: 0 }}>
                  {t('login_forgot')}
                </button>
              </div>
            )}

            {!isSignUp && showReset && (
              <div style={{ textAlign: 'left', marginBottom: '14px', padding: '12px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)' }}>
                <input id="reset-email" name="resetEmail" type="email" placeholder="name@company.com" required value={resetEmail} onChange={(e) => setResetEmail(e.target.value)} style={{ marginBottom: '12px', width: '100%' }} />
                <button type="button" className="btn btn-primary" onClick={handleResetPassword} disabled={resetLoading} style={{ width: '100%' }}>
                  {resetLoading ? t('login_processing') : t('login_reset_send')}
                </button>
                {resetMessage && <div style={{ marginTop: '10px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{resetMessage}</div>}
              </div>
            )}

            {isSignUp && (
              <div className="form-group" style={{ textAlign: 'left' }}>
                <label htmlFor="login-confirm-password" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Lock size={16} /> {t('login_confirm_password')}
                </label>
                <input id="login-confirm-password" name="confirmPassword" type={showPassword ? 'text' : 'password'} placeholder="••••••••" required value={confirmPassword} onChange={(e) => handleChange('confirmPassword', e.target.value)} onBlur={() => handleBlur('confirmPassword')} autoComplete="new-password" aria-invalid={touched.confirmPassword && !!fieldErrors.confirmPassword} aria-describedby={touched.confirmPassword && fieldErrors.confirmPassword ? 'confirm-error' : undefined} />
                {touched.confirmPassword && fieldErrors.confirmPassword && <p id="confirm-error" role="alert" style={{ color: 'var(--status-critical)', fontSize: '0.8rem', marginTop: '4px' }}>{fieldErrors.confirmPassword}</p>}
              </div>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '10px', display: 'flex', gap: '10px', justifyContent: 'center' }} disabled={loading}>
              {loading ? t('login_processing') : isSignUp ? <><UserPlus size={18} /> {t('signup_btn')}</> : <><LogIn size={18} /> {t('login_btn')}</>}
            </button>
          </form>

          <p style={{ marginTop: '20px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
            {isSignUp ? t('login_has_account') : t('login_no_account')}
            <button onClick={() => { setIsSignUp(!isSignUp); setError(null); }}
              style={{ background: 'none', border: 'none', color: 'var(--primary-color)', fontWeight: '600', cursor: 'pointer', marginLeft: '8px' }}>
              {isSignUp ? t('login_btn') : t('signup_btn')}
            </button>
          </p>
        </div>
      </div>
    </>
  );
};

export default Login;
