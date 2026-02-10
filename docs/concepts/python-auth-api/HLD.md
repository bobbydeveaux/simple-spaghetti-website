# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-10T19:18:49Z
**Status:** Draft

## 1. Architecture Overview

<!-- AI: Describe the overall system architecture (microservices, monolith, serverless, etc.) -->

Single-process monolithic REST API built with FastAPI. Synchronous request-response model with in-memory user storage. No external dependencies beyond Python libraries. Suitable for development, testing, and educational purposes.

---

## 2. System Components

<!-- AI: List major components/services with brief descriptions -->

- **API Layer**: FastAPI application exposing REST endpoints for auth operations
- **Auth Service**: Handles registration, login, token generation and validation logic
- **User Repository**: In-memory dictionary storing user data (email → user object mapping)
- **JWT Manager**: Encapsulates token creation, signing, verification, and expiration logic
- **Password Hasher**: Wrapper for bcrypt hashing and verification operations

---

## 3. Data Model

<!-- AI: High-level data entities and relationships -->

**User Entity** (in-memory dict):
- email: str (unique, primary key)
- password_hash: str (bcrypt hashed)
- created_at: datetime

**JWT Payload**:
- sub: email (subject)
- exp: expiration timestamp
- iat: issued at timestamp
- type: "access" | "refresh"

---

## 4. API Contracts

<!-- AI: Define key API endpoints, request/response formats -->

**POST /register**
Request: `{"email": "user@example.com", "password": "SecurePass123"}`
Response 201: `{"message": "User registered", "email": "user@example.com"}`
Response 409: `{"detail": "Email already registered"}`

**POST /login**
Request: `{"email": "user@example.com", "password": "SecurePass123"}`
Response 200: `{"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}`
Response 401: `{"detail": "Invalid credentials"}`

**POST /refresh**
Request: `{"refresh_token": "eyJ..."}`
Response 200: `{"access_token": "eyJ...", "token_type": "bearer"}`
Response 401: `{"detail": "Invalid or expired refresh token"}`

**GET /protected**
Headers: `Authorization: Bearer eyJ...`
Response 200: `{"message": "Access granted", "user": "user@example.com"}`
Response 401: `{"detail": "Invalid or missing token"}`

---

## 5. Technology Stack

### Backend
- Python 3.9+
- FastAPI (web framework)
- PyJWT (JWT token handling)
- passlib[bcrypt] (password hashing)
- pydantic (request/response validation)
- uvicorn (ASGI server)

### Frontend
N/A - API only

### Infrastructure
- Local development: uvicorn server
- No containerization required

### Data Storage
- In-memory Python dictionary (no persistence)

---

## 6. Integration Points

<!-- AI: External systems, APIs, webhooks -->

None. Self-contained API with no external dependencies or third-party integrations.

---

## 7. Security Architecture

<!-- AI: Authentication, authorization, encryption, secrets management -->

- Passwords hashed with bcrypt (12 rounds minimum)
- JWT tokens signed using HS256 algorithm with environment-variable secret key
- Access tokens expire in 15 minutes, refresh tokens in 7 days
- Authorization via Bearer token in HTTP Authorization header
- JWT middleware validates signature, expiration, and token type on protected routes
- No sensitive data in JWT payload (only email as subject)

---

## 8. Deployment Architecture

<!-- AI: How components are deployed (K8s, containers, serverless) -->

Single-process deployment via `uvicorn main:app --host 0.0.0.0 --port 8000`. No orchestration needed. Suitable for local development or simple hosting environments.

---

## 9. Scalability Strategy

<!-- AI: How the system scales (horizontal, vertical, auto-scaling) -->

Not designed for production scale. In-memory storage limits to ~1000 users. For scaling, would need to replace user repository with Redis or database and add session persistence.

---

## 10. Monitoring & Observability

<!-- AI: Logging, metrics, tracing, alerting strategy -->

- Python logging module for request/response and error logging
- FastAPI automatic OpenAPI documentation at /docs
- Basic exception handlers for 401, 409, 422, 500 errors
- No distributed tracing or metrics collection (not needed for simple API)

---

## 11. Architectural Decisions (ADRs)

<!-- AI: Key architectural decisions with rationale -->

**ADR-001: Use FastAPI over Flask**
FastAPI provides automatic OpenAPI docs, built-in pydantic validation, and better async support for future extensibility.

**ADR-002: In-memory storage**
Per requirements, no database needed. Python dict provides O(1) lookup and sufficient capacity for testing/development.

**ADR-003: HS256 JWT signing**
Symmetric signing sufficient for single-service architecture. Simpler than RS256 and meets security requirements.

**ADR-004: 15-minute access token expiry**
Balances security (short-lived tokens) with UX (refresh mechanism prevents frequent re-login).

---

## Appendix: PRD Reference

# Product Requirements Document: Medium sized Python API that handles user authentication and JWT tokens. Mock the data so no database is needed. Include user registration, login, token refresh, and protected endpoints.

**Created:** 2026-02-10T19:18:16Z
**Status:** Draft

## 1. Overview

**Concept:** Medium sized Python API that handles user authentication and JWT tokens. Mock the data so no database is needed. Include user registration, login, token refresh, and protected endpoints.

**Description:** Medium sized Python API that handles user authentication and JWT tokens. Mock the data so no database is needed. Include user registration, login, token refresh, and protected endpoints.

---

## 2. Goals

- Provide secure user registration and login functionality with JWT-based authentication
- Implement token refresh mechanism to maintain user sessions without re-authentication
- Create protected endpoints that validate JWT tokens before granting access
- Use in-memory data storage for users to avoid database dependencies

---

## 3. Non-Goals

- Persistent database integration or data persistence across server restarts
- OAuth2 or third-party authentication providers (Google, GitHub, etc.)
- Password reset or email verification workflows
- User profile management beyond basic registration

---

## 4. User Stories

- As a new user, I want to register with email and password so that I can access the API
- As a registered user, I want to login with credentials so that I receive a JWT access token
- As an authenticated user, I want to refresh my token so that I can maintain my session without re-login
- As an API consumer, I want to access protected endpoints so that I can retrieve secure data
- As a user, I want my password hashed so that my credentials are stored securely

---

## 5. Acceptance Criteria

**Registration:**
- Given valid email and password, when POST /register, then user created and success response returned
- Given duplicate email, when POST /register, then 409 Conflict error returned

**Login:**
- Given valid credentials, when POST /login, then access and refresh tokens returned
- Given invalid credentials, when POST /login, then 401 Unauthorized returned

**Token Refresh:**
- Given valid refresh token, when POST /refresh, then new access token returned

**Protected Endpoints:**
- Given valid JWT, when GET /protected, then data returned
- Given invalid/missing JWT, when GET /protected, then 401 Unauthorized returned

---

## 6. Functional Requirements

- FR-001: API accepts POST /register with email and password, validates format, hashes password, stores user in-memory
- FR-002: API accepts POST /login, validates credentials, returns JWT access token (15min expiry) and refresh token (7day expiry)
- FR-003: API accepts POST /refresh with refresh token, validates it, returns new access token
- FR-004: API provides GET /protected endpoint that requires valid JWT in Authorization header
- FR-005: API validates JWT signature, expiration, and structure on all protected endpoints

---

## 7. Non-Functional Requirements

### Performance
- Token generation and validation complete within 100ms
- API handles 100 concurrent requests without degradation

### Security
- Passwords hashed using bcrypt with minimum 12 rounds
- JWT signed with HS256 algorithm and secret key
- Access tokens expire after 15 minutes, refresh tokens after 7 days
- No sensitive data in JWT payload

### Scalability
- In-memory storage suitable for development/testing with up to 1000 users

### Reliability
- API returns appropriate HTTP status codes and error messages
- Token validation failures logged for monitoring

---

## 8. Dependencies

- Python 3.9+
- FastAPI or Flask web framework
- PyJWT library for JWT encoding/decoding
- bcrypt or passlib for password hashing
- pydantic for request/response validation

---

## 9. Out of Scope

- Database integration (PostgreSQL, MongoDB, etc.)
- Email verification or password reset flows
- Rate limiting or throttling mechanisms
- Admin dashboard or user management UI
- Docker containerization or deployment configuration

---

## 10. Success Metrics

- All API endpoints return correct status codes per acceptance criteria
- JWT tokens successfully authenticate users on protected endpoints
- Password hashing prevents plaintext storage
- Token refresh extends session without requiring re-login
- API passes integration tests covering registration, login, refresh, and protected access flows

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers
