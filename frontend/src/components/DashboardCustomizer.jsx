import React, { useState, useEffect } from 'react';
import { GripVertical, Plus, Trash2, Settings2, Save, RotateCcw, X } from 'lucide-react';

const DEFAULT_LAYOUT = {
  widgets: [
    { id: 'kpi-1', type: 'kpi', name: 'Total Contributions', x: 0, y: 0, w: 3, h: 1 },
    { id: 'kpi-2', type: 'kpi', name: 'Pension Disbursement', x: 3, y: 0, w: 3, h: 1 },
    { id: 'kpi-3', type: 'kpi', name: 'AT/MP Frequency', x: 6, y: 0, w: 3, h: 1 },
    { id: 'kpi-4', type: 'kpi', name: 'Contributions by Region', x: 9, y: 0, w: 3, h: 1 },
    { id: 'chart-1', type: 'chart', name: 'KPI Trends', x: 0, y: 1, w: 6, h: 2 },
    { id: 'chart-2', type: 'chart', name: 'Forecasts', x: 6, y: 1, w: 6, h: 2 },
    { id: 'map-1', type: 'map', name: 'Regional Map', x: 0, y: 3, w: 12, h: 2 },
  ],
};

export default function DashboardCustomizer({ isOpen, onClose, onSave, currentLayout }) {
  const [layout, setLayout] = useState(currentLayout || DEFAULT_LAYOUT);
  const [selectedWidget, setSelectedWidget] = useState(null);
  const [_isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    if (currentLayout) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLayout(currentLayout);
    }
  }, [currentLayout]);

  const handleAddWidget = (type) => {
    const newWidget = {
      id: `${type}-${Date.now()}`,
      type,
      name: `New ${type.charAt(0).toUpperCase() + type.slice(1)}`,
      x: 0,
      y: layout.widgets.length,
      w: type === 'map' ? 12 : 3,
      h: type === 'map' ? 2 : 1,
    };
    setLayout({
      ...layout,
      widgets: [...layout.widgets, newWidget],
    });
  };

  const handleRemoveWidget = (widgetId) => {
    setLayout({
      ...layout,
      widgets: layout.widgets.filter(w => w.id !== widgetId),
    });
  };

  const handleUpdateWidget = (widgetId, updates) => {
    setLayout({
      ...layout,
      widgets: layout.widgets.map(w =>
        w.id === widgetId ? { ...w, ...updates } : w
      ),
    });
  };

  const handleReset = () => {
    setLayout(DEFAULT_LAYOUT);
  };

  const handleSave = () => {
    onSave?.(layout);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 10000,
      padding: '20px',
      backdropFilter: 'blur(4px)',
    }}>
      <div style={{
        background: 'var(--ea-bg-card)',
        borderRadius: 'var(--ea-radius-lg)',
        padding: '24px',
        maxWidth: '900px',
        width: '100%',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
        border: '1px solid var(--ea-border)',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '24px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Settings2 size={24} color="var(--ea-primary)" />
            <h2 style={{ margin: 0, fontSize: '1.3rem' }}>Customize Dashboard</h2>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--ea-text-secondary)',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Section visibility summary */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          {['kpi', 'chart', 'map'].map(type => {
            const active = layout.widgets.some(w => w.type === type);
            const labels = { kpi: '📊 KPI Cards', chart: '📈 Charts', map: '🗺️ Regional Map' };
            return (
              <span key={type} style={{
                padding: '4px 12px', borderRadius: 20, fontSize: '0.78rem', fontWeight: 600,
                background: active ? 'rgba(59,130,246,0.12)' : 'var(--ea-bg-hover)',
                color: active ? 'var(--ea-primary)' : 'var(--ea-text-secondary)',
                border: `1px solid ${active ? 'var(--ea-primary)' : 'var(--ea-border)'}`,
              }}>
                {active ? '✓' : '✗'} {labels[type]}
              </span>
            );
          })}
        </div>

        {/* Add Widget Buttons */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
          <button className="ea-btn ea-btn-secondary" onClick={() => handleAddWidget('kpi')} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Plus size={16} /> Add KPI Card
          </button>
          <button className="ea-btn ea-btn-secondary" onClick={() => handleAddWidget('chart')} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Plus size={16} /> Add Chart
          </button>
          <button className="ea-btn ea-btn-secondary" onClick={() => handleAddWidget('map')} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Plus size={16} /> Add Map
          </button>
        </div>

        {/* Widget List */}
        <div style={{
          display: 'grid',
          gap: '12px',
          marginBottom: '24px',
        }}>
          {layout.widgets.map((widget) => (
            <div
              key={widget.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px',
                background: 'var(--ea-bg-hover)',
                borderRadius: '8px',
                border: selectedWidget === widget.id
                  ? '2px solid var(--ea-primary)'
                  : '1px solid var(--ea-border)',
                cursor: 'grab',
                transition: 'all 0.2s',
              }}
              onClick={() => setSelectedWidget(widget.id)}
              draggable
              onDragStart={(e) => {
                setIsDragging(true);
                e.dataTransfer.setData('text/plain', widget.id);
              }}
              onDragEnd={() => setIsDragging(false)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const draggedId = e.dataTransfer.getData('text/plain');
                if (draggedId !== widget.id) {
                  const draggedIndex = layout.widgets.findIndex(w => w.id === draggedId);
                  const targetIndex = layout.widgets.findIndex(w => w.id === widget.id);
                  const newWidgets = [...layout.widgets];
                  const [removed] = newWidgets.splice(draggedIndex, 1);
                  newWidgets.splice(targetIndex, 0, removed);
                  setLayout({ ...layout, widgets: newWidgets });
                }
              }}
            >
              <GripVertical size={16} color="var(--ea-text-secondary)" style={{ cursor: 'grab' }} />
              
              <div style={{ flex: 1 }}>
                <input
                  type="text"
                  value={widget.name}
                  onChange={(e) => handleUpdateWidget(widget.id, { name: e.target.value })}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--ea-text-primary)',
                    fontSize: '0.95rem',
                    fontWeight: 500,
                    width: '100%',
                    outline: 'none',
                  }}
                />
                <div style={{
                  fontSize: '0.75rem',
                  color: 'var(--ea-text-secondary)',
                  marginTop: '4px',
                }}>
                  {widget.type.toUpperCase()} • Size: {widget.w}×{widget.h}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '4px' }}>
                <select
                  value={widget.w}
                  onChange={(e) => handleUpdateWidget(widget.id, { w: parseInt(e.target.value) })}
                  style={{
                    background: 'var(--ea-bg)',
                    border: '1px solid var(--ea-border)',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    fontSize: '0.8rem',
                    color: 'var(--ea-text-primary)',
                    cursor: 'pointer',
                  }}
                >
                  {[1, 2, 3, 4, 6, 8, 12].map(size => (
                    <option key={size} value={size}>{size}w</option>
                  ))}
                </select>
                <select
                  value={widget.h}
                  onChange={(e) => handleUpdateWidget(widget.id, { h: parseInt(e.target.value) })}
                  style={{
                    background: 'var(--ea-bg)',
                    border: '1px solid var(--ea-border)',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    fontSize: '0.8rem',
                    color: 'var(--ea-text-primary)',
                    cursor: 'pointer',
                  }}
                >
                  {[1, 2, 3, 4].map(size => (
                    <option key={size} value={size}>{size}h</option>
                  ))}
                </select>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleRemoveWidget(widget.id);
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '6px',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--ea-danger)',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = 'rgba(239, 68, 68, 0.1)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = 'transparent';
                }}
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>

        {layout.widgets.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: '48px',
            color: 'var(--ea-text-secondary)',
          }}>
            <Settings2 size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
            <p>No widgets configured. Add widgets above to customize your dashboard.</p>
          </div>
        )}

        {/* Actions */}
        <div style={{
          display: 'flex',
          gap: '12px',
          justifyContent: 'space-between',
          paddingTop: '20px',
          borderTop: '1px solid var(--ea-border)',
        }}>
          <button
            className="ea-btn ea-btn-ghost"
            onClick={handleReset}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RotateCcw size={16} /> Reset to Default
          </button>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button className="ea-btn ea-btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              className="ea-btn ea-btn-primary"
              onClick={handleSave}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Save size={16} /> Save Layout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}