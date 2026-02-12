# Python Authentication API Documentation

## Overview

This document describes the Python Authentication API built with FastAPI. The API provides secure user authentication using JWT tokens with bcrypt password hashing.

## Security Features

- **Password Hashing**: Uses bcrypt with 12 rounds for secure password storage
- **JWT Tokens**: Separate access and refresh tokens for secure authentication
- **Email Validation**: Comprehensive regex validation for email addresses
- **Password Requirements**: Enforces strong password policies
- **CORS Protection**: Environment-specific CORS configuration
- **Environment Variables**: Secure configuration management

## Environment Setup

### Required Environment Variables

```bash
# REQUIRED: JWT Secret Key (minimum 32 characters recommended)
JWT_SECRET=your-secure-jwt-secret-key-here

# OPTIONAL: CORS allowed origins (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# OPTIONAL: Debug mode
DEBUG=false
```

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (create `.env` file):
```bash
JWT_SECRET=your-secure-jwt-secret-key-here
ALLOWED_ORIGINS=http://localhost:3000
DEBUG=false
```

3. Run the application:
```bash
uvicorn api.main:app --reload
```

## API Endpoints

### Base URL
```
http://localhost:8000/api/v1/auth
```

### 1. User Registration

**POST** `/register`

Register a new user with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one letter
- At least one digit

**Success Response (201):**
```json
{
  "email": "user@example.com",
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Error Responses:**
- `400`: User already exists or validation error
- `422`: Invalid input format

### 2. User Login

**POST** `/login`

Authenticate user and receive JWT tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401`: Invalid email or password
- `422`: Invalid input format

### 3. Refresh Tokens

**POST** `/refresh`

Get new access and refresh tokens using a valid refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401`: Invalid or expired refresh token

### 4. User Profile

**GET** `/profile`

Get current user's profile information. Requires authentication.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "email": "user@example.com",
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Error Responses:**
- `401`: Invalid or expired token
- `403`: Missing authorization header
- `404`: User not found

### 5. Protected Endpoint (Example)

**GET** `/protected`

Example protected endpoint that requires authentication.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "message": "Hello user@example.com, this is a protected endpoint!",
  "user": "user@example.com"
}
```

**Error Responses:**
- `401`: Invalid or expired token
- `403`: Missing authorization header

## Authentication Flow

### Registration Flow
1. User submits email and password to `/register`
2. Server validates input and checks for existing user
3. Password is hashed using bcrypt (12 rounds)
4. User is stored in repository
5. User information (excluding password) is returned

### Login Flow
1. User submits credentials to `/login`
2. Server validates email and verifies password hash
3. Server generates access token (15 minutes) and refresh token (7 days)
4. Tokens are returned to client

### Token Usage
1. Client includes access token in `Authorization: Bearer <token>` header
2. Server validates token on protected endpoints
3. When access token expires, client uses refresh token to get new tokens

### Token Refresh Flow
1. Client submits refresh token to `/refresh`
2. Server validates refresh token
3. New access and refresh tokens are generated and returned

## Token Configuration

### Access Tokens
- **Expiry**: 15 minutes
- **Type**: `access`
- **Usage**: API authentication

### Refresh Tokens
- **Expiry**: 7 days
- **Type**: `refresh`
- **Usage**: Token renewal only

## Security Considerations

### Password Security
- Passwords are hashed using bcrypt with 12 rounds
- Plain text passwords are never stored
- Password requirements enforce basic security

### JWT Security
- Tokens are signed with HS256 algorithm
- Secret key must be set via environment variable
- No default secret key in production

### CORS Security
- Development: Allows all origins (`*`) when `DEBUG=true`
- Production: Restricted to specific origins from `ALLOWED_ORIGINS`

## Data Models

### User (Internal)
```python
@dataclass
class User:
    email: str
    password_hash: str
    created_at: datetime
```

### Request/Response Models
- `RegisterRequest`: Email + password
- `LoginRequest`: Email + password
- `RefreshRequest`: Refresh token
- `UserResponse`: Email + created_at (no password)
- `TokenResponse`: Access token + refresh token + type

## Error Handling

All errors return JSON responses with appropriate HTTP status codes:

```json
{
  "detail": "Error description"
}
```

Common error patterns:
- `400`: Bad request (validation, duplicate user)
- `401`: Authentication failed
- `403`: Missing authorization
- `404`: Resource not found
- `422`: Invalid input format
- `500`: Internal server error

## Testing

Comprehensive test suite covers:
- Password hashing utilities
- JWT token operations
- User model validation
- Authentication routes
- Security requirements
- Error handling

Run tests with:
```bash
python -m pytest tests/ -v
```

## Development Notes

### Repository Pattern
- In-memory user storage for development/testing
- Thread-safe operations with locking
- Suitable for up to ~1000 users

### Configuration
- Environment-based configuration
- Required vs. optional settings
- Development vs. production modes

### Extensibility
- Modular design with separate services
- Easy to swap storage backends
- Pluggable authentication middleware