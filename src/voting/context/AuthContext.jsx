/**
 * PTA Voting System - Authentication Context
 * Provides voter authentication state and methods throughout the voting app
 */

import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { authAPI, tokenUtils } from '../api/votingApi';

// Auth action types
const AUTH_ACTIONS = {
  LOADING: 'LOADING',
  LOGIN_SUCCESS: 'LOGIN_SUCCESS',
  LOGIN_ERROR: 'LOGIN_ERROR',
  LOGOUT: 'LOGOUT',
  CLEAR_ERROR: 'CLEAR_ERROR',
  SET_VERIFICATION_SENT: 'SET_VERIFICATION_SENT',
};

// Initial auth state
const initialState = {
  isAuthenticated: false,
  isLoading: false,
  token: null,
  voterId: null,
  email: null,
  error: null,
  verificationSent: false,
};

// Auth reducer
function authReducer(state, action) {
  switch (action.type) {
    case AUTH_ACTIONS.LOADING:
      return {
        ...state,
        isLoading: true,
        error: null,
      };

    case AUTH_ACTIONS.LOGIN_SUCCESS:
      return {
        ...state,
        isAuthenticated: true,
        isLoading: false,
        token: action.payload.token,
        voterId: action.payload.voterId,
        email: action.payload.email,
        error: null,
      };

    case AUTH_ACTIONS.LOGIN_ERROR:
      return {
        ...state,
        isAuthenticated: false,
        isLoading: false,
        token: null,
        voterId: null,
        error: action.payload.error,
      };

    case AUTH_ACTIONS.LOGOUT:
      return {
        ...state,
        isAuthenticated: false,
        token: null,
        voterId: null,
        email: null,
        error: null,
        verificationSent: false,
      };

    case AUTH_ACTIONS.CLEAR_ERROR:
      return {
        ...state,
        error: null,
      };

    case AUTH_ACTIONS.SET_VERIFICATION_SENT:
      return {
        ...state,
        verificationSent: action.payload.sent,
        email: action.payload.email || state.email,
        isLoading: false,
      };

    default:
      return state;
  }
}

// Create context
const AuthContext = createContext();

/**
 * AuthProvider component that wraps the voting app
 */
export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Check for existing auth on mount
  useEffect(() => {
    const token = tokenUtils.getToken();
    const voterId = tokenUtils.getVoterId();

    if (token && voterId) {
      // Verify token is still valid by making a test request
      // For now, just assume it's valid if it exists
      dispatch({
        type: AUTH_ACTIONS.LOGIN_SUCCESS,
        payload: {
          token,
          voterId,
          email: null, // We don't store email in localStorage
        },
      });
    }
  }, []);

  /**
   * Request verification code for email
   */
  const requestVerificationCode = async (email) => {
    dispatch({ type: AUTH_ACTIONS.LOADING });

    try {
      await authAPI.requestVerificationCode(email);

      dispatch({
        type: AUTH_ACTIONS.SET_VERIFICATION_SENT,
        payload: {
          sent: true,
          email,
        },
      });

      return { success: true };
    } catch (error) {
      dispatch({
        type: AUTH_ACTIONS.LOGIN_ERROR,
        payload: {
          error: error.message,
        },
      });
      return { success: false, error: error.message };
    }
  };

  /**
   * Verify code and complete login
   */
  const verifyCode = async (email, code) => {
    dispatch({ type: AUTH_ACTIONS.LOADING });

    try {
      const response = await authAPI.verifyCode(email, code);

      // Store token and voter ID
      tokenUtils.storeToken(response.token, response.voter_id);

      dispatch({
        type: AUTH_ACTIONS.LOGIN_SUCCESS,
        payload: {
          token: response.token,
          voterId: response.voter_id,
          email,
        },
      });

      return { success: true };
    } catch (error) {
      dispatch({
        type: AUTH_ACTIONS.LOGIN_ERROR,
        payload: {
          error: error.message,
        },
      });
      return { success: false, error: error.message };
    }
  };

  /**
   * Logout voter
   */
  const logout = () => {
    tokenUtils.clearToken();
    dispatch({ type: AUTH_ACTIONS.LOGOUT });
  };

  /**
   * Clear any error messages
   */
  const clearError = () => {
    dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR });
  };

  /**
   * Reset verification state (to allow re-sending code)
   */
  const resetVerification = () => {
    dispatch({
      type: AUTH_ACTIONS.SET_VERIFICATION_SENT,
      payload: {
        sent: false,
        email: state.email,
      },
    });
  };

  const value = {
    // State
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    token: state.token,
    voterId: state.voterId,
    email: state.email,
    error: state.error,
    verificationSent: state.verificationSent,

    // Actions
    requestVerificationCode,
    verifyCode,
    logout,
    clearError,
    resetVerification,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Custom hook to use auth context
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;