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