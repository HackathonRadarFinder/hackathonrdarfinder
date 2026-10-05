/**
 * @file Register.jsx
 * @description Registration page view for Hackathon Radar AI.
 */

import RegisterForm from '../../components/auth/RegisterForm';

export default function Register() {
  return (
    <div className="auth-page-container">
      <div className="auth-card">
        {/* Brand header */}
        <div className="auth-brand-badge">
          <span className="auth-radar-pulse" aria-hidden="true" />
          <span className="auth-brand-text">HACKATHON RADAR AI</span>
        </div>

        <div className="auth-header">
          <h1 className="auth-title">Create Account</h1>
          <p className="auth-subtitle">
            Join thousands of hackers discovering global opportunities with AI intelligence.
          </p>
        </div>

        <RegisterForm />

        <div className="auth-perks-list">
          <div className="auth-perk-item">
            <span className="auth-perk-dot" />
            <span>AI hackathon matching</span>
          </div>
          <div className="auth-perk-item">
            <span className="auth-perk-dot" />
            <span>Real-time deadline radar</span>
          </div>
          <div className="auth-perk-item">
            <span className="auth-perk-dot" />
            <span>Global builder squad finder</span>
          </div>
        </div>
      </div>
    </div>
  );
}
