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
