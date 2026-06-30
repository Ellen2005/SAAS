import React from 'react';

// Simple SVG-based map for CNPS regions (no external dependencies)
// For production, replace with react-simple-maps or leaflet

const REGIONS = [
  { id: 'douala', name: 'Douala', x: 50, y: 55, color: '#3b82f6' },
  { id: 'yaounde', name: 'Yaoundé', x: 52, y: 48, color: '#10b981' },
  { id: 'bafoussam', name: 'Bafoussam', x: 42, y: 42, color: '#f59e0b' },
  { id: 'garoua', name: 'Garoua', x: 55, y: 28, color: '#8b5cf6' },
  { id: 'maroua', name: 'Maroua', x: 68, y: 22, color: '#ef4444' },
  { id: 'bamenda', name: 'Bamenda', x: 38, y: 35, color: '#06b6d4' },
  { id: 'ebolowa', name: 'Ebolowa', x: 48, y: 62, color: '#ec4899' },
  { id: 'bertoua', name: 'Bertoua', x: 62, y: 45, color: '#84cc16' },
  { id: 'nanga', name: 'Nanga-Eboko', x: 58, y: 50, color: '#f97316' },
  { id: 'buea', name: 'Buea', x: 35, y: 58, color: '#6366f1' },
];

export default function MapVisualization({ data = [], onRegionClick, height = 400 }) {
  // data format: [{ region_id, region_name, value, color?, size? }]
  const maxValue = Math.max(...data.map((d) => Math.abs(d.value || 0)), 1);

  const dataMap = new Map();
  data.forEach((d, idx) => {
    // Match by region_id or region_name, or fall back to index-based assignment
    const region = REGIONS.find((r) => r.id === d.region_id || r.name === d.region_name)
      || REGIONS[idx % REGIONS.length];
    if (region) {
      dataMap.set(region.id, {
        ...region,
        value: d.value,
        customColor: d.color,
        size: d.size || Math.max(12, Math.min(50, Math.abs(d.value || 0) / maxValue * 40 + 10)),
      });
    }
  });

  return (
    <div style={{ position: 'relative', width: '100%', height, background: 'var(--ea-bg)', borderRadius: 'var(--ea-radius-lg)', border: '1px solid var(--ea-border)', overflow: 'hidden' }}>
      {/* Title */}
      <div style={{ position: 'absolute', top: 12, left: 16, zIndex: 10 }}>
        <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--ea-text-primary)' }}>Regional Performance</h3>
        <p style={{ margin: '4px 0 0', fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>Click a region for details</p>
      </div>

      {/* Legend */}
      {data.length > 0 && (
        <div style={{ position: 'absolute', top: 12, right: 16, zIndex: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {data.slice(0, 5).map((d, i) => (
            <span key={i} style={{ fontSize: '0.7rem', padding: '2px 8px', background: 'var(--ea-bg-card)', borderRadius: 4, border: '1px solid var(--ea-border)', color: 'var(--ea-text-primary)' }}>
              {d.region_name}: {typeof d.value === 'number' ? d.value.toLocaleString() : d.value}
            </span>
          ))}
        </div>
      )}

      {/* SVG Map */}
      <svg viewBox="0 0 100 100" style={{ width: '100%', height: '100%', padding: '40px 16px 16px' }}>
        {/* Cameroon outline (simplified) */}
        <path
          d="M 30 20 L 70 15 L 75 30 L 80 50 L 75 70 L 60 80 L 40 78 L 25 65 L 20 45 Z"
          fill="var(--ea-bg-hover)"
          stroke="var(--ea-border)"
          strokeWidth="0.5"
          opacity="0.6"
        />

        {/* Region markers */}
        {REGIONS.map((region) => {
          const regionData = dataMap.get(region.id);
          if (!regionData && data.length > 0) return null; // Only show regions with data

          const size = regionData ? regionData.size : 8;
          const color = regionData?.customColor || region.color;
          const hasData = !!regionData;

          return (
            <g key={region.id} onClick={() => hasData && onRegionClick?.(regionData)} style={{ cursor: hasData ? 'pointer' : 'default' }}>
              {/* Outer glow for active regions */}
              {hasData && (
                <circle cx={region.x} cy={region.y} r={size + 4} fill={color} opacity="0.2">
                  <animate attributeName="r" values={`${size + 4};${size + 8};${size + 4}`} dur="2s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.2;0.4;0.2" dur="2s" repeatCount="indefinite" />
                </circle>
              )}
              
              {/* Main circle */}
              <circle
                cx={region.x}
                cy={region.y}
                r={size}
                fill={hasData ? color : 'var(--ea-bg-hover)'}
                stroke={hasData ? color : 'var(--ea-border)'}
                strokeWidth={hasData ? 1.5 : 0.5}
                opacity={hasData ? 0.9 : 0.5}
              />

              {/* Value label */}
              {hasData && regionData.value != null && (
                <text
                  x={region.x}
                  y={region.y + 1}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="white"
                  fontSize="3"
                  fontWeight="bold"
                  style={{ pointerEvents: 'none' }}
                >
                  {typeof regionData.value === 'number' ? (regionData.value >= 1000 ? `${(regionData.value / 1000).toFixed(0)}k` : regionData.value.toFixed(0)) : ''}
                </text>
              )}

              {/* Region name */}
              <text
                x={region.x}
                y={region.y + size + 4}
                textAnchor="middle"
                fill="var(--ea-text-secondary)"
                fontSize="2.5"
                fontWeight={hasData ? 600 : 400}
              >
                {region.name}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Tooltip on hover (simple implementation) */}
      {data.length === 0 && (
        <div style={{ position: 'absolute', bottom: 16, left: 16, right: 16, textAlign: 'center', color: 'var(--ea-text-secondary)', fontSize: '0.85rem' }}>
          No regional data available. Connect a database and sync to see regional performance.
        </div>
      )}
    </div>
  );
}