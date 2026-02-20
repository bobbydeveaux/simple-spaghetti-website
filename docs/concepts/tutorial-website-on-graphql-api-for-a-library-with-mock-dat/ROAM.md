# ROAM Analysis: tutorial-website-on-graphql-api-for-a-library-with-mock-dat

**Feature Count:** 7
**Created:** 2026-02-18T20:46:12Z
**Refined:** 2026-02-18

## Risks

1. **`graph-gophers/graphql-go` API Compatibility** (Medium): The schema-first resolver pattern in `graph-gophers/graphql-go` requires method signatures to match exported field names exactly (e.g., `Books()`, `Users()`). A mismatch between schema field names and Go method names causes a runtime panic at schema parse time, not a compile-time error. This could delay the GraphQL feature and tests if the resolver wiring is not validated early. The LLD defines five resolver types (`QueryResolver`, `DashboardResolver`, `RentalResolver`, `BookResolver`, `UserResolver`) — each with its own method surface, increasing the number of potential mismatch points.

2. **Tutorial Narrative Accuracy of the N+1 Demonstration** (Medium): The dashboard fires 4 REST calls (`/books`, `/users`, `/rentals`, `/library`) but the true N+1 problem emerges when fetching nested relations per-record (e.g., one request per rental to resolve its book). With flat endpoints and client-side joining, the demo shows over-fetching and request count, but does not strictly demonstrate N+1 in its classical form. This risks misleading learners about what N+1 actually is.

3. **Go Version Compatibility with `embed` Directive** (Low): `//go:embed` requires Go 1.16+; the LLD targets Go 1.21+. If a developer has an older toolchain, the server will fail to compile with an opaque error. No toolchain version enforcement exists in the plan beyond a `go.mod` directive.

4. **GraphQL Payload Size Comparison Reliability** (Low): The integration test asserts that the GraphQL payload is smaller than the `/library` response. This holds only when the dashboard query requests a subset of fields. If the query is later expanded to request all fields, the test will fail or the tutorial's core claim becomes false. The comparison is sensitive to the exact GraphQL query string used in the frontend.

5. **CORS Configuration Scope Creep into Production Use** (Low): The design documents `Access-Control-Allow-Origin: *` as acceptable for a tutorial. If the repo is used as a starting point for a real service, the open CORS policy will be copied without review. The risk is low for this artifact but medium for downstream misuse.

6. **`embed.FS` Path Resolution for Static Files** (Medium): The `//go:embed static` directive in `main.go` requires the `static/` directory to be at the correct path relative to `main.go` at compile time. If the module is run from a different working directory or the embed path is misconfigured, the server compiles but serves 404s for all static routes — a non-obvious failure mode for tutorial users running `go run .` from a parent directory.

7. **Tutorial Page Code Snippet Drift** (Low): `tutorial.html` contains hardcoded Go source snippets copied from the actual implementation. If `graphql.go` or `handlers.go` are modified after initial implementation, the tutorial snippets will silently diverge from the real code, undermining the tutorial's accuracy. There is no automated check to detect this drift.

8. **`BookResolver` and `UserResolver` Completeness** (Low): The epic description and LLD function signatures both list `BookResolver` and `UserResolver` as resolver types required by `DashboardResolver.Books()` and `DashboardResolver.Users()`. These types are referenced but their field methods (e.g., `ID()`, `Title()`, `Author()` on `BookResolver`) are not enumerated in the LLD. Missing or incomplete field resolver methods will cause runtime panics when those fields are requested via GraphQL.

---

## Obstacles

- **No Go toolchain version pinned in the repository**: The plan specifies Go 1.21+ in prose but there is no `go.toolchain` directive or `.go-version` file. A developer with Go 1.16–1.20 will encounter subtle behavioral differences (e.g., `any` type alias availability, `net/http` behavior changes) without a clear error message pointing to the version requirement.

- **`graph-gophers/graphql-go` requires exact method-to-field name matching verified only at runtime**: Unlike `gqlgen`, which generates type-safe resolver stubs, `graph-gophers/graphql-go` panics at startup if resolver methods do not match the schema. There is no compile-time validation, meaning the GraphQL endpoint cannot be confirmed working until the server is actually started — a potential blocker during initial development if the schema and resolvers are built separately.

- **No CI or automated build verification defined**: The plan explicitly excludes deployment infrastructure and CI/CD. This means there is no automated gate to catch a broken `go build`, failing tests, or embed path issues before the tutorial is shared. Breakage will only surface when a user manually runs the project.

- **Tutorial HTML requires manual synchronization with Go source**: There is no tooling (e.g., a `go generate` step or test asserting snippet content) to keep `tutorial.html` code blocks consistent with `graphql.go` and `handlers.go`. This is a manual process with no safety net.

- **`go.sum` must be committed and kept in sync**: The epic lists `go.sum` as a tracked file. If `go mod tidy` is not run after any dependency change (or if `go.sum` is absent on a fresh clone), the build will fail. Tutorial users following the `go run .` path may not know to run `go mod tidy` first.

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

6. **Assumption: All five resolver types (`QueryResolver`, `DashboardResolver`, `RentalResolver`, `BookResolver`, `UserResolver`) can be implemented with their full field method sets without undocumented constraints in `graph-gophers/graphql-go`.**
   *Validation approach*: Verify each resolver type against the library's documented method conventions during the `graphql.go` implementation session. Run `TestDashboardQuery` and `TestPartialFieldQuery` against all five resolver types before marking the GraphQL endpoint feature complete.

---

## Mitigations

**Risk 1 — `graph-gophers/graphql-go` API Compatibility**
- Implement `graphql.go` and run `go run .` as the first development task, before any other feature is built. Validate that the schema parses and the `dashboard` query returns data.
- Write `TestDashboardQuery` in `graphql_test.go` as the second task, immediately after the handler works, to lock in the resolver contract.
- Keep a reference to the `graph-gophers/graphql-go` example repository open during implementation to cross-check method naming conventions.
- Enumerate all field methods for `BookResolver` and `UserResolver` in the implementation notes before writing code, to prevent the gap identified in Risk 8.

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

**Risk 8 — `BookResolver` and `UserResolver` Completeness**
- Before writing any resolver code, define the complete set of field methods required by the GraphQL schema for both `BookResolver` (e.g., `ID()`, `Title()`, `Author()`, `Genre()`, `Year()`, `ISBN()`, `Available()`) and `UserResolver` (e.g., `ID()`, `Name()`, `Email()`, `MemberSince()`).
- Include these method signatures in the LLD or implementation notes so they are not discovered piecemeal at runtime.

**Obstacle — `go.sum` sync**
- Include `go mod tidy && go run .` as the documented startup sequence in `tutorial.html` and any README snippet, so first-time users do not encounter missing checksum errors.

---

## Appendix: Plan Documents

### PRD
See PRD: *Tutorial website on graphql API for a library with mock data* (2026-02-18)

### HLD
See HLD: *simple-spaghetti-repo* (2026-02-18)

### LLD
See LLD: *simple-spaghetti-repo* (2026-02-18)