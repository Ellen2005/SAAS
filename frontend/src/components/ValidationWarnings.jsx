import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle } from 'lucide-react';

const ValidationWarnings = ({ validations = [] }) => {
  if (!validations || validations.length === 0) return null;

  const allPassed = validations.every((validation) => validation.status === 'pass');
  if (allPassed) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '12px 16px',
          background: 'rgba(16,185,129,0.08)',
          borderRadius: '8px',
          borderLeft: '4px solid var(--status-normal)',
          marginBottom: '16px',
        }}
      >
        <CheckCircle size={16} color="var(--status-normal)" />
        <span style={{ fontSize: '0.9rem', color: 'var(--status-normal)' }}>All validation checks passed.</span>
      </div>
    );
  }

  return (
    <div style={{ marginBottom: '16px' }}>
      {validations.map((validation, index) => {
        if (validation.status === 'pass') return null;

        const isFailure = validation.status === 'fail';
        const icon = isFailure
          ? <AlertTriangle size={16} color="var(--status-critical)" />
          : <AlertCircle size={16} color="var(--status-warning)" />;

        return (
          <div
            key={`${validation.check_type}-${index}`}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              padding: '12px 16px',
              background: isFailure ? 'rgba(239,68,68,0.08)' : 'rgba(245,158,11,0.08)',
              borderRadius: '8px',
              borderLeft: `4px solid ${isFailure ? 'var(--status-critical)' : 'var(--status-warning)'}`,
              marginBottom: '8px',
            }}
          >
            {icon}
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.85rem', textTransform: 'uppercase' }}>
                {validation.check_type} Check - {validation.status}
              </div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                {validation.message}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ValidationWarnings;
