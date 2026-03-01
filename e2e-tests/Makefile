# E2E Testing Makefile
# Provides convenient commands for running end-to-end tests

.PHONY: help install validate test-api test-chrome test-full clean

# Default target
help:
	@echo "Doc Translation System - E2E Testing"
	@echo "======================================"
	@echo ""
	@echo "Available targets:"
	@echo "  install      - Install test dependencies"
	@echo "  install-all  - Install with browser automation deps"
	@echo "  validate     - Validate test environment"
	@echo "  test-api     - Run API-only tests"
	@echo "  test-chrome  - Run Chrome DevTools MCP tests"
	@echo "  test-full    - Run complete E2E test suite"
	@echo "  clean        - Clean test artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make install"
	@echo "  make validate"
	@echo "  make test-full"

# Install test dependencies
install:
	@echo "📦 Installing E2E test dependencies..."
	uv sync
	@echo "✅ Dependencies installed"

# Install with browser automation dependencies
install-all:
	@echo "📦 Installing E2E test dependencies with browser support..."
	uv sync --extra browser
	@echo "✅ Dependencies installed"

# Validate test environment
validate:
	@echo "🔍 Validating test environment..."
	uv run python run_e2e_tests.py --mode validate

# Run API-only tests (no browser automation)
test-api:
	@echo "🔌 Running API-only tests..."
	uv run python run_e2e_tests.py --mode api

# Run Chrome DevTools MCP tests
test-chrome:
	@echo "🤖 Running Chrome DevTools MCP tests..."
	uv run python run_e2e_tests.py --mode chrome

# Run complete E2E test suite
test-full:
	@echo "🧪 Running complete E2E test suite..."
	uv run python run_e2e_tests.py --mode full

# Run tests with pytest directly
test-pytest:
	@echo "🧪 Running pytest E2E tests..."
	uv run pytest test_e2e_chrome_devtools.py -v

# Run specific test
test-workflow:
	@echo "🔄 Running user workflow test..."
	uv run pytest test_e2e_chrome_devtools.py::TestE2EChrome::test_complete_user_workflow -v

# Run responsive design tests
test-responsive:
	@echo "📱 Running responsive design tests..."
	uv run pytest test_e2e_chrome_devtools.py::TestE2EChrome::test_responsive_design_viewports -v

# Clean test artifacts
clean:
	@echo "🧹 Cleaning test artifacts..."
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -f e2e_test_report.json
	rm -rf debug/
	rm -rf screenshots/
	@echo "✅ Cleanup complete"

# Development helpers
dev-setup: install validate
	@echo "🚀 Development environment ready for E2E testing"

# CI/CD target
ci-test: validate test-api
	@echo "🤖 CI/CD tests completed"

# Lock dependencies
lock:
	@echo "🔒 Locking dependencies..."
	uv lock
	@echo "✅ Dependencies locked"