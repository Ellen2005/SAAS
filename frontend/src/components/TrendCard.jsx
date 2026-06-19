import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts';

/**
 * Enterprise Trend Card — Power BI style sparkline card.
 */
const TrendCard = ({ title, value, delta, data, dataKey = 'value', color = '#2563eb', format, subtitle }) => {
  const fmt = format || ((v) => {
    if (v == null) return '—';
    const num = Number(v);
    if (Math.abs(num) >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (Math.abs(num) >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toLocaleString('fr-FR', { maximumFractionDigits: 0 });
  });

  const TrendIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;
  const trendColor = delta > 0 ? 'var(--ea-success)' : delta < 0 ? 'var(--ea-danger)' : 'var(--ea-text-muted)';

  return (
    <div className="ea-card" style={{ overflow: 'hidden' }}>
      <div style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--ea-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {title}
          </div>
          {subtitle && <div style={{ fontSize: '0.7rem', color: 'var(--ea-text-muted)', marginTop: 2 }}>{subtitle}</div>}
          <div style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: 4, color: 'var(--ea-text-primary)' }}>
            {fmt(value)}
          </div>
          {delta != null && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 4, color: trendColor, fontSize: '0.8rem', fontWeight: 500 }}>
              <TrendIcon size={14} />
              {Math.abs(delta).toFixed(1)}%
              <span style={{ color: 'var(--ea-text-muted)', fontWeight: 400, fontSize: '0.75rem' }}>vs previous</span>
            </div>
          )}
        </div>
      </div>
      {data && data.length > 1 && (
        <div style={{ height: 60, margin: '0 4px 4px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id={`trend-${title?.replace(/\s/g, '')}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.2} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Tooltip contentStyle={{ fontSize: '0.75rem', borderRadius: 6 }} />
              <Area type="monotone" dataKey={dataKey} stroke={color} fill={`url(#trend-${title?.replace(/\s/g, '')})`} strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default TrendCard;