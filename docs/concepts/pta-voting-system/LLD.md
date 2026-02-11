# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-11T15:03:52Z
**Status:** Draft

## 1. Implementation Overview

The PTA voting system will be implemented as a new application within the existing simple-spaghetti-repo. The backend will extend the existing FastAPI structure in the `api/` directory with new modules for voting, candidates, elections, and results. The frontend will be a new React application in `src/voting/` using the existing Tailwind CSS setup. The in-memory data store will use Python dictionaries with threading.Lock for thread-safe access, following the pattern established in `api/data_store.py`. Authentication will leverage the existing JWT infrastructure in `api/utils/jwt_manager.py` while adding voter-specific verification code logic. The implementation maintains clear separation between voter tracking and vote records to ensure anonymity.

---

## 2. File Structure

**New Backend Files:**
- `api/voting/` - New voting application module
  - `__init__.py` - Module initialization
  - `data_store.py` - In-memory storage with thread-safe dictionaries
  - `models.py` - Pydantic models for Voter, Candidate, Vote, Election, Session, AuditLog
  - `routes.py` - All voting-related API endpoints
  - `services.py` - Business logic for voting, results calculation, duplicate prevention
  - `admin_routes.py` - Admin-only endpoints for election/candidate management
  - `middleware.py` - Voter and admin authentication middleware

**New Frontend Files:**
- `src/voting/` - Voting application React components
  - `App.jsx` - Main voting app with routing
  - `pages/VoterLogin.jsx` - Email/code authentication page
  - `pages/Ballot.jsx` - Voting interface showing all positions
  - `pages/Results.jsx` - Public live results dashboard
  - `pages/admin/AdminLogin.jsx` - Admin authentication
  - `pages/admin/Dashboard.jsx` - Admin panel main view
  - `pages/admin/CandidateManagement.jsx` - CRUD for candidates
  - `pages/admin/ElectionManagement.jsx` - Election configuration
  - `pages/admin/AuditLogs.jsx` - Audit log viewer
  - `components/CandidateCard.jsx` - Candidate profile display
  - `components/PositionBallot.jsx` - Single position voting UI
  - `context/AuthContext.jsx` - Voter session management
  - `api/votingApi.js` - Axios client for backend API

**Modified Files:**
- `api/main.py` - Register voting routes
- `requirements.txt` - Add `python-multipart` for file uploads
- `package.json` - Add `recharts` for results visualization
- `vite.config.js` - Add proxy for `/api/voting/*` endpoints

**New Test Files:**
- `test_voting_api.py` - Backend API tests
- `test_vote_anonymity.py` - Verify anonymity guarantees
- `src/voting/__tests__/Ballot.test.jsx` - Frontend component tests

---

## 3. Detailed Component Designs

### Backend Data Store (`api/voting/data_store.py`)

**Class: VotingDataStore**
- Thread-safe singleton managing all in-memory data
- Storage dictionaries:
  - `voters: Dict[str, Voter]` - Keyed by voter_id
  - `candidates: Dict[str, Candidate]` - Keyed by candidate_id
  - `votes: List[Vote]` - No indexing by voter for anonymity
  - `sessions: Dict[str, Session]` - Keyed by session_id
  - `audit_logs: List[AuditLog]` - Append-only log
  - `election: Optional[Election]` - Single active election
  - `verification_codes: Dict[str, str]` - email -> code mapping (temporary)
- `threading.Lock()` instance for all write operations
- Methods: `get_voter()`, `create_voter()`, `record_vote()`, `get_results()`, `add_audit_log()`

### Voter Authentication Service (`api/voting/services.py`)

**Function: request_verification_code(email: str) -> Voter**
- Generate 6-digit random code
- Create or retrieve Voter record by email
- Store code in `verification_codes` dict (expires in 15 min)
- Return voter_id for client reference

**Function: verify_code(email: str, code: str) -> Session**
- Validate code matches stored value
- Create Session with JWT token (2-hour expiration)
- Clear verification code after successful auth
- Add LOGIN audit log entry

**Function: validate_session(token: str) -> Session**
- Decode JWT using existing `jwt_manager.py`
- Lookup session in data store
- Check expiration
- Return session or raise 401 error

### Voting Service (`api/voting/services.py`)

**Function: cast_votes(session: Session, votes: List[VoteSubmission]) -> None**
- Acquire data store lock
- Validate voter hasn't voted for each position (check `voter.voted_positions`)
- Validate candidate_id exists and matches position
- Create Vote records WITHOUT voter_id
- Update `voter.voted_positions` set
- Add VOTE_CAST audit log (position only, no candidate)
- Release lock

**Function: get_voter_status(voter_id: str) -> Set[str]**
- Return voter.voted_positions to show what positions are completed

### Results Service (`api/voting/services.py`)

**Function: calculate_results() -> Dict[str, List[CandidateResult]]**
- Iterate through all votes (no voter linkage)
- Group by position, count votes per candidate_id
- Calculate percentages
- Return structured results by position

### Admin Service (`api/voting/services.py`)

**Function: create_election(positions: List[str], admin_session: Session) -> Election**
- Verify admin_session.is_admin flag
- Create Election object with SETUP status
- Store in data store

**Function: add_candidate(candidate_data: CandidateCreate, admin_session: Session) -> Candidate**
- Verify admin privileges
- Validate position exists in election
- Create Candidate record
- Add ADMIN_ACTION audit log

**Function: get_audit_logs(limit: int, offset: int, admin_session: Session) -> List[AuditLog]**
- Verify admin privileges
- Return paginated audit logs

### Frontend Ballot Component (`src/voting/pages/Ballot.jsx`)

**Component Structure:**
- Fetch ballot data on mount via `/api/voting/ballot`
- Display four PositionBallot sub-components (one per position)
- Track selected candidates in local state: `{President: candidateId, ...}`
- Submit button calls `/api/voting/vote` with all selections
- Show confirmation modal on success
- Disable already-voted positions based on `/api/voting/status`

**Key Functions:**
- `fetchBallot()` - GET request with auth token
- `handleVoteSubmit()` - POST votes, handle errors (duplicate, network)
- `checkVotingStatus()` - GET voter's completed positions

### Frontend Results Dashboard (`src/voting/pages/Results.jsx`)

**Component Structure:**
- Poll `/api/voting/results` every 2 seconds using `setInterval`
- Display results grouped by position
- Use recharts BarChart for visual representation
- Show vote count and percentage for each candidate
- Real-time updates without page refresh

### Admin Dashboard (`src/voting/pages/admin/Dashboard.jsx`)

**Component Structure:**
- Tab navigation: Candidates | Election Config | Audit Logs
- Candidate tab: Table with add/edit/delete actions
- Election tab: Position configuration, status toggle (SETUP/ACTIVE/CLOSED)
- Audit tab: Paginated table showing timestamp, voter_id, action, position

---

## 4. Database Schema Changes

No database schema changes - this implementation uses in-memory Python dictionaries. The data models are defined as Pydantic classes for validation and serialization only.

**In-Memory Data Models (Pydantic):**

```python
class Voter(BaseModel):
    voter_id: str = Field(default_factory=lambda: str(uuid4()))
    email: EmailStr
    verification_code: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    voted_positions: Set[str] = Field(default_factory=set)

class Candidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    bio: str
    photo_url: Optional[str] = None
    position: Literal["President", "Vice President", "Secretary", "Treasurer"]

class Vote(BaseModel):
    vote_id: str = Field(default_factory=lambda: str(uuid4()))
    position: str
    candidate_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # NO voter_id field for anonymity

class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    voter_id: str
    token: str
    created_at: datetime
    expires_at: datetime
    is_admin: bool = False

class AuditLog(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    voter_id: str
    action: Literal["LOGIN", "VOTE_CAST", "ADMIN_ACTION"]
    position: Optional[str] = None  # Only for VOTE_CAST
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Election(BaseModel):
    election_id: str = Field(default_factory=lambda: str(uuid4()))
    positions: List[str]
    status: Literal["SETUP", "ACTIVE", "CLOSED"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 5. API Implementation Details

### POST /api/voting/auth/request-code
- **Request Body:** `{"email": "voter@example.com"}`
- **Handler Logic:**
  1. Validate email format (Pydantic EmailStr)
  2. Call `request_verification_code(email)`
  3. Mock send email (log code to console for testing)
- **Response:** `{"message": "Code sent", "voter_id": "uuid"}`
- **Error Handling:** 400 for invalid email

### POST /api/voting/auth/verify
- **Request Body:** `{"email": "voter@example.com", "code": "123456"}`
- **Handler Logic:**
  1. Call `verify_code(email, code)`
  2. Return session token
- **Response:** `{"token": "jwt...", "session_id": "uuid"}`
- **Error Handling:** 401 for invalid code, 404 if email not found

### GET /api/voting/ballot
- **Headers:** `Authorization: Bearer <token>`
- **Middleware:** Validate session via `validate_session()`
- **Handler Logic:**
  1. Fetch active election
  2. Get all candidates grouped by position
  3. Return ballot structure
- **Response:** `{"positions": [{"position": "President", "candidates": [...]}]}`
- **Error Handling:** 401 if unauthenticated, 404 if no active election

### POST /api/voting/vote
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:** `{"votes": [{"position": "President", "candidate_id": "uuid"}, ...]}`
- **Handler Logic:**
  1. Validate session
  2. Call `cast_votes(session, votes)`
  3. Handle duplicate vote exception
- **Response:** `{"success": true, "message": "Votes recorded"}`
- **Error Handling:** 400 for duplicate vote, 404 for invalid candidate_id, 401 if unauthenticated

### GET /api/voting/vote/status
- **Headers:** `Authorization: Bearer <token>`
- **Handler Logic:**
  1. Validate session
  2. Call `get_voter_status(voter_id)`
- **Response:** `{"voted_positions": ["President", "Secretary"]}`

### GET /api/voting/results
- **Handler Logic:**
  1. Call `calculate_results()`
  2. Return aggregated results
- **Response:** `{"results": [{"position": "President", "candidates": [{"candidate": {...}, "vote_count": 10, "percentage": 45.5}]}]}`
- **Error Handling:** None (public endpoint)

### POST /api/voting/admin/candidates
- **Headers:** `Admin-Token: Bearer <admin_token>`
- **Middleware:** Validate admin session
- **Request Body:** `{"name": "John Doe", "bio": "...", "photo_url": "...", "position": "President"}`
- **Handler Logic:**
  1. Call `add_candidate(data, admin_session)`
- **Response:** `{"candidate_id": "uuid"}`
- **Error Handling:** 403 if not admin, 400 for validation errors

### GET /api/voting/admin/audit
- **Headers:** `Admin-Token: Bearer <admin_token>`
- **Query Params:** `?limit=50&offset=0`
- **Handler Logic:**
  1. Call `get_audit_logs(limit, offset, admin_session)`
- **Response:** `{"logs": [{"timestamp": "...", "action": "VOTE_CAST", "voter_id": "uuid"}]}`
- **Error Handling:** 403 if not admin

---

## 6. Function Signatures

### Backend Services

```python
# api/voting/services.py

def request_verification_code(email: str) -> Voter:
    """Generate verification code and create/retrieve voter."""
    pass

def verify_code(email: str, code: str) -> Session:
    """Validate code and create authenticated session."""
    pass

def validate_session(token: str) -> Session:
    """Decode JWT and validate session exists and is not expired."""
    pass

def cast_votes(session: Session, votes: List[VoteSubmission]) -> None:
    """Record votes, enforce duplicate prevention, maintain anonymity."""
    pass

def get_voter_status(voter_id: str) -> Set[str]:
    """Return positions voter has already voted for."""
    pass

def calculate_results() -> Dict[str, List[CandidateResult]]:
    """Aggregate votes by position and candidate, calculate percentages."""
    pass

def create_election(positions: List[str], admin_session: Session) -> Election:
    """Create new election configuration (admin only)."""
    pass

def add_candidate(data: CandidateCreate, admin_session: Session) -> Candidate:
    """Add candidate to election (admin only)."""
    pass

def get_audit_logs(limit: int, offset: int, admin_session: Session) -> List[AuditLog]:
    """Retrieve paginated audit logs (admin only)."""
    pass
```

### Frontend API Client

```javascript
// src/voting/api/votingApi.js

export async function requestVerificationCode(email: string): Promise<{voter_id: string}> {}

export async function verifyCode(email: string, code: string): Promise<{token: string, session_id: string}> {}

export async function fetchBallot(token: string): Promise<BallotData> {}

export async function submitVotes(token: string, votes: VoteSubmission[]): Promise<{success: boolean}> {}

export async function fetchVotingStatus(token: string): Promise<{voted_positions: string[]}> {}

export async function fetchResults(): Promise<ResultsData> {}

export async function adminLogin(username: string, password: string): Promise<{token: string}> {}

export async function createCandidate(token: string, candidate: CandidateCreate): Promise<Candidate> {}

export async function fetchAuditLogs(token: string, limit: number, offset: number): Promise<AuditLog[]} {}
```

---

## 7. State Management

### Frontend State (React Context)

**AuthContext (`src/voting/context/AuthContext.jsx`):**
- Manages voter authentication state
- Stores: `token`, `sessionId`, `votedPositions`
- Methods: `login(email, code)`, `logout()`, `checkStatus()`
- Persists token to localStorage for page refresh
- Provides context to all components via `useAuth()` hook

**Admin State:**
- Separate `AdminAuthContext` for admin session
- Stores: `adminToken`, `isAdmin`

**Results State:**
- Local component state in `Results.jsx`
- Polling mechanism updates state every 2 seconds
- No global state needed (read-only public data)

### Backend State (In-Memory)

**VotingDataStore Singleton:**
- Single instance shared across all requests
- Thread-safe access via `threading.Lock()`
- Lock acquired for all write operations (vote recording, voter creation)
- Read operations (results, ballot fetch) use lock to prevent dirty reads during writes

---

## 8. Error Handling Strategy

### Backend Error Codes

- **400 Bad Request:** Invalid input (malformed email, missing fields, duplicate vote attempt)
- **401 Unauthorized:** Invalid or expired token, incorrect verification code
- **403 Forbidden:** Non-admin attempting admin operation
- **404 Not Found:** Voter email not found, invalid candidate_id, no active election
- **500 Internal Server Error:** Unexpected exceptions (logged with stack trace)

### Exception Classes

```python
class VotingException(Exception):
    """Base exception for voting system."""
    pass

class DuplicateVoteError(VotingException):
    """Raised when voter attempts to vote twice for same position."""
    pass

class InvalidCandidateError(VotingException):
    """Raised when candidate_id doesn't exist or doesn't match position."""
    pass

class SessionExpiredError(VotingException):
    """Raised when JWT token or session has expired."""
    pass
```

### Frontend Error Handling

- API client wraps all requests in try-catch
- Display user-friendly error messages in modals
- Example messages:
  - "You have already voted for this position"
  - "Verification code is incorrect or expired"
  - "Your session has expired, please log in again"
- Network errors: "Unable to connect to server, please try again"

### Audit Logging for Errors

- Failed login attempts NOT logged (prevent voter enumeration)
- Failed vote submissions logged with reason (duplicate, invalid candidate)
- Admin action failures logged for security monitoring

---

## 9. Test Plan

### Unit Tests

**Backend (`test_voting_api.py`):**
- `test_generate_verification_code()` - Verify 6-digit code generated
- `test_verify_code_success()` - Valid code creates session
- `test_verify_code_invalid()` - Invalid code raises 401
- `test_cast_vote_success()` - Vote recorded, voter marked as voted
- `test_cast_vote_duplicate()` - Second vote for same position raises DuplicateVoteError
- `test_calculate_results()` - Vote counts and percentages accurate
- `test_vote_anonymity()` - Verify Vote records contain no voter_id
- `test_admin_create_candidate()` - Admin can add candidate
- `test_non_admin_create_candidate()` - Non-admin gets 403

**Frontend (`src/voting/__tests__/Ballot.test.jsx`):**
- `test_ballot_renders_all_positions()` - Four position components rendered
- `test_vote_submission()` - Form submission calls API correctly
- `test_disabled_voted_positions()` - Already-voted positions are disabled
- `test_error_display()` - Error modal shows on API failure

### Integration Tests

**API Integration (`test_voting_integration.py`):**
- `test_full_voting_flow()` - Request code → verify → fetch ballot → submit vote → check status
- `test_duplicate_prevention()` - Two vote attempts result in second failure
- `test_results_accuracy()` - Submit votes, verify results endpoint reflects counts
- `test_admin_workflow()` - Admin login → create election → add candidates → view audit logs

**Frontend Integration:**
- `test_voter_journey()` - Login → view ballot → submit votes → see confirmation
- `test_results_polling()` - Results update when new votes cast

### E2E Tests

**Cypress Tests (`cypress/e2e/voting.cy.js`):**
- `test_complete_voter_flow()` - Full user journey from login to vote submission
- `test_admin_panel()` - Admin creates election, adds candidates, views logs
- `test_live_results()` - Results dashboard updates in real-time
- `test_concurrent_voters()` - Multiple browser sessions voting simultaneously
- `test_session_expiration()` - Expired session redirects to login

---

## 10. Migration Strategy

**Phase 1: Backend Setup**
1. Create `api/voting/` directory structure
2. Implement data models and in-memory data store
3. Register routes in `api/main.py`
4. Add mock admin credentials to `api/config.py`

**Phase 2: Core Voting API**
1. Implement authentication endpoints (request code, verify)
2. Implement voting endpoints (ballot, vote, status)
3. Implement results endpoint
4. Unit test all services

**Phase 3: Admin API**
1. Implement admin authentication
2. Implement candidate management endpoints
3. Implement election configuration endpoints
4. Implement audit log endpoint

**Phase 4: Frontend Setup**
1. Create `src/voting/` directory structure
2. Setup routing with React Router
3. Create AuthContext for session management
4. Build API client with Axios

**Phase 5: Voter UI**
1. Build voter login page
2. Build ballot page with position components
3. Build results dashboard with polling
4. Integrate with backend APIs

**Phase 6: Admin UI**
1. Build admin login page
2. Build dashboard with tab navigation
3. Build candidate management interface
4. Build audit log viewer

**Phase 7: Testing & Polish**
1. Run all unit and integration tests
2. Perform E2E testing with Cypress
3. Test concurrent voting scenarios
4. Verify anonymity guarantees

**Deployment:**
- Backend: Update `api/main.py` to include voting routes, deploy to existing server
- Frontend: Build `src/voting/` as separate app bundle, serve from `/voting` path
- Configure proxy in `vite.config.js` for local development

---

## 11. Rollback Plan

**If Deployment Fails:**

1. **Backend Rollback:**
   - Revert `api/main.py` to previous version (remove voting route registration)
   - Remove `api/voting/` directory
   - Restart server with previous code

2. **Frontend Rollback:**
   - Remove `src/voting/` directory
   - Revert `vite.config.js` and `package.json` changes
   - Rebuild frontend with `npm run build`
   - Deploy previous dist/ bundle

3. **Database/State:**
   - No database rollback needed (in-memory data)
   - Server restart clears all voting data automatically

4. **Testing Rollback:**
   - If tests are failing, disable new test files
   - Existing tests for other features should remain unaffected

**Rollback Triggers:**
- Critical bugs preventing voting
- Security vulnerabilities discovered
- Performance degradation affecting existing features
- Data corruption in in-memory store

**Validation After Rollback:**
- Verify existing auth API still works (`/api/auth/*`)
- Verify frontend loads correctly
- Check server logs for errors

---

## 12. Performance Considerations

### Backend Optimizations

**Thread-Safe In-Memory Access:**
- Use `threading.RLock()` for reentrant lock support
- Minimize lock hold time (acquire, execute, release immediately)
- Read-heavy operations (results) use shared lock if needed

**Results Calculation Caching:**
- Cache results for 1 second to reduce computation on high-traffic results endpoint
- Invalidate cache on new vote submission
- Implementation: `@lru_cache` with TTL

**Session Validation:**
- Cache decoded JWT payloads for 30 seconds to avoid repeated decoding
- Use in-memory session lookup (O(1) dict access)

### Frontend Optimizations

**Results Polling:**
- 2-second polling interval balances real-time feel with server load
- Use `AbortController` to cancel in-flight requests on unmount
- Implement exponential backoff on network errors

**Component Memoization:**
- Use `React.memo()` for CandidateCard to prevent re-renders
- Memoize results calculations in Results.jsx with `useMemo()`

**Bundle Optimization:**
- Code-split admin panel (lazy load with `React.lazy()`)
- Tree-shake unused Tailwind classes in production build
- Compress images with `vite-plugin-imagemin`

### Concurrency Handling

**Race Condition Prevention:**
- Lock acquisition in `cast_votes()` ensures atomic vote recording
- Optimistic UI updates in frontend with rollback on error
- Session validation happens before lock acquisition to reduce lock contention

**Load Testing Targets:**
- 500 concurrent voters (per PRD NFR)
- 50 requests/second sustained
- <200ms API response time at peak load

**Monitoring:**
- Log request duration for all endpoints
- Track lock wait times to identify contention
- Monitor memory usage (in-memory store grows with users)

### Database Migration Path (Future)

When migrating to persistent database:
1. Replace `VotingDataStore` with SQLAlchemy ORM
2. Use database transactions instead of threading.Lock
3. Index `votes.position` and `votes.candidate_id` for fast results aggregation
4. Add Redis for session storage to enable horizontal scaling
5. Implement read replicas for results endpoint (read-heavy workload)

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
.gitignore
.pr-number
README.md
api/
  __init__.py
  app.py
  auth.py
  config.py
  data_store.py
  main.py
  middleware/
    __init__.py
    auth_middleware.py
  models/
    __init__.py
    token.py
    user.py
  routes/
    __init__.py
    auth.py
    protected.py
  services/
    __init__.py
    auth_service.py
    user_repository.py
  utils/
    __init__.py
    jwt_manager.py
    password.py
  validators.py
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
    pta-voting-system/
      HLD.md
      PRD.md
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
test_auth_implementation.py
test_data_store_validators.py
test_library_api.py
test_loan_implementation.py
test_member_registration.py
test_models.py
vite.config.js
```
