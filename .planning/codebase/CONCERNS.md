# Codebase Concerns

**Analysis Date:** 2026-01-09

## Tech Debt

**Large monolithic files:**
- Issue: `zettl/cli.py` is 2,099 lines; `zettl/database.py` is 1,084 lines
- Files: `zettl/cli.py`, `zettl/database.py`
- Why: Rapid development, features added incrementally
- Impact: Hard to test, maintain, and understand
- Fix approach: Split `cli.py` into `zettl/cli/commands/` directory; extract caching from `database.py`

**Duplicate command logic:**
- Issue: `note_cmd`, `idea_cmd`, `todo_cmd` have ~500+ lines of nearly identical code
- File: `zettl/cli.py`
- Why: Copy-paste during feature development
- Impact: Bug fixes need to be applied 3+ times
- Fix approach: Extract shared command logic to utility functions

**Generic exception handling:**
- Issue: Specific errors converted to generic `Exception`
- Files: `zettl/database.py` (lines 252-257, 289-294)
- Why: Quick error wrapping
- Impact: Loss of exception type, harder to handle specific failures
- Fix approach: Create custom exception hierarchy (DatabaseError, AuthError, etc.)

## Known Bugs

**Silent failures in cache operations:**
- Symptoms: Operations succeed but cached data is stale or missing
- Trigger: Any exception during cache get/set
- Files: `zettl/auth.py` (lines 53, 101, 120), `zettl/database.py` (lines 645, 653)
- Workaround: None (failures are silent)
- Root cause: Bare `except:` blocks swallow all errors including critical ones
- Fix: Use specific exceptions (`except (IOError, KeyError):`) with logging

**JWT token caching without expiration check:**
- Symptoms: Requests fail with expired token after long idle periods
- Trigger: Token expires before 1-hour cache expiry
- File: `zettl/database.py` (lines 82-102)
- Workaround: Restart CLI or manually clear cache
- Root cause: Cache TTL doesn't check actual token exp claim
- Fix: Parse JWT, check exp claim before using cached token

## Security Considerations

**Shell injection in editor command:**
- Risk: Command injection if editor variable contains malicious input
- File: `zettl/cli.py` (line 1802)
- Code: `subprocess.call(editor + ' ' + temp_path, shell=True)`
- Current mitigation: None
- Recommendations: Use `subprocess.call([editor, temp_path])` without `shell=True`

**Disabled HTTPS warnings:**
- Risk: Silent SSL/TLS verification failures, man-in-the-middle attacks
- File: `zettl/llm.py` (line 7)
- Code: `urllib3.disable_warnings()`
- Current mitigation: None
- Recommendations: Remove line; handle specific warnings with context managers only

**Hardcoded production URLs as defaults:**
- Risk: Local development may accidentally hit production
- File: `zettl/config.py`
- Current mitigation: Users should set env vars
- Recommendations: Use localhost defaults: `http://localhost:8080/api/...`

## Performance Bottlenecks

**Unbounded in-memory cache:**
- Problem: Global cache dict can grow without limit
- File: `zettl/database.py` (lines 15-52)
- Measurement: No max size; memory grows with usage
- Cause: No eviction policy or size limits
- Improvement path: Add LRU cache with max entries (e.g., `functools.lru_cache` or cachetools)

**Fallback to individual requests:**
- Problem: Batch tag operations fall back to N+1 pattern on failure
- File: `zettl/database.py` (lines 631-658)
- Measurement: 10 tags = 10 HTTP requests on batch failure
- Cause: No retry logic, immediate fallback
- Improvement path: Implement retry with exponential backoff before fallback

## Fragile Areas

**CLI command handlers:**
- File: `zettl/cli.py`
- Why fragile: Massive file with intertwined display and business logic
- Common failures: Changes break multiple commands due to shared code
- Safe modification: Test all related commands after any change
- Test coverage: No tests currently

**Cache invalidation:**
- Files: `zettl/database.py`
- Why fragile: Manual invalidation across multiple operations
- Common failures: Stale data after mutations
- Safe modification: Trace all cache keys affected by operation
- Test coverage: No tests currently

## Scaling Limits

**In-memory caching:**
- Current capacity: Single process, single machine
- Limit: Memory constraints of host
- Symptoms at limit: OOM errors, slow response
- Scaling path: Replace with Redis for multi-process/distributed caching

**PostgREST API:**
- Current capacity: Single container, no connection pooling config visible
- Limit: PostgreSQL connection limits
- Symptoms at limit: Connection refused errors
- Scaling path: Add PgBouncer, horizontal scaling with load balancer

## Dependencies at Risk

**anthropic SDK version:**
- Risk: Broad version constraint `>=0.3.0` with no upper bound
- File: `setup.py`, `requirements.txt`
- Impact: Major version changes could break LLM integration
- Migration plan: Pin to compatible range: `anthropic>=0.3.0,<1.0.0`

**No lockfile for Python:**
- Risk: Different dependency versions across environments
- Impact: "Works on my machine" issues
- Migration plan: Use `pip-tools` or `poetry` for reproducible builds

## Missing Critical Features

**Test suite:**
- Problem: No automated tests exist
- Current workaround: Manual testing
- Blocks: Confident refactoring, CI/CD pipeline, regression prevention
- Implementation complexity: Medium (need to set up fixtures, mocks)

**.env.example file:**
- Problem: No template for required environment variables
- Current workaround: Users must discover variables from code
- Blocks: Easy onboarding, documentation
- Implementation complexity: Low (copy .env, remove secrets)

**Custom exception hierarchy:**
- Problem: All errors are generic `Exception`
- Current workaround: String matching on error messages
- Blocks: Proper error handling, retry logic
- Implementation complexity: Low (create exception classes)

## Test Coverage Gaps

**Database operations:**
- What's not tested: All CRUD operations in `zettl/database.py`
- Risk: Data corruption, silent failures undetected
- Priority: High
- Difficulty to test: Medium (need to mock HTTP requests)

**Authentication flow:**
- What's not tested: API key validation, JWT refresh
- Risk: Auth failures not caught until production
- Priority: High
- Difficulty to test: Medium (mock auth service responses)

**CLI commands:**
- What's not tested: All Click commands
- Risk: User-facing bugs go unnoticed
- Priority: High
- Difficulty to test: Low (Click has testing utilities)

**Cache invalidation:**
- What's not tested: Cache consistency after mutations
- Risk: Stale data served to users
- Priority: Medium
- Difficulty to test: Medium (need state tracking)

---

*Concerns audit: 2026-01-09*
*Update as issues are fixed or new ones discovered*
