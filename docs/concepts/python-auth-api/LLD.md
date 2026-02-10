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
