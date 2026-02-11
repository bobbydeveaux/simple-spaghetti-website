/**
 * PTA Voting System - Voter Login Page
 * Two-step authentication: Email → Verification Code → Access Token
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

function VoterLogin({ onLoginSuccess }) {
  const {
    isAuthenticated,
    isLoading,
    error,
    verificationSent,
    email: savedEmail,
    requestVerificationCode,
    verifyCode,
    clearError,
    resetVerification,
  } = useAuth();

  // Form state
  const [email, setEmail] = useState(savedEmail || '');
  const [code, setCode] = useState('');
  const [emailError, setEmailError] = useState('');
  const [codeError, setCodeError] = useState('');

  // Clear errors when switching between steps
  useEffect(() => {
    clearError();
    setEmailError('');
    setCodeError('');
  }, [verificationSent, clearError]);

  // Redirect on successful authentication
  useEffect(() => {
    if (isAuthenticated) {
      onLoginSuccess?.();
    }
  }, [isAuthenticated, onLoginSuccess]);

  // Email validation
  const validateEmail = (emailValue) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(emailValue);
  };

  // Handle email submission
  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setEmailError('');

    // Validate email
    if (!email.trim()) {
      setEmailError('Email is required');
      return;
    }

    if (!validateEmail(email)) {
      setEmailError('Please enter a valid email address');
      return;
    }

    // Request verification code
    const result = await requestVerificationCode(email);

    if (!result.success) {
      setEmailError(result.error);
    }
  };

  // Handle code submission
  const handleCodeSubmit = async (e) => {
    e.preventDefault();
    setCodeError('');

    // Validate code
    if (!code.trim()) {
      setCodeError('Verification code is required');
      return;
    }

    if (code.length !== 6) {
      setCodeError('Verification code must be 6 digits');
      return;
    }

    if (!/^\d{6}$/.test(code)) {
      setCodeError('Verification code must contain only numbers');
      return;
    }

    // Verify code
    const result = await verifyCode(savedEmail || email, code);

    if (!result.success) {
      setCodeError(result.error);
    }
  };

  // Handle going back to email step
  const handleBackToEmail = () => {
    resetVerification();
    setCode('');
    setCodeError('');
  };

  // Handle resending verification code
  const handleResendCode = async () => {
    setCodeError('');
    const result = await requestVerificationCode(savedEmail || email);

    if (!result.success) {
      setCodeError(result.error);
    }
  };

  if (!verificationSent) {
    // Step 1: Email input
    return (
      <div className="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            PTA Voting Login
          </h1>
          <p className="text-gray-600">
            Enter your email to receive a verification code
          </p>
        </div>

        <form onSubmit={handleEmailSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email Address
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed ${
                emailError ? 'border-red-500' : 'border-gray-300'
              }`}
              placeholder="your.email@example.com"
              autoComplete="email"
              autoFocus
            />
            {emailError && (
              <p className="mt-1 text-sm text-red-600">{emailError}</p>
            )}
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full py-2 px-4 rounded-md font-medium transition-colors ${
              isLoading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 focus:bg-blue-700'
            } text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`}
          >
            {isLoading ? (
              <div className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"></circle>
                  <path fill="currentColor" className="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Sending Code...
              </div>
            ) : (
              'Send Verification Code'
            )}
          </button>
        </form>
      </div>
    );
  }

  // Step 2: Verification code input
  return (
    <div className="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Enter Verification Code
        </h1>
        <p className="text-gray-600 mb-2">
          We've sent a 6-digit code to:
        </p>
        <p className="font-medium text-gray-900">
          {savedEmail || email}
        </p>
      </div>

      <form onSubmit={handleCodeSubmit} className="space-y-4">
        <div>
          <label htmlFor="code" className="block text-sm font-medium text-gray-700 mb-1">
            Verification Code
          </label>
          <input
            type="text"
            id="code"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            disabled={isLoading}
            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed text-center text-lg font-mono tracking-wider ${
              codeError ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder="123456"
            maxLength="6"
            autoComplete="one-time-code"
            autoFocus
          />
          {codeError && (
            <p className="mt-1 text-sm text-red-600">{codeError}</p>
          )}
          <p className="mt-1 text-xs text-gray-500">
            Enter the 6-digit code sent to your email
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading || code.length !== 6}
          className={`w-full py-2 px-4 rounded-md font-medium transition-colors ${
            isLoading || code.length !== 6
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-green-600 hover:bg-green-700 focus:bg-green-700'
          } text-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2`}
        >
          {isLoading ? (
            <div className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"></circle>
                <path fill="currentColor" className="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Verifying...
            </div>
          ) : (
            'Verify Code & Login'
          )}
        </button>

        <div className="flex justify-between items-center text-sm">
          <button
            type="button"
            onClick={handleBackToEmail}
            className="text-gray-600 hover:text-gray-900 transition-colors"
            disabled={isLoading}
          >
            ← Change email
          </button>
          <button
            type="button"
            onClick={handleResendCode}
            className="text-blue-600 hover:text-blue-800 transition-colors"
            disabled={isLoading}
          >
            Resend code
          </button>
        </div>
      </form>
    </div>
  );
}

export default VoterLogin;