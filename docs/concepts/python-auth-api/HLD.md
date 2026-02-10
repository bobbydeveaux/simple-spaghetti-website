# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-10T18:51:16Z
**Status:** Draft

## 1. Architecture Overview

Single-process monolithic REST API built with FastAPI. All components run in one Python application with in-memory data storage. Stateless design with JWT tokens carrying user identity.

---

## 2. System Components

- **Authentication Service**: Handles registration, login, token generation/validation
- **User Storage**: In-memory dictionary storing user credentials (email -> hashed password)
- **Token Manager**: JWT creation, signing, verification, and refresh logic
- **Protected Resource Handler**: Example endpoint demonstrating token validation
- **Request Validators**: Input validation middleware for email/password format

---

## 3. Data Model

**User (in-memory)**
- email: string (unique identifier)
- password_hash: string (bcrypt hashed)

**JWT Payload**
- sub: string (user email)
- exp: integer (expiration timestamp)
- type: string ("access" or "refresh")

---

## 4. API Contracts

**POST /api/v1/auth/register**
Request: `{"email": "user@example.com", "password": "securepass"}`
Response: `{"message": "User registered", "email": "user@example.com"}`

**POST /api/v1/auth/login**
Request: `{"email": "user@example.com", "password": "securepass"}`
Response: `{"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}`

**POST /api/v1/auth/refresh**
Request: `{"refresh_token": "eyJ..."}`
Response: `{"access_token": "eyJ...", "token_type": "bearer"}`

**GET /api/v1/protected/profile**
Headers: `Authorization: Bearer eyJ...`
Response: `{"email": "user@example.com", "message": "This is protected data"}`

---

## 5. Technology Stack

### Backend
- FastAPI (web framework)
- PyJWT (token generation/validation)
- passlib with bcrypt (password hashing)
- Pydantic (request/response validation)
- uvicorn (ASGI server)

### Frontend
N/A - API only

### Infrastructure
- Python 3.10+
- Virtual environment (venv)
- pip for dependency management

### Data Storage
In-memory Python dictionary (no persistence)

---

## 6. Integration Points

None - standalone API with no external dependencies or integrations

---

## 7. Security Architecture

- Passwords hashed with bcrypt (cost factor 12)
- JWT tokens signed with HS256 and secret key from environment variable
- Access tokens expire in 15 minutes, refresh tokens in 7 days
- Bearer token authentication via Authorization header
- Input validation on all endpoints (email format, password length)
- CORS middleware configured for allowed origins

---

## 8. Deployment Architecture

Single Python process deployed as container or systemd service. Environment variables for JWT_SECRET_KEY and CORS origins. Runs behind reverse proxy (nginx) for TLS termination.

---

## 9. Scalability Strategy

Stateless design allows horizontal scaling with load balancer. In-memory storage limits to single instance for this implementation. For production, migrate to Redis or database with session sharing.

---

## 10. Monitoring & Observability

- FastAPI automatic OpenAPI/Swagger documentation at /docs
- Structured logging (JSON) with request/response details
- Health check endpoint at /health
- Metrics: response times, auth success/failure rates, token expiration events

---

## 11. Architectural Decisions (ADRs)

**ADR-001: FastAPI over Flask**
Rationale: Built-in async support, automatic request validation with Pydantic, OpenAPI generation

**ADR-002: In-memory storage**
Rationale: PRD explicitly requires no database, simplifies deployment, sufficient for demo/testing

**ADR-003: HS256 for JWT signing**
Rationale: Symmetric algorithm suitable for single-service architecture, simpler key management

**ADR-004: Separate access and refresh tokens**
Rationale: Short-lived access tokens limit exposure, refresh tokens enable session extension

---

## Appendix: PRD Reference

# Product Requirements Document: Medium sized Python API that handles user authentication and JWT tokens. Mock the data so no database is needed. Include user registration, login, token refresh, and protected endpoints.

**Created:** 2026-02-10T18:50:46Z
**Status:** Draft

## 1. Overview

**Concept:** Medium sized Python API that handles user authentication and JWT tokens. Mock the data so no database is needed. Include user registration, login, token refresh, and protected endpoints.

**Description:** Medium sized Python API that handles user authentication and JWT tokens. Mock the data so no database is needed. Include user registration, login, token refresh, and protected endpoints.

---

## 2. Goals

- Provide secure JWT-based authentication for API users
- Enable user registration and login with password hashing
- Support token refresh mechanism for extended sessions
- Implement protected endpoints that validate JWT tokens

---

## 3. Non-Goals

- Database integration or persistence layer
- OAuth or third-party authentication providers
- Email verification or password reset flows
- Role-based access control beyond basic authentication

---

## 4. User Stories

- As a new user, I want to register with email and password so that I can access the API
- As a registered user, I want to login with credentials so that I receive a JWT token
- As an authenticated user, I want to refresh my token so that I maintain access without re-logging in
- As an authenticated user, I want to access protected endpoints so that I can retrieve secure data
- As a user, I want my password securely hashed so that my credentials are protected

---

## 5. Acceptance Criteria

- Given valid email and password, when registering, then user is created and confirmation returned
- Given valid credentials, when logging in, then JWT access and refresh tokens are returned
- Given valid refresh token, when requesting refresh, then new access token is issued
- Given valid access token, when accessing protected endpoint, then resource is returned
- Given invalid/expired token, when accessing protected endpoint, then 401 error is returned

---

## 6. Functional Requirements

- FR-001: API accepts POST /register with email and password, validates input, hashes password
- FR-002: API accepts POST /login with credentials, validates, returns access and refresh tokens
- FR-003: API accepts POST /refresh with refresh token, validates, returns new access token
- FR-004: API provides GET /protected endpoint requiring valid JWT in Authorization header
- FR-005: API validates JWT signature, expiration, and returns appropriate error codes

---

## 7. Non-Functional Requirements

### Performance
- Token generation completes within 100ms
- Protected endpoint response time under 50ms

### Security
- Passwords hashed using bcrypt with salt
- JWT tokens signed with HS256 algorithm
- Access tokens expire after 15 minutes, refresh tokens after 7 days

### Scalability
- In-memory data structure supports up to 1000 mock users

### Reliability
- API returns appropriate HTTP status codes for all error conditions
- Token validation handles malformed tokens gracefully

---

## 8. Dependencies

- Python 3.8+
- PyJWT library for token generation and validation
- bcrypt or passlib for password hashing
- FastAPI or Flask framework for REST API

---

## 9. Out of Scope

- Database or file-based persistence
- Email notifications or verification
- Password reset functionality
- Multi-factor authentication
- API rate limiting or throttling

---

## 10. Success Metrics

- All authentication endpoints return correct status codes
- JWT tokens properly encode user identity and expiration
- Protected endpoints reject invalid/expired tokens
- Password hashing prevents plaintext storage

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers
