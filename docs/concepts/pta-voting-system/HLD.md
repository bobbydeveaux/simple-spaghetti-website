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
