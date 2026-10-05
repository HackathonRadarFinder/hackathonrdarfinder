/**
 * @file App.jsx
 * @description Main application routing and shell for Hackathon Radar AI.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthProvider';
import { useAuth } from './context/AuthContext';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import ForgotPassword from './pages/auth/ForgotPassword';
import './App.css';

/**
 * Component displayed when an authenticated user visits the root route.
 */
function DashboardView() {
  const { user, logout, isLoading } = useAuth();

  return (
    <div className="auth-page-container">
      <div className="auth-card auth-dashboard-card">
        <div className="auth-brand-badge">
          <span className="auth-radar-pulse" aria-hidden="true" />
          <span className="auth-brand-text">HACKATHON RADAR AI</span>
        </div>

        <div className="auth-header">
          <div className="auth-avatar-circle">
            {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
          </div>
          <h1 className="auth-title">Welcome, {user?.name || 'Hacker'}!</h1>
          <p className="auth-subtitle">
            You are signed in to Hackathon Radar AI.
          </p>
        </div>

        <div className="auth-session-details">
          <div className="auth-session-row">
            <span className="auth-session-label">Email:</span>
            <span className="auth-session-val">{user?.email}</span>
          </div>
          <div className="auth-session-row">
            <span className="auth-session-label">Status:</span>
            <span className="auth-status-pill">
              <span className="auth-status-dot" /> Authenticated
            </span>
          </div>
        </div>

        <div className="auth-dashboard-actions">
          <button
            type="button"
            onClick={logout}
            disabled={isLoading}
            className="auth-submit-btn auth-btn-secondary"
            id="dashboard-logout-btn"
          >
            {isLoading ? 'Signing Out...' : 'Sign Out'}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Route protection wrapper for the dashboard.
 */
function ProtectedDashboard() {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <DashboardView />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/" element={<ProtectedDashboard />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
