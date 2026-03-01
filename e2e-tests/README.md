# Doc Translation System - E2E Tests

End-to-end and integration tests for the Doc Translation System.

## Quick Start

```bash
cd e2e-tests
uv sync                      # Install dependencies
uv run python run_e2e_tests.py   # Run tests
```

## Prerequisites

Start both services before running E2E tests:

```bash
# Terminal 1: Backend
cd backend
uv run main.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

## Test Files

| File | Description |
|------|-------------|
| `run_e2e_tests.py` | Unified E2E test runner with environment validation |
| `test_e2e_chrome_devtools.py` | API and browser automation tests |
| `e2e_chrome_runner.py` | Chrome DevTools MCP automation runner |
| `test_cross_platform.py` | Cross-platform compatibility tests |
| `e2e_config.json` | Test configuration (URLs, credentials, timeouts) |

## Running Tests

```bash
cd e2e-tests

# Full E2E suite
uv run python run_e2e_tests.py --mode full

# API-only tests (no browser)
uv run python run_e2e_tests.py --mode api

# Environment validation only
uv run python run_e2e_tests.py --mode validate

# Using pytest directly
uv run pytest test_e2e_chrome_devtools.py -v
uv run pytest test_cross_platform.py -v

# Run specific test markers
uv run pytest -m "e2e and api" -v
uv run pytest -m "not browser" -v
```

## Test Markers

- `e2e` - End-to-end tests requiring running services
- `api` - API-only tests (no browser automation)
- `browser` - Browser automation tests (requires Chrome DevTools MCP)
- `slow` - Slow running tests

## E2E Test Coverage

### API Tests
- Health endpoint validation
- Authentication flow (login, token verification)
- Language pairs query and management
- Model configuration query
- File upload via REST endpoint
- Jobs query and creation
- Error handling (unauthenticated requests, invalid login)

### Browser Tests (with Chrome DevTools MCP)
- Complete user workflow: login → upload → translate → download
- Language pair management UI
- Error scenarios and recovery
- Responsive design at different viewports
- Real-time progress updates

### Cross-Platform Tests
- Platform detection (Windows, macOS, Linux)
- File path handling and normalization
- Unicode filename support
- Document file creation and manipulation
- Concurrent API requests

## Configuration

Edit `e2e_config.json` to customize:

```json
{
  "test_environment": {
    "backend_url": "http://localhost:8000",
    "frontend_url": "http://localhost:5173",
    "graphql_endpoint": "http://localhost:8000/graphql"
  },
  "test_credentials": {
    "username": "admin",
    "password": "admin123"
  },
  "test_timeouts": {
    "translation_job": 120,
    "polling_interval": 2
  }
}
```

## Chrome DevTools MCP (Optional)

For browser automation tests, configure Chrome DevTools MCP in `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "uvx",
      "args": ["mcp-chrome-devtools@latest"],
      "disabled": false
    }
  }
}
```

## Test Reports

- **JSON Report**: `e2e_test_report.json` (generated after Chrome MCP tests)
- **Console Output**: Real-time progress and results

## Environment Variables

Override configuration via environment variables:

```bash
BACKEND_URL=http://localhost:8000 \
FRONTEND_URL=http://localhost:5173 \
TEST_TIMEOUT=600 \
uv run python run_e2e_tests.py
```

---

[Back to main README](../README.md)
