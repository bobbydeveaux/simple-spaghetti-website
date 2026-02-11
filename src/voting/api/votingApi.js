/**
 * PTA Voting System API Client
 * Handles all API calls to the voting system backend
 */

const API_BASE_URL = 'http://localhost:5000/api/voting';

// Create axios-like helper for fetch
const api = {
  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
      }

      return data;
    } catch (error) {
      // Enhanced error handling
      if (error.message.includes('Failed to fetch')) {
        throw new Error('Unable to connect to voting system. Please check if the server is running.');
      }
      throw error;
    }
  },

  // Helper method to include authentication token
  async authenticatedRequest(endpoint, options = {}) {
    const token = localStorage.getItem('voting_auth_token');
    if (!token) {
      throw new Error('No authentication token found. Please log in.');
    }

    return this.request(endpoint, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
      },
    });
  },
};

// Authentication API functions

/**
 * Request verification code for voter email
 * @param {string} email - Voter's email address
 * @returns {Promise<{message: string, code: string, voter_id: string}>}
 */
export const requestVerificationCode = async (email) => {
  return api.request('/auth/request-code', {
    method: 'POST',
    body: { email },
  });
};

/**
 * Verify code and authenticate voter
 * @param {string} email - Voter's email address
 * @param {string} code - Verification code
 * @returns {Promise<{token: string, voter_id: string, session_id: string, expires_at: string, message: string}>}
 */
export const verifyCode = async (email, code) => {
  return api.request('/auth/verify', {
    method: 'POST',
    body: { email, code },
  });
};

/**
 * Admin login
 * @param {string} username - Admin username
 * @param {string} password - Admin password
 * @returns {Promise<{token: string, voter_id: string, session_id: string, is_admin: boolean, expires_at: string, message: string}>}
 */
export const adminLogin = async (username, password) => {
  return api.request('/auth/admin-login', {
    method: 'POST',
    body: { username, password },
  });
};

/**
 * Logout current session
 * @returns {Promise<{message: string}>}
 */
export const logout = async () => {
  return api.authenticatedRequest('/auth/logout', {
    method: 'POST',
  });
};

/**
 * Get current session information
 * @returns {Promise<{session_id: string, voter_id: string, email: string, is_admin: boolean, expires_at: string, voting_progress: object}>}
 */
export const getSessionInfo = async () => {
  return api.authenticatedRequest('/auth/session', {
    method: 'GET',
  });
};

// Election API functions

/**
 * Get information about the active election
 * @returns {Promise<{election_id: string, name: string, description: string, is_active: boolean, positions: array, stats: object}>}
 */
export const getElectionInfo = async () => {
  return api.request('/election/info', {
    method: 'GET',
  });
};

// Local storage utilities

export const authUtils = {
  /**
   * Store authentication data in localStorage
   */
  storeAuthData(authData) {
    localStorage.setItem('voting_auth_token', authData.token);
    localStorage.setItem('voting_voter_id', authData.voter_id);
    localStorage.setItem('voting_session_id', authData.session_id);
    localStorage.setItem('voting_expires_at', authData.expires_at);
    if (authData.is_admin !== undefined) {
      localStorage.setItem('voting_is_admin', authData.is_admin.toString());
    }
  },

  /**
   * Get stored authentication data
   */
  getAuthData() {
    const token = localStorage.getItem('voting_auth_token');
    if (!token) return null;

    return {
      token,
      voter_id: localStorage.getItem('voting_voter_id'),
      session_id: localStorage.getItem('voting_session_id'),
      expires_at: localStorage.getItem('voting_expires_at'),
      is_admin: localStorage.getItem('voting_is_admin') === 'true',
    };
  },

  /**
   * Clear all authentication data
   */
  clearAuthData() {
    localStorage.removeItem('voting_auth_token');
    localStorage.removeItem('voting_voter_id');
    localStorage.removeItem('voting_session_id');
    localStorage.removeItem('voting_expires_at');
    localStorage.removeItem('voting_is_admin');
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    const authData = this.getAuthData();
    if (!authData || !authData.token) return false;

    // Check if token has expired
    if (authData.expires_at) {
      const expiresAt = new Date(authData.expires_at);
      if (new Date() >= expiresAt) {
        this.clearAuthData();
        return false;
      }
    }

    return true;
  },

  /**
   * Check if user is admin
   */
  isAdmin() {
    const authData = this.getAuthData();
    return authData?.is_admin === true;
  },
};

// Error handling utilities
export const errorUtils = {
  /**
   * Get user-friendly error message
   */
  getErrorMessage(error) {
    if (typeof error === 'string') return error;
    if (error?.message) return error.message;
    return 'An unexpected error occurred. Please try again.';
  },

  /**
   * Check if error is authentication-related
   */
  isAuthError(error) {
    const message = this.getErrorMessage(error).toLowerCase();
    return message.includes('unauthorized') ||
           message.includes('invalid token') ||
           message.includes('expired') ||
           message.includes('authentication');
  },
};

export default {
  requestVerificationCode,
  verifyCode,
  adminLogin,
  logout,
  getSessionInfo,
  getElectionInfo,
  authUtils,
  errorUtils,
};