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
            Create a regular account to access supported portal features.
          </p>
        </div>

        <RegisterForm />

        <div className="auth-perks-list">
          <div className="auth-perk-item">
            <span className="auth-perk-dot" />
            <span>Explore the event catalog</span>
          </div>
          <div className="auth-perk-item">
            <span className="auth-perk-dot" />
            <span>Check event deadlines</span>
          </div>
          <div className="auth-perk-item">
            <span className="auth-perk-dot" />
            <span>Follow organizer links</span>
          </div>
        </div>
      </div>
    </div>
  );
}
