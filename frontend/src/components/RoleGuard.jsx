import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../lib/authContext';

const RoleGuard = ({ allowedRoles, children, fallback = '/dashboard' }) => {
  const { role, loading } = useAuth();

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '60vh',
        color: 'var(--text-secondary)'
      }}>
        <p>Checking permissions...</p>
      </div>
    );
  }

  if (!role || !allowedRoles.includes(role)) {
    return <Navigate to={fallback} replace />;
  }

  return children;
};

export default RoleGuard;
