import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle } from 'lucide-react';

const ValidationWarnings = ({ validations = [] }) => {
  if (!validations || validations.length === 0) return null;

  const allPassed = validations.every((validation) => (validation.status || '').toLowerCase() === 'pass');
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
        const status = (validation.status || 'warning').toLowerCase();
        if (status === 'pass') return null;

        const isFailure = status === 'fail';
        const details = validation.details || {};
        const detailRows = [];
        if (details.flagged_columns) {
          Object.entries(details.flagged_columns).forEach(([name, value]) => {
            detailRows.push(`${name}: ${value.null_pct}% null (${value.null_count}/${value.total_rows})`);
          });
        }
        if (details.flagged_kpis) {
          Object.entries(details.flagged_kpis).forEach(([name, value]) => {
            detailRows.push(`${name}: ${value.change_pct}% change (${value.previous_total} -> ${value.current_total})`);
          });
        }
        if (details.missing_fields) {
          detailRows.push(`Missing: ${details.missing_fields.join(', ')}`);
        }
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
                {validation.check_type || 'validation'} Check - {status}
              </div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                {validation.message || 'Validation issue detected.'}
              </div>
              {detailRows.length > 0 && (
                <ul style={{ margin: '8px 0 0', paddingLeft: '18px', color: 'var(--text-secondary)', fontSize: '0.82rem', lineHeight: 1.5 }}>
                  {detailRows.slice(0, 5).map((detail) => <li key={detail}>{detail}</li>)}
                </ul>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ValidationWarnings;
