"""
Semantic Layer
==============
Translates between raw database schema and business concepts.
The AI never reasons directly on raw database schema — this layer
provides the translation.

Tables involved:
  semantic_templates  — Business field definition templates
  semantic_fields     — Field definitions within templates
  field_mappings      — User's local columns → global business fields
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SemanticLayer:
    """
    Per-user semantic translation layer.
    
    Usage:
        layer = SemanticLayer(db, user_id)
        await layer.load_mappings()
        
        # Translate raw → business
        biz_name = layer.to_business("claim_amt")  # → "Claim Amount"
        
        # Translate business → raw
        raw_name = layer.to_raw("Claim Amount")     # → "claim_amt"
        
        # Get AI-friendly schema context
        ctx = layer.get_schema_context()
        # → "- Claim Amount (currency): stored as 'claim_amt'\n..."
        
        # Translate SQL with business names back to raw names
        raw_sql = layer.translate_query(sql_with_business_names)
    """

    def __init__(self, db, user_id: str):
        self.db = db
        self.user_id = user_id
        self._raw_to_business = {}   # raw_column → business_name
        self._business_to_raw = {}   # business_name → raw_column
        self._field_meta = {}        # business_name → {data_type, required, description}
        self._loaded = False

    async def load_mappings(self) -> None:
        """Load all field mappings for the user's department."""
        if self._loaded:
            return

        try:
            # 1. Get user's department
            user_roles_resp = self.db.table("user_roles") \
                .select("department_id") \
                .eq("user_id", self.user_id) \
                .execute()
            user_roles = user_roles_resp.data if hasattr(user_roles_resp, "data") else []

            department_id = None
            for row in user_roles:
                if row.get("department_id"):
                    department_id = row["department_id"]
                    break

            if not department_id:
                # Try "General" department
                gen_resp = self.db.table("departments") \
                    .select("id") \
                    .eq("name", "General") \
                    .limit(1) \
                    .execute()
                gen_rows = gen_resp.data if hasattr(gen_resp, "data") else []
                if gen_rows:
                    department_id = gen_rows[0]["id"]

            if not department_id:
                logger.debug(f"No department for user {self.user_id}")
                self._loaded = True
                return

            # 2. Get department's template_id
            dept_resp = self.db.table("departments") \
                .select("template_id") \
                .eq("id", department_id) \
                .limit(1) \
                .execute()
            dept_rows = dept_resp.data if hasattr(dept_resp, "data") else []
            if not dept_rows or not dept_rows[0].get("template_id"):
                self._loaded = True
                return

            template_id = dept_rows[0]["template_id"]

            # 3. Get semantic fields for this template
            fields_resp = self.db.table("semantic_fields") \
                .select("*") \
                .eq("template_id", template_id) \
                .execute()
            fields = fields_resp.data if hasattr(fields_resp, "data") else []

            # 4. Get user's field mappings
            mappings_resp = self.db.table("field_mappings") \
                .select("*, semantic_fields(global_field_name, data_type, required, description)") \
                .eq("user_id", self.user_id) \
                .execute()
            mappings = mappings_resp.data if hasattr(mappings_resp, "data") else []

            # 5. Build translation dictionaries
            for mapping in mappings:
                local_col = mapping.get("local_column_name", "")
                field_info = mapping.get("semantic_fields", {})
                if not field_info or not local_col:
                    continue

                biz_name = field_info.get("global_field_name", "")
                if not biz_name:
                    continue

                self._raw_to_business[local_col] = biz_name
                self._business_to_raw[biz_name] = local_col
                self._field_meta[biz_name] = {
                    "data_type": field_info.get("data_type", "string"),
                    "required": field_info.get("required", False),
                    "description": field_info.get("description", ""),
                    "local_column": local_col,
                }

            logger.debug(
                f"Loaded {len(self._raw_to_business)} mappings for user {self.user_id}"
            )

        except Exception as e:
            logger.warning(f"Failed to load semantic mappings: {e}")

        self._loaded = True

    def to_business(self, raw_name: str) -> str:
        """Convert a raw database column name to a business-friendly name."""
        return self._raw_to_business.get(raw_name, raw_name)

    def to_raw(self, business_name: str) -> str:
        """Convert a business-friendly name to the raw database column name."""
        return self._business_to_raw.get(business_name, business_name)

    def get_schema_context(self) -> str:
        """
        Generate an AI-friendly description of the schema using business terms.
        Used in prompts so the AI reasons in business language.
        """
        if not self._field_meta:
            return "(no semantic mappings configured)"

        lines = []
        for biz_name, meta in sorted(self._field_meta.items()):
            dtype = meta["data_type"]
            desc = meta.get("description", "")
            local = meta["local_column"]
            line = f"- {biz_name} ({dtype}): stored as '{local}'"
            if desc:
                line += f" — {desc}"
            lines.append(line)
        return "\n".join(lines)

    def get_field_list(self) -> list:
        """Return list of all mapped fields with metadata."""
        return [
            {"business_name": name, **meta}
            for name, meta in self._field_meta.items()
        ]

    def translate_query(self, sql: str) -> str:
        """
        Translate business names in generated SQL back to raw column names.
        The LLM generates SQL using business names; this converts them
        to actual database column names before execution.
        """
        # Sort by length descending to avoid partial replacements
        sorted_names = sorted(
            self._business_to_raw.keys(),
            key=len,
            reverse=True
        )
        for biz_name in sorted_names:
            raw_name = self._business_to_raw[biz_name]
            # Case-insensitive replacement
            import re
            pattern = re.compile(re.escape(biz_name), re.IGNORECASE)
            sql = pattern.sub(raw_name, sql)
        return sql

    def reverse_translate_results(self, rows: list, columns: list) -> tuple:
        """
        Translate raw column names in query results back to business names.
        Returns (translated_columns, translated_rows).
        """
        translated_cols = [self.to_business(col) for col in columns]
        translated_rows = []
        for row in rows:
            new_row = {}
            for raw_col, val in row.items():
                biz_col = self.to_business(raw_col)
                new_row[biz_col] = val
            translated_rows.append(new_row)
        return translated_cols, translated_rows

    def has_mappings(self) -> bool:
        """Check if any mappings are loaded."""
        return len(self._raw_to_business) > 0
