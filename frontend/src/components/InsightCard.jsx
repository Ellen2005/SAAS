import React, { useState } from 'react';
import { Lightbulb, AlertTriangle, TrendingUp, TrendingDown, Info, ChevronDown, ChevronUp, Star } from 'lucide-react';

/**
 * Enterprise Insight Card — displays AI-generated insights with metadata.
 */
const InsightCard = ({ 
  title, 
  description, 
  type = 'insight', 
  confidence, 
  impact, 
  metric, 
  value, 
  recommendation,
  onSave,
  onExplain,
  isNew 
}) => {
  const [expanded, setExpanded] = useState(false);

  const typeConfig = {
    insight: { icon: Lightbulb, color: 'var(--ea-primary)', bg: 'var(--ea-primary-bg)' },
    warning: { icon: AlertTriangle, color: 'var(--ea-warning)', bg: 'var(--ea-warning-bg)' },
    positive: { icon: TrendingUp, color: 'var(--ea-success)', bg: 'var(--ea-success-bg)' },
    negative: { icon: TrendingDown, color: 'var(--ea-danger)', bg: 'var(--ea-danger-bg)' },
    info: { icon: Info, color: 'var(--ea-info)', bg: 'var(--ea-info-bg)' },
  };

  const config = typeConfig[type] || typeConfig.insight;
  const Icon = config.icon;

  const confidenceColor = confidence >= 0.8 ? 'var(--ea-success)' : confidence >= 0.5 ? 'var(--ea-warning)' : 'var(--ea-danger)';

  return (
    <div className={`ea-card ${isNew ? 'ea-card-new' : ''}`} style={{ 
      borderLeft: `4px solid ${config.color}`,
      marginBottom: '12px',
      ...(isNew ? { animation: 'ea-glow 2s ease-in-out' } : {})
    }}>
      <div className="ea-card-body" style={{ padding: '16px 20px', cursor: 'pointer' }} onClick={() => setExpanded(!expanded)}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flex: 1 }}>
            <div style={{ 
              width: 36, height: 36, borderRadius: 'var(--ea-radius-md)', 
              background: config.bg, color: config.color,
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
            }}>
              <Icon size={18} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <h4 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: 'var(--ea-text-primary)' }}>{title}</h4>
                {isNew && <span className="ea-badge ea-badge-info">NEW</span>}
              </div>
              <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--ea-text-secondary)', lineHeight: 1.5 }}>
                {description}
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
            {confidence != null && (
              <div style={{ fontSize: '0.75rem', color: confidenceColor, fontWeight: 600 }}>
                {(confidence * 100).toFixed(0)}%
              </div>
            )}
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
        </div>
        
        {expanded && (
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--ea-border)' }}>
            {metric && value && (
              <div style={{ display: 'flex', gap: 16, marginBottom: 12, flexWrap: 'wrap' }}>
                <div>
                  <span style={{ fontSize: '0.7rem', color: 'var(--ea-text-muted)', textTransform: 'uppercase' }}>Metric</span>
                  <div style={{ fontSize: '0.85rem', fontWeight: 500 }}>{metric}</div>
                </div>
                <div>
                  <span style={{ fontSize: '0.7rem', color: 'var(--ea-text-muted)', textTransform: 'uppercase' }}>Value</span>
                  <div style={{ fontSize: '0.85rem', fontWeight: 500 }}>{value}</div>
                </div>
                {impact && (
                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--ea-text-muted)', textTransform: 'uppercase' }}>Impact</span>
                    <div style={{ fontSize: '0.85rem', fontWeight: 500, color: impact > 0 ? 'var(--ea-success)' : 'var(--ea-danger)' }}>
                      {impact > 0 ? '+' : ''}{impact}%
                    </div>
                  </div>
                )}
              </div>
            )}
            {recommendation && (
              <div style={{ 
                padding: '12px', background: 'var(--ea-bg)', borderRadius: 'var(--ea-radius-md)', 
                border: '1px solid var(--ea-border)', marginBottom: 12 
              }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--ea-text-secondary)', marginBottom: 4 }}>
                  <Star size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} /> Recommendation
                </div>
                <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--ea-text-primary)' }}>{recommendation}</p>
              </div>
            )}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              {onSave && (
                <button className="ea-btn ea-btn-ghost ea-btn-sm" onClick={(e) => { e.stopPropagation(); onSave(); }}>
                  <Star size={14} /> Save
                </button>
              )}
              {onExplain && (
                <button className="ea-btn ea-btn-ghost ea-btn-sm" onClick={(e) => { e.stopPropagation(); onExplain(); }}>
                  <Info size={14} /> Explain
                </button>
              )}
            </div>
          </div>
        )}
      </div>
      <style>{`
        @keyframes ea-glow {
          0%, 100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
          50% { box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.15); }
        }
      `}</style>
    </div>
  );
};

export default InsightCard;