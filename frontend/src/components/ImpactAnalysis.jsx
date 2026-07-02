import React, { useState } from 'react';
import { AlertTriangle, TrendingDown, TrendingUp, Activity, DollarSign, Users, FileText, ArrowRight, Info, Lightbulb } from 'lucide-react';

const IMPACT_CATEGORIES = [
  { id: 'financial', name: 'Financial', icon: <DollarSign size={20} />, color: '#3b82f6' },
  { id: 'operational', name: 'Operational', icon: <Activity size={20} />, color: '#10b981' },
  { id: 'compliance', name: 'Compliance', icon: <FileText size={20} />, color: '#f59e0b' },
  { id: 'stakeholder', name: 'Stakeholder', icon: <Users size={20} />, color: '#8b5cf6' },
];

export default function ImpactAnalysis({ kpiData = [], onAnalyze, height = 500 }) {
  const [selectedKpi, setSelectedKpi] = useState(null);
  const [scenario, setScenario] = useState('10'); // percentage change
  const [direction, setDirection] = useState('decrease'); // increase or decrease
  const [analysis, setAnalysis] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAnalyze = async () => {
    if (!selectedKpi || !onAnalyze) return;
    
    setIsAnalyzing(true);
    try {
      const result = await onAnalyze({
        kpi: selectedKpi,
        scenario: `${direction}_${scenario}`,
      });
      setAnalysis(result);
    } catch (err) {
      console.error('Impact analysis failed:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getImpactLevel = (score) => {
    if (score >= 80) return { label: 'Critical', color: '#ef4444', icon: <AlertTriangle size={20} /> };
    if (score >= 60) return { label: 'High', color: '#f59e0b', icon: <TrendingDown size={20} /> };
    if (score >= 40) return { label: 'Medium', color: '#f59e0b', icon: <Activity size={20} /> };
    return { label: 'Low', color: '#10b981', icon: <TrendingUp size={20} /> };
  };

  const renderImpactCard = (category, impact) => {
    const categoryInfo = IMPACT_CATEGORIES.find(c => c.id === category);
    if (!categoryInfo || !impact) return null;

    const impactLevel = getImpactLevel(impact.score || 0);

    return (
      <div
        key={category}
        style={{
          padding: '16px',
          background: 'var(--ea-bg-hover)',
          borderRadius: '8px',
          border: '1px solid var(--ea-border)',
          borderLeft: `4px solid ${categoryInfo.color}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            background: categoryInfo.color,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
          }}>
            {categoryInfo.icon}
          </div>
          <div style={{ flex: 1 }}>
            <h4 style={{ margin: 0, fontSize: '0.95rem' }}>{categoryInfo.name} Impact</h4>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.75rem',
              color: impactLevel.color,
              fontWeight: 600,
            }}>
              {impactLevel.icon}
              {impactLevel.label} Impact
            </div>
          </div>
          <div style={{
            padding: '4px 8px',
            background: impactLevel.color,
            color: 'white',
            borderRadius: '4px',
            fontSize: '0.75rem',
            fontWeight: 600,
          }}>
            {impact.score || 0}%
          </div>
        </div>

        <p style={{ margin: '0 0 12px', fontSize: '0.85rem', color: 'var(--ea-text-secondary)', lineHeight: 1.5 }}>
          {impact.description || 'No detailed analysis available.'}
        </p>

        {impact.affectedMetrics && impact.affectedMetrics.length > 0 && (
          <div style={{ marginTop: '12px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--ea-text-secondary)', marginBottom: '6px' }}>
              Affected Metrics:
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              {impact.affectedMetrics.map((metric, i) => (
                <span
                  key={i}
                  style={{
                    padding: '2px 8px',
                    background: 'var(--ea-bg)',
                    border: '1px solid var(--ea-border)',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    color: 'var(--ea-text-primary)',
                  }}
                >
                  {metric}
                </span>
              ))}
            </div>
          </div>
        )}

        {impact.recommendations && impact.recommendations.length > 0 && (
          <div style={{ marginTop: '12px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--ea-text-secondary)', marginBottom: '6px' }}>
              Recommendations:
            </div>
            <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '0.8rem', color: 'var(--ea-text-primary)' }}>
              {impact.recommendations.map((rec, i) => (
                <li key={i} style={{ marginBottom: '4px' }}>{rec}</li>
              ))}
            </ul>
          </div>
        )}
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
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Lightbulb size={20} color="var(--ea-primary)" /> Impact Analysis
        </h3>
        <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: 'var(--ea-text-secondary)' }}>
          Simulate "what-if" scenarios to understand downstream effects
        </p>
      </div>

      {/* KPI Selection */}
      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px', color: 'var(--ea-text-primary)' }}>
          Select KPI to Analyze
        </label>
        <select
          value={selectedKpi?.id || ''}
          onChange={(e) => {
            const kpi = kpiData.find(k => k.id === e.target.value);
            setSelectedKpi(kpi || null);
            setAnalysis(null);
          }}
          style={{
            width: '100%',
            padding: '10px 12px',
            background: 'var(--ea-bg-card)',
            border: '1px solid var(--ea-border)',
            borderRadius: '6px',
            fontSize: '0.9rem',
            color: 'var(--ea-text-primary)',
            cursor: 'pointer',
          }}
        >
          <option value="">-- Select a KPI --</option>
          {kpiData.map(kpi => (
            <option key={kpi.id} value={kpi.id}>
              {kpi.kpi_name?.replace(/_/g, ' ') || kpi.name}
            </option>
          ))}
        </select>
      </div>

      {/* Scenario Configuration */}
      {selectedKpi && (
        <div style={{
          padding: '16px',
          background: 'var(--ea-bg-hover)',
          borderRadius: '8px',
          marginBottom: '20px',
        }}>
          <h4 style={{ margin: '0 0 12px', fontSize: '0.95rem' }}>Scenario Configuration</h4>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', marginBottom: '4px', color: 'var(--ea-text-secondary)' }}>
                Change Direction
              </label>
              <select
                value={direction}
                onChange={(e) => setDirection(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px',
                  background: 'var(--ea-bg)',
                  border: '1px solid var(--ea-border)',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  color: 'var(--ea-text-primary)',
                }}
              >
                <option value="decrease">Decrease</option>
                <option value="increase">Increase</option>
              </select>
            </div>
            
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', marginBottom: '4px', color: 'var(--ea-text-secondary)' }}>
                Magnitude (%)
              </label>
              <input
                type="number"
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                min="1"
                max="100"
                style={{
                  width: '100%',
                  padding: '8px',
                  background: 'var(--ea-bg)',
                  border: '1px solid var(--ea-border)',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  color: 'var(--ea-text-primary)',
                }}
              />
            </div>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing}
            style={{
              width: '100%',
              padding: '10px',
              background: 'linear-gradient(135deg, var(--ea-primary), #8b5cf6)',
              border: 'none',
              borderRadius: '6px',
              color: 'white',
              fontSize: '0.9rem',
              fontWeight: 600,
              cursor: isAnalyzing ? 'not-allowed' : 'pointer',
              opacity: isAnalyzing ? 0.7 : 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
            }}
          >
            {isAnalyzing ? 'Analyzing...' : 'Run Impact Analysis'}
            <ArrowRight size={16} />
          </button>
        </div>
      )}

      {/* Analysis Results */}
      {analysis && (
        <div>
          <div style={{
            padding: '12px 16px',
            background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1))',
            borderRadius: '8px',
            marginBottom: '16px',
            border: '1px solid var(--ea-primary)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <Info size={18} color="var(--ea-primary)" />
              <h4 style={{ margin: 0, fontSize: '0.95rem' }}>Analysis Summary</h4>
            </div>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--ea-text-secondary)', lineHeight: 1.6 }}>
              {analysis.summary || 'Impact analysis completed. Review the category-specific impacts below.'}
            </p>
          </div>

          <div style={{ display: 'grid', gap: '12px' }}>
            {IMPACT_CATEGORIES.map(category => 
              renderImpactCard(category.id, analysis[category.id])
            )}
          </div>
        </div>
      )}

      {!selectedKpi && !analysis && (
        <div style={{
          textAlign: 'center',
          padding: '48px',
          color: 'var(--ea-text-secondary)',
        }}>
          <Lightbulb size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
          <p style={{ margin: 0 }}>Select a KPI and configure a scenario to see impact analysis</p>
        </div>
      )}
    </div>
  );
}