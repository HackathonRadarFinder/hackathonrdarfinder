/** Password recovery with email OTP. No reset secret is stored in the browser. */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { validateEmail } from '../../utils/validation';

export default function ForgotPasswordForm() {
  const { forgotPassword, confirmPasswordReset, isLoading, authError, authSuccess, clearMessages } = useAuth();
  const [step, setStep] = useState('request');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [localError, setLocalError] = useState('');

  useEffect(() => { clearMessages(); }, [clearMessages]);

  async function requestCode(event) {
    event.preventDefault();
    setLocalError('');
    const invalid = validateEmail(email);
    if (invalid) { setLocalError(invalid); return; }
    const response = await forgotPassword(email);
    if (response.success) setStep('confirm');
  }

  async function changePassword(event) {
    event.preventDefault();
    setLocalError('');
    if (!/^\d{6}$/.test(code)) { setLocalError('Enter the six-digit code from your email.'); return; }
    if (password.length < 12 || new TextEncoder().encode(password).length > 72) {
      setLocalError('Use a password of at least 12 characters and at most 72 UTF-8 bytes.');
      return;
    }
    if (password !== confirmation) { setLocalError('The passwords do not match.'); return; }
    const result = await confirmPasswordReset(email, code, password);
    if (result.success) {
      setStep('done');
      setCode(''); setPassword(''); setConfirmation('');
    }
  }

  return <div>
    {authError && <div role="alert" className="auth-alert auth-alert-error">{authError}</div>}
    {authSuccess && <div role="status" className="auth-alert auth-alert-success">{authSuccess}</div>}
    {localError && <div role="alert" className="auth-alert auth-alert-error">{localError}</div>}
    {step === 'request' && <form className="auth-form" onSubmit={requestCode}>
      <p className="auth-instructions">Enter your account email to request a six-digit password reset code. Codes expire after 10 minutes.</p>
      <div className="auth-field-group">
        <label htmlFor="forgot-email" className="auth-label">Email address</label>
        <input id="forgot-email" className="auth-input" name="email" type="email" autoComplete="email"
          value={email} onChange={event => setEmail(event.target.value)}
          disabled={isLoading} required maxLength={254} />
      </div>
      <button className="auth-submit-btn" type="submit" disabled={isLoading}>
        {isLoading ? 'Requesting code…' : 'Email me a reset code'}
      </button>
    </form>}
    {step === 'confirm' && <form className="auth-form" onSubmit={changePassword}>
      <p className="auth-instructions">If an account exists, a code was requested for {email}. Check your inbox and spam folder.</p>
      <div className="auth-field-group">
        <label htmlFor="reset-code" className="auth-label">Six-digit email code</label>
        <input id="reset-code" className="auth-input" type="text" autoComplete="one-time-code"
          inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={code}
          onChange={event => setCode(event.target.value.replace(/\D/g, ''))} required disabled={isLoading} />
      </div>
      <div className="auth-field-group">
        <label htmlFor="reset-password" className="auth-label">New password</label>
        <input id="reset-password" className="auth-input" type="password" autoComplete="new-password"
          minLength={12} value={password} onChange={event => setPassword(event.target.value)}
          required disabled={isLoading} />
      </div>
      <div className="auth-field-group">
        <label htmlFor="reset-confirm" className="auth-label">Confirm new password</label>
        <input id="reset-confirm" className="auth-input" type="password" autoComplete="new-password"
          minLength={12} value={confirmation} onChange={event => setConfirmation(event.target.value)}
          required disabled={isLoading} />
      </div>
      <button className="auth-submit-btn" type="submit" disabled={isLoading}>
        {isLoading ? 'Verifying…' : 'Verify code and reset password'}
      </button>
      <button className="auth-link" type="button" disabled={isLoading}
        onClick={() => { clearMessages(); setLocalError(''); setStep('request'); setCode(''); setPassword(''); setConfirmation(''); }}>
        Request a new code
      </button>
    </form>}
    {step === 'done' && <p role="status">Password changed. Older sessions have been invalidated. Sign in again.</p>}
    <div className="auth-back-action"><Link to="/login" className="auth-link auth-link-back">Back to Sign In</Link></div>
  </div>;
}
