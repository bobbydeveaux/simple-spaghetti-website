"""
PTA Voting System Admin Routes
Admin-only endpoints for candidate management and election administration.
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, List
import logging

# Import existing utilities and models
from .data_store import voting_data_store
from .models import Candidate
from .middleware import admin_required

# Create Blueprint for admin routes
admin_bp = Blueprint('admin', __name__, url_prefix='/api/voting/admin')

# Set up logging
logger = logging.getLogger(__name__)


def validate_candidate_data(data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate candidate data from request.

    Args:
        data: Dictionary containing candidate data

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ['name', 'position']

    # Check required fields
    for field in required_fields:
        if not data.get(field):
            return False, f"Missing required field: {field}"

    # Validate field types and lengths
    if not isinstance(data['name'], str) or len(data['name'].strip()) < 2:
        return False, "Name must be at least 2 characters"

    if not isinstance(data['position'], str) or len(data['position'].strip()) < 2:
        return False, "Position must be at least 2 characters"

    # Validate bio if provided
    if 'bio' in data and data['bio'] is not None:
        if not isinstance(data['bio'], str):
            return False, "Bio must be a string"
        if len(data['bio']) > 1000:
            return False, "Bio must be less than 1000 characters"

    # Validate photo_url if provided
    if 'photo_url' in data and data['photo_url'] is not None:
        if not isinstance(data['photo_url'], str):
            return False, "Photo URL must be a string"
        if len(data['photo_url']) > 500:
            return False, "Photo URL must be less than 500 characters"

    return True, ""


@admin_bp.route('/candidates', methods=['GET'])
@admin_required
def get_all_candidates():
    """
    Get all candidates in the system.

    Returns:
        200: List of all candidates
        401: Unauthorized (handled by decorator)
        403: Admin access required (handled by decorator)
        500: Server error
    """
    try:
        candidates = voting_data_store.get_all_candidates()

        # Convert candidates to dictionaries for JSON response
        candidates_data = []
        for candidate in candidates:
            candidate_dict = {
                "candidate_id": candidate.candidate_id,
                "name": candidate.name,
                "position": candidate.position,
                "bio": candidate.bio or "",
                "photo_url": candidate.photo_url or "",
                "created_at": candidate.created_at.isoformat() if candidate.created_at else None
            }
            candidates_data.append(candidate_dict)

        return jsonify({
            "candidates": candidates_data,
            "total": len(candidates_data)
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving candidates: {str(e)}")
        return jsonify({
            "error": "Failed to retrieve candidates",
            "detail": str(e)
        }), 500


@admin_bp.route('/candidates', methods=['POST'])
@admin_required
def create_candidate():
    """
    Create a new candidate.

    Request Body:
        {
            "name": "string (required)",
            "position": "string (required)",
            "bio": "string (optional)",
            "photo_url": "string (optional)"
        }

    Returns:
        201: Candidate created successfully
        400: Invalid data
        401: Unauthorized (handled by decorator)
        403: Admin access required (handled by decorator)
        500: Server error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "error": "No data provided",
                "detail": "Request body must contain candidate data"
            }), 400

        # Validate input data
        is_valid, error_msg = validate_candidate_data(data)
        if not is_valid:
            return jsonify({
                "error": "Validation failed",
                "detail": error_msg
            }), 400

        # Create candidate object
        candidate = Candidate(
            name=data['name'].strip(),
            position=data['position'].strip(),
            bio=data.get('bio', '').strip() if data.get('bio') else None,
            photo_url=data.get('photo_url', '').strip() if data.get('photo_url') else None
        )

        # Add to data store
        voting_data_store.add_candidate(candidate)

        # Return created candidate data
        return jsonify({
            "candidate": {
                "candidate_id": candidate.candidate_id,
                "name": candidate.name,
                "position": candidate.position,
                "bio": candidate.bio or "",
                "photo_url": candidate.photo_url or "",
                "created_at": candidate.created_at.isoformat()
            },
            "message": "Candidate created successfully"
        }), 201

    except Exception as e:
        logger.error(f"Error creating candidate: {str(e)}")
        return jsonify({
            "error": "Failed to create candidate",
            "detail": str(e)
        }), 500


@admin_bp.route('/candidates/<string:candidate_id>', methods=['GET'])
@admin_required
def get_candidate(candidate_id: str):
    """
    Get a specific candidate by ID.

    Args:
        candidate_id: The ID of the candidate to retrieve

    Returns:
        200: Candidate data
        404: Candidate not found
        401: Unauthorized (handled by decorator)
        403: Admin access required (handled by decorator)
        500: Server error
    """
    try:
        candidate = voting_data_store.get_candidate_by_id(candidate_id)

        if not candidate:
            return jsonify({
                "error": "Candidate not found",
                "detail": f"No candidate found with ID: {candidate_id}"
            }), 404

        return jsonify({
            "candidate": {
                "candidate_id": candidate.candidate_id,
                "name": candidate.name,
                "position": candidate.position,
                "bio": candidate.bio or "",
                "photo_url": candidate.photo_url or "",
                "created_at": candidate.created_at.isoformat() if candidate.created_at else None
            }
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving candidate {candidate_id}: {str(e)}")
        return jsonify({
            "error": "Failed to retrieve candidate",
            "detail": str(e)
        }), 500


@admin_bp.route('/candidates/<string:candidate_id>', methods=['PUT'])
@admin_required
def update_candidate(candidate_id: str):
    """
    Update an existing candidate.

    Args:
        candidate_id: The ID of the candidate to update

    Request Body:
        {
            "name": "string (required)",
            "position": "string (required)",
            "bio": "string (optional)",
            "photo_url": "string (optional)"
        }

    Returns:
        200: Candidate updated successfully
        400: Invalid data
        404: Candidate not found
        401: Unauthorized (handled by decorator)
        403: Admin access required (handled by decorator)
        500: Server error
    """
    try:
        # Check if candidate exists
        existing_candidate = voting_data_store.get_candidate_by_id(candidate_id)
        if not existing_candidate:
            return jsonify({
                "error": "Candidate not found",
                "detail": f"No candidate found with ID: {candidate_id}"
            }), 404

        data = request.get_json()
        if not data:
            return jsonify({
                "error": "No data provided",
                "detail": "Request body must contain candidate data"
            }), 400

        # Validate input data
        is_valid, error_msg = validate_candidate_data(data)
        if not is_valid:
            return jsonify({
                "error": "Validation failed",
                "detail": error_msg
            }), 400

        # Create updated candidate object
        updated_candidate = Candidate(
            candidate_id=candidate_id,  # Keep the same ID
            name=data['name'].strip(),
            position=data['position'].strip(),
            bio=data.get('bio', '').strip() if data.get('bio') else None,
            photo_url=data.get('photo_url', '').strip() if data.get('photo_url') else None,
            created_at=existing_candidate.created_at  # Keep original creation time
        )

        # Update in data store
        success = voting_data_store.update_candidate(candidate_id, updated_candidate)
        if not success:
            return jsonify({
                "error": "Update failed",
                "detail": "Failed to update candidate in data store"
            }), 500

        # Return updated candidate data
        return jsonify({
            "candidate": {
                "candidate_id": updated_candidate.candidate_id,
                "name": updated_candidate.name,
                "position": updated_candidate.position,
                "bio": updated_candidate.bio or "",
                "photo_url": updated_candidate.photo_url or "",
                "created_at": updated_candidate.created_at.isoformat() if updated_candidate.created_at else None
            },
            "message": "Candidate updated successfully"
        }), 200

    except Exception as e:
        logger.error(f"Error updating candidate {candidate_id}: {str(e)}")
        return jsonify({
            "error": "Failed to update candidate",
            "detail": str(e)
        }), 500


@admin_bp.route('/candidates/<string:candidate_id>', methods=['DELETE'])
@admin_required
def delete_candidate(candidate_id: str):
    """
    Delete a candidate by ID.

    Args:
        candidate_id: The ID of the candidate to delete

    Returns:
        200: Candidate deleted successfully
        404: Candidate not found
        401: Unauthorized (handled by decorator)
        403: Admin access required (handled by decorator)
        500: Server error
    """
    try:
        # Check if candidate exists
        existing_candidate = voting_data_store.get_candidate_by_id(candidate_id)
        if not existing_candidate:
            return jsonify({
                "error": "Candidate not found",
                "detail": f"No candidate found with ID: {candidate_id}"
            }), 404

        # Delete from data store
        success = voting_data_store.delete_candidate(candidate_id)
        if not success:
            return jsonify({
                "error": "Delete failed",
                "detail": "Failed to delete candidate from data store"
            }), 500

        return jsonify({
            "message": "Candidate deleted successfully",
            "deleted_candidate_id": candidate_id
        }), 200

    except Exception as e:
        logger.error(f"Error deleting candidate {candidate_id}: {str(e)}")
        return jsonify({
            "error": "Failed to delete candidate",
            "detail": str(e)
        }), 500


@admin_bp.route('/candidates/by-position/<string:position>', methods=['GET'])
@admin_required
def get_candidates_by_position(position: str):
    """
    Get all candidates for a specific position.

    Args:
        position: The position to filter candidates by

    Returns:
        200: List of candidates for the position
        401: Unauthorized (handled by decorator)
        403: Admin access required (handled by decorator)
        500: Server error
    """
    try:
        candidates = voting_data_store.get_candidates_for_position(position)

        # Convert candidates to dictionaries for JSON response
        candidates_data = []
        for candidate in candidates:
            candidate_dict = {
                "candidate_id": candidate.candidate_id,
                "name": candidate.name,
                "position": candidate.position,
                "bio": candidate.bio or "",
                "photo_url": candidate.photo_url or "",
                "created_at": candidate.created_at.isoformat() if candidate.created_at else None
            }
            candidates_data.append(candidate_dict)

        return jsonify({
            "position": position,
            "candidates": candidates_data,
            "total": len(candidates_data)
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving candidates for position {position}: {str(e)}")
        return jsonify({
            "error": "Failed to retrieve candidates for position",
            "detail": str(e)
        }), 500