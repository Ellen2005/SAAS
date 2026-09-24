import React from 'react';
import { ArrowUpRight, ArrowDownRight, TrendingUp, TrendingDown } from 'lucide-react';
import SparklineChart from './SparklineChart';

/**
 * Enterprise KPI Card — Power BI style with optional sparkline.
 */
const KpiCard = ({
  title, value, delta, trend, status = 'neutral', subtitle, icon,
  format = 'number', progress, onClick, sparkData, sparkColor,
}) => {
  const fmt = (v) => {
    if (v == null || v === '—') return '—';
    const num = typeof v === 'string' ? parseFloat(v) : v;
    if (isNaN(num)) return v;
    if (format === 'currency') {
      return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'XAF', maximumFractionDigits: 0 }).format(num);
    }
    if (format === 'percent') return `${num.toFixed(1)}%`;
    if (Math.abs(num) >= 1_000_000_000) return `${(num / 1_000_000_000).toFixed(1)}B`;
    if (Math.abs(num) >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (Math.abs(num) >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toLocaleString('fr-FR', { maximumFractionDigits: 0 });
  };

  const statusColors = {
    positive: { accent: 'var(--ea-success)', bg: 'var(--ea-success-bg)' },
    negative: { accent: 'var(--ea-danger)', bg: 'var(--ea-danger-bg)' },
    warning: { accent: 'var(--ea-warning)', bg: 'var(--ea-warning-bg)' },
    neutral: { accent: 'var(--ea-primary)', bg: 'var(--ea-primary-bg)' },
  };

  const color = statusColors[status] || statusColors.neutral;
  const deltaColor = delta > 0 ? 'var(--ea-success)' : delta < 0 ? 'var(--ea-danger)' : 'var(--ea-text-muted)';
  const TrendIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : null;

  const autoSparkColor = delta > 0 ? '#10b981' : delta < 0 ? '#ef4444' : '#3b82f6';

  return (
    <div
      className="ea-kpi-card"
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
      role="region"
      aria-label={`KPI Card: ${title}`}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="ea-kpi-label">{title}</div>
          {subtitle && <div style={{ fontSize: '0.7rem', color: 'var(--ea-text-muted)', marginTop: 2 }}>{subtitle}</div>}
        </div>
        {icon && (
          <div className="ea-kpi-icon" style={{ background: color.bg, color: color.accent }}>
            {icon}
          </div>
        )}
      </div>

      <div className="ea-kpi-value">{fmt(value)}</div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
        {delta != null && delta !== 0 && (
          <span className={`ea-kpi-delta ${delta > 0 ? 'positive' : 'negative'}`}>
            {delta > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
            {Math.abs(delta).toFixed(1)}%
          </span>
        )}
        {trend !== 'neutral' && TrendIcon && (
          <TrendIcon size={16} style={{ color: deltaColor }} />
        )}
      </div>

      {/* Sparkline */}
      {sparkData && sparkData.length > 1 && (
        <div style={{ marginTop: 10, opacity: 0.8 }}>
          <SparklineChart
            data={sparkData}
            width={180}
            height={28}
            color={sparkColor || autoSparkColor}
            strokeWidth={1.5}
          />
        </div>
      )}

      {progress != null && (
        <div className="ea-progress" style={{ marginTop: 12 }}>
          <div className="ea-progress-bar" style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} />
        </div>
      )}
    </div>
  );
};

export default KpiCard;
