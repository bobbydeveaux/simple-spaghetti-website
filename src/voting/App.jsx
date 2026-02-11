/**
 * PTA Voting System - Main Voting App
 * Entry point for the voting system with authentication flow and routing
 */

import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import VoterLogin from './pages/VoterLogin';
import AdminDashboard from './pages/admin/Dashboard';

/**
 * Authenticated voting dashboard (placeholder for now)
 */
function VotingDashboard() {
  const { logout, voterId, email } = useAuth();

  return (
    <div className="max-w-4xl mx-auto mt-8 p-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              PTA Election Voting
            </h1>
            <p className="text-gray-600">
              Welcome! You are logged in and ready to vote.
            </p>
            {email && (
              <p className="text-sm text-gray-500 mt-1">
                Logged in as: {email}
              </p>
            )}
          </div>
          <button
            onClick={logout}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
          >
            Logout
          </button>
        </div>

        {/* Placeholder content for voting dashboard */}
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <p className="text-gray-500 mb-2">
            Voting dashboard will be implemented in Sprint 3
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
 * Main voting app component with routing
 */
function VotingAppContent() {
  const { isAuthenticated, isAdmin } = useAuth();

  return (
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

      {/* Main voting dashboard route - requires voter authentication */}
      <Route
        path="/"
        element={
          isAuthenticated ? (
            isAdmin() ? (
              <Navigate to="/admin" replace />
            ) : (
              <VotingDashboard />
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