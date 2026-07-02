"""
Deployment validation tests - ensure the application can start and handle requests properly.
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def valid_env():
    """Fixture providing valid environment variables."""
    return {
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_KEY": "test-key",
        "GROQ_API_KEY": "test-groq-key",
        "INSTITUTION_NAME": "Test Institution",
        "ENVIRONMENT": "testing",
    }


@pytest.fixture
def invalid_env():
    """Fixture with missing required environment variables."""
    return {
        "INSTITUTION_NAME": "Test Institution",
    }


def test_environment_validation_with_valid_env(valid_env):
    """Test that environment validation passes with all required variables."""
    with patch.dict(os.environ, valid_env, clear=False):
        from backend.api.core.env_config import validate_environment
        result = validate_environment()
        assert result["valid"] is True
        assert len(result["missing"]) == 0
        assert len(result["errors"]) == 0


def test_environment_validation_with_invalid_env(invalid_env):
    """Test that environment validation fails with missing variables."""
    with patch.dict(os.environ, invalid_env, clear=True):
        from backend.api.core.env_config import validate_environment, EnvironmentValidationError
        with pytest.raises(EnvironmentValidationError):
            validate_environment()


def test_cors_origins_development():
    """Test CORS origins configuration in development."""
    with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=False):
        from backend.api.core.env_config import configure_cors_origins
        origins = configure_cors_origins()
        assert "http://localhost:5000" in origins
        assert "http://localhost:5173" in origins


def test_cors_origins_production():
    """Test CORS origins configuration in production."""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "FRONTEND_URL": "https://myapp.com"
    }, clear=False):
        from backend.api.core.env_config import configure_cors_origins
        origins = configure_cors_origins()
        assert "https://myapp.com" in origins


def test_cors_origins_custom():
    """Test CORS origins from custom configuration."""
    with patch.dict(os.environ, {
        "CORS_ORIGINS": "https://app1.com,https://app2.com"
    }, clear=False):
        from backend.api.core.env_config import configure_cors_origins
        origins = configure_cors_origins()
        assert "https://app1.com" in origins
        assert "https://app2.com" in origins


@pytest.mark.integration
def test_application_startup_with_mocked_services(valid_env):
    """Test that the FastAPI application starts successfully."""
    with patch.dict(os.environ, valid_env, clear=False):
        with patch('backend.api.core.supabase_client.get_supabase'):
            with patch('backend.api.core.scheduler.start_scheduler'):
                with patch('backend.api.core.scheduler.shutdown_scheduler'):
                    try:
                        from backend.api.main import app
                        client = TestClient(app)
                        response = client.get("/api/ping")
                        assert response.status_code == 200
                        data = response.json()
                        assert data["ok"] is True
                        assert "timestamp" in data
                    except Exception as e:
                        pytest.fail(f"Application failed to start: {str(e)}")


@pytest.mark.integration
def test_favicon_endpoint():
    """Test favicon endpoint returns 204."""
    with patch('backend.api.core.supabase_client.get_supabase'):
        with patch('backend.api.core.scheduler.start_scheduler'):
            with patch('backend.api.core.scheduler.shutdown_scheduler'):
                from backend.api.main import app
                client = TestClient(app)
                response = client.get("/favicon.ico")
                assert response.status_code == 204


@pytest.mark.integration
def test_root_endpoint():
    """Test root endpoint returns welcome message."""
    with patch('backend.api.core.supabase_client.get_supabase'):
        with patch('backend.api.core.scheduler.start_scheduler'):
            with patch('backend.api.core.scheduler.shutdown_scheduler'):
                from backend.api.main import app
                client = TestClient(app)
                response = client.get("/")
                assert response.status_code == 200
                data = response.json()
                assert "message" in data


@pytest.mark.integration
def test_security_headers():
    """Test that security headers are present in responses."""
    with patch('backend.api.core.supabase_client.get_supabase'):
        with patch('backend.api.core.scheduler.start_scheduler'):
            with patch('backend.api.core.scheduler.shutdown_scheduler'):
                from backend.api.main import app
                client = TestClient(app)
                response = client.get("/")
                
                assert "X-Content-Type-Options" in response.headers
                assert response.headers["X-Content-Type-Options"] == "nosniff"
                
                assert "X-Frame-Options" in response.headers
                assert response.headers["X-Frame-Options"] == "DENY"
                
                assert "X-XSS-Protection" in response.headers
                assert response.headers["X-XSS-Protection"] == "1; mode=block"


@pytest.mark.integration
def test_401_on_missing_auth():
    """Test that protected endpoints return 401 without authentication."""
    with patch('backend.api.core.supabase_client.get_supabase'):
        with patch('backend.api.core.scheduler.start_scheduler'):
            with patch('backend.api.core.scheduler.shutdown_scheduler'):
                from backend.api.main import app
                client = TestClient(app)
                
                # Endpoints that require authentication
                response = client.get("/api/users/me")
                assert response.status_code == 401


@pytest.mark.integration
def test_422_on_invalid_request():
    """Test that invalid requests return 422."""
    with patch('backend.api.core.supabase_client.get_supabase'):
        with patch('backend.api.core.scheduler.start_scheduler'):
            with patch('backend.api.core.scheduler.shutdown_scheduler'):
                from backend.api.main import app
                client = TestClient(app)
                
                # Send invalid request to POST endpoint
                response = client.post("/api/analysis/run", json={})
                # Should return either 422 (validation error) or 401 (auth required)
                assert response.status_code in [401, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
