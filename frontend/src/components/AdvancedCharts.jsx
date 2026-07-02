import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Sankey, Treemap } from 'recharts';

// Box Plot Data Generator
function generateBoxPlotData(data) {
  if (!data || data.length === 0) return [];
  
  const values = data.map(d => d.value || d).filter(v => v != null);
  if (values.length === 0) return [];
  
  values.sort((a, b) => a - b);
  const q1 = values[Math.floor(values.length * 0.25)];
  const median = values[Math.floor(values.length * 0.5)];
  const q3 = values[Math.floor(values.length * 0.75)];
  const min = values[0];
  const max = values[values.length - 1];
  const iqr = q3 - q1;
  const lowerFence = q1 - 1.5 * iqr;
  const upperFence = q3 + 1.5 * iqr;
  
  const outliers = values.filter(v => v < lowerFence || v > upperFence);
  
  return [
    { name: 'Min', value: min, type: 'whisker' },
    { name: 'Q1', value: q1, type: 'box' },
    { name: 'Median', value: median, type: 'median' },
    { name: 'Q3', value: q3, type: 'box' },
    { name: 'Max', value: max, type: 'whisker' },
    ...outliers.map((v, i) => ({ name: `Outlier ${i + 1}`, value: v, type: 'outlier' })),
  ];
}

// Box Plot Component
export function BoxPlot({ data = [], title = 'Box Plot', height = 300 }) {
  const boxData = generateBoxPlotData(data);
  
  if (boxData.length === 0) {
    return <div style={{ textAlign: 'center', padding: '40px', color: 'var(--ea-text-secondary)' }}>No data available for box plot</div>;
  }
  
  return (
    <div style={{ width: '100%' }}>
      {title && <h4 style={{ marginBottom: '12px', fontSize: '0.9rem', color: 'var(--ea-text-secondary)' }}>{title}</h4>}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={boxData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
          <XAxis 
            dataKey="name" 
            stroke="var(--ea-text-secondary)" 
            fontSize={11}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis stroke="var(--ea-text-secondary)" fontSize={11} />
          <Tooltip 
            contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
            formatter={(value) => Number(value).toLocaleString()}
          />
          <Bar dataKey="value" fill="#3b82f6" />
        </BarChart>
      </ResponsiveContainer>
      <div style={{ fontSize: '0.75rem', color: 'var(--ea-text-secondary)', marginTop: '8px', textAlign: 'center' }}>
        Box shows Q1-Q3 (middle 50%), line is median, whiskers extend to min/max, dots are outliers
      </div>
    </div>
  );
}

// Sankey Diagram Component
export function SankeyDiagram({ data = {}, title = 'Sankey Diagram', height = 400 }) {
  // Transform data to Recharts Sankey format
  const { nodes = [], links = [] } = data;
  
  if (nodes.length === 0 || links.length === 0) {
    return <div style={{ textAlign: 'center', padding: '40px', color: 'var(--ea-text-secondary)' }}>No data available for Sankey diagram</div>;
  }
  
  const sankeyData = {
    nodes: nodes.map((node) => ({ name: node.name || node })),
    links: links.map(link => ({
      source: nodes.findIndex(n => (n.name || n) === link.source),
      target: nodes.findIndex(n => (n.name || n) === link.target),
      value: link.value || 1,
    })),
  };
  
  return (
    <div style={{ width: '100%' }}>
      {title && <h4 style={{ marginBottom: '12px', fontSize: '0.9rem', color: 'var(--ea-text-secondary)' }}>{title}</h4>}
      <ResponsiveContainer width="100%" height={height}>
        <Sankey
          data={sankeyData}
          node={{ fill: '#3b82f6' }}
          link={{ fill: '#93c5fd', stroke: '#3b82f6' }}
          margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
        >
          <Tooltip 
            contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
          />
        </Sankey>
      </ResponsiveContainer>
    </div>
  );
}

// Word Cloud Component (simplified version using bar chart)
export function WordCloudChart({ data = [], title = 'Word Cloud', height = 300 }) {
  if (!data || data.length === 0) {
    return <div style={{ textAlign: 'center', padding: '40px', color: 'var(--ea-text-secondary)' }}>No data available for word cloud</div>;
  }
  
  const sortedData = [...data].sort((a, b) => (b.value || b.count || 0) - (a.value || a.count || 0)).slice(0, 20);
  
  return (
    <div style={{ width: '100%' }}>
      {title && <h4 style={{ marginBottom: '12px', fontSize: '0.9rem', color: 'var(--ea-text-secondary)' }}>{title}</h4>}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={sortedData} layout="vertical" margin={{ top: 20, right: 30, left: 100, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--ea-border)" />
          <XAxis type="number" stroke="var(--ea-text-secondary)" fontSize={11} />
          <YAxis dataKey="name" type="category" stroke="var(--ea-text-secondary)" fontSize={11} width={100} />
          <Tooltip 
            contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
            formatter={(value) => Number(value).toLocaleString()}
          />
          <Bar dataKey="value" fill="#8b5cf6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// Treemap Component
export function TreemapChart({ data = [], title = 'Treemap', height = 300 }) {
  if (!data || data.length === 0) {
    return <div style={{ textAlign: 'center', padding: '40px', color: 'var(--ea-text-secondary)' }}>No data available for treemap</div>;
  }
  
  const _colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899', '#84cc16'];
  
  return (
    <div style={{ width: '100%' }}>
      {title && <h4 style={{ marginBottom: '12px', fontSize: '0.9rem', color: 'var(--ea-text-secondary)' }}>{title}</h4>}
      <ResponsiveContainer width="100%" height={height}>
        <Treemap
          data={data}
          dataKey="value"
          aspectRatio={4 / 3}
          stroke="var(--ea-border)"
          fill="var(--ea-primary)"
        >
          <Tooltip 
            contentStyle={{ background: 'var(--ea-bg-card)', border: '1px solid var(--ea-border)', borderRadius: 8 }}
            formatter={(value, name) => [Number(value).toLocaleString(), name]}
          />
        </Treemap>
      </ResponsiveContainer>
    </div>
  );
}

// Export all advanced chart components
export default {
  BoxPlot,
  SankeyDiagram,
  WordCloudChart,
  TreemapChart,
  generateBoxPlotData,
};