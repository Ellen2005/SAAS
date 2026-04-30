import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../lib/authContext';

const RoleGuard = ({ allowedRoles, children, fallback = '/dashboard' }) => {
  const { role, loading } = useAuth();

  // While role is loading, render children optimistically if we have a cached role,
  // otherwise show nothing (avoids flash of wrong content)
  if (loading) return null;

  if (!role || !allowedRoles.includes(role)) {
    return <Navigate to={fallback} replace />;
  }

  return children;
};

export default RoleGuard;
