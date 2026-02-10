# ROAM Analysis: python-auth-api

**Feature Count:** 3
**Created:** 2026-02-10T19:20:59Z

## Risks

<!-- AI: Identify 5-10 project risks with severity (High/Medium/Low) -->

1. **JWT Secret Key Management** (High): The JWT secret key must be securely managed via environment variables. If hardcoded or committed to version control, all tokens can be forged, compromising the entire authentication system.

2. **In-Memory Data Loss** (Medium): All user data stored in Python dictionary is lost on process restart or crash. No persistence mechanism exists, requiring users to re-register after every deployment or server restart.

3. **Bcrypt Performance Bottleneck** (Medium): Bcrypt hashing with 12 rounds takes ~100ms per operation. Under concurrent load (registration/login spikes), this could cause request queuing and timeout issues, failing the 100 concurrent request requirement.

4. **Token Expiry Edge Cases** (Medium): Clock skew between token generation and validation, or tokens generated right before expiry threshold, may cause intermittent 401 errors and poor user experience.

5. **Missing Input Validation** (Low): Email format validation relies solely on Pydantic's EmailStr. Malformed emails that pass validation could cause issues. Password validation (min 8 chars) may be insufficient for security requirements.

6. **Concurrent Access Race Conditions** (Low): In-memory dictionary modifications (user registration) are not thread-safe. Concurrent registrations with same email could result in data corruption or duplicate entries bypassing validation.

7. **Refresh Token Abuse** (Medium): 7-day refresh token expiry without revocation mechanism means compromised refresh tokens remain valid indefinitely within that window. No way to force logout or invalidate sessions.

---

## Obstacles

<!-- AI: Current blockers or challenges (technical, resource, dependency) -->

- **No existing Python API structure**: Repository contains React/Vite frontend code. New `api/` directory tree must be created from scratch with proper module structure and `__init__.py` files.

- **Environment configuration setup**: No existing `.env` file or configuration management. Must establish environment variable loading pattern and document required variables (JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS).

- **Testing infrastructure gap**: No Python testing framework (pytest) configured. Need to set up test directory structure, fixtures for user data, and integration test client for FastAPI endpoints.

- **Dependency version conflicts**: FastAPI, PyJWT, and passlib versions must be carefully selected to avoid compatibility issues. Python 3.9+ requirement may conflict with existing system Python version.

---

## Assumptions

<!-- AI: Key assumptions the plan depends on -->

1. **Single-process deployment**: Assumes API runs as single uvicorn process. Multi-process or multi-instance deployment would break in-memory storage without Redis/database migration. *Validation: Document in README as development-only limitation.*

2. **Python 3.9+ availability**: Assumes target environment has Python 3.9 or higher installed. Type hints and dict union syntax (`dict[str, str]`) require 3.9+. *Validation: Add Python version check in main.py startup.*

3. **Email uniqueness as primary key**: Assumes email addresses are unique identifiers and users cannot change emails. No username or user ID system. *Validation: Explicitly document in API documentation and user model.*

4. **No CORS restrictions**: Assumes API will be consumed from same origin or CORS middleware will allow all origins for development. *Validation: Configure CORS in main.py with explicit allowed origins.*

5. **Synchronous operation sufficient**: Assumes bcrypt hashing blocking time acceptable for expected load (100 concurrent requests). No async database calls needed with in-memory storage. *Validation: Load testing with 100 concurrent users to verify sub-100ms token operations.*

---

## Mitigations

<!-- AI: For each risk, propose mitigation strategies -->

**JWT Secret Key Management (High)**
- Action 1: Create `.env.example` template with placeholder JWT_SECRET, add `.env` to `.gitignore`
- Action 2: Add startup validation in `config.py` that fails fast if JWT_SECRET not set or using default/weak value
- Action 3: Document secret key generation command in README: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- Action 4: Add pre-commit hook check to prevent committing files containing JWT_SECRET pattern

**In-Memory Data Loss (Medium)**
- Action 1: Prominently document data persistence limitation in README with "Development Only" warning
- Action 2: Add startup banner log message: "WARNING: Using in-memory storage. All data will be lost on restart."
- Action 3: Implement optional JSON file persistence mode via config flag for local development convenience
- Action 4: Document migration path to Redis or database in README for production use

**Bcrypt Performance Bottleneck (Medium)**
- Action 1: Configure bcrypt rounds via environment variable (default 12) to allow tuning based on hardware
- Action 2: Add performance logging for registration/login endpoints to identify slowdowns
- Action 3: Consider implementing async bcrypt hashing using `asyncio.to_thread()` if FastAPI async endpoints added later
- Action 4: Load test with 100 concurrent requests and document results in performance section

**Token Expiry Edge Cases (Medium)**
- Action 1: Add 30-second clock skew tolerance in JWT decode validation (`leeway=30` parameter)
- Action 2: Return token expiration timestamps in login/refresh responses so clients can proactively refresh
- Action 3: Log token validation failures with timestamps for debugging
- Action 4: Document refresh token flow best practices in API documentation (refresh 5min before expiry)

**Missing Input Validation (Low)**
- Action 1: Add password strength validation: minimum 8 chars, require uppercase, lowercase, digit, special char
- Action 2: Add custom Pydantic validator for email to reject disposable email domains if needed
- Action 3: Add max length constraints to email (254 chars) and password (128 chars) fields
- Action 4: Return detailed validation error messages in 422 responses

**Concurrent Access Race Conditions (Low)**
- Action 1: Add threading.Lock around UserRepository dictionary modifications (add_user method)
- Action 2: Use dict.setdefault() or check-then-set atomic pattern for duplicate detection
- Action 3: Add unit tests with concurrent registration attempts to same email
- Action 4: Document thread-safety considerations in UserRepository docstring

**Refresh Token Abuse (Medium)**
- Action 1: Implement optional refresh token rotation: issue new refresh token on each refresh, invalidate old one
- Action 2: Add token revocation list (in-memory set of blacklisted JTIs) with background cleanup task
- Action 3: Include JTI (JWT ID) claim in refresh tokens for revocation tracking
- Action 4: Document logout endpoint implementation pattern that blacklists refresh token

---

## Appendix: Plan Documents

### PRD
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


### HLD
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


### LLD
# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-10T19:19:36Z
**Status:** Draft

## 1. Implementation Overview

<!-- AI: Brief summary of implementation approach -->

FastAPI-based REST API with in-memory user storage. Project structure follows standard Python package layout with separation of concerns: routes, services, models, and utilities. JWT middleware implemented as FastAPI dependency. Password hashing encapsulated in utility module. All components are synchronous with no async/await complexity.

---

## 2. File Structure

<!-- AI: List all new and modified files with descriptions -->

```
api/
  __init__.py                 # Package initializer
  main.py                     # FastAPI app initialization, CORS, exception handlers
  routes/
    __init__.py
    auth.py                   # Auth endpoints: /register, /login, /refresh
    protected.py              # Protected endpoint: /protected
  services/
    __init__.py
    auth_service.py           # Business logic for registration, login, token refresh
    user_repository.py        # In-memory user storage (dict-based)
  models/
    __init__.py
    user.py                   # User dataclass and Pydantic request/response models
    token.py                  # Token Pydantic models
  utils/
    __init__.py
    jwt_manager.py            # JWT creation, validation, decoding
    password.py               # bcrypt hashing and verification
  middleware/
    __init__.py
    auth_middleware.py        # JWT validation dependency for FastAPI
  config.py                   # Environment variables, JWT secret, token expiry
requirements.txt              # Python dependencies
README.md                     # Setup and usage instructions
```

---

## 3. Detailed Component Designs

<!-- AI: For each major component from HLD, provide detailed design -->

**AuthService** (`services/auth_service.py`):
- `register_user(email, password)`: Validates email format, checks duplicates in UserRepository, hashes password, creates User, returns User object
- `authenticate_user(email, password)`: Retrieves user from repository, verifies password hash, returns User or None
- `generate_tokens(email)`: Creates access and refresh JWTs via JWTManager, returns dict with both tokens

**UserRepository** (`services/user_repository.py`):
- `_users`: Class-level dict mapping email -> User
- `add_user(user)`: Stores user, raises ValueError if duplicate
- `get_user_by_email(email)`: Returns User or None
- `user_exists(email)`: Boolean check

**JWTManager** (`utils/jwt_manager.py`):
- `create_access_token(email)`: Generates JWT with 15min expiry, type="access"
- `create_refresh_token(email)`: Generates JWT with 7day expiry, type="refresh"
- `decode_token(token)`: Validates signature and expiration, returns payload dict or raises JWTError
- `verify_token_type(payload, expected_type)`: Checks token type field

**PasswordHasher** (`utils/password.py`):
- `hash_password(password)`: Returns bcrypt hash string
- `verify_password(plain, hashed)`: Returns boolean

---

## 4. Database Schema Changes

<!-- AI: SQL/migration scripts for schema changes -->

N/A - No database used. In-memory storage only.

---

## 5. API Implementation Details

<!-- AI: For each API endpoint, specify handler logic, validation, error handling -->

**POST /register**:
- Input: Pydantic `RegisterRequest(email: EmailStr, password: str)`
- Validation: Email format via EmailStr, password min 8 chars
- Logic: Call `auth_service.register_user()`, catch ValueError for duplicates
- Response: 201 with `RegisterResponse(message, email)` or 409 with error detail

**POST /login**:
- Input: Pydantic `LoginRequest(email: EmailStr, password: str)`
- Logic: Call `auth_service.authenticate_user()`, if None return 401
- On success: Call `auth_service.generate_tokens()`, return 200 with `TokenResponse`
- Response: 200 with tokens or 401 "Invalid credentials"

**POST /refresh**:
- Input: Pydantic `RefreshRequest(refresh_token: str)`
- Logic: Decode token via JWTManager, verify type="refresh", extract email, generate new access token
- Response: 200 with new access token or 401 "Invalid or expired refresh token"

**GET /protected**:
- Dependency: `Depends(verify_access_token)` extracts email from JWT
- Logic: Return success message with user email
- Response: 200 with `ProtectedResponse(message, user)` or 401 if middleware fails

---

## 6. Function Signatures

<!-- AI: Key function/method signatures with parameters and return types -->

```python
# services/auth_service.py
def register_user(email: str, password: str) -> User
def authenticate_user(email: str, password: str) -> Optional[User]
def generate_tokens(email: str) -> dict[str, str]  # {"access_token": ..., "refresh_token": ...}

# services/user_repository.py
def add_user(user: User) -> None
def get_user_by_email(email: str) -> Optional[User]
def user_exists(email: str) -> bool

# utils/jwt_manager.py
def create_access_token(email: str) -> str
def create_refresh_token(email: str) -> str
def decode_token(token: str) -> dict
def verify_token_type(payload: dict, expected_type: str) -> bool

# utils/password.py
def hash_password(password: str) -> str
def verify_password(plain_password: str, hashed_password: str) -> bool

# middleware/auth_middleware.py
def verify_access_token(authorization: str = Header(...)) -> str  # Returns email
```

---

## 7. State Management

<!-- AI: How application state is managed (Redux, Context, database) -->

In-memory dictionary in `UserRepository._users` (class-level variable). State persists only during process lifetime. No state synchronization needed (single-process). On restart, all user data lost.

---

## 8. Error Handling Strategy

<!-- AI: Error codes, exception handling, user-facing messages -->

**HTTP Status Codes**:
- 201: User created
- 200: Success (login, refresh, protected access)
- 400: Invalid request format (Pydantic validation)
- 401: Unauthorized (invalid credentials, expired/invalid token)
- 409: Conflict (duplicate email)
- 500: Internal server error

**Exception Handlers**:
- `HTTPException` with status_code and detail message
- Global exception handler logs traceback and returns 500
- JWT decode errors caught and re-raised as 401 HTTPException

---

## 9. Test Plan

### Unit Tests
- Password hashing and verification correctness
- JWT creation with correct expiry and payload structure
- JWT decoding and signature validation
- UserRepository add/get/exists operations
- AuthService registration duplicate detection

### Integration Tests
- POST /register with valid data returns 201
- POST /register with duplicate email returns 409
- POST /login with valid credentials returns tokens
- POST /login with invalid credentials returns 401
- POST /refresh with valid refresh token returns new access token
- GET /protected with valid access token returns 200
- GET /protected without token returns 401

### E2E Tests
- Full registration → login → access protected endpoint flow
- Token refresh flow maintaining session continuity
- Expired token rejection on protected endpoint

---

## 10. Migration Strategy

<!-- AI: How to migrate from current state to new implementation -->

New API implementation, no existing state to migrate. Deploy as standalone service. Users must register fresh accounts.

---

## 11. Rollback Plan

<!-- AI: How to rollback if deployment fails -->

Stop uvicorn process. No database rollback needed. No persistent state to clean up.

---

## 12. Performance Considerations

<!-- AI: Performance optimizations, caching, indexing -->

In-memory dict provides O(1) user lookup by email. Bcrypt hashing (12 rounds) adds ~100ms per registration/login. No caching needed for stateless JWT validation. Process can handle 100+ concurrent requests on single core.

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
      slices.yaml
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
vite.config.js
```
