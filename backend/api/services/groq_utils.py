"""
Groq utility — centralised client creation and model selection.

Supported current models (June 2026):
  qwen2.5-72b-instruct      — best quality, default (replaces deprecated llama-3.3-70b)
  gpt-oss-120b              — alternative large model
  qwen2.5-27b-instruct      — balanced performance
  llama-3.1-8b-instant      — fast, lower latency
  gemma2-9b-it              — lightweight fallback

Set GROQ_MODEL in .env to override the default.
"""
import os
import logging

logger = logging.getLogger(__name__)

# Ordered list of models to try — first available wins
_CANDIDATE_MODELS = [
    "qwen2.5-72b-instruct",
    "gpt-oss-120b",
    "qwen2.5-27b-instruct",
    "llama-3.1-8b-instant",
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


def get_groq_model(default: str = "qwen2.5-72b-instruct") -> str:
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
    messages: list | None = None,
    prompt: str | None = None,
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

    # Normalize: allow single prompt string for backward compatibility
    if prompt and not messages:
        messages = [{"role": "user", "content": prompt}]
    if not messages:
        raise ValueError("Either 'messages' or 'prompt' must be provided.")

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
