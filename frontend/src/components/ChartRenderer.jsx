import React, { useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ScatterChart,
  Scatter,
  ZAxis,
  Treemap,
  FunnelChart,
  Funnel,
  LabelList,
  ComposedChart,
  RadialBarChart,
  RadialBar,
} from 'recharts';

const DEFAULT_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444',
  '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1',
  '#14b8a6', '#a855f7', '#e11d48', '#0ea5e9',
];

const formatNum = (v) => {
  if (v == null) return '';
  const n = Number(v);
  if (isNaN(n)) return String(v);
  if (Math.abs(n) >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toLocaleString('en-US', { maximumFractionDigits: 2 });
};

const CustomTooltip = ({ active, payload, label, formatter }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--ea-bg-card, #fff)',
      border: '1px solid var(--ea-border, #e5e7eb)',
      borderRadius: 10,
      padding: '10px 14px',
      boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
      fontSize: '0.82rem',
      maxWidth: 240,
    }}>
      {label && <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--ea-text-primary, #111)' }}>{label}</div>}
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, color: 'var(--ea-text-secondary, #666)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: p.color, display: 'inline-block' }} />
            {p.name || p.dataKey}
          </span>
          <span style={{ fontWeight: 600, color: 'var(--ea-text-primary, #111)' }}>
            {formatter ? formatter(p.value) : formatNum(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
};

const CustomBarLabel = ({ x, y, width, value, color }) => {
  if (value == null || value === 0) return null;
  return (
    <text x={x + width / 2} y={y - 6} textAnchor="middle" fill={color || '#374151'} fontSize={11} fontWeight={600}>
      {formatNum(value)}
    </text>
  );
};

export default function ChartRenderer({ spec, height = 280 }) {
  if (!spec || spec.type === 'table') {
    return spec?.data ? (
      <div style={{ overflowX: 'auto' }}>
        {spec.title && (
          <div style={{ marginBottom: 10 }}>
            <h4 style={{ fontSize: '0.95rem', margin: 0, color: 'var(--ea-text-primary)', fontWeight: 600 }}>{spec.title}</h4>
            {spec.data.length > 0 && (
              <span style={{ fontSize: '0.72rem', color: 'var(--ea-text-secondary)' }}>
                {spec.data.length} row{spec.data.length > 1 ? 's' : ''} · {Object.keys(spec.data[0]).length} columns
              </span>
            )}
          </div>
        )}
        <div style={{ borderRadius: 10, border: '1px solid var(--ea-border)', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr>
                {(spec.columns || Object.keys(spec.data[0] || {})).map((col) => (
                  <th key={col} style={{
                    padding: '10px 14px', textAlign: 'left',
                    background: 'var(--ea-bg-hover, #f9fafb)',
                    borderBottom: '2px solid var(--ea-border, #e5e7eb)',
                    color: 'var(--ea-text-secondary, #6b7280)',
                    fontWeight: 600, fontSize: '0.78rem',
                    textTransform: 'uppercase', letterSpacing: '0.04em',
                    whiteSpace: 'nowrap',
                  }}>
                    {col.replace(/_/g, ' ')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(spec.data || []).slice(0, 50).map((row, i) => (
                <tr key={i} style={{
                  borderBottom: '1px solid var(--ea-border, #f3f4f6)',
                  background: i % 2 === 0 ? 'transparent' : 'var(--ea-bg-hover, #f9fafb)',
                  transition: 'background 0.15s',
                }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--ea-primary-bg, #eff6ff)'}
                  onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : 'var(--ea-bg-hover, #f9fafb)'}
                >
                  {(spec.columns || Object.keys(row)).map((col) => (
                    <td key={col} style={{
                      padding: '9px 14px', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis',
                      color: 'var(--ea-text-primary, #111)', whiteSpace: 'nowrap',
                    }}>
                      {row[col] === null
                        ? <span style={{ color: 'var(--ea-text-secondary, #9ca3af)', fontStyle: 'italic' }}>—</span>
                        : typeof row[col] === 'number'
                          ? row[col].toLocaleString('en-US', { maximumFractionDigits: 2 })
                          : String(row[col])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {spec.data.length > 50 && (
          <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.78rem', marginTop: 6, textAlign: 'right' }}>
            Showing 50 of {spec.data.length} rows
          </p>
        )}
        {spec.message && <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.85rem', marginTop: 8 }}>{spec.message}</p>}
      </div>
    ) : (
      spec?.message ? <p style={{ color: 'var(--ea-text-secondary)', fontSize: '0.9rem', margin: 0 }}>{spec.message}</p> : null
    );
  }

  const data = spec.data || [];
  const colors = spec.colors || DEFAULT_COLORS;
  const xKey = spec.xKey || 'label';
  const yKey = spec.yKey || 'value';
  const title = spec.title;

  if (!data.length) return null;

  const renderChart = () => {
    switch (spec.type) {
      // ── HORIZONTAL BAR ──────────────────────────────────────
      case 'horizontalBar':
        return (
          <BarChart data={data} layout="vertical" margin={{ top: 8, right: 30, left: 140, bottom: 8 }}>
            <defs>
              <linearGradient id="hbarGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor={colors[0]} stopOpacity={0.85} />
                <stop offset="100%" stopColor={colors[0]} stopOpacity={1} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" horizontal={false} />
            <XAxis type="number" stroke="var(--ea-text-secondary)" fontSize={11} tickLine={false}
              tickFormatter={(v) => formatNum(v)} />
            <YAxis type="category" dataKey={spec.yKey || 'name'} stroke="var(--ea-text-secondary)" fontSize={10} width={130} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey={spec.xKey || 'value'} fill="url(#hbarGrad)" radius={[0, 6, 6, 0]} maxBarSize={24} />
          </BarChart>
        );

      // ── PIE ─────────────────────────────────────────────────
      case 'pie':
        return (
          <PieChart>
            <Pie data={data} dataKey={yKey} nameKey={xKey} cx="50%" cy="50%"
              outerRadius={Math.min(130, height / 2.4)} innerRadius={0}
              stroke="var(--ea-bg-card, #fff)" strokeWidth={2}
              label={({ label, percent }) => percent > 0.05 ? `${label}\n${(percent * 100).toFixed(0)}%` : ''}
              labelLine={{ stroke: 'var(--ea-text-secondary, #999)', strokeWidth: 1 }}
              animationBegin={0} animationDuration={800} animationEasing="ease-out">
              {data.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: 8 }} />
          </PieChart>
        );

      // ── DOUGHNUT ────────────────────────────────────────────
      case 'doughnut':
        return (
          <PieChart>
            <Pie data={data} dataKey={yKey} nameKey={xKey} cx="50%" cy="50%"
              innerRadius={55} outerRadius={Math.min(130, height / 2.4)}
              stroke="var(--ea-bg-card, #fff)" strokeWidth={3}
              label={({ label, percent }) => percent > 0.05 ? `${label}\n${(percent * 100).toFixed(0)}%` : ''}
              labelLine={{ stroke: 'var(--ea-text-secondary, #999)', strokeWidth: 1 }}
              animationBegin={0} animationDuration={800} animationEasing="ease-out">
              {data.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: 8 }} />
          </PieChart>
        );

      // ── LINE ────────────────────────────────────────────────
      case 'line':
        return (
          <LineChart data={data} margin={{ top: 16, right: 20, left: 10, bottom: 8 }}>
            <defs>
              <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={colors[0]} stopOpacity={0.15} />
                <stop offset="100%" stopColor={colors[0]} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" vertical={false} />
            <XAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={11} tickLine={false}
              tickFormatter={(v) => v?.length > 12 ? `${v.slice(0, 10)}…` : v} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={60} tickLine={false} axisLine={false}
              tickFormatter={(v) => formatNum(v)} />
            <Tooltip content={<CustomTooltip />} />
            <Line type="monotone" dataKey={yKey} stroke={colors[0]} strokeWidth={2.5}
              dot={{ r: 4, fill: '#fff', stroke: colors[0], strokeWidth: 2 }}
              activeDot={{ r: 6, fill: colors[0], stroke: '#fff', strokeWidth: 2 }} />
            {data[0]?.value2 && (
              <Line type="monotone" dataKey="value2" stroke={colors[1]} strokeWidth={2}
                dot={{ r: 3, fill: '#fff', stroke: colors[1], strokeWidth: 2 }} />
            )}
          </LineChart>
        );

      // ── AREA ────────────────────────────────────────────────
      case 'area':
        return (
          <AreaChart data={data} margin={{ top: 16, right: 20, left: 10, bottom: 8 }}>
            <defs>
              <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={colors[0]} stopOpacity={0.25} />
                <stop offset="100%" stopColor={colors[0]} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" vertical={false} />
            <XAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={11} tickLine={false} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={60} tickLine={false} axisLine={false}
              tickFormatter={(v) => formatNum(v)} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey={yKey} stroke={colors[0]} fill="url(#areaGrad)" strokeWidth={2.5}
              dot={{ r: 3, fill: '#fff', stroke: colors[0], strokeWidth: 2 }}
              activeDot={{ r: 5, fill: colors[0] }} />
          </AreaChart>
        );

      // ── BAR ─────────────────────────────────────────────────
      case 'bar':
        return (
          <BarChart data={data} margin={{ top: 20, right: 20, left: 10, bottom: 8 }}>
            <defs>
              <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={colors[0]} stopOpacity={0.95} />
                <stop offset="100%" stopColor={colors[0]} stopOpacity={0.7} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" vertical={false} />
            <XAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={11} tickLine={false}
              tickFormatter={(v) => v?.length > 12 ? `${v.slice(0, 10)}…` : v} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={60} tickLine={false} axisLine={false}
              tickFormatter={(v) => formatNum(v)} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey={yKey} fill="url(#barGrad)" radius={[6, 6, 0, 0]} maxBarSize={48}
              label={<CustomBarLabel color={colors[0]} />} />
          </BarChart>
        );

      // ── SCATTER ─────────────────────────────────────────────
      case 'scatter':
        const scatterData = data.map((d) => ({ x: d.value, y: d.value2 || d.value, label: d.label }));
        return (
          <ScatterChart margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
            <XAxis dataKey="x" stroke="var(--ea-text-secondary)" fontSize={11} name="X" />
            <YAxis dataKey="y" stroke="var(--ea-text-secondary)" fontSize={11} name="Y" />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
              formatter={(v, name) => [Number(v).toLocaleString(), name === 'x' ? 'X Value' : 'Y Value']}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.label || ''} />
            <Scatter data={scatterData} fill={colors[0]} />
          </ScatterChart>
        );

      // ── BUBBLE ─────────────────────────────────────────────
      case 'bubble':
        const bubbleData = data.map((d) => ({
          x: d.value,
          y: d.value2 || d.value,
          z: d.value3 || Math.abs(d.value) / 10,
          label: d.label,
        }));
        return (
          <ScatterChart margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
            <XAxis dataKey="x" stroke="var(--ea-text-secondary)" fontSize={11} name="X" />
            <YAxis dataKey="y" stroke="var(--ea-text-secondary)" fontSize={11} name="Y" />
            <ZAxis dataKey="z" range={[50, 400]} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
              formatter={(v, name) => [Number(v).toLocaleString(), name === 'z' ? 'Size' : name === 'x' ? 'X Value' : 'Y Value']}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.label || ''} />
            <Scatter data={bubbleData} fill={colors[0]} fillOpacity={0.6} />
          </ScatterChart>
        );

      // ── RADAR ──────────────────────────────────────────────
      case 'radar':
        return (
          <RadarChart data={data} outerRadius={Math.min(120, height / 2.5)}>
            <PolarGrid stroke="var(--ea-border)" />
            <PolarAngleAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={10} />
            <PolarRadiusAxis stroke="var(--ea-text-secondary)" fontSize={9} />
            <Radar name="Metric 1" dataKey={yKey} stroke={colors[0]} fill={colors[0]} fillOpacity={0.3} strokeWidth={2} />
            {data[0]?.value2 && (
              <Radar name="Metric 2" dataKey="value2" stroke={colors[1]} fill={colors[1]} fillOpacity={0.2} strokeWidth={2} />
            )}
            <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
              formatter={(v) => Number(v).toLocaleString()} />
          </RadarChart>
        );

      // ── GAUGE (simulated with horizontal bars) ────────────────
      case 'gauge':
        const gaugeMax = Math.max(...data.map((d) => d.value), 1);
        return (
          <div style={{ display: 'grid', gap: 12, padding: '8px 0' }}>
            {data.map((d, i) => {
              const pct = Math.min((d.value / gaugeMax) * 100, 100);
              const color = pct > 80 ? colors[1] : pct > 50 ? colors[2] : colors[4];
              return (
                <div key={i}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: 4 }}>
                    <span style={{ fontWeight: 600 }}>{d.label}</span>
                    <span>{Number(d.value).toLocaleString()}</span>
                  </div>
                  <div style={{ background: 'var(--ea-bg-hover)', borderRadius: 8, height: 20, overflow: 'hidden' }}>
                    <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 8, transition: 'width 0.5s' }} />
                  </div>
                </div>
              );
            })}
          </div>
        );

      // ── HISTOGRAM ─────────────────────────────────────────────
      case 'histogram':
        const bins = 10;
        const values = data.map((d) => d.value).filter((v) => v != null);
        if (!values.length) return null;
        const min = Math.min(...values);
        const max = Math.max(...values);
        const binWidth = (max - min) / bins || 1;
        const histogram = Array(bins).fill(0);
        values.forEach((v) => {
          const idx = Math.min(bins - 1, Math.floor((v - min) / binWidth));
          histogram[idx]++;
        });
        const histData = histogram.map((count, i) => ({
          label: `${(min + i * binWidth).toFixed(0)}-${(min + (i + 1) * binWidth).toFixed(0)}`,
          value: count,
        }));
        return (
          <BarChart data={histData} margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
            <XAxis dataKey="label" stroke="var(--ea-text-secondary)" fontSize={10} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={50} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
              formatter={(v) => [Number(v), 'Count']} />
            <Bar dataKey="value" fill={colors[0]} radius={[2, 2, 0, 0]} />
          </BarChart>
        );

      // ── TREEMAP ─────────────────────────────────────────────
      case 'treemap':
        const treemapData = data.map((d, i) => ({
          name: d.label,
          size: Math.max(1, Math.abs(d.value)),
          fill: colors[i % colors.length],
        }));
        return (
          <Treemap data={treemapData} dataKey="size" aspectRatio={4/3} stroke="var(--ea-bg-card)">
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
              formatter={(v, name) => [Number(v).toLocaleString(), name]} />
          </Treemap>
        );

      // ── FUNNEL ───────────────────────────────────────────────
      case 'funnel':
        return (
          <FunnelChart margin={{ top: 8, right: 20, left: 20, bottom: 8 }}>
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
              formatter={(v) => [Number(v).toLocaleString(), 'Count']} />
            <Funnel dataKey={yKey} data={data} isAnimationActive>
              {data.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} stroke="none" />
              ))}
              <LabelList dataKey={xKey} position="right" fill="var(--ea-text-primary)" fontSize={12} />
            </Funnel>
          </FunnelChart>
        );

      // ── WATERFALL (simulated with stacked bar) ──────────────
      case 'waterfall':
        let cumulative = 0;
        const waterfallData = data.map((d) => {
          cumulative += d.value;
          return { ...d, cumulative, base: cumulative - d.value };
        });
        return (
          <BarChart data={waterfallData} margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
            <XAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={11} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={70} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
              formatter={(v, name) => [Number(v).toLocaleString(), name === 'value' ? 'Change' : 'Cumulative']} />
            <Bar dataKey="cumulative" fill={colors[0]} radius={[4, 4, 0, 0]} />
          </BarChart>
        );

      // ── COMPOSED (line + bar) ──────────────────────────────
      case 'composed':
        return (
          <ComposedChart data={data} margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
            <XAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={11} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={70} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }} />
            <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
            <Bar dataKey={yKey} fill={colors[0]} radius={[4, 4, 0, 0]} />
            {data[0]?.value2 && <Line type="monotone" dataKey="value2" stroke={colors[1]} strokeWidth={2} />}
          </ComposedChart>
        );

      // ── RADIAL BAR ─────────────────────────────────────────
      case 'radialBar':
        return (
          <RadialBarChart data={data} innerRadius="20%" outerRadius="90%" startAngle={180} endAngle={0}>
            <RadialBar label={{ fill: 'var(--ea-text-primary)', fontSize: 11 }} background dataKey={yKey}>
              {data.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </RadialBar>
            <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }} />
          </RadialBarChart>
        );

      // ── HEATMAP (simulated with colored bars) ──────────────
      case 'heatmap':
        const heatmapMax = Math.max(...data.map(d => Math.abs(d.value)), 1);
        return (
          <div style={{ display: 'grid', gap: 4, padding: '8px 0' }}>
            {data.map((d, i) => {
              const intensity = Math.abs(d.value) / heatmapMax;
              const bgColor = `rgba(59, 130, 246, ${intensity})`;
              return (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: '0.85rem', width: 120, overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--ea-text-primary)' }}>{d.label}</span>
                  <div style={{ flex: 1, height: 32, background: bgColor, borderRadius: 4, display: 'flex', alignItems: 'center', padding: '0 12px', color: intensity > 0.5 ? 'white' : 'var(--ea-text-primary)' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{Number(d.value).toLocaleString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        );

      // ── GROUPED BAR ────────────────────────────────────────
      case 'groupedBar':
        return (
          <BarChart data={data} margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
            <XAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={11} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={70} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }} />
            <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
            {Object.keys(data[0] || {})
              .filter(k => k !== xKey)
              .slice(0, 6)
              .map((key, i) => (
                <Bar key={key} dataKey={key} fill={colors[i % colors.length]} radius={[4, 4, 0, 0]} />
              ))}
          </BarChart>
        );

      // ── STACKED BAR ─────────────────────────────────────────
      case 'stackedBar':
        return (
          <BarChart data={data} margin={{ top: 8, right: 20, left: 0, bottom: 8 }} stackOffset="sign">
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
            <XAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={11} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={70} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }} />
            <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
            {Object.keys(data[0] || {})
              .filter(k => k !== xKey)
              .slice(0, 6)
              .map((key, i) => (
                <Bar key={key} dataKey={key} stackId="a" fill={colors[i % colors.length]} />
              ))}
          </BarChart>
        );

      // ── DEFAULT (Bar) ──────────────────────────────────────
      default:
        return (
          <BarChart data={data} margin={{ top: 20, right: 20, left: 10, bottom: 8 }}>
            <defs>
              <linearGradient id="barGradDef" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={colors[0]} stopOpacity={0.95} />
                <stop offset="100%" stopColor={colors[0]} stopOpacity={0.7} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" vertical={false} />
            <XAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={11} tickLine={false} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={60} tickLine={false} axisLine={false}
              tickFormatter={(v) => formatNum(v)} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey={yKey} fill="url(#barGradDef)" radius={[6, 6, 0, 0]} maxBarSize={48}
              label={<CustomBarLabel color={colors[0]} />} />
          </BarChart>
        );
    }
  };

  // ── Meta info & axis labels ──────────────────────────────
  const meta = spec.meta || {};
  const xAxisLabel = meta.x_column ? meta.x_column.replace(/_/g, ' ') : null;
  const yAxisLabel = meta.y_column ? meta.y_column.replace(/_/g, ' ') : null;
  const metaInfo = [];
  if (meta.row_count) metaInfo.push(`${meta.row_count} data points`);
  if (meta.total_rows && meta.total_rows !== meta.row_count) metaInfo.push(`of ${meta.total_rows} total`);

  return (
    <div>
      {title && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14 }}>
          <h3 style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: 8, margin: 0, color: 'var(--ea-text-primary)' }}>
            {title}
          </h3>
          {metaInfo.length > 0 && (
            <span style={{ fontSize: '0.72rem', color: 'var(--ea-text-secondary)', background: 'var(--ea-bg-hover)', padding: '3px 8px', borderRadius: 6 }}>
              {metaInfo.join(' · ')}
            </span>
          )}
        </div>
      )}
      <div style={{ borderRadius: 10, border: '1px solid var(--ea-border)', padding: '12px 8px 8px', background: 'var(--ea-bg-card)' }}>
        <ResponsiveContainer width="100%" height={height}>
          {renderChart()}
        </ResponsiveContainer>
        {/* Axis labels */}
        {(xAxisLabel || yAxisLabel) && (
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 12px 0', fontSize: '0.7rem', color: 'var(--ea-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            <span>{xAxisLabel || ''}</span>
            <span>{yAxisLabel || ''}</span>
          </div>
        )}
      </div>
    </div>
  );
}