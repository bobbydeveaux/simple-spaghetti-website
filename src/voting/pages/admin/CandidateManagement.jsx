import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import CandidateCard, { CandidateGrid } from '../../components/CandidateCard';
import {
    getAllCandidates,
    createCandidate,
    updateCandidate,
    deleteCandidate
} from '../../api/votingApi';

/**
 * CandidateManagement page for admin candidate CRUD operations
 * Includes forms for add/edit and displays candidates grouped by position
 */
const CandidateManagement = () => {
    const { isAdmin, logout } = useAuth();

    // State management
    const [candidates, setCandidates] = useState([]);
    const [candidatesByPosition, setCandidatesByPosition] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // Form state
    const [showForm, setShowForm] = useState(false);
    const [editingCandidate, setEditingCandidate] = useState(null);
    const [formData, setFormData] = useState({
        name: '',
        position: 'President',
        bio: '',
        photo_url: ''
    });
    const [formErrors, setFormErrors] = useState({});
    const [formLoading, setFormLoading] = useState(false);

    // Delete confirmation state
    const [deleteCandidate, setDeleteCandidate] = useState(null);
    const [deleteLoading, setDeleteLoading] = useState(false);

    // Active tab for position filtering
    const [activeTab, setActiveTab] = useState('all');

    const positions = ['President', 'Vice President', 'Secretary', 'Treasurer'];

    // Redirect if not admin
    useEffect(() => {
        if (!isAdmin()) {
            logout();
        }
    }, [isAdmin, logout]);

    // Load candidates on component mount
    useEffect(() => {
        loadCandidates();
    }, []);

    /**
     * Load all candidates from API
     */
    const loadCandidates = async () => {
        try {
            setLoading(true);
            setError('');

            const response = await getAllCandidates();

            setCandidates(response.candidates || []);
            setCandidatesByPosition(response.candidates_by_position || {});
        } catch (err) {
            console.error('Error loading candidates:', err);
            setError('Failed to load candidates. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    /**
     * Validate form data
     */
    const validateForm = (data) => {
        const errors = {};

        // Name validation
        if (!data.name?.trim()) {
            errors.name = 'Name is required';
        } else if (data.name.trim().length < 2) {
            errors.name = 'Name must be at least 2 characters';
        } else if (data.name.trim().length > 100) {
            errors.name = 'Name must be less than 100 characters';
        }

        // Position validation
        if (!data.position) {
            errors.position = 'Position is required';
        } else if (!positions.includes(data.position)) {
            errors.position = 'Invalid position selected';
        }

        // Bio validation
        if (!data.bio?.trim()) {
            errors.bio = 'Bio is required';
        } else if (data.bio.trim().length < 10) {
            errors.bio = 'Bio must be at least 10 characters';
        } else if (data.bio.trim().length > 500) {
            errors.bio = 'Bio must be less than 500 characters';
        }

        // Photo URL validation (optional)
        if (data.photo_url?.trim()) {
            const urlPattern = /^https?:\/\/[^\s/$.?#].[^\s]*$/;
            if (!urlPattern.test(data.photo_url.trim())) {
                errors.photo_url = 'Photo URL must be a valid HTTP/HTTPS URL';
            }
        }

        return errors;
    };

    /**
     * Handle form submission (create or update)
     */
    const handleSubmit = async (e) => {
        e.preventDefault();

        // Validate form
        const errors = validateForm(formData);
        setFormErrors(errors);

        if (Object.keys(errors).length > 0) {
            return;
        }

        try {
            setFormLoading(true);
            setError('');
            setSuccess('');

            // Prepare data
            const candidateData = {
                name: formData.name.trim(),
                position: formData.position,
                bio: formData.bio.trim(),
                photo_url: formData.photo_url?.trim() || null
            };

            if (editingCandidate) {
                // Update existing candidate
                await updateCandidate(editingCandidate.candidate_id, candidateData);
                setSuccess('Candidate updated successfully');
            } else {
                // Create new candidate
                await createCandidate(candidateData);
                setSuccess('Candidate created successfully');
            }

            // Reset form and reload data
            resetForm();
            await loadCandidates();

        } catch (err) {
            console.error('Error saving candidate:', err);
            if (err.message && err.message.includes('Validation failed')) {
                setError('Please check your input and try again.');
            } else {
                setError('Failed to save candidate. Please try again.');
            }
        } finally {
            setFormLoading(false);
        }
    };

    /**
     * Handle candidate deletion
     */
    const handleDelete = async (candidate) => {
        try {
            setDeleteLoading(true);
            setError('');
            setSuccess('');

            await deleteCandidate(candidate.candidate_id);

            setSuccess('Candidate deleted successfully');
            setDeleteCandidate(null);
            await loadCandidates();

        } catch (err) {
            console.error('Error deleting candidate:', err);
            setError('Failed to delete candidate. Please try again.');
        } finally {
            setDeleteLoading(false);
        }
    };

    /**
     * Start editing a candidate
     */
    const handleEdit = (candidate) => {
        setEditingCandidate(candidate);
        setFormData({
            name: candidate.name,
            position: candidate.position,
            bio: candidate.bio,
            photo_url: candidate.photo_url || ''
        });
        setFormErrors({});
        setShowForm(true);
    };

    /**
     * Reset form to initial state
     */
    const resetForm = () => {
        setEditingCandidate(null);
        setFormData({
            name: '',
            position: 'President',
            bio: '',
            photo_url: ''
        });
        setFormErrors({});
        setShowForm(false);
    };

    /**
     * Get candidates for active tab
     */
    const getDisplayCandidates = () => {
        if (activeTab === 'all') {
            return candidates;
        }
        return candidatesByPosition[activeTab] || [];
    };

    // Show loading spinner
    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Page Header */}
                <div className="md:flex md:items-center md:justify-between mb-8">
                    <div className="flex-1 min-w-0">
                        <h1 className="text-3xl font-bold leading-tight text-gray-900">
                            Candidate Management
                        </h1>
                        <p className="mt-1 text-sm text-gray-500">
                            Manage candidates for the PTA election. Add, edit, and organize candidates by position.
                        </p>
                    </div>
                    <div className="mt-4 flex md:mt-0 md:ml-4">
                        <button
                            onClick={() => setShowForm(true)}
                            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        >
                            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                            </svg>
                            Add Candidate
                        </button>
                    </div>
                </div>

                {/* Alert Messages */}
                {error && (
                    <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
                        <div className="flex">
                            <svg className="flex-shrink-0 h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <div className="ml-3">
                                <p className="text-sm text-red-700">{error}</p>
                            </div>
                        </div>
                    </div>
                )}

                {success && (
                    <div className="mb-6 bg-green-50 border border-green-200 rounded-md p-4">
                        <div className="flex">
                            <svg className="flex-shrink-0 h-5 w-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <div className="ml-3">
                                <p className="text-sm text-green-700">{success}</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Position Tabs */}
                <div className="mb-6">
                    <nav className="flex space-x-8" aria-label="Position Tabs">
                        <button
                            onClick={() => setActiveTab('all')}
                            className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'all'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            All Candidates ({candidates.length})
                        </button>
                        {positions.map((position) => (
                            <button
                                key={position}
                                onClick={() => setActiveTab(position)}
                                className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                                    activeTab === position
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }`}
                            >
                                {position} ({(candidatesByPosition[position] || []).length})
                            </button>
                        ))}
                    </nav>
                </div>

                {/* Candidates Display */}
                <div className="mb-8">
                    <CandidateGrid
                        candidates={getDisplayCandidates()}
                        showActions={true}
                        onEdit={handleEdit}
                        onDelete={(candidate) => setDeleteCandidate(candidate)}
                        emptyMessage={
                            activeTab === 'all'
                                ? "No candidates have been added yet. Click 'Add Candidate' to get started."
                                : `No candidates for ${activeTab} position yet.`
                        }
                    />
                </div>

                {/* Add/Edit Candidate Modal */}
                {showForm && (
                    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                        <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-2xl shadow-lg rounded-md bg-white">
                            <div className="mt-3">
                                <div className="flex items-center justify-between mb-6">
                                    <h3 className="text-lg font-medium text-gray-900">
                                        {editingCandidate ? 'Edit Candidate' : 'Add New Candidate'}
                                    </h3>
                                    <button
                                        onClick={resetForm}
                                        className="text-gray-400 hover:text-gray-600"
                                    >
                                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                </div>

                                <form onSubmit={handleSubmit} className="space-y-6">
                                    {/* Name Field */}
                                    <div>
                                        <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                                            Name *
                                        </label>
                                        <input
                                            type="text"
                                            id="name"
                                            value={formData.name}
                                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                                formErrors.name ? 'border-red-300' : 'border-gray-300'
                                            }`}
                                            placeholder="Enter candidate's full name"
                                        />
                                        {formErrors.name && (
                                            <p className="mt-1 text-sm text-red-600">{formErrors.name}</p>
                                        )}
                                    </div>

                                    {/* Position Field */}
                                    <div>
                                        <label htmlFor="position" className="block text-sm font-medium text-gray-700 mb-2">
                                            Position *
                                        </label>
                                        <select
                                            id="position"
                                            value={formData.position}
                                            onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                                            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                                formErrors.position ? 'border-red-300' : 'border-gray-300'
                                            }`}
                                        >
                                            {positions.map((position) => (
                                                <option key={position} value={position}>
                                                    {position}
                                                </option>
                                            ))}
                                        </select>
                                        {formErrors.position && (
                                            <p className="mt-1 text-sm text-red-600">{formErrors.position}</p>
                                        )}
                                    </div>

                                    {/* Photo URL Field */}
                                    <div>
                                        <label htmlFor="photo_url" className="block text-sm font-medium text-gray-700 mb-2">
                                            Photo URL
                                        </label>
                                        <input
                                            type="url"
                                            id="photo_url"
                                            value={formData.photo_url}
                                            onChange={(e) => setFormData({ ...formData, photo_url: e.target.value })}
                                            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                                formErrors.photo_url ? 'border-red-300' : 'border-gray-300'
                                            }`}
                                            placeholder="https://example.com/photo.jpg (optional)"
                                        />
                                        {formErrors.photo_url && (
                                            <p className="mt-1 text-sm text-red-600">{formErrors.photo_url}</p>
                                        )}
                                        <p className="mt-1 text-sm text-gray-500">
                                            Optional. Provide a direct link to the candidate's photo.
                                        </p>
                                    </div>

                                    {/* Bio Field */}
                                    <div>
                                        <label htmlFor="bio" className="block text-sm font-medium text-gray-700 mb-2">
                                            Bio *
                                        </label>
                                        <textarea
                                            id="bio"
                                            rows="4"
                                            value={formData.bio}
                                            onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                                            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                                formErrors.bio ? 'border-red-300' : 'border-gray-300'
                                            }`}
                                            placeholder="Enter candidate's background, qualifications, and goals..."
                                        />
                                        {formErrors.bio && (
                                            <p className="mt-1 text-sm text-red-600">{formErrors.bio}</p>
                                        )}
                                        <p className="mt-1 text-sm text-gray-500">
                                            {formData.bio.length}/500 characters (minimum 10 required)
                                        </p>
                                    </div>

                                    {/* Form Actions */}
                                    <div className="flex justify-end space-x-3 pt-6">
                                        <button
                                            type="button"
                                            onClick={resetForm}
                                            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            type="submit"
                                            disabled={formLoading}
                                            className="inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {formLoading && (
                                                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                </svg>
                                            )}
                                            {editingCandidate ? 'Update' : 'Add'} Candidate
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                )}

                {/* Delete Confirmation Modal */}
                {deleteCandidate && (
                    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                        <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-md shadow-lg rounded-md bg-white">
                            <div className="mt-3 text-center">
                                <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                                    <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.232 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                    </svg>
                                </div>
                                <h3 className="text-lg font-medium text-gray-900 mb-2">Delete Candidate</h3>
                                <p className="text-sm text-gray-500 mb-6">
                                    Are you sure you want to delete <strong>{deleteCandidate.name}</strong>?
                                    This action cannot be undone.
                                </p>
                                <div className="flex justify-center space-x-3">
                                    <button
                                        onClick={() => setDeleteCandidate(null)}
                                        className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={() => handleDelete(deleteCandidate)}
                                        disabled={deleteLoading}
                                        className="inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {deleteLoading && (
                                            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                            </svg>
                                        )}
                                        Delete
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default CandidateManagement;