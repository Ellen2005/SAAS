import React, { useMemo } from 'react';
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const KPI_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'];

/**
 * Lazy-loaded forecast chart component using recharts.
 * Separated into its own chunk so it doesn't bloat the main bundle.
 */
const ForecastChart = ({ forecasts, height = 280 }) => {
  const { chartData, kpiNames } = useMemo(() => {
    if (!forecasts || !forecasts.length) return { chartData: [], kpiNames: [] };
    const dateMap = {};
    forecasts.forEach((f) => {
      if (!dateMap[f.forecast_date]) dateMap[f.forecast_date] = { date: f.forecast_date };
      dateMap[f.forecast_date][f.kpi_name.replace(/_/g, ' ')] = f.predicted_value;
    });
    const data = Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date));
    const names = [...new Set(forecasts.map((f) => f.kpi_name.replace(/_/g, ' ')))];
    return { chartData: data, kpiNames: names };
  }, [forecasts]);

  if (!chartData.length) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ea-text-secondary)' }}>
        No forecast data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <defs>
          {kpiNames.map((n, i) => (
            <linearGradient key={n} id={`fc-${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={KPI_COLORS[i % KPI_COLORS.length]} stopOpacity={0.25} />
              <stop offset="95%" stopColor={KPI_COLORS[i % KPI_COLORS.length]} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
        <XAxis dataKey="date" stroke="var(--ea-text-secondary)" fontSize={11} tickFormatter={(v) => v.slice(5)} />
        <YAxis stroke="var(--ea-text-secondary)" fontSize={11} width={70} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
        <Tooltip
          contentStyle={{
            background: 'var(--ea-bg-card)',
            border: '1px solid var(--ea-border)',
            borderRadius: 8,
            fontSize: '0.82rem',
          }}
          formatter={(value, name) => [Number(value).toLocaleString(), name]}
          labelFormatter={(l) => `Date: ${l}`}
        />
        <Legend wrapperStyle={{ fontSize: '0.82rem', paddingTop: 12 }} />
        {kpiNames.map((n, i) => (
          <Area
            key={n}
            type="monotone"
            dataKey={n}
            name={n}
            stroke={KPI_COLORS[i % KPI_COLORS.length]}
            fill={`url(#fc-${i})`}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default ForecastChart;