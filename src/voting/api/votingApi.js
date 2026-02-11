/**
 * PTA Voting System - API Client
 * Axios-based client for voting system endpoints
 */

import axios from 'axios';

// Create axios instance for voting API
const votingAPI = axios.create({
  baseURL: 'http://localhost:8000/voting',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 second timeout
});

// Add request interceptor to include auth token
votingAPI.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('voter_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
votingAPI.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle common errors
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('voter_token');
      localStorage.removeItem('voter_id');
      // Could redirect to login here if needed
    }

    // Return a normalized error
    const errorMessage = error.response?.data?.detail ||
                        error.response?.data?.error?.detail ||
                        error.message ||
                        'An unexpected error occurred';

    return Promise.reject(new Error(errorMessage));
  }
);

/**
 * Authentication APIs
 */
export const authAPI = {
  /**
   * Request verification code for email
   */
  requestVerificationCode: async (email) => {
    const response = await votingAPI.post('/auth/request-code', { email });
    return response.data;
  },

  /**
   * Verify code and get access token
   */
  verifyCode: async (email, code) => {
    const response = await votingAPI.post('/auth/verify', { email, code });
    return response.data;
  },
};

/**
 * Voting APIs
 */
export const votingAPIs = {
  /**
   * Get the current ballot with all candidates
   */
  getBallot: async () => {
    const response = await votingAPI.get('/ballot');
    return response.data;
  },

  /**
   * Get voter status (what positions they've voted for)
   */
  getVoterStatus: async () => {
    const response = await votingAPI.get('/status');
    return response.data;
  },

  /**
   * Cast votes for selected candidates
   * @param {Object} votes - Object with position -> candidate_id mappings
   */
  castVotes: async (votes) => {
    const response = await votingAPI.post('/vote', { votes });
    return response.data;
  },
};

/**
 * Health check
 */
export const healthAPI = {
  check: async () => {
    const response = await votingAPI.get('/health');
    return response.data;
  },
};

// Token management utilities
export const tokenUtils = {
  /**
   * Store voter token and ID in localStorage
   */
  storeToken: (token, voterId) => {
    localStorage.setItem('voter_token', token);
    localStorage.setItem('voter_id', voterId);
  },

  /**
   * Get stored voter token
   */
  getToken: () => {
    return localStorage.getItem('voter_token');
  },

  /**
   * Get stored voter ID
   */
  getVoterId: () => {
    return localStorage.getItem('voter_id');
  },

  /**
   * Clear stored voter data
   */
  clearToken: () => {
    localStorage.removeItem('voter_token');
    localStorage.removeItem('voter_id');
  },

  /**
   * Check if voter is authenticated
   */
  isAuthenticated: () => {
    const token = localStorage.getItem('voter_token');
    const voterId = localStorage.getItem('voter_id');
    return !!(token && voterId);
  },
};

export default votingAPI;