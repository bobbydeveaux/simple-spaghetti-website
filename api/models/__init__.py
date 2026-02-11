"""
Data models and schemas for the authentication API
"""

from .user import User, RegisterRequest, RegisterResponse, LoginRequest
from .token import TokenResponse, RefreshRequest, ProtectedResponse
from .loan import (
    Loan,
    BorrowRequest,
    BorrowResponse,
    ReturnRequest,
    ReturnResponse,
    LoanDetailResponse
)

__all__ = [
    "User",
    "RegisterRequest",
    "RegisterResponse",
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "ProtectedResponse",
    "Loan",
    "BorrowRequest",
    "BorrowResponse",
    "ReturnRequest",
    "ReturnResponse",
    "LoanDetailResponse"
]