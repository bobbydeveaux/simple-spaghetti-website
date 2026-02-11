# ROAM Analysis: pta-voting-system

**Feature Count:** 6
**Created:** 2026-02-11T15:07:31Z

## Risks

1. **In-Memory Data Loss** (High): Server restarts or crashes during active voting will result in complete data loss including all votes cast, candidate information, and session state. This is critical during live elections and could undermine trust in the system.

2. **Race Conditions in Concurrent Voting** (High): Despite using threading.Lock, the separate storage of voter tracking (voted_positions) and vote records creates a window where lock release/acquisition could allow duplicate votes if not implemented atomically. With 500 concurrent voters, race conditions are highly probable.

3. **Vote Anonymity Implementation Gap** (Medium): The separation between voter tracking and vote records relies on correct implementation discipline. Any inadvertent logging, error messages, or debugging code could leak voter-vote associations. The audit logs track voter_id and position, creating potential correlation risks.

4. **Session State Scalability Bottleneck** (Medium): All session validation, vote recording, and results calculation share a single threading.Lock, creating a serialization bottleneck. At 500 concurrent voters with <200ms response time requirements, lock contention could cause cascading failures.

5. **JWT Token Security Without Refresh Mechanism** (Medium): 2-hour token expiration without refresh tokens means voters could be logged out mid-voting during long sessions. Lost tokens cannot be revoked (in-memory sessions disappear on restart), creating security gaps.

6. **Frontend Polling Overhead** (Low): Every client polling /api/results every 2 seconds creates O(n) load on results calculation. With public access and no rate limiting, this endpoint could be abused for DoS attacks.

7. **Mock Verification Code Exposure** (Low): Logging verification codes to console for testing purposes could be accidentally left enabled in production, allowing unauthorized access via server log inspection.

---

## Obstacles

- **No existing thread-safe data store pattern**: The repo's current `api/data_store.py` doesn't implement concurrent access patterns needed for voting. Need to design and test threading.Lock implementation from scratch without existing reference code.

- **JWT infrastructure mismatch**: Existing `api/utils/jwt_manager.py` is designed for user authentication, not voter sessions with anonymity requirements. May need parallel JWT implementation to avoid coupling voter and admin authentication.

- **Frontend architecture separation**: Voting app in `src/voting/` is completely isolated from existing `src/` app. Need to determine routing strategy (separate entry point vs. integrated routing) and whether to share Tailwind config or duplicate.

- **Testing infrastructure gap**: No existing E2E test setup (Cypress mentioned in LLD but not in repo). Need to bootstrap entire testing infrastructure including concurrent voting simulation tools.

---

## Assumptions

1. **Verification codes are sufficient authentication**: Assumes email-based 6-digit codes provide adequate security for school PTA elections without implementing actual email delivery, CAPTCHA, or rate limiting. *Validation: Review with school administration on acceptable authentication level.*

2. **Single active election model**: Assumes only one election runs at a time (single Election object in data store). *Validation: Confirm with stakeholders that sequential elections are acceptable.*

3. **500 concurrent voters is maximum scale**: In-memory design assumes school voter population won't exceed 500 simultaneous users. *Validation: Analyze historical PTA participation rates and peak voting patterns.*

4. **Threading.Lock provides sufficient concurrency**: Assumes Python's GIL and threading.Lock will handle concurrent writes without deadlocks or performance degradation at target load. *Validation: Load testing with 500 simulated concurrent voters before production deployment.*

5. **Voters use single device/session**: Assumes voters won't attempt to vote from multiple devices simultaneously with same credentials. *Validation: Test multi-device scenario and document expected behavior.*

---

## Mitigations

### For Risk 1: In-Memory Data Loss (High)

- **Periodic State Snapshots**: Implement automatic JSON serialization of entire data store every 30 seconds to disk. On server restart, load latest snapshot to recover state (won't prevent loss of last 30s of votes, but limits damage).

- **Graceful Shutdown Handler**: Add signal handlers (SIGTERM/SIGINT) that flush current state to disk before server shutdown. Prevents data loss during planned restarts.

- **Dual-Write Logging**: Write all vote submissions to append-only log file immediately after recording in memory. Provides audit trail and recovery mechanism even if in-memory state is lost.

- **Pre-Production Communication**: Document data loss risk explicitly for stakeholders. Schedule elections during low-traffic periods to minimize server restart needs.

### For Risk 2: Race Conditions in Concurrent Voting (High)

- **Atomic Vote Recording**: Refactor `cast_votes()` to acquire lock once, perform all checks (voter.voted_positions) and updates (vote recording + voter.voted_positions update) within single lock context. Never release and re-acquire lock mid-transaction.

- **Comprehensive Concurrency Tests**: Create dedicated `test_concurrent_voting.py` using threading.Thread to simulate 50+ simultaneous vote submissions for same voter. Assert only one succeeds.

- **Transaction Logging**: Log every lock acquisition/release with timestamps and operation type. Monitor logs during load testing to detect lock hold time exceeding 50ms (warning sign of contention).

- **Read-Write Lock Upgrade**: Replace threading.Lock with threading.RLock (reentrant) or implement read-write lock using threading.Condition to allow concurrent reads (results calculation) while blocking writes.

### For Risk 3: Vote Anonymity Implementation Gap (Medium)

- **Anonymity Verification Test Suite**: Create `test_vote_anonymity.py` that records votes, then searches entire data store (voters, votes, audit_logs) for any data structure containing both voter_id and candidate_id. Assert none exist.

- **Code Review Checklist**: Before merging, review all logging statements, error handlers, and audit log entries to verify no voter-vote linkage appears in any output.

- **Separate Vote Recording Module**: Isolate vote recording logic in dedicated module that never receives voter_id as parameter. Pass only position and candidate_id to prevent accidental linkage.

- **Production Log Sanitization**: Implement custom logging filter that scrubs any log messages containing both "voter_id" and "candidate" patterns before writing to disk.

### For Risk 4: Session State Scalability Bottleneck (Medium)

- **Read-Heavy Optimization**: Results calculation and ballot fetching (read-only operations) should use copy-on-read pattern - create shallow dict copy outside lock, then process without holding lock.

- **Lock Profiling**: Add instrumentation to measure lock wait times per endpoint. Set alert threshold at 100ms wait time. If exceeded during load testing, implement per-resource locks (separate locks for voters, votes, candidates).

- **Results Caching**: Implement 1-second TTL cache for `calculate_results()` as specified in LLD. Invalidate on vote submission. Reduces lock acquisition frequency for most common read operation.

- **Load Testing Validation**: Before production, run load test simulating 500 concurrent voters with 70% voting, 30% viewing results. Assert p95 latency stays under 200ms.

### For Risk 5: JWT Token Security Without Refresh Mechanism (Medium)

- **Extended Session Duration**: Increase token expiration to 4 hours instead of 2 hours to cover typical voting session duration. School elections unlikely to require multi-hour voting sessions.

- **Session Extension Endpoint**: Add `POST /api/auth/extend-session` that issues new token if current token is valid and less than 30 minutes expired. Frontend calls automatically when detecting token expiring within 10 minutes.

- **Voter Re-Authentication Flow**: Design UX to gracefully handle session expiration - save ballot selections to localStorage, redirect to login, restore selections after re-authentication.

- **Admin Token Separation**: Use separate JWT signing key for admin tokens vs voter tokens to prevent privilege escalation if voter token is compromised.

### For Risk 6: Frontend Polling Overhead (Low)

- **Exponential Backoff Polling**: Start with 2-second interval, but if results unchanged for 3 consecutive polls, increase interval to 5 seconds, then 10 seconds. Resume 2-second polling after detecting result change.

- **Conditional GET with ETag**: Return ETag header with results response hash. Frontend sends If-None-Match header. Backend returns 304 Not Modified if results unchanged, saving computation and bandwidth.

- **Rate Limiting Middleware**: Add rate limiter to `/api/results` endpoint allowing max 1 request per second per IP. Prevents DoS abuse while allowing legitimate polling.

- **Server-Sent Events (SSE) Future Migration**: Document SSE as future enhancement to replace polling with push-based updates. Prototype remains with polling for simplicity.

### For Risk 7: Mock Verification Code Exposure (Low)

- **Environment-Based Logging**: Wrap verification code logging in `if os.getenv('ENVIRONMENT') == 'development'` check. Never log codes in production environment.

- **Code Delivery Abstraction**: Create `EmailService` interface with `MockEmailService` (logs codes) and `ProductionEmailService` (silent) implementations. Inject via dependency injection based on environment.

- **Security Audit Checklist**: Add pre-deployment checklist item: "Verify no verification codes appear in production logs during test voting session."

- **Alternative Testing Method**: In production, display verification code in API response only (not logs). Admin can view code via admin panel for troubleshooting without exposing in server logs.

---

## Appendix: Plan Documents

### PRD
# Product Requirements Document: An advanced voting system to allow my school to elect a new PTA (Parent-Teacher Association).

Technical Stack:
- Frontend: React with Tailwind CSS for a modern, responsive UI
- Backend: FastAPI (Python) for the API layer
- Data: Mock/in-memory data store (no real database needed for now)

Core Features:
- Candidate registration and profile management
- Voter authentication (simple email/code verification mock)
- Ballot creation with multiple positions (President, Vice President, Secretary, Treasurer)
- Real-time voting with duplicate vote prevention
- Live results dashboard with vote counts and percentages
- Admin panel to manage elections, candidates, and view audit logs

Security Requirements:
- Each voter can only vote once per position
- Votes are anonymous but auditable
- Admin-only access to sensitive operations

The system should be production-ready in terms of code quality but use mock data
to avoid database complexity for this prototype.


**Created:** 2026-02-11T15:01:14Z
**Status:** Draft

## 1. Overview

**Concept:** An advanced voting system to allow my school to elect a new PTA (Parent-Teacher Association).

Technical Stack:
- Frontend: React with Tailwind CSS for a modern, responsive UI
- Backend: FastAPI (Python) for the API layer
- Data: Mock/in-memory data store (no real database needed for now)

Core Features:
- Candidate registration and profile management
- Voter authentication (simple email/code verification mock)
- Ballot creation with multiple positions (President, Vice President, Secretary, Treasurer)
- Real-time voting with duplicate vote prevention
- Live results dashboard with vote counts and percentages
- Admin panel to manage elections, candidates, and view audit logs

Security Requirements:
- Each voter can only vote once per position
- Votes are anonymous but auditable
- Admin-only access to sensitive operations

The system should be production-ready in terms of code quality but use mock data
to avoid database complexity for this prototype.


**Description:** An advanced voting system to allow my school to elect a new PTA (Parent-Teacher Association).

Technical Stack:
- Frontend: React with Tailwind CSS for a modern, responsive UI
- Backend: FastAPI (Python) for the API layer
- Data: Mock/in-memory data store (no real database needed for now)

Core Features:
- Candidate registration and profile management
- Voter authentication (simple email/code verification mock)
- Ballot creation with multiple positions (President, Vice President, Secretary, Treasurer)
- Real-time voting with duplicate vote prevention
- Live results dashboard with vote counts and percentages
- Admin panel to manage elections, candidates, and view audit logs

Security Requirements:
- Each voter can only vote once per position
- Votes are anonymous but auditable
- Admin-only access to sensitive operations

The system should be production-ready in terms of code quality but use mock data
to avoid database complexity for this prototype.


---

## 2. Goals

- Enable secure, anonymous voting for PTA elections across four positions (President, Vice President, Secretary, Treasurer)
- Prevent duplicate votes while maintaining voter anonymity through a one-vote-per-position enforcement mechanism
- Provide real-time visibility into election results through a live dashboard with vote counts and percentages
- Streamline candidate management and election administration through a dedicated admin panel
- Deliver a production-quality prototype using mock data to validate system design before database integration

---

## 3. Non-Goals

- Implementing a persistent database or data storage layer (mock/in-memory only)
- Supporting multi-election management or historical election archives
- Implementing advanced identity verification beyond email/code mock authentication
- Mobile native applications (responsive web only)
- Integration with existing school management systems or third-party identity providers

---

## 4. User Stories

- As a voter, I want to authenticate using my email and a verification code so that I can access the voting ballot
- As a voter, I want to view all candidates for each position with their profiles so that I can make an informed decision
- As a voter, I want to cast one vote per position so that I can participate in the election
- As a voter, I want to see confirmation after voting so that I know my vote was recorded
- As a candidate, I want to register my profile with biographical information so that voters can learn about me
- As an admin, I want to create and manage election ballots with multiple positions so that I can configure elections
- As an admin, I want to view live voting results and statistics so that I can monitor election progress
- As an admin, I want to access audit logs showing voting activity so that I can ensure election integrity
- As a public user, I want to view the live results dashboard so that I can see election outcomes as votes are cast

---

## 5. Acceptance Criteria

**Voter Authentication:**
- Given a valid email address, when I request a verification code, then I receive a mock code and can authenticate
- Given an authenticated session, when I access the ballot, then I see all positions and candidates

**Voting Process:**
- Given I am authenticated, when I select one candidate per position and submit, then my votes are recorded
- Given I have already voted, when I attempt to vote again, then I am prevented and see an appropriate message
- Given I submit my ballot, when votes are recorded, then my voter identity is not linked to my vote choices

**Admin Panel:**
- Given I am an admin, when I create an election, then I can define positions and add candidates to each position
- Given an active election, when I view the admin dashboard, then I see real-time vote counts and audit logs

---

## 6. Functional Requirements

- FR-001: System shall authenticate voters using email and a mock verification code mechanism
- FR-002: System shall display a ballot with four positions: President, Vice President, Secretary, Treasurer
- FR-003: System shall allow candidates to register with name, bio, and optional photo
- FR-004: System shall enforce one vote per voter per position using session-based tracking
- FR-005: System shall record votes anonymously without linking voter identity to vote choices
- FR-006: System shall display a live results dashboard showing vote counts and percentages for each candidate
- FR-007: System shall provide an admin panel to create elections, manage candidates, and view audit logs
- FR-008: System shall log all voting events (timestamp, position voted) without recording voter-vote linkage

---

## 7. Non-Functional Requirements

### Performance
- Page load times shall not exceed 2 seconds on standard broadband connections
- Live results dashboard shall update within 1 second of a vote being cast
- API response times shall be under 200ms for voting and authentication operations

### Security
- Voter authentication tokens shall expire after 2 hours of inactivity
- Admin panel access shall require separate authentication with elevated privileges
- Vote anonymity shall be preserved by separating voter tracking from vote recording
- All API endpoints shall validate input and prevent injection attacks

### Scalability
- In-memory data store shall support up to 500 concurrent voters
- System shall handle up to 50 candidates across all positions
- Results dashboard shall efficiently serve read-heavy traffic during election periods

### Reliability
- System shall maintain data consistency in the in-memory store during concurrent vote submissions
- System shall handle race conditions when multiple voters submit votes simultaneously
- System shall provide clear error messages for failed operations without exposing system internals

---

## 8. Dependencies

- **React** (v18+): Frontend framework for building the user interface
- **Tailwind CSS** (v3+): Utility-first CSS framework for responsive styling
- **FastAPI** (v0.100+): Python web framework for building the REST API
- **Uvicorn**: ASGI server for running the FastAPI application
- **Pydantic**: Data validation library for FastAPI request/response models
- **CORS Middleware**: For handling cross-origin requests between React and FastAPI

---

## 9. Out of Scope

- Persistent database implementation (PostgreSQL, MongoDB, etc.)
- Email service integration for sending actual verification codes
- Multi-language support or internationalization
- Ranked-choice or complex voting algorithms beyond simple plurality
- Vote editing or retraction after submission
- Blockchain or cryptographic vote verification mechanisms
- SMS or phone-based authentication
- Accessibility compliance certification (though basic WCAG guidelines should be followed)

---

## 10. Success Metrics

- 100% of voters can successfully authenticate and cast votes without technical assistance
- Zero duplicate votes recorded per voter per position
- Live results dashboard achieves 99%+ accuracy compared to backend vote tallies
- Admin panel successfully manages elections and candidates with zero data loss during session
- System maintains vote anonymity with no voter-vote linkage discoverable in audit logs
- Application loads and operates smoothly with 100+ concurrent simulated voters

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers


### HLD
# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-11T15:02:09Z
**Status:** Draft

## 1. Architecture Overview

The system follows a **two-tier client-server architecture** with a React SPA frontend and FastAPI backend monolith. The backend maintains in-memory state using Python dictionaries with thread-safe access patterns. The frontend communicates with the backend via REST APIs. This monolithic approach is optimal for the prototype scope with mock data, avoiding unnecessary distributed system complexity while maintaining production-quality code structure for future database migration.

---

## 2. System Components

**Frontend Application (React SPA)**
- Voter Portal: Authentication, ballot viewing, vote submission
- Results Dashboard: Real-time vote counts and percentages
- Admin Panel: Election/candidate management, audit log viewing
- Candidate Registration: Self-service profile creation

**Backend API (FastAPI Monolith)**
- Authentication Service: Email/code verification, session management
- Voting Service: Vote recording, duplicate prevention, anonymity enforcement
- Election Service: Ballot/candidate CRUD operations
- Results Service: Live vote aggregation and statistics
- Audit Service: Event logging without voter-vote linkage

**In-Memory Data Store**
- Thread-safe dictionaries for voters, candidates, votes, sessions, audit logs
- Separate storage for voter tracking and vote records to ensure anonymity

---

## 3. Data Model

**Voter**
- voter_id (UUID), email, verification_code, created_at
- voted_positions (Set[str]): Tracks positions voted without vote choices

**Candidate**
- candidate_id (UUID), name, bio, photo_url, position (enum: President/VP/Secretary/Treasurer)

**Vote**
- vote_id (UUID), position, candidate_id, timestamp
- NO voter_id reference (anonymity requirement)

**Session**
- session_id (UUID), voter_id, token, created_at, expires_at, is_admin (bool)

**AuditLog**
- log_id (UUID), voter_id, action (enum: LOGIN/VOTE_CAST/ADMIN_ACTION), position (optional), timestamp

**Election**
- election_id (UUID), positions (List[str]), status (enum: SETUP/ACTIVE/CLOSED), created_at

---

## 4. API Contracts

**Authentication**
- POST /api/auth/request-code: {email} → {message, voter_id}
- POST /api/auth/verify: {email, code} → {token, session_id}
- POST /api/auth/admin-login: {username, password} → {token, session_id}

**Voting**
- GET /api/ballot: Header[Authorization] → {positions: [{position, candidates[]}]}
- POST /api/vote: Header[Authorization], {votes: [{position, candidate_id}]} → {success, message}
- GET /api/vote/status: Header[Authorization] → {voted_positions: []}

**Results**
- GET /api/results: → {results: [{position, candidates: [{candidate, vote_count, percentage}]}]}

**Admin - Candidates**
- POST /api/admin/candidates: Header[Admin-Token], {name, bio, photo_url, position} → {candidate_id}
- GET /api/admin/candidates: Header[Admin-Token] → [{candidate}]
- PUT /api/admin/candidates/{id}: Header[Admin-Token], {updates} → {candidate}

**Admin - Election**
- POST /api/admin/election: Header[Admin-Token], {positions[]} → {election_id}
- GET /api/admin/election: Header[Admin-Token] → {election}

**Admin - Audit**
- GET /api/admin/audit: Header[Admin-Token], ?limit, ?offset → {logs: [{timestamp, action, voter_id}]}

---

## 5. Technology Stack

### Backend
- **FastAPI** (v0.100+): REST API framework with automatic OpenAPI documentation
- **Uvicorn**: ASGI server for production-grade async request handling
- **Pydantic**: Request/response validation and serialization
- **Python 3.10+**: Type hints for code quality
- **threading.Lock**: Thread-safe in-memory data access

### Frontend
- **React** (v18+): Component-based UI with hooks for state management
- **React Router**: Client-side routing for SPA navigation
- **Tailwind CSS** (v3+): Utility-first styling framework
- **Axios**: HTTP client for API communication
- **React Context**: Global state for auth session

### Infrastructure
- **Node.js/npm**: Frontend build tooling
- **Vite**: Fast development server and build tool
- **CORS Middleware**: Cross-origin request handling

### Data Storage
- **In-Memory Python Dictionaries**: Primary data storage with threading.Lock for concurrency
- **No persistence layer**: Data resets on server restart (prototype requirement)

---

## 6. Integration Points

**Internal Integration**
- React frontend ↔ FastAPI backend via REST over HTTP
- CORS configuration allows http://localhost:3000 (dev) and production domain

**No External Integrations** (per PRD non-goals)
- Email verification uses mock codes (no SMTP/email service)
- No third-party identity providers
- No database connections
- No school management system integration

---

## 7. Security Architecture

**Authentication & Authorization**
- **Voter Auth**: Email-based with mock 6-digit verification codes (simulates email flow)
- **Admin Auth**: Separate credentials with elevated privileges (hardcoded for prototype)
- **Session Management**: JWT tokens with 2-hour expiration, stored in-memory
- **Token Validation**: Middleware validates tokens on protected endpoints

**Vote Anonymity**
- Voter tracking (voted_positions set) stored separately from vote records
- Vote records contain NO voter_id reference
- Audit logs track voter actions but NOT vote choices

**Input Validation**
- Pydantic models validate all request payloads
- Sanitization prevents injection attacks (SQL injection N/A with in-memory)
- Position/candidate_id validated against election configuration

**Access Control**
- Admin endpoints require is_admin flag in session
- Voters can only access their own voting status
- Results dashboard is public (read-only)

---

## 8. Deployment Architecture

**Development**
- Frontend: Vite dev server on port 3000
- Backend: Uvicorn on port 8000
- Single-machine deployment

**Production (Prototype)**
- Frontend: Static build served via Nginx or Vercel/Netlify
- Backend: Uvicorn with 4-8 workers behind reverse proxy (Nginx)
- Single VPS/EC2 instance (t3.medium sufficient for 500 concurrent users)
- HTTPS via Let's Encrypt

**Container Option** (if preferred)
- Dockerfile for FastAPI backend
- Docker Compose for local development (frontend + backend)
- Deployment to Docker-capable hosting (DigitalOcean, AWS ECS)

---

## 9. Scalability Strategy

**Current Capacity**
- In-memory storage supports 500 concurrent voters (per PRD)
- Single-process with threading.Lock ensures consistency

**Horizontal Scaling Constraints**
- In-memory data prevents multi-instance deployment
- Sticky sessions could enable scale-out but lose failover

**Vertical Scaling**
- Increase server CPU/RAM to handle higher concurrency
- Python asyncio in FastAPI efficiently handles I/O-bound operations

**Future Database Migration Path**
- Replace in-memory dicts with PostgreSQL/MongoDB
- Enables stateless backend for horizontal scaling
- Add Redis for session storage and rate limiting

---

## 10. Monitoring & Observability

**Logging**
- FastAPI middleware logs all requests (method, path, status, duration)
- Application logs for auth events, vote submissions, admin actions
- Python logging module with structured JSON format

**Metrics** (Basic)
- Manual counters in code: total_votes, active_sessions, votes_per_position
- Expose /api/health endpoint for uptime monitoring

**Error Tracking**
- Try-catch blocks with detailed error messages
- HTTP exception handlers return user-friendly errors without stack traces

**Real-Time Monitoring**
- Frontend polls /api/results every 2 seconds for live updates
- Admin dashboard displays audit log tail

**Future Enhancements**
- Add Prometheus metrics exporter
- Integrate Sentry for error tracking
- Structured logging to ELK stack

---

## 11. Architectural Decisions (ADRs)

**ADR-001: In-Memory Storage Instead of Database**
- Context: PRD specifies mock data for prototype
- Decision: Use Python dictionaries with threading.Lock
- Rationale: Simplifies development, validates business logic before DB complexity
- Consequences: Data loss on restart, no horizontal scaling, migration path needed

**ADR-002: Vote Anonymity via Separate Storage**
- Context: Votes must be anonymous but voters tracked for duplicates
- Decision: Store voter.voted_positions separately from vote records
- Rationale: Physical separation ensures no linkage possible in data model
- Consequences: Slightly more complex logic, but guarantees anonymity

**ADR-003: JWT Tokens with In-Memory Session Store**
- Context: Need stateful session tracking for duplicate prevention
- Decision: JWT tokens reference session_id in backend memory
- Rationale: Balances stateless token benefits with server-side control
- Consequences: Sessions lost on restart, but acceptable for prototype

**ADR-004: Monolithic FastAPI Backend**
- Context: Could split into microservices (auth, voting, results)
- Decision: Single FastAPI application with logical service modules
- Rationale: Prototype scope doesn't justify distributed system complexity
- Consequences: Simpler deployment, easier development, clear migration path

**ADR-005: Public Results Dashboard**
- Context: Real-time results could be admin-only or public
- Decision: Public read-only endpoint for transparency
- Rationale: Election transparency encourages participation
- Consequences: No authentication overhead, potential for result scraping (acceptable)

---

## Appendix: PRD Reference

# Product Requirements Document: An advanced voting system to allow my school to elect a new PTA (Parent-Teacher Association).

Technical Stack:
- Frontend: React with Tailwind CSS for a modern, responsive UI
- Backend: FastAPI (Python) for the API layer
- Data: Mock/in-memory data store (no real database needed for now)

Core Features:
- Candidate registration and profile management
- Voter authentication (simple email/code verification mock)
- Ballot creation with multiple positions (President, Vice President, Secretary, Treasurer)
- Real-time voting with duplicate vote prevention
- Live results dashboard with vote counts and percentages
- Admin panel to manage elections, candidates, and view audit logs

Security Requirements:
- Each voter can only vote once per position
- Votes are anonymous but auditable
- Admin-only access to sensitive operations

The system should be production-ready in terms of code quality but use mock data
to avoid database complexity for this prototype.


**Created:** 2026-02-11T15:01:14Z
**Status:** Draft

## 1. Overview

**Concept:** An advanced voting system to allow my school to elect a new PTA (Parent-Teacher Association).

Technical Stack:
- Frontend: React with Tailwind CSS for a modern, responsive UI
- Backend: FastAPI (Python) for the API layer
- Data: Mock/in-memory data store (no real database needed for now)

Core Features:
- Candidate registration and profile management
- Voter authentication (simple email/code verification mock)
- Ballot creation with multiple positions (President, Vice President, Secretary, Treasurer)
- Real-time voting with duplicate vote prevention
- Live results dashboard with vote counts and percentages
- Admin panel to manage elections, candidates, and view audit logs

Security Requirements:
- Each voter can only vote once per position
- Votes are anonymous but auditable
- Admin-only access to sensitive operations

The system should be production-ready in terms of code quality but use mock data
to avoid database complexity for this prototype.


**Description:** An advanced voting system to allow my school to elect a new PTA (Parent-Teacher Association).

Technical Stack:
- Frontend: React with Tailwind CSS for a modern, responsive UI
- Backend: FastAPI (Python) for the API layer
- Data: Mock/in-memory data store (no real database needed for now)

Core Features:
- Candidate registration and profile management
- Voter authentication (simple email/code verification mock)
- Ballot creation with multiple positions (President, Vice President, Secretary, Treasurer)
- Real-time voting with duplicate vote prevention
- Live results dashboard with vote counts and percentages
- Admin panel to manage elections, candidates, and view audit logs

Security Requirements:
- Each voter can only vote once per position
- Votes are anonymous but auditable
- Admin-only access to sensitive operations

The system should be production-ready in terms of code quality but use mock data
to avoid database complexity for this prototype.


---

## 2. Goals

- Enable secure, anonymous voting for PTA elections across four positions (President, Vice President, Secretary, Treasurer)
- Prevent duplicate votes while maintaining voter anonymity through a one-vote-per-position enforcement mechanism
- Provide real-time visibility into election results through a live dashboard with vote counts and percentages
- Streamline candidate management and election administration through a dedicated admin panel
- Deliver a production-quality prototype using mock data to validate system design before database integration

---

## 3. Non-Goals

- Implementing a persistent database or data storage layer (mock/in-memory only)
- Supporting multi-election management or historical election archives
- Implementing advanced identity verification beyond email/code mock authentication
- Mobile native applications (responsive web only)
- Integration with existing school management systems or third-party identity providers

---

## 4. User Stories

- As a voter, I want to authenticate using my email and a verification code so that I can access the voting ballot
- As a voter, I want to view all candidates for each position with their profiles so that I can make an informed decision
- As a voter, I want to cast one vote per position so that I can participate in the election
- As a voter, I want to see confirmation after voting so that I know my vote was recorded
- As a candidate, I want to register my profile with biographical information so that voters can learn about me
- As an admin, I want to create and manage election ballots with multiple positions so that I can configure elections
- As an admin, I want to view live voting results and statistics so that I can monitor election progress
- As an admin, I want to access audit logs showing voting activity so that I can ensure election integrity
- As a public user, I want to view the live results dashboard so that I can see election outcomes as votes are cast

---

## 5. Acceptance Criteria

**Voter Authentication:**
- Given a valid email address, when I request a verification code, then I receive a mock code and can authenticate
- Given an authenticated session, when I access the ballot, then I see all positions and candidates

**Voting Process:**
- Given I am authenticated, when I select one candidate per position and submit, then my votes are recorded
- Given I have already voted, when I attempt to vote again, then I am prevented and see an appropriate message
- Given I submit my ballot, when votes are recorded, then my voter identity is not linked to my vote choices

**Admin Panel:**
- Given I am an admin, when I create an election, then I can define positions and add candidates to each position
- Given an active election, when I view the admin dashboard, then I see real-time vote counts and audit logs

---

## 6. Functional Requirements

- FR-001: System shall authenticate voters using email and a mock verification code mechanism
- FR-002: System shall display a ballot with four positions: President, Vice President, Secretary, Treasurer
- FR-003: System shall allow candidates to register with name, bio, and optional photo
- FR-004: System shall enforce one vote per voter per position using session-based tracking
- FR-005: System shall record votes anonymously without linking voter identity to vote choices
- FR-006: System shall display a live results dashboard showing vote counts and percentages for each candidate
- FR-007: System shall provide an admin panel to create elections, manage candidates, and view audit logs
- FR-008: System shall log all voting events (timestamp, position voted) without recording voter-vote linkage

---

## 7. Non-Functional Requirements

### Performance
- Page load times shall not exceed 2 seconds on standard broadband connections
- Live results dashboard shall update within 1 second of a vote being cast
- API response times shall be under 200ms for voting and authentication operations

### Security
- Voter authentication tokens shall expire after 2 hours of inactivity
- Admin panel access shall require separate authentication with elevated privileges
- Vote anonymity shall be preserved by separating voter tracking from vote recording
- All API endpoints shall validate input and prevent injection attacks

### Scalability
- In-memory data store shall support up to 500 concurrent voters
- System shall handle up to 50 candidates across all positions
- Results dashboard shall efficiently serve read-heavy traffic during election periods

### Reliability
- System shall maintain data consistency in the in-memory store during concurrent vote submissions
- System shall handle race conditions when multiple voters submit votes simultaneously
- System shall provide clear error messages for failed operations without exposing system internals

---

## 8. Dependencies

- **React** (v18+): Frontend framework for building the user interface
- **Tailwind CSS** (v3+): Utility-first CSS framework for responsive styling
- **FastAPI** (v0.100+): Python web framework for building the REST API
- **Uvicorn**: ASGI server for running the FastAPI application
- **Pydantic**: Data validation library for FastAPI request/response models
- **CORS Middleware**: For handling cross-origin requests between React and FastAPI

---

## 9. Out of Scope

- Persistent database implementation (PostgreSQL, MongoDB, etc.)
- Email service integration for sending actual verification codes
- Multi-language support or internationalization
- Ranked-choice or complex voting algorithms beyond simple plurality
- Vote editing or retraction after submission
- Blockchain or cryptographic vote verification mechanisms
- SMS or phone-based authentication
- Accessibility compliance certification (though basic WCAG guidelines should be followed)

---

## 10. Success Metrics

- 100% of voters can successfully authenticate and cast votes without technical assistance
- Zero duplicate votes recorded per voter per position
- Live results dashboard achieves 99%+ accuracy compared to backend vote tallies
- Admin panel successfully manages elections and candidates with zero data loss during session
- System maintains vote anonymity with no voter-vote linkage discoverable in audit logs
- Application loads and operates smoothly with 100+ concurrent simulated voters

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers


### LLD
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
