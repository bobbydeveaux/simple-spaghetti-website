import React from 'react';

/**
 * CandidateCard component for displaying candidate information
 * Used in candidate management and voting interfaces
 */
const CandidateCard = ({
    candidate,
    showActions = false,
    onEdit = null,
    onDelete = null,
    compact = false
}) => {
    const {
        candidate_id,
        name,
        position,
        bio,
        photo_url,
        created_at
    } = candidate;

    // Default photo placeholder if no photo provided
    const defaultPhoto = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120' viewBox='0 0 120 120'%3E%3Crect width='120' height='120' fill='%23f3f4f6'/%3E%3Ctext x='60' y='60' text-anchor='middle' dy='.35em' font-family='Arial, sans-serif' font-size='14' fill='%23666'%3ENo Photo%3C/text%3E%3C/svg%3E";

    return (
        <div className={`bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 ${
            compact ? 'p-4' : 'p-6'
        }`}>
            {/* Header with photo and basic info */}
            <div className="flex items-start space-x-4">
                {/* Candidate Photo */}
                <div className={`flex-shrink-0 ${compact ? 'w-16 h-16' : 'w-20 h-20'}`}>
                    <img
                        src={photo_url || defaultPhoto}
                        alt={`${name} - ${position} candidate`}
                        className="w-full h-full rounded-lg object-cover border border-gray-200"
                        onError={(e) => {
                            e.target.src = defaultPhoto;
                        }}
                    />
                </div>

                {/* Candidate Info */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                        <div>
                            <h3 className={`font-semibold text-gray-900 ${
                                compact ? 'text-lg' : 'text-xl'
                            }`}>
                                {name}
                            </h3>
                            <p className={`text-gray-600 font-medium ${
                                compact ? 'text-sm' : 'text-base'
                            }`}>
                                {position}
                            </p>
                            {created_at && !compact && (
                                <p className="text-xs text-gray-400 mt-1">
                                    Added {new Date(created_at).toLocaleDateString()}
                                </p>
                            )}
                        </div>

                        {/* Action Buttons */}
                        {showActions && (
                            <div className="flex space-x-2 ml-4">
                                {onEdit && (
                                    <button
                                        onClick={() => onEdit(candidate)}
                                        className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                                        title="Edit candidate"
                                    >
                                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                        </svg>
                                        Edit
                                    </button>
                                )}

                                {onDelete && (
                                    <button
                                        onClick={() => onDelete(candidate)}
                                        className="inline-flex items-center px-3 py-1 border border-red-300 rounded-md text-sm font-medium text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                                        title="Delete candidate"
                                    >
                                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                        </svg>
                                        Delete
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Candidate Bio */}
            {bio && (
                <div className="mt-4">
                    <p className={`text-gray-700 leading-relaxed ${
                        compact ? 'text-sm line-clamp-2' : 'text-base'
                    }`}>
                        {bio}
                    </p>
                </div>
            )}

            {/* Position Badge */}
            <div className="mt-3 flex items-center justify-between">
                <div className="flex">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        position === 'President' ? 'bg-blue-100 text-blue-800' :
                        position === 'Vice President' ? 'bg-green-100 text-green-800' :
                        position === 'Secretary' ? 'bg-purple-100 text-purple-800' :
                        position === 'Treasurer' ? 'bg-orange-100 text-orange-800' :
                        'bg-gray-100 text-gray-800'
                    }`}>
                        {position}
                    </span>
                </div>

                {/* Candidate ID for debugging (admin only) */}
                {showActions && (
                    <span className="text-xs text-gray-400 font-mono">
                        ID: {candidate_id?.slice(0, 8)}...
                    </span>
                )}
            </div>
        </div>
    );
};

/**
 * CandidateGrid component for displaying multiple candidates in a grid layout
 */
export const CandidateGrid = ({
    candidates = [],
    showActions = false,
    onEdit,
    onDelete,
    compact = false,
    emptyMessage = "No candidates found"
}) => {
    if (candidates.length === 0) {
        return (
            <div className="text-center py-12">
                <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                    <path d="M34 40h10v-4a6 6 0 00-10.712-3.714M34 40H14m20 0v-4a9.971 9.971 0 00-.712-3.714M14 40H4v-4a6 6 0 0110.713-3.714M14 40v-4c0-1.313.253-2.566.713-3.714m0 0A10.003 10.003 0 0124 26c4.21 0 7.813 2.602 9.288 6.286M30 14a6 6 0 11-12 0 6 6 0 0112 0z" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <h3 className="mt-2 text-sm font-medium text-gray-900">No candidates</h3>
                <p className="mt-1 text-sm text-gray-500">{emptyMessage}</p>
            </div>
        );
    }

    return (
        <div className={`grid gap-6 ${
            compact ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1 md:grid-cols-2'
        }`}>
            {candidates.map((candidate) => (
                <CandidateCard
                    key={candidate.candidate_id}
                    candidate={candidate}
                    showActions={showActions}
                    onEdit={onEdit}
                    onDelete={onDelete}
                    compact={compact}
                />
            ))}
        </div>
    );
};

export default CandidateCard;