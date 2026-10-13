/**
 * @file AuthProvider.jsx
 * @description Authentication context provider component for Hackathon Radar AI frontend.
 * Manages in-memory UI authentication state (user, loading, error, success).
 */

import { useState, useCallback, useEffect } from 'react';
import { authService } from '../services/authService';
import { AuthContext } from './AuthContext';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [authSuccess, setAuthSuccess] = useState(null);
  useEffect(() => authService.subscribe(setUser), []);

  const clearMessages = useCallback(() => {
    setAuthError(null);
    setAuthSuccess(null);
  }, []);

  /**
   * Log in user
   * @param {string} email
   * @param {string} password
   */
  const login = useCallback(async (email, password) => {
    setIsLoading(true);
    setAuthError(null);
    setAuthSuccess(null);

    try {
      const response = await authService.login(email, password);
      setUser(response.user);
      setAuthSuccess(`Welcome back, ${response.user.name}!`);
      return { success: true, user: response.user };
    } catch (err) {
      const message = err?.message || 'Failed to sign in. Please try again.';
      setAuthError(message);
      return { success: false, error: message };
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Register a new account
   * @param {{ name: string, email: string, password: string }} data
   */
  const register = useCallback(async (data) => {
    setIsLoading(true);
    setAuthError(null);
    setAuthSuccess(null);

    try {
      const response = await authService.register(data);
      setUser(response.user);
      setAuthSuccess(
        `Account created successfully! Welcome to Hackathon Radar AI, ${response.user.name}!`
      );
      return { success: true, user: response.user };
    } catch (err) {
      const message = err?.message || 'Failed to create account. Please try again.';
      setAuthError(message);
      return { success: false, error: message };
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Send a password reset link
   * @param {string} email
   */
  const forgotPassword = useCallback(async (email) => {
    setIsLoading(true);
    setAuthError(null);
    setAuthSuccess(null);

    try {
      const response = await authService.forgotPassword(email);
      setAuthSuccess(response.message);
      return { success: true, message: response.message };
    } catch (err) {
      const message = err?.message || 'Unable to process password reset request.';
      setAuthError(message);
      return { success: false, error: message };
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Log out current user
   */
  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await authService.logout();
      setUser(null);
      clearMessages();
    } catch {
      setUser(null);
      setAuthError('Signed out on this device. Server revocation could not be confirmed.');
    } finally {
      setIsLoading(false);
    }
  }, [clearMessages]);

  const value = {
    user,
    isLoading,
    authError,
    authSuccess,
    login,
    register,
    forgotPassword,
    logout,
    clearMessages,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;
