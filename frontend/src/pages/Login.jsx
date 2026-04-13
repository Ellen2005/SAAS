import React, { useState } from 'react';
import { Activity, LogIn, Lock, User, Eye, EyeOff, UserPlus } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

const Login = () => {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [showReset, setShowReset] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetLoading, setResetLoading] = useState(false);
  const [resetMessage, setResetMessage] = useState(null);

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResetMessage(null);

    if (isSignUp && password !== confirmPassword) {
      setError("Passwords do not match.");
      setLoading(false);
      return;
    }

    if (!import.meta.env.VITE_SUPABASE_URL || import.meta.env.VITE_SUPABASE_URL === 'MOCK_URL') {
      setError("Frontend is in Mock Mode. Please set VITE_SUPABASE_URL in your .env to continue.");
      setLoading(false);
      return;
    }

    try {
      let result;
      if (isSignUp) {
        result = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: { name }
          }
        });
      } else {
        result = await supabase.auth.signInWithPassword({
          email,
          password,
        });
      }

      if (result.error) throw result.error;
      // AuthProvider will detect the auth state change and redirect
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    if (e?.preventDefault) e.preventDefault();
    setResetLoading(true);
    setResetMessage(null);
    try {
      const { error: resetError } = await supabase.auth.resetPasswordForEmail(resetEmail || email, {
        redirectTo: `${window.location.origin}/login`,
      });
      if (resetError) throw resetError;
      setResetMessage('If the email exists, you will receive a reset link shortly.');
      setShowReset(false);
    } catch (err) {
      setResetMessage(err.message || 'Unable to send reset email.');
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <div
      className="login-page"
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'var(--bg-color)',
        padding: '20px'
      }}
    >
      <div className="glass-panel" style={{ width: '100%', maxWidth: '400px', textAlign: 'center' }}>
        <div style={{ display: 'inline-flex', background: 'var(--primary-color)', padding: '12px', borderRadius: '12px', marginBottom: '20px' }}>
          <Activity color="white" size={32} />
        </div>
        <h1 style={{ fontSize: '1.8rem', marginBottom: '10px' }}>
          {isSignUp ? 'Create your Account' : 'Welcome to SAAS'}
        </h1>
        <p style={{ marginBottom: '30px' }}>
          {isSignUp ? 'Sign up to start your automated analytics.' : 'Enter your credentials to access the analytics dashboard.'}
        </p>

        {error && (
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--status-critical)', padding: '10px', borderRadius: '8px', marginBottom: '20px', fontSize: '0.9rem' }}>
            {error}
          </div>
        )}

        <div style={{ marginBottom: '18px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Continue with email and password</div>

        <form onSubmit={handleAuth}>
          {isSignUp && (
            <div className="form-group" style={{ textAlign: 'left' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <UserPlus size={16} /> Name
              </label>
              <input
                type="text"
                placeholder="Department or Username"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
          )}

          <div className="form-group" style={{ textAlign: 'left' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <User size={16} /> Email Address
            </label>
            <input
              type="email"
              placeholder="name@company.com"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ textAlign: 'left', position: 'relative' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Lock size={16} /> Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ paddingRight: '45px' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {!isSignUp && (
            <div style={{ textAlign: 'left', marginTop: '-8px', marginBottom: '10px' }}>
              <button
                type="button"
                onClick={() => {
                  setResetEmail(email);
                  setResetMessage(null);
                  setShowReset(true);
                }}
                disabled={loading}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--primary-color)',
                  fontWeight: 600,
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                Forgot password?
              </button>
            </div>
          )}

          {!isSignUp && showReset && (
            <div style={{ textAlign: 'left', marginBottom: '14px', padding: '12px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)' }}>
              <div style={{ marginBottom: '10px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                Enter your email and we will send a reset link.
              </div>
              <input
                type="email"
                placeholder="name@company.com"
                required
                value={resetEmail}
                onChange={(e) => setResetEmail(e.target.value)}
                style={{ marginBottom: '12px' }}
              />
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => handleResetPassword()}
                disabled={resetLoading}
                style={{ width: '100%' }}
              >
                {resetLoading ? 'Sending...' : 'Send reset email'}
              </button>
              {resetMessage && (
                <div style={{ marginTop: '10px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                  {resetMessage}
                </div>
              )}
            </div>
          )}

          {isSignUp && (
            <div className="form-group" style={{ textAlign: 'left' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Lock size={16} /> Confirm Password
              </label>
              <input
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '10px', display: 'flex', gap: '10px', justifyContent: 'center' }}
            disabled={loading}
          >
            {loading ? 'Processing...' : (
              isSignUp ? <><UserPlus size={18} /> Sign Up</> : <><LogIn size={18} /> Sign In</>
            )}
          </button>
        </form>

        <p style={{ marginTop: '20px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
          {isSignUp ? 'Already have an account?' : "Don't have an account?"}
          <button
            onClick={() => { setIsSignUp(!isSignUp); setError(null); }}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--primary-color)',
              fontWeight: '600',
              cursor: 'pointer',
              marginLeft: '8px'
            }}
          >
            {isSignUp ? 'Sign In' : 'Sign Up'}
          </button>
        </p>
      </div>
    </div>
  );
};

export default Login;
