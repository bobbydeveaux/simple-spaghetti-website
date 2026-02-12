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
