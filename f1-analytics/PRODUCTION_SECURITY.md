# F1 Analytics Production Security Guide

## Critical Security Requirements

### 1. Environment Variables & Secrets

#### Required Actions:
- [ ] Generate secure JWT secret: `openssl rand -base64 64`
- [ ] Use strong database passwords (minimum 16 characters)
- [ ] Use strong Redis passwords (minimum 16 characters)
- [ ] Never commit `.env` files to version control
- [ ] Use secure secret management system (AWS Secrets Manager, HashiCorp Vault, etc.)

#### Environment File Checklist:
```bash
# Verify no weak credentials
grep -E "(f1password|f1redis|dev-secret|change.*production)" .env.production
# Should return no matches

# Verify strong JWT secret (minimum 64 characters)
grep "JWT_SECRET_KEY" .env.production | cut -d'=' -f2 | wc -c
# Should be > 64

# Verify production environment
grep "ENVIRONMENT=production" .env.production
grep "DEBUG=false" .env.production
```

### 2. Database Security

#### PostgreSQL Configuration:
- [ ] Use dedicated database server (not localhost)
- [ ] Enable SSL/TLS connections
- [ ] Implement connection pooling limits
- [ ] Regular security patches
- [ ] Backup encryption

#### Production Database URL Format:
```
DATABASE_URL=postgresql://username:strong_password@db-server:5432/f1_analytics_prod?sslmode=require
```

### 3. Redis Security

#### Redis Configuration:
- [ ] Enable authentication (`requirepass`)
- [ ] Use dedicated Redis instance
- [ ] Configure memory limits
- [ ] Enable persistence if needed
- [ ] Network security (VPC/firewall rules)

### 4. Network Security

#### HTTPS/TLS:
- [ ] Valid SSL certificate (Let's Encrypt, commercial CA)
- [ ] HTTPS redirect enabled
- [ ] HSTS headers configured
- [ ] TLS 1.2+ only

#### Firewall Rules:
```
Allow:
- Port 443 (HTTPS) from internet
- Port 80 (HTTP) for redirect only
- Database port (5432) from application servers only
- Redis port (6379) from application servers only

Deny:
- Direct access to application ports (8000, 3000)
- Administrative ports except from management network
```

### 5. Application Security Headers

The application automatically includes these security headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: [Restrictive policy]
```

### 6. CORS Configuration

#### Production CORS Settings:
```env
# ONLY allow your production domains
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# NO localhost, wildcards, or development URLs
# ❌ BAD: http://localhost:3000,*,http://127.0.0.1
# ✅ GOOD: https://f1analytics.example.com
```

### 7. Rate Limiting

#### Default Limits:
- API endpoints: 30 requests/minute
- Health checks: 300 requests/minute
- Burst allowance: 60 requests

#### Monitoring:
- Monitor rate limit violations
- Implement progressive penalties for abuse
- Whitelist known good sources if needed

### 8. Monitoring & Logging

#### Security Monitoring:
- [ ] Failed authentication attempts
- [ ] Rate limit violations
- [ ] Unusual API usage patterns
- [ ] Database connection failures
- [ ] Security header violations

#### Log Management:
- [ ] Centralized logging (ELK, Splunk, etc.)
- [ ] Log rotation configured
- [ ] No sensitive data in logs
- [ ] Access logs retention policy

### 9. Container Security

#### Docker Security:
- [ ] Non-root user in containers
- [ ] Minimal base images (alpine)
- [ ] Regular image updates
- [ ] Vulnerability scanning
- [ ] Resource limits configured

#### Example secure Dockerfile additions:
```dockerfile
# Create non-root user
RUN adduser --disabled-password --gecos "" --uid 1000 appuser
USER appuser

# Set resource limits
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

### 10. Backup & Recovery

#### Backup Requirements:
- [ ] Database backups (daily, encrypted)
- [ ] Configuration backups
- [ ] Disaster recovery plan
- [ ] Backup testing procedure
- [ ] Recovery time objectives defined

### 11. Dependency Security

#### Security Scanning:
```bash
# Backend dependency scanning
cd backend && pip-audit

# Frontend dependency scanning
cd frontend && npm audit

# Container scanning
docker scout cves f1-analytics-backend:latest
docker scout cves f1-analytics-frontend:latest
```

### 12. Pre-Deployment Security Checklist

#### Automated Security Tests:
```bash
# Run security validation
python -c "from app.core.config import get_settings, validate_production_config; s = get_settings(); print(validate_production_config(s))"

# Verify environment security
curl -f http://localhost:8000/health | jq '.checks.security'

# Test JWT secret strength
python -c "from app.core.security import validate_jwt_secret; validate_jwt_secret()"
```

#### Manual Verification:
- [ ] All environment variables use production values
- [ ] No debug/development features enabled
- [ ] CORS configured for production domains only
- [ ] JWT secrets are cryptographically secure
- [ ] Database and Redis use strong authentication
- [ ] SSL certificates are valid
- [ ] Security headers are present
- [ ] Rate limiting is active
- [ ] Logging is configured

### 13. Incident Response

#### Security Incident Plan:
1. **Detection**: Monitor alerts, logs, health checks
2. **Assessment**: Determine impact and scope
3. **Containment**: Isolate affected systems
4. **Recovery**: Restore service with patches
5. **Lessons**: Document and improve security

#### Emergency Contacts:
- [ ] Security team contact information
- [ ] Database administrator
- [ ] Infrastructure team
- [ ] Management escalation path

### 14. Compliance & Audit

#### Documentation Requirements:
- [ ] Security configuration documentation
- [ ] Access control procedures
- [ ] Data handling policies
- [ ] Audit log procedures
- [ ] Vulnerability management process

## Quick Security Validation Commands

```bash
# 1. Check environment configuration
grep -v "^#" .env.production | grep -E "(password|secret|key)" | head -5

# 2. Validate JWT secret strength
echo $JWT_SECRET_KEY | wc -c  # Should be > 64

# 3. Test health endpoint security
curl -i https://yourapi.com/health | grep -i "x-"

# 4. Verify CORS headers
curl -H "Origin: https://malicious.com" -i https://yourapi.com/

# 5. Test rate limiting
for i in {1..35}; do curl -s https://yourapi.com/api/v1/info >/dev/null && echo $i; done

# 6. Check database connection security
psql $DATABASE_URL -c "SHOW ssl;" # Should show 'on'
```

## Security Contact

For security issues, contact: security@f1analytics.com

Report vulnerabilities privately before public disclosure.