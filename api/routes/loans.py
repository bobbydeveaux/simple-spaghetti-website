"""Loan endpoints for borrowing and returning books."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import ValidationError

from api.models.loan import (
    BorrowRequest,
    BorrowResponse,
    ReturnRequest,
    ReturnResponse,
    LoanDetailResponse
)
from api.data_store import (
    LOANS, BOOKS, MEMBERS,
    get_next_loan_id
)
from api.validators import validate_loan, validate_loan_return
from api.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("/borrow", response_model=BorrowResponse, status_code=status.HTTP_201_CREATED)
async def borrow_book(request: BorrowRequest, current_user: str = Depends(get_current_user)):
    """
    Borrow a book by creating a new loan record.

    Args:
        request: BorrowRequest containing book_id and member_id
        current_user: Email of the authenticated user (from JWT token)

    Returns:
        BorrowResponse with loan details and success message

    Raises:
        HTTPException: 400 for validation errors, 404 if book/member not found
    """
    try:
        # Convert request to dictionary for validation
        loan_data = {
            "book_id": request.book_id,
            "member_id": request.member_id
        }

        # Validate loan data
        is_valid, error_msg = validate_loan(loan_data)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Get book and member details for response
        book = BOOKS[request.book_id]
        member = MEMBERS[request.member_id]

        # Create the loan
        loan_id = get_next_loan_id()
        borrow_date = datetime.now().strftime("%Y-%m-%d")

        new_loan = {
            "id": loan_id,
            "book_id": request.book_id,
            "member_id": request.member_id,
            "borrow_date": borrow_date,
            "return_date": None,
            "status": "borrowed"
        }

        # Add loan to data store
        LOANS[loan_id] = new_loan

        # Decrease available copies of the book
        book["available_copies"] -= 1

        return BorrowResponse(
            loan_id=loan_id,
            book_id=request.book_id,
            member_id=request.member_id,
            borrow_date=borrow_date,
            book_title=book["title"],
            member_name=member["name"],
            status="borrowed",
            message=f"Book '{book['title']}' successfully borrowed by {member['name']}"
        )

    except KeyError as e:
        # This shouldn't happen if validation works correctly, but just in case
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource not found: {str(e)}"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/return", response_model=ReturnResponse, status_code=status.HTTP_200_OK)
async def return_book(request: ReturnRequest, current_user: str = Depends(get_current_user)):
    """
    Return a borrowed book by updating the loan record.

    Args:
        request: ReturnRequest containing loan_id
        current_user: Email of the authenticated user (from JWT token)

    Returns:
        ReturnResponse with loan details and success message

    Raises:
        HTTPException: 400 for validation errors, 404 if loan not found
    """
    try:
        # Validate loan return
        is_valid, error_msg = validate_loan_return(request.loan_id)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Get loan, book, and member details
        loan = LOANS[request.loan_id]
        book = BOOKS[loan["book_id"]]
        member = MEMBERS[loan["member_id"]]

        # Update the loan
        return_date = datetime.now().strftime("%Y-%m-%d")
        loan["return_date"] = return_date
        loan["status"] = "returned"

        # Increase available copies of the book
        book["available_copies"] += 1

        return ReturnResponse(
            loan_id=request.loan_id,
            book_id=loan["book_id"],
            member_id=loan["member_id"],
            borrow_date=loan["borrow_date"],
            return_date=return_date,
            book_title=book["title"],
            member_name=member["name"],
            status="returned",
            message=f"Book '{book['title']}' successfully returned by {member['name']}"
        )

    except KeyError as e:
        # This shouldn't happen if validation works correctly, but just in case
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource not found: {str(e)}"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{loan_id}", response_model=LoanDetailResponse, status_code=status.HTTP_200_OK)
async def get_loan_details(loan_id: int, current_user: str = Depends(get_current_user)):
    """
    Get details of a specific loan by ID.

    Args:
        loan_id: ID of the loan to retrieve
        current_user: Email of the authenticated user (from JWT token)

    Returns:
        LoanDetailResponse with full loan details

    Raises:
        HTTPException: 404 if loan not found
    """
    try:
        if loan_id not in LOANS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Loan with ID {loan_id} not found"
            )

        loan = LOANS[loan_id]
        book = BOOKS[loan["book_id"]]
        member = MEMBERS[loan["member_id"]]

        return LoanDetailResponse(
            loan_id=loan["id"],
            book_id=loan["book_id"],
            member_id=loan["member_id"],
            borrow_date=loan["borrow_date"],
            return_date=loan.get("return_date"),
            book_title=book["title"],
            member_name=member["name"],
            status=loan["status"]
        )

    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Related resource not found: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )