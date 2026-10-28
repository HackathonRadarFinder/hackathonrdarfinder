/**
 * @file ForgotPassword.jsx
 * @description Forgot Password page view for Hackathon Radar AI.
 */

import ForgotPasswordForm from '../../components/auth/ForgotPasswordForm';

export default function ForgotPassword() {
  return (
    <div className="auth-page-container">
      <div className="auth-card">
        {/* Brand header */}
        <div className="auth-brand-badge">
          <span className="auth-radar-pulse" aria-hidden="true" />
          <span className="auth-brand-text">HACKATHON RADAR AI</span>
        </div>

        <div className="auth-header">
          <h1 className="auth-title">Reset Password</h1>
          <p className="auth-subtitle">
            Regain access to your Hackathon Radar AI dashboard and project bookmarks.
          </p>
        </div>

        <ForgotPasswordForm />
      </div>
    </div>
  );
}
