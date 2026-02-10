# ROAM Analysis: python-auth-api

**Feature Count:** 3
**Created:** 2026-02-10T18:53:37Z

## Risks

1. **JWT Secret Key Management** (High): The JWT_SECRET_KEY must be stored securely in environment variables. Hardcoded secrets or weak keys could allow token forgery and complete authentication bypass. If the secret is compromised, all issued tokens become invalid and attackers can generate valid tokens for any user.

2. **In-Memory Data Loss** (Medium): All user data is stored in memory without persistence. Server restarts, crashes, or deployments will wipe all registered users and force re-registration. This limits production viability and creates poor user experience during development iterations.

3. **Bcrypt Performance Bottleneck** (Medium): Bcrypt cost factor 12 is intentionally slow for security, but may cause registration/login endpoints to exceed 100ms performance target under concurrent load. High traffic could degrade response times and violate NFR specifications.

4. **Token Refresh Security Gap** (Medium): Refresh tokens with 7-day expiration lack revocation mechanism. Compromised refresh tokens remain valid until expiration, allowing attackers extended access even after user changes password or detects breach.

5. **CORS Misconfiguration** (Low): Improper CORS_ORIGINS configuration could either block legitimate clients or expose API to cross-origin attacks. Wildcard (*) configurations in production would violate security requirements.

6. **Concurrent User Storage Race Conditions** (Medium): In-memory UserStorage dictionary operations (add_user, get_user) lack thread-safety mechanisms. Concurrent registration requests for same email could result in race conditions, data corruption, or duplicate user creation.

7. **PyJWT Dependency Vulnerabilities** (Low): PyJWT library vulnerabilities (like CVE-2022-29217 algorithm confusion) could compromise token validation. Outdated dependencies may contain known security flaws requiring version pinning and monitoring.

---

## Obstacles

- **Missing Low-Level Design**: LLD document exists but is not in the provided epic.yaml features list, creating potential gaps between design documentation and implementation tracking.

- **Environment Configuration Complexity**: .env.example template requires manual setup for JWT_SECRET_KEY and CORS_ORIGINS. Missing or incorrect configuration will cause runtime failures with unclear error messages.

- **Lack of Test Infrastructure**: Test plan specifies unit, integration, and E2E tests but no test framework (pytest, unittest), fixtures, or CI/CD integration defined. Testing setup must be bootstrapped alongside implementation.

- **Python Version Compatibility**: PRD specifies Python 3.8+ while HLD targets 3.10+. Version mismatch could cause deployment issues or require backporting type hints (union operator | syntax requires 3.10).

---

## Assumptions

1. **Single-Process Deployment**: Assumes API runs as single process/instance. Multi-instance deployments would require external session store (Redis) for shared user data, invalidating in-memory storage approach.

2. **Development/Demo Environment**: In-memory storage and lack of persistence assumes this is demo/testing system not intended for production use. Real deployment would require database migration.

3. **Trusted Network Environment**: 15-minute access token expiration and 7-day refresh token validity assume network traffic is monitored and users operate in reasonably secure environments. Higher security contexts may require shorter expirations.

4. **Standard Email Format**: Email validation assumes standard RFC 5322 format via Pydantic. Custom enterprise email systems or international domain names may require additional validation logic.

5. **Synchronous Request Processing**: FastAPI async capabilities not required for bcrypt operations. Assumes blocking password hashing won't impact overall throughput for target 1000 user scale.

---

## Mitigations

### JWT Secret Key Management (High)
- Generate cryptographically secure random secret (32+ bytes) using secrets module in deployment script
- Document secret rotation procedure and implement version-based signing to support key rollover
- Use environment variable validation at startup to fail fast if JWT_SECRET_KEY is missing or weak
- Add warning logs if secret appears to be default/example value from .env.example

### In-Memory Data Loss (Medium)
- Document data loss behavior clearly in README with warning about non-production use
- Implement optional JSON file persistence layer as configuration flag for development convenience
- Create seed data script to quickly repopulate test users after restart
- Add startup logging showing in-memory storage mode and expected behavior

### Bcrypt Performance Bottleneck (Medium)
- Profile bcrypt hashing time with cost factor 12 and adjust to 10 if exceeding 100ms target
- Implement async password hashing using asyncio.to_thread() to prevent blocking event loop
- Add performance monitoring/logging for registration and login endpoint response times
- Document load testing results and concurrency limits in deployment notes

### Token Refresh Security Gap (Medium)
- Implement optional in-memory token blacklist/revocation list (limited to refresh tokens)
- Add token family/chain tracking to detect token reuse attacks
- Document refresh token handling in security architecture and user guidelines
- Consider reducing refresh token expiration to 24-48 hours if security context requires

### CORS Misconfiguration (Low)
- Provide sensible defaults in config.py (localhost:3000, localhost:8000 for development)
- Add explicit validation for wildcard CORS origins with error/warning in production mode
- Document CORS configuration requirements in deployment guide
- Implement environment-based CORS presets (development vs production)

### Concurrent User Storage Race Conditions (Medium)
- Add threading.Lock to UserStorage class wrapping all dict operations
- Implement atomic check-and-set pattern for user_exists + add_user operations
- Add integration tests specifically for concurrent registration scenarios
- Document thread-safety guarantees and single-process limitation

### PyJWT Dependency Vulnerabilities (Low)
- Pin PyJWT version in requirements.txt to known-secure version (>=2.8.0)
- Configure Dependabot or similar tool for automated security updates
- Add "none" algorithm to JWT decode denied algorithms list explicitly
- Document security update process and testing requirements

---

## Appendix: Plan Documents

### PRD
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


### HLD
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


### LLD
# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-10T18:52:00Z
**Status:** Draft

## 1. Implementation Overview

FastAPI application with modular structure separating auth logic, token management, and route handlers. Password hashing via passlib with bcrypt. JWT tokens generated/validated using PyJWT. In-memory dictionary for user storage. Pydantic models for request/response validation. CORS middleware for cross-origin support.

---

## 2. File Structure

```
api/
  __init__.py
  main.py                    # FastAPI app initialization, CORS, routes registration
  config.py                  # Environment variables, JWT settings, constants
  models.py                  # Pydantic request/response models
  auth/
    __init__.py
    password.py              # Password hashing/verification functions
    tokens.py                # JWT creation/validation functions
    storage.py               # In-memory user storage
  routes/
    __init__.py
    auth.py                  # Registration, login, refresh endpoints
    protected.py             # Protected resource endpoints
  dependencies.py            # FastAPI dependency for token validation
requirements.txt             # PyJWT, fastapi, uvicorn, passlib, bcrypt
.env.example                 # Template for environment variables
```

---

## 3. Detailed Component Designs

**Authentication Service (api/auth/)**
- password.py: hash_password() uses bcrypt cost 12, verify_password() compares hashes
- tokens.py: create_access_token() generates JWT with 15min expiry, create_refresh_token() with 7d expiry, decode_token() validates signature and expiration
- storage.py: UserStorage class with dict, add_user(), get_user(), user_exists() methods

**Route Handlers (api/routes/)**
- auth.py: register(), login(), refresh() endpoints with business logic
- protected.py: get_profile() endpoint using dependency injection for auth

**Configuration (api/config.py)**
- Settings class with JWT_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES (15), REFRESH_TOKEN_EXPIRE_DAYS (7), CORS_ORIGINS

---

## 4. Database Schema Changes

N/A - No database required. In-memory storage only.

---

## 5. API Implementation Details

**POST /api/v1/auth/register**
- Validate email format and password length (min 8 chars)
- Check if user exists, return 400 if duplicate
- Hash password with bcrypt, store in UserStorage
- Return 201 with user email

**POST /api/v1/auth/login**
- Retrieve user from storage, return 401 if not found
- Verify password hash, return 401 if invalid
- Generate access and refresh tokens
- Return 200 with both tokens

**POST /api/v1/auth/refresh**
- Decode refresh token, validate type field is "refresh"
- Return 401 if invalid or expired
- Generate new access token with same subject
- Return 200 with new access token

**GET /api/v1/protected/profile**
- Dependency validates Authorization header Bearer token
- Extract email from token subject
- Return 200 with user email and message

---

## 6. Function Signatures

```python
# api/auth/password.py
def hash_password(password: str) -> str
def verify_password(plain_password: str, hashed_password: str) -> bool

# api/auth/tokens.py
def create_access_token(data: dict) -> str
def create_refresh_token(data: dict) -> str
def decode_token(token: str) -> dict

# api/auth/storage.py
class UserStorage:
    def add_user(self, email: str, password_hash: str) -> None
    def get_user(self, email: str) -> dict | None
    def user_exists(self, email: str) -> bool

# api/dependencies.py
async def get_current_user(authorization: str = Header(...)) -> str
```

---

## 7. State Management

In-memory Python dictionary in UserStorage singleton. Structure: `{"email": {"email": str, "password_hash": str}}`. No persistence between restarts. Thread-safe for single-process deployment.

---

## 8. Error Handling Strategy

- 400: Invalid input (email format, password length, duplicate user)
- 401: Authentication failed (invalid credentials, expired/invalid token)
- 422: Pydantic validation errors (missing fields, wrong types)
- 500: Unexpected server errors (logged with traceback)

Custom HTTPException raised with status_code and detail. FastAPI handles automatic JSON error responses.

---

## 9. Test Plan

### Unit Tests
- test_password.py: hash_password produces bcrypt hash, verify_password validates correct/incorrect passwords
- test_tokens.py: create tokens have correct expiration, decode_token validates signature and expiration
- test_storage.py: add/get/exists operations on UserStorage

### Integration Tests
- test_auth_routes.py: register creates user, login returns tokens, refresh issues new token, duplicate registration fails
- test_protected_routes.py: valid token accesses profile, expired token rejected, missing token rejected

### E2E Tests
- Full flow: register -> login -> access protected endpoint -> refresh -> access again

---

## 10. Migration Strategy

N/A - Greenfield implementation. Deploy as new service. No existing system to migrate from.

---

## 11. Rollback Plan

Remove container/process. No data persistence means no cleanup required. Restore previous service if replacing existing auth.

---

## 12. Performance Considerations

- Bcrypt hashing is intentionally slow (100ms target met)
- In-memory lookup O(1) for user retrieval
- JWT validation is stateless, no database lookup
- For 1000+ users, consider dict -> LRU cache for password hashes

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
      PRD.md
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
