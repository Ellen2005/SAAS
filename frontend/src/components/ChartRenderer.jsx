import React from 'react';
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
  ErrorBar,
} from 'recharts';

const DEFAULT_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444',
  '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1',
  '#14b8a6', '#a855f7', '#e11d48', '#0ea5e9',
];

export default function ChartRenderer({ spec, height = 280 }) {
  if (!spec || spec.type === 'table') {
    return spec?.data ? (
      <div style={{ overflowX: 'auto' }}>
        <h4 style={{ fontSize: '0.95rem', marginBottom: 8 }}>{spec.title || 'Results'}</h4>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--ea-border)' }}>
              {(spec.columns || Object.keys(spec.data[0] || {})).map((col) => (
                <th key={col} style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--ea-text-secondary)', fontWeight: 600 }}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(spec.data || []).slice(0, 20).map((row, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--ea-border)' }}>
                {(spec.columns || Object.keys(row)).map((col) => (
                  <td key={col} style={{ padding: '6px 10px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {row[col] === null ? <span style={{ color: 'var(--ea-text-secondary)', fontStyle: 'italic' }}>null</span> : String(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
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
          <BarChart data={data} layout="vertical" margin={{ top: 8, right: 20, left: 140, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
            <XAxis type="number" stroke="var(--ea-text-secondary)" fontSize={11}
              tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
            <YAxis type="category" dataKey={spec.yKey || 'name'} stroke="var(--ea-text-secondary)" fontSize={10} width={130} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
              formatter={(v) => [Number(v).toLocaleString(), 'Value']} />
            <Bar dataKey={spec.xKey || 'value'} fill={colors[0]} radius={[0, 4, 4, 0]} />
          </BarChart>
        );

      // ── PIE ─────────────────────────────────────────────────
      case 'pie':
        return (
          <PieChart>
            <Pie data={data} dataKey={yKey} nameKey={xKey} cx="50%" cy="50%" outerRadius={Math.min(120, height / 2.5)}
              label={({ label, percent }) => `${label} (${(percent * 100).toFixed(0)}%)`}>
              {data.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(v) => Number(v).toLocaleString()} />
            <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
          </PieChart>
        );

      // ── DOUGHNUT ────────────────────────────────────────────
      case 'doughnut':
        return (
          <PieChart>
            <Pie data={data} dataKey={yKey} nameKey={xKey} cx="50%" cy="50%" innerRadius={50} outerRadius={Math.min(120, height / 2.5)}
              label={({ label, percent }) => `${label} (${(percent * 100).toFixed(0)}%)`}>
              {data.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(v) => Number(v).toLocaleString()} />
            <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
          </PieChart>
        );

      // ── LINE ────────────────────────────────────────────────
      case 'line':
        return (
          <LineChart data={data} margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
            <XAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={11}
              tickFormatter={(v) => v?.length > 12 ? `${v.slice(0, 10)}...` : v} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={70}
              tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
              formatter={(v) => [Number(v).toLocaleString(), 'Value']} />
            <Line type="monotone" dataKey={yKey} stroke={colors[0]} strokeWidth={2} dot={{ r: 3, fill: colors[0] }} activeDot={{ r: 5 }} />
            {data[0]?.value2 && <Line type="monotone" dataKey="value2" stroke={colors[1]} strokeWidth={2} dot={{ r: 3, fill: colors[1] }} />}
          </LineChart>
        );

      // ── AREA ────────────────────────────────────────────────
      case 'area':
        return (
          <AreaChart data={data} margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
            <defs>
              <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={colors[0]} stopOpacity={0.3} />
                <stop offset="100%" stopColor={colors[0]} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
            <XAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={11} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={70} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
              formatter={(v) => [Number(v).toLocaleString(), 'Value']} />
            <Area type="monotone" dataKey={yKey} stroke={colors[0]} fill="url(#areaGrad)" strokeWidth={2} />
          </AreaChart>
        );

      // ── BAR ─────────────────────────────────────────────────
      case 'bar':
        return (
          <BarChart data={data} margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
            <XAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={11}
              tickFormatter={(v) => v?.length > 10 ? `${v.slice(0, 8)}..` : v} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={70}
              tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
              formatter={(v) => [Number(v).toLocaleString(), 'Value']} />
            <Bar dataKey={yKey} fill={colors[0]} radius={[4, 4, 0, 0]} />
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
          <BarChart data={data} margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
            <XAxis dataKey={xKey} stroke="var(--ea-text-secondary)" fontSize={11} />
            <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={70} />
            <Tooltip contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
              formatter={(v) => [Number(v).toLocaleString(), 'Value']} />
            <Bar dataKey={yKey} fill={colors[0]} radius={[4, 4, 0, 0]} />
          </BarChart>
        );
    }
  };

  // ── Meta info row ─────────────────────────────────────────
  const meta = spec.meta || {};
  const metaInfo = [];
  if (meta.row_count) metaInfo.push(`${meta.row_count} rows displayed`);
  if (meta.total_rows) metaInfo.push(`of ${meta.total_rows} total`);
  if (meta.x_column) metaInfo.push(`X: ${meta.x_column}`);
  if (meta.y_column) metaInfo.push(`Y: ${meta.y_column}`);

  return (
    <div>
      {title && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 12 }}>
          <h3 style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: 8, margin: 0, color: 'var(--ea-text-primary)' }}>
            <span style={{ color: 'var(--ea-primary)' }}>◆</span> {title}
          </h3>
          {metaInfo.length > 0 && (
            <span style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)' }}>{metaInfo.join(' | ')}</span>
          )}
        </div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        {renderChart()}
      </ResponsiveContainer>
      {spec.type !== 'table' && (
        <div style={{ display: 'flex', gap: 6, marginTop: 8, justifyContent: 'flex-end' }}>
          <span style={{ fontSize: '0.7rem', padding: '2px 8px', background: 'var(--ea-bg-hover)', borderRadius: 4, color: 'var(--ea-text-secondary)' }}>
            {spec.type}
          </span>
        </div>
      )}
    </div>
  );
}