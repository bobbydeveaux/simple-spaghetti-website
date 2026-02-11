import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import ElectionManagement from './ElectionManagement';

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('election');
  const { isAdmin, logout } = useAuth();

  useEffect(() => {
    // Redirect if not admin
    if (!isAdmin()) {
      window.location.href = '/voting/login';
    }
  }, [isAdmin]);

  const handleLogout = () => {
    logout();
    window.location.href = '/voting/login';
  };

  if (!isAdmin()) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Access Denied</h1>
          <p className="text-gray-600">Admin access required</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <h1 className="text-3xl font-bold text-gray-900">PTA Voting Admin</h1>
            </div>
            <button
              onClick={handleLogout}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-white rounded-lg shadow">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8" aria-label="Tabs">
              <button
                onClick={() => setActiveTab('election')}
                className={`${
                  activeTab === 'election'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-6 border-b-2 font-medium text-sm`}
              >
                Election Config
              </button>
              <button
                onClick={() => setActiveTab('candidates')}
                className={`${
                  activeTab === 'candidates'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-6 border-b-2 font-medium text-sm`}
              >
                Candidates
              </button>
              <button
                onClick={() => setActiveTab('audit')}
                className={`${
                  activeTab === 'audit'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-6 border-b-2 font-medium text-sm`}
              >
                Audit Logs
              </button>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'election' && <ElectionManagement />}
            {activeTab === 'candidates' && (
              <div className="text-center text-gray-500 py-12">
                <h3 className="text-lg font-medium">Candidate Management</h3>
                <p>This feature will be implemented in issue #121</p>
              </div>
            )}
            {activeTab === 'audit' && (
              <div className="text-center text-gray-500 py-12">
                <h3 className="text-lg font-medium">Audit Logs</h3>
                <p>This feature will be implemented in issue #121</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;