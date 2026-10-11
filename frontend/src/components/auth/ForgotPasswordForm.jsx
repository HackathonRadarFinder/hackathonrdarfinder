/**
 * @file ForgotPasswordForm.jsx
 * @description Forgot password request form component for Hackathon Radar AI.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { validateForgotPasswordForm, validateEmail } from '../../utils/validation';

export default function ForgotPasswordForm() {
  const { forgotPassword, isLoading, authError, authSuccess, clearMessages } = useAuth();

  const [email, setEmail] = useState('');
  const [fieldError, setFieldError] = useState(null);
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    clearMessages();
  }, [clearMessages]);

  const handleChange = (e) => {
    const val = e.target.value;
    setEmail(val);
    if (touched) {
      setFieldError(validateEmail(val));
    }
  };

  const handleBlur = () => {
    setTouched(true);
    setFieldError(validateEmail(email));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setTouched(true);

    const { isValid, errors } = validateForgotPasswordForm({ email });
    setFieldError(errors.email || null);

    if (!isValid) {
      return;
    }

    await forgotPassword(email);
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      {/* Feedback alerts */}
      {authError && (
        <div className="auth-alert auth-alert-error" role="alert">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="auth-alert-icon"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{authError}</span>
        </div>
      )}

      {authSuccess && (
        <div className="auth-alert auth-alert-success" role="status">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="auth-alert-icon"
          >
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          <span>{authSuccess}</span>
        </div>
      )}

      <p className="auth-instructions">
        Enter the email address associated with your Hackathon Radar account and we will send you a password reset link.
      </p>

      {/* Email Field */}
      <div className="auth-field-group">
        <label htmlFor="forgot-email" className="auth-label">
          Email Address <span className="auth-required-star" aria-hidden="true">*</span>
        </label>
        <div className="auth-input-wrapper">
          <input
            id="forgot-email"
            name="email"
            type="email"
            value={email}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="developer@radar.ai"
            autoComplete="email"
            disabled={isLoading}
            required
            className={`auth-input ${fieldError ? 'auth-input-error' : ''}`}
            aria-invalid={Boolean(fieldError)}
            aria-describedby={fieldError ? 'forgot-email-error' : undefined}
          />
        </div>
        {fieldError && (
          <p id="forgot-email-error" className="auth-field-error" role="alert">
            {fieldError}
          </p>
        )}
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="auth-submit-btn"
        id="forgot-password-submit-btn"
      >
        {isLoading ? (
          <span className="auth-spinner-wrapper">
            <span className="auth-spinner" aria-hidden="true" />
            Sending Reset Link...
          </span>
        ) : (
          'Send Reset Instructions'
        )}
      </button>

      {/* Navigation back to Login */}
      <div className="auth-back-action">
        <Link to="/login" className="auth-link auth-link-back">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="auth-back-icon"
          >
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          Back to Sign In
        </Link>
      </div>
    </form>
  );
}
