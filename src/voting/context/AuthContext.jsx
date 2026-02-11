/**
 * PTA Voting System Authentication Context
 * Manages voter authentication state and provides auth methods to components
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import { authUtils, getSessionInfo, logout, errorUtils } from '../api/votingApi';

const AuthContext = createContext(null);

/**
 * Authentication Provider Component
 */
export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Initialize auth state on component mount
   */
  useEffect(() => {
    initializeAuth();
  }, []);

  /**
   * Initialize authentication state from localStorage and validate session
   */
  const initializeAuth = async () => {
    try {
      setLoading(true);
      setError(null);

      // Check if we have stored auth data
      if (!authUtils.isAuthenticated()) {
        setIsAuthenticated(false);
        setUser(null);
        setLoading(false);
        return;
      }

      // Validate session with backend
      const sessionInfo = await getSessionInfo();

      // Update user state with session info
      setUser({
        voter_id: sessionInfo.voter_id,
        email: sessionInfo.email,
        is_admin: sessionInfo.is_admin,
        session_id: sessionInfo.session_id,
        expires_at: sessionInfo.expires_at,
        voting_progress: sessionInfo.voting_progress,
      });
      setIsAuthenticated(true);

    } catch (error) {
      console.error('Auth initialization error:', error);

      // If session validation fails, clear auth data
      if (errorUtils.isAuthError(error)) {
        authUtils.clearAuthData();
        setIsAuthenticated(false);
        setUser(null);
        setError(null); // Don't show error for invalid stored sessions
      } else {
        setError(errorUtils.getErrorMessage(error));
      }
    } finally {
      setLoading(false);
    }
  };

  /**
   * Login with authentication data from login process
   */
  const login = async (authData) => {
    try {
      setLoading(true);
      setError(null);

      // Store auth data
      authUtils.storeAuthData(authData);

      // Get full session info
      const sessionInfo = await getSessionInfo();

      setUser({
        voter_id: sessionInfo.voter_id,
        email: sessionInfo.email,
        is_admin: sessionInfo.is_admin,
        session_id: sessionInfo.session_id,
        expires_at: sessionInfo.expires_at,
        voting_progress: sessionInfo.voting_progress,
      });
      setIsAuthenticated(true);

      return { success: true };
    } catch (error) {
      const errorMessage = errorUtils.getErrorMessage(error);
      setError(errorMessage);
      authUtils.clearAuthData();
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  /**
   * Logout user and clear auth state
   */
  const handleLogout = async () => {
    try {
      setLoading(true);
      setError(null);

      // Call backend logout endpoint
      if (authUtils.isAuthenticated()) {
        await logout();
      }
    } catch (error) {
      console.error('Logout error:', error);
      // Continue with logout even if backend call fails
    } finally {
      // Clear local auth data
      authUtils.clearAuthData();
      setIsAuthenticated(false);
      setUser(null);
      setLoading(false);
    }
  };

  /**
   * Refresh user session info
   */
  const refreshSession = async () => {
    if (!isAuthenticated) return { success: false, error: 'Not authenticated' };

    try {
      const sessionInfo = await getSessionInfo();
      setUser(prevUser => ({
        ...prevUser,
        voting_progress: sessionInfo.voting_progress,
        expires_at: sessionInfo.expires_at,
      }));
      return { success: true };
    } catch (error) {
      const errorMessage = errorUtils.getErrorMessage(error);

      if (errorUtils.isAuthError(error)) {
        // Session expired, logout user
        await handleLogout();
      }

      return { success: false, error: errorMessage };
    }
  };

  /**
   * Check if user is admin
   */
  const isAdmin = () => {
    return user?.is_admin === true;
  };

  /**
   * Get voting progress information
   */
  const getVotingProgress = () => {
    return user?.voting_progress || {
      total_positions: 0,
      voted_positions: [],
      remaining_positions: [],
    };
  };

  /**
   * Check if session is expiring soon (within 5 minutes)
   */
  const isSessionExpiringSoon = () => {
    if (!user?.expires_at) return false;

    const expiresAt = new Date(user.expires_at);
    const now = new Date();
    const fiveMinutesFromNow = new Date(now.getTime() + 5 * 60 * 1000);

    return expiresAt <= fiveMinutesFromNow;
  };

  const value = {
    // State
    isAuthenticated,
    user,
    loading,
    error,

    // Methods
    login,
    logout: handleLogout,
    refreshSession,
    initializeAuth,

    // Utility methods
    isAdmin,
    getVotingProgress,
    isSessionExpiringSoon,

    // Clear error
    clearError: () => setError(null),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

/**
 * Custom hook to use authentication context
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

/**
 * Higher-order component to protect routes that require authentication
 */
export const withAuth = (Component) => {
  return function AuthenticatedComponent(props) {
    const { isAuthenticated, loading } = useAuth();

    if (loading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      );
    }

    if (!isAuthenticated) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full mx-4">
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  Authentication Required
                </h2>
                <p className="text-gray-600 mb-4">
                  You must be logged in to access this page.
                </p>
                <button
                  onClick={() => window.location.reload()}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
                >
                  Go to Login
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return <Component {...props} />;
  };
};

/**
 * Higher-order component to protect routes that require admin access
 */
export const withAdminAuth = (Component) => {
  return function AdminAuthenticatedComponent(props) {
    const { isAuthenticated, isAdmin, loading } = useAuth();

    if (loading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      );
    }

    if (!isAuthenticated || !isAdmin()) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full mx-4">
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  Admin Access Required
                </h2>
                <p className="text-gray-600 mb-4">
                  You must be an administrator to access this page.
                </p>
                <button
                  onClick={() => window.location.reload()}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
                >
                  Back to Login
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return <Component {...props} />;
  };
};

export default AuthContext;