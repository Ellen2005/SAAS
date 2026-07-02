import React, { useState } from 'react';
import { History, GitCompare, RotateCcw, Eye, Download, FileText, Clock, User, Tag, ChevronRight, ChevronDown } from 'lucide-react';

// Version Control Component for Reports
export default function ReportVersionControl({ versions = [], onRestore, onCompare, onView, height = 600 }) {
  const [selectedVersions, setSelectedVersions] = useState([]);
  const [expandedVersion, setExpandedVersion] = useState(null);
  const [showCompare, setShowCompare] = useState(false);

  const handleSelectVersion = (versionId) => {
    if (selectedVersions.includes(versionId)) {
      setSelectedVersions(selectedVersions.filter(id => id !== versionId));
    } else if (selectedVersions.length < 2) {
      setSelectedVersions([...selectedVersions, versionId]);
    }
  };

  const handleCompare = () => {
    if (selectedVersions.length === 2 && onCompare) {
      onCompare(selectedVersions[0], selectedVersions[1]);
      setShowCompare(true);
    }
  };

  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getChangeTypeColor = (changeType) => {
    switch (changeType) {
      case 'created': return '#10b981';
      case 'modified': return '#f59e0b';
      case 'major': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const renderVersionDiff = (version1, version2) => {
    // Simplified diff view - in production, use a proper diff library
    return (
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '16px',
        marginTop: '16px',
      }}>
        <div>
          <h4 style={{ margin: '0 0 12px', fontSize: '0.9rem', color: 'var(--ea-text-secondary)' }}>
            Version {version1.version} - {formatDate(version1.created_at)}
          </h4>
          <div style={{
            padding: '12px',
            background: 'var(--ea-bg-hover)',
            borderRadius: '8px',
            fontSize: '0.85rem',
            lineHeight: 1.6,
            maxHeight: '400px',
            overflow: 'auto',
            whiteSpace: 'pre-wrap',
          }}>
            {version1.narrative || 'No content'}
          </div>
        </div>
        
        <div>
          <h4 style={{ margin: '0 0 12px', fontSize: '0.9rem', color: 'var(--ea-text-secondary)' }}>
            Version {version2.version} - {formatDate(version2.created_at)}
          </h4>
          <div style={{
            padding: '12px',
            background: 'var(--ea-bg-hover)',
            borderRadius: '8px',
            fontSize: '0.85rem',
            lineHeight: 1.6,
            maxHeight: '400px',
            overflow: 'auto',
            whiteSpace: 'pre-wrap',
          }}>
            {version2.narrative || 'No content'}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={{
      background: 'var(--ea-bg)',
      borderRadius: 'var(--ea-radius-lg)',
      border: '1px solid var(--ea-border)',
      padding: '24px',
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
            <History size={20} color="var(--ea-primary)" />
            Version History
          </h3>
          <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: 'var(--ea-text-secondary)' }}>
            Track changes and restore previous versions
          </p>
        </div>
        
        {selectedVersions.length === 2 && (
          <button
            onClick={handleCompare}
            className="ea-btn ea-btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <GitCompare size={16} />
            Compare Selected
          </button>
        )}
      </div>

      {/* Version Timeline */}
      {versions.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '48px',
          color: 'var(--ea-text-secondary)',
        }}>
          <History size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
          <p>No version history available</p>
        </div>
      ) : (
        <div style={{ position: 'relative' }}>
          {/* Timeline line */}
          <div style={{
            position: 'absolute',
            left: '24px',
            top: 0,
            bottom: 0,
            width: '2px',
            background: 'var(--ea-border)',
          }} />

          {/* Versions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {versions.map((version, index) => (
              <div
                key={version.id}
                style={{
                  display: 'flex',
                  gap: '16px',
                  position: 'relative',
                }}
              >
                {/* Timeline dot */}
                <div style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: getChangeTypeColor(version.change_type),
                  border: '2px solid var(--ea-bg)',
                  boxShadow: '0 0 0 2px var(--ea-border)',
                  marginTop: '24px',
                  flexShrink: 0,
                  zIndex: 1,
                }} />

                {/* Version card */}
                <div
                  style={{
                    flex: 1,
                    padding: '16px',
                    background: 'var(--ea-bg-hover)',
                    borderRadius: '8px',
                    border: selectedVersions.includes(version.id)
                      ? '2px solid var(--ea-primary)'
                      : '1px solid var(--ea-border)',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  onClick={() => handleSelectVersion(version.id)}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '12px',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{
                        padding: '4px 8px',
                        background: getChangeTypeColor(version.change_type),
                        color: 'white',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>
                        {version.change_type}
                      </div>
                      <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                        Version {version.version}
                      </span>
                    </div>
                    
                    <div style={{ display: 'flex', gap: '4px' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onView?.(version);
                        }}
                        style={{
                          padding: '6px',
                          background: 'transparent',
                          border: '1px solid var(--ea-border)',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          color: 'var(--ea-text-secondary)',
                        }}
                        title="View this version"
                      >
                        <Eye size={14} />
                      </button>
                      
                      {index > 0 && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onRestore?.(version);
                          }}
                          style={{
                            padding: '6px',
                            background: 'transparent',
                            border: '1px solid var(--ea-border)',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            color: 'var(--ea-text-secondary)',
                          }}
                          title="Restore this version"
                        >
                          <RotateCcw size={14} />
                        </button>
                      )}
                    </div>
                  </div>

                  <div style={{
                    display: 'flex',
                    gap: '16px',
                    fontSize: '0.8rem',
                    color: 'var(--ea-text-secondary)',
                    marginBottom: '8px',
                  }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={12} />
                      {formatDate(version.created_at)}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <User size={12} />
                      {version.author?.name || 'System'}
                    </span>
                  </div>

                  {version.change_summary && (
                    <p style={{
                      margin: '0 0 8px',
                      fontSize: '0.85rem',
                      color: 'var(--ea-text-primary)',
                      lineHeight: 1.5,
                    }}>
                      {version.change_summary}
                    </p>
                  )}

                  {version.tags && version.tags.length > 0 && (
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                      {version.tags.map((tag, i) => (
                        <span
                          key={i}
                          style={{
                            padding: '2px 8px',
                            background: 'var(--ea-bg)',
                            border: '1px solid var(--ea-border)',
                            borderRadius: '4px',
                            fontSize: '0.7rem',
                            color: 'var(--ea-text-secondary)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <Tag size={10} />
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}

                  {expandedVersion === version.id && (
                    <div style={{
                      marginTop: '12px',
                      padding: '12px',
                      background: 'var(--ea-bg)',
                      borderRadius: '6px',
                      fontSize: '0.85rem',
                      lineHeight: 1.6,
                      maxHeight: '300px',
                      overflow: 'auto',
                      whiteSpace: 'pre-wrap',
                    }}>
                      {version.narrative || 'No content available'}
                    </div>
                  )}

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setExpandedVersion(expandedVersion === version.id ? null : version.id);
                    }}
                    style={{
                      marginTop: '8px',
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '0.8rem',
                      color: 'var(--ea-primary)',
                    }}
                  >
                    {expandedVersion === version.id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    {expandedVersion === version.id ? 'Hide' : 'Show'} full content
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Compare Modal */}
      {showCompare && selectedVersions.length === 2 && (
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
            maxWidth: '1200px',
            width: '100%',
            maxHeight: '90vh',
            overflow: 'auto',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
            border: '1px solid var(--ea-border)',
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '20px',
            }}>
              <h3 style={{ margin: 0, fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <GitCompare size={20} color="var(--ea-primary)" />
                Compare Versions
              </h3>
              <button
                onClick={() => setShowCompare(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '8px',
                  borderRadius: '50%',
                  color: 'var(--ea-text-secondary)',
                }}
              >
                ✕
              </button>
            </div>

            {renderVersionDiff(
              versions.find(v => v.id === selectedVersions[0]),
              versions.find(v => v.id === selectedVersions[1])
            )}

            <div style={{
              marginTop: '20px',
              paddingTop: '16px',
              borderTop: '1px solid var(--ea-border)',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '8px',
            }}>
              <button
                onClick={() => setShowCompare(false)}
                className="ea-btn ea-btn-secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}