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