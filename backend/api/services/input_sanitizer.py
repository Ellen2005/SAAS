"""
Input Sanitization Service
==========================
Centralized input cleaning and validation for all user-facing endpoints.

Handles:
  - XSS prevention (HTML entity encoding)
  - SQL keyword detection in natural language
  - Prompt injection detection (system prompt override attempts)
  - Path traversal prevention
  - Null byte injection prevention
  - Unicode normalization
  - Length limits
"""
import re
import html
import unicodedata
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Prompt Injection Patterns ────────────────────────────────────────────────

_PROMPT_INJECTION_PATTERNS = [
    # System prompt override attempts
    (re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE), "Prompt override attempt"),
    (re.compile(r"disregard\s+(all\s+)?prior\s+instructions", re.IGNORECASE), "Prompt override attempt"),
    (re.compile(r"forget\s+(all\s+)?your\s+instructions", re.IGNORECASE), "Prompt override attempt"),
    (re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE), "Persona override attempt"),
    (re.compile(r"act\s+as\s+if\s+you\s+are", re.IGNORECASE), "Persona override attempt"),
    (re.compile(r"pretend\s+you\s+are", re.IGNORECASE), "Persona override attempt"),

    # Data exfiltration attempts
    (re.compile(r"(show|print|output|reveal)\s+(me\s+)?(your|the)\s+(system\s+)?prompt", re.IGNORECASE), "Prompt exfiltration attempt"),
    (re.compile(r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions)", re.IGNORECASE), "Prompt exfiltration attempt"),

    # Role manipulation
    (re.compile(r"you\s+are\s+(now\s+)?DAN\b", re.IGNORECASE), "DAN jailbreak attempt"),
    (re.compile(r"do\s+anything\s+now", re.IGNORECASE), "DAN jailbreak attempt"),
]

# ── Dangerous HTML/Script Patterns ───────────────────────────────────────────

_XSS_PATTERNS = [
    re.compile(r"<script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"<iframe[^>]*>", re.IGNORECASE),
    re.compile(r"<object[^>]*>", re.IGNORECASE),
    re.compile(r"<embed[^>]*>", re.IGNORECASE),
    re.compile(r"<link[^>]*>", re.IGNORECASE),
]


class InputSanitizer:
    """
    Sanitizes user input for safety.

    Usage:
        sanitizer = InputSanitizer()

        # Full sanitization
        clean = sanitizer.sanitize("Hello <script>alert('xss')</script> World")

        # Check for prompt injection
        result = sanitizer.check_prompt_injection("Ignore previous instructions and...")
        # result = {"safe": False, "threats": ["Prompt override attempt"]}

        # Path traversal check
        safe = sanitizer.sanitize_path("../../etc/passwd")
        # safe = "etc/passwd"
    """

    MAX_LENGTH = 10000
    MAX_PROMPT_LENGTH = 5000

    def sanitize(self, text: str, max_length: Optional[int] = None) -> str:
        """
        Full sanitization pipeline:
        1. Unicode normalization
        2. Null byte removal
        3. HTML entity encoding
        4. Length truncation
        """
        if not text:
            return ""

        # 1. Unicode normalization
        text = unicodedata.normalize("NFC", text)

        # 2. Null byte removal
        text = text.replace("\x00", "")

        # 3. HTML entity encoding (prevent XSS)
        text = html.escape(text)

        # 4. Strip excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {3,}", "  ", text)

        # 5. Truncate
        limit = max_length or self.MAX_LENGTH
        if len(text) > limit:
            text = text[:limit]

        return text.strip()

    def sanitize_for_llm(self, prompt: str) -> str:
        """
        Sanitize a prompt specifically for LLM input.
        More aggressive than general sanitization.
        """
        if not prompt:
            return ""

        # Unicode normalization
        prompt = unicodedata.normalize("NFC", prompt)

        # Null byte removal
        prompt = prompt.replace("\x00", "")

        # Strip HTML tags (but keep content)
        prompt = re.sub(r"<[^>]+>", "", prompt)

        # Strip control characters
        prompt = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", prompt)

        # Length limit
        if len(prompt) > self.MAX_PROMPT_LENGTH:
            prompt = prompt[:self.MAX_PROMPT_LENGTH]

        return prompt.strip()

    def sanitize_path(self, path: str) -> str:
        """Remove path traversal sequences."""
        if not path:
            return ""
        # Remove null bytes
        path = path.replace("\x00", "")
        # Remove ../ and ..\\ sequences
        path = re.sub(r"\.\.[\\/]", "", path)
        # Remove leading slashes
        path = path.lstrip("/\\")
        # Normalize forward slashes
        path = path.replace("\\", "/")
        return path

    def check_prompt_injection(self, text: str) -> dict:
        """
        Check if text contains prompt injection attempts.
        Returns: {safe: bool, threats: list[str]}
        """
        if not text:
            return {"safe": True, "threats": []}

        threats = []
        for pattern, message in _PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                threats.append(message)

        return {
            "safe": len(threats) == 0,
            "threats": list(set(threats)),
        }

    def check_xss(self, text: str) -> dict:
        """
        Check if text contains XSS attempts.
        Returns: {safe: bool, threats: list[str]}
        """
        if not text:
            return {"safe": True, "threats": []}

        threats = []
        for pattern in _XSS_PATTERNS:
            if pattern.search(text):
                threats.append(f"XSS pattern: {pattern.pattern[:50]}")

        return {
            "safe": len(threats) == 0,
            "threats": threats,
        }

    def validate_length(self, text: str, field_name: str = "input", max_length: Optional[int] = None) -> Optional[str]:
        """Validate text length. Returns error message or None if valid."""
        limit = max_length or self.MAX_LENGTH
        if len(text) > limit:
            return f"{field_name} exceeds maximum length of {limit} characters"
        return None

    def clean_nlq_input(self, question: str) -> str:
        """
        Clean a natural language question for the NLQ pipeline.
        Removes potential injection attempts while preserving meaning.
        """
        if not question:
            return ""

        # Basic sanitization
        question = self.sanitize_for_llm(question)

        # Remove SQL-like keywords that shouldn't appear in natural language
        sql_keywords = [
            "DROP TABLE", "DELETE FROM", "INSERT INTO", "UPDATE SET",
            "ALTER TABLE", "CREATE TABLE", "TRUNCATE", "EXEC",
        ]
        for kw in sql_keywords:
            question = re.sub(re.escape(kw), "", question, flags=re.IGNORECASE)

        return question.strip()


# Module-level singleton
_sanitizer = InputSanitizer()


def sanitize_input(text: str) -> str:
    """Module-level convenience function."""
    return _sanitizer.sanitize(text)


def sanitize_for_llm(prompt: str) -> str:
    """Module-level convenience function."""
    return _sanitizer.sanitize_for_llm(prompt)


def check_prompt_injection(text: str) -> dict:
    """Module-level convenience function."""
    return _sanitizer.check_prompt_injection(text)
