import React from 'react';

// Enhanced error boundary with user-friendly messages
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error('Component Error:', error, errorInfo);
  }

  getErrorMessage(error) {
    const message = error?.message || '';
    
    // Database connection errors
    if (message.includes('connection') || message.includes('connect')) {
      return {
        title: 'Database Connection Failed',
        description: 'Unable to connect to your database. Please check your connection settings in the Configuration page.',
        action: 'Go to Settings',
        icon: '🔌'
      };
    }
    
    // SQL syntax errors
    if (message.includes('SQL') || message.includes('syntax') || message.includes('query')) {
      return {
        title: 'Invalid Query',
        description: 'The SQL query contains a syntax error. Please review your query and try again.',
        suggestion: 'Try using simpler queries or the natural language query feature.',
        icon: '📝'
      };
    }
    
    // Oracle-specific errors
    if (message.includes('ORA-')) {
      const oraCode = message.match(/ORA-\d+/)?.[0];
      return {
        title: `Oracle Error ${oraCode || 'Unknown'}`,
        description: 'Oracle database returned an error. This might be due to permissions, invalid table/column names, or connection issues.',
        suggestion: 'Verify your Oracle credentials and table/column names in Settings.',
        icon: '🗄️'
      };
    }
    
    // Chart rendering errors
    if (message.includes('chart') || message.includes('Chart')) {
      return {
        title: 'Chart Rendering Error',
        description: 'Unable to render the chart. This might be due to invalid data or unsupported chart type.',
        suggestion: 'Try selecting a different chart type or check your data query.',
        icon: '📊'
      };
    }
    
    // Generic error
    return {
      title: 'Something went wrong',
      description: message || 'An unexpected error occurred.',
      suggestion: 'Please try refreshing the page or contact support if the problem persists.',
      icon: '⚠️'
    };
  }

  render() {
    if (this.state.hasError) {
      const errorDetails = this.getErrorMessage(this.state.error);
      
      return (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '400px',
          padding: '24px',
          background: 'var(--ea-bg)',
          borderRadius: 'var(--ea-radius-lg)',
          border: '1px solid var(--ea-border)'
        }}>
          <div style={{ maxWidth: '500px', textAlign: 'center' }}>
            <div style={{ fontSize: '3rem', marginBottom: '16px' }}>{errorDetails.icon}</div>
            <h2 style={{ marginBottom: '12px', color: 'var(--ea-text-primary)' }}>{errorDetails.title}</h2>
            <p style={{ marginBottom: '16px', color: 'var(--ea-text-secondary)', lineHeight: 1.6 }}>
              {errorDetails.description}
            </p>
            {errorDetails.suggestion && (
              <p style={{ marginBottom: '24px', fontSize: '0.9rem', color: 'var(--ea-text-secondary)', fontStyle: 'italic' }}>
                💡 {errorDetails.suggestion}
              </p>
            )}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                className="ea-btn ea-btn-primary"
                onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
              >
                Try Again
              </button>
              <button
                className="ea-btn ea-btn-secondary"
                onClick={() => window.location.reload()}
              >
                Refresh Page
              </button>
            </div>
            {import.meta.env.MODE === 'development' && (
              <details style={{ marginTop: '24px', textAlign: 'left', fontSize: '0.8rem' }}>
                <summary style={{ cursor: 'pointer', color: 'var(--ea-text-secondary)' }}>Error Details (Dev Only)</summary>
                <pre style={{
                  marginTop: '8px',
                  padding: '12px',
                  background: 'var(--ea-bg-hover)',
                  borderRadius: '6px',
                  overflow: 'auto',
                  fontSize: '0.75rem'
                }}>
                  {this.state.error?.toString()}
                  {'\n\n'}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}