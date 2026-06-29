import React, { useState, useCallback } from 'react';
import { GripVertical, X, Plus, BarChart3, Download, FileText } from 'lucide-react';
import { apiJson } from '../lib/api';
import ChartRenderer from './ChartRenderer';

const CHART_TYPES = [
  { id: 'bar', name: 'Bar Chart', icon: '📊' },
  { id: 'line', name: 'Line Chart', icon: '📈' },
  { id: 'pie', name: 'Pie Chart', icon: '🥧' },
  { id: 'area', name: 'Area Chart', icon: '🏔️' },
  { id: 'horizontalBar', name: 'Horizontal Bar', icon: '📊' },
  { id: 'doughnut', name: 'Doughnut', icon: '🍩' },
  { id: 'radar', name: 'Radar', icon: '🎯' },
  { id: 'scatter', name: 'Scatter', icon: '✨' },
  { id: 'heatmap', name: 'Heatmap', icon: '🔥' },
  { id: 'treemap', name: 'Treemap', icon: '🌳' },
];

const AVAILABLE_FIELDS = [
  { name: 'kpi_name', label: 'KPI Name', type: 'dimension' },
  { name: 'value', label: 'Value', type: 'measure' },
  { name: 'recorded_at', label: 'Date', type: 'dimension' },
  { name: 'status', label: 'Status', type: 'dimension' },
  { name: 'dod_pct', label: 'Day-over-Day %', type: 'measure' },
  { name: 'wow_pct', label: 'Week-over-Week %', type: 'measure' },
];

export default function DragDropReportBuilder({ onClose, onSave }) {
  const [widgets, setWidgets] = useState([]);
  const [draggedField, setDraggedField] = useState(null);
  const [reportName, setReportName] = useState('My Custom Report');
  const [generating, setGenerating] = useState(false);

  const addWidget = useCallback(() => {
    const newWidget = {
      id: Date.now(),
      chartType: 'bar',
      title: `Chart ${widgets.length + 1}`,
      xAxis: [],
      yAxis: [],
      filters: [],
    };
    setWidgets([...widgets, newWidget]);
  }, [widgets]);

  const updateWidget = useCallback((id, updates) => {
    setWidgets(widgets.map(w => w.id === id ? { ...w, ...updates } : w));
  }, [widgets]);

  const removeWidget = useCallback((id) => {
    setWidgets(widgets.filter(w => w.id !== id));
  }, [widgets]);

  const handleDragStart = (field) => {
    setDraggedField(field);
  };

  const handleDrop = (widgetId, axis) => {
    if (!draggedField) return;
    const widget = widgets.find(w => w.id === widgetId);
    if (!widget) return;

    const currentAxis = widget[axis] || [];
    if (!currentAxis.find(f => f.name === draggedField.name)) {
      updateWidget(widgetId, {
        [axis]: [...currentAxis, draggedField]
      });
    }
    setDraggedField(null);
  };

  const removeField = (widgetId, axis, fieldName) => {
    const widget = widgets.find(w => w.id === widgetId);
    if (!widget) return;
    updateWidget(widgetId, {
      [axis]: (widget[axis] || []).filter(f => f.name !== fieldName)
    });
  };

  const generateReport = async () => {
    setGenerating(true);
    try {
      const reportData = {
        name: reportName,
        widgets: widgets.map(w => ({
          chartType: w.chartType,
          title: w.title,
          xAxis: w.xAxis.map(f => f.name),
          yAxis: w.yAxis.map(f => f.name),
        })),
      };

      const result = await apiJson('/api/reports/custom', {
        method: 'POST',
        body: JSON.stringify({
          instruction: `Generate report: ${reportName}`,
          report_scope: 'my_department',
          format_type: 'detailed',
        }),
      });

      if (onSave) {
        onSave(result);
      }
    } catch (error) {
      console.error('Failed to generate report:', error);
    } finally {
      setGenerating(false);
    }
  };

  const exportReport = async (format) => {
    try {
      if (format === 'pdf') {
        window.open(`${import.meta.env.VITE_API_URL || ''}/api/export/report/pdf?report_type=dg`, '_blank', 'noopener,noreferrer');
      } else if (format === 'excel') {
        window.open(`${import.meta.env.VITE_API_URL || ''}/api/export/excel?table=kpi_results`, '_blank', 'noopener,noreferrer');
      } else if (format === 'csv') {
        window.open(`${import.meta.env.VITE_API_URL || ''}/api/export/csv?table=kpi_results`, '_blank', 'noopener,noreferrer');
      }
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.8)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: 20,
    }}>
      <div style={{
        background: 'var(--surface-color)',
        borderRadius: 12,
        width: '100%',
        maxWidth: 1400,
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.3rem' }}>📊 Report Builder</h2>
            <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Drag fields to build your custom report
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => exportReport('pdf')}
              className="btn btn-outline"
              style={{ display: 'flex', gap: 6, alignItems: 'center' }}
            >
              <Download size={16} /> PDF
            </button>
            <button
              onClick={() => exportReport('excel')}
              className="btn btn-outline"
              style={{ display: 'flex', gap: 6, alignItems: 'center' }}
            >
              <Download size={16} /> Excel
            </button>
            <button
              onClick={generateReport}
              disabled={generating || widgets.length === 0}
              className="btn btn-primary"
              style={{ display: 'flex', gap: 6, alignItems: 'center' }}
            >
              <FileText size={16} /> {generating ? 'Generating...' : 'Generate Report'}
            </button>
            <button onClick={onClose} className="btn btn-outline" style={{ padding: '8px 12px' }}>
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Left Sidebar - Available Fields */}
          <div style={{
            width: 250,
            borderRight: '1px solid var(--border-color)',
            padding: 16,
            overflowY: 'auto',
          }}>
            <h3 style={{ fontSize: '0.9rem', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Available Fields
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {AVAILABLE_FIELDS.map(field => (
                <div
                  key={field.name}
                  draggable
                  onDragStart={() => handleDragStart(field)}
                  style={{
                    padding: '10px 12px',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 6,
                    cursor: 'grab',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    fontSize: '0.85rem',
                  }}
                >
                  <GripVertical size={14} style={{ opacity: 0.5 }} />
                  <span style={{ flex: 1 }}>{field.label}</span>
                  <span style={{
                    fontSize: '0.7rem',
                    padding: '2px 6px',
                    borderRadius: 4,
                    background: field.type === 'measure' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(59, 130, 246, 0.2)',
                    color: field.type === 'measure' ? '#10b981' : '#3b82f6',
                  }}>
                    {field.type}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Center - Report Canvas */}
          <div style={{
            flex: 1,
            padding: 20,
            overflowY: 'auto',
          }}>
            <div style={{ marginBottom: 16 }}>
              <input
                type="text"
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
                style={{
                  fontSize: '1.1rem',
                  fontWeight: 600,
                  background: 'transparent',
                  border: 'none',
                  borderBottom: '2px solid var(--border-color)',
                  padding: '8px 0',
                  width: '100%',
                  maxWidth: 400,
                }}
              />
            </div>

            {widgets.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: 60,
                color: 'var(--text-secondary)',
              }}>
                <BarChart3 size={48} style={{ marginBottom: 16, opacity: 0.5 }} />
                <h3 style={{ marginBottom: 8 }}>No widgets yet</h3>
                <p style={{ marginBottom: 24 }}>Click "Add Widget" to start building your report</p>
                <button onClick={addWidget} className="btn btn-primary" style={{ display: 'inline-flex', gap: 8 }}>
                  <Plus size={18} /> Add Widget
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {widgets.map((widget, idx) => (
                  <div
                    key={widget.id}
                    style={{
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 8,
                      padding: 16,
                    }}
                  >
                    {/* Widget Header */}
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: 12,
                    }}>
                      <input
                        type="text"
                        value={widget.title}
                        onChange={(e) => updateWidget(widget.id, { title: e.target.value })}
                        style={{
                          fontSize: '1rem',
                          fontWeight: 600,
                          background: 'transparent',
                          border: 'none',
                          borderBottom: '1px solid var(--border-color)',
                          padding: '4px 0',
                          width: 300,
                        }}
                      />
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <select
                          value={widget.chartType}
                          onChange={(e) => updateWidget(widget.id, { chartType: e.target.value })}
                          style={{
                            background: 'var(--surface-color)',
                            border: '1px solid var(--border-color)',
                            borderRadius: 4,
                            padding: '4px 8px',
                            fontSize: '0.85rem',
                          }}
                        >
                          {CHART_TYPES.map(ct => (
                            <option key={ct.id} value={ct.id}>{ct.icon} {ct.name}</option>
                          ))}
                        </select>
                        <button
                          onClick={() => removeWidget(widget.id)}
                          style={{
                            background: 'rgba(239, 68, 68, 0.1)',
                            border: 'none',
                            borderRadius: 4,
                            padding: '4px 8px',
                            cursor: 'pointer',
                            color: '#ef4444',
                          }}
                        >
                          <X size={16} />
                        </button>
                      </div>
                    </div>

                    {/* Drop Zones */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                      <div
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={() => handleDrop(widget.id, 'xAxis')}
                        style={{
                          minHeight: 60,
                          border: '2px dashed var(--border-color)',
                          borderRadius: 6,
                          padding: 8,
                          background: 'rgba(59, 130, 246, 0.05)',
                        }}
                      >
                        <div style={{
                          fontSize: '0.75rem',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          color: 'var(--text-secondary)',
                          marginBottom: 6,
                        }}>
                          X Axis (Dimensions)
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {(widget.xAxis || []).map(field => (
                            <span
                              key={field.name}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 4,
                                padding: '4px 8px',
                                background: 'rgba(59, 130, 246, 0.2)',
                                borderRadius: 4,
                                fontSize: '0.8rem',
                              }}
                            >
                              {field.label}
                              <button
                                onClick={() => removeField(widget.id, 'xAxis', field.name)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
                              >
                                <X size={12} />
                              </button>
                            </span>
                          ))}
                        </div>
                      </div>

                      <div
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={() => handleDrop(widget.id, 'yAxis')}
                        style={{
                          minHeight: 60,
                          border: '2px dashed var(--border-color)',
                          borderRadius: 6,
                          padding: 8,
                          background: 'rgba(16, 185, 129, 0.05)',
                        }}
                      >
                        <div style={{
                          fontSize: '0.75rem',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          color: 'var(--text-secondary)',
                          marginBottom: 6,
                        }}>
                          Y Axis (Measures)
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {(widget.yAxis || []).map(field => (
                            <span
                              key={field.name}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 4,
                                padding: '4px 8px',
                                background: 'rgba(16, 185, 129, 0.2)',
                                borderRadius: 4,
                                fontSize: '0.8rem',
                              }}
                            >
                              {field.label}
                              <button
                                onClick={() => removeField(widget.id, 'yAxis', field.name)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
                              >
                                <X size={12} />
                              </button>
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Chart Preview */}
                    {widget.xAxis.length > 0 && widget.yAxis.length > 0 && (
                      <div style={{
                        background: 'rgba(0,0,0,0.2)',
                        borderRadius: 6,
                        padding: 16,
                        minHeight: 200,
                      }}>
                        <ChartRenderer
                          spec={{
                            type: widget.chartType,
                            title: widget.title,
                            data: [], // Would be populated with actual data
                            xKey: widget.xAxis[0]?.name,
                            yKey: widget.yAxis[0]?.name,
                          }}
                          height={250}
                        />
                      </div>
                    )}
                  </div>
                ))}

                <button
                  onClick={addWidget}
                  className="btn btn-outline"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    padding: 16,
                    borderStyle: 'dashed',
                  }}
                >
                  <Plus size={18} /> Add Widget
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}