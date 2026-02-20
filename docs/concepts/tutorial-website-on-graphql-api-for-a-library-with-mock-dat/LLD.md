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