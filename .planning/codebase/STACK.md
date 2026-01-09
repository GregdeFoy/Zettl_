# Technology Stack

**Analysis Date:** 2026-01-09

## Languages

**Primary:**
- Python 3.11 - All application code (`zettl/`, `zettl_web/`, `zettl_mcp/`)
- JavaScript (Node.js 20) - Authentication service (`auth-service/`)

**Secondary:**
- HTML/Jinja2 - Web templates (`zettl_web/templates/`)
- SQL - Database migrations and views (`sql/`, `migrations/`)
- Nginx Configuration - Reverse proxy (`nginx/nginx.conf`)

## Runtime

**Environment:**
- Python 3.11-slim - `zettl_web/Dockerfile`, `zettl_mcp/Dockerfile`
- Node.js 20-alpine - `auth-service/Dockerfile`
- Docker Compose - Multi-container orchestration

**Package Manager:**
- pip for Python - `requirements.txt`, `zettl_web/requirements.txt`
- npm for Node.js - `auth-service/package.json`
- Lockfile: `auth-service/package-lock.json` present

## Frameworks

**Core:**
- Flask 3.0.0 - Web framework (`zettl_web/zettl_web.py`)
- Click 8.1.0 - CLI framework (`zettl/cli.py`)
- Express.js 4.18.2 - Auth service (`auth-service/`)
- PostgREST - Auto-generated REST API from PostgreSQL (`docker-compose.yml`)

**Testing:**
- pytest 7.0.0 - Python tests (`requirements.txt`)
- Jest 29.7.0 - Node.js tests (`auth-service/package.json`)

**Build/Dev:**
- Gunicorn 21.2.0 - WSGI server (`zettl_web/Dockerfile`)
- Black 22.0.0 - Python formatter (`requirements.txt`)
- Pylint 2.15.0 - Python linter (`requirements.txt`)
- MyPy 0.991 - Python type checker (`requirements.txt`)
- nodemon 3.0.2 - Node.js dev server (`auth-service/package.json`)

## Key Dependencies

**Critical:**
- anthropic 0.3.0+ - Claude API client (`setup.py`, `zettl/llm.py`)
- mcp 0.1.0+ - Model Context Protocol SDK (`setup.py`, `zettl/mcp/`)
- Click 8.1.0 - CLI framework (`zettl/cli.py`)
- Rich 10.0.0 - Terminal formatting (`zettl/cli.py`)
- requests 2.28.0+ - HTTP client (`zettl/database.py`)

**Infrastructure:**
- Flask 3.0.0 - Web framework (`zettl_web/`)
- Flask-HTTPAuth 4.8.0 - Authentication middleware
- Flask-CORS 4.0.0 - Cross-origin handling
- pg 8.11.3 - PostgreSQL client for Node.js (`auth-service/`)
- bcrypt 5.1.1 - Password hashing (`auth-service/`)
- jsonwebtoken 9.0.2 - JWT handling (`auth-service/`)
- PyJWT 2.8.0+ - Python JWT (`zettl/mcp/auth.py`)

**Security:**
- helmet 7.1.0 - HTTP security headers (`auth-service/`)
- express-rate-limit 7.1.5 - Rate limiting (`auth-service/`)

## Configuration

**Environment:**
- `.env` file for environment variables
- `secrets/` directory for sensitive data (JWT keys, DB passwords)
- File-based secrets support: `JWT_SECRET_FILE`, `DB_PASSWORD_FILE`, `ENCRYPTION_KEY_FILE`
- Key configs: `POSTGREST_URL`, `AUTH_URL`, `DATABASE_URL`, `JWT_SECRET`

**Build:**
- `setup.py` - Python package configuration
- `docker-compose.yml` - Full stack orchestration
- `Dockerfile` per service - Container definitions

## Platform Requirements

**Development:**
- Docker + Docker Compose required
- Python 3.11+, Node.js 20+
- PostgreSQL 16 (via Docker)

**Production:**
- Docker containers on host server
- Cloudflare Tunnel for external access
- Nginx reverse proxy (port 8080 external, routes internally)
- PostgreSQL 16-alpine with daily backups

---

*Stack analysis: 2026-01-09*
*Update after major dependency changes*
