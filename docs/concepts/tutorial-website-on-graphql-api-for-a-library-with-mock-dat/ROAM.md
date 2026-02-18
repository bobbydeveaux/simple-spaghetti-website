# ROAM Analysis: tutorial-website-on-graphql-api-for-a-library-with-mock-dat

**Feature Count:** 7
**Created:** 2026-02-18T20:46:12Z

## Risks

1. **`graph-gophers/graphql-go` API Compatibility** (Medium): The schema-first resolver pattern in `graph-gophers/graphql-go` requires method signatures to match exported field names exactly (e.g., `Books()`, `Users()`). A mismatch between schema field names and Go method names causes a runtime panic at schema parse time, not a compile-time error. This could delay the GraphQL feature and tests if the resolver wiring is not validated early.

2. **Tutorial Narrative Accuracy of the N+1 Demonstration** (Medium): The dashboard fires 4 REST calls (`/books`, `/users`, `/rentals`, `/library`) but the true N+1 problem emerges when fetching nested relations per-record (e.g., one request per rental to resolve its book). With flat endpoints and client-side joining, the demo shows over-fetching and request count, but does not strictly demonstrate N+1 in its classical form. This risks misleading learners about what N+1 actually is.

3. **Go Version Compatibility with `embed` Directive** (Low): `//go:embed` requires Go 1.16+; the LLD targets Go 1.21+. If a developer has an older toolchain, the server will fail to compile with an opaque error. No toolchain version enforcement exists in the plan beyond a `go.mod` directive.

4. **GraphQL Payload Size Comparison Reliability** (Low): The integration test asserts that the GraphQL payload is smaller than the `/library` response. This holds only when the dashboard query requests a subset of fields. If the query is later expanded to request all fields, the test will fail or the tutorial's core claim becomes false. The comparison is sensitive to the exact GraphQL query string used in the frontend.

5. **CORS Configuration Scope Creep into Production Use** (Low): The design documents `Access-Control-Allow-Origin: *` as acceptable for a tutorial. If the repo is used as a starting point for a real service, the open CORS policy will be copied without review. The risk is low for this artifact but medium for downstream misuse.

6. **`embed.FS` Path Resolution for Static Files** (Medium): The `//go:embed static` directive in `main.go` requires the `static/` directory to be at the correct path relative to `main.go` at compile time. If the module is run from a different working directory or the embed path is misconfigured, the server compiles but serves 404s for all static routes — a non-obvious failure mode for tutorial users running `go run .` from a parent directory.

7. **Tutorial Page Code Snippet Drift** (Low): `tutorial.html` contains hardcoded Go source snippets copied from the actual implementation. If `graphql.go` or `handlers.go` are modified after initial implementation, the tutorial snippets will silently diverge from the real code, undermining the tutorial's accuracy. There is no automated check to detect this drift.

---

## Obstacles

- **No Go toolchain version pinned in the repository**: The plan specifies Go 1.21+ in prose but there is no `go.toolchain` directive or `.go-version` file. A developer with Go 1.16–1.20 will encounter subtle behavioral differences (e.g., `any` type alias availability, `net/http` behavior changes) without a clear error message pointing to the version requirement.

- **`graph-gophers/graphql-go` requires exact method-to-field name matching verified only at runtime**: Unlike `gqlgen`, which generates type-safe resolver stubs, `graph-gophers/graphql-go` panics at startup if resolver methods do not match the schema. There is no compile-time validation, meaning the GraphQL endpoint cannot be confirmed working until the server is actually started — a potential blocker during initial development if the schema and resolvers are built separately.

- **No CI or automated build verification defined**: The plan explicitly excludes deployment infrastructure and CI/CD. This means there is no automated gate to catch a broken `go build`, failing tests, or embed path issues before the tutorial is shared. Breakage will only surface when a user manually runs the project.

- **Tutorial HTML requires manual synchronization with Go source**: There is no tooling (e.g., a `go generate` step or test asserting snippet content) to keep `tutorial.html` code blocks consistent with `graphql.go` and `handlers.go`. This is a manual process with no safety net.

---

## Assumptions

1. **Assumption: `graph-gophers/graphql-go` resolver method naming convention is straightforward to implement correctly.**
   *Validation approach*: Implement and start the GraphQL handler in the first development session, before writing tests. Confirm schema parses and the `dashboard` query resolves end-to-end against mock data before building the dashboard UI that depends on it.

2. **Assumption: Client-side `performance.now()` and `TextEncoder.byteLength` measurements will show a meaningful, consistent difference between REST and GraphQL payloads on localhost.**
   *Validation approach*: Run the dashboard manually on localhost and verify that the GraphQL byte count is measurably lower than combined REST bytes. If the mock dataset is too small to show a clear difference, increase the number of mock records or add more fields to the REST structs.

3. **Assumption: `go run .` from inside `library-tutorial/` correctly resolves the `//go:embed static` directive and serves static files without additional configuration.**
   *Validation approach*: Explicitly test `go run .` from the `library-tutorial/` directory on a clean checkout as the first integration smoke test, before any other testing.

4. **Assumption: The 4-REST-call demonstration (books + users + rentals + library) is sufficient to convey the over-fetching and multiple-request problem to the target audience without a strict N+1 pattern.**
   *Validation approach*: Review the tutorial narrative with a developer unfamiliar with GraphQL and confirm the dashboard's "request count" and "total bytes" panels communicate the intended lesson. If the N+1 framing is confusing, update `tutorial.html` to clarify that the demo shows over-fetching and request multiplicity, not classical N+1 per-record fetching.

5. **Assumption: Vanilla JS `fetch` with `Promise.all` parallelism is sufficient to make the REST panel visually slower (more requests) than the GraphQL panel, even on localhost where latency is near-zero.**
   *Validation approach*: Verify that request count and byte size metrics — not raw latency — are the primary "winner" indicators in the UI, since localhost timing differences will be negligible. Adjust the dashboard UI copy to emphasize request count and payload size over elapsed time if latency numbers are indistinguishable.

---

## Mitigations

**Risk 1 — `graph-gophers/graphql-go` API Compatibility**
- Implement `graphql.go` and run `go run .` as the first development task, before any other feature is built. Validate that the schema parses and the `dashboard` query returns data.
- Write `TestDashboardQuery` in `graphql_test.go` as the second task, immediately after the handler works, to lock in the resolver contract.
- Keep a reference to the `graph-gophers/graphql-go` example repository open during implementation to cross-check method naming conventions.

**Risk 2 — Tutorial Narrative Accuracy of N+1 Demonstration**
- Update `tutorial.html` and dashboard UI copy to explicitly describe the pattern as "over-fetching and request multiplicity" rather than "N+1 problem." Reserve the N+1 label for the section explaining what would happen if rentals were fetched one-by-one per user.
- Add a commented code block in `tutorial.html` showing the hypothetical N+1 loop (pseudocode) that GraphQL resolvers avoid, making the distinction concrete without implementing it.

**Risk 3 — Go Version Compatibility**
- Add `go 1.21` directive to `go.mod` (already implied by LLD; confirm it is set explicitly).
- Add a one-line note at the top of the README (or in `tutorial.html`) stating the minimum Go version requirement.

**Risk 4 — GraphQL Payload Size Comparison Reliability**
- In `integration_test.go`, hardcode the exact GraphQL query string used by the frontend and assert payload size against the `/library` response. Add a comment explaining that the test will need updating if the query scope changes.
- Document in the dashboard UI that the comparison assumes a partial-field GraphQL query; if users modify the query to request all fields, the size advantage disappears.

**Risk 5 — CORS Wildcard in Production Misuse**
- Add a comment in `main.go` adjacent to the CORS middleware: `// TUTORIAL ONLY: Do not use Access-Control-Allow-Origin: * in production.`
- Reference this in `tutorial.html` as a deliberate simplification with an explanation of why it is unsafe for real services.

**Risk 6 — `embed.FS` Path Resolution**
- Add a startup log line confirming the static file embed succeeded (e.g., list embedded file count via `fs.ReadDir`).
- Test `go run .` from both the `library-tutorial/` directory and the repo root to confirm behavior and document the correct invocation path in the tutorial.

**Risk 7 — Tutorial Page Code Snippet Drift**
- Add a `// Tutorial snippet — keep in sync with tutorial.html` comment above each function block referenced in the tutorial (`newGraphQLHandler`, resolver methods, `withCORS`).
- Optionally add a `TestTutorialSnippets` integration test that reads `tutorial.html` and asserts that key function signature strings are present in the file, catching gross divergence without full synchronization tooling.

---

## Appendix: Plan Documents

### PRD
# Product Requirements Document: Tutorial website on graphql API for a library with mock data

I want a simple endpoint that demonstrates why one wouldn't  use /books /users /library /rentals - or whatever - want all REST endpoints to exist but then demonstrate why a graphQL is better. please use Go as the language of choice for the API but I want to see if something (a dashboard?) was consuming the API, why a graphql endpoint is better. the website should show a comparison of loading each endpoint on one URL compares to using GraphQL on another endpoint.

**Created:** 2026-02-18T19:49:04Z
**Status:** Draft

## 1. Overview

**Concept:** Tutorial website on graphql API for a library with mock data

I want a simple endpoint that demonstrates why one wouldn't  use /books /users /library /rentals - or whatever - want all REST endpoints to exist but then demonstrate why a graphQL is better. please use Go as the language of choice for the API but I want to see if something (a dashboard?) was consuming the API, why a graphql endpoint is better. the website should show a comparison of loading each endpoint on one URL compares to using GraphQL on another endpoint.

**Description:** Tutorial website on graphql API for a library with mock data

I want a simple endpoint that demonstrates why one wouldn't  use /books /users /library /rentals - or whatever - want all REST endpoints to exist but then demonstrate why a graphQL is better. please use Go as the language of choice for the API but I want to see if something (a dashboard?) was consuming the API, why a graphql endpoint is better. the website should show a comparison of loading each endpoint on one URL compares to using GraphQL on another endpoint.

---

## 2. Goals

- **G-1:** Build a Go-based API server exposing both REST endpoints (`/books`, `/users`, `/rentals`, `/library`) and a single `/graphql` endpoint with identical mock data.
- **G-2:** Create a comparison dashboard (HTML/JS) that visually shows the number of HTTP requests, response payload size, and latency for REST vs GraphQL when loading the same library dashboard view.
- **G-3:** Demonstrate the N+1 problem and over-fetching issues with REST by showing raw request waterfalls side-by-side with a single GraphQL query result.
- **G-4:** Provide annotated, readable code so the site serves as a self-contained tutorial for developers learning GraphQL trade-offs.

---

## 3. Non-Goals

- **NG-1:** Production authentication, authorization, or user management — this is a tutorial with mock data only.
- **NG-2:** Rewriting or replacing the existing Python/Flask REST API — the Go server is a parallel, standalone tutorial artifact.
- **NG-3:** Persistent storage or database integration — all data is in-memory mock data.
- **NG-4:** Full CRUD operations — read-only endpoints are sufficient to demonstrate the comparison.
- **NG-5:** Mobile-optimized UI or accessibility compliance beyond basic HTML semantics.

---

## 4. User Stories

- **US-1:** As a developer learning GraphQL, I want to see REST vs GraphQL side-by-side so I understand why GraphQL reduces over-fetching.
- **US-2:** As a developer, I want to trigger the REST dashboard load and see all individual HTTP requests so I can observe the N+1 problem in action.
- **US-3:** As a developer, I want to trigger the GraphQL dashboard load and see a single request returning only the needed fields so I can compare directly.
- **US-4:** As a developer, I want to see request count, payload size, and timing metrics displayed so the performance difference is quantified.
- **US-5:** As a developer, I want to browse the Go source code annotations on the page so I understand how the GraphQL resolver is structured.
- **US-6:** As a tutorial reader, I want the comparison to auto-run on page load so I see live results without manual setup.

---

## 5. Acceptance Criteria

**US-2 (REST load):**
- Given the dashboard page loads, when the REST panel runs, then it fires separate requests to `/books`, `/users`, `/rentals` and displays each response payload.

**US-3 (GraphQL load):**
- Given the dashboard page loads, when the GraphQL panel runs, then it fires exactly one POST to `/graphql` returning only requested fields.

**US-4 (Metrics):**
- Given both panels have completed, then request count, total bytes, and elapsed ms are shown for each side with a clear winner indicator.

**US-6 (Auto-run):**
- Given a user navigates to the dashboard URL, then both REST and GraphQL comparisons execute automatically without user interaction.

---

## 6. Functional Requirements

- **FR-001:** Go HTTP server serves REST endpoints: `GET /books`, `GET /users`, `GET /rentals`, `GET /library` returning JSON mock data.
- **FR-002:** Go HTTP server serves `POST /graphql` using a Go GraphQL library (e.g., `graph-gophers/graphql-go`).
- **FR-003:** Mock data includes at least 5 books, 3 users, and 3 rentals with relational references (user IDs on rentals, book IDs on rentals).
- **FR-004:** GraphQL schema exposes a `dashboard` query returning books, users, and active rentals with nested relations in one request.
- **FR-005:** Frontend dashboard page (`/`) served by Go as static HTML with two side-by-side panels: REST waterfall and GraphQL single-request view.
- **FR-006:** Each panel displays: list of requests made, response payload (collapsed JSON), total request count, total bytes, and elapsed time.
- **FR-007:** CORS headers enabled on Go server so frontend can call API from same-origin or local dev.
- **FR-008:** A `/tutorial` page or section explains the N+1 problem and over-fetching with inline code examples from the actual Go source.

---

## 7. Non-Functional Requirements

### Performance
API responses must return in under 100ms (mock data, no DB). Dashboard comparison must complete both panels within 2 seconds on localhost.

### Security
No authentication required. No user input accepted beyond triggering the demo. No SQL or external calls — eliminates injection surface entirely.

### Scalability
Single-binary Go server; no scaling requirements. Tutorial artifact, not production workload.

### Reliability
Server must start with `go run .` or a single binary with no external dependencies beyond Go stdlib and chosen GraphQL library.

---

## 8. Dependencies

- **Go 1.21+** — primary language runtime
- **`graph-gophers/graphql-go`** or **`99designs/gqlgen`** — Go GraphQL server library
- **Vanilla HTML/CSS/JS** — frontend dashboard (no framework dependency)
- **Existing mock data concepts** from `api/data_store.py` (books, authors, members, loans) — reuse data shape in Go structs

---

## 9. Out of Scope

- Mutations (create, update, delete) via GraphQL or REST
- JWT authentication or any session management
- Database or external API integration
- Reuse or modification of existing Python/Flask API
- GraphQL subscriptions or real-time features
- Deployment infrastructure (Docker, CI/CD, cloud hosting)

---

## 10. Success Metrics

- **SM-1:** Dashboard visually shows REST making 3+ requests vs GraphQL making 1 request for equivalent data.
- **SM-2:** GraphQL payload bytes are measurably smaller than combined REST payloads for the same dashboard view.
- **SM-3:** A developer with no prior GraphQL experience can understand the trade-off within 5 minutes of visiting the page (validated by tutorial clarity and inline annotations).
- **SM-4:** Go server starts and runs with a single command; zero external services required.

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers

### HLD
# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-18T19:50:33Z
**Status:** Draft

## 1. Architecture Overview

Single-binary Go monolith serving both API and static frontend. No external services, databases, or build pipeline. The server embeds static HTML/JS files and handles all routes internally.

```
Browser
  ├── GET /          → static dashboard HTML (served by Go)
  ├── GET /tutorial  → static tutorial HTML (served by Go)
  ├── GET /books, /users, /rentals, /library  → REST handlers
  └── POST /graphql  → GraphQL handler
```

All mock data lives in Go structs initialized at startup. The frontend JavaScript makes fetch() calls to the same origin, measuring timing and payload size client-side.

---

## 2. System Components

| Component | Description |
|---|---|
| **Go HTTP Server** | `net/http` mux routing all requests; single binary entry point |
| **REST Handlers** | `GET /books`, `/users`, `/rentals`, `/library` — return full JSON mock payloads |
| **GraphQL Handler** | `POST /graphql` via `graph-gophers/graphql-go`; resolves `dashboard` query |
| **Mock Data Store** | In-memory Go structs: Books, Users, Rentals with cross-references |
| **Static File Server** | Embedded HTML/CSS/JS via `embed.FS`; serves `/` and `/tutorial` |
| **Dashboard UI** | Vanilla JS: fires REST calls + GraphQL query, collects metrics, renders panels |
| **Tutorial Page** | Static HTML with annotated Go source snippets explaining N+1 and over-fetching |

---

## 3. Data Model

```
Book        { ID, Title, Author, Genre, Year, ISBN, Available }
User        { ID, Name, Email, MemberSince }
Rental      { ID, UserID, BookID, RentedAt, DueAt, Returned }

Relations:
  Rental.UserID → User.ID
  Rental.BookID → Book.ID
```

Mock data: 5 books, 3 users, 3 rentals (2 active). Rentals carry nested Book and User fields in GraphQL resolvers (resolved in-memory, no DB queries). REST endpoints return flat collections — consumer must join client-side, demonstrating N+1.

---

## 4. API Contracts

**REST Endpoints**
```
GET /books      → [ { id, title, author, genre, year, isbn, available }, ... ]
GET /users      → [ { id, name, email, memberSince }, ... ]
GET /rentals    → [ { id, userId, bookId, rentedAt, dueAt, returned }, ... ]
GET /library    → { books: [...], users: [...], rentals: [...] }  // kitchen-sink
```

**GraphQL Endpoint**
```
POST /graphql
Content-Type: application/json

{ "query": "{ dashboard { books { id title author } users { id name } rentals { id rentedAt book { title } user { name } } } }" }

Response: { "data": { "dashboard": { books, users, rentals } } }
```

GraphQL returns only requested fields. REST always returns full objects. This delta is measured and displayed by the dashboard UI.

---

## 5. Technology Stack

### Backend
- **Go 1.21+** — standard library `net/http` for routing; `encoding/json` for serialization
- **`graph-gophers/graphql-go`** — schema-first GraphQL; lightweight, no codegen required
- **`embed`** package — bundle static files into single binary

### Frontend
- **Vanilla HTML5/CSS3/JS** — no framework; keeps tutorial dependencies minimal
- **Fetch API** — native browser HTTP client; `performance.now()` for timing
- **`TextEncoder`** — byte-accurate payload size measurement

### Infrastructure
- None. Single `go run .` or compiled binary. No containers, no reverse proxy.

### Data Storage
- In-memory Go structs initialized in `main.go`. No persistence layer.

---

## 6. Integration Points

None. The system is fully self-contained. The frontend calls the same-origin Go server. No third-party APIs, webhooks, CDNs, or external services.

CORS headers (`Access-Control-Allow-Origin: *`) are set to support local dev scenarios where frontend and server ports may differ during development.

---

## 7. Security Architecture

Minimal attack surface by design:

- **No authentication** — tutorial artifact, no sensitive data
- **No user input processed server-side** — GraphQL query is fixed in frontend JS; no dynamic query construction
- **Read-only resolvers** — no mutations; no state change possible
- **No external calls** — eliminates SSRF surface entirely
- **CORS open** — acceptable for local tutorial; documented as not-for-production

---

## 8. Deployment Architecture

```
Developer machine
└── go run .   (or)   ./library-tutorial
      └── Listens on :8080
            ├── Serves embedded static files
            └── Handles API routes
```

No Docker, no CI/CD, no cloud deployment. Distribution is a single compiled Go binary or `go run .` from source. `go.mod` + `go.sum` define the only dependency (`graph-gophers/graphql-go`).

---

## 9. Scalability Strategy

Not applicable. This is a single-developer tutorial artifact with in-memory data. No horizontal or vertical scaling is needed or designed for. If repurposed, the stateless handler design supports running multiple instances behind a load balancer trivially — but that is out of scope.

---

## 10. Monitoring & Observability

No production monitoring required. For tutorial purposes:

- **Server-side**: `log.Printf` on startup showing listen address and routes registered
- **Client-side**: Dashboard UI displays real-time metrics (request count, bytes, ms) as the tutorial's own "observability" demonstration
- **Error display**: GraphQL and fetch errors surfaced in UI panels, not silently swallowed

---

## 11. Architectural Decisions (ADRs)

**ADR-1: Single Go binary, no framework**
Go stdlib `net/http` is sufficient. Adding Gin/Echo adds dependency weight with no benefit for 4 routes. Keeps `go run .` start simple.

**ADR-2: `graph-gophers/graphql-go` over `gqlgen`**
Schema-first without codegen. Simpler to annotate for tutorial purposes. `gqlgen` requires a generation step that obscures the resolver structure from learners.

**ADR-3: Frontend measures its own metrics**
Client-side `performance.now()` and `TextEncoder.encode(json).byteLength` give accurate, browser-observable numbers. Server-side timing would require custom headers and added complexity.

**ADR-4: `embed.FS` for static files**
Keeps single-binary guarantee. No file path assumptions at runtime. Tutorial users don't need to manage a `static/` directory separately.

**ADR-5: `/library` endpoint as "kitchen-sink" REST**
Mirrors what a developer might build to avoid N+1 — a mega-endpoint. Used in the tutorial to show that this solution has its own trade-offs (over-fetching all fields regardless of need), setting up the GraphQL argument.

---

## Appendix: PRD Reference

See PRD: *Tutorial website on graphql API for a library with mock data* (2026-02-18)

### LLD
# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-18T19:51:37Z
**Status:** Draft

## 1. Implementation Overview

Self-contained Go module in `library-tutorial/` directory. Single binary serving embedded static files and all API routes. No database, no build pipeline. `go run .` starts the server on `:8080`. The tutorial contrasts REST (N+1, over-fetching) with GraphQL (precise field selection) using identical in-memory mock data.

---

## 2. File Structure

```
library-tutorial/
  main.go           # HTTP server, route registration, embed directive
  data.go           # Mock data structs and initialization
  handlers.go       # REST handlers: /books, /users, /rentals, /library
  graphql.go        # Schema definition, resolver types, GraphQL handler
  go.mod            # module declaration + graph-gophers/graphql-go dep
  go.sum            # dependency checksums
  static/
    index.html      # Dashboard UI (vanilla JS, fetch + performance.now)
    tutorial.html   # Static tutorial with annotated code snippets
    style.css       # Shared minimal styles
```

New directory; no existing repo files modified.

---

## 3. Detailed Component Designs

### 3.1 Mock Data (`data.go`)

```go
type Book   struct { ID, Title, Author, Genre string; Year int; ISBN string; Available bool }
type User   struct { ID, Name, Email, MemberSince string }
type Rental struct { ID, UserID, BookID, RentedAt, DueAt string; Returned bool }

var Books   = []Book{...}   // 5 entries
var Users   = []User{...}   // 3 entries
var Rentals = []Rental{...} // 3 entries (2 active)
```

### 3.2 REST Handlers (`handlers.go`)

Each handler serializes the relevant slice to JSON. `/library` combines all three. CORS header set on every response via middleware wrapper.

### 3.3 GraphQL (`graphql.go`)

Schema defined as a raw string constant. Three resolver types: `QueryResolver`, `DashboardResolver`, `RentalResolver`. `RentalResolver` joins Book/User in-memory by ID — demonstrating the resolver pattern without N+1 (single pass through slices).

### 3.4 Dashboard UI (`static/index.html`)

On load, fires 4 fetch calls (books, users, rentals, library) and 1 GraphQL POST. Uses `performance.now()` for latency and `TextEncoder.encode(JSON.stringify(body)).byteLength` for payload size. Renders results in side-by-side panels.

### 3.5 Tutorial Page (`static/tutorial.html`)

Static HTML with `<pre><code>` blocks showing annotated Go source for N+1 problem, over-fetching pattern, and GraphQL resolver. No JS required.

---

## 4. Database Schema Changes

None. All data is in-memory Go structs initialized at process start. No migration scripts required.

---

## 5. API Implementation Details

**CORS middleware** — wraps all handlers; sets `Access-Control-Allow-Origin: *`.

**GET /books**
- Returns `json.Marshal(data.Books)`
- Status 200; Content-Type: application/json

**GET /users**
- Returns `json.Marshal(data.Users)`

**GET /rentals**
- Returns `json.Marshal(data.Rentals)` (flat, no joins)

**GET /library**
- Returns `json.Marshal(struct{ Books, Users, Rentals }{...})`
- Kitchen-sink endpoint demonstrating over-fetching

**POST /graphql**
- Reads body into `{"query": "..."}` struct
- Delegates to `graphql.Handler` from `graph-gophers/graphql-go`
- Fixed schema; no introspection restrictions needed

**GET /** → serve `static/index.html` from `embed.FS`
**GET /tutorial** → serve `static/tutorial.html` from `embed.FS`
**GET /style.css** → serve `static/style.css` from `embed.FS`

---

## 6. Function Signatures

```go
// main.go
func main()
func withCORS(h http.HandlerFunc) http.HandlerFunc

// handlers.go
func booksHandler(w http.ResponseWriter, r *http.Request)
func usersHandler(w http.ResponseWriter, r *http.Request)
func rentalsHandler(w http.ResponseWriter, r *http.Request)
func libraryHandler(w http.ResponseWriter, r *http.Request)
func writeJSON(w http.ResponseWriter, v any)

// graphql.go
func newGraphQLHandler() http.HandlerFunc

// Resolver types
type QueryResolver struct{}
type DashboardResolver struct{}
type RentalResolver struct{ rental data.Rental }

func (r *QueryResolver)    Dashboard() *DashboardResolver
func (r *DashboardResolver) Books()   []*BookResolver
func (r *DashboardResolver) Users()   []*UserResolver
func (r *DashboardResolver) Rentals() []*RentalResolver
func (r *RentalResolver)   Book()    *BookResolver
func (r *RentalResolver)   User()    *UserResolver
```

---

## 7. State Management

No runtime state mutation. All mock data is package-level `var` slices in `data.go`, initialized once at startup. Handlers are pure read-only functions. No session state, no caching layer.

---

## 8. Error Handling Strategy

| Scenario | Behavior |
|---|---|
| Invalid HTTP method on REST | `405 Method Not Allowed` |
| GraphQL parse error | `graph-gophers` returns `{"errors":[...]}` with 200 (GraphQL spec) |
| `json.Marshal` failure | `500` + `log.Printf` (cannot occur with fixed structs) |
| Unknown route | Default mux 404 |

Dashboard UI: each fetch call wrapped in `try/catch`; errors rendered in the relevant panel as red text. GraphQL errors checked in `data.errors` field of response.

---

## 9. Test Plan

### Unit Tests

`library-tutorial/handlers_test.go`
- `TestBooksHandler` — httptest.NewRecorder, assert 200 + valid JSON array of 5 books
- `TestUsersHandler` — assert 3 users returned
- `TestRentalsHandler` — assert 3 rentals, flat (no nested book/user fields)
- `TestLibraryHandler` — assert response contains books/users/rentals keys

`library-tutorial/graphql_test.go`
- `TestDashboardQuery` — POST full dashboard query, assert nested book title in rental
- `TestPartialFieldQuery` — query only `books { id title }`, assert author field absent
- `TestRentalJoin` — assert rental resolver returns correct book/user by ID

### Integration Tests

`library-tutorial/integration_test.go`
- Start `httptest.NewServer(mux)`, hit all 5 endpoints, assert CORS header present
- Verify GraphQL payload smaller than `/library` response (over-fetching demo)

### E2E Tests

Manual browser verification only (no headless browser tooling to keep zero-dependency goal):
- Open `http://localhost:8080` — confirm all 5 panels populate with metrics
- Open `http://localhost:8080/tutorial` — confirm code snippets render correctly

---

## 10. Migration Strategy

New isolated directory `library-tutorial/` added to existing repo root. No existing files touched. Run:

```bash
cd library-tutorial
go mod tidy
go run .
```

The existing repo's Python/JS ecosystem is unaffected.

---

## 11. Rollback Plan

Delete `library-tutorial/` directory. No shared dependencies, no database changes, no modified files — rollback is a single directory removal with no side effects.

---

## 12. Performance Considerations

- **Startup**: Sub-millisecond; 5+3+3 structs initialized inline.
- **Request latency**: All handlers are memory reads + JSON marshal. Expected <1ms server-side for tutorial data volumes.
- **Binary size**: Single binary ~8MB (Go runtime + one dependency). `embed.FS` adds ~10KB for static files.
- **Concurrency**: `net/http` handles concurrent requests; handlers are stateless and goroutine-safe (read-only data).
- No caching, pooling, or optimization needed at tutorial scale.

---

## Appendix: Existing Repository Structure

The new `library-tutorial/` Go module is added as a standalone subdirectory. It has its own `go.mod` and does not interact with the existing Python API, React frontend, or any other component in the repository.