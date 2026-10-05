/**
 * @file LoginForm.jsx
 * @description Authentication Login form component for Hackathon Radar AI.
 */

import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { validateLoginForm, validateEmail, validatePassword } from '../../utils/validation';
import PasswordInput from './PasswordInput';

export default function LoginForm() {
  const navigate = useNavigate();
  const { login, isLoading, authError, authSuccess, clearMessages } = useAuth();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  const [fieldErrors, setFieldErrors] = useState({});
  const [touched, setTouched] = useState({});

  // Clear any residual messages on initial mount
  useEffect(() => {
    clearMessages();
  }, [clearMessages]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // Real-time error clearance or re-validation if touched
    if (touched[name]) {
      let err = null;
      if (name === 'email') err = validateEmail(value);
      if (name === 'password') err = validatePassword(value);

      setFieldErrors((prev) => ({
        ...prev,
        [name]: err,
      }));
    }
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    setTouched((prev) => ({ ...prev, [name]: true }));

    let err = null;
    if (name === 'email') err = validateEmail(value);
    if (name === 'password') err = validatePassword(value);

    setFieldErrors((prev) => ({
      ...prev,
      [name]: err,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Mark fields touched
    setTouched({ email: true, password: true });

    const { isValid, errors } = validateLoginForm(formData);
    setFieldErrors(errors);

    if (!isValid) {
      return;
    }

    const result = await login(formData.email, formData.password);
    if (result.success) {
      // Optional brief delay or immediate redirect
      setTimeout(() => {
        navigate('/');
      }, 700);
    }
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

      {/* Email Field */}
      <div className="auth-field-group">
        <label htmlFor="login-email" className="auth-label">
          Email Address <span className="auth-required-star" aria-hidden="true">*</span>
        </label>
        <div className="auth-input-wrapper">
          <input
            id="login-email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="developer@radar.ai"
            autoComplete="email"
            disabled={isLoading}
            required
            className={`auth-input ${fieldErrors.email ? 'auth-input-error' : ''}`}
            aria-invalid={Boolean(fieldErrors.email)}
            aria-describedby={fieldErrors.email ? 'login-email-error' : undefined}
          />
        </div>
        {fieldErrors.email && (
          <p id="login-email-error" className="auth-field-error" role="alert">
            {fieldErrors.email}
          </p>
        )}
      </div>

      {/* Password Field */}
      <PasswordInput
        id="login-password"
        name="password"
        label="Password"
        value={formData.password}
        onChange={handleChange}
        placeholder="Enter your password"
        error={fieldErrors.password}
        disabled={isLoading}
        autoComplete="current-password"
        required
      />

      {/* Forgot Password link */}
      <div className="auth-row-between">
        <span />
        <Link to="/forgot-password" className="auth-link auth-link-subtle">
          Forgot password?
        </Link>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="auth-submit-btn"
        id="login-submit-btn"
      >
        {isLoading ? (
          <span className="auth-spinner-wrapper">
            <span className="auth-spinner" aria-hidden="true" />
            Signing in...
          </span>
        ) : (
          'Sign In to Radar'
        )}
      </button>

      {/* Navigation to Register */}
      <p className="auth-switch-text">
        Don&apos;t have an account?{' '}
        <Link to="/register" className="auth-link auth-link-accent">
          Create an account
        </Link>
      </p>
    </form>
  );
}
