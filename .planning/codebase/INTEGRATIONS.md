# External Integrations

**Analysis Date:** 2026-01-09

## APIs & External Services

**AI/LLM:**
- Anthropic Claude API - AI-powered note analysis and chat (`zettl/llm.py`)
  - SDK/Client: anthropic Python package
  - Auth: API key retrieved from auth service endpoint (`/api/auth/settings/claude-key`)
  - Model: `claude-sonnet-4-5-20250929` (`zettl/llm.py` line 41)
  - Features: Chat, note analysis, poetry analysis

**Payment Processing:**
- Not detected

**Email/SMS:**
- Not detected

**Analytics:**
- Not detected

## Data Storage

**Databases:**
- PostgreSQL 16-alpine - Primary data store (`docker-compose.yml`)
  - Connection: Via `DATABASE_URL` env var
  - Client: PostgREST auto-generated REST API
  - Tables: notes, tags, links, conversations, messages
  - Features: Row-Level Security, pg_trgm for fuzzy search

**File Storage:**
- Local file system only
- No cloud storage integration detected

**Caching:**
- In-memory Python dict cache (`zettl/database.py`)
  - TTL-based expiration (5 min default)
  - No Redis or external cache

## Authentication & Identity

**Auth Provider:**
- Custom Node.js auth service (`auth-service/`)
  - JWT token generation and validation
  - API key management for CLI users
  - Password hashing with bcrypt
  - Rate limiting: 5 auth attempts per 15 minutes

**Token Storage:**
- CLI: `~/.zettl/config` for API key, `~/.zettl/cache/jwt_*` for cached tokens
- Web: httpOnly cookies via Flask sessions

**OAuth Integrations:**
- Not detected

## Monitoring & Observability

**Error Tracking:**
- Not detected (no Sentry, Rollbar, etc.)

**Analytics:**
- Not detected

**Logs:**
- Docker container logs (stdout/stderr)
- Nginx access logs with performance metrics (`nginx/nginx.conf`)

## CI/CD & Deployment

**Hosting:**
- Self-hosted Docker containers
- Cloudflare Tunnel for external access (`docker-compose.yml` lines 170-180)
  - Container: `zettl-tunnel` (cloudflare/cloudflared:latest)
  - Token: `CLOUDFLARE_TUNNEL_TOKEN` env var
  - Domain: `zettlnotes.app`

**CI Pipeline:**
- Not detected (no GitHub Actions, GitLab CI)

**Backup:**
- PostgreSQL automated backups (`docker-compose.yml` line 184)
  - Image: `prodrigestivill/postgres-backup-local:16`
  - Schedule: Daily at 2 AM
  - Retention: 7 days daily, 4 weeks weekly, 6 months monthly

## Environment Configuration

**Development:**
- Required env vars: `POSTGREST_URL`, `AUTH_URL`, `DATABASE_URL`
- Secrets location: `.env` file, `secrets/` directory
- Docker Compose for local services

**Staging:**
- Not configured separately

**Production:**
- Secrets in file system (`secrets/` directory)
- Environment vars via `.env`
- Cloudflare Tunnel for secure access

## Webhooks & Callbacks

**Incoming:**
- Not detected

**Outgoing:**
- Not detected

## Internal Service Architecture

**PostgREST API Gateway:**
- Container: `zettl-api` (port 3000 internal)
- Auto-generated REST API from PostgreSQL schema
- Uses `authenticator` role for Row Level Security
- Accessed by: `zettl/database.py`

**Auth Service (Node.js):**
- Container: `zettl-auth` (port 3001 internal)
- Endpoints:
  - `/api/auth/login` - User login
  - `/api/auth/register` - User registration
  - `/api/auth/settings/claude-key` - Claude API key storage
  - `/token-from-key` - Convert API key to JWT
  - `/health` - Health check

**MCP Server:**
- Container: `zettl-mcp` (port 3002 internal)
- Model Context Protocol server for AI assistants
- Flask HTTP wrapper over MCP protocol
- Tools: search, create, append, tag notes

**Web Application:**
- Container: `zettl-web` (port 5000 internal)
- Flask with Gunicorn WSGI
- Templates in `zettl_web/templates/`

**Reverse Proxy (Nginx):**
- Container: `zettl-nginx` (port 8080 external)
- Routes to Flask, PostgREST, auth service
- Gzip compression, static caching

## Network Architecture

- Docker bridge network: `zettl-network` (172.26.0.0/16)
- All services communicate via Docker DNS
- External access via Cloudflare Tunnel only

---

*Integration audit: 2026-01-09*
*Update when adding/removing external services*
