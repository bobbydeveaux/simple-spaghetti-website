# ROAM Analysis: library-api

**Feature Count:** 3
**Created:** 2026-02-10T21:16:36Z

## Risks

1. **JWT Secret Key Management** (High): SECRET_KEY must be set via environment variable for JWT signing. If not configured or leaked, authentication system fails or becomes compromised. No key rotation mechanism planned.

2. **In-Memory Data Loss** (Medium): All data stored in global dictionaries disappears on server restart or crash. No persistence layer means complete data loss between deployments or worker restarts with gunicorn.

3. **Gunicorn Multi-Worker Data Inconsistency** (High): LLD states gunicorn workers have separate memory spaces. If deployed with multiple workers, each worker maintains separate BOOKS/LOANS/MEMBERS dictionaries, causing inconsistent state across requests.

4. **No Rate Limiting or Input Sanitization** (Medium): API lacks rate limiting, request size limits, or comprehensive input sanitization. Vulnerable to abuse through repeated requests or malicious payloads in book titles/member names.

5. **Shared State Concurrency Issues** (Low): While single-threaded dev server is safe, Flask can be configured for threading. Global dictionary mutations without locks could cause race conditions if threaded mode enabled.

6. **Password Validation Weakness** (Medium): LLD specifies email/password format validation but doesn't define minimum password complexity requirements. Weak passwords undermine JWT authentication security.

7. **Author CRUD Endpoints Missing** (Medium): Data model includes AUTHORS table with pre-populated data, but no API endpoints exist for creating/updating/deleting authors. Book creation requires author_id but no way to manage authors via API.

---

## Obstacles

- Existing `api/models/` directory contains `token.py` and `user.py` which may conflict with new authentication implementation in `auth.py`
- Repository contains React frontend code (`src/`, `dist/`, Vite config) that is out of scope but may cause confusion about project structure
- No existing test infrastructure or CI/CD pipeline mentioned - unclear if pytest or testing framework is already configured
- SECRET_KEY environment variable configuration not documented in existing README or deployment instructions

---

## Assumptions

1. **Python 3.8+ availability**: Assumes deployment environment has Python 3.8 or higher with pip available. Validation: Check runtime environment Python version during deployment setup.

2. **Single-worker deployment**: Assumes production will run with single gunicorn worker to avoid data inconsistency, or that in-memory data loss is acceptable. Validation: Document deployment configuration constraints in README.

3. **No data persistence required**: Assumes business accepts complete data loss on restart, treating this as pure demo/prototype API. Validation: Confirm with stakeholders that mock data volatility is acceptable.

4. **Development-only usage**: Assumes API is for testing/demo purposes only, not production traffic. Validation: Clarify expected usage volume and environment with stakeholders.

5. **Existing api/models/ code unused**: Assumes existing `token.py` and `user.py` are from previous experiments and won't interfere with new implementation. Validation: Review existing files to confirm they can coexist or be removed.

---

## Mitigations

**For Risk 1 (JWT Secret Key Management):**
- Add SECRET_KEY generation script that creates cryptographically secure random key
- Include SECRET_KEY validation check in app.py startup that fails fast if not configured
- Document SECRET_KEY setup prominently in README with example: `export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')`
- Add warning log message if SECRET_KEY appears to be weak or default value

**For Risk 2 (In-Memory Data Loss):**
- Add prominent documentation in README warning about data volatility
- Include data export/import utility functions to dump dictionaries to JSON files for backup
- Consider adding startup script to pre-populate data from JSON file if it exists
- Document that this is prototype/demo limitation, not production-ready

**For Risk 3 (Gunicorn Multi-Worker Data Inconsistency):**
- Explicitly configure gunicorn with `--workers 1` in deployment documentation
- Add runtime check in app.py that detects multi-worker configuration and logs warning
- Include architecture note in README explaining single-worker constraint
- Suggest Redis or SQLite as future enhancement for multi-worker deployments

**For Risk 4 (No Rate Limiting or Input Sanitization):**
- Add Flask-Limiter dependency for basic rate limiting (e.g., 100 requests/minute per IP)
- Implement max length validation in validators.py for all string fields (title: 200 chars, name: 100 chars)
- Add HTML/script tag detection in string inputs to prevent XSS in potential future UI
- Document API usage guidelines and rate limits in README

**For Risk 5 (Shared State Concurrency Issues):**
- Explicitly disable threading in Flask app config: `app.config['THREADED'] = False`
- Add comments in data_store.py warning about thread-safety assumptions
- Include note in deployment docs to avoid threaded WSGI servers

**For Risk 6 (Password Validation Weakness):**
- Implement password complexity check in validate_member(): minimum 8 characters, require mix of letters and numbers
- Return clear validation error message: "Password must be at least 8 characters with letters and numbers"
- Add password strength recommendations in API documentation

**For Risk 7 (Author CRUD Endpoints Missing):**
- Add GET /authors, POST /authors, PUT /authors/{id}, DELETE /authors/{id} endpoints to app.py
- Update epic.yaml to include author management in Data Store and Authentication feature
- Create validate_author() function in validators.py
- Document author management endpoints in README with examples

---

## Appendix: Plan Documents

### PRD
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


### HLD
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


### LLD
# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-10T21:14:26Z
**Status:** Draft

## 1. Implementation Overview

Flask REST API with single-file application structure. JWT authentication using PyJWT, in-memory dictionaries for data storage, function-based request handlers. Password hashing via werkzeug.security. Development server runs directly with `python app.py`, production deployment uses gunicorn.

---

## 2. File Structure

```
api/
  __init__.py                 # Existing, no changes
  app.py                      # New: Main Flask application
  auth.py                     # New: JWT utilities and decorator
  data_store.py               # New: In-memory mock data
  validators.py               # New: Input validation functions
requirements.txt              # Modified: Add flask, pyjwt
```

---

## 3. Detailed Component Designs

**Flask Application (app.py)**
- Single Flask app instance with all route handlers
- CORS enabled for development
- Error handler decorator for 400/401/404/500
- Routes registered directly on app object

**Authentication Module (auth.py)**
- `generate_token(member_id)`: Creates JWT with 1hr expiration
- `token_required` decorator: Validates JWT from Authorization header
- `verify_password(plain, hashed)`: Compares passwords using werkzeug

**Data Store (data_store.py)**
- Four global dictionaries: BOOKS, AUTHORS, MEMBERS, LOANS
- Auto-increment ID generators for each entity
- Pre-populated with 5 books, 3 authors, 2 members, 1 loan

**Validators (validators.py)**
- `validate_book(data)`: Ensures title, author_id, isbn present
- `validate_member(data)`: Checks name, email, password format
- `validate_loan(data)`: Verifies book_id, member_id exist and book available

---

## 4. Database Schema Changes

N/A - No database. In-memory dictionaries with this structure:

```python
BOOKS = {1: {"id": 1, "title": str, "author_id": int, "isbn": str, "available": bool}}
AUTHORS = {1: {"id": 1, "name": str, "bio": str}}
MEMBERS = {1: {"id": 1, "name": str, "email": str, "password_hash": str, "registration_date": str}}
LOANS = {1: {"id": 1, "book_id": int, "member_id": int, "borrow_date": str, "return_date": str|None, "status": str}}
```

---

## 5. API Implementation Details

**POST /auth/login**
Handler: `login()` - Validates email/password, returns JWT token

**GET /books** (public)
Handler: `list_books()` - Filters by query params `?title=&author=`, returns book list with author name joined

**POST /books** (protected)
Handler: `create_book()` - Validates input, generates ID, adds to BOOKS dict

**GET /books/{id}** (public)
Handler: `get_book(id)` - Returns 404 if not found, else book with author details

**POST /loans** (protected)
Handler: `create_loan()` - Checks book availability, sets available=False, creates loan with borrow_date

**POST /loans/{id}/return** (protected)
Handler: `return_loan(id)` - Sets return_date, status="returned", book available=True

---

## 6. Function Signatures

```python
# auth.py
def generate_token(member_id: int) -> str
def token_required(f: Callable) -> Callable
def verify_password(plain: str, hashed: str) -> bool

# validators.py
def validate_book(data: dict) -> tuple[bool, str|None]
def validate_member(data: dict) -> tuple[bool, str|None]
def validate_loan(data: dict) -> tuple[bool, str|None]

# app.py
@app.route('/auth/login', methods=['POST'])
def login() -> tuple[dict, int]

@app.route('/books', methods=['GET', 'POST'])
@token_required  # Only for POST
def books() -> tuple[dict|list, int]

@app.route('/books/<int:book_id>')
def get_book(book_id: int) -> tuple[dict, int]

@app.route('/loans', methods=['POST'])
@token_required
def create_loan() -> tuple[dict, int]
```

---

## 7. State Management

In-memory global dictionaries in `data_store.py`. No persistence across restarts. Shared state accessed directly by route handlers. No locking needed (single-threaded dev server). For production with gunicorn workers, each worker has separate memory space - data not shared.

---

## 8. Error Handling Strategy

- 400: Validation failures, missing required fields - `{"error": "Missing required field: title"}`
- 401: Invalid/expired JWT, wrong password - `{"error": "Invalid credentials"}`
- 404: Resource not found - `{"error": "Book not found"}`
- 500: Uncaught exceptions - `{"error": "Internal server error"}`

Global error handler catches exceptions, logs to stdout, returns JSON response.

---

## 9. Test Plan

### Unit Tests
- `test_validators.py`: Test validate_book/member/loan with valid/invalid inputs
- `test_auth.py`: Test generate_token, verify_password, token expiration

### Integration Tests
- `test_api.py`: Test all endpoints with pytest and Flask test client
- Test JWT authentication flow: login -> use token -> expired token
- Test book search with title/author filters
- Test loan creation and return flow

### E2E Tests
N/A - API only, no frontend

---

## 10. Migration Strategy

New implementation, no migration. Steps:
1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variable: `export SECRET_KEY=your-secret-key`
3. Run app: `python api/app.py` (dev) or `gunicorn -w 4 api.app:app` (prod)
4. Test with curl/Postman

---

## 11. Rollback Plan

No existing API to rollback to. If deployment fails: stop process, fix errors, restart. In-memory data lost on restart (acceptable per PRD). For critical failures, revert code to previous commit and redeploy.

---

## 12. Performance Considerations

All operations O(n) or better with small mock data (n<100). Search iterates BOOKS dict - acceptable for 100 books. No caching needed. No database queries. Response times <50ms. For scaling beyond mock data, replace dicts with database queries and add Redis caching.

---

## Appendix: Existing Repository Structure

## Repository File Structure

```
.claude-output.json
.claude-plan.json
.claude-resolution.json
.conflict-info.json
.eslintrc.cjs
.git
.pr-number
README.md
api/
  __init__.py
  models/
    __init__.py
    token.py
    user.py
dist/
  assets/
    index-DpoD3wlk.css
    index-uUlMrwkr.js
  index.html
docs/
  concepts/
    cool-penguin-page/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    happy-llama-page/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    library-api/
      HLD.md
      PRD.md
    pasta-recipes-react/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    pigeon-website/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    python-auth-api/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
  plans/
    simple-spaghetti-website/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    test-pizza-page/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
index.html
package-lock.json
package.json
postcss.config.js
requirements.txt
src/
  App.css
  App.jsx
  components/
    FilterPanel.jsx
    Navigation.jsx
    RecipeCard.jsx
    RecipeDetail.jsx
    RecipeList.jsx
    SearchBar.jsx
  context/
    RecipeContext.jsx
  data/
    recipes.json
  index.css
  main.jsx
  utils/
    filterHelpers.js
tailwind.config.js
test_models.py
vite.config.js
```
