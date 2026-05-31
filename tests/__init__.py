"""
Test suite for Archery Scoring System Backend.

Contains:
- conftest.py: pytest configuration and fixtures
- test_services.py: Unit tests for business logic
- test_api_endpoints.py: Integration tests for API endpoints
- test_middleware.py: Tests for middleware functionality

Running tests:
    pytest                          # Run all tests
    pytest tests/                   # Run tests directory
    pytest -v                       # Verbose output
    pytest --cov=src                # With coverage report
    pytest -k test_login            # Run specific test
    pytest -m integration           # Run only integration tests
"""
