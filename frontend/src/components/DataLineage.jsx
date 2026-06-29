import React, { useState, useEffect } from 'react';
import { GitBranch, Database, Table, ArrowRight, ChevronDown, ChevronRight, Info, ZoomIn, ZoomOut, Maximize, Activity, FileText, Layout } from 'lucide-react';

// Sample data lineage structure
const SAMPLE_LINEAGE = {
  nodes: [
    { id: 'source-1', name: 'Oracle CNPS DB', type: 'source', icon: 'database' },
    { id: 'table-1', name: 'contributions', type: 'table', icon: 'table' },
    { id: 'table-2', name: 'employers', type: 'table', icon: 'table' },
    { id: 'table-3', name: 'regions', type: 'table', icon: 'table' },
    { id: 'transform-1', name: 'ETL Pipeline', type: 'transform', icon: 'git-branch' },
    { id: 'kpi-1', name: 'total_contributions', type: 'kpi', icon: 'activity' },
    { id: 'kpi-2', name: 'collection_rate', type: 'kpi', icon: 'activity' },
    { id: 'kpi-3', name: 'regional_share', type: 'kpi', icon: 'activity' },
    { id: 'report-1', name: 'Daily Report', type: 'report', icon: 'file-text' },
    { id: 'dashboard-1', name: 'Dashboard', type: 'dashboard', icon: 'layout' },
  ],
  edges: [
    { from: 'source-1', to: 'table-1', label: 'reads' },
    { from: 'source-1', to: 'table-2', label: 'reads' },
    { from: 'source-1', to: 'table-3', label: 'reads' },
    { from: 'table-1', to: 'transform-1', label: 'transforms' },
    { from: 'table-2', to: 'transform-1', label: 'joins' },
    { from: 'table-3', to: 'transform-1', label: 'joins' },
    { from: 'transform-1', to: 'kpi-1', label: 'calculates' },
    { from: 'transform-1', to: 'kpi-2', label: 'calculates' },
    { from: 'transform-1', to: 'kpi-3', label: 'calculates' },
    { from: 'kpi-1', to: 'report-1', label: 'includes' },
    { from: 'kpi-2', to: 'report-1', label: 'includes' },
    { from: 'kpi-1', to: 'dashboard-1', label: 'displays' },
    { from: 'kpi-2', to: 'dashboard-1', label: 'displays' },
    { from: 'kpi-3', to: 'dashboard-1', label: 'displays' },
  ],
};

const NODE_COLORS = {
  source: '#8b5cf6',
  table: '#3b82f6',
  transform: '#f59e0b',
  kpi: '#10b981',
  report: '#ef4444',
  dashboard: '#06b6d4',
};

const NODE_ICONS = {
  database: <Database size={16} />,
  table: <Table size={16} />,
  'git-branch': <GitBranch size={16} />,
  activity: <Activity size={16} />,
  'file-text': <FileText size={16} />,
  layout: <Layout size={16} />,
};

export default function DataLineage({ data = SAMPLE_LINEAGE, onNodeClick, height = 600 }) {
  const [selectedNode, setSelectedNode] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [expandedNodes, setExpandedNodes] = useState(new Set(['source-1', 'transform-1']));

  const handleNodeClick = (node) => {
    setSelectedNode(node);
    onNodeClick?.(node);
  };

  const toggleExpand = (nodeId) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId);
    } else {
      newExpanded.add(nodeId);
    }
    setExpandedNodes(newExpanded);
  };

  const getConnectedNodes = (nodeId) => {
    const incoming = data.edges.filter(e => e.to === nodeId).map(e => e.from);
    const outgoing = data.edges.filter(e => e.from === nodeId).map(e => e.to);
    return { incoming, outgoing };
  };

  const renderNode = (node) => {
    const isExpanded = expandedNodes.has(node.id);
    const { incoming, outgoing } = getConnectedNodes(node.id);
    const hasChildren = outgoing.length > 0;
    const color = NODE_COLORS[node.type] || '#6b7280';

    return (
      <div
        key={node.id}
        style={{
          display: 'inline-flex',
          flexDirection: 'column',
          alignItems: 'center',
          margin: '8px',
          padding: '12px',
          background: selectedNode?.id === node.id ? 'var(--ea-primary)' : 'var(--ea-bg-card)',
          border: `2px solid ${selectedNode?.id === node.id ? 'var(--ea-primary)' : color}`,
          borderRadius: '8px',
          cursor: 'pointer',
          minWidth: '120px',
          transition: 'all 0.2s',
          transform: 'none',
          transformOrigin: 'center',
          fontSize: `${zoom * 100}%`,
        }}
        onClick={() => handleNodeClick(node)}
      >
        {hasChildren && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleExpand(node.id);
            }}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: '2px',
              marginBottom: '4px',
              color: 'var(--ea-text-secondary)',
            }}
          >
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        )}
        
        <div style={{
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          background: color,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          marginBottom: '8px',
        }}>
          {NODE_ICONS[node.icon] || <Database size={16} />}
        </div>
        
        <div style={{
          fontSize: '0.8rem',
          fontWeight: 600,
          color: selectedNode?.id === node.id ? 'white' : 'var(--ea-text-primary)',
          textAlign: 'center',
          maxWidth: '100px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {node.name}
        </div>
        
        <div style={{
          fontSize: '0.65rem',
          color: selectedNode?.id === node.id ? 'rgba(255,255,255,0.8)' : 'var(--ea-text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}>
          {node.type}
        </div>
      </div>
    );
  };

  const renderEdge = (edge) => {
    const fromNode = data.nodes.find(n => n.id === edge.from);
    const toNode = data.nodes.find(n => n.id === edge.to);
    if (!fromNode || !toNode) return null;

    return (
      <div key={`${edge.from}-${edge.to}`} style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '4px 8px',
        fontSize: '0.7rem',
        color: 'var(--ea-text-secondary)',
        background: 'var(--ea-bg-hover)',
        borderRadius: '4px',
        margin: '0 4px',
      }}>
        <ArrowRight size={12} style={{ margin: '0 4px' }} />
        {edge.label}
      </div>
    );
  };

  return (
    <div style={{
      background: 'var(--ea-bg)',
      borderRadius: 'var(--ea-radius-lg)',
      border: '1px solid var(--ea-border)',
      padding: '20px',
      height,
      overflow: 'auto',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px',
      }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <GitBranch size={20} color="var(--ea-primary)" /> Data Lineage
          </h3>
          <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: 'var(--ea-text-secondary)' }}>
            Trace data flow from source to dashboard
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setZoom(Math.max(0.5, zoom - 0.1))}
            style={{
              padding: '6px 10px',
              background: 'var(--ea-bg-hover)',
              border: '1px solid var(--ea-border)',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              color: 'var(--ea-text-primary)',
            }}
          >
            <ZoomOut size={14} />
          </button>
          <button
            onClick={() => setZoom(1)}
            style={{
              padding: '6px 10px',
              background: 'var(--ea-bg-hover)',
              border: '1px solid var(--ea-border)',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              color: 'var(--ea-text-primary)',
              fontSize: '0.8rem',
            }}
          >
            {Math.round(zoom * 100)}%
          </button>
          <button
            onClick={() => setZoom(Math.min(1.5, zoom + 0.1))}
            style={{
              padding: '6px 10px',
              background: 'var(--ea-bg-hover)',
              border: '1px solid var(--ea-border)',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              color: 'var(--ea-text-primary)',
            }}
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={() => setZoom(1)}
            style={{
              padding: '6px 10px',
              background: 'var(--ea-bg-hover)',
              border: '1px solid var(--ea-border)',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              color: 'var(--ea-text-primary)',
            }}
          >
            <Maximize size={14} />
          </button>
        </div>
      </div>

      {/* Legend */}
      <div style={{
        display: 'flex',
        gap: '12px',
        marginBottom: '20px',
        flexWrap: 'wrap',
        padding: '12px',
        background: 'var(--ea-bg-hover)',
        borderRadius: '8px',
      }}>
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: color }} />
            <span style={{ textTransform: 'capitalize' }}>{type}</span>
          </div>
        ))}
      </div>

      {/* Lineage Graph */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '8px',
        transform: 'none',
        transformOrigin: 'top center',
        transition: 'opacity 0.2s',
        maxWidth: '100%',
        overflow: 'auto',
      }}>
        {/* Source Layer */}
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center' }}>
          {data.nodes.filter(n => n.type === 'source').map(node => renderNode(node))}
        </div>

        {/* Edges */}
        {data.edges.filter(e => e.from.startsWith('source-')).map(edge => renderEdge(edge))}

        {/* Table Layer */}
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center' }}>
          {data.nodes.filter(n => n.type === 'table').map(node => renderNode(node))}
        </div>

        {/* Edges */}
        {data.edges.filter(e => e.from.startsWith('table-')).map(edge => renderEdge(edge))}

        {/* Transform Layer */}
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center' }}>
          {data.nodes.filter(n => n.type === 'transform').map(node => renderNode(node))}
        </div>

        {/* Edges */}
        {data.edges.filter(e => e.from.startsWith('transform-')).map(edge => renderEdge(edge))}

        {/* KPI Layer */}
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center' }}>
          {data.nodes.filter(n => n.type === 'kpi').map(node => renderNode(node))}
        </div>

        {/* Edges */}
        {data.edges.filter(e => e.from.startsWith('kpi-')).map(edge => renderEdge(edge))}

        {/* Output Layer */}
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center' }}>
          {data.nodes.filter(n => ['report', 'dashboard'].includes(n.type)).map(node => renderNode(node))}
        </div>
      </div>

      {/* Selected Node Details */}
      {selectedNode && (
        <div style={{
          marginTop: '20px',
          padding: '16px',
          background: 'var(--ea-bg-hover)',
          borderRadius: '8px',
          border: '1px solid var(--ea-border)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              background: NODE_COLORS[selectedNode.type],
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
            }}>
              {NODE_ICONS[selectedNode.icon] || <Database size={20} />}
            </div>
            <div>
              <h4 style={{ margin: 0, fontSize: '1rem' }}>{selectedNode.name}</h4>
              <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: 'var(--ea-text-secondary)', textTransform: 'uppercase' }}>
                {selectedNode.type}
              </p>
            </div>
          </div>
          
          <div style={{ fontSize: '0.85rem', color: 'var(--ea-text-secondary)' }}>
            <div style={{ marginBottom: '8px' }}>
              <strong>Incoming:</strong> {getConnectedNodes(selectedNode.id).incoming.length} connections
            </div>
            <div>
              <strong>Outgoing:</strong> {getConnectedNodes(selectedNode.id).outgoing.length} connections
            </div>
          </div>
          
          <button
            onClick={() => setSelectedNode(null)}
            style={{
              marginTop: '12px',
              padding: '6px 12px',
              background: 'var(--ea-bg)',
              border: '1px solid var(--ea-border)',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              color: 'var(--ea-text-primary)',
            }}
          >
            Close Details
          </button>
        </div>
      )}
    </div>
  );
}