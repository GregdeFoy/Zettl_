# Testing Patterns

**Analysis Date:** 2026-01-09

## Test Framework

**Runner:**
- Python: pytest 7.0.0 (`requirements.txt`)
- JavaScript: Jest 29.7.0 (`auth-service/package.json`)

**Assertion Library:**
- pytest built-in assertions (Python)
- Jest expect (JavaScript)

**Run Commands:**
```bash
# Python (when tests exist)
pytest                              # Run all tests
pytest -v                           # Verbose output
pytest path/to/test.py              # Single file
pytest --cov=zettl                  # Coverage report

# JavaScript (auth-service)
npm test                            # Run Jest tests
```

## Test File Organization

**Current State:**
- No test files currently exist in the codebase
- No `tests/`, `__tests__/`, or `test/` directories
- Test framework configured but not implemented

**Expected Location (when added):**
- Python: `zettl/tests/` or `tests/` at project root
- JavaScript: `auth-service/__tests__/` or `auth-service/*.test.js`

**Expected Naming:**
- Python: `test_*.py` or `*_test.py`
- JavaScript: `*.test.js` or `*.spec.js`

**Expected Structure:**
```
zettl/
├── tests/
│   ├── test_database.py
│   ├── test_notes.py
│   ├── test_auth.py
│   ├── test_cli.py
│   └── fixtures/
│       └── sample_notes.py
auth-service/
└── __tests__/
    └── auth.test.js
```

## Test Structure

**Expected Suite Organization (Python):**
```python
import pytest
from zettl.database import Database

class TestDatabase:
    """Tests for Database class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db = Database(api_key="test-key")

    def test_create_note_success(self):
        """Should create note and return ID."""
        # arrange
        content = "Test note content"

        # act
        result = self.db.create_note(content)

        # assert
        assert result is not None
        assert len(result) == 5  # Zettelkasten ID format

    def test_create_note_empty_content(self):
        """Should handle empty content."""
        with pytest.raises(Exception):
            self.db.create_note("")
```

**Patterns:**
- Class-based test organization
- `setup_method` for per-test setup
- Arrange/Act/Assert structure
- Descriptive test method names

## Mocking

**Framework:**
- Python: pytest-mock or unittest.mock
- JavaScript: Jest built-in mocking

**Expected Patterns (Python):**
```python
from unittest.mock import Mock, patch

@patch('zettl.database.requests.Session')
def test_api_call(mock_session):
    """Mock HTTP requests to PostgREST."""
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "12abc"}
    mock_session.return_value.post.return_value = mock_response

    db = Database(api_key="test")
    result = db.create_note("content")

    assert result == "12abc"
```

**What to Mock:**
- HTTP requests to PostgREST API
- HTTP requests to auth service
- File system operations (`~/.zettl/` config)
- Anthropic API calls

**What NOT to Mock:**
- Pure functions (formatting, ID generation)
- Data transformation logic

## Fixtures and Factories

**Expected Test Data Pattern:**
```python
# tests/fixtures/notes.py
def create_test_note(overrides=None):
    """Factory for test note objects."""
    note = {
        "id": "12abc",
        "content": "Test note content",
        "type": "note",
        "created_at": "2026-01-09T12:00:00Z",
        "updated_at": "2026-01-09T12:00:00Z"
    }
    if overrides:
        note.update(overrides)
    return note

# Shared fixtures
SAMPLE_NOTES = [
    create_test_note({"id": "01abc", "content": "First note"}),
    create_test_note({"id": "02def", "content": "Second note"}),
]
```

**Location:**
- Factory functions: `tests/fixtures/`
- Shared test data: `tests/conftest.py` (pytest)

## Coverage

**Requirements:**
- No enforced coverage target currently
- Recommended: 80%+ for critical paths

**Configuration (when added):**
```ini
# pytest.ini or pyproject.toml
[tool:pytest]
addopts = --cov=zettl --cov-report=html

[coverage:run]
omit =
    */tests/*
    */__init__.py
```

**Critical Paths to Test:**
- `zettl/database.py` - All CRUD operations
- `zettl/auth.py` - Token validation, API key management
- `zettl/notes.py` - Notes facade
- `zettl/mcp/tools.py` - MCP tool handlers

## Test Types

**Unit Tests (Priority: High):**
- Scope: Single function/class in isolation
- Mock all external dependencies
- Files: `test_database.py`, `test_auth.py`, `test_notes.py`

**Integration Tests (Priority: Medium):**
- Scope: Multiple modules together
- Mock external services (PostgREST, auth)
- Files: `test_cli_integration.py`, `test_mcp_integration.py`

**E2E Tests (Priority: Low):**
- Not currently planned
- Would test full Docker Compose stack
- CLI command to database round-trip

## Common Patterns

**Async Testing (for MCP):**
```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_mcp_tool():
    """Test async MCP tool handler."""
    result = await tool_handler.search_notes(query="test")
    assert len(result) > 0
```

**Error Testing:**
```python
def test_invalid_api_key():
    """Should raise on invalid API key."""
    db = Database(api_key="invalid")
    with pytest.raises(Exception, match="Authentication failed"):
        db.list_notes()
```

**CLI Testing (Click):**
```python
from click.testing import CliRunner
from zettl.cli import cli

def test_list_command():
    """Test list notes CLI command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['list'])
    assert result.exit_code == 0
    assert "notes" in result.output
```

## Code Quality Tools

**Installed:**
- Black 22.0.0 - Code formatter
- Pylint 2.15.0 - Linter
- MyPy 0.991 - Type checker

**Run Commands:**
```bash
black .                    # Format all Python
black --check .            # Check formatting
pylint zettl/              # Lint package
mypy zettl/                # Type check
```

**Not Installed:**
- pre-commit hooks
- CI/CD pipeline
- ESLint for JavaScript

---

*Testing analysis: 2026-01-09*
*Update when test patterns change*
