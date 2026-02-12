# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-10T21:13:35Z
**Status:** Draft

## 1. Architecture Overview

Single-tier monolithic Flask REST API application. All endpoints, business logic, and mock data storage reside in a single Python process. No external services or databases required.

---

## 2. System Components

- **Flask Web Server**: Handles HTTP requests/responses, routing, and middleware
- **Authentication Module**: JWT token generation and validation
- **Mock Data Store**: In-memory Python dictionaries for books, authors, members, loans
- **Business Logic Layer**: Validation, search, loan management, CRUD operations
- **Error Handler**: Centralized exception handling and HTTP error responses

---

## 3. Data Model

**Book**: id, title, author_id, isbn, available (bool)
**Author**: id, name, bio
**Member**: id, name, email, password_hash, registration_date
**Loan**: id, book_id, member_id, borrow_date, return_date (nullable), status

Relationships: Book -> Author (many-to-one), Loan -> Book/Member (many-to-one)

---

## 4. API Contracts

**Public Endpoints:**
- POST /auth/login (email, password) → {token, expires_at}
- POST /members (name, email, password) → {id, name, email}
- GET /books?title=&author= → [{id, title, author, available}]
- GET /books/{id} → {id, title, author, isbn, available}

**Protected Endpoints (JWT required):**
- POST /books (title, author_id, isbn) → {id, title}
- PUT /books/{id} (title, author_id, isbn) → {id, title}
- DELETE /books/{id} → 204
- POST /loans (book_id, member_id) → {loan_id, borrow_date}
- POST /loans/{id}/return → {loan_id, return_date}
- GET /members → [{id, name, email}]

---

## 5. Technology Stack

### Backend
- Python 3.8+
- Flask (web framework)
- PyJWT (JWT token handling)
- Werkzeug (password hashing)

### Frontend
N/A (API only)

### Infrastructure
Local Python runtime (development), gunicorn for production serving

### Data Storage
In-memory Python dictionaries and lists (mock data, no persistence)

---

## 6. Integration Points

None. Self-contained API with no external dependencies or third-party integrations.

---

## 7. Security Architecture

- JWT tokens signed with HS256 algorithm, 1-hour expiration
- Secret key loaded from environment variable
- Passwords hashed using werkzeug.security (pbkdf2:sha256)
- Protected endpoints validate JWT signature and expiration via decorator
- No role-based access control (all authenticated users have full access)

---

## 8. Deployment Architecture

Single Flask application process. Development: Flask dev server. Production: gunicorn with 4 workers behind reverse proxy (nginx). Containerization optional (Docker). No orchestration needed.

---

## 9. Scalability Strategy

Not applicable for mock data implementation. In-memory data limits scalability to single process. For future scaling: replace mock store with real database, use Redis for session management, deploy multiple instances behind load balancer.

---

## 10. Monitoring & Observability

- Flask built-in logging to stdout (INFO level)
- HTTP access logs via gunicorn
- Custom error logging for validation failures and exceptions
- No APM or distributed tracing (not needed for simple API)

---

## 11. Architectural Decisions (ADRs)

**ADR-001: Mock Data Over Database**
Use in-memory Python structures instead of database to meet PRD non-goal of no real database integration. Simplifies development and deployment.

**ADR-002: JWT Over Session-Based Auth**
JWT stateless authentication avoids need for session storage. Tokens are self-contained and easily validated.

**ADR-003: Monolithic Over Microservices**
Single Flask app sufficient for 4 entities and 12 endpoints. Microservices add unnecessary complexity for this scope.

---

## Appendix: PRD Reference

# Product Requirements Document: Python Flask API for a library system. Include:
- REST/CRUD endpoints for books, authors, members, and loans
- JWT authentication for protected endpoints
- Mock database with static data (no real database needed)
- Endpoints: list books, get book by ID, create/update/delete books
- Endpoints: list members, register member, borrow book, return book
- Search functionality for books by title/author
- Proper error handling and validation


**Created:** 2026-02-10T21:12:58Z
**Status:** Draft

## 1. Overview

**Concept:** Python Flask API for a library system. Include:
- REST/CRUD endpoints for books, authors, members, and loans
- JWT authentication for protected endpoints
- Mock database with static data (no real database needed)
- Endpoints: list books, get book by ID, create/update/delete books
- Endpoints: list members, register member, borrow book, return book
- Search functionality for books by title/author
- Proper error handling and validation


**Description:** Python Flask API for a library system. Include:
- REST/CRUD endpoints for books, authors, members, and loans
- JWT authentication for protected endpoints
- Mock database with static data (no real database needed)
- Endpoints: list books, get book by ID, create/update/delete books
- Endpoints: list members, register member, borrow book, return book
- Search functionality for books by title/author
- Proper error handling and validation


---

## 2. Goals

- Build REST API with full CRUD operations for books, authors, members, and loans
- Implement JWT-based authentication for endpoint protection
- Provide search capability for books by title and author
- Ensure proper validation and error handling across all endpoints

---

## 3. Non-Goals

- Real database integration (use mock data only)
- Frontend UI or web interface
- Advanced features like reservations, late fees, or notifications
- User roles beyond basic authentication
- Production deployment or hosting infrastructure

---

## 4. User Stories

- As a library staff member, I want to list all books so that I can see available inventory
- As a library staff member, I want to create/update/delete books so that I can manage the collection
- As a library patron, I want to search books by title or author so that I can find specific books
- As a library patron, I want to register as a member so that I can borrow books
- As a library patron, I want to borrow and return books so that I can read them
- As an API consumer, I want JWT authentication so that only authorized users can modify data

---

## 5. Acceptance Criteria

**Book Management:**
- Given valid credentials, when I GET /books, then I receive a list of all books
- Given valid book data, when I POST /books, then a new book is created
- Given a book ID, when I GET /books/{id}, then I receive that book's details

**Member & Loan Management:**
- Given member details, when I POST /members, then a new member is registered
- Given a member borrows a book, when I POST /loans, then the loan is recorded
- Given a loan exists, when I POST /loans/{id}/return, then the book is marked returned

---

## 6. Functional Requirements

- FR-001: API must provide GET /books, POST /books, GET /books/{id}, PUT /books/{id}, DELETE /books/{id}
- FR-002: API must provide GET /members, POST /members
- FR-003: API must provide POST /loans (borrow), POST /loans/{id}/return
- FR-004: API must support query parameters for book search (title, author)
- FR-005: API must validate all input data and return appropriate error messages
- FR-006: API must implement JWT token generation and validation
- FR-007: Protected endpoints must require valid JWT token in Authorization header

---

## 7. Non-Functional Requirements

### Performance
- API should respond within 200ms for all endpoints with mock data

### Security
- JWT tokens must expire after 1 hour
- Passwords must be hashed before storage
- Protected endpoints must validate JWT signature and expiration

### Scalability
- Mock data structure should support up to 100 books, 50 members, 200 loans

### Reliability
- API must return proper HTTP status codes (200, 201, 400, 401, 404, 500)
- All errors must include descriptive JSON error messages

---

## 8. Dependencies

- Python 3.8+
- Flask web framework
- PyJWT for JWT token handling
- Flask-CORS for cross-origin support (optional)

---

## 9. Out of Scope

- Database integration (SQLite, PostgreSQL, MongoDB)
- Admin dashboard or UI
- Email notifications
- Advanced search filters (genre, ISBN, publication year)
- Rate limiting or API throttling
- Automated testing suite

---

## 10. Success Metrics

- All 7 functional requirements implemented and testable via Postman/curl
- JWT authentication working for protected endpoints
- Search returns correct results for title and author queries
- All endpoints return proper error messages for invalid input

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers
