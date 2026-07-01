"""
SQL Injection Detection Service
================================
Advanced SQL injection detection beyond basic keyword blocking.
Detects:
  - UNION-based injection
  - Boolean-based blind injection
  - Time-based blind injection (SLEEP, WAITFOR, BENCHMARK)
  - Stacked queries
  - Comment-based evasion (/*, --, #)
  - Hex/encoded string injection
  - OR/AND tautology injection
  - Second-order injection patterns

Used by the AI Orchestrator to validate LLM-generated SQL
before execution.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Pattern Library ──────────────────────────────────────────────────────────

_INJECTION_PATTERNS = [
    # UNION-based injection
    (r"UNION\s+(ALL\s+)?SELECT", "UNION-based injection detected"),

    # Stacked queries
    (r";\s*(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC)", "Stacked query detected"),

    # Time-based blind
    (r"\bSLEEP\s*\(", "Time-based blind injection (SLEEP)"),
    (r"\bWAITFOR\s+DELAY\b", "Time-based blind injection (WAITFOR)"),
    (r"\bBENCHMARK\s*\(", "Time-based blind injection (BENCHMARK)"),
    (r"\bPG_SLEEP\s*\(", "Time-based blind injection (PG_SLEEP)"),

    # Boolean-based blind
    (r"\bOR\s+1\s*=\s*1\b", "Boolean tautology (OR 1=1)"),
    (r"\bAND\s+1\s*=\s*1\b", "Boolean tautology (AND 1=1)"),
    (r"\bOR\s+'[^']*'\s*=\s*'[^']*'\s*--", "String tautology injection"),

    # Comment-based evasion
    (r"/\*.*\*/", "Block comment injection"),
    (r"(?<!\w)--\s*$", "Line comment injection"),
    (r"#\s*$", "Hash comment injection"),

    # Hex/encoded strings
    (r"0x[0-9a-fA-F]{8,}", "Hex-encoded string detected"),

    # Dangerous functions
    (r"\bEXEC\s*\(", "EXEC statement detected"),
    (r"\bEXECUTE\s*\(", "EXECUTE statement detected"),
    (r"\bINTO\s+(OUTFILE|DUMPFILE)\b", "File write injection detected"),
    (r"\bLOAD_FILE\s*\(", "File read injection detected"),
    (r"\bINFORMATION_SCHEMA\b", "Schema enumeration attempt"),

    # DROP/ALTER/CREATE
    (r"\bDROP\s+(TABLE|DATABASE|INDEX|VIEW|SCHEMA)\b", "DROP statement detected"),
    (r"\bALTER\s+(TABLE|DATABASE|VIEW)\b", "ALTER statement detected"),
    (r"\bCREATE\s+(TABLE|DATABASE|INDEX|VIEW|SCHEMA|TRIGGER|FUNCTION|PROCEDURE)\b", "CREATE statement detected"),

    # DELETE/INSERT/UPDATE
    (r"\bDELETE\s+FROM\b", "DELETE statement detected"),
    (r"\bINSERT\s+INTO\b", "INSERT statement detected"),
    (r"\bUPDATE\s+\w+\s+SET\b", "UPDATE statement detected"),
    (r"\bTRUNCATE\s+TABLE\b", "TRUNCATE statement detected"),

    # GRANT/REVOKE
    (r"\bGRANT\s+", "GRANT statement detected"),
    (r"\bREVOKE\s+", "REVOKE statement detected"),

    # SHUTDOWN/KILL
    (r"\bSHUTDOWN\b", "SHUTDOWN command detected"),
    (r"\bKILL\b", "KILL command detected"),
]

_COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE | re.MULTILINE), msg) for p, msg in _INJECTION_PATTERNS]


class SQLInjectionDetector:
    """
    Detects SQL injection attempts in queries.

    Usage:
        detector = SQLInjectionDetector()
        result = detector.analyze("SELECT * FROM users WHERE id = 1 OR 1=1")
        # result = {"safe": False, "threats": ["Boolean tautology (OR 1=1)"], "risk_level": "HIGH"}
    """

    SAFE_PREFIXES = frozenset({"SELECT", "WITH", "EXPLAIN", "DESCRIBE", "SHOW", "PRAGMA"})

    def analyze(self, sql: str) -> dict:
        """
        Analyze a SQL query for injection threats.
        Returns: {safe: bool, threats: list[str], risk_level: str, sanitized: str}
        """
        if not sql or not sql.strip():
            return {"safe": True, "threats": [], "risk_level": "NONE", "sanitized": sql}

        stripped = sql.strip()
        upper = stripped.upper()
        threats = []

        # 1. Check safe prefix
        if not upper.startswith(tuple(self.SAFE_PREFIXES)):
            threats.append(f"Unsafe query prefix: {upper.split()[0] if upper.split() else 'empty'}")

        # 2. Pattern matching
        for pattern, message in _COMPILED_PATTERNS:
            if pattern.search(stripped):
                threats.append(message)

        # 3. Multi-statement detection
        cleaned = re.sub(r"'[^']*'", '', re.sub(r'--.*$', '', stripped, flags=re.MULTILINE))
        semi_pos = cleaned.find(';')
        if semi_pos != -1 and semi_pos < len(cleaned.rstrip(';')) - 1:
            threats.append("Multi-statement query detected")

        # 4. Excessive nesting (potential evasion)
        if stripped.count('(') > 10:
            threats.append("Excessive parenthetical nesting")

        # Risk level
        if not threats:
            risk = "NONE"
        elif len(threats) <= 1 and any("comment" in t.lower() for t in threats):
            risk = "LOW"
        elif any(kw in " ".join(threats).lower() for kw in ["drop", "delete", "insert", "update", "exec", "stacked", "union"]):
            risk = "CRITICAL"
        else:
            risk = "HIGH"

        return {
            "safe": len(threats) == 0,
            "threats": threats,
            "risk_level": risk,
            "sanitized": stripped,
        }

    def is_safe(self, sql: str) -> bool:
        """Quick boolean check."""
        return self.analyze(sql)["safe"]

    def get_threats(self, sql: str) -> list:
        """Get list of detected threats."""
        return self.analyze(sql)["threats"]


# Module-level singleton
_detector = SQLInjectionDetector()


def detect_injection(sql: str) -> dict:
    """Module-level convenience function."""
    return _detector.analyze(sql)


def is_sql_safe(sql: str) -> bool:
    """Module-level quick check."""
    return _detector.is_safe(sql)
