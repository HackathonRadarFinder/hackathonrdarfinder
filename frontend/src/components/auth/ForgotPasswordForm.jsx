/** Password recovery with email OTP. No reset secret is stored in the browser. */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { validateEmail } from '../../utils/validation';
import PasswordInput from './PasswordInput';

export default function ForgotPasswordForm() {
  const { forgotPassword, confirmPasswordReset, isLoading, authError, authSuccess, clearMessages } = useAuth();
  const [step, setStep] = useState('request');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [localError, setLocalError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

  useEffect(() => {
    clearMessages();
  }, [clearMessages]);

  async function requestCode(event) {
    event.preventDefault();
    setLocalError('');
    clearMessages();
    const emailErr = validateEmail(email);
    if (emailErr) {
      setFieldErrors({ email: emailErr });
      setLocalError(emailErr);
      return;
    }
    setFieldErrors({});
    const response = await forgotPassword(email);
    if (response.success) {
      setStep('confirm');
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    setLocalError('');
    clearMessages();
    const errors = {};

    if (!/^\d{6}$/.test(code)) {
      errors.code = 'Enter the six-digit code from your email.';
    }
    if (password.length < 12 || new TextEncoder().encode(password).length > 72) {
      errors.password = 'Use a password of at least 12 characters and at most 72 UTF-8 bytes.';
    }
    if (password !== confirmation) {
      errors.confirmation = 'The passwords do not match.';
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setLocalError(Object.values(errors)[0]);
      return;
    }

    setFieldErrors({});
    const result = await confirmPasswordReset(email, code, password);
    if (result.success) {
      setStep('done');
      setCode('');
      setPassword('');
      setConfirmation('');
    }
  }

  return (
    <div className="auth-form-wrapper">
      {authError && (
        <div role="alert" className="auth-alert auth-alert-error">
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
        <div role="status" className="auth-alert auth-alert-success">
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

      {localError && (
        <div role="alert" className="auth-alert auth-alert-error">
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
          <span>{localError}</span>
        </div>
      )}

      {step === 'request' && (
        <form className="auth-form" onSubmit={requestCode} noValidate>
          <p className="auth-instructions">
            Enter your account email to request a six-digit password reset code. Codes expire after 10 minutes.
          </p>

          <div className="auth-field-group">
            <div className="auth-field-header">
              <label htmlFor="forgot-email" className="auth-label">
                Email address <span className="auth-required-star" aria-hidden="true">*</span>
              </label>
            </div>
            <div className="auth-input-wrapper">
              <input
                id="forgot-email"
                className={`auth-input ${fieldErrors.email ? 'auth-input-error' : ''}`}
                name="email"
                type="email"
                autoComplete="email"
                placeholder="developer@radar.ai"
                value={email}
                onChange={event => {
                  setEmail(event.target.value);
                  if (fieldErrors.email) setFieldErrors(prev => ({ ...prev, email: null }));
                  if (localError) setLocalError('');
                }}
                disabled={isLoading}
                required
                maxLength={254}
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? 'forgot-email-error' : undefined}
              />
            </div>
            {fieldErrors.email && (
              <p id="forgot-email-error" className="auth-field-error" role="alert">
                {fieldErrors.email}
              </p>
            )}
          </div>

          <button className="auth-submit-btn" type="submit" disabled={isLoading}>
            {isLoading ? (
              <span className="auth-spinner-wrapper">
                <span className="auth-spinner" aria-hidden="true" />
                Requesting code…
              </span>
            ) : (
              'Email me a reset code'
            )}
          </button>
        </form>
      )}

      {step === 'confirm' && (
        <form className="auth-form" onSubmit={changePassword} noValidate>
          <p className="auth-instructions">
            If an account exists, a code was requested for <strong>{email}</strong>. Check your inbox and spam folder.
          </p>

          <div className="auth-field-group">
            <div className="auth-field-header">
              <label htmlFor="reset-code" className="auth-label">
                Six-digit email code <span className="auth-required-star" aria-hidden="true">*</span>
              </label>
            </div>
            <div className="auth-input-wrapper">
              <input
                id="reset-code"
                className={`auth-input ${fieldErrors.code ? 'auth-input-error' : ''}`}
                type="text"
                autoComplete="one-time-code"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                placeholder="123456"
                value={code}
                onChange={event => {
                  setCode(event.target.value.replace(/\D/g, ''));
                  if (fieldErrors.code) setFieldErrors(prev => ({ ...prev, code: null }));
                  if (localError) setLocalError('');
                }}
                required
                disabled={isLoading}
                aria-invalid={Boolean(fieldErrors.code)}
                aria-describedby={fieldErrors.code ? 'reset-code-error' : undefined}
              />
            </div>
            {fieldErrors.code && (
              <p id="reset-code-error" className="auth-field-error" role="alert">
                {fieldErrors.code}
              </p>
            )}
          </div>

          <PasswordInput
            id="reset-password"
            name="password"
            label="New password"
            value={password}
            onChange={event => {
              setPassword(event.target.value);
              if (fieldErrors.password) setFieldErrors(prev => ({ ...prev, password: null }));
              if (localError) setLocalError('');
            }}
            placeholder="At least 12 characters"
            error={fieldErrors.password}
            disabled={isLoading}
            autoComplete="new-password"
            required
          />

          <PasswordInput
            id="reset-confirm"
            name="confirmation"
            label="Confirm new password"
            value={confirmation}
            onChange={event => {
              setConfirmation(event.target.value);
              if (fieldErrors.confirmation) setFieldErrors(prev => ({ ...prev, confirmation: null }));
              if (localError) setLocalError('');
            }}
            placeholder="Confirm new password"
            error={fieldErrors.confirmation}
            disabled={isLoading}
            autoComplete="new-password"
            required
          />

          <button className="auth-submit-btn" type="submit" disabled={isLoading}>
            {isLoading ? (
              <span className="auth-spinner-wrapper">
                <span className="auth-spinner" aria-hidden="true" />
                Verifying code…
              </span>
            ) : (
              'Verify code and reset password'
            )}
          </button>

          <button
            className="auth-link auth-link-subtle"
            type="button"
            disabled={isLoading}
            onClick={() => {
              clearMessages();
              setLocalError('');
              setFieldErrors({});
              setStep('request');
              setCode('');
              setPassword('');
              setConfirmation('');
            }}
          >
            ← Request a new code
          </button>
        </form>
      )}

      {step === 'done' && (
        <div className="auth-form">
          <p className="auth-instructions">
            Password changed successfully. Older sessions have been invalidated. Sign in again with your new password.
          </p>
          <Link
            to="/login"
            className="auth-submit-btn"
            style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', textDecoration: 'none' }}
          >
            Sign in now
          </Link>
        </div>
      )}

      <div className="auth-back-action">
        <Link to="/login" className="auth-link auth-link-back">
          Back to Sign In
        </Link>
      </div>
    </div>
  );
}
