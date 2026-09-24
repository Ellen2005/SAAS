import React, { useState, useEffect, useRef } from 'react';
import { Activity, LogIn, Lock, User, Eye, EyeOff, UserPlus, ArrowRight, BarChart2, Shield, Zap } from 'lucide-react';
import { useNavigate, Link } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import { useLang } from '../lib/i18n';
import { useAuth } from '../lib/authContext';
import { useOrg } from '../lib/orgContext';
import LanguagePicker from '../components/LanguagePicker';
import useIsMobile from '../hooks/useIsMobile';

const Login = () => {
  const { t } = useLang();
  const { user } = useAuth();
  const { org } = useOrg();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showLangPicker, setShowLangPicker] = useState(false);
  const [showReset, setShowReset] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetLoading, setResetLoading] = useState(false);
  const [resetMessage, setResetMessage] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [touched, setTouched] = useState({});

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

  const validateEmail = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);

  const validateField = (field, value) => {
    switch (field) {
      case 'email': if (!value) return 'Email is required'; if (!validateEmail(value)) return 'Invalid email format'; return null;
      case 'password': if (!value) return 'Password is required'; if (value.length < 6) return 'At least 6 characters'; return null;
      case 'confirmPassword': if (!value) return 'Please confirm'; if (value !== password) return 'Passwords do not match'; return null;
      case 'name': if (isSignUp && !value) return 'Name is required'; return null;
      default: return null;
    }
  };

  const handleBlur = (field) => {
    setTouched(prev => ({ ...prev, [field]: true }));
    const val = field === 'confirmPassword' ? confirmPassword : field === 'password' ? password : field === 'email' ? email : name;
    setFieldErrors(prev => ({ ...prev, [field]: validateField(field, val) }));
  };

  const handleChange = (field, value) => {
    const setter = { email: setEmail, password: setPassword, confirmPassword: setConfirmPassword, name: setName }[field];
    if (setter) setter(value);
    if (touched[field]) {
      const val = field === 'confirmPassword' ? value : field === 'password' ? value : field === 'email' ? value : name;
      setFieldErrors(prev => ({ ...prev, [field]: validateField(field, val) }));
    }
  };

  useEffect(() => { if (user) navigate('/dashboard', { replace: true }); }, [user, navigate]);

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResetMessage(null);

    if (isSignUp && password !== confirmPassword) {
      setError('Passwords do not match.');
      setLoading(false);
      return;
    }
    if (!import.meta.env.VITE_SUPABASE_URL || import.meta.env.VITE_SUPABASE_URL === 'MOCK_URL') {
      setError('Frontend is in Mock Mode. Set VITE_SUPABASE_URL in .env to continue.');
      setLoading(false);
      return;
    }
    try {
      let result;
      if (isSignUp) {
        result = await supabase.auth.signUp({ email, password, options: { data: { name } } });
        if (!result.error) { setShowLangPicker(true); setLoading(false); }
      } else {
        result = await supabase.auth.signInWithPassword({ email, password });
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

  const inputStyle = {
    width: '100%', padding: '12px 14px', background: 'var(--ea-bg-card)',
    border: '1px solid var(--ea-border)', borderRadius: 10,
    color: 'var(--ea-text-primary)', fontSize: '0.95rem', outline: 'none',
    transition: 'border-color 0.2s, box-shadow 0.2s',
  };

  const labelStyle = {
    display: 'block', fontSize: '0.8rem', fontWeight: 600,
    color: 'var(--ea-text-secondary)', marginBottom: 6,
  };

  return (
    <>
      {showLangPicker && <LanguagePicker onClose={() => setShowLangPicker(false)} />}
      <div style={{
        display: 'flex', minHeight: '100vh', background: 'var(--ea-bg)',
      }}>
        {/* Left panel — branding (hidden on mobile) */}
        {!isMobile && (
          <div style={{
            flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center',
            padding: '60px 60px', background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
            position: 'relative', overflow: 'hidden',
          }}>
            {/* Glow */}
            <div style={{
              position: 'absolute', width: 500, height: 500, borderRadius: '50%',
              background: 'radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%)',
              top: '20%', left: '10%', animation: 'pulse 6s infinite alternate ease-in-out',
            }} />

            <div style={{ position: 'relative', zIndex: 1, maxWidth: 440 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 40 }}>
                <img src={org?.logo_url || '/logo.png'} alt="" style={{ width: 44, height: 44 }} />
                <span style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--ea-text-primary)' }}>
                  {org?.name || 'Smart Analytics'}
                </span>
              </div>

              <h1 style={{
                fontSize: '2.8rem', fontWeight: 800, lineHeight: 1.1, marginBottom: 20,
                background: 'linear-gradient(135deg, #f8fafc, #94a3b8)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              }}>
                Institutional Analytics Platform
              </h1>
              <p style={{ fontSize: '1.1rem', color: 'var(--ea-text-secondary)', lineHeight: 1.6, marginBottom: 40 }}>
                Automated insights, anomaly detection, and professional reporting — all in one platform.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {[
                  { icon: Zap, text: 'AI-powered executive narratives generated automatically', color: '#3b82f6' },
                  { icon: BarChart2, text: 'Statistical analysis with regression, forecasting, and correlation', color: '#10b981' },
                  { icon: Shield, text: 'Enterprise-grade security with role-based access control', color: '#f59e0b' },
                ].map(({ icon: Icon, text, color }, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: 10, flexShrink: 0,
                      background: `${color}18`, color, display: 'flex',
                      alignItems: 'center', justifyContent: 'center',
                    }}>
                      <Icon size={18} />
                    </div>
                    <span style={{ fontSize: '0.9rem', color: 'var(--ea-text-secondary)' }}>{text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Right panel — form */}
        <div style={{
          display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
          padding: isMobile ? '24px 20px' : '60px 48px',
          width: isMobile ? '100%' : 480, flexShrink: 0,
        }}>
          <div style={{ width: '100%', maxWidth: 380 }}>
            {/* Mobile-only brand */}
            {isMobile && (
              <div style={{ textAlign: 'center', marginBottom: 32 }}>
                <img src={org?.logo_url || '/logo.png'} alt="" style={{ width: 48, height: 48, marginBottom: 12 }} />
                <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--ea-text-primary)' }}>
                  {org?.name || 'Smart Analytics'}
                </h2>
              </div>
            )}

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--ea-text-primary)', marginBottom: 6 }}>
              {isSignUp ? 'Create your account' : 'Welcome back'}
            </h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--ea-text-muted)', marginBottom: 28 }}>
              {isSignUp ? 'Sign up to start your automated analytics.' : 'Sign in to access your analytics dashboard.'}
            </p>

            {error && (
              <div role="alert" style={{
                background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)',
                color: '#f87171', padding: '10px 14px', borderRadius: 10, marginBottom: 20,
                fontSize: '0.85rem',
              }}>
                {error}
              </div>
            )}

            <form onSubmit={handleAuth}>
              {isSignUp && (
                <div style={{ marginBottom: 16 }}>
                  <label style={labelStyle}>Full Name</label>
                  <input
                    type="text" placeholder="Department or Username" required
                    value={name} onChange={(e) => handleChange('name', e.target.value)}
                    onBlur={() => handleBlur('name')} style={inputStyle}
                  />
                  {touched.name && fieldErrors.name && <p style={{ color: '#f87171', fontSize: '0.75rem', marginTop: 4 }}>{fieldErrors.name}</p>}
                </div>
              )}

              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Email Address</label>
                <input
                  type="email" placeholder="name@company.com" required
                  value={email} onChange={(e) => handleChange('email', e.target.value)}
                  onBlur={() => handleBlur('email')} style={inputStyle} autoComplete="email"
                />
                {touched.email && fieldErrors.email && <p style={{ color: '#f87171', fontSize: '0.75rem', marginTop: 4 }}>{fieldErrors.email}</p>}
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••" required value={password}
                    onChange={(e) => handleChange('password', e.target.value)}
                    onBlur={() => handleBlur('password')}
                    style={{ ...inputStyle, paddingRight: 44 }}
                    autoComplete={isSignUp ? 'new-password' : 'current-password'}
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)}
                    style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--ea-text-muted)', cursor: 'pointer', display: 'flex' }}>
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {touched.password && fieldErrors.password && <p style={{ color: '#f87171', fontSize: '0.75rem', marginTop: 4 }}>{fieldErrors.password}</p>}
                {isSignUp && password && (() => {
                  const s = getPasswordStrength(password);
                  return (
                    <div style={{ marginTop: 6 }}>
                      <div style={{ display: 'flex', gap: 3, marginBottom: 4 }}>
                        {[1, 2, 3].map(i => (
                          <div key={i} style={{ flex: 1, height: 3, borderRadius: 2, background: i <= s.score ? s.color : 'var(--ea-border)' }} />
                        ))}
                      </div>
                      <span style={{ fontSize: '0.7rem', color: s.color }}>{s.label}</span>
                    </div>
                  );
                })()}
              </div>

              {!isSignUp && (
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
                  <button type="button" onClick={() => { setResetEmail(email); setResetMessage(null); setShowReset(true); }}
                    style={{ background: 'none', border: 'none', color: 'var(--ea-primary)', fontWeight: 600, cursor: 'pointer', padding: 0, fontSize: '0.85rem' }}>
                    {t('login_forgot')}
                  </button>
                </div>
              )}

              {!isSignUp && showReset && (
                <div style={{ marginBottom: 16, padding: 14, borderRadius: 10, border: '1px solid var(--ea-border)', background: 'var(--ea-bg-card)' }}>
                  <input type="email" placeholder="name@company.com" required value={resetEmail}
                    onChange={(e) => setResetEmail(e.target.value)} style={{ ...inputStyle, marginBottom: 10 }} />
                  <button type="button" className="btn btn-primary" onClick={handleResetPassword} disabled={resetLoading} style={{ width: '100%' }}>
                    {resetLoading ? 'Sending...' : t('login_reset_send')}
                  </button>
                  {resetMessage && <div style={{ marginTop: 8, color: 'var(--ea-text-secondary)', fontSize: '0.85rem' }}>{resetMessage}</div>}
                </div>
              )}

              {isSignUp && (
                <div style={{ marginBottom: 20 }}>
                  <label style={labelStyle}>Confirm Password</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      placeholder="••••••••" required value={confirmPassword}
                      onChange={(e) => handleChange('confirmPassword', e.target.value)}
                      onBlur={() => handleBlur('confirmPassword')}
                      style={{ ...inputStyle, paddingRight: 44 }} autoComplete="new-password"
                    />
                    <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--ea-text-muted)', cursor: 'pointer', display: 'flex' }}>
                      {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  {touched.confirmPassword && fieldErrors.confirmPassword && <p style={{ color: '#f87171', fontSize: '0.75rem', marginTop: 4 }}>{fieldErrors.confirmPassword}</p>}
                </div>
              )}

              <button type="submit" className="btn btn-primary" style={{
                width: '100%', padding: '13px 20px', fontSize: '0.95rem',
                display: 'flex', gap: 10, justifyContent: 'center', alignItems: 'center',
              }} disabled={loading}>
                {loading ? (
                  <div style={{ width: 18, height: 18, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
                ) : isSignUp ? (
                  <><UserPlus size={18} /> Create Account</>
                ) : (
                  <><LogIn size={18} /> Sign In</>
                )}
              </button>
            </form>

            <p style={{ marginTop: 24, fontSize: '0.85rem', color: 'var(--ea-text-muted)', textAlign: 'center' }}>
              {isSignUp ? 'Already have an account?' : "Don't have an account?"}
              <button onClick={() => { setIsSignUp(!isSignUp); setError(null); setTouched({}); setFieldErrors({}); }}
                style={{ background: 'none', border: 'none', color: 'var(--ea-primary)', fontWeight: 600, cursor: 'pointer', marginLeft: 6 }}>
                {isSignUp ? 'Sign In' : 'Sign Up'}
              </button>
            </p>

            <Link to="/" style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              marginTop: 20, fontSize: '0.8rem', color: 'var(--ea-text-muted)',
              textDecoration: 'none', transition: 'color 0.15s',
            }}>
              ← Back to home
            </Link>
          </div>
        </div>

        <style>{`
          @keyframes spin { to { transform: rotate(360deg); } }
          @keyframes pulse { from { transform: scale(0.9); opacity: 0.1; } to { transform: scale(1.1); opacity: 0.3; } }
          input:focus { border-color: var(--ea-primary) !important; box-shadow: 0 0 0 3px rgba(59,130,246,0.15); }
        `}</style>
      </div>
    </>
  );
};

export default Login;
