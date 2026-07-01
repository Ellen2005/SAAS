import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


class TestGetCurrentUser:
    def test_get_current_user_no_header(self, client):
        response = client.get("/api/summary")
        assert response.status_code in (401, 422)

    def test_get_current_user_invalid_token(self, client):
        with patch("api.core.auth.get_supabase") as mock_sb:
            mock_sb.return_value.auth.get_user.side_effect = Exception("invalid")
            response = client.get(
                "/api/summary",
                headers={"Authorization": "Bearer invalid-token"},
            )
            assert response.status_code == 401


class TestResolveUserId:
    def test_resolve_user_id_no_header(self, client):
        response = client.get("/api/summary")
        assert response.status_code in (401, 422)


class TestRequireRole:
    def test_require_role_wrong_role(self, client, test_user_id):
        with patch("api.core.auth.get_user_info") as mock_info, \
             patch("api.core.auth.resolve_user_id", return_value=test_user_id):
            mock_info.return_value = {
                "user_id": test_user_id,
                "role": "viewer",
                "department_id": "dept-1",
                "department_name": "Test",
            }
            from api.core.auth import require_role
            checker = require_role(["admin", "manager"])
            with pytest.raises(HTTPException) as exc_info:
                checker()
            assert exc_info.value.status_code == 403

    def test_require_role_correct_role(self, test_user_id):
        with patch("api.core.auth.get_user_info") as mock_info, \
             patch("api.core.auth.resolve_user_id", return_value=test_user_id):
            mock_info.return_value = {
                "user_id": test_user_id,
                "role": "admin",
                "department_id": "dept-1",
                "department_name": "Test",
            }
            from api.core.auth import require_role
            checker = require_role(["admin"])
            # The returned function uses Depends, so we extract the inner closure
            # by calling the function's code with the mocked resolve_user_id
            import inspect
            # Get the inner role_checker closure
            role_checker = checker.__func__ if hasattr(checker, '__func__') else checker
            # Directly call with the resolved user id
            context = role_checker(resolved_user_id=test_user_id)
            assert context["user_id"] == test_user_id
            assert context["role"] == "admin"
