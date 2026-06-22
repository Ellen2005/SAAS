import React, { useState, useEffect } from 'react';
import { X, ChevronRight, ChevronLeft, Play, Database, BarChart2, FileText, Settings, Sparkles } from 'lucide-react';

const STEPS = [
  {
    id: 'welcome',
    title: 'Welcome to Enterprise Analytics',
    description: 'Your Power BI alternative for CNPS and enterprise data analytics. Let\'s take a quick tour to get you started.',
    icon: '👋',
    target: null,
  },
  {
    id: 'connect',
    title: 'Connect Your Database',
    description: 'Start by connecting your Oracle, PostgreSQL, MySQL, or MongoDB database. Go to Settings → Database Connection to get started.',
    icon: <Database size={32} color="var(--ea-primary)" />,
    target: 'settings-link',
    action: 'Navigate to Settings',
  },
  {
    id: 'sync',
    title: 'Sync Your Data',
    description: 'Click "Sync Now" to fetch data from your database. The system will automatically discover KPIs and generate insights.',
    icon: <BarChart2 size={32} color="var(--ea-primary)" />,
    target: 'sync-button',
    action: 'Try Syncing',
  },
  {
    id: 'reports',
    title: 'Generate AI Reports',
    description: 'Click "Generate Report" to create AI-powered narratives with insights, anomalies, and recommendations.',
    icon: <Sparkles size={32} color="var(--ea-primary)" />,
    target: 'generate-report-button',
    action: 'Generate Your First Report',
  },
  {
    id: 'query',
    title: 'Ask Your Data',
    description: 'Use natural language to query your data. Just type questions like "Show me total contributions by region" and get instant visualizations.',
    icon: <FileText size={32} color="var(--ea-primary)" />,
    target: 'query-link',
    action: 'Try Querying',
  },
  {
    id: 'customize',
    title: 'Customize Your Dashboard',
    description: 'Click on any KPI card to see detailed analytics. Use the date range selector (7D/30D/90D/1Y) to explore trends over time.',
    icon: <Settings size={32} color="var(--ea-primary)" />,
    target: 'kpi-card',
    action: 'Explore KPIs',
  },
];

export default function OnboardingTour({ onComplete, onSkip }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Check if user has completed onboarding
    const hasCompleted = localStorage.getItem('onboarding_completed');
    if (!hasCompleted) {
      setIsVisible(true);
    }
  }, []);

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = () => {
    localStorage.setItem('onboarding_completed', 'true');
    setIsVisible(false);
    onComplete?.();
  };

  const handleSkip = () => {
    localStorage.setItem('onboarding_completed', 'true');
    setIsVisible(false);
    onSkip?.();
  };

  const handleAction = () => {
    const step = STEPS[currentStep];
    if (step.action) {
      // Trigger navigation or actions based on current step
      if (currentStep === 1) {
        window.location.href = '/settings';
      } else if (currentStep === 3) {
        window.location.href = '/query';
      }
    }
    handleNext();
  };

  if (!isVisible) return null;

  const step = STEPS[currentStep];
  const progress = ((currentStep + 1) / STEPS.length) * 100;

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
        padding: '32px',
        maxWidth: '600px',
        width: '100%',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
        border: '1px solid var(--ea-border)',
        position: 'relative',
        animation: 'slideIn 0.3s ease-out',
      }}>
        <style>{`
          @keyframes slideIn {
            from {
              opacity: 0;
              transform: translateY(-20px) scale(0.95);
            }
            to {
              opacity: 1;
              transform: translateY(0) scale(1);
            }
          }
        `}</style>

        {/* Close button */}
        <button
          onClick={handleSkip}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: '8px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--ea-text-secondary)',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => {
            e.target.style.background = 'var(--ea-bg-hover)';
            e.target.style.color = 'var(--ea-text-primary)';
          }}
          onMouseLeave={(e) => {
            e.target.style.background = 'transparent';
            e.target.style.color = 'var(--ea-text-secondary)';
          }}
        >
          <X size={20} />
        </button>

        {/* Progress bar */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          height: '4px',
          background: 'linear-gradient(90deg, var(--ea-primary), #8b5cf6)',
          borderRadius: 'var(--ea-radius-lg) var(--ea-radius-lg) 0 0',
          width: `${progress}%`,
          transition: 'width 0.3s ease',
        }} />

        {/* Icon */}
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, var(--ea-primary), #8b5cf6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px',
          fontSize: '2rem',
        }}>
          {step.icon}
        </div>

        {/* Content */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <h2 style={{
            fontSize: '1.5rem',
            fontWeight: 600,
            marginBottom: '12px',
            color: 'var(--ea-text-primary)',
          }}>
            {step.title}
          </h2>
          <p style={{
            fontSize: '1rem',
            lineHeight: 1.7,
            color: 'var(--ea-text-secondary)',
            margin: 0,
          }}>
            {step.description}
          </p>
        </div>

        {/* Step indicators */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '8px',
          marginBottom: '24px',
        }}>
          {STEPS.map((_, index) => (
            <div
              key={index}
              style={{
                width: index === currentStep ? '24px' : '8px',
                height: '8px',
                borderRadius: '4px',
                background: index === currentStep
                  ? 'linear-gradient(90deg, var(--ea-primary), #8b5cf6)'
                  : index < currentStep
                    ? 'var(--ea-primary)'
                    : 'var(--ea-border)',
                transition: 'all 0.3s ease',
              }}
            />
          ))}
        </div>

        {/* Actions */}
        <div style={{
          display: 'flex',
          gap: '12px',
          justifyContent: 'space-between',
        }}>
          <div>
            {currentStep > 0 && (
              <button
                className="ea-btn ea-btn-secondary"
                onClick={handlePrevious}
                style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <ChevronLeft size={16} /> Back
              </button>
            )}
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              className="ea-btn ea-btn-ghost"
              onClick={handleSkip}
              style={{ color: 'var(--ea-text-secondary)' }}
            >
              Skip Tour
            </button>
            {step.action && currentStep < STEPS.length - 1 && (
              <button
                className="ea-btn ea-btn-secondary"
                onClick={handleAction}
                style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                {step.action} <Play size={14} />
              </button>
            )}
            <button
              className="ea-btn ea-btn-primary"
              onClick={handleNext}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              {currentStep === STEPS.length - 1 ? 'Get Started' : 'Next'}
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        {/* Step counter */}
        <div style={{
          textAlign: 'center',
          marginTop: '16px',
          fontSize: '0.85rem',
          color: 'var(--ea-text-secondary)',
        }}>
          Step {currentStep + 1} of {STEPS.length}
        </div>
      </div>
    </div>
  );
}