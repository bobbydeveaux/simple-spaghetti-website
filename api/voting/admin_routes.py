"""
PTA Voting System Admin Routes
Administrative endpoints for candidate management and audit log access.
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any, Tuple, List
import uuid
from datetime import datetime
import re

from .data_store import voting_data_store
from .middleware import admin_required
from .models import Candidate

# Create Blueprint for admin routes
admin_bp = Blueprint('admin', __name__, url_prefix='/api/voting/admin')


def validate_candidate_data(data: Dict[str, Any], is_update: bool = False) -> Tuple[List[str], bool]:
    """
    Validate candidate form data with comprehensive validation.

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
@admin_required
def get_all_candidates() -> Tuple[Dict[str, Any], int]:
    """
    Get all candidates in the system.

    Returns:
        200: {
            "candidates": [list of candidate objects],
            "candidates_by_position": {position: [candidates]},
            "total_count": number
        }
        500: {"error": "error message"}
    """
    try:
        all_candidates = voting_data_store.get_all_candidates()

        # Group candidates by position for enhanced UI support
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
            "total": len(candidate_dicts),
            "total_count": len(candidate_dicts)
        }, 200

    except Exception as e:
        print(f"Get all candidates error: {str(e)}")
        return {"error": "Failed to retrieve candidates"}, 500


@admin_bp.route('/candidates', methods=['POST'])
@admin_required
def create_candidate() -> Tuple[Dict[str, Any], int]:
    """
    Create a new candidate.

    Request body:
        {
            "name": "Candidate Name",
            "position": "president",
            "bio": "Candidate biography",
            "photo_url": "https://example.com/photo.jpg" (optional)
        }

    Returns:
        201: {"candidate": candidate_object, "message": "success message"}
        400: {"error": "validation message", "errors": ["field errors"]}
        500: {"error": "error message"}
    """
    try:
        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        # Enhanced validation using comprehensive validation function
        errors, is_valid = validate_candidate_data(data)
        if not is_valid:
            return {"error": "Validation failed", "errors": errors}, 400

        # Validate required fields with fallback to basic validation
        name = data.get("name", "").strip()
        position = data.get("position", "").strip()
        bio = data.get("bio", "").strip()
        photo_url = data.get("photo_url", "").strip() if data.get("photo_url") else None

        if not name:
            return {"error": "Candidate name is required"}, 400
        if not position:
            return {"error": "Position is required"}, 400
        if not bio:
            return {"error": "Candidate biography is required"}, 400

        # Validate position exists in election
        active_election = voting_data_store.get_active_election()
        if not active_election:
            return {"error": "No active election found"}, 400

        if position not in active_election.get_positions_list():
            return {"error": f"Invalid position. Available positions: {', '.join(active_election.get_positions_list())}"}, 400

        # Create candidate
        candidate = Candidate(
            candidate_id=str(uuid.uuid4()),
            name=name,
            position=position,
            bio=bio,
            photo_url=photo_url,
            created_at=datetime.utcnow()
        )

        # Add to data store
        voting_data_store.add_candidate(candidate)

        # Create audit log for admin action
        from .models import AuditLog
        from flask import g

        audit_log = AuditLog(
            voter_id=g.session.voter_id,
            action="ADMIN_ACTION",
            metadata={
                "admin_action": "create_candidate",
                "candidate_id": candidate.candidate_id,
                "candidate_name": name,
                "position": position
            }
        )
        voting_data_store.add_audit_log(audit_log)

        return {
            "candidate": candidate.to_dict(),
            "message": f"Candidate '{name}' created successfully for position '{position}'"
        }, 201

    except Exception as e:
        print(f"Create candidate error: {str(e)}")
        return {"error": "Failed to create candidate"}, 500


@admin_bp.route('/candidates/<candidate_id>', methods=['PUT'])
@admin_required
def update_candidate(candidate_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Update an existing candidate.

    Request body:
        {
            "name": "Updated Name",
            "position": "president",
            "bio": "Updated biography",
            "photo_url": "https://example.com/photo.jpg" (optional)
        }

    Returns:
        200: {"candidate": candidate_object, "message": "success message"}
        400: {"error": "validation message", "errors": ["field errors"]}
        404: {"error": "Candidate not found"}
        500: {"error": "error message"}
    """
    try:
        # Get existing candidate
        existing_candidate = voting_data_store.get_candidate_by_id(candidate_id)
        if not existing_candidate:
            return {"error": "Candidate not found"}, 404

        data = request.get_json()
        if not data:
            return {"error": "Request body required"}, 400

        # Enhanced validation using comprehensive validation function
        errors, is_valid = validate_candidate_data(data, is_update=True)
        if not is_valid:
            return {"error": "Validation failed", "errors": errors}, 400

        # Validate fields if provided with fallback to basic validation
        name = data.get("name", "").strip() if "name" in data else existing_candidate.name
        position = data.get("position", "").strip() if "position" in data else existing_candidate.position
        bio = data.get("bio", "").strip() if "bio" in data else existing_candidate.bio
        photo_url = data.get("photo_url", "").strip() if data.get("photo_url") else existing_candidate.photo_url

        if not name:
            return {"error": "Candidate name cannot be empty"}, 400
        if not position:
            return {"error": "Position cannot be empty"}, 400
        if not bio:
            return {"error": "Candidate biography cannot be empty"}, 400

        # Validate position exists in election
        active_election = voting_data_store.get_active_election()
        if active_election and position not in active_election.get_positions_list():
            return {"error": f"Invalid position. Available positions: {', '.join(active_election.get_positions_list())}"}, 400

        # Update candidate
        updated_candidate = Candidate(
            candidate_id=candidate_id,
            name=name,
            position=position,
            bio=bio,
            photo_url=photo_url,
            created_at=existing_candidate.created_at  # Keep original creation time
        )

        # Update in data store
        success = voting_data_store.update_candidate(candidate_id, updated_candidate)
        if not success:
            return {"error": "Failed to update candidate"}, 500

        # Create audit log for admin action
        from .models import AuditLog
        from flask import g

        audit_log = AuditLog(
            voter_id=g.session.voter_id,
            action="ADMIN_ACTION",
            metadata={
                "admin_action": "update_candidate",
                "candidate_id": candidate_id,
                "candidate_name": name,
                "position": position,
                "changes": {
                    "name": {"old": existing_candidate.name, "new": name},
                    "position": {"old": existing_candidate.position, "new": position},
                    "bio": {"old": existing_candidate.bio[:50] + "..." if len(existing_candidate.bio) > 50 else existing_candidate.bio, "new": bio[:50] + "..." if len(bio) > 50 else bio}
                }
            }
        )
        voting_data_store.add_audit_log(audit_log)

        return {
            "candidate": updated_candidate.to_dict(),
            "message": f"Candidate '{name}' updated successfully"
        }, 200

    except Exception as e:
        print(f"Update candidate error: {str(e)}")
        return {"error": "Failed to update candidate"}, 500


@admin_bp.route('/candidates/<candidate_id>', methods=['DELETE'])
@admin_required
def delete_candidate(candidate_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Delete a candidate.

    Returns:
        200: {"message": "success message"}
        404: {"error": "Candidate not found"}
        500: {"error": "error message"}
    """
    try:
        # Get candidate before deleting for audit log
        candidate = voting_data_store.get_candidate_by_id(candidate_id)
        if not candidate:
            return {"error": "Candidate not found"}, 404

        # Delete from data store
        success = voting_data_store.delete_candidate(candidate_id)
        if not success:
            return {"error": "Failed to delete candidate"}, 500

        # Create audit log for admin action
        from .models import AuditLog
        from flask import g

        audit_log = AuditLog(
            voter_id=g.session.voter_id,
            action="ADMIN_ACTION",
            metadata={
                "admin_action": "delete_candidate",
                "candidate_id": candidate_id,
                "candidate_name": candidate.name,
                "position": candidate.position
            }
        )
        voting_data_store.add_audit_log(audit_log)

        return {
            "message": f"Candidate '{candidate.name}' deleted successfully"
        }, 200

    except Exception as e:
        print(f"Delete candidate error: {str(e)}")
        return {"error": "Failed to delete candidate"}, 500


@admin_bp.route('/audit', methods=['GET'])
@admin_required
def get_audit_logs() -> Tuple[Dict[str, Any], int]:
    """
    Get audit logs with pagination.

    Query parameters:
        - limit: Number of logs to return (default: 50, max: 100)
        - offset: Number of logs to skip (default: 0)
        - action: Filter by action type (optional)
        - voter_id: Filter by voter ID (optional)

    Returns:
        200: {"audit_logs": [list of audit log objects], "total": total_count, "limit": limit, "offset": offset}
        500: {"error": "error message"}
    """
    try:
        # Get query parameters
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 per request
        offset = max(int(request.args.get('offset', 0)), 0)
        action_filter = request.args.get('action', '').strip().upper()
        voter_id_filter = request.args.get('voter_id', '').strip()

        # Get all audit logs
        all_logs = voting_data_store.get_all_audit_logs()

        # Apply filters
        filtered_logs = all_logs
        if action_filter:
            filtered_logs = [log for log in filtered_logs if log.action == action_filter]
        if voter_id_filter:
            filtered_logs = [log for log in filtered_logs if log.voter_id == voter_id_filter]

        # Sort by timestamp (newest first)
        filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply pagination
        paginated_logs = filtered_logs[offset:offset + limit]

        # Convert to dicts
        logs_data = []
        for log in paginated_logs:
            log_dict = log.to_dict()

            # Add voter email for easier identification
            voter = voting_data_store.get_voter_by_id(log.voter_id)
            if voter:
                log_dict["voter_email"] = voter.email
            else:
                log_dict["voter_email"] = "Unknown"

            logs_data.append(log_dict)

        return {
            "audit_logs": logs_data,
            "total": len(filtered_logs),
            "limit": limit,
            "offset": offset,
            "filters": {
                "action": action_filter if action_filter else None,
                "voter_id": voter_id_filter if voter_id_filter else None
            }
        }, 200

    except ValueError as e:
        return {"error": "Invalid query parameters"}, 400
    except Exception as e:
        print(f"Get audit logs error: {str(e)}")
        return {"error": "Failed to retrieve audit logs"}, 500


@admin_bp.route('/candidates/<candidate_id>', methods=['GET'])
@admin_required
def get_candidate(candidate_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Get a specific candidate by ID.

    Returns:
        200: {"candidate": candidate_object}
        404: {"error": "Candidate not found"}
        500: {"error": "error message"}
    """
    try:
        candidate = voting_data_store.get_candidate_by_id(candidate_id)
        if not candidate:
            return {"error": "Candidate not found"}, 404

        return {"candidate": candidate.to_dict()}, 200

    except Exception as e:
        print(f"Get candidate error: {str(e)}")
        return {"error": "Failed to retrieve candidate"}, 500


@admin_bp.route('/statistics', methods=['GET'])
@admin_required
def get_admin_statistics() -> Tuple[Dict[str, Any], int]:
    """
    Get administrative statistics about the voting system.

    Returns:
        200: {"statistics": {...}}
        500: {"error": "error message"}
    """
    try:
        # Get basic stats from data store
        stats = voting_data_store.get_stats()

        # Add admin-specific stats
        all_voters = voting_data_store.get_all_voters()
        all_candidates = voting_data_store.get_all_candidates()
        all_audit_logs = voting_data_store.get_all_audit_logs()

        # Count votes by position
        votes_by_position = {}
        active_election = voting_data_store.get_active_election()
        if active_election:
            for position in active_election.get_positions_list():
                position_votes = voting_data_store.get_votes_for_position(position)
                votes_by_position[position] = len(position_votes)

        # Count recent activity (last 24 hours)
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        recent_logs = [log for log in all_audit_logs if log.timestamp >= yesterday]

        admin_stats = {
            **stats,  # Include existing stats
            "total_voters": len(all_voters),
            "total_candidates": len(all_candidates),
            "total_audit_logs": len(all_audit_logs),
            "votes_by_position": votes_by_position,
            "recent_activity": {
                "total_actions": len(recent_logs),
                "logins": len([log for log in recent_logs if log.action in ["LOGIN", "VERIFICATION_CODE_USED"]]),
                "votes_cast": len([log for log in recent_logs if log.action == "VOTE_CAST"]),
                "admin_actions": len([log for log in recent_logs if log.action == "ADMIN_ACTION"])
            },
            "candidate_distribution": {}
        }

        # Count candidates per position
        if active_election:
            for position in active_election.get_positions_list():
                position_candidates = voting_data_store.get_candidates_for_position(position)
                admin_stats["candidate_distribution"][position] = len(position_candidates)

        return {"statistics": admin_stats}, 200

    except Exception as e:
        print(f"Get admin statistics error: {str(e)}")
        return {"error": "Failed to retrieve statistics"}, 500


# Export the Blueprint
__all__ = ['admin_bp']