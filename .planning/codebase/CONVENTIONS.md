# Coding Conventions

**Analysis Date:** 2026-01-09

## Naming Patterns

**Files:**
- `snake_case.py` for Python modules (`cli.py`, `auth.py`, `database.py`)
- `snake_case.js` for JavaScript (`index.js`, `encryption.js`)
- `UPPER_CASE.md` for important docs (`README.md`, `CLAUDE.md`)
- No test file conventions established yet

**Functions:**
- Python: `snake_case` (`get_api_key()`, `create_note()`, `list_notes()`)
- JavaScript: `camelCase` (`generateTokens()`, `verifyToken()`)
- Private: underscore prefix (`_make_request()`, `_get_iso_timestamp()`)
- Handlers: no special prefix convention

**Variables:**
- Python: `snake_case` for variables
- Constants: `UPPER_CASE` (`APP_NAME`, `POSTGREST_URL`, `JWT_SECRET`)
- Private attributes: `_mode`, `_http_session`, `_global_cache`

**Types:**
- Classes: `PascalCase` (`Database`, `Notes`, `LLMHelper`, `ZettlFormatter`)
- No interfaces (Python uses duck typing)
- Type hints use standard library types

## Code Style

**Formatting:**
- Python: Black with default settings (88 char line length)
- Indentation: 4 spaces (Python), 2 spaces (JavaScript)
- Quotes: Single for strings, triple for docstrings (Python)
- Semicolons: Required in JavaScript, not used in Python

**Linting:**
- Pylint 2.15.0 for Python (`requirements.txt`)
- MyPy 0.991 for type checking
- No ESLint config for JavaScript
- Run: `black .`, `pylint zettl/`, `mypy zettl/`

## Import Organization

**Order (per CLAUDE.md):**
1. Standard library imports
2. Third-party imports
3. Local imports

**Grouping:**
- Blank line between groups
- No enforced sorting within groups

**Path Aliases:**
- None used; relative imports within package

**Example from `zettl/cli.py`:**
```python
import os
import click
from zettl.notes import Notes
```

## Error Handling

**Patterns:**
- Python: try/except with specific exceptions preferred
- Raise Exception with context message
- Many bare `except:` blocks (technical debt)

**Error Types:**
- Generic `Exception` for most errors
- No custom exception hierarchy
- Context added to error messages

**Logging:**
- Console output via Rich (CLI)
- `console.error()` in JavaScript
- No structured logging framework

## Logging

**Framework:**
- Python CLI: Rich console for styled output
- JavaScript: console.log/error
- No centralized logging library

**Patterns:**
- CLI uses `ZettlFormatter` for styled output
- Errors displayed with Rich error styling
- No log levels (debug, info, warn, error) implemented

## Comments

**When to Comment:**
- Docstrings on all public functions and classes
- Inline comments for complex logic
- TODO comments for known issues

**Docstring Format:**
```python
"""Summary line.

Optional extended description.

Args:
    param1: Description

Returns:
    Description of return value
"""
```

**TODO Comments:**
- Format: `# TODO: description`
- No issue linking convention

## Function Design

**Size:**
- Large functions exist (some 100+ lines in `cli.py`)
- Recommended: Extract helpers for complex logic

**Parameters:**
- Type hints on all parameters and returns
- Default values for optional params
- No max parameter count enforced

**Return Values:**
- Explicit returns
- Type hints indicate return type
- `None` returned implicitly when no return

## Module Design

**Exports:**
- All module-level functions/classes exported
- No `__all__` declarations
- No barrel files (index.py)

**Organization:**
- Single responsibility per module
- `auth.py` - authentication
- `database.py` - data access
- `notes.py` - notes facade
- `llm.py` - LLM integration

**Package Structure:**
- `__init__.py` with version only
- Subpackages: `chat/`, `mcp/`

## Type Hints

**Usage:**
- Consistently used in function signatures
- Complex types: `List[Dict[str, Any]]`, `Optional[str]`
- Type checking via MyPy

**Examples:**
```python
def create_note(self, content: str) -> str:
def list_notes(self, limit: int = 10) -> List[Dict[str, Any]]:
def search_notes(self, query: str, threshold: float = 0.3) -> List[Dict[str, Any]]:
```

## Configuration Pattern

**Environment Variables:**
- Loaded via `os.getenv()` with defaults
- File-based secrets: `JWT_SECRET_FILE` pattern
- `.env` file for local development

**Example from `zettl/config.py`:**
```python
POSTGREST_URL = os.getenv("POSTGREST_URL", "https://zettlnotes.app/api/v1")
AUTH_URL = os.getenv("AUTH_URL", "https://zettlnotes.app/api/auth")
```

## Caching Pattern

**Implementation in `zettl/database.py`:**
```python
_global_cache = {}
_global_cache_ttl = {}
_default_ttl = 300  # 5 minutes

def get_from_cache(key: str) -> Optional[Any]:
def set_in_cache(key: str, value: Any, ttl: int = None):
def invalidate_cache(pattern: str):
```

**Cache Key Format:**
- `note:{note_id}` - Individual note (600s TTL)
- `list_notes:{limit}` - Note list (60s TTL)
- `tags:{note_id}` - Note tags (300s TTL)
- `related_notes:{note_id}` - Linked notes (300s TTL)

---

*Convention analysis: 2026-01-09*
*Update when patterns change*
