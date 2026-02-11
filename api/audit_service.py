"""
Audit logging service for tracking all user actions in the library management system.
Provides comprehensive logging of CRUD operations, authentication events, and admin actions.
"""

from datetime import datetime
from flask import request
from typing import Dict, Any, Optional, List
from api.data_store import AUDIT_LOGS, get_next_audit_log_id

class AuditService:
    """Service for logging user actions and system events"""

    @staticmethod
    def log_action(
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        action: str = "",
        resource_type: str = "",
        resource_id: Optional[int] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        status: str = "success",
        details: str = "",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        Log a user action or system event to the audit trail.

        Args:
            user_id: ID of the user performing the action
            user_email: Email of the user performing the action
            action: Type of action (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, BORROW, RETURN, etc.)
            resource_type: Type of resource affected (book, member, loan, author, etc.)
            resource_id: ID of the affected resource
            old_value: Previous state of the resource (for updates/deletes)
            new_value: New state of the resource (for creates/updates)
            status: success or failed
            details: Additional context or error messages
            ip_address: IP address of the user (optional)
            user_agent: User agent string (optional)

        Returns:
            Audit log ID
        """
        # Auto-extract request info if available
        if hasattr(request, 'environ'):
            if ip_address is None:
                ip_address = request.environ.get('REMOTE_ADDR', 'unknown')
            if user_agent is None:
                user_agent = request.headers.get('User-Agent', 'unknown')

        # Auto-extract user info from request context if available
        if user_id is None and hasattr(request, 'current_member_id'):
            user_id = request.current_member_id
        if user_email is None and hasattr(request, 'current_member_email'):
            user_email = request.current_member_email

        # Create audit log entry
        audit_id = get_next_audit_log_id()
        audit_log = {
            "id": audit_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id,
            "user_email": user_email or "unknown",
            "action": action.upper(),
            "resource_type": resource_type.lower(),
            "resource_id": resource_id,
            "old_value": old_value,
            "new_value": new_value,
            "status": status.lower(),
            "ip_address": ip_address or "unknown",
            "user_agent": user_agent or "unknown",
            "details": details
        }

        # Store the audit log
        AUDIT_LOGS[audit_id] = audit_log

        return audit_id

    @staticmethod
    def log_authentication(user_email: str, action: str, status: str, details: str = "") -> int:
        """
        Log authentication events (login, logout, failed login).

        Args:
            user_email: Email of the user
            action: LOGIN or LOGOUT
            status: success or failed
            details: Additional details (e.g., failure reason)

        Returns:
            Audit log ID
        """
        from api.data_store import MEMBERS

        # Try to find user ID by email
        user_id = None
        for member_id, member in MEMBERS.items():
            if member["email"].lower() == user_email.lower():
                user_id = member_id
                break

        return AuditService.log_action(
            user_id=user_id,
            user_email=user_email,
            action=action,
            resource_type="authentication",
            status=status,
            details=details
        )

    @staticmethod
    def log_book_action(action: str, book_id: int, old_book: Optional[Dict] = None, new_book: Optional[Dict] = None, status: str = "success") -> int:
        """
        Log book-related actions (create, update, delete).

        Args:
            action: CREATE, UPDATE, or DELETE
            book_id: ID of the book
            old_book: Previous book state (for updates/deletes)
            new_book: New book state (for creates/updates)
            status: success or failed

        Returns:
            Audit log ID
        """
        return AuditService.log_action(
            action=action,
            resource_type="book",
            resource_id=book_id,
            old_value=old_book,
            new_value=new_book,
            status=status
        )

    @staticmethod
    def log_member_action(action: str, member_id: int, old_member: Optional[Dict] = None, new_member: Optional[Dict] = None, status: str = "success") -> int:
        """
        Log member-related actions (create, update, delete, promote, suspend).

        Args:
            action: CREATE, UPDATE, DELETE, PROMOTE, SUSPEND, etc.
            member_id: ID of the member
            old_member: Previous member state (for updates/deletes)
            new_member: New member state (for creates/updates)
            status: success or failed

        Returns:
            Audit log ID
        """
        # Filter out password_hash from logged data for security
        safe_old_member = None
        safe_new_member = None

        if old_member:
            safe_old_member = {k: v for k, v in old_member.items() if k != 'password_hash'}

        if new_member:
            safe_new_member = {k: v for k, v in new_member.items() if k != 'password_hash'}

        return AuditService.log_action(
            action=action,
            resource_type="member",
            resource_id=member_id,
            old_value=safe_old_member,
            new_value=safe_new_member,
            status=status
        )

    @staticmethod
    def log_loan_action(action: str, loan_id: int, old_loan: Optional[Dict] = None, new_loan: Optional[Dict] = None, status: str = "success") -> int:
        """
        Log loan-related actions (borrow, return).

        Args:
            action: BORROW or RETURN
            loan_id: ID of the loan
            old_loan: Previous loan state (for returns)
            new_loan: New loan state (for creates/returns)
            status: success or failed

        Returns:
            Audit log ID
        """
        return AuditService.log_action(
            action=action,
            resource_type="loan",
            resource_id=loan_id,
            old_value=old_loan,
            new_value=new_loan,
            status=status
        )

    @staticmethod
    def get_audit_logs(
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with filtering options.

        Args:
            limit: Maximum number of logs to return
            offset: Number of logs to skip
            user_id: Filter by user ID
            action: Filter by action type
            resource_type: Filter by resource type
            status: Filter by status (success/failed)
            start_date: Filter by start date (YYYY-MM-DD)
            end_date: Filter by end date (YYYY-MM-DD)

        Returns:
            List of audit log entries
        """
        logs = []

        for log in AUDIT_LOGS.values():
            # Apply filters
            if user_id is not None and log["user_id"] != user_id:
                continue
            if action and log["action"] != action.upper():
                continue
            if resource_type and log["resource_type"] != resource_type.lower():
                continue
            if status and log["status"] != status.lower():
                continue
            if start_date and log["timestamp"][:10] < start_date:
                continue
            if end_date and log["timestamp"][:10] > end_date:
                continue

            logs.append(log)

        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x["timestamp"], reverse=True)

        # Apply pagination
        return logs[offset:offset + limit]

    @staticmethod
    def get_audit_log_stats() -> Dict[str, Any]:
        """
        Get statistics about audit logs for admin dashboard.

        Returns:
            Dictionary with audit log statistics
        """
        total_logs = len(AUDIT_LOGS)

        # Count by action type
        action_counts = {}
        status_counts = {"success": 0, "failed": 0}
        user_activity = {}

        for log in AUDIT_LOGS.values():
            # Count actions
            action = log["action"]
            action_counts[action] = action_counts.get(action, 0) + 1

            # Count status
            status = log["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

            # Count user activity
            user_email = log["user_email"]
            if user_email != "unknown":
                user_activity[user_email] = user_activity.get(user_email, 0) + 1

        # Get recent activity (last 10 logs)
        recent_logs = AuditService.get_audit_logs(limit=10)

        return {
            "total_logs": total_logs,
            "action_counts": action_counts,
            "status_counts": status_counts,
            "user_activity": user_activity,
            "recent_activity": recent_logs
        }