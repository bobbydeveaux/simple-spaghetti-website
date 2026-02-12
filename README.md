# Simple Spaghetti Website

## Python Authentication API

This branch contains a complete Python authentication API built with FastAPI, featuring secure user registration, login, and JWT token management.

### Features

- ✅ **Secure Authentication**: JWT-based authentication with access and refresh tokens
- ✅ **Password Security**: bcrypt hashing with 12 rounds for secure password storage
- ✅ **Input Validation**: Comprehensive email and password validation
- ✅ **Thread-Safe Storage**: In-memory user repository with concurrent access support
- ✅ **CORS Protection**: Environment-specific CORS configuration
- ✅ **Comprehensive Testing**: Full test suite covering all functionality
- ✅ **Production Ready**: Secure configuration management with environment variables

### API Endpoints

- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User authentication
- `POST /api/v1/auth/refresh` - Token refresh
- `GET /api/v1/auth/profile` - Get user profile (protected)
- `GET /api/v1/auth/protected` - Example protected endpoint

### Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export JWT_SECRET="your-secure-jwt-secret-key-here"
   export ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8080"
   export DEBUG="false"
   ```

3. **Run the API:**
   ```bash
   uvicorn api.main:app --reload
   ```

4. **Access API documentation:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Security Requirements

- **JWT_SECRET**: Must be set via environment variable (no default in production)
- **CORS Origins**: Configurable per environment
- **Password Policy**: Minimum 8 chars, letters + digits required
- **Token Expiry**: Access tokens (15 min), Refresh tokens (7 days)

### Documentation

- [Authentication API Documentation](docs/authentication-api.md) - Complete API reference
- [PRD](docs/PRD.md) - Original product requirements
- [Architecture](docs/architecture.md) - System design and patterns

### Testing

Run the comprehensive test suite:
```bash
python -m pytest tests/ -v
```

Tests cover:
- Password hashing and verification
- JWT token operations and security
- User model validation
- Authentication routes and error handling
- Security requirements compliance
