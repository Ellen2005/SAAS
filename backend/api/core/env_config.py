"""
Environment validation and error handling utilities for deployment.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "DATABASE_URL",
    "GROQ_API_KEY",
]

OPTIONAL_BUT_RECOMMENDED = [
    "BREVO_API_KEY",
    "FRONTEND_URL",
    "EMAIL_SENDER_ADDRESS",
]


class EnvironmentValidationError(Exception):
    """Raised when environment validation fails."""
    pass


def validate_environment() -> dict:
    """
    Validate that all required environment variables are present and accessible.
    Raises EnvironmentValidationError if validation fails.
    Returns a dict with validation results.
    """
    results = {
        "valid": True,
        "missing": [],
        "warnings": [],
        "errors": [],
    }
    
    # Check required variables
    for var_name in REQUIRED_ENV_VARS:
        value = os.getenv(var_name)
        if not value or not value.strip():
            results["missing"].append(var_name)
            results["valid"] = False
            results["errors"].append(f"Missing required environment variable: {var_name}")
    
    # Check optional but recommended variables
    for var_name in OPTIONAL_BUT_RECOMMENDED:
        value = os.getenv(var_name)
        if not value or not value.strip():
            results["warnings"].append(f"Missing recommended environment variable: {var_name}")
    
    # Validate specific formats
    db_url = os.getenv("DATABASE_URL")
    if db_url and not db_url.startswith(("postgresql://", "postgresql+psycopg2://", "mysql://", "sqlite://", "oracle://")):
        results["warnings"].append("DATABASE_URL has unexpected format")
    
    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url and "supabase.co" not in supabase_url:
        results["warnings"].append("SUPABASE_URL does not appear to be a valid Supabase URL")
    
    if results["errors"]:
        error_msg = "\n".join(results["errors"])
        logger.error(f"Environment validation failed:\n{error_msg}")
        raise EnvironmentValidationError(error_msg)
    
    if results["warnings"]:
        for warning in results["warnings"]:
            logger.warning(warning)
    
    return results


def get_safe_env(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """
    Safely get an environment variable with validation.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: If True, raises error if not found
    
    Returns:
        The environment variable value
        
    Raises:
        EnvironmentValidationError if required and not found
    """
    value = os.getenv(key, default)
    if required and (not value or not value.strip()):
        raise EnvironmentValidationError(f"Required environment variable not found: {key}")
    return value or ""


def configure_cors_origins() -> list:
    """
    Get CORS origins from environment or use defaults.
    Supports comma-separated list in CORS_ORIGINS env var.
    """
    cors_env = os.getenv("CORS_ORIGINS")
    if cors_env:
        return [origin.strip() for origin in cors_env.split(",")]
    
    # Defaults based on environment
    env = os.getenv("ENVIRONMENT", "development").lower()
    if env == "production":
        frontend_url = os.getenv("FRONTEND_URL")
        return [frontend_url] if frontend_url else ["https://yourdomain.com"]
    
    # Development defaults
    return [
        "http://localhost:5000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:4173",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:4173",
    ]
