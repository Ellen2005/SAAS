import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BarChart3, Bell, Shield, Database, Zap } from 'lucide-react';

const Landing = () => {
  return (
    <div className="landing-container" style={{ 
      background: 'var(--bg-color)', 
      minHeight: '100vh',
      color: 'var(--text-primary)',
      overflowX: 'hidden'
    }}>
      {/* Hero Section */}
      <section style={{ 
        padding: '80px 20px', 
        textAlign: 'center', 
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center'
      }}>
        {/* Animated Background Elements */}
        <div className="pulse-circle" style={{ 
          position: 'absolute', 
          width: '400px', 
          height: '400px', 
          background: 'radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%)',
          borderRadius: '50%',
          top: '10%',
          zIndex: 0,
          animation: 'pulse 4s infinite alternate ease-in-out'
        }}></div>

        <div style={{ zIndex: 1, position: 'relative', maxWidth: '900px' }}>
          <img 
            src="/logo.png" 
            alt="SAAS Logo" 
            style={{ 
              width: '120px', 
              height: '120px', 
              marginBottom: '32px',
              filter: 'drop-shadow(0 0 20px rgba(59, 130, 246, 0.5))',
              animation: 'float 6s infinite ease-in-out'
            }} 
          />
          <h1 style={{ 
            fontSize: '4.5rem', 
            marginBottom: '24px', 
            fontWeight: '800', 
            background: 'linear-gradient(to right, #fff, #94a3b8)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            lineHeight: '1.1'
          }}>
            Smart Automated Analytics System
          </h1>
          <p style={{ 
            fontSize: '1.4rem', 
            marginBottom: '40px', 
            color: 'var(--text-secondary)',
            maxWidth: '700px',
            margin: '0 auto 48px'
          }}>
            Nightly AI-driven intelligence for department heads. Connect your data, get your briefings, and act before the coffee is cold.
          </p>
          
          <div style={{ display: 'flex', gap: '20px', justifyContent: 'center' }}>
            <Link to="/login" className="btn btn-primary" style={{ padding: '16px 32px', fontSize: '1.1rem', gap: '10px' }}>
              Enter Platform <ArrowRight size={20} />
            </Link>
          </div>
        </div>

        {/* Hero Image Container */}
        <div className="hero-image-container" style={{ 
          marginTop: '60px', 
          width: '100%', 
          maxWidth: '900px',
          position: 'relative',
          borderRadius: '24px',
          overflow: 'hidden',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
          border: '1px solid var(--border-color)',
          animation: 'slideUp 1.2s cubic-bezier(0.16, 1, 0.3, 1), floatHero 8s infinite ease-in-out',
          transition: 'transform 0.5s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.5s ease, border-color 0.5s ease',
          cursor: 'pointer',
          height: '400px'
        }}>
          <img 
            src="/hero.png" 
            alt="SaaS Dashboard Interface" 
            style={{ 
              width: '100%', 
              height: '100%', 
              display: 'block',
              objectFit: 'cover',
              objectPosition: 'top'
            }} 
          />
          <div style={{ 
            position: 'absolute', 
            bottom: 0, 
            left: 0, 
            right: 0, 
            height: '150px', 
            background: 'linear-gradient(to top, var(--bg-color), transparent)' 
          }}></div>
        </div>
      </section>

      {/* Features Grid */}
      <section style={{ padding: '100px 20px', maxWidth: '1200px', margin: '0 auto' }}>
        <h2 style={{ textAlign: 'center', fontSize: '2.5rem', marginBottom: '64px' }}>Powering Decentralized Intelligence</h2>
        <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
          
          <div className="glass-panel" style={{ textAlign: 'left' }}>
            <div style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '12px', borderRadius: '12px', width: 'fit-content', marginBottom: '20px' }}>
              <Zap color="var(--primary-color)" />
            </div>
            <h3>AI-Driven Summaries</h3>
            <p>Don't look at charts for hours. Our system writes a concise executive narrative of your previous 24 hours automatically.</p>
          </div>

          <div className="glass-panel" style={{ textAlign: 'left' }}>
            <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '12px', borderRadius: '12px', width: 'fit-content', marginBottom: '20px' }}>
              <Shield color="var(--status-normal)" />
            </div>
            <h3>Anomaly Detection</h3>
            <p>Sudden dips or spikes? Our ML engine flags statistical outliers before they become major operational bottlenecks.</p>
          </div>

          <div className="glass-panel" style={{ textAlign: 'left' }}>
            <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '12px', borderRadius: '12px', width: 'fit-content', marginBottom: '20px' }}>
              <Database color="var(--status-warning)" />
            </div>
            <h3>Unified Data Sync</h3>
            <p>Connect MS SQL, PostgreSQL, or MySQL directly. Local or hosted, we fetch and process your data on your schedule.</p>
          </div>

        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding: '64px 20px', borderTop: '1px solid var(--border-color)', textAlign: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', marginBottom: '20px' }}>
          <img src="/logo.png" alt="SAAS logo" style={{ width: '32px', height: '32px' }} />
          <h2 style={{ margin: 0, letterSpacing: '-0.05em' }}>SAAS</h2>
        </div>
        <p>© 2026 Smart Automated Analytics System. All rights reserved.</p>
      </footer>

      {/* Animations CSS */}
      <style>{`
        @keyframes pulse {
          from { transform: scale(0.9); opacity: 0.1; }
          to { transform: scale(1.1); opacity: 0.3; }
        }
        @keyframes float {
          0% { transform: translateY(0px); }
          50% { transform: translateY(-15px); }
          100% { transform: translateY(0px); }
        }
        @keyframes floatHero {
          0% { transform: translateY(0px) rotate(0deg); }
          33% { transform: translateY(-10px) rotate(0.5deg); }
          66% { transform: translateY(-5px) rotate(-0.5deg); }
          100% { transform: translateY(0px) rotate(0deg); }
        }
        @keyframes slideUp {
          from { transform: translateY(100px); opacity: 0; }
          to { transform: translateY(0px); opacity: 1; }
        }
        .hero-image-container:hover {
          transform: scale(1.02) translateY(-15px) !important;
          box-shadow: 0 40px 80px -20px rgba(59, 130, 246, 0.4) !important;
          border-color: var(--primary-color) !important;
        }
      `}</style>

    </div>
  );
};

export default Landing;
