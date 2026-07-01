"""
Dependency Injection Container
==============================
Provides singleton access to shared services.
Avoids creating new instances on every request.
"""
from functools import lru_cache
from ..core.supabase_client import get_supabase


@lru_cache(maxsize=1)
def get_db():
    """Get the singleton Supabase client."""
    return get_supabase()


@lru_cache(maxsize=1)
def get_prompt_manager():
    """Get the singleton PromptManager."""
    from ..services.prompt_manager import PromptManager
    return PromptManager(get_db())


@lru_cache(maxsize=1)
def get_semantic_layer_factory():
    """
    Returns a factory function that creates per-request SemanticLayer instances.
    SemanticLayer is per-user (loads user-specific mappings), so we don't
    singleton it directly.
    """
    from ..services.semantic_layer import SemanticLayer

    def create(user_id: str):
        return SemanticLayer(get_db(), user_id)
    return create


@lru_cache(maxsize=1)
def get_audit_service():
    """Get the singleton AuditService."""
    from ..services.audit_service import AuditService
    return AuditService(get_db())


@lru_cache(maxsize=1)
def get_ai_governance():
    """Get the singleton AIGovernance."""
    from ..services.ai_governance import AIGovernance
    return AIGovernance(get_db())


@lru_cache(maxsize=1)
def get_ai_monitor():
    """Get the singleton AIMonitor."""
    from ..services.ai_monitor import AIMonitor
    return AIMonitor(get_db())


@lru_cache(maxsize=1)
def get_confidence_engine():
    """Get the singleton ConfidenceEngine."""
    from ..services.confidence_engine import ConfidenceEngine
    return ConfidenceEngine(get_db())


@lru_cache(maxsize=1)
def get_explainability_engine():
    """Get the singleton ExplainabilityEngine."""
    from ..services.explainability_engine import ExplainabilityEngine
    return ExplainabilityEngine()


@lru_cache(maxsize=1)
def get_recommendation_engine():
    """Get the singleton RecommendationEngine."""
    from ..services.recommendation_engine import RecommendationEngine
    return RecommendationEngine()


@lru_cache(maxsize=1)
def get_dependency_analyzer():
    """Get the singleton DependencyAnalyzer."""
    from ..services.dependency_analyzer import DependencyAnalyzer
    return DependencyAnalyzer(get_db())


def clear_cache():
    """Clear all cached singletons (for testing or config changes)."""
    get_db.cache_clear()
    get_prompt_manager.cache_clear()
    get_semantic_layer_factory.cache_clear()
    get_audit_service.cache_clear()
    get_ai_governance.cache_clear()
    get_ai_monitor.cache_clear()
    get_confidence_engine.cache_clear()
    get_explainability_engine.cache_clear()
    get_recommendation_engine.cache_clear()
    get_dependency_analyzer.cache_clear()
