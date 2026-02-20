# ROAM Analysis: a-simple-go-protobuf-api

**Feature Count:** 2
**Created:** 2026-02-17T20:51:51Z

## Risks

1. **Buf CLI Availability** (Low): Developers may not have Buf CLI installed or may have incompatible versions, blocking code generation workflow
2. **Connect-Go Version Compatibility** (Medium): Connect-Go library is relatively new and may have breaking changes between versions, potentially causing generated code incompatibilities
3. **Protobuf Syntax Errors** (Low): Manual editing of .proto files could introduce syntax errors that only surface during buf generate, blocking development
4. **Go Module Resolution** (Low): Incorrect go.mod configuration or import paths for generated code could prevent compilation
5. **Port Conflict** (Low): Port 8080 may already be in use on development machines, preventing server startup
6. **Generated Code Not Gitignored** (Medium): If gen/ directory is accidentally committed, could cause merge conflicts and repository bloat
7. **Missing Buf Configuration** (Medium): Incorrect buf.yaml or buf.gen.yaml configuration could generate code in wrong locations or with wrong package names

---

## Obstacles

- **Initial Toolchain Setup**: Developers need to install Go 1.21+, Buf CLI, and understand Protobuf workflow before starting implementation
- **Connect Documentation Gaps**: Connect (Buf) is newer than traditional gRPC, so developers may encounter limited examples or community resources
- **Code Generation Workflow**: Team must establish clear workflow for when to regenerate code (pre-commit, manual, CI) to avoid stale generated files
- **Local Testing Tools**: No specification for how to test the API (curl, Postman, custom client), which may slow validation

---

## Assumptions

1. **Development Environment**: Assuming developers have Go 1.21+ already installed and configured with proper GOPATH/module support - validate during environment setup
2. **Network Connectivity**: Assuming developers can reach go.pkg.dev and buf.build for dependency downloads - verify firewall/proxy settings don't block these
3. **Buf CLI Compatibility**: Assuming latest Buf CLI version (v1.x) is compatible with specified Connect-Go library version - verify through initial spike
4. **Import Path Convention**: Assuming generated code will use module path that matches go.mod declaration - validate with initial code generation test
5. **Empty Name Handling**: Assuming "Hello, !" is acceptable response for empty name input based on POC scope - confirm with stakeholder if validation needed

---

## Mitigations

### Risk 1: Buf CLI Availability
- Create installation documentation with curl/brew/apt commands for Buf CLI
- Add version check script that validates Buf CLI presence before build
- Include buf.lock file to pin exact Buf module versions

### Risk 2: Connect-Go Version Compatibility
- Pin exact Connect-Go version in go.mod (e.g., v1.14.0) rather than using version ranges
- Add comment in go.mod documenting tested Connect-Go version
- Test code generation immediately after dependency changes

### Risk 3: Protobuf Syntax Errors
- Configure buf lint with default rules in buf.yaml to catch syntax errors early
- Add buf breaking check to prevent accidental breaking changes to proto definitions
- Run buf generate as pre-commit hook or make target

### Risk 4: Go Module Resolution
- Use fully qualified import paths in go.mod matching buf.gen.yaml output
- Create Makefile with generate target that runs buf generate and go mod tidy
- Add sanity check build step after generation: go build ./...

### Risk 5: Port Conflict
- Make HTTP port configurable via environment variable (default 8080)
- Add startup error handling with clear message if port binding fails
- Document in README how to specify alternate port

### Risk 6: Generated Code Not Gitignored
- Add gen/ to .gitignore immediately during project setup
- Document in README that gen/ is generated and should not be committed
- Add CI check that fails if gen/ directory exists in commits

### Risk 7: Missing Buf Configuration
- Create buf.yaml and buf.gen.yaml before writing .proto files
- Validate buf configuration with buf mod update and buf build
- Use standard buf template configurations from official Connect-Go examples

---

## Appendix: Plan Documents

### PRD
# Product Requirements Document: A simple Go Protobuf API

I want to use Connect (Buf)  to create a POC Protobuf API - a simple hello {name} API is fine

**Created:** 2026-02-17T20:46:39Z
**Status:** Draft

## 1. Overview

**Concept:** A simple Go Protobuf API

I want to use Connect (Buf)  to create a POC Protobuf API - a simple hello {name} API is fine

**Description:** A simple Go Protobuf API

I want to use Connect (Buf)  to create a POC Protobuf API - a simple hello {name} API is fine

---

## 2. Goals

- Create a working proof-of-concept Go service using Connect (Buf) framework
- Implement a single "hello {name}" API endpoint that accepts a name parameter and returns a greeting
- Successfully generate Go code from Protobuf definitions using Buf tooling

---

## 3. Non-Goals

- Production-ready authentication or authorization
- Complex business logic or multiple service endpoints
- Deployment infrastructure or containerization
- Performance optimization or load testing

---

## 4. User Stories

- As a developer, I want to send a name to the API so that I receive a personalized greeting response
- As a developer, I want to use Protobuf definitions so that I have type-safe API contracts

---

## 5. Acceptance Criteria

- Given a valid name string, When I call the hello endpoint, Then I receive a greeting message containing that name
- Given the Protobuf schema, When I run Buf generation, Then valid Go code is created without errors

---

## 6. Functional Requirements

- FR-001: API accepts a name parameter as input via Protobuf message
- FR-002: API returns a greeting message in format "Hello, {name}!" via Protobuf response

---

## 7. Non-Functional Requirements

### Performance
Basic response time under 100ms for local requests

### Security
Accept any input for POC purposes

### Scalability
Single instance sufficient for POC

### Reliability
Service runs without crashes for basic happy-path requests

---

## 8. Dependencies

- Go 1.21+
- Buf CLI for Protobuf code generation
- Connect-Go library (connectrpc.com/connect)

---

## 9. Out of Scope

- Error handling beyond basic cases
- Multiple endpoints or services
- Database integration
- Production deployment

---

## 10. Success Metrics

- Service starts successfully and accepts requests
- API returns correct greeting for provided names

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers

### HLD
# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-17T20:48:31Z
**Status:** Draft

## 1. Architecture Overview

Single-process monolith HTTP server written in Go, exposing a Connect-compatible Protobuf API endpoint.

---

## 2. System Components

- **Greeter Service**: Single service implementing the hello endpoint
- **HTTP Server**: Connect-Go HTTP handler serving the Protobuf API

---

## 3. Data Model

- **HelloRequest**: Message with single `name` field (string)
- **HelloResponse**: Message with single `greeting` field (string)

---

## 4. API Contracts

**Endpoint**: `/greet.v1.GreeterService/SayHello`
- Request: `{ "name": "string" }`
- Response: `{ "greeting": "Hello, {name}!" }`
- Protocol: Connect (HTTP/JSON or binary Protobuf)

---

## 5. Technology Stack

### Backend
Go 1.21+, Connect-Go (connectrpc.com/connect), Buf for code generation

### Frontend
N/A (API only)

### Infrastructure
Local development only

### Data Storage
None (stateless service)

---

## 6. Integration Points

None (standalone POC)

---

## 7. Security Architecture

No authentication or authorization (POC only)

---

## 8. Deployment Architecture

Single binary run locally via `go run` or compiled executable

---

## 9. Scalability Strategy

Not applicable for POC

---

## 10. Monitoring & Observability

Standard output logging only

---

## 11. Architectural Decisions (ADRs)

**ADR-001**: Use Connect over gRPC - simpler setup, HTTP/JSON compatibility
**ADR-002**: No persistence layer - POC requires no state

---

## Appendix: PRD Reference

[PRD content omitted for brevity]

### LLD
# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-17T20:49:31Z
**Status:** Draft

## 1. Implementation Overview

Standalone Go module with Protobuf definitions, generated Connect service stubs, and a basic HTTP server. Uses Buf for code generation and Connect-Go for the RPC framework.

---

## 2. File Structure

```
go-greeter/
  buf.gen.yaml         # Buf code generation config
  buf.yaml             # Buf workspace config
  go.mod               # Go module dependencies
  main.go              # HTTP server entrypoint
  proto/greeter/v1/greeter.proto  # Protobuf service definition
  gen/                 # Generated code (gitignored)
```

---

## 3. Detailed Component Designs

**Protobuf Service**: Define `GreeterService` with `SayHello` RPC in `proto/greeter/v1/greeter.proto`

**Service Handler**: Implement `GreeterServiceHandler` in `main.go` with `SayHello(context.Context, *connect.Request[v1.HelloRequest]) (*connect.Response[v1.HelloResponse], error)`

**HTTP Server**: Create `http.Server` listening on `:8080`, mount Connect handler at `/greet.v1.GreeterService/`

---

## 4. Database Schema Changes

N/A - stateless service

---

## 5. API Implementation Details

**Endpoint**: `POST /greet.v1.GreeterService/SayHello`
- Parse `name` from request body
- Return `{"greeting": "Hello, <name>!"}`
- Log request to stdout

---

## 6. Function Signatures

```go
func (s *greeterServer) SayHello(ctx context.Context, req *connect.Request[v1.HelloRequest]) (*connect.Response[v1.HelloResponse], error)
func main()
```

---

## 7. State Management

No state - all responses generated from request data

---

## 8. Error Handling Strategy

Return Connect errors for invalid input; standard library HTTP errors for server issues

---

## 9. Test Plan

### Unit Tests
Test `SayHello` handler with sample inputs

### Integration Tests
N/A for POC

### E2E Tests
N/A for POC

---

## 10. Migration Strategy

Net-new implementation in separate directory; no migration needed

---

## 11. Rollback Plan

Delete `go-greeter/` directory

---

## 12. Performance Considerations

None required for POC

---

## Appendix: Existing Repository Structure

[Existing structure omitted - POC lives in isolated directory]