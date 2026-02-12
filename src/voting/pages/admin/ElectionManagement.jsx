import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';

const ElectionManagement = () => {
  // Note: useAuth is available but not currently used in this component
  useAuth();

  // Get token from localStorage since AuthContext doesn't expose it directly
  const token = localStorage.getItem('auth_token');
  const [election, setElection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updating, setUpdating] = useState(false);
  const [newPosition, setNewPosition] = useState('');
  const [addingPosition, setAddingPosition] = useState(false);

  // Status mapping for display
  const statusLabels = {
    'SETUP': 'Setup',
    'ACTIVE': 'Active',
    'CLOSED': 'Closed'
  };

  // Status colors
  const statusColors = {
    'SETUP': 'bg-yellow-100 text-yellow-800',
    'ACTIVE': 'bg-green-100 text-green-800',
    'CLOSED': 'bg-gray-100 text-gray-800'
  };

  const fetchElection = useCallback(async () => {
    try {
      setLoading(true);
      setError('');

      const response = await fetch('/api/voting/admin/election', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch election data');
      }

      setElection(data.election);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching election:', err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  const updateElectionStatus = async (newStatus) => {
    try {
      setUpdating(true);
      setError('');

      const response = await fetch('/api/voting/admin/election/status', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: newStatus })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to update election status');
      }

      // Update local state
      setElection(prev => ({
        ...prev,
        status: newStatus,
        start_time: data.election.start_time || prev.start_time,
        end_time: data.election.end_time || prev.end_time
      }));

      // Show success message briefly
      setError('');
    } catch (err) {
      setError(err.message);
      console.error('Error updating election status:', err);
    } finally {
      setUpdating(false);
    }
  };

  const addPosition = async () => {
    if (!newPosition.trim()) {
      setError('Position name cannot be empty');
      return;
    }

    try {
      setAddingPosition(true);
      setError('');

      const response = await fetch('/api/voting/admin/election/positions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ position: newPosition.trim() })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to add position');
      }

      // Update local state
      setElection(prev => ({
        ...prev,
        positions: data.positions
      }));

      setNewPosition('');
    } catch (err) {
      setError(err.message);
      console.error('Error adding position:', err);
    } finally {
      setAddingPosition(false);
    }
  };

  const removePosition = async (position) => {
    if (!confirm(`Are you sure you want to remove the "${position}" position?`)) {
      return;
    }

    try {
      setError('');

      const response = await fetch(`/api/voting/admin/election/positions/${encodeURIComponent(position)}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to remove position');
      }

      // Update local state
      setElection(prev => ({
        ...prev,
        positions: data.positions
      }));
    } catch (err) {
      setError(err.message);
      console.error('Error removing position:', err);
    }
  };

  useEffect(() => {
    fetchElection();
  }, [fetchElection]);

  // Auto refresh election status every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchElection, 30000);
    return () => clearInterval(interval);
  }, [fetchElection]);

  if (loading && !election) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Loading election data...</p>
      </div>
    );
  }

  if (error && !election) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">
          <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-red-800">Failed to Load Election</h3>
        <p className="text-red-600 mb-4">{error}</p>
        <button
          onClick={fetchElection}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
            <div className="ml-auto pl-3">
              <button
                onClick={() => setError('')}
                className="inline-flex text-red-400 hover:text-red-600"
              >
                <span className="sr-only">Dismiss</span>
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Election Overview */}
      {election && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Election Overview</h2>
            <button
              onClick={fetchElection}
              disabled={loading}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              <svg className={`-ml-0.5 mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Election Details</h3>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Name</dt>
                  <dd className="text-sm text-gray-900">{election.name}</dd>
                </div>
                {election.description && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Description</dt>
                    <dd className="text-sm text-gray-900">{election.description}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-sm font-medium text-gray-500">Created</dt>
                  <dd className="text-sm text-gray-900">
                    {election.created_at ? new Date(election.created_at).toLocaleDateString() : 'N/A'}
                  </dd>
                </div>
                {election.start_time && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Started</dt>
                    <dd className="text-sm text-gray-900">
                      {new Date(election.start_time).toLocaleString()}
                    </dd>
                  </div>
                )}
                {election.end_time && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Ended</dt>
                    <dd className="text-sm text-gray-900">
                      {new Date(election.end_time).toLocaleString()}
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Current Status</h3>
              <div className="space-y-4">
                <div>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[election.status] || 'bg-gray-100 text-gray-800'}`}>
                    {statusLabels[election.status] || election.status}
                  </span>
                </div>

                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-gray-500">Change Status</h4>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => updateElectionStatus('SETUP')}
                      disabled={updating || election.status === 'SETUP'}
                      className="px-3 py-1 text-xs font-medium rounded-md bg-yellow-100 text-yellow-800 hover:bg-yellow-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Setup
                    </button>
                    <button
                      onClick={() => updateElectionStatus('ACTIVE')}
                      disabled={updating || election.status === 'ACTIVE'}
                      className="px-3 py-1 text-xs font-medium rounded-md bg-green-100 text-green-800 hover:bg-green-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Activate
                    </button>
                    <button
                      onClick={() => updateElectionStatus('CLOSED')}
                      disabled={updating || election.status === 'CLOSED'}
                      className="px-3 py-1 text-xs font-medium rounded-md bg-gray-100 text-gray-800 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Close
                    </button>
                  </div>
                  {updating && (
                    <p className="text-xs text-gray-500">Updating status...</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Position Management */}
      {election && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Position Configuration</h2>

          {/* Add New Position */}
          <div className="mb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Add New Position</h3>
            <div className="flex gap-3">
              <input
                type="text"
                value={newPosition}
                onChange={(e) => setNewPosition(e.target.value)}
                placeholder="Enter position name (e.g., President, Secretary)"
                className="flex-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                onKeyPress={(e) => e.key === 'Enter' && addPosition()}
              />
              <button
                onClick={addPosition}
                disabled={addingPosition || !newPosition.trim()}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {addingPosition ? 'Adding...' : 'Add Position'}
              </button>
            </div>
          </div>

          {/* Current Positions */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Current Positions</h3>
            {election.positions && election.positions.length > 0 ? (
              <div className="space-y-2">
                {election.positions.map((position, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-3 px-4 bg-gray-50 rounded-md"
                  >
                    <span className="text-sm font-medium text-gray-900">{position}</span>
                    <button
                      onClick={() => removePosition(position)}
                      className="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded text-red-700 bg-red-100 hover:bg-red-200"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-gray-500">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <h3 className="mt-2 text-sm font-medium">No positions configured</h3>
                <p className="mt-1 text-sm">Add positions above to get started.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ElectionManagement;