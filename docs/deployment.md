# Deployment Guide

## Production Deployment Checklist

### Environment Configuration

1. **JWT Secret** (CRITICAL):
   ```bash
   # Generate a secure random secret (32+ characters)
   openssl rand -hex 32
   export JWT_SECRET="generated_secret_here"
   ```

2. **CORS Configuration**:
   ```bash
   # Set allowed origins for your frontend domains
   export ALLOWED_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
   ```

3. **Debug Mode**:
   ```bash
   # Always disable debug in production
   export DEBUG="false"
   ```

### Security Hardening

1. **Environment Variables**: Never commit secrets to version control
2. **HTTPS Only**: Use HTTPS in production for token security
3. **CORS**: Restrict origins to your actual frontend domains
4. **Token Storage**: Store JWT tokens securely in HTTP-only cookies (client-side implementation)

### Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/

ENV PYTHONPATH=/app

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  auth-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
      - DEBUG=false
    restart: unless-stopped
```

### Cloud Deployment Options

#### 1. Railway / Render / Fly.io
- Set environment variables in platform dashboard
- Deploy directly from GitHub repository
- Automatic HTTPS and scaling

#### 2. AWS ECS / Google Cloud Run
- Use container-based deployment
- Set environment variables in service configuration
- Enable auto-scaling and health checks

#### 3. Traditional VPS
```bash
# Install dependencies
sudo apt update && sudo apt install python3-pip nginx

# Set up application
git clone <your-repo>
cd <repo-directory>
pip3 install -r requirements.txt

# Create systemd service
sudo nano /etc/systemd/system/auth-api.service
```

Example systemd service file:
```ini
[Unit]
Description=Python Auth API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/app
Environment=JWT_SECRET=your-secret-here
Environment=ALLOWED_ORIGINS=https://yourdomain.com
Environment=DEBUG=false
ExecStart=/usr/bin/python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Monitoring and Logging

1. **Health Check**: Use `/health` endpoint for monitoring
2. **Logging**: Configure structured logging for production
3. **Metrics**: Monitor token creation/validation rates
4. **Alerts**: Set up alerts for authentication failures

### Database Migration (Future)

When ready to move beyond in-memory storage:

1. **PostgreSQL Setup**:
   ```bash
   pip install asyncpg sqlalchemy
   ```

2. **Migration Strategy**:
   - Create database models with SQLAlchemy
   - Implement async database operations
   - Add connection pooling
   - Update repository to use database

3. **Environment Variables**:
   ```bash
   export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
   ```

### Performance Considerations

1. **Concurrency**: Use multiple workers for production
   ```bash
   uvicorn api.main:app --workers 4 --host 0.0.0.0 --port 8000
   ```

2. **Rate Limiting**: Implement rate limiting for auth endpoints
3. **Token Caching**: Consider Redis for token blacklisting
4. **Database Optimization**: Add indexes on email fields

### Backup and Recovery

1. **Database Backups**: Regular automated backups
2. **Configuration Backup**: Secure backup of environment variables
3. **Disaster Recovery**: Document recovery procedures

### Scaling Considerations

1. **Horizontal Scaling**: Stateless design allows easy scaling
2. **Load Balancing**: Use load balancer for multiple instances
3. **Session Storage**: Move to shared storage (Redis/Database)
4. **Microservices**: Split into separate auth service