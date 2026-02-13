"""
Base Pydantic schemas for F1 Analytics API.

This module provides base schemas and common validation patterns.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, validator


class TimestampMixin(BaseModel):
    """Base mixin for models with timestamps."""

    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Record last update timestamp")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda dt: dt.isoformat() + 'Z' if dt else None,
            date: lambda d: d.isoformat() if d else None,
            Decimal: lambda d: float(d) if d is not None else None,
        }
    )


class PaginationParams(BaseModel):
    """Standard pagination parameters."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page")

    @property
    def offset(self) -> int:
        """Calculate database offset."""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseSchema):
    """Standard paginated response."""

    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there's a next page")
    has_prev: bool = Field(..., description="Whether there's a previous page")


class ErrorDetail(BaseModel):
    """Error detail structure."""

    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[list[ErrorDetail]] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda dt: dt.isoformat() + 'Z'
        }
    )


class SuccessResponse(BaseSchema):
    """Standard success response."""

    success: bool = Field(True, description="Operation success flag")
    message: str = Field(..., description="Success message")
    data: Optional[dict] = Field(None, description="Response data")