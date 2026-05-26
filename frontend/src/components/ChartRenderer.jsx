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
} from 'recharts';

const DEFAULT_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'];

export default function ChartRenderer({ spec, height = 280 }) {
  if (!spec || spec.type === 'table_only') {
    return spec?.message ? (
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>{spec.message}</p>
    ) : null;
  }

  const data = spec.data || [];
  const colors = spec.colors || DEFAULT_COLORS;
  const xKey = spec.xKey || 'label';
  const yKey = spec.yKey || 'value';
  const title = spec.title;

  if (!data.length) return null;

  const renderChart = () => {
    if (spec.layout === 'vertical' || (spec.type === 'bar' && spec.yKey === 'name')) {
      return (
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 16, left: 120, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis type="number" stroke="var(--text-secondary)" fontSize={11} />
          <YAxis type="category" dataKey={spec.yKey || 'name'} stroke="var(--text-secondary)" fontSize={10} width={110} />
          <Tooltip
            contentStyle={{ background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: 8 }}
            formatter={(v) => [Number(v).toLocaleString(), 'Value']}
          />
          <Bar dataKey={spec.xKey || 'value'} fill={colors[0]} radius={[0, 4, 4, 0]} />
        </BarChart>
      );
    }

    if (spec.type === 'pie') {
      return (
        <PieChart>
          <Pie data={data} dataKey={yKey} nameKey={xKey} cx="50%" cy="50%" outerRadius={100} label>
            {data.map((_, i) => (
              <Cell key={i} fill={colors[i % colors.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(v) => Number(v).toLocaleString()} />
          <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
        </PieChart>
      );
    }

    if (spec.type === 'line') {
      return (
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey={xKey} stroke="var(--text-secondary)" fontSize={11} />
          <YAxis stroke="var(--text-secondary)" fontSize={11} width={70} />
          <Tooltip formatter={(v) => Number(v).toLocaleString()} />
          <Line type="monotone" dataKey={yKey} stroke={colors[0]} strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      );
    }

    if (spec.type === 'area') {
      return (
        <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey={xKey} stroke="var(--text-secondary)" fontSize={11} />
          <YAxis stroke="var(--text-secondary)" fontSize={11} width={70} />
          <Tooltip formatter={(v) => Number(v).toLocaleString()} />
          <Area type="monotone" dataKey={yKey} stroke={colors[0]} fill={`${colors[0]}33`} />
        </AreaChart>
      );
    }

    return (
      <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey={xKey} stroke="var(--text-secondary)" fontSize={11} />
        <YAxis stroke="var(--text-secondary)" fontSize={11} width={70} />
        <Tooltip formatter={(v) => Number(v).toLocaleString()} />
        <Bar dataKey={yKey} fill={colors[0]} radius={[4, 4, 0, 0]} />
      </BarChart>
    );
  };

  return (
    <div>
      {title && (
        <h3 style={{ fontSize: '1rem', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          {title}
        </h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
}
