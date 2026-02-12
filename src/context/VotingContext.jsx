import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

// Create the context
const VotingContext = createContext();

// Custom hook to use the Voting context
export const useVoting = () => {
  const context = useContext(VotingContext);
  if (!context) {
    throw new Error('useVoting must be used within a VotingProvider');
  }
  return context;
};

// Voting Provider component
export const VotingProvider = ({ children }) => {
  // State for voting data
  const [ballots, setBallots] = useState([]);
  const [myVotes, setMyVotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authToken, setAuthToken] = useState(null);

  // Initialize authentication state
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    if (token) {
      setAuthToken(token);
      setIsAuthenticated(true);
    }
  }, []);

  // API base URL
  const API_BASE_URL = 'http://localhost:5000';

  // Helper function to make authenticated API calls
  const makeAuthenticatedRequest = useCallback(async (url, options = {}) => {
    const headers = {
      'Content-Type': 'application/json',
      ...(authToken && { Authorization: `Bearer ${authToken}` }),
      ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }, [authToken]);

  // Function to load ballots
  const loadBallots = useCallback(async () => {
    try {
      setLoading(true);
      const data = await makeAuthenticatedRequest('/ballots');
      setBallots(data);
      setError(null);
    } catch (err) {
      setError('Failed to load ballots');
      console.error('Error loading ballots:', err);
    } finally {
      setLoading(false);
    }
  }, [makeAuthenticatedRequest]);

  // Function to load user's votes
  const loadMyVotes = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      const data = await makeAuthenticatedRequest('/votes/my-votes');
      setMyVotes(data);
    } catch (err) {
      console.error('Error loading user votes:', err);
      // Don't set error for this as it's not critical
    }
  }, [isAuthenticated, makeAuthenticatedRequest]);

  // Function to submit a vote
  const submitVote = async (ballotId, optionId) => {
    if (!isAuthenticated) {
      throw new Error('Authentication required');
    }

    try {
      setLoading(true);
      const data = await makeAuthenticatedRequest('/votes', {
        method: 'POST',
        body: JSON.stringify({
          ballot_id: ballotId,
          option_id: optionId,
        }),
      });

      // Refresh votes after successful submission
      await loadMyVotes();
      setError(null);
      return data;
    } catch (err) {
      const errorMessage = err.message || 'Failed to submit vote';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Function to get ballot results
  const getBallotResults = async (ballotId) => {
    try {
      return await makeAuthenticatedRequest(`/ballots/${ballotId}/results`);
    } catch (err) {
      console.error('Error loading ballot results:', err);
      throw err;
    }
  };

  // Function to login
  const login = async (email, password) => {
    try {
      setLoading(true);
      const data = await makeAuthenticatedRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });

      const { token, member_id } = data;
      localStorage.setItem('authToken', token);
      localStorage.setItem('memberId', member_id);

      setAuthToken(token);
      setIsAuthenticated(true);
      setError(null);

      // Load user data after login
      await Promise.all([loadBallots(), loadMyVotes()]);

      return data;
    } catch (err) {
      const errorMessage = err.message || 'Login failed';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Function to logout
  const logout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('memberId');
    setAuthToken(null);
    setIsAuthenticated(false);
    setBallots([]);
    setMyVotes([]);
    setError(null);
  };

  // Load ballots when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadBallots();
      loadMyVotes();
    }
  }, [isAuthenticated, loadBallots, loadMyVotes]);

  // Get user's vote for a specific ballot
  const getUserVoteForBallot = (ballotId) => {
    return myVotes.filter(vote => vote.ballot_id === ballotId);
  };

  // Check if user can vote on a ballot
  const canUserVoteOnBallot = (ballot) => {
    if (!isAuthenticated) return false;

    const userVotes = getUserVoteForBallot(ballot.id);
    return userVotes.length < ballot.max_votes_per_member;
  };

  // Get remaining votes for a ballot
  const getRemainingVotesForBallot = (ballot) => {
    const userVotes = getUserVoteForBallot(ballot.id);
    return ballot.max_votes_per_member - userVotes.length;
  };

  // Context value
  const value = {
    // Data
    ballots,
    myVotes,

    // Authentication
    isAuthenticated,
    login,
    logout,

    // Actions
    loadBallots,
    loadMyVotes,
    submitVote,
    getBallotResults,

    // Helper functions
    getUserVoteForBallot,
    canUserVoteOnBallot,
    getRemainingVotesForBallot,

    // Loading states
    loading,
    error,
    setError,

    // Computed values
    totalBallots: ballots.length,
    totalVotes: myVotes.length,
  };

  return (
    <VotingContext.Provider value={value}>
      {children}
    </VotingContext.Provider>
  );
};