# Architecture

**Analysis Date:** 2026-01-09

## Pattern Overview

**Overall:** Modular Microservices with Multi-Frontend (CLI & Web)

**Key Characteristics:**
- Zettelkasten-style note-taking system
- CLI frontend for terminal users (Python Click)
- Web frontend for browser users (Flask)
- MCP server for AI assistant integration
- PostgREST API gateway for database access
- Docker Compose orchestration

## Layers

**CLI/Interface Layer:**
- Purpose: Parse user input, format output
- Contains: Command handlers, formatters, help system
- Location: `zettl/cli.py`, `zettl/formatting.py`, `zettl/help.py`
- Depends on: Business Logic layer
- Used by: End users via terminal

**Web Interface Layer:**
- Purpose: Serve web UI, manage sessions
- Contains: Flask routes, Jinja2 templates
- Location: `zettl_web/zettl_web.py`, `zettl_web/templates/`
- Depends on: Business Logic layer, Auth service
- Used by: Browser users

**MCP Layer:**
- Purpose: AI assistant tool interface
- Contains: MCP protocol server, tool definitions
- Location: `zettl/mcp/server.py`, `zettl/mcp/tools.py`, `zettl/mcp/http_server.py`
- Depends on: Data Access layer
- Used by: Claude and other MCP-compatible AI assistants

**Business Logic Layer:**
- Purpose: Core note operations, LLM integration
- Contains: Notes facade, LLM helper, Chat manager
- Location: `zettl/notes.py`, `zettl/llm.py`, `zettl/chat/manager.py`
- Depends on: Data Access layer
- Used by: CLI, Web, MCP layers

**Data Access Layer:**
- Purpose: HTTP abstraction to PostgREST, caching
- Contains: Database class, cache management
- Location: `zettl/database.py`
- Depends on: PostgREST API
- Used by: Business Logic layer

**Authentication Layer:**
- Purpose: API key management, JWT validation
- Contains: Auth helpers, token caching
- Location: `zettl/auth.py`, `zettl/mcp/auth.py`, `auth-service/`
- Depends on: Auth service (Node.js)
- Used by: All layers

## Data Flow

**CLI Command Execution:**

1. User runs: `zettl note "My note content"`
2. Click parses args (`zettl/cli.py`)
3. `get_notes_manager()` creates Notes instance with API key
4. Notes calls Database methods (`zettl/database.py`)
5. Database makes HTTP request to PostgREST
6. PostgREST translates to SQL, queries PostgreSQL
7. Response cached in `_global_cache` (5-min TTL)
8. `ZettlFormatter` formats output for terminal (Rich markup)
9. Result displayed to user

**Web Request:**

1. User visits web page
2. Nginx routes to Flask (`zettl_web/zettl_web.py`)
3. Session validated via JWT cookie
4. Flask calls Notes/Database for data
5. Jinja2 template rendered with data
6. HTML response sent to browser

**MCP Tool Execution:**

1. AI assistant calls MCP tool
2. HTTP request to MCP server (`zettl/mcp/http_server.py`)
3. JWT validated (`zettl/mcp/auth.py`)
4. Tool handler invoked (`zettl/mcp/tools.py`)
5. Database operations executed
6. JSON response returned to AI

**State Management:**
- File-based: All persistent state in PostgreSQL
- CLI state: API key in `~/.zettl/config`, JWT cache in `~/.zettl/cache/`
- Web state: Session cookies (30-day expiry)
- In-memory cache: TTL-based dict in `zettl/database.py`

## Key Abstractions

**Database:**
- Purpose: HTTP client wrapper for PostgREST API
- Location: `zettl/database.py`
- Examples: `create_note()`, `search_notes()`, `get_related_notes()`
- Pattern: Singleton HTTP session, TTL caching

**Notes:**
- Purpose: Thin facade over Database
- Location: `zettl/notes.py`
- Examples: `create_note()`, `list_notes()`, `delete_note()`
- Pattern: Facade pattern

**LLMHelper:**
- Purpose: Claude API integration
- Location: `zettl/llm.py`
- Examples: `_call_llm_api()`, `_get_claude_api_key()`
- Pattern: Lazy-loaded client, strategy pattern for context

**ZettlFormatter:**
- Purpose: Context-aware output formatting
- Location: `zettl/formatting.py`
- Examples: `header()`, `success()`, `error()`
- Pattern: Strategy pattern (CLI vs Web mode)

**ZettlMCPTools:**
- Purpose: MCP tool implementations
- Location: `zettl/mcp/tools.py`
- Examples: `search_notes()`, `create_note()`, `add_tags()`
- Pattern: Adapter over Database

## Entry Points

**CLI Entry:**
- Location: `zettl/cli.py`
- Triggers: User runs `z`, `zt`, or `zettl` command
- Responsibilities: Parse args, route to command, format output
- Registration: `setup.py` console_scripts

**Web Entry:**
- Location: `zettl_web/zettl_web.py`
- Triggers: HTTP request to Flask server
- Responsibilities: Session management, template rendering, API endpoints

**MCP Entry:**
- Location: `zettl/mcp/http_server.py`
- Triggers: HTTP request from AI assistant
- Responsibilities: Auth, route to tool handler, JSON response

## Error Handling

**Strategy:** Throw exceptions at source, catch at boundaries, log and format for user

**Patterns:**
- Database layer raises `Exception` with context
- CLI catches and displays with Rich formatting
- Web returns JSON error responses with status codes
- Silent failures in non-critical paths (cache operations)

**Issues:**
- Many bare `except:` blocks (see CONCERNS.md)
- Generic Exception re-raising loses context

## Cross-Cutting Concerns

**Logging:**
- Console output via Rich (CLI)
- Docker container logs (stdout/stderr)
- Nginx access logs with timing

**Validation:**
- Minimal input validation currently
- PostgREST handles schema validation
- JWT validation at auth boundaries

**Authentication:**
- API key in `X-API-Key` header (CLI)
- JWT in session cookie (Web)
- Bearer token to PostgREST

**Caching:**
- In-memory dict with TTL (`zettl/database.py`)
- JWT tokens cached locally (1-hour expiry)
- Auth validation cached (24-hour expiry)

---

*Architecture analysis: 2026-01-09*
*Update when major patterns change*
