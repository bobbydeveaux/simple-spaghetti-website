import React from 'react';
import { useVoting } from '../context/VotingContext';
import LoginForm from './LoginForm';
import BallotCard from './BallotCard';

const VotingPage = () => {
  const {
    isAuthenticated,
    ballots,
    loading,
    error,
    logout,
    totalVotes,
    loadBallots
  } = useVoting();

  const handleRetry = () => {
    loadBallots();
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Page Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">PTA Voting System</h1>
          <p className="text-gray-600">
            Participate in important PTA decisions by casting your votes on active ballots
          </p>
        </div>

        {/* Authentication Section */}
        {!isAuthenticated ? (
          <div className="mb-8">
            <LoginForm />
          </div>
        ) : (
          <div className="mb-8 p-4 bg-white rounded-lg shadow-md">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Welcome back!</h2>
                <p className="text-gray-600">
                  You have cast {totalVotes} vote{totalVotes === 1 ? '' : 's'} across all ballots
                </p>
              </div>
              <button
                onClick={logout}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors duration-200"
              >
                Logout
              </button>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-medium">Error</h3>
                <p className="mt-1">{error}</p>
              </div>
              <button
                onClick={handleRetry}
                className="ml-4 text-sm text-red-600 hover:text-red-800 underline"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-600">Loading ballots...</p>
          </div>
        )}

        {/* Ballots Section */}
        {isAuthenticated && !loading && (
          <div>
            {ballots.length === 0 ? (
              <div className="text-center py-12">
                <div className="bg-white rounded-lg shadow-md p-8">
                  <h3 className="text-xl font-medium text-gray-900 mb-2">No Active Ballots</h3>
                  <p className="text-gray-600">
                    There are currently no active voting ballots. Check back later for new voting opportunities.
                  </p>
                  <button
                    onClick={handleRetry}
                    className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors duration-200"
                  >
                    Refresh
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Active Ballots</h2>
                  <p className="text-gray-600">
                    {ballots.length} active ballot{ballots.length === 1 ? '' : 's'} available for voting
                  </p>
                </div>

                <div className="space-y-6">
                  {ballots.map((ballot) => (
                    <BallotCard key={ballot.id} ballot={ballot} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default VotingPage;