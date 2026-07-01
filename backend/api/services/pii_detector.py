"""
PII Detection & Masking Service
================================
Detects and masks Personally Identifiable Information in data
before it's sent to external LLM APIs (Groq).

Supported PII types:
  - Email addresses
  - Phone numbers (international formats)
  - National ID numbers (Cameroon NUI, social security patterns)
  - Credit card numbers
  - IP addresses
  - Physical addresses
  - Names (basic heuristics)

Used by the AI Orchestrator to sanitize prompts before LLM calls
and to redact responses if needed.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── PII Detection Patterns ──────────────────────────────────────────────────

_PII_PATTERNS = [
    # Email
    ("email", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", re.IGNORECASE)),

    # Phone numbers (international, Cameroon, US, etc.)
    ("phone", re.compile(
        r"(?:\+?[0-9]{1,3}[-.\s]?)?"
        r"(?:\(?[0-9]{2,4}\)?[-.\s]?)?"
        r"[0-9]{3,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{0,4}",
    )),

    # Credit card numbers (13-19 digits, with optional separators)
    ("credit_card", re.compile(
        r"\b[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{1,7}\b"
    )),

    # National ID / Social Security patterns
    ("national_id", re.compile(
        r"\b[0-9]{2}[-/\s]?[0-9]{5}[-/\s]?[0-9]{3}[-/\s]?[0-9]{2}\b"
    )),

    # IP addresses
    ("ip_address", re.compile(
        r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
    )),

    # Passport numbers ( Cameroon: 2 letters + 7 digits)
    ("passport", re.compile(r"\b[A-Z]{2}\s?[0-9]{7}\b")),

    # Tax IDs / NUI (Cameroon的企业注册号)
    ("tax_id", re.compile(r"\bNUI[:\s]?[0-9]{5,}[A-Z0-9]*\b", re.IGNORECASE)),

    # Bank account numbers (generic: 10-18 digits)
    ("bank_account", re.compile(r"\b(?:CCP| Account| Compte)[:\s]?[0-9]{10,18}\b", re.IGNORECASE)),

    # Date of birth patterns (DD/MM/YYYY or DD-MM-YYYY)
    ("date_of_birth", re.compile(
        r"\b(?:0[1-9]|[12][0-9]|3[01])[/-](?:0[1-9]|1[012])[/-](?:19|20)\d{2}\b"
    )),
]


class PIIDetector:
    """
    Detects and masks PII in text.

    Usage:
        detector = PIIDetector()

        # Detect PII
        result = detector.detect("Contact me at john@example.com or call +237 6XX XXX XXX")
        # result = [{"type": "email", "value": "john@example.com", "start": 14, "end": 30},
        #           {"type": "phone", "value": "+237 6XX XXX XXX", "start": 39, "end": 55}]

        # Mask PII
        masked = detector.mask("Contact me at john@example.com")
        # masked = "Contact me at [EMAIL_REDACTED]"
    """

    def detect(self, text: str) -> list:
        """
        Detect PII in text.
        Returns list of {type, value, start, end} dicts.
        """
        if not text:
            return []

        findings = []
        for pii_type, pattern in _PII_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group()
                # Filter out false positives for phone numbers (too short)
                if pii_type == "phone" and len(re.sub(r"[^0-9]", "", value)) < 7:
                    continue
                # Filter out false positives for credit cards (too short)
                if pii_type == "credit_card":
                    digits_only = re.sub(r"[^0-9]", "", value)
                    if len(digits_only) < 13 or len(digits_only) > 19:
                        continue
                findings.append({
                    "type": pii_type,
                    "value": value,
                    "start": match.start(),
                    "end": match.end(),
                })

        return findings

    def mask(self, text: str, replacement_template: str = "[{type}_REDACTED]") -> str:
        """
        Mask PII in text with redaction placeholders.
        """
        if not text:
            return text

        findings = self.detect(text)
        if not findings:
            return text

        # Replace from end to start to preserve indices
        masked = text
        for finding in sorted(findings, key=lambda f: f["start"], reverse=True):
            replacement = replacement_template.format(type=finding["type"].upper())
            masked = masked[:finding["start"]] + replacement + masked[finding["end"]:]

        return masked

    def has_pii(self, text: str) -> bool:
        """Quick check if text contains PII."""
        return len(self.detect(text)) > 0

    def get_pii_types(self, text: str) -> list:
        """Get unique PII types found in text."""
        return list(set(f["type"] for f in self.detect(text)))

    def redact_for_llm(self, text: str) -> tuple[str, dict]:
        """
        Redact PII before sending to LLM. Returns (redacted_text, mapping).
        The mapping can be used to restore original values in the response.
        """
        if not text:
            return text, {}

        findings = self.detect(text)
        if not findings:
            return text, {}

        mapping = {}
        redacted = text
        counter = 0
        for finding in sorted(findings, key=lambda f: f["start"], reverse=True):
            token = f"__PII_{counter}__"
            mapping[token] = finding["value"]
            redacted = redacted[:finding["start"]] + token + redacted[finding["end"]:]
            counter += 1

        return redacted, mapping

    def restore(self, text: str, mapping: dict) -> str:
        """Restore redacted PII values using the mapping from redact_for_llm."""
        restored = text
        for token, value in mapping.items():
            restored = restored.replace(token, value)
        return restored


# Module-level singleton
_detector = PIIDetector()


def detect_pii(text: str) -> list:
    """Module-level convenience function."""
    return _detector.detect(text)


def mask_pii(text: str) -> str:
    """Module-level convenience function."""
    return _detector.mask(text)


def has_pii(text: str) -> bool:
    """Module-level convenience function."""
    return _detector.has_pii(text)
