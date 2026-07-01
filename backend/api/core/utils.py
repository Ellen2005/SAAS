"""
Core Utilities
==============
Shared utility functions used across the application.
Eliminates duplicated helper functions (e.g., _safe_data in 8 routers).
"""
from typing import Any, Optional


def safe_data(response) -> list:
    """
    Safely extract data list from a Supabase response object.
    Handles both object-style (.data attribute) and dict-style responses.
    Replaces the 8 duplicated _safe_data() definitions across routers.
    """
    if response is None:
        return []
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        return response.get("data", [])
    data = getattr(response, "data", None)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return []


def safe_get(data: Any, *keys, default=None) -> Any:
    """
    Safely traverse nested dict/list structure.
    
    Example:
        safe_get(response, "data", 0, "name", default="unknown")
    """
    current = data
    for key in keys:
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(key, default)
        elif isinstance(current, (list, tuple)) and isinstance(key, int):
            current = current[key] if 0 <= key < len(current) else default
        else:
            return default
    return current if current is not None else default


def extract_user_id(user) -> str:
    """Extract user ID from various user object formats (dict or object)."""
    if isinstance(user, dict):
        return str(user.get("id") or user.get("user_id", ""))
    return str(getattr(user, "id", "") or getattr(user, "user_id", ""))


def extract_user_email(user) -> str:
    """Extract email from various user object formats."""
    if isinstance(user, dict):
        return user.get("email", "")
    return getattr(user, "email", "")
