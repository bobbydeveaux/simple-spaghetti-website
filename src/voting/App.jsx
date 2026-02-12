/**
 * PTA Voting System - Main Voting App
 * Entry point for the voting system with authentication flow and routing
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import { AuthProvider, useAuth, withAdminAuth } from './context/AuthContext';
import VoterLogin from './pages/VoterLogin';
import AdminDashboard from './pages/admin/Dashboard';
import CandidateManagement from './pages/admin/CandidateManagement';

/**
 * Navigation header component
 */
function NavigationHeader() {
  const { logout, voterId, email, isAdmin } = useAuth();

  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              PTA Election System
            </h1>
            {email && (
              <p className="text-sm text-gray-500">
                Logged in as: {email} {isAdmin() && <span className="text-blue-600">(Admin)</span>}
              </p>
            )}
          </div>
          <div className="flex items-center space-x-4">
            <Link
              to="/"
              className="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium"
            >
              Dashboard
            </Link>
            {isAdmin() && (
              <Link
                to="/admin/candidates"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium"
              >
                Manage Candidates
              </Link>
            )}
            <button
              onClick={logout}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors text-sm font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}

/**
 * Voter dashboard (placeholder for now)
 */
function VoterDashboard() {
  const { voterId } = useAuth();

  return (
    <div className="max-w-4xl mx-auto mt-8 p-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Voting Dashboard
        </h2>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <p className="text-gray-500 mb-2">
            Voting interface will be implemented in Sprint 3
          </p>
          <p className="text-sm text-gray-400">
            Voter ID: {voterId}
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Protected admin candidate management page
 */
const ProtectedCandidateManagement = withAdminAuth(CandidateManagement);

/**
 * Main voting app component with routing
 */
function VotingAppContent() {
  const { isAuthenticated, isAdmin } = useAuth();

  const handleLoginSuccess = () => {
    console.log('Login successful!');
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-8">
          <VoterLogin onLoginSuccess={handleLoginSuccess} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Router>
        <NavigationHeader />
        <Routes>
          {/* Login route - accessible to all unauthenticated users */}
          <Route
            path="/login"
            element={
              isAuthenticated ? (
                <Navigate to={isAdmin() ? '/admin' : '/'} replace />
              ) : (
                <VoterLogin />
              )
            }
          />

          {/* Admin dashboard route - requires admin authentication */}
          <Route path="/admin" element={<AdminDashboard />} />

          {/* Admin candidate management route */}
          <Route
            path="/admin/candidates"
            element={<ProtectedCandidateManagement />}
          />

          {/* Dashboard route - different for admin vs voter */}
          <Route
            path="/"
            element={
              isAuthenticated ? (
                isAdmin() ? (
                  <Navigate to="/admin" replace />
                ) : (
                  <VoterDashboard />
                )
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          {/* Catch-all redirect to appropriate dashboard */}
          <Route
            path="*"
            element={
              <Navigate to={isAuthenticated ? (isAdmin() ? '/admin' : '/') : '/login'} replace />
            }
          />
        </Routes>
      </Router>
    </div>
  );
}

/**
 * Voting app with authentication provider
 */
function VotingApp() {
  return (
    <AuthProvider>
      <VotingAppContent />
    </AuthProvider>
  );
}

export default VotingApp;