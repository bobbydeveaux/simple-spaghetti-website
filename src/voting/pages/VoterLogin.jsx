/**
 * PTA Voting System - Voter Login Page
 * Provides email-code authentication for voters and admin login
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { requestVerificationCode, verifyCode, adminLogin, errorUtils } from '../api/votingApi';

const VoterLogin = () => {
  const { login, isAuthenticated, loading, error: authError, clearError } = useAuth();

  // Form state
  const [step, setStep] = useState('email'); // 'email', 'code', 'admin'
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [adminUsername, setAdminUsername] = useState('');
  const [adminPassword, setAdminPassword] = useState('');

  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [codeExpiry, setCodeExpiry] = useState(null);
  const [debugInfo, setDebugInfo] = useState(null);

  // Clear errors when switching steps
  useEffect(() => {
    setError('');
    clearError();
  }, [step, clearError]);

  // Code expiry countdown
  useEffect(() => {
    if (codeExpiry) {
      const timer = setInterval(() => {
        const now = Date.now();
        if (now >= codeExpiry) {
          setCodeExpiry(null);
          setStep('email');
          setError('Verification code expired. Please request a new one.');
        }
      }, 1000);

      return () => clearInterval(timer);
    }
  }, [codeExpiry]);

  // Redirect if already authenticated
  if (isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full mx-4">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Already Logged In
              </h2>
              <p className="text-gray-600 mb-4">
                You are already authenticated and ready to vote.
              </p>
              <button
                onClick={() => window.location.href = '/voting'}
                className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
              >
                Go to Voting
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /**
   * Handle email submission to request verification code
   */
  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');

    try {
      const response = await requestVerificationCode(email.trim());

      // Store debug info for development
      setDebugInfo(response);

      // Set code expiry (15 minutes from now)
      setCodeExpiry(Date.now() + 15 * 60 * 1000);

      setStep('code');
    } catch (err) {
      setError(errorUtils.getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * Handle code verification
   */
  const handleCodeSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');

    try {
      const authData = await verifyCode(email.trim(), code.trim());
      const loginResult = await login(authData);

      if (loginResult.success) {
        // Successful login - redirect will happen via auth context
        window.location.href = '/voting';
      } else {
        setError(loginResult.error);
      }
    } catch (err) {
      setError(errorUtils.getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * Handle admin login
   */
  const handleAdminLogin = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');

    try {
      const authData = await adminLogin(adminUsername.trim(), adminPassword);
      const loginResult = await login(authData);

      if (loginResult.success) {
        // Successful admin login
        window.location.href = '/voting/admin';
      } else {
        setError(loginResult.error);
      }
    } catch (err) {
      setError(errorUtils.getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * Render loading spinner
   */
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const currentError = error || authError;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 bg-blue-600 rounded-full flex items-center justify-center">
            <svg className="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16l-4-4m0 0l4-4m-4 4h18" />
            </svg>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            PTA Voting System
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            {step === 'email' && 'Enter your email to receive a verification code'}
            {step === 'code' && 'Enter the verification code sent to your email'}
            {step === 'admin' && 'Administrator Login'}
          </p>
        </div>

        {/* Error Message */}
        {currentError && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-800">{currentError}</p>
              </div>
            </div>
          </div>
        )}

        {/* Email Step */}
        {step === 'email' && (
          <form className="mt-8 space-y-6" onSubmit={handleEmailSubmit}>
            <div>
              <label htmlFor="email" className="sr-only">Email address</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
                disabled={isSubmitting}
              />
            </div>

            <div>
              <button
                type="submit"
                disabled={isSubmitting || !email.trim()}
                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Sending Code...' : 'Send Verification Code'}
              </button>
            </div>

            <div className="text-center">
              <button
                type="button"
                onClick={() => setStep('admin')}
                className="text-blue-600 hover:text-blue-500 text-sm font-medium"
              >
                Admin Login
              </button>
            </div>
          </form>
        )}

        {/* Code Verification Step */}
        {step === 'code' && (
          <form className="mt-8 space-y-6" onSubmit={handleCodeSubmit}>
            <div>
              <p className="text-sm text-gray-600 mb-4">
                We sent a verification code to <strong>{email}</strong>
              </p>

              {codeExpiry && (
                <p className="text-xs text-gray-500 mb-4">
                  Code expires in {Math.max(0, Math.floor((codeExpiry - Date.now()) / 1000 / 60))} minutes
                </p>
              )}

              <label htmlFor="code" className="sr-only">Verification Code</label>
              <input
                id="code"
                name="code"
                type="text"
                autoComplete="one-time-code"
                required
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm text-center text-lg tracking-widest"
                placeholder="123456"
                maxLength="6"
                disabled={isSubmitting}
              />
            </div>

            <div className="flex space-x-3">
              <button
                type="button"
                onClick={() => {
                  setStep('email');
                  setCode('');
                  setCodeExpiry(null);
                }}
                className="flex-1 py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={isSubmitting || code.length !== 6}
                className="flex-1 py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Verifying...' : 'Verify & Login'}
              </button>
            </div>
          </form>
        )}

        {/* Admin Login Step */}
        {step === 'admin' && (
          <form className="mt-8 space-y-6" onSubmit={handleAdminLogin}>
            <div className="space-y-4">
              <div>
                <label htmlFor="admin-username" className="sr-only">Username</label>
                <input
                  id="admin-username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  required
                  value={adminUsername}
                  onChange={(e) => setAdminUsername(e.target.value)}
                  className="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  placeholder="Admin username"
                  disabled={isSubmitting}
                />
              </div>
              <div>
                <label htmlFor="admin-password" className="sr-only">Password</label>
                <input
                  id="admin-password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  className="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                  placeholder="Password"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div className="flex space-x-3">
              <button
                type="button"
                onClick={() => {
                  setStep('email');
                  setAdminUsername('');
                  setAdminPassword('');
                }}
                className="flex-1 py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !adminUsername.trim() || !adminPassword.trim()}
                className="flex-1 py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Signing In...' : 'Sign In'}
              </button>
            </div>

            <div className="text-center text-xs text-gray-500">
              <p>For testing: admin@pta.school / admin123</p>
            </div>
          </form>
        )}

        {/* Debug Info (Development Only) */}
        {debugInfo && import.meta.env.DEV && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mt-6">
            <h4 className="text-sm font-medium text-yellow-800 mb-2">Debug Info (Development)</h4>
            <p className="text-xs text-yellow-700">
              <strong>Verification Code:</strong> {debugInfo.code}
            </p>
            <p className="text-xs text-yellow-700">
              <strong>Voter ID:</strong> {debugInfo.voter_id}
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="text-center">
          <p className="text-xs text-gray-500">
            PTA Voting System - Sprint 1 | Authentication & Session Management
          </p>
        </div>
      </div>
    </div>
  );
};

export default VoterLogin;