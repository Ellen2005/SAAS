import React, { useState } from 'react';

// Simple SVG-based map for CNPS regions (no external dependencies)

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

const formatVal = (v) => {
  if (v == null) return '';
  const n = Number(v);
  if (isNaN(n)) return String(v);
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toLocaleString('en-US', { maximumFractionDigits: 1 });
};

export default function MapVisualization({ data = [], onRegionClick, height = 400 }) {
  const [selectedRegion, setSelectedRegion] = useState(null);

  const maxValue = Math.max(...data.map((d) => Math.abs(d.value || 0)), 1);

  const dataMap = new Map();
  data.forEach((d, idx) => {
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

  const handleClick = (regionData) => {
    setSelectedRegion(regionData);
    onRegionClick?.(regionData);
  };

  return (
    <div style={{ position: 'relative', width: '100%', height, background: 'linear-gradient(135deg, var(--ea-bg, #f8fafc) 0%, var(--ea-bg-hover, #f1f5f9) 100%)', borderRadius: 14, border: '1px solid var(--ea-border)', overflow: 'hidden' }}>
      {/* Title */}
      <div style={{ position: 'absolute', top: 14, left: 18, zIndex: 10 }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: 'var(--ea-text-primary)' }}>Regional Performance</h3>
        <p style={{ margin: '4px 0 0', fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>
          {data.length > 0 ? `${data.length} regions with data` : 'No data available'}
        </p>
      </div>

      {/* Legend (top right) */}
      {data.length > 0 && (
        <div style={{ position: 'absolute', top: 14, right: 16, zIndex: 10, display: 'flex', flexDirection: 'column', gap: 4 }}>
          {data.slice(0, 6).map((d, i) => (
            <span key={i} style={{ fontSize: '0.7rem', padding: '3px 8px', background: 'var(--ea-bg-card)', borderRadius: 6, border: '1px solid var(--ea-border)', color: 'var(--ea-text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: REGIONS.find(r => r.id === d.region_id)?.color || '#3b82f6', flexShrink: 0 }} />
              {d.region_name}: {formatVal(d.value)}
            </span>
          ))}
        </div>
      )}

      {/* SVG Map */}
      <svg viewBox="0 0 100 100" style={{ width: '100%', height: '100%', padding: '50px 20px 20px' }}>
        {/* Cameroon outline */}
        <defs>
          <linearGradient id="mapBg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#e2e8f0" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#cbd5e1" stopOpacity="0.2" />
          </linearGradient>
          <filter id="regionShadow">
            <feDropShadow dx="0" dy="1" stdDeviation="1.5" floodOpacity="0.15" />
          </filter>
        </defs>
        <path
          d="M 30 20 L 70 15 L 75 30 L 80 50 L 75 70 L 60 80 L 40 78 L 25 65 L 20 45 Z"
          fill="url(#mapBg)"
          stroke="var(--ea-border)"
          strokeWidth="0.4"
        />

        {/* Region markers */}
        {REGIONS.map((region) => {
          const regionData = dataMap.get(region.id);
          if (!regionData && data.length > 0) return null;

          const size = regionData ? regionData.size : 8;
          const color = regionData?.customColor || region.color;
          const hasData = !!regionData;
          const isSelected = selectedRegion?.id === region.id;

          return (
            <g key={region.id} onClick={() => hasData && handleClick(regionData)} style={{ cursor: hasData ? 'pointer' : 'default' }}>
              {/* Pulse glow for active regions */}
              {hasData && (
                <circle cx={region.x} cy={region.y} r={size + 4} fill={color} opacity="0.15">
                  <animate attributeName="r" values={`${size + 4};${size + 8};${size + 4}`} dur="2.5s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.15;0.3;0.15" dur="2.5s" repeatCount="indefinite" />
                </circle>
              )}

              {/* Selection ring */}
              {isSelected && (
                <circle cx={region.x} cy={region.y} r={size + 6} fill="none" stroke={color} strokeWidth="0.8" opacity="0.6">
                  <animate attributeName="r" values={`${size + 6};${size + 10};${size + 6}`} dur="1.5s" repeatCount="indefinite" />
                </circle>
              )}

              {/* Main circle */}
              <circle
                cx={region.x}
                cy={region.y}
                r={size}
                fill={hasData ? color : 'var(--ea-bg-hover)'}
                stroke={isSelected ? '#fff' : hasData ? color : 'var(--ea-border)'}
                strokeWidth={isSelected ? 1.5 : hasData ? 1 : 0.5}
                opacity={hasData ? 0.9 : 0.5}
                filter={hasData ? 'url(#regionShadow)' : undefined}
              />

              {/* Value label inside bubble */}
              {hasData && regionData.value != null && size >= 10 && (
                <text
                  x={region.x}
                  y={region.y + 0.5}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="white"
                  fontSize="2.8"
                  fontWeight="bold"
                  style={{ pointerEvents: 'none', textShadow: '0 1px 2px rgba(0,0,0,0.3)' }}
                >
                  {formatVal(regionData.value)}
                </text>
              )}

              {/* Region name */}
              <text
                x={region.x}
                y={region.y + size + 3.5}
                textAnchor="middle"
                fill="var(--ea-text-secondary)"
                fontSize="2.4"
                fontWeight={hasData ? 600 : 400}
                style={{ pointerEvents: 'none' }}
              >
                {region.name}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Selected region detail panel */}
      {selectedRegion && (
        <div style={{
          position: 'absolute', bottom: 16, left: 16, right: 16,
          background: 'var(--ea-bg-card)', borderRadius: 10,
          border: '1px solid var(--ea-border)', padding: '12px 16px',
          boxShadow: '0 4px 16px rgba(0,0,0,0.06)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          zIndex: 10, animation: 'fadeSlideUp 0.2s ease-out',
        }}>
          <div>
            <div style={{ fontWeight: 600, color: 'var(--ea-text-primary)', fontSize: '0.9rem' }}>{selectedRegion.name}</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--ea-text-secondary)', marginTop: 2 }}>
              Performance: <span style={{ fontWeight: 600, color: selectedRegion.customColor || selectedRegion.color }}>{formatVal(selectedRegion.value)}</span>
            </div>
          </div>
          <button
            onClick={() => setSelectedRegion(null)}
            style={{ background: 'none', border: 'none', color: 'var(--ea-text-secondary)', cursor: 'pointer', fontSize: '0.8rem', padding: '4px 8px', borderRadius: 6 }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Empty state */}
      {data.length === 0 && (
        <div style={{ position: 'absolute', bottom: 16, left: 16, right: 16, textAlign: 'center', color: 'var(--ea-text-secondary)', fontSize: '0.85rem' }}>
          No regional data available. Connect a database and sync to see regional performance.
        </div>
      )}

      <style>{`
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}