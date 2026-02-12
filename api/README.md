# Python Auth API

FastAPI-based authentication API with JWT token management.

## Setup and Installation

1. **Install Python 3.9+**
   ```bash
   # Verify Python installation
   python3 --version
   ```

2. **Install dependencies**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Set environment variables** (optional)
   ```bash
   export JWT_SECRET_KEY="your-secure-secret-key"
   export ACCESS_TOKEN_EXPIRE_MINUTES=15
   export REFRESH_TOKEN_EXPIRE_DAYS=7
   export CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
   ```

## Running the Application

There are multiple ways to start the FastAPI development server:

### Option 1: Using uvicorn directly
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 2: Running as a Python module
```bash
python3 -m api
```

### Option 3: Using the run script
```bash
python3 run.py
```

### Option 4: Direct execution
```bash
python3 api/main.py
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Core Infrastructure Endpoints

- `GET /` - Root endpoint with basic information
- `GET /health` - Health check endpoint

### Future Endpoints (Next Sprints)

- `POST /register` - User registration
- `POST /login` - User authentication
- `POST /refresh` - Token refresh
- `GET /protected` - Protected endpoint requiring JWT

## Configuration

The application uses environment variables for configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | Secret key for JWT signing | `your-secret-key-change-this-in-production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiry in minutes | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry in days | `7` |
| `CORS_ORIGINS` | Comma-separated CORS origins | `http://localhost:3000,http://localhost:5173` |
| `PASSWORD_HASH_ROUNDS` | bcrypt hash rounds | `12` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |

## Project Structure

```
api/
├── __init__.py              # Package initializer
├── __main__.py              # Entry point for module execution
├── main.py                  # FastAPI app initialization, CORS, exception handlers
├── config.py                # Environment variables, JWT secret, token expiry
├── routes/                  # API endpoints (future sprints)
├── services/                # Business logic and repositories (future sprints)
├── models/                  # Data models and schemas (future sprints)
├── utils/                   # JWT and password utilities (future sprints)
├── middleware/              # Authentication middleware (future sprints)
└── README.md               # This file

requirements.txt             # Python dependencies
run.py                       # Simple execution script
```

## Development

### Testing the Setup

1. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

2. Start the server (any of the methods above):
   ```bash
   uvicorn api.main:app --reload
   # OR
   python3 -m api
   # OR
   python3 run.py
   ```

3. Test endpoints:
   ```bash
   # Health check
   curl http://localhost:8000/health

   # Root endpoint
   curl http://localhost:8000/
   ```

4. View interactive documentation at http://localhost:8000/docs

### CORS Configuration

The API is configured to accept requests from:
- `http://localhost:3000` (typical React development server)
- `http://localhost:5173` (Vite development server)

## Next Steps

This implementation covers Sprint 1 - Core Infrastructure Setup. Upcoming sprints will add:

1. **Sprint 2**: Authentication endpoints (`/register`, `/login`, `/refresh`)
2. **Sprint 3**: Protected endpoint with JWT middleware