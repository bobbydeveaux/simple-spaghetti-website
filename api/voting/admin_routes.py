"""
Admin routes for PTA Voting System.
Handles candidate management and other admin operations.
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any, Tuple, List
from .middleware import require_admin
from .data_store import voting_data_store
from .models import Candidate
import re


admin_bp = Blueprint('admin', __name__, url_prefix='/api/voting/admin')


def validate_candidate_data(data: Dict[str, Any], is_update: bool = False) -> Tuple[List[str], bool]:
    """
    Validate candidate form data.

    Args:
        data: Candidate data dict
        is_update: Whether this is an update operation

    Returns:
        Tuple of (error_messages, is_valid)
    """
    errors = []

    # Required fields
    if not data.get('name', '').strip():
        errors.append("Name is required")
    elif len(data['name'].strip()) < 2:
        errors.append("Name must be at least 2 characters")
    elif len(data['name'].strip()) > 100:
        errors.append("Name must be less than 100 characters")

    if not data.get('position', '').strip():
        errors.append("Position is required")
    elif data['position'] not in ["President", "Vice President", "Secretary", "Treasurer"]:
        errors.append("Invalid position. Must be one of: President, Vice President, Secretary, Treasurer")

    if not data.get('bio', '').strip():
        errors.append("Bio is required")
    elif len(data['bio'].strip()) < 10:
        errors.append("Bio must be at least 10 characters")
    elif len(data['bio'].strip()) > 500:
        errors.append("Bio must be less than 500 characters")

    # Optional photo URL validation
    photo_url = data.get('photo_url', '').strip()
    if photo_url:
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, photo_url):
            errors.append("Photo URL must be a valid HTTP/HTTPS URL")

    return errors, len(errors) == 0


@admin_bp.route('/candidates', methods=['GET'])
@require_admin
def get_candidates() -> Tuple[Dict[str, Any], int]:
    """
    Get all candidates grouped by position.

    Returns:
        200: {
            "candidates": [
                {
                    "candidate_id": "uuid",
                    "name": "John Doe",
                    "position": "President",
                    "bio": "Bio text",
                    "photo_url": "http://example.com/photo.jpg",
                    "created_at": "2024-01-01T00:00:00"
                }
            ],
            "candidates_by_position": {
                "President": [...],
                "Vice President": [...],
                "Secretary": [...],
                "Treasurer": [...]
            }
        }
        500: {"error": "message"}
    """
    try:
        all_candidates = voting_data_store.get_all_candidates()

        # Group candidates by position
        candidates_by_position = {
            "President": [],
            "Vice President": [],
            "Secretary": [],
            "Treasurer": []
        }

        candidate_dicts = []
        for candidate in all_candidates:
            candidate_dict = candidate.to_dict()
            candidate_dicts.append(candidate_dict)

            position = candidate.position
            if position in candidates_by_position:
                candidates_by_position[position].append(candidate_dict)

        return {
            "candidates": candidate_dicts,
            "candidates_by_position": candidates_by_position,
            "total_count": len(candidate_dicts)
        }, 200

    except Exception as e:
        print(f"Get candidates error: {str(e)}")
        return {"error": "Failed to retrieve candidates"}, 500


@admin_bp.route('/candidates', methods=['POST'])
@require_admin
def create_candidate() -> Tuple[Dict[str, Any], int]:
    """
    Create a new candidate.

    Request body:
        {
            "name": "John Doe",
            "position": "President",
            "bio": "Candidate bio text",
            "photo_url": "http://example.com/photo.jpg" (optional)
        }

    Returns:
        201: {"candidate": {...}, "message": "Candidate created successfully"}
        400: {"error": "Validation error message", "errors": ["field error 1", ...]}
        500: {"error": "Internal server error"}
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        # Validate input data
        errors, is_valid = validate_candidate_data(data)
        if not is_valid:
            return {"error": "Validation failed", "errors": errors}, 400

        # Create candidate object
        candidate = Candidate(
            name=data['name'].strip(),
            position=data['position'],
            bio=data['bio'].strip(),
            photo_url=data.get('photo_url', '').strip() or None
        )

        # Add to data store
        voting_data_store.add_candidate(candidate)

        return {
            "candidate": candidate.to_dict(),
            "message": "Candidate created successfully"
        }, 201

    except Exception as e:
        print(f"Create candidate error: {str(e)}")
        return {"error": "Failed to create candidate"}, 500


@admin_bp.route('/candidates/<candidate_id>', methods=['PUT'])
@require_admin
def update_candidate(candidate_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Update an existing candidate.

    Args:
        candidate_id: The UUID of the candidate to update

    Request body:
        {
            "name": "John Doe",
            "position": "President",
            "bio": "Updated bio text",
            "photo_url": "http://example.com/photo.jpg" (optional)
        }

    Returns:
        200: {"candidate": {...}, "message": "Candidate updated successfully"}
        400: {"error": "Validation error message", "errors": ["field error 1", ...]}
        404: {"error": "Candidate not found"}
        500: {"error": "Internal server error"}
    """
    try:
        # Check if candidate exists
        existing_candidate = voting_data_store.get_candidate_by_id(candidate_id)
        if not existing_candidate:
            return {"error": "Candidate not found"}, 404

        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        # Validate input data
        errors, is_valid = validate_candidate_data(data, is_update=True)
        if not is_valid:
            return {"error": "Validation failed", "errors": errors}, 400

        # Create updated candidate object (preserving original created_at)
        updated_candidate = Candidate(
            candidate_id=candidate_id,
            name=data['name'].strip(),
            position=data['position'],
            bio=data['bio'].strip(),
            photo_url=data.get('photo_url', '').strip() or None,
            created_at=existing_candidate.created_at  # Preserve original timestamp
        )

        # Update in data store
        success = voting_data_store.update_candidate(candidate_id, updated_candidate)
        if not success:
            return {"error": "Failed to update candidate"}, 500

        return {
            "candidate": updated_candidate.to_dict(),
            "message": "Candidate updated successfully"
        }, 200

    except Exception as e:
        print(f"Update candidate error: {str(e)}")
        return {"error": "Failed to update candidate"}, 500


@admin_bp.route('/candidates/<candidate_id>', methods=['DELETE'])
@require_admin
def delete_candidate(candidate_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Delete a candidate.

    Args:
        candidate_id: The UUID of the candidate to delete

    Returns:
        200: {"message": "Candidate deleted successfully"}
        404: {"error": "Candidate not found"}
        500: {"error": "Internal server error"}
    """
    try:
        # Check if candidate exists
        existing_candidate = voting_data_store.get_candidate_by_id(candidate_id)
        if not existing_candidate:
            return {"error": "Candidate not found"}, 404

        # Delete from data store
        success = voting_data_store.delete_candidate(candidate_id)
        if not success:
            return {"error": "Failed to delete candidate"}, 500

        return {"message": "Candidate deleted successfully"}, 200

    except Exception as e:
        print(f"Delete candidate error: {str(e)}")
        return {"error": "Failed to delete candidate"}, 500


@admin_bp.route('/candidates/<candidate_id>', methods=['GET'])
@require_admin
def get_candidate(candidate_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Get a specific candidate by ID.

    Args:
        candidate_id: The UUID of the candidate to retrieve

    Returns:
        200: {"candidate": {...}}
        404: {"error": "Candidate not found"}
        500: {"error": "Internal server error"}
    """
    try:
        candidate = voting_data_store.get_candidate_by_id(candidate_id)
        if not candidate:
            return {"error": "Candidate not found"}, 404

        return {"candidate": candidate.to_dict()}, 200

    except Exception as e:
        print(f"Get candidate error: {str(e)}")
        return {"error": "Failed to retrieve candidate"}, 500