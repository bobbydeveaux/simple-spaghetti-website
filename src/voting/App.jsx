/**
 * PTA Voting System - Main Voting App
 * Entry point for the voting system with authentication flow
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import { AuthProvider, useAuth, withAdminAuth } from './context/AuthContext';
import VoterLogin from './pages/VoterLogin';
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
 * Admin dashboard
 */
function AdminDashboard() {
  return (
    <div className="max-w-7xl mx-auto mt-8 p-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Admin Dashboard
        </h2>
        <p className="text-gray-600 mb-6">
          Welcome to the PTA Election admin panel. Manage candidates and monitor the election.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Candidate Management Card */}
          <Link
            to="/admin/candidates"
            className="block bg-blue-50 p-6 rounded-lg border border-blue-200 hover:bg-blue-100 transition-colors"
          >
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-8 w-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.196-2.121M17 20H7m10 0v-2a3 3 0 00-3-3v-1a3 3 0 116 0v4zm-5-9a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-medium text-gray-900">Candidate Management</h3>
                <p className="text-sm text-gray-600">Add, edit, and organize election candidates</p>
              </div>
            </div>
          </Link>

          {/* Placeholder for future admin features */}
          <div className="bg-gray-50 p-6 rounded-lg border border-gray-200">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-medium text-gray-500">Election Results</h3>
                <p className="text-sm text-gray-400">View live results and analytics (Coming in Sprint 3)</p>
              </div>
            </div>
          </div>
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
          {/* Dashboard route - different for admin vs voter */}
          <Route
            path="/"
            element={isAdmin() ? <AdminDashboard /> : <VoterDashboard />}
          />

          {/* Admin routes */}
          <Route
            path="/admin/candidates"
            element={<ProtectedCandidateManagement />}
          />

          {/* Catch all - redirect to dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
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