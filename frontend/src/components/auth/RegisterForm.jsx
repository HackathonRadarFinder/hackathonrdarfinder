/**
 * @file RegisterForm.jsx
 * @description Registration form component for Hackathon Radar AI.
 */

import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  validateRegisterForm,
  validateName,
  validateEmail,
  validatePassword,
} from '../../utils/validation';
import PasswordInput from './PasswordInput';

export default function RegisterForm() {
  const navigate = useNavigate();
  const { register, isLoading, authError, authSuccess, clearMessages } = useAuth();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const [fieldErrors, setFieldErrors] = useState({});
  const [touched, setTouched] = useState({});

  useEffect(() => {
    clearMessages();
  }, [clearMessages]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // Instant validation if already touched
    if (touched[name]) {
      let err = null;
      if (name === 'name') err = validateName(value);
      if (name === 'email') err = validateEmail(value);
      if (name === 'password') {
        err = validatePassword(value, 8);
        // Also check confirm password match if touched
        if (touched.confirmPassword && formData.confirmPassword) {
          setFieldErrors((prev) => ({
            ...prev,
            confirmPassword:
              value !== formData.confirmPassword ? 'Passwords do not match.' : null,
          }));
        }
      }
      if (name === 'confirmPassword') {
        if (!value) err = 'Confirming your password is required.';
        else if (value !== formData.password) err = 'Passwords do not match.';
      }

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
    if (name === 'name') err = validateName(value);
    if (name === 'email') err = validateEmail(value);
    if (name === 'password') err = validatePassword(value, 8);
    if (name === 'confirmPassword') {
      if (!value) err = 'Confirming your password is required.';
      else if (value !== formData.password) err = 'Passwords do not match.';
    }

    setFieldErrors((prev) => ({
      ...prev,
      [name]: err,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setTouched({
      name: true,
      email: true,
      password: true,
      confirmPassword: true,
    });

    const { isValid, errors } = validateRegisterForm(formData);
    setFieldErrors(errors);

    if (!isValid) {
      return;
    }

    const result = await register({
      name: formData.name,
      email: formData.email,
      password: formData.password,
    });

    if (result.success) {
      setTimeout(() => {
        navigate('/');
      }, 900);
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

      {/* Full Name */}
      <div className="auth-field-group">
        <label htmlFor="register-name" className="auth-label">
          Full Name <span className="auth-required-star" aria-hidden="true">*</span>
        </label>
        <div className="auth-input-wrapper">
          <input
            id="register-name"
            name="name"
            type="text"
            value={formData.name}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="Alex Radar"
            autoComplete="name"
            disabled={isLoading}
            required
            className={`auth-input ${fieldErrors.name ? 'auth-input-error' : ''}`}
            aria-invalid={Boolean(fieldErrors.name)}
            aria-describedby={fieldErrors.name ? 'register-name-error' : undefined}
          />
        </div>
        {fieldErrors.name && (
          <p id="register-name-error" className="auth-field-error" role="alert">
            {fieldErrors.name}
          </p>
        )}
      </div>

      {/* Email Address */}
      <div className="auth-field-group">
        <label htmlFor="register-email" className="auth-label">
          Email Address <span className="auth-required-star" aria-hidden="true">*</span>
        </label>
        <div className="auth-input-wrapper">
          <input
            id="register-email"
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
            aria-describedby={fieldErrors.email ? 'register-email-error' : undefined}
          />
        </div>
        {fieldErrors.email && (
          <p id="register-email-error" className="auth-field-error" role="alert">
            {fieldErrors.email}
          </p>
        )}
      </div>

      {/* Password */}
      <PasswordInput
        id="register-password"
        name="password"
        label="Password"
        value={formData.password}
        onChange={handleChange}
        placeholder="At least 8 characters"
        error={fieldErrors.password}
        disabled={isLoading}
        autoComplete="new-password"
        required
      />

      {/* Confirm Password */}
      <PasswordInput
        id="register-confirm-password"
        name="confirmPassword"
        label="Confirm Password"
        value={formData.confirmPassword}
        onChange={handleChange}
        placeholder="Re-enter your password"
        error={fieldErrors.confirmPassword}
        disabled={isLoading}
        autoComplete="new-password"
        required
      />

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="auth-submit-btn"
        id="register-submit-btn"
      >
        {isLoading ? (
          <span className="auth-spinner-wrapper">
            <span className="auth-spinner" aria-hidden="true" />
            Creating Account...
          </span>
        ) : (
          'Create Account'
        )}
      </button>

      {/* Navigation to Login */}
      <p className="auth-switch-text">
        Already have an account?{' '}
        <Link to="/login" className="auth-link auth-link-accent">
          Sign In
        </Link>
      </p>
    </form>
  );
}
