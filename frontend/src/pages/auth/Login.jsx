/**
 * @file Login.jsx
 * @description Login page view for Hackathon Radar AI.
 */

import LoginForm from '../../components/auth/LoginForm';

export default function Login() {
  return (
    <div className="auth-page-container">
      <div className="auth-card">
        {/* Brand header */}
        <div className="auth-brand-badge">
          <span className="auth-radar-pulse" aria-hidden="true" />
          <span className="auth-brand-text">HACKATHON RADAR AI</span>
        </div>

        <div className="auth-header">
          <h1 className="auth-title">Welcome Back</h1>
          <p className="auth-subtitle">
            Sign in to track live hackathons, match with teams, and submit your builds.
          </p>
        </div>

        <LoginForm />
      </div>
    </div>
  );
}
