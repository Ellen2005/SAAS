import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Ensure required env vars are set for tests."""
    env_defaults = {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
        "GROQ_API_KEY": "test-groq-key",
        "INSTITUTION_NAME": "Test Analytics",
    }
    with patch.dict(os.environ, env_defaults, clear=False):
        yield


@pytest.fixture
def mock_supabase():
    """Mock Supabase client that returns empty data."""
    mock = MagicMock()
    mock.auth.get_user.return_value = MagicMock(user={"id": "test-user-123"})
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[])
    mock.table.return_value = table_mock
    return mock


@pytest.fixture
def client(mock_supabase):
    """FastAPI TestClient with mocked dependencies."""
    with patch("api.core.supabase_client.get_supabase", return_value=mock_supabase), \
         patch("api.core.auth.get_supabase", return_value=mock_supabase):
        from api.main import app
        yield TestClient(app)


@pytest.fixture
def test_user_id():
    """Return a fixed test user ID."""
    return "test-user-123"


@pytest.fixture
def mock_resolve_user_id(test_user_id):
    """Patch resolve_user_id to return a test user ID."""
    with patch("api.core.auth.resolve_user_id", return_value=test_user_id):
        yield test_user_id


@pytest.fixture
def mock_require_role(test_user_id):
    """Patch require_role to return a test context dict."""
    def _make_context(roles=None):
        context = {
            "user_id": test_user_id,
            "role": roles[0] if roles else "admin",
            "department_id": "dept-1",
            "department_name": "Test Department",
        }
        return context

    def _require_role(allowed_roles):
        def role_checker():
            context = _make_context(allowed_roles)
            return context
        return role_checker

    with patch("api.core.auth.require_role", side_effect=_require_role):
        yield _make_context
