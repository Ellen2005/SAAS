"""
Groq utility — centralised client creation and model selection.

Supported current models (May 2026):
  llama-3.3-70b-versatile   — best quality, default
  llama-3.1-8b-instant      — fast, lower latency
  mixtral-8x7b-32768        — good for long context
  gemma2-9b-it              — lightweight fallback

Set GROQ_MODEL in .env to override the default.
"""
import os
import logging

logger = logging.getLogger(__name__)

# Ordered list of models to try — first available wins
_CANDIDATE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

_DECOMMISSION_SIGNALS = (
    "model not found",
    "decommission",
    "invalid_request_error",
    "invalid model",
    "unknown model",
    "does not exist",
    "no longer available",
    "deprecated",
    "not supported",
)


def get_groq_model(default: str = "llama-3.3-70b-versatile") -> str:
    """Return the configured model name, falling back to the best available."""
    return os.getenv("GROQ_MODEL", default)


def create_groq_client():
    """Create and return a Groq client. Raises RuntimeError if key is missing."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not configured in environment.")
    from groq import Groq
    return Groq(api_key=api_key)


def execute_groq_completion(
    messages: list,
    temperature: float = 0.1,
    max_tokens: int = 400,
    model: str | None = None,
) -> object:
    """
    Execute a Groq chat completion with automatic model fallback.

    Tries the requested model first, then walks through _CANDIDATE_MODELS
    until one succeeds. Raises RuntimeError only if all candidates fail.
    """
    client = create_groq_client()
    requested = model or get_groq_model()

    # Build ordered candidate list: requested first, then the rest
    candidates = [requested] + [m for m in _CANDIDATE_MODELS if m != requested]
    seen: set[str] = set()
    errors: list[str] = []

    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            return client.chat.completions.create(
                model=candidate,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            msg = str(exc).lower()
            if any(sig in msg for sig in _DECOMMISSION_SIGNALS):
                logger.warning(f"Groq model '{candidate}' unavailable: {exc}")
                errors.append(f"{candidate}: {exc}")
                continue
            # Non-model error (auth, rate limit, network) — raise immediately
            raise

    raise RuntimeError(
        f"All Groq model candidates failed. Errors: {' | '.join(errors)}"
    )
