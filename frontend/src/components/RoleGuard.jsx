import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../lib/authContext';

const RoleGuard = ({ allowedRoles, children, fallback = '/dashboard' }) => {
  const { role, loading } = useAuth();

  if (loading && !role) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '40vh', color: 'var(--ea-text-secondary, #9ca3af)' }}>
        <div style={{ width: '28px', height: '28px', border: '3px solid var(--border-color, #374151)', borderTopColor: 'var(--primary-color, #6366f1)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
      </div>
    );
  }

  if (!role || !allowedRoles.includes(role)) {
    return <Navigate to={fallback} replace />;
  }

  return children;
};

export default RoleGuard;
