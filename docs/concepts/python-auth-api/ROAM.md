# ROAM Analysis: python-auth-api

**Feature Count:** 3
**Created:** 2026-02-10T18:55:56Z

## Risks

1. **JWT Secret Key Management** (High): JWT_SECRET_KEY stored in environment variable could be exposed through config leaks, container inspection, or process dumps. Compromise allows attackers to forge valid tokens and impersonate any user.

2. **In-Memory Data Loss** (Medium): UserStorage dictionary lost on process restart or crash. No persistence means all registered users disappear, forcing re-registration and breaking active sessions.

3. **Bcrypt Performance Bottleneck** (Medium): Bcrypt cost factor 12 takes ~100ms per hash. Under load, registration and login endpoints could queue requests, causing timeouts. Single-threaded FastAPI worker exacerbates this.

4. **Refresh Token Revocation Gap** (High): No revocation mechanism for refresh tokens. Compromised refresh token valid for 7 days with no way to invalidate. Logout endpoint cannot truly end sessions.

5. **Email Validation Bypass** (Low): Pydantic email validation may allow edge cases (disposable emails, non-RFC compliant formats). Could enable spam registrations or enumeration attacks.

6. **Token Timing Attack** (Medium): Token validation uses standard equality checks. Attackers could exploit timing differences to brute-force token signatures or expirations.

7. **CORS Misconfiguration** (Medium): CORS_ORIGINS from environment could be set to wildcard (*) or overly permissive domains, allowing unauthorized cross-origin requests from malicious sites.

---

## Obstacles

- **No LLD File**: Missing `docs/concepts/python-auth-api/LLD.md` - implementation details not documented in repository. Epic references LLD but file doesn't exist in docs structure.

- **Repository Mismatch**: Current repo contains React/Vite frontend (pasta recipes app). Adding Python FastAPI to same repo creates mixed technology stack, complicating deployment and CI/CD pipelines.

- **Dependency Version Conflicts**: requirements.txt needs specific versions (PyJWT 2.x, passlib 1.7.x, bcrypt 4.x) but no lockfile. Transitive dependency conflicts between cryptography versions could break installations.

- **Test Framework Setup**: Test plan requires pytest, pytest-asyncio, httpx for async FastAPI testing. No existing Python test infrastructure in repository to build on.

---

## Assumptions

1. **Single-Instance Deployment**: Assumes single process deployment. In-memory UserStorage breaks with multiple instances/workers unless migrated to shared Redis/database. Needs validation if horizontal scaling required.

2. **Development/Demo Use Case**: Assumes non-production environment given in-memory storage and no audit logging. Production use requires significant hardening (token revocation, rate limiting, audit trails).

3. **Python 3.10+ Environment**: LLD specifies Python 3.10+ for modern type hints (dict | None syntax). Deployment environment must support this version - containers/systems with only 3.8 will fail.

4. **Environment Variable Configuration**: Assumes deployment platform supports .env files or environment injection (Docker, systemd, cloud platform). Manual configuration required for each environment.

5. **Reverse Proxy TLS Termination**: Assumes nginx or similar proxy handles HTTPS. API runs HTTP-only. Direct internet exposure without proxy would transmit tokens in cleartext.

---

## Mitigations

### JWT Secret Key Management (High)
- Generate cryptographically random 256-bit secret on deployment using secrets.token_urlsafe(32)
- Store in platform secret manager (AWS Secrets Manager, Kubernetes Secrets, HashiCorp Vault)
- Add startup validation: fail fast if JWT_SECRET_KEY missing or using default/weak value
- Implement secret rotation strategy with dual-key grace period for zero-downtime rotation

### In-Memory Data Loss (Medium)
- Add optional Redis backend toggle via environment variable for persistent storage
- Implement UserStorage interface with InMemoryStorage and RedisStorage implementations
- Document data loss behavior clearly in README with restart warnings
- Add health check endpoint that reports storage type and uptime

### Bcrypt Performance Bottleneck (Medium)
- Use FastAPI BackgroundTasks for password hashing on registration to unblock response
- Add uvicorn workers configuration (--workers 4) for CPU-bound bcrypt operations
- Implement request timeout (30s) and return 503 with Retry-After header under load
- Consider bcrypt cost factor 10 (instead of 12) if performance testing shows 100ms target missed

### Refresh Token Revocation Gap (High)
- Implement in-memory token blacklist (set of revoked token JTIs) in UserStorage
- Add /logout endpoint that adds refresh token JTI to blacklist with TTL matching expiration
- Validate token JTI not in blacklist during decode_token() check
- Migrate blacklist to Redis if moving to multi-instance deployment

### Email Validation Bypass (Low)
- Use pydantic.EmailStr for strict RFC 5322 validation
- Add custom validator to reject disposable email domains (maintain blocklist or use API)
- Implement case normalization (lowercase) before storage to prevent duplicate registrations
- Add email existence verification in integration tests

### Token Timing Attack (Medium)
- Use hmac.compare_digest() for token signature comparison in decode_token()
- Add constant-time string comparison for refresh token type validation
- Implement rate limiting on auth endpoints (10 req/min per IP) using slowapi middleware
- Add exponential backoff on failed login attempts per email

### CORS Misconfiguration (Medium)
- Set default CORS_ORIGINS to empty list in config.py (deny all by default)
- Require explicit comma-separated list of allowed origins in environment variable
- Add startup validation to reject wildcard (*) in production mode
- Document CORS configuration in .env.example with security notes

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
