/**
 * PTA Voting System API Client
 * Comprehensive API client supporting both Axios (FastAPI) and Fetch (Flask) patterns
 */

// Base configuration
const API_BASE_URL = 'http://localhost:5000/api/voting';

// Detect available HTTP client and use appropriate approach
let httpClient;
let useAxios = false;

// Use fetch API for browser environment
useAxios = false;

// Fetch-based API helper (Flask approach)
const fetchAPI = {
    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        // Add auth token if available
        const token = localStorage.getItem('voting_auth_token') || localStorage.getItem('voter_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }

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
            if (error.message.includes('Failed to fetch')) {
                throw new Error('Unable to connect to voting system. Please check if the server is running.');
            }
            throw error;
        }
    },
};

// ============================================================================
// Authentication API functions
// ============================================================================

/**
 * Request verification code for voter email
 */
export const requestVerificationCode = async (email) => {
    if (useAxios) {
        const response = await httpClient.post('/auth/request-code', { email });
        return response.data;
    } else {
        return fetchAPI.request('/auth/request-code', {
            method: 'POST',
            body: { email },
        });
    }
};

/**
 * Verify code and authenticate voter
 */
export const verifyCode = async (email, code) => {
    if (useAxios) {
        const response = await httpClient.post('/auth/verify', { email, code });
        return response.data;
    } else {
        return fetchAPI.request('/auth/verify', {
            method: 'POST',
            body: { email, code },
        });
    }
};

/**
 * Admin login
 */
export const adminLogin = async (username, password) => {
    if (useAxios) {
        // FastAPI doesn't have admin login endpoint, simulate response
        throw new Error('Admin login not supported in FastAPI mode');
    } else {
        return fetchAPI.request('/auth/admin-login', {
            method: 'POST',
            body: { username, password },
        });
    }
};

/**
 * Logout current session
 */
export const logout = async () => {
    if (useAxios) {
        // FastAPI logout handling
        localStorage.removeItem('voter_token');
        localStorage.removeItem('voter_id');
        return { message: 'Logged out successfully' };
    } else {
        return fetchAPI.request('/auth/logout', {
            method: 'POST',
        });
    }
};

/**
 * Get current session information
 */
export const getSessionInfo = async () => {
    if (useAxios) {
        const response = await httpClient.get('/status');
        return response.data;
    } else {
        return fetchAPI.request('/auth/session', {
            method: 'GET',
        });
    }
};

// ============================================================================
// Voting API functions
// ============================================================================

/**
 * Get the current ballot with all candidates
 */
export const getBallot = async () => {
    if (useAxios) {
        const response = await httpClient.get('/ballot');
        return response.data;
    } else {
        return fetchAPI.request('/election/info', {
            method: 'GET',
        });
    }
};

/**
 * Get voter status (what positions they've voted for)
 */
export const getVoterStatus = async () => {
    if (useAxios) {
        const response = await httpClient.get('/status');
        return response.data;
    } else {
        return fetchAPI.request('/auth/session', {
            method: 'GET',
        });
    }
};

/**
 * Cast votes for selected candidates
 */
export const castVotes = async (votes) => {
    if (useAxios) {
        const response = await httpClient.post('/vote', { votes });
        return response.data;
    } else {
        // Flask implementation would need a voting endpoint
        throw new Error('Vote casting not implemented in Flask mode');
    }
};

/**
 * Get information about the active election
 */
export const getElectionInfo = async () => {
    if (useAxios) {
        // Simulate election info from ballot
        const ballot = await getBallot();
        return {
            election_id: 'default',
            name: 'PTA Election',
            description: 'Annual PTA Board Election',
            is_active: true,
            positions: ballot.positions,
        };
    } else {
        return fetchAPI.request('/election/info', {
            method: 'GET',
        });
    }
};

/**
 * Health check
 */
export const healthCheck = async () => {
    if (useAxios) {
        const response = await httpClient.get('/health');
        return response.data;
    } else {
        // Flask health check not implemented, simulate
        return { status: 'healthy', service: 'pta-voting-system' };
    }
};

// ============================================================================
// Local storage utilities
// ============================================================================

export const authUtils = {
    /**
     * Store authentication data in localStorage
     */
    storeAuthData(authData) {
        if (useAxios) {
            // FastAPI approach
            localStorage.setItem('voter_token', authData.token);
            localStorage.setItem('voter_id', authData.voter_id);
        } else {
            // Flask approach
            localStorage.setItem('voting_auth_token', authData.token);
            localStorage.setItem('voting_voter_id', authData.voter_id);
            localStorage.setItem('voting_session_id', authData.session_id);
            localStorage.setItem('voting_expires_at', authData.expires_at);
            if (authData.is_admin !== undefined) {
                localStorage.setItem('voting_is_admin', authData.is_admin.toString());
            }
        }
    },

    /**
     * Get stored authentication data
     */
    getAuthData() {
        if (useAxios) {
            // FastAPI approach
            const token = localStorage.getItem('voter_token');
            if (!token) return null;

            return {
                token,
                voter_id: localStorage.getItem('voter_id'),
            };
        } else {
            // Flask approach
            const token = localStorage.getItem('voting_auth_token');
            if (!token) return null;

            return {
                token,
                voter_id: localStorage.getItem('voting_voter_id'),
                session_id: localStorage.getItem('voting_session_id'),
                expires_at: localStorage.getItem('voting_expires_at'),
                is_admin: localStorage.getItem('voting_is_admin') === 'true',
            };
        }
    },

    /**
     * Clear all authentication data
     */
    clearAuthData() {
        // Clear both approaches
        localStorage.removeItem('voter_token');
        localStorage.removeItem('voter_id');
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

        // Check if token has expired (Flask mode)
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

// ============================================================================
// Error handling utilities
// ============================================================================

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

// ============================================================================
// Legacy exports for backward compatibility
// ============================================================================

// FastAPI-style exports
export const authAPI = {
    requestVerificationCode,
    verifyCode,
};

export const votingAPIs = {
    getBallot,
    getVoterStatus,
    castVotes,
};

export const healthAPI = {
    check: healthCheck,
};

export const tokenUtils = {
    storeToken: (token, voterId) => authUtils.storeAuthData({ token, voter_id: voterId }),
    getToken: () => authUtils.getAuthData()?.token,
    getVoterId: () => authUtils.getAuthData()?.voter_id,
    clearToken: () => authUtils.clearAuthData(),
    isAuthenticated: () => authUtils.isAuthenticated(),
};

// Default export
export default {
    requestVerificationCode,
    verifyCode,
    adminLogin,
    logout,
    getSessionInfo,
    getElectionInfo,
    getBallot,
    getVoterStatus,
    castVotes,
    healthCheck,
    authUtils,
    errorUtils,
    // Legacy
    authAPI,
    votingAPIs,
    healthAPI,
    tokenUtils,
};
