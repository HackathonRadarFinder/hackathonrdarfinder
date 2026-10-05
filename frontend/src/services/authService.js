/**
 * @file authService.js
 * @description Authentication service interface for Hackathon Radar AI.
 * Provides minimal mock responses to drive frontend UI states (loading, success, error)
 * and can be connected directly to backend API endpoints (e.g. via fetch or axios).
 */

/**
 * Simulates a brief network delay to test loading states in the UI.
 * @param {number} ms
 * @returns {Promise<void>}
 */
const delay = (ms = 400) => new Promise((resolve) => setTimeout(resolve, ms));

export const authService = {
  /**
   * Log in user with email and password.
   * Future API integration: POST /api/auth/login
   * @param {string} email
   * @param {string} password
   * @returns {Promise<{ user: { id: string, name: string, email: string } }>}
   */
  async login(email, _password) {
    await delay(400);

    // Minimal mock response to keep UI functional
    return {
      user: {
        id: 'usr_mock_001',
        name: email.split('@')[0] || 'Radar Builder',
        email,
      },
    };
  },

  /**
   * Register a new user account.
   * Future API integration: POST /api/auth/register
   * @param {{ name: string, email: string, password?: string }} data
   * @returns {Promise<{ user: { id: string, name: string, email: string } }>}
   */
  async register({ name, email, password: _password }) {
    await delay(400);

    // Minimal mock response to keep UI functional
    return {
      user: {
        id: 'usr_mock_001',
        name: name.trim() || 'Radar Builder',
        email: email.trim().toLowerCase(),
      },
    };
  },

  /**
   * Request password reset instructions.
   * Future API integration: POST /api/auth/forgot-password
   * @param {string} email
   * @returns {Promise<{ message: string }>}
   */
  async forgotPassword(email) {
    await delay(400);

    // Minimal mock response to keep UI functional
    return {
      message: `Password reset instructions have been sent to ${email.trim()}. Please check your inbox.`,
    };
  },

  /**
   * Log out user session.
   * Future API integration: POST /api/auth/logout (if session invalidated server-side)
   * @returns {Promise<void>}
   */
  async logout() {
    await delay(150);
  },
};

export default authService;
