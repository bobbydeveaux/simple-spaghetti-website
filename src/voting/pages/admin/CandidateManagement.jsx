/**
 * CandidateManagement component for PTA Voting System Admin Panel
 *
 * Provides complete candidate management functionality with:
 * - Table view of all candidates with edit/delete actions
 * - Add new candidate form
 * - Edit existing candidate form
 * - Confirmation dialogs for destructive actions
 * - Responsive design with Tailwind CSS
 */

import React, { useState, useEffect } from 'react';
import votingApi from '../../api/votingApi';

const CandidateManagement = () => {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editingCandidate, setEditingCandidate] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  // Form state for add/edit candidate
  const [formData, setFormData] = useState({
    name: '',
    position: 'president',
    bio: '',
    photo_url: ''
  });

  const positions = [
    { value: 'president', label: 'President' },
    { value: 'vice_president', label: 'Vice President' },
    { value: 'secretary', label: 'Secretary' },
    { value: 'treasurer', label: 'Treasurer' }
  ];

  // Load all candidates
  const loadCandidates = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await votingApi.getAllCandidates();
      setCandidates(response.candidates || []);
    } catch (err) {
      console.error('Failed to load candidates:', err);
      setError(err.message || 'Failed to load candidates');
    } finally {
      setLoading(false);
    }
  };

  // Load data on component mount
  useEffect(() => {
    loadCandidates();
  }, []);

  // Reset form to initial state
  const resetForm = () => {
    setFormData({
      name: '',
      position: 'president',
      bio: '',
      photo_url: ''
    });
    setEditingCandidate(null);
  };

  // Handle opening add candidate modal
  const handleAddCandidate = () => {
    resetForm();
    setShowModal(true);
  };

  // Handle opening edit candidate modal
  const handleEditCandidate = (candidate) => {
    setFormData({
      name: candidate.name,
      position: candidate.position,
      bio: candidate.bio,
      photo_url: candidate.photo_url || ''
    });
    setEditingCandidate(candidate);
    setShowModal(true);
  };

  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setError(null);

      // Validate form data
      if (!formData.name.trim()) {
        throw new Error('Candidate name is required');
      }
      if (!formData.bio.trim()) {
        throw new Error('Candidate biography is required');
      }

      const candidateData = {
        name: formData.name.trim(),
        position: formData.position,
        bio: formData.bio.trim(),
        ...(formData.photo_url.trim() && { photo_url: formData.photo_url.trim() })
      };

      if (editingCandidate) {
        // Update existing candidate
        await votingApi.updateCandidate(editingCandidate.candidate_id, candidateData);
      } else {
        // Create new candidate
        await votingApi.createCandidate(candidateData);
      }

      // Reload candidates and close modal
      await loadCandidates();
      setShowModal(false);
      resetForm();

    } catch (err) {
      console.error('Failed to save candidate:', err);
      setError(err.message || 'Failed to save candidate');
    }
  };

  // Handle delete candidate confirmation
  const handleDeleteClick = (candidate) => {
    setDeleteConfirm(candidate);
  };

  // Handle confirmed deletion
  const handleConfirmDelete = async () => {
    if (!deleteConfirm) return;

    try {
      setError(null);
      await votingApi.deleteCandidate(deleteConfirm.candidate_id);
      await loadCandidates();
      setDeleteConfirm(null);
    } catch (err) {
      console.error('Failed to delete candidate:', err);
      setError(err.message || 'Failed to delete candidate');
    }
  };

  // Format position for display
  const formatPosition = (position) => {
    const positionMap = {
      'president': 'President',
      'vice_president': 'Vice President',
      'secretary': 'Secretary',
      'treasurer': 'Treasurer'
    };
    return positionMap[position] || position;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading candidates...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-gray-200 pb-4">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Candidate Management</h2>
            <p className="mt-1 text-gray-600">
              Manage election candidates. Total: {candidates.length} candidates
            </p>
          </div>
          <button
            onClick={handleAddCandidate}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Add Candidate
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-2 text-sm text-red-700">{error}</div>
              <div className="mt-3">
                <button
                  onClick={() => setError(null)}
                  className="text-sm bg-red-100 text-red-700 px-3 py-1 rounded hover:bg-red-200"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Candidates Table */}
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Candidate
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Position
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Biography
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {candidates.length === 0 ? (
                <tr>
                  <td colSpan="4" className="px-6 py-12 text-center text-gray-500">
                    No candidates found. Add the first candidate to get started.
                  </td>
                </tr>
              ) : (
                candidates.map((candidate) => (
                  <tr key={candidate.candidate_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {candidate.photo_url && (
                          <div className="flex-shrink-0 h-10 w-10">
                            <img
                              className="h-10 w-10 rounded-full object-cover"
                              src={candidate.photo_url}
                              alt={candidate.name}
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                          </div>
                        )}
                        <div className={candidate.photo_url ? "ml-4" : ""}>
                          <div className="text-sm font-medium text-gray-900">
                            {candidate.name}
                          </div>
                          <div className="text-sm text-gray-500 font-mono">
                            ID: {candidate.candidate_id.substring(0, 12)}...
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                        {formatPosition(candidate.position)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 max-w-xs truncate">
                        {candidate.bio}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                      <button
                        onClick={() => handleEditCandidate(candidate)}
                        className="text-indigo-600 hover:text-indigo-900 px-2 py-1 rounded hover:bg-indigo-50"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteClick(candidate)}
                        className="text-red-600 hover:text-red-900 px-2 py-1 rounded hover:bg-red-50"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add/Edit Candidate Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900">
                {editingCandidate ? 'Edit Candidate' : 'Add New Candidate'}
              </h3>

              <form onSubmit={handleSubmit} className="mt-4 space-y-4">
                {/* Name */}
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                    Candidate Name*
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter candidate's full name"
                  />
                </div>

                {/* Position */}
                <div>
                  <label htmlFor="position" className="block text-sm font-medium text-gray-700">
                    Position*
                  </label>
                  <select
                    id="position"
                    name="position"
                    value={formData.position}
                    onChange={handleInputChange}
                    required
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    {positions.map(pos => (
                      <option key={pos.value} value={pos.value}>
                        {pos.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Biography */}
                <div>
                  <label htmlFor="bio" className="block text-sm font-medium text-gray-700">
                    Biography*
                  </label>
                  <textarea
                    id="bio"
                    name="bio"
                    value={formData.bio}
                    onChange={handleInputChange}
                    required
                    rows="4"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter candidate's background and qualifications"
                  />
                </div>

                {/* Photo URL */}
                <div>
                  <label htmlFor="photo_url" className="block text-sm font-medium text-gray-700">
                    Photo URL (optional)
                  </label>
                  <input
                    type="url"
                    id="photo_url"
                    name="photo_url"
                    value={formData.photo_url}
                    onChange={handleInputChange}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="https://example.com/photo.jpg"
                  />
                </div>

                {/* Form Actions */}
                <div className="flex space-x-3 pt-4">
                  <button
                    type="submit"
                    className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  >
                    {editingCandidate ? 'Update Candidate' : 'Add Candidate'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      resetForm();
                    }}
                    className="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-full max-w-sm shadow-lg rounded-md bg-white">
            <div className="mt-3 text-center">
              <h3 className="text-lg font-medium text-gray-900">Confirm Deletion</h3>
              <div className="mt-2 px-7 py-3">
                <p className="text-sm text-gray-500">
                  Are you sure you want to delete candidate "{deleteConfirm.name}"?
                  This action cannot be undone.
                </p>
              </div>
              <div className="flex space-x-3 px-4 py-3">
                <button
                  onClick={handleConfirmDelete}
                  className="flex-1 bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                >
                  Delete
                </button>
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CandidateManagement;