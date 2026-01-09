# Codebase Structure

**Analysis Date:** 2026-01-09

## Directory Layout

```
zettl/
├── zettl/                    # Main Python package
│   ├── __init__.py           # Version: 0.9.3
│   ├── cli.py                # CLI entry point & commands (Click)
│   ├── notes.py              # Notes facade/business logic
│   ├── database.py           # Core data access layer
│   ├── auth.py               # Authentication & API key management
│   ├── config.py             # Configuration loader
│   ├── llm.py                # LLM/Claude integration
│   ├── formatting.py         # Context-aware formatter
│   ├── help.py               # Help system
│   ├── cli_wrapper.py        # Readline wrapper
│   ├── completion.py         # Tab completion
│   ├── chat/                 # Chat feature
│   │   └── manager.py        # Conversation management
│   └── mcp/                  # Model Context Protocol
│       ├── server.py         # MCP server (async)
│       ├── tools.py          # Tool implementations
│       ├── auth.py           # JWT auth for MCP
│       ├── http_server.py    # Flask HTTP wrapper
│       └── run_server.py     # Server runner
├── zettl_web/                # Web application
│   ├── zettl_web.py          # Flask main app
│   ├── poetry_web.py         # Poetry companion feature
│   ├── Dockerfile            # Container definition
│   ├── requirements.txt      # Web dependencies
│   └── templates/            # Jinja2 templates
│       ├── index.html
│       ├── settings.html
│       └── poetry.html
├── zettl_mcp/                # Standalone MCP server container
│   └── Dockerfile
├── auth-service/             # Node.js authentication service
│   ├── index.js              # Express app
│   ├── encryption.js         # Encryption utilities
│   ├── Dockerfile
│   └── package.json
├── nginx/                    # Reverse proxy config
│   └── nginx.conf
├── sql/                      # Custom SQL schemas & views
├── migrations/               # Database migrations
├── config/                   # Database & service configs
│   └── postgresql/
│       └── init/             # DB initialization scripts
├── secrets/                  # Secret files (gitignored)
├── docker-compose.yml        # Multi-service orchestration
├── setup.py                  # Python package installer
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
├── CLAUDE.md                 # Claude Code instructions
└── README.md                 # Project documentation
```

## Directory Purposes

**zettl/**
- Purpose: Main Python package for CLI and core logic
- Contains: CLI commands, business logic, data access
- Key files: `cli.py` (entry point), `database.py` (data access), `notes.py` (facade)
- Subdirectories: `chat/` (conversation features), `mcp/` (AI integration)

**zettl/mcp/**
- Purpose: Model Context Protocol server for AI assistants
- Contains: MCP protocol implementation, tool definitions
- Key files: `server.py`, `tools.py`, `http_server.py`

**zettl/chat/**
- Purpose: Chat/conversation management
- Contains: Conversation and message handling
- Key files: `manager.py`

**zettl_web/**
- Purpose: Flask web application
- Contains: Routes, templates, session management
- Key files: `zettl_web.py` (main app), `poetry_web.py` (poetry feature)
- Subdirectories: `templates/` (Jinja2 HTML)

**auth-service/**
- Purpose: Node.js JWT/API key authentication service
- Contains: Express routes, password hashing, token generation
- Key files: `index.js` (main app), `encryption.js` (crypto utilities)

**nginx/**
- Purpose: Reverse proxy configuration
- Contains: Nginx config for routing and caching
- Key files: `nginx.conf`

## Key File Locations

**Entry Points:**
- `zettl/cli.py` - CLI entry, ~2,099 lines, all commands
- `zettl_web/zettl_web.py` - Web entry, Flask app
- `zettl/mcp/http_server.py` - MCP HTTP wrapper
- `auth-service/index.js` - Auth service entry

**Configuration:**
- `setup.py` - Package configuration, entry points
- `docker-compose.yml` - Full stack orchestration (~245 lines)
- `.env` - Environment variables
- `zettl/config.py` - Config loader

**Core Logic:**
- `zettl/database.py` - Data access layer (~1,084 lines)
- `zettl/notes.py` - Notes facade (~100 lines)
- `zettl/llm.py` - Claude integration (~500 lines)
- `zettl/auth.py` - Authentication helpers

**Testing:**
- No dedicated test directory (gap identified)

**Documentation:**
- `README.md` - User documentation
- `CLAUDE.md` - Claude Code instructions
- `CHANGELOG.md` - Version history

## Naming Conventions

**Files:**
- `snake_case.py` for Python modules
- `snake_case.js` for JavaScript files
- `UPPER_CASE.md` for important docs (README, CLAUDE, CHANGELOG)

**Directories:**
- `snake_case` for all directories
- `zettl_*` prefix for related service directories

**Special Patterns:**
- `__init__.py` for Python packages
- `*.md` templates in `.planning/`
- `Dockerfile` per service

## Where to Add New Code

**New CLI Command:**
- Primary code: `zettl/cli.py` (add Click command)
- Tests: `zettl/tests/` (to be created)
- Consider extracting to `zettl/cli/commands/` if refactoring

**New MCP Tool:**
- Implementation: `zettl/mcp/tools.py` (add method to ZettlMCPTools)
- Registration: `zettl/mcp/server.py` (register tool)

**New Web Route:**
- Implementation: `zettl_web/zettl_web.py` (add Flask route)
- Template: `zettl_web/templates/*.html`
- Or create new Blueprint file for feature

**New Database Operation:**
- Implementation: `zettl/database.py` (add method to Database class)
- Consider cache invalidation logic

**Utilities:**
- Shared helpers: `zettl/` (new module like `zettl/utils.py`)
- Formatting: `zettl/formatting.py`

## Special Directories

**secrets/**
- Purpose: Sensitive credentials (JWT keys, DB passwords)
- Source: Created manually, not in Git
- Committed: No (gitignored)

**.planning/**
- Purpose: GSD planning documents
- Source: Created by GSD workflow
- Committed: Yes

**config/postgresql/init/**
- Purpose: Database initialization scripts
- Source: Run on container first start
- Committed: Yes

---

*Structure analysis: 2026-01-09*
*Update when directory structure changes*
