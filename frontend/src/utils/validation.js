/**
 * @file validation.js
 * @description Reusable validation utility functions for authentication forms.
 */

// Regular expression for validating standard email formats
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Validates a single email string.
 * @param {string} email
 * @returns {string|null} Error message or null if valid.
 */
export function validateEmail(email) {
  if (!email || !email.trim()) {
    return 'Email address is required.';
  }
  const trimmed = email.trim();
  if (!EMAIL_REGEX.test(trimmed)) {
    return 'Please enter a valid email address (e.g., alex@example.com).';
  }
  return null;
}

/**
 * Validates a password string.
 * @param {string} password
 * @param {number} [minLength=6]
 * @returns {string|null} Error message or null if valid.
 */
export function validatePassword(password, minLength = 6) {
  if (!password) {
    return 'Password is required.';
  }
  if (password.length < minLength) {
    return `Password must be at least ${minLength} characters long.`;
  }
  return null;
}

/**
 * Validates a user's full name.
 * @param {string} name
 * @returns {string|null} Error message or null if valid.
 */
export function validateName(name) {
  if (!name || !name.trim()) {
    return 'Full name is required.';
  }
  if (name.trim().length < 2) {
    return 'Full name must be at least 2 characters.';
  }
  return null;
}

/**
 * Validates the complete Login form state.
 * @param {{ email?: string, password?: string }} values
 * @returns {{ isValid: boolean, errors: Record<string, string> }}
 */
export function validateLoginForm({ email = '', password = '' }) {
  const errors = {};

  const emailError = validateEmail(email);
  if (emailError) {
    errors.email = emailError;
  }

  const passwordError = validatePassword(password);
  if (passwordError) {
    errors.password = passwordError;
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}

/**
 * Validates the complete Register form state.
 * @param {{ name?: string, email?: string, password?: string, confirmPassword?: string }} values
 * @returns {{ isValid: boolean, errors: Record<string, string> }}
 */
export function validateRegisterForm({
  name = '',
  email = '',
  password = '',
  confirmPassword = '',
}) {
  const errors = {};

  const nameError = validateName(name);
  if (nameError) {
    errors.name = nameError;
  }

  const emailError = validateEmail(email);
  if (emailError) {
    errors.email = emailError;
  }

  const passwordError = validatePassword(password, 6);
  if (passwordError) {
    errors.password = passwordError;
  }

  if (!confirmPassword) {
    errors.confirmPassword = 'Confirming your password is required.';
  } else if (password !== confirmPassword) {
    errors.confirmPassword = 'Passwords do not match.';
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}

/**
 * Validates the Forgot Password form state.
 * @param {{ email?: string }} values
 * @returns {{ isValid: boolean, errors: Record<string, string> }}
 */
export function validateForgotPasswordForm({ email = '' }) {
  const errors = {};

  const emailError = validateEmail(email);
  if (emailError) {
    errors.email = emailError;
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}
