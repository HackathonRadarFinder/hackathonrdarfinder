/**
 * @file auth.js
 * @description Type definitions for authentication UI components in Hackathon Radar AI.
 */

/**
 * @typedef {Object} User
 * @property {string} id - Unique identifier for the user.
 * @property {string} name - User's full name.
 * @property {string} email - User's email address.
 * @property {string} [avatar] - Optional avatar URL.
 */

/**
 * @typedef {Object} AuthResponse
 * @property {boolean} success - Whether the authentication operation succeeded.
 * @property {User} [user] - Authenticated user object if successful.
 * @property {string} [message] - Success or error description message.
 */

/**
 * @typedef {Object} ValidationResult
 * @property {boolean} isValid - Whether validation passed.
 * @property {Record<string, string>} errors - Map of field names to error messages.
 */

export {};
