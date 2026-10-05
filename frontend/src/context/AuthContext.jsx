/**
 * @file AuthContext.jsx
 * @description Authentication React Context and useAuth hook.
 */

import { createContext, useContext } from 'react';

export const AuthContext = createContext(null);

/**
 * Custom hook for consuming authentication context.
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
