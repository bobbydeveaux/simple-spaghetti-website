"""
Loan-related data models and Pydantic schemas for request/response handling.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


@dataclass
class Loan:
    """
    Data class representing a loan record.
    """
    id: int
    book_id: int
    member_id: int
    borrow_date: str
    return_date: Optional[str] = None
    status: str = "borrowed"  # borrowed, returned


class BorrowRequest(BaseModel):
    """
    Request schema for borrowing a book.
    """
    book_id: int = Field(..., description="ID of the book to borrow", gt=0)
    member_id: int = Field(..., description="ID of the member borrowing the book", gt=0)


class BorrowResponse(BaseModel):
    """
    Response schema for successful book borrowing.
    """
    loan_id: int = Field(..., description="ID of the created loan")
    book_id: int = Field(..., description="ID of the borrowed book")
    member_id: int = Field(..., description="ID of the member who borrowed the book")
    borrow_date: str = Field(..., description="Date when the book was borrowed (YYYY-MM-DD)")
    book_title: str = Field(..., description="Title of the borrowed book")
    member_name: str = Field(..., description="Name of the member who borrowed the book")
    status: str = Field(..., description="Status of the loan")
    message: str = Field(..., description="Success message")


class ReturnRequest(BaseModel):
    """
    Request schema for returning a book.
    """
    loan_id: int = Field(..., description="ID of the loan to return", gt=0)


class ReturnResponse(BaseModel):
    """
    Response schema for successful book return.
    """
    loan_id: int = Field(..., description="ID of the returned loan")
    book_id: int = Field(..., description="ID of the returned book")
    member_id: int = Field(..., description="ID of the member who returned the book")
    borrow_date: str = Field(..., description="Date when the book was borrowed (YYYY-MM-DD)")
    return_date: str = Field(..., description="Date when the book was returned (YYYY-MM-DD)")
    book_title: str = Field(..., description="Title of the returned book")
    member_name: str = Field(..., description="Name of the member who returned the book")
    status: str = Field(..., description="Status of the loan (should be 'returned')")
    message: str = Field(..., description="Success message")


class LoanDetailResponse(BaseModel):
    """
    Response schema for loan details.
    """
    loan_id: int = Field(..., description="ID of the loan")
    book_id: int = Field(..., description="ID of the book")
    member_id: int = Field(..., description="ID of the member")
    borrow_date: str = Field(..., description="Date when the book was borrowed (YYYY-MM-DD)")
    return_date: Optional[str] = Field(None, description="Date when the book was returned (YYYY-MM-DD), null if not returned")
    book_title: str = Field(..., description="Title of the book")
    member_name: str = Field(..., description="Name of the member")
    status: str = Field(..., description="Status of the loan (borrowed or returned)")