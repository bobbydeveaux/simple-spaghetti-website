/**
 * AuditLogs component for PTA Voting System Admin Panel
 *
 * Displays paginated audit logs showing voting activity with:
 * - Timestamp, voter ID, action, and position
 * - Filtering by action type and voter ID
 * - Pagination controls
 * - Responsive table layout
 */

import React, { useState, useEffect } from 'react';
import votingApi from '../../api/votingApi';

const AuditLogs = () => {
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalLogs, setTotalLogs] = useState(0);
  const [logsPerPage] = useState(50);
  const [filters, setFilters] = useState({
    action: '',
    voter_id: ''
  });

  const actionTypes = [
    { value: '', label: 'All Actions' },
    { value: 'LOGIN', label: 'Login' },
    { value: 'VOTE_CAST', label: 'Vote Cast' },
    { value: 'ADMIN_ACTION', label: 'Admin Action' },
    { value: 'VERIFICATION_CODE_REQUESTED', label: 'Code Requested' },
    { value: 'VERIFICATION_CODE_USED', label: 'Code Used' }
  ];

  // Load audit logs with current filters and pagination
  const loadAuditLogs = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = {
        limit: logsPerPage,
        offset: (currentPage - 1) * logsPerPage,
        ...(filters.action && { action: filters.action }),
        ...(filters.voter_id && { voter_id: filters.voter_id })
      };

      const response = await votingApi.getAuditLogs(params);
      setAuditLogs(response.audit_logs);
      setTotalLogs(response.total);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
      setError(err.response?.data?.error || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  // Load data on component mount and when dependencies change
  useEffect(() => {
    loadAuditLogs();
  }, [currentPage, filters]);

  // Handle filter changes
  const handleFilterChange = (filterType, value) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: value
    }));
    setCurrentPage(1); // Reset to first page when filtering
  };

  // Handle page navigation
  const totalPages = Math.ceil(totalLogs / logsPerPage);
  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  // Format timestamp for display
  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch (error) {
      return timestamp;
    }
  };

  // Format action for display
  const formatAction = (action) => {
    const actionMap = {
      'LOGIN': 'Login',
      'VOTE_CAST': 'Vote Cast',
      'ADMIN_ACTION': 'Admin Action',
      'VERIFICATION_CODE_REQUESTED': 'Code Requested',
      'VERIFICATION_CODE_USED': 'Code Used'
    };
    return actionMap[action] || action;
  };

  // Get action badge color
  const getActionBadgeColor = (action) => {
    const colorMap = {
      'LOGIN': 'bg-blue-100 text-blue-800',
      'VOTE_CAST': 'bg-green-100 text-green-800',
      'ADMIN_ACTION': 'bg-red-100 text-red-800',
      'VERIFICATION_CODE_REQUESTED': 'bg-yellow-100 text-yellow-800',
      'VERIFICATION_CODE_USED': 'bg-purple-100 text-purple-800'
    };
    return colorMap[action] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading audit logs...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-2xl font-semibold text-gray-900">Audit Logs</h2>
        <p className="mt-1 text-gray-600">
          View system activity and voting audit trail. Total: {totalLogs} entries
        </p>
      </div>

      {/* Filters */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <h3 className="text-lg font-medium text-gray-900 mb-3">Filters</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Action Filter */}
          <div>
            <label htmlFor="action-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Action Type
            </label>
            <select
              id="action-filter"
              value={filters.action}
              onChange={(e) => handleFilterChange('action', e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              {actionTypes.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          {/* Voter ID Filter */}
          <div>
            <label htmlFor="voter-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Voter ID
            </label>
            <input
              type="text"
              id="voter-filter"
              placeholder="Enter voter ID..."
              value={filters.voter_id}
              onChange={(e) => handleFilterChange('voter_id', e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Clear Filters */}
        {(filters.action || filters.voter_id) && (
          <button
            onClick={() => {
              setFilters({ action: '', voter_id: '' });
              setCurrentPage(1);
            }}
            className="mt-3 px-4 py-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
          >
            Clear all filters
          </button>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error Loading Audit Logs</h3>
              <div className="mt-2 text-sm text-red-700">{error}</div>
              <div className="mt-3">
                <button
                  onClick={loadAuditLogs}
                  className="text-sm bg-red-100 text-red-700 px-3 py-1 rounded hover:bg-red-200"
                >
                  Try again
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Audit Logs Table */}
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Voter
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Position
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-12 text-center text-gray-500">
                    No audit logs found matching your criteria.
                  </td>
                </tr>
              ) : (
                auditLogs.map((log) => (
                  <tr key={log.log_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatTimestamp(log.timestamp)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 font-medium">
                        {log.voter_email}
                      </div>
                      <div className="text-sm text-gray-500 font-mono">
                        {log.voter_id.substring(0, 8)}...
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getActionBadgeColor(log.action)}`}>
                        {formatAction(log.action)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {log.position || '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {log.metadata && typeof log.metadata === 'object' ? (
                        <div className="space-y-1">
                          {Object.entries(log.metadata).map(([key, value]) => (
                            <div key={key} className="text-xs">
                              <span className="font-medium">{key}:</span> {
                                typeof value === 'object' ? JSON.stringify(value) : String(value)
                              }
                            </div>
                          ))}
                        </div>
                      ) : log.metadata ? (
                        <span className="text-xs">{String(log.metadata)}</span>
                      ) : (
                        '-'
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Showing{' '}
                  <span className="font-medium">{(currentPage - 1) * logsPerPage + 1}</span>{' '}
                  to{' '}
                  <span className="font-medium">
                    {Math.min(currentPage * logsPerPage, totalLogs)}
                  </span>{' '}
                  of{' '}
                  <span className="font-medium">{totalLogs}</span>{' '}
                  results
                </p>
              </div>
              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                  <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>

                  {/* Page numbers */}
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum;
                    if (totalPages <= 5) {
                      pageNum = i + 1;
                    } else if (currentPage <= 3) {
                      pageNum = i + 1;
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i;
                    } else {
                      pageNum = currentPage - 2 + i;
                    }

                    return (
                      <button
                        key={pageNum}
                        onClick={() => handlePageChange(pageNum)}
                        className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                          pageNum === currentPage
                            ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                            : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}

                  <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="text-sm text-gray-600">
        {auditLogs.length > 0 && (
          <p>
            Displaying {auditLogs.length} of {totalLogs} audit log entries
            {(filters.action || filters.voter_id) && ' (filtered)'}
          </p>
        )}
      </div>
    </div>
  );
};

export default AuditLogs;