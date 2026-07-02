import React, { useMemo, useId } from 'react';

/**
 * Lightweight SVG sparkline chart alternative to recharts AreaChart.
 * ~2KB vs recharts ~500KB - eliminates the main bundle size issue.
 */
const SparklineChart = ({ data, width = 200, height = 32, color = '#10b981', strokeWidth = 1.5 }) => {
  const path = useMemo(() => {
    if (!data || data.length < 2) return null;
    
    const padding = 2;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;
    
    const values = data.map(d => d.value ?? d);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    
    const xStep = chartWidth / (values.length - 1);
    const points = values.map((v, i) => ({
      x: padding + i * xStep,
      y: padding + chartHeight - ((v - min) / range) * chartHeight,
    }));
    
    const parts = points.map((p, i) => {
      if (i === 0) return `M ${p.x} ${p.y}`;
      // Use smooth curves
      const prev = points[i - 1];
      const cpx1 = prev.x + (p.x - prev.x) / 2;
      const cpy1 = prev.y;
      const cpx2 = prev.x + (p.x - prev.x) / 2;
      const cpy2 = p.y;
      return `C ${cpx1} ${cpy1}, ${cpx2} ${cpy2}, ${p.x} ${p.y}`;
    });
    
    return parts.join(' ');
  }, [data, width, height]);

  const gradientId = useId();

  if (!path) return null;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: 'block' }}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.3} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path
        d={`${path} L ${width - 2} ${height} L 2 ${height} Z`}
        fill={`url(#${gradientId})`}
        opacity={0.5}
      />
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

export default SparklineChart;