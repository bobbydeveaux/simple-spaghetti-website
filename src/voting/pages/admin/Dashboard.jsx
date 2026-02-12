/**
 * PTA Voting System - Admin Dashboard
 * Main admin interface with tab navigation for Candidates, Election Config, and Audit Logs
 */

import React, { useState, useEffect } from 'react';
import { useAuth, withAdminAuth } from '../../context/AuthContext';

/**
 * Main Admin Dashboard Component
 * Provides tab-based navigation for admin functions
 */
const AdminDashboard = () => {
  const { user, isSessionExpiringSoon, logout, refreshSession } = useAuth();

  // Tab state management
  const [activeTab, setActiveTab] = useState('candidates');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Available tabs configuration
  const tabs = [
    {
      id: 'candidates',
      name: 'Candidates',
      description: 'Manage candidates for election positions',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
        </svg>
      )
    },
    {
      id: 'election-config',
      name: 'Election Config',
      description: 'Configure election settings and positions',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      )
    },
    {
      id: 'audit-logs',
      name: 'Audit Logs',
      description: 'View voting activity and system audit logs',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      )
    }
  ];

  // Session expiry warning effect
  useEffect(() => {
    if (isSessionExpiringSoon()) {
      setError('Your session will expire soon. Please save your work.');
    }
  }, [isSessionExpiringSoon]);

  // Handle tab switching
  const handleTabSwitch = (tabId) => {
    setActiveTab(tabId);
    setError(''); // Clear any errors when switching tabs
  };

  // Handle session refresh
  const handleRefreshSession = async () => {
    setLoading(true);
    try {
      const result = await refreshSession();
      if (!result.success) {
        setError(result.error);
      } else {
        setError('');
      }
    } catch (err) {
      setError('Failed to refresh session');
    } finally {
      setLoading(false);
    }
  };

  // Get current tab configuration
  const currentTab = tabs.find(tab => tab.id === activeTab);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                PTA Voting System Admin Dashboard
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Welcome, {user?.email} | Admin Panel
              </p>
            </div>

            <div className="flex items-center space-x-4">
              {/* Session expiry indicator */}
              {isSessionExpiringSoon() && (
                <div className="flex items-center space-x-2 text-yellow-600">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm font-medium">Session Expiring</span>
                  <button
                    onClick={handleRefreshSession}
                    className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200 transition-colors"
                  >
                    Refresh
                  </button>
                </div>
              )}

              {/* Logout button */}
              <button
                onClick={logout}
                className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4 mx-4 mt-4">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
            <div className="ml-auto pl-3">
              <button
                onClick={() => setError('')}
                className="inline-flex text-red-400 hover:text-red-600"
              >
                <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          {/* Tab Navigation */}
          <div className="border-b border-gray-200">
            <nav className="flex space-x-0" aria-label="Admin Tabs">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => handleTabSwitch(tab.id)}
                    className={`
                      flex items-center px-6 py-4 text-sm font-medium border-b-2 transition-colors
                      ${isActive
                        ? 'border-blue-500 text-blue-600 bg-blue-50'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                      }
                    `}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <span className={`mr-2 ${isActive ? 'text-blue-600' : 'text-gray-400'}`}>
                      {tab.icon}
                    </span>
                    {tab.name}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {loading && (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            )}

            {!loading && (
              <>
                {/* Tab Header */}
                <div className="mb-6">
                  <div className="flex items-center">
                    <span className="text-blue-600 mr-3">
                      {currentTab?.icon}
                    </span>
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        {currentTab?.name}
                      </h2>
                      <p className="text-gray-600 mt-1">
                        {currentTab?.description}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Tab-specific Content Placeholders */}
                {activeTab === 'candidates' && (
                  <div className="bg-gray-50 rounded-lg p-8 text-center">
                    <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                            d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                    </svg>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      Candidate Management
                    </h3>
                    <p className="text-gray-600 mb-4">
                      This section will allow you to add, edit, and remove candidates for election positions.
                    </p>
                    <div className="bg-blue-50 border border-blue-200 rounded-md p-4 text-left">
                      <p className="text-sm text-blue-800">
                        <strong>Coming in Issue #121:</strong> Full candidate management interface with add/edit/delete functionality.
                      </p>
                    </div>
                  </div>
                )}

                {activeTab === 'election-config' && (
                  <div className="bg-gray-50 rounded-lg p-8 text-center">
                    <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      Election Configuration
                    </h3>
                    <p className="text-gray-600 mb-4">
                      This section will allow you to configure election positions and manage election status.
                    </p>
                    <div className="bg-blue-50 border border-blue-200 rounded-md p-4 text-left">
                      <p className="text-sm text-blue-800">
                        <strong>Coming in Issue #120:</strong> Election management interface with position configuration and status controls (SETUP/ACTIVE/CLOSED).
                      </p>
                    </div>
                  </div>
                )}

                {activeTab === 'audit-logs' && (
                  <div className="bg-gray-50 rounded-lg p-8 text-center">
                    <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      Audit Logs
                    </h3>
                    <p className="text-gray-600 mb-4">
                      This section will display voting activity and system audit logs with pagination.
                    </p>
                    <div className="bg-blue-50 border border-blue-200 rounded-md p-4 text-left">
                      <p className="text-sm text-blue-800">
                        <strong>Coming in Issue #121:</strong> Audit log viewer with paginated table showing voting activity without exposing vote choices.
                      </p>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Dashboard Footer */}
        <div className="mt-8 text-center">
          <p className="text-sm text-gray-500">
            PTA Voting System Admin Dashboard - Version 1.0
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Session expires at: {user?.expires_at ? new Date(user.expires_at).toLocaleString() : 'Unknown'}
          </p>
        </div>
      </div>
    </div>
  );
};

// Export component with admin authentication protection
export default withAdminAuth(AdminDashboard);
