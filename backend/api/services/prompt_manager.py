"""
Prompt Management System
========================
Centralized prompt library with versioning, categories, and variable substitution.
Replaces inline f-strings scattered across 10+ services.

Tables involved:
  prompt_templates  — Active prompt definitions
  prompt_versions   — Historical versions for rollback/comparison
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)
UTC = timezone.utc


# ── Default Prompt Library ───────────────────────────────────────────────────
# These are seeded on first use if the prompt_templates table is empty.

DEFAULT_PROMPTS = {
    # ── NLQ ──────────────────────────────────────────────────────────────
    "nlq:sql_generation": {
        "name": "sql_generation",
        "category": "nlq",
        "description": "Translate natural language to SQL query",
        "template": (
            "You are a SQL expert. Generate a read-only SQL query for the following question.\n\n"
            "Database schema:\n{schema_context}\n\n"
            "Question: {question}\n\n"
            "Rules:\n"
            "- Only generate SELECT queries. Never generate INSERT, UPDATE, DELETE, DROP, or ALTER.\n"
            "- Use standard SQL compatible with {dialect}.\n"
            "- Return ONLY the SQL query, no explanation.\n"
            "- Use table and column names from the schema above.\n"
            "- If the question is ambiguous, make reasonable assumptions and note them.\n"
        ),
        "variables": ["schema_context", "question", "dialect"],
    },
    "nlq:answer_generation": {
        "name": "answer_generation",
        "category": "nlq",
        "description": "Generate a natural language answer from query results",
        "template": (
            "Based on the following database query results, provide a clear and concise "
            "natural language answer to the user's question.\n\n"
            "Question: {question}\n"
            "Results: {results}\n"
            "Row count: {row_count}\n\n"
            "Provide a brief, helpful answer. Include specific numbers where relevant."
        ),
        "variables": ["question", "results", "row_count"],
    },

    # ── Narrative ─────────────────────────────────────────────────────────
    "narrative:daily_briefing": {
        "name": "daily_briefing",
        "category": "narrative",
        "description": "Generate executive daily briefing from KPI data",
        "template": (
            "You are a senior analyst at {company_name}. Generate a professional "
            "daily performance briefing for the {department} department.\n\n"
            "Period: {period}\n"
            "RAG Status: {rag_status}\n\n"
            "KPI Data:\n{kpi_table}\n\n"
            "Anomalies:\n{anomaly_text}\n\n"
            "{base_definitions}\n"
            "{focus}\n\n"
            "Generate a structured report with:\n"
            "1. Executive Summary (3-5 bullet points)\n"
            "2. Key Metrics Analysis\n"
            "3. Anomaly Commentary\n"
            "4. Risk Assessment\n"
            "5. Recommended Actions\n\n"
            "Tone: {tone}\n"
            "Language: {language}\n"
        ),
        "variables": [
            "company_name", "department", "period", "rag_status",
            "kpi_table", "anomaly_text", "base_definitions", "focus",
            "tone", "language"
        ],
    },
    "narrative:weekly_summary": {
        "name": "weekly_summary",
        "category": "narrative",
        "description": "Generate weekly department summary",
        "template": (
            "Generate a weekly summary for {company_name} - {department}.\n"
            "Period: {period}\n"
            "Key metrics: {kpi_summary}\n"
            "Tone: {tone}\n"
            "Language: {language}\n\n"
            "Include: trends, highlights, concerns, and next week outlook."
        ),
        "variables": ["company_name", "department", "period", "kpi_summary", "tone", "language"],
    },

    # ── Analyst ───────────────────────────────────────────────────────────
    "analyst:insight_generation": {
        "name": "insight_generation",
        "category": "analyst",
        "description": "Generate insights from statistical analysis results",
        "template": (
            "You are a data analyst. Analyze the following data and identify "
            "significant trends, correlations, and risks.\n\n"
            "Data Summary:\n{data_summary}\n\n"
            "Statistical Results:\n{stats}\n\n"
            "For each insight found, provide:\n"
            "- Type: trend_shift | correlation | concentration_risk | data_freshness\n"
            "- Severity: info | warning | critical\n"
            "- Title: Brief descriptive title\n"
            "- Description: Detailed explanation\n"
            "- Evidence: Supporting data points\n"
        ),
        "variables": ["data_summary", "stats"],
    },
    "analyst:xai_explanation": {
        "name": "xai_explanation",
        "category": "analyst",
        "description": "Explain a KPI or anomaly in plain language",
        "template": (
            "Explain the following metric or anomaly in plain business language.\n\n"
            "Metric: {metric_name}\n"
            "Value: {metric_value}\n"
            "Context: {context}\n"
            "Historical trend: {trend}\n\n"
            "Provide:\n"
            "1. What this means in plain language\n"
            "2. Why this might be happening\n"
            "3. What action should be considered\n"
            "4. Confidence level in this explanation\n"
        ),
        "variables": ["metric_name", "metric_value", "context", "trend"],
    },
    "analyst:governance_assessment": {
        "name": "governance_assessment",
        "category": "analyst",
        "description": "Assess data governance quality",
        "template": (
            "Assess the data governance quality for the following dataset.\n\n"
            "Completeness: {completeness}%\n"
            "Freshness: {freshness}%\n"
            "Validity: {validity}%\n"
            "Consistency: {consistency}%\n\n"
            "Provide a governance grade (A-F) and specific recommendations "
            "for improvement."
        ),
        "variables": ["completeness", "freshness", "validity", "consistency"],
    },

    # ── Report ────────────────────────────────────────────────────────────
    "report:custom_report": {
        "name": "custom_report",
        "category": "report",
        "description": "Generate custom report with user-defined focus",
        "template": (
            "Generate a {format} report for {company_name} - {department}.\n\n"
            "Scope: {scope}\n"
            "Period: {period}\n"
            "Data:\n{data}\n\n"
            "Custom instructions: {instructions}\n\n"
            "Tone: {tone}\n"
            "Language: {language}\n\n"
            "Generate a professional report with executive summary, "
            "detailed analysis, charts descriptions, and recommendations."
        ),
        "variables": [
            "format", "company_name", "department", "scope", "period",
            "data", "instructions", "tone", "language"
        ],
    },
    "report:executive_summary": {
        "name": "executive_summary",
        "category": "report",
        "description": "Generate executive-level summary",
        "template": (
            "Generate an executive summary for {company_name}.\n\n"
            "Period: {period}\n"
            "Key Findings:\n{findings}\n\n"
            "Audience: Board of Directors / Senior Leadership\n"
            "Tone: Formal, authoritative\n"
            "Language: {language}\n\n"
            "Include: strategic overview, key metrics, risks, opportunities, "
            "and recommended decisions."
        ),
        "variables": ["company_name", "period", "findings", "language"],
    },

    # ── Forecast ──────────────────────────────────────────────────────────
    "forecast:forecast_commentary": {
        "name": "forecast_commentary",
        "category": "forecast",
        "description": "Explain forecast results in business terms",
        "template": (
            "Explain the following forecast results for {metric_name}.\n\n"
            "Historical values: {historical}\n"
            "Forecasted values: {forecast}\n"
            "Confidence interval: {confidence_interval}\n"
            "Trend: {trend}\n\n"
            "Provide:\n"
            "1. Plain-language forecast summary\n"
            "2. Key drivers identified\n"
            "3. Risks to the forecast\n"
            "4. Recommended actions based on the forecast\n"
        ),
        "variables": [
            "metric_name", "historical", "forecast",
            "confidence_interval", "trend"
        ],
    },

    # ── Assistant ─────────────────────────────────────────────────────────
    "assistant:help_response": {
        "name": "help_response",
        "category": "assistant",
        "description": "In-app assistant responses",
        "template": (
            "You are a helpful assistant for the CNPS Smart Analytics Platform.\n"
            "Answer the user's question concisely and accurately.\n"
            "If you don't know the answer, say so honestly.\n\n"
            "User question: {question}\n"
            "Context: {context}\n"
        ),
        "variables": ["question", "context"],
    },

    # ── Recommendation ────────────────────────────────────────────────────
    "recommendation:prioritized_actions": {
        "name": "prioritized_actions",
        "category": "recommendation",
        "description": "Generate prioritized business recommendations",
        "template": (
            "Based on the following analysis results, generate prioritized "
            "business recommendations.\n\n"
            "Analysis Results:\n{analysis_results}\n\n"
            "For each recommendation, provide:\n"
            "- Priority: CRITICAL | HIGH | MEDIUM | LOW\n"
            "- Category: risk | opportunity | improvement | investigation\n"
            "- Title: Brief action title\n"
            "- Expected Impact: What this achieves\n"
            "- Risk: What happens if not addressed\n"
            "- Business Value: Why this matters\n"
            "- Suggested Actions: Specific steps to take\n"
        ),
        "variables": ["analysis_results"],
    },
}


class PromptManager:
    """
    Manages prompt templates with versioning and variable substitution.
    
    Usage:
        pm = PromptManager(db)
        
        # Get a prompt with variables filled in
        prompt = await pm.get_prompt(
            category="nlq",
            name="sql_generation",
            variables={"schema_context": "...", "question": "...", "dialect": "postgresql"}
        )
        
        # List all prompts in a category
        prompts = await pm.list_prompts(category="narrative")
        
        # Create a new prompt
        await pm.create_prompt(
            name="custom_analysis",
            category="analyst",
            template="Analyze {data} focusing on {focus}...",
            variables=["data", "focus"]
        )
        
        # Update a prompt (creates new version)
        await pm.update_prompt(prompt_id, template="Updated template...", changelog="v2")
    """

    def __init__(self, db):
        self.db = db
        self._cache = {}  # "category:name" → prompt_template_dict
        self._initialized = False

    async def _ensure_defaults(self) -> None:
        """Seed default prompts if table is empty."""
        if self._initialized:
            return

        try:
            result = self.db.table("prompt_templates").select("id").limit(1).execute()
            existing = result.data if hasattr(result, "data") else []
            if existing:
                self._initialized = True
                return

            # Table is empty — seed defaults
            for key, prompt in DEFAULT_PROMPTS.items():
                self.db.table("prompt_templates").insert({
                    "name": prompt["name"],
                    "category": prompt["category"],
                    "description": prompt["description"],
                    "template": prompt["template"],
                    "variables": prompt["variables"],
                    "version": 1,
                    "is_active": True,
                }).execute()

            logger.info(f"Seeded {len(DEFAULT_PROMPTS)} default prompts")
            self._initialized = True

        except Exception as e:
            logger.warning(f"Failed to seed default prompts: {e}")
            self._initialized = True  # Don't retry on every call

    async def get_prompt(
        self,
        category: str,
        name: str,
        variables: Optional[dict] = None,
    ) -> str:
        """
        Get a prompt template and fill in variables.
        Returns the fully-rendered prompt string.
        """
        await self._ensure_defaults()

        cache_key = f"{category}:{name}"

        if cache_key not in self._cache:
            try:
                result = (
                    self.db.table("prompt_templates")
                    .select("*")
                    .eq("category", category)
                    .eq("name", name)
                    .eq("is_active", True)
                    .limit(1)
                    .execute()
                )
                rows = result.data if hasattr(result, "data") else []
                if rows:
                    self._cache[cache_key] = rows[0]
                else:
                    # Fall back to defaults
                    if cache_key in DEFAULT_PROMPTS:
                        self._cache[cache_key] = {
                            **DEFAULT_PROMPTS[cache_key],
                            "id": None,
                            "version": 1,
                        }
                    else:
                        raise ValueError(f"Prompt not found: {category}/{name}")
            except ValueError:
                raise
            except Exception as e:
                # Fall back to defaults on DB error
                if cache_key in DEFAULT_PROMPTS:
                    self._cache[cache_key] = {
                        **DEFAULT_PROMPTS[cache_key],
                        "id": None,
                        "version": 1,
                    }
                else:
                    raise RuntimeError(f"Failed to load prompt {category}/{name}: {e}")

        template_str = self._cache[cache_key]["template"]

        if variables:
            try:
                return template_str.format(**variables)
            except KeyError as e:
                logger.warning(f"Missing prompt variable: {e}")
                return template_str

        return template_str

    async def get_prompt_meta(self, category: str, name: str) -> Optional[dict]:
        """Get prompt metadata without rendering."""
        await self._ensure_defaults()
        cache_key = f"{category}:{name}"
        if cache_key not in self._cache:
            await self.get_prompt(category, name)
        return self._cache.get(cache_key)

    async def list_prompts(self, category: Optional[str] = None) -> list:
        """List all prompt templates, optionally filtered by category."""
        await self._ensure_defaults()
        try:
            query = self.db.table("prompt_templates").select("*")
            if category:
                query = query.eq("category", category)
            result = query.order("category").order("name").execute()
            return result.data if hasattr(result, "data") else []
        except Exception as e:
            logger.warning(f"Failed to list prompts: {e}")
            return []

    async def create_prompt(
        self,
        *,
        name: str,
        category: str,
        template: str,
        variables: Optional[list] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> dict:
        """Create a new prompt template."""
        payload = {
            "name": name,
            "category": category,
            "template": template,
            "variables": variables or [],
            "description": description,
            "version": 1,
            "is_active": True,
            "created_by": created_by,
            "created_at": datetime.now(UTC).isoformat(),
        }
        result = self.db.table("prompt_templates").insert(payload).execute()
        rows = result.data if hasattr(result, "data") else []

        # Invalidate cache
        cache_key = f"{category}:{name}"
        self._cache.pop(cache_key, None)

        return rows[0] if rows else payload

    async def update_prompt(
        self,
        prompt_id: str,
        *,
        template: str,
        variables: Optional[list] = None,
        changelog: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> dict:
        """
        Update a prompt template (creates a version snapshot first).
        """
        # Get current version
        current_result = (
            self.db.table("prompt_templates")
            .select("*")
            .eq("id", prompt_id)
            .limit(1)
            .execute()
        )
        current_rows = current_result.data if hasattr(current_result, "data") else []
        if not current_rows:
            raise ValueError(f"Prompt not found: {prompt_id}")

        current = current_rows[0]
        new_version = current.get("version", 1) + 1

        # Save old version to prompt_versions
        self.db.table("prompt_versions").insert({
            "prompt_id": prompt_id,
            "version": current["version"],
            "template": current["template"],
            "variables": current.get("variables", []),
            "changelog": changelog,
            "created_by": created_by,
            "created_at": datetime.now(UTC).isoformat(),
        }).execute()

        # Update current
        update_payload = {
            "template": template,
            "version": new_version,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if variables is not None:
            update_payload["variables"] = variables

        self.db.table("prompt_templates").update(update_payload).eq("id", prompt_id).execute()

        # Invalidate cache
        cache_key = f"{current['category']}:{current['name']}"
        self._cache.pop(cache_key, None)

        return {**current, **update_payload}

    async def get_versions(self, prompt_id: str) -> list:
        """Get version history for a prompt."""
        try:
            result = (
                self.db.table("prompt_versions")
                .select("*")
                .eq("prompt_id", prompt_id)
                .order("version", desc=True)
                .execute()
            )
            return result.data if hasattr(result, "data") else []
        except Exception as e:
            logger.warning(f"Failed to get prompt versions: {e}")
            return []

    async def rollback(self, prompt_id: str, target_version: int) -> dict:
        """Rollback a prompt to a specific version."""
        versions = await self.get_versions(prompt_id)
        target = next((v for v in versions if v["version"] == target_version), None)
        if not target:
            raise ValueError(f"Version {target_version} not found for prompt {prompt_id}")

        return await self.update_prompt(
            prompt_id,
            template=target["template"],
            variables=target.get("variables"),
            changelog=f"Rollback to version {target_version}",
        )
