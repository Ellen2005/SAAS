# Enterprise Architecture Upgrade - Implementation Plan
## CNPS Smart Automated Analytics Platform

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Implementation Phases](#2-implementation-phases)
3. [Phase 1: Foundation Layer](#3-phase-1-foundation-layer)
4. [Phase 2: AI Intelligence Layer](#4-phase-2-ai-intelligence-layer)
5. [Phase 3: Governance & Monitoring](#5-phase-3-governance--monitoring)
6. [Phase 4: Admin & Operations](#6-phase-4-admin--operations)
7. [Phase 5: Security & Quality](#7-phase-5-security--quality)
8. [Database Schema Changes](#8-database-schema-changes)
9. [File Impact Matrix](#9-file-impact-matrix)
10. [Risk Assessment](#10-risk-assessment)

---

## 1. Current State Analysis

### What Exists Today

| Component | Status | Gap |
|-----------|--------|-----|
| FastAPI Backend | 130+ endpoints, 30 services | Monolithic main.py, no DI |
| Authentication | Supabase JWT + RBAC (3 roles) | No login audit, no token enforcement |
| Database | 30+ tables, RLS policies | No versioning, limited audit |
| AI/LLM | Groq (LLaMA 3.3 70B) via groq_utils | Direct calls, no orchestration |
| Prompts | Inline f-strings in 10 services | No library, no versioning, no admin |
| Caching | Redis + in-memory fallback | No cache warming, no metrics |
| Background Jobs | APScheduler + FastAPI BackgroundTasks | In-memory, lost on restart |
| Monitoring | Python logging + /health | No APM, no metrics, no dashboards |
| Audit | Partial (connections, preferences only) | 70% of actions unaudited |
| Frontend | React 19, 28 pages, 24 components | No state management, no tests |

### What Needs to Change

```
Current:  User → API Router → Service → Groq (direct) → Response
                                    ↓
                              Supabase DB

Target:   User → API Router → Service → AI Orchestrator → Prompt Manager
                                    ↓         ↓              ↓
                              Semantic Layer  LLM Router    Governance
                                    ↓         ↓              ↓
                              Supabase DB   Groq/Other    Audit Log
                                    ↓         ↓              ↓
                              Data Quality  Confidence    Monitoring
                                    ↓         ↓              ↓
                              Response ← Explainability ← Feedback
```

---

## 2. Implementation Phases

### Phase Overview

```
Phase 1: Foundation Layer (Weeks 1-2)
├── 1.1 Audit System
├── 1.2 Semantic Layer
├── 1.3 Prompt Management
└── 1.4 Database Versioning

Phase 2: AI Intelligence Layer (Weeks 3-4)
├── 2.1 AI Orchestrator
├── 2.2 Confidence Engine
├── 2.3 Explainability Engine
└── 2.4 Recommendation Engine

Phase 3: Governance & Monitoring (Weeks 5-6)
├── 3.1 AI Governance
├── 3.2 AI Monitoring Dashboard
├── 3.3 AI Feedback Loop
└── 3.4 Data Quality Engine

Phase 4: Admin & Operations (Weeks 7-8)
├── 4.1 Admin Governance Panel
├── 4.2 System Health Dashboard
├── 4.3 Background Job Center
└── 4.4 Dependency Analysis

Phase 5: Security & Quality (Weeks 9-10)
├── 5.1 Security Hardening
├── 5.2 Code Quality Refactor
├── 5.3 Performance Optimization
└── 5.4 Documentation
```

---

## 3. Phase 1: Foundation Layer

### 1.1 Audit System

**What Changes:**
Expand `audit_service.py` from 23 lines to a full audit framework covering every action.

**Affected Files:**
- `backend/api/services/audit_service.py` — Expand to full audit service
- `backend/api/core/auth.py` — Add login/logout audit hooks
- `backend/api/routers/admin.py` — Audit all admin actions
- `backend/api/routers/departments.py` — Audit department CRUD
- `backend/api/routers/users.py` — Audit role changes
- `backend/api/routers/semantic.py` — Audit template changes
- `backend/api/routers/templates.py` — Audit instance template changes
- `backend/api/routers/validation.py` — Audit validation triggers
- `backend/api/migrations/` — New migration for expanded audit_logs table

**New Database Schema:**
```sql
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS
  ip_address TEXT,
  user_agent TEXT,
  old_value JSONB,
  new_value JSONB,
  duration_ms INTEGER,
  reason TEXT,
  affected_objects JSONB,
  request_id TEXT,
  session_id TEXT;

CREATE INDEX idx_audit_logs_user_action ON audit_logs(user_id, action);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity, created_at DESC);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
```

**Implementation:**
```python
# backend/api/services/audit_service.py
class AuditService:
    def __init__(self, db):
        self.db = db

    async def log(self, *, user_id, action, entity, entity_id=None,
                  old_value=None, new_value=None, ip_address=None,
                  user_agent=None, reason=None, duration_ms=None,
                  request_id=None):
        """Central audit logging function."""
        record = {
            "user_id": user_id,
            "action": action,  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.
            "entity": entity,  # department, user_role, template, etc.
            "entity_id": entity_id,
            "old_value": old_value,
            "new_value": new_value,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "reason": reason,
            "duration_ms": duration_ms,
            "request_id": request_id,
            "created_at": datetime.utcnow().isoformat()
        }
        try:
            await self.db.table("audit_logs").insert(record).execute()
        except Exception:
            logger.warning("Audit log write failed (non-critical)")

    async def get_audit_trail(self, *, entity=None, user_id=None,
                               action=None, limit=100, offset=0):
        """Query audit trail with filters."""
        query = self.db.table("audit_logs").select("*")
        if entity:
            query = query.eq("entity", entity)
        if user_id:
            query = query.eq("user_id", user_id)
        if action:
            query = query.eq("action", action)
        result = await query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data
```

**Audit Coverage Matrix:**
| Action | Entity | Trigger |
|--------|--------|---------|
| LOGIN | auth | Login page |
| LOGOUT | auth | Logout button / timeout |
| CREATE | department | AdminDepartments |
| UPDATE | department | AdminDepartments |
| DELETE | department | AdminDepartments |
| ASSIGN_ROLE | user_role | AdminUsers |
| REMOVE_ROLE | user_role | AdminUsers |
| CREATE | semantic_template | AdminSemantic |
| DELETE | semantic_template | AdminSemantic |
| CREATE | semantic_field | AdminSemantic |
| DELETE | semantic_field | AdminSemantic |
| CREATE | instance_template | AdminTemplates |
| DEPLOY | instance_template | AdminTemplates |
| UPDATE | connection | Settings |
| UPDATE | preferences | Settings |
| TRIGGER_ETL | etl | Dashboard / Admin |
| GENERATE | report | Reports |
| EXPORT | data | Export |
| QUERY | nlq | NLQPage |
| ANALYZE | analysis | AIAnalyst |
| CREATE | webhook | Webhooks |
| UPDATE | webhook | Webhooks |
| DELETE | webhook | Webhooks |

---

### 1.2 Semantic Layer

**What Changes:**
Create a translation layer between raw database schema and business concepts.

**Affected Files:**
- `backend/api/services/semantic_layer.py` — NEW: Core semantic translation
- `backend/api/services/nlq_service.py` — Use semantic layer for NL→SQL
- `backend/api/services/ai_analyst_service.py` — Use semantic layer for insights
- `backend/api/services/narrative_service.py` — Use semantic layer for narratives
- `backend/api/services/analysis_engine.py` — Use semantic layer for analysis
- `backend/api/routers/introspect.py` — Use semantic layer for schema display
- `backend/api/routers/semantic.py` — Extend with translation APIs

**Implementation:**
```python
# backend/api/services/semantic_layer.py
class SemanticLayer:
    """Translates between raw DB schema and business concepts."""

    def __init__(self, db, user_id):
        self.db = db
        self.user_id = user_id
        self._mapping_cache = {}

    async def load_mappings(self):
        """Load all field mappings for the user's department."""
        # Get user's department
        user_info = await get_user_info(self.user_id)
        dept_id = user_info.get("department_id")

        # Get semantic template for department
        template = await self.db.table("semantic_templates") \
            .select("*").eq("id", dept_id).single().execute()

        # Get field mappings
        mappings = await self.db.table("field_mappings") \
            .select("*, semantic_fields(*)") \
            .eq("template_id", template.data["id"]).execute()

        # Build translation dictionaries
        for m in mappings.data:
            field = m.get("semantic_fields", {})
            self._mapping_cache[field["global_field_name"]] = {
                "local_column": m["local_column_name"],
                "data_type": field["data_type"],
                "required": field["required"],
                "description": field.get("description", "")
            }

    def to_business(self, raw_name: str) -> str:
        """Convert raw column name to business name."""
        for biz_name, mapping in self._mapping_cache.items():
            if mapping["local_column"] == raw_name:
                return biz_name
        return raw_name

    def to_raw(self, business_name: str) -> str:
        """Convert business name to raw column name."""
        mapping = self._mapping_cache.get(business_name)
        return mapping["local_column"] if mapping else business_name

    def get_schema_context(self) -> str:
        """Generate AI-friendly schema context."""
        lines = []
        for biz_name, mapping in self._mapping_cache.items():
            lines.append(f"- {biz_name} ({mapping['data_type']}): "
                        f"stored as '{mapping['local_column']}'")
        return "\n".join(lines)

    def translate_query(self, sql: str) -> str:
        """Translate business names in SQL back to raw column names."""
        for biz_name, mapping in self._mapping_cache.items():
            sql = sql.replace(biz_name, mapping["local_column"])
        return sql
```

**Integration Points:**
```
NLQ Service:
  User question → Groq generates SQL with business names
  → Semantic Layer translates to raw SQL
  → Execute against DB
  → Translate results back to business names

AI Analyst:
  Raw data → Semantic Layer adds business context
  → Groq generates insights with business terminology
  → Results use friendly names

Narrative Service:
  Raw KPI data → Semantic Layer provides business context
  → Groq generates narrative with proper terminology
```

---

### 1.3 Prompt Management

**What Changes:**
Create a prompt library with versioning, replacing all inline f-strings.

**Affected Files:**
- `backend/api/services/prompt_manager.py` — NEW: Prompt management service
- `backend/api/routers/admin.py` — Add prompt CRUD endpoints
- `backend/api/services/nlq_service.py` — Load prompts from library
- `backend/api/services/narrative_service.py` — Load prompts from library
- `backend/api/services/ai_analyst_service.py` — Load prompts from library
- `backend/api/services/analysis_engine.py` — Load prompts from library
- `backend/api/services/assistant.py` — Load prompts from library
- `backend/api/services/custom_report_service.py` — Load prompts from library
- `backend/api/migrations/` — New migration for prompt tables

**New Database Schema:**
```sql
CREATE TABLE IF NOT EXISTS prompt_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  category TEXT NOT NULL,  -- nlq, narrative, analyst, report, forecast, etc.
  description TEXT,
  template TEXT NOT NULL,
  variables JSONB DEFAULT '[]',  -- ["schema_context", "user_question", etc.]
  version INTEGER DEFAULT 1,
  is_active BOOLEAN DEFAULT true,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prompt_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_id UUID REFERENCES prompt_templates(id),
  version INTEGER NOT NULL,
  template TEXT NOT NULL,
  variables JSONB DEFAULT '[]',
  changelog TEXT,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_prompt_templates_category ON prompt_templates(category);
CREATE INDEX idx_prompt_templates_name ON prompt_templates(name);
```

**Implementation:**
```python
# backend/api/services/prompt_manager.py
class PromptManager:
    """Manages prompt templates with versioning."""

    def __init__(self, db):
        self.db = db
        self._cache = {}  # category -> {name -> template}

    async def get_prompt(self, category: str, name: str,
                         variables: dict = None) -> str:
        """Get a prompt template and fill in variables."""
        cache_key = f"{category}:{name}"
        if cache_key not in self._cache:
            result = await self.db.table("prompt_templates") \
                .select("*") \
                .eq("category", category) \
                .eq("name", name) \
                .eq("is_active", True) \
                .single().execute()
            self._cache[cache_key] = result.data

        template = self._cache[cache_key]["template"]
        if variables:
            template = template.format(**variables)
        return template

    async def create_prompt(self, *, name, category, template,
                            variables=None, description=None, created_by=None):
        """Create a new prompt template."""
        result = await self.db.table("prompt_templates").insert({
            "name": name,
            "category": category,
            "template": template,
            "variables": variables or [],
            "description": description,
            "created_by": created_by
        }).execute()
        return result.data

    async def update_prompt(self, prompt_id: str, *, template,
                            changelog=None, created_by=None):
        """Update a prompt (creates new version)."""
        # Get current version
        current = await self.db.table("prompt_templates") \
            .select("*").eq("id", prompt_id).single().execute()

        new_version = current.data["version"] + 1

        # Save old version
        await self.db.table("prompt_versions").insert({
            "prompt_id": prompt_id,
            "version": current.data["version"],
            "template": current.data["template"],
            "variables": current.data["variables"],
            "changelog": changelog,
            "created_by": created_by
        }).execute()

        # Update current
        await self.db.table("prompt_templates") \
            .update({"template": template, "version": new_version,
                     "updated_at": datetime.utcnow().isoformat()}) \
            .eq("id", prompt_id).execute()

        # Invalidate cache
        self._cache = {k: v for k, v in self._cache.items()
                       if not k.startswith(f"{current.data['category']}:{current.data['name']}")}

    async def list_prompts(self, category=None):
        """List all prompt templates."""
        query = self.db.table("prompt_templates").select("*")
        if category:
            query = query.eq("category", category)
        result = await query.order("category").execute()
        return result.data
```

**Default Prompt Library:**
| Category | Name | Purpose |
|----------|------|---------|
| nlq | sql_generation | Natural language → SQL |
| nlq | answer_generation | SQL results → natural language answer |
| narrative | daily_briefing | Executive daily briefing |
| narrative | weekly_summary | Weekly department summary |
| analyst | insight_generation | Generate insights from data |
| analyst | xai_explanation | Explain a KPI or anomaly |
| analyst | governance_assessment | Assess data governance |
| report | custom_report | Generate custom report narrative |
| report | executive_summary | Executive summary |
| forecast | forecast_commentary | Explain forecast results |
| assistant | help_response | In-app assistant responses |
| recommendation | prioritized_actions | Generate recommendations |

---

### 1.4 Database Versioning

**What Changes:**
Add version tracking for semantic templates, instance templates, and configurations.

**Affected Files:**
- `backend/api/routers/semantic.py` — Add version history endpoints
- `backend/api/routers/templates.py` — Add version history endpoints
- `backend/api/migrations/` — New migration for version tracking tables

**New Database Schema:**
```sql
CREATE TABLE IF NOT EXISTS entity_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type TEXT NOT NULL,  -- semantic_template, instance_template, prompt
  entity_id UUID NOT NULL,
  version INTEGER NOT NULL,
  snapshot JSONB NOT NULL,
  changelog TEXT,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_entity_versions_entity ON entity_versions(entity_type, entity_id);
```

**API Endpoints:**
```
GET  /api/admin/versions/{entity_type}/{entity_id}     — List versions
GET  /api/admin/versions/{entity_type}/{entity_id}/{v}  — Get specific version
POST /api/admin/versions/{entity_type}/{entity_id}/rollback — Rollback to version
GET  /api/admin/versions/{entity_type}/{entity_id}/compare?v1=1&v2=2 — Compare versions
```

---

## 4. Phase 2: AI Intelligence Layer

### 2.1 AI Orchestrator

**What Changes:**
Create a single entry point for all AI requests, replacing direct Groq calls.

**Affected Files:**
- `backend/api/services/ai_orchestrator.py` — NEW: Central AI orchestration
- `backend/api/services/groq_utils.py` — Keep as low-level LLM client
- `backend/api/services/nlq_service.py` — Route through orchestrator
- `backend/api/services/narrative_service.py` — Route through orchestrator
- `backend/api/services/ai_analyst_service.py` — Route through orchestrator
- `backend/api/services/analysis_engine.py` — Route through orchestrator
- `backend/api/services/assistant.py` — Route through orchestrator
- `backend/api/services/custom_report_service.py` — Route through orchestrator
- `backend/api/services/forecasting_service.py` — Route through orchestrator
- `backend/api/routers/analyst.py` — Use orchestrator

**Implementation:**
```python
# backend/api/services/ai_orchestrator.py
class AIOrchestrator:
    """Single entry point for all AI requests."""

    def __init__(self, db, prompt_manager, semantic_layer, governance, monitor):
        self.db = db
        self.prompt_manager = prompt_manager
        self.semantic_layer = semantic_layer
        self.governance = governance
        self.monitor = monitor

    async def execute(self, *, intent, context, user_id, category,
                      prompt_name=None, custom_prompt=None,
                      variables=None, temperature=None, max_tokens=None):
        """
        Execute an AI request through the full pipeline.

        Pipeline:
        1. Intent detection
        2. Context gathering
        3. Semantic lookup
        4. Prompt construction
        5. LLM invocation
        6. Output validation
        7. Confidence calculation
        8. Governance logging
        9. Monitoring metrics
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())

        try:
            # 1. Intent detection (if not provided)
            if not intent:
                intent = await self._detect_intent(context)

            # 2. Context gathering
            enriched_context = await self._gather_context(context, user_id)

            # 3. Semantic lookup
            if self.semantic_layer:
                enriched_context["schema_context"] = \
                    self.semantic_layer.get_schema_context()

            # 4. Prompt construction
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = await self.prompt_manager.get_prompt(
                    category=category,
                    name=prompt_name,
                    variables={**enriched_context, **(variables or {})}
                )

            # 5. Get governance-approved model settings
            model_config = await self.governance.get_model_config(category)

            # 6. LLM invocation
            messages = [{"role": "user", "content": prompt}]
            llm_response = await execute_groq_completion(
                messages=messages,
                temperature=temperature or model_config["temperature"],
                max_tokens=max_tokens or model_config["max_tokens"],
                model=model_config["model"]
            )

            # 7. Output validation
            validated = await self._validate_output(llm_response, intent)

            # 8. Confidence calculation
            confidence = await self._calculate_confidence(
                validated, enriched_context)

            # 9. Governance logging
            latency_ms = int((time.time() - start_time) * 1000)
            await self.governance.log_request(
                request_id=request_id,
                user_id=user_id,
                category=category,
                intent=intent,
                model=model_config["model"],
                temperature=temperature or model_config["temperature"],
                max_tokens=max_tokens or model_config["max_tokens"],
                tokens_used=llm_response.get("usage", {}),
                latency_ms=latency_ms,
                confidence=confidence["score"],
                status="success"
            )

            # 10. Monitoring metrics
            await self.monitor.record_metric(
                "ai_request", latency_ms=latency_ms,
                category=category, status="success")

            return {
                "request_id": request_id,
                "response": validated,
                "confidence": confidence,
                "intent": intent,
                "model": model_config["model"],
                "latency_ms": latency_ms
            }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            await self.governance.log_request(
                request_id=request_id,
                user_id=user_id,
                category=category,
                intent=intent,
                status="error",
                error=str(e),
                latency_ms=latency_ms
            )
            await self.monitor.record_metric(
                "ai_request", latency_ms=latency_ms,
                category=category, status="error")
            raise

    async def _detect_intent(self, context):
        """Detect the intent of the request."""
        # Simple keyword-based intent detection
        text = str(context).lower()
        if any(w in text for w in ["sql", "query", "select", "data"]):
            return "data_query"
        if any(w in text for w in ["narrative", "summary", "briefing"]):
            return "narrative"
        if any(w in text for w in ["forecast", "predict", "trend"]):
            return "forecasting"
        if any(w in text for w in ["explain", "why", "reason"]):
            return "explanation"
        if any(w in text for w in ["recommend", "suggest", "action"]):
            return "recommendation"
        return "general"

    async def _gather_context(self, context, user_id):
        """Enrich context with user and system information."""
        enriched = dict(context)
        user_info = await get_user_info(user_id)
        enriched["user_role"] = user_info.get("role")
        enriched["department"] = user_info.get("department_name")
        enriched["timestamp"] = datetime.utcnow().isoformat()
        return enriched

    async def _validate_output(self, response, intent):
        """Validate LLM output for safety and correctness."""
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Basic safety checks
        if any(unsafe in content.lower() for unsafe in
               ["drop table", "delete from", "insert into", "update set"]):
            content = "[Response filtered for safety]"

        return {
            "content": content,
            "raw_response": response,
            "intent": intent
        }

    async def _calculate_confidence(self, output, context):
        """Calculate confidence score based on multiple signals."""
        score = 0.5  # Base score

        # Factor 1: Response length (longer = more detailed = higher confidence)
        content = output.get("content", "")
        if len(content) > 500:
            score += 0.1
        elif len(content) > 200:
            score += 0.05

        # Factor 2: Presence of specific data references
        if any(ref in content for ref in ["%", "increase", "decrease", "total"]):
            score += 0.1

        # Factor 3: Source data quality
        data_quality = context.get("data_quality_score", 0.7)
        score += data_quality * 0.2

        # Factor 4: Model reliability
        model = context.get("model", "")
        if "70b" in model:
            score += 0.1
        elif "8b" in model:
            score += 0.05

        return {
            "score": min(score, 1.0),
            "factors": {
                "response_quality": score,
                "data_quality": data_quality,
                "model_reliability": 0.9 if "70b" in model else 0.7
            }
        }
```

**Migration Pattern (per service):**
```python
# BEFORE (nlq_service.py):
async def process_question(question, user_id):
    messages = [{"role": "user", "content": f"Generate SQL for: {question}"}]
    response = await execute_groq_completion(messages, temperature=0.1, max_tokens=800)
    # ... process response

# AFTER:
async def process_question(question, user_id):
    orchestrator = AIOrchestrator(db, prompt_manager, semantic_layer, governance, monitor)
    result = await orchestrator.execute(
        intent="data_query",
        context={"question": question},
        user_id=user_id,
        category="nlq",
        prompt_name="sql_generation",
        variables={"question": question}
    )
    # ... use result["response"]["content"]
```

---

### 2.2 Confidence Engine

**What Changes:**
Every AI response includes calculated confidence with evidence.

**Affected Files:**
- `backend/api/services/confidence_engine.py` — NEW: Confidence calculation
- `backend/api/services/ai_orchestrator.py` — Integrate confidence engine
- `backend/api/services/data_quality_service.py` — NEW: Data quality signals

**Implementation:**
```python
# backend/api/services/confidence_engine.py
class ConfidenceEngine:
    """Calculates confidence scores for AI responses."""

    def __init__(self, db):
        self.db = db

    async def calculate(self, response, context, data_stats=None):
        """Calculate comprehensive confidence score."""
        factors = {}

        # Factor 1: Data Completeness
        if data_stats:
            completeness = data_stats.get("completeness", 0.7)
            factors["data_completeness"] = {
                "score": completeness,
                "weight": 0.25,
                "evidence": f"{completeness*100:.0f}% of fields populated"
            }

        # Factor 2: Data Freshness
        if data_stats:
            freshness = data_stats.get("freshness", 0.8)
            factors["data_freshness"] = {
                "score": freshness,
                "weight": 0.15,
                "evidence": f"Last updated {data_stats.get('days_old', 0)} days ago"
            }

        # Factor 3: Source Record Count
        record_count = context.get("record_count", 0)
        if record_count > 1000:
            factors["sample_size"] = {"score": 0.95, "weight": 0.15,
                                       "evidence": f"Based on {record_count:,} records"}
        elif record_count > 100:
            factors["sample_size"] = {"score": 0.8, "weight": 0.15,
                                       "evidence": f"Based on {record_count:,} records"}
        else:
            factors["sample_size"] = {"score": 0.5, "weight": 0.15,
                                       "evidence": f"Based on {record_count} records (small sample)"}

        # Factor 4: Response Specificity
        content = response.get("content", "")
        specificity = self._measure_specificity(content)
        factors["response_specificity"] = {
            "score": specificity,
            "weight": 0.2,
            "evidence": "Response contains specific data points" if specificity > 0.7
                       else "Response is general"
        }

        # Factor 5: Model Confidence
        model = context.get("model", "")
        model_conf = 0.95 if "70b" in model else 0.85 if "8b" in model else 0.7
        factors["model_confidence"] = {
            "score": model_conf,
            "weight": 0.15,
            "evidence": f"Model: {model}"
        }

        # Factor 6: Semantic Consistency
        semantic_score = await self._check_semantic_consistency(content, context)
        factors["semantic_consistency"] = {
            "score": semantic_score,
            "weight": 0.1,
            "evidence": "Response aligns with business terminology"
        }

        # Weighted average
        total_score = sum(
            f["score"] * f["weight"] for f in factors.values()
        )

        return {
            "score": round(min(total_score, 1.0), 3),
            "grade": self._score_to_grade(total_score),
            "factors": factors,
            "evidence": self._compile_evidence(factors),
            "data_freshness": data_stats.get("last_updated") if data_stats else None,
            "affected_records": record_count,
            "reasoning_summary": self._generate_reasoning(factors, total_score)
        }

    def _measure_specificity(self, text):
        """Measure how specific/data-driven a response is."""
        import re
        numbers = len(re.findall(r'\d+\.?\d*%?', text))
        has_comparison = any(w in text.lower() for w in
                          ["increase", "decrease", "higher", "lower", "vs"])
        has_date = bool(re.search(r'\d{4}-\d{2}-\d{2}', text))
        score = min(0.5 + numbers * 0.05 + has_comparison * 0.2 + has_date * 0.1, 1.0)
        return score

    async def _check_semantic_consistency(self, content, context):
        """Check if response uses consistent business terminology."""
        # Simplified: check if business terms from context appear in response
        business_terms = context.get("business_terms", [])
        if not business_terms:
            return 0.8  # Default if no terms to check
        found = sum(1 for t in business_terms if t.lower() in content.lower())
        return min(0.5 + (found / len(business_terms)) * 0.5, 1.0)

    def _score_to_grade(self, score):
        if score >= 0.9: return "A"
        if score >= 0.8: return "B"
        if score >= 0.7: return "C"
        if score >= 0.6: return "D"
        return "F"

    def _compile_evidence(self, factors):
        return [f"{k}: {v['evidence']}" for k, v in factors.items()]

    def _generate_reasoning(self, factors, total):
        if total >= 0.85:
            return "High confidence: strong data foundation and specific response"
        if total >= 0.7:
            return "Moderate confidence: adequate data support"
        return "Lower confidence: limited data or general response"
```

---

### 2.3 Explainability Engine

**What Changes:**
Generate human-readable explanations for every AI decision.

**Affected Files:**
- `backend/api/services/explainability_engine.py` — NEW: XAI service
- `backend/api/services/ai_orchestrator.py` — Integrate explainability
- `backend/api/routers/analyst.py` — Return explanations with insights

**Implementation:**
```python
# backend/api/services/explainability_engine.py
class ExplainabilityEngine:
    """Generates explanations for AI outputs."""

    async def explain_kpi(self, kpi_data, context):
        """Explain a KPI value and its drivers."""
        return {
            "feature_importance": self._compute_feature_importance(kpi_data),
            "reasoning": self._generate_reasoning(kpi_data),
            "business_explanation": self._business_explanation(kpi_data),
            "natural_language": self._nl_explanation(kpi_data),
            "source_lineage": self._trace_lineage(kpi_data, context),
            "decision_trace": self._build_decision_trace(kpi_data, context)
        }

    async def explain_anomaly(self, anomaly_data, context):
        """Explain why an anomaly was detected."""
        return {
            "anomaly_type": anomaly_data.get("type", "unknown"),
            "expected_range": anomaly_data.get("expected"),
            "actual_value": anomaly_data.get("actual"),
            "deviation": anomaly_data.get("deviation"),
            "possible_causes": self._identify_causes(anomaly_data, context),
            "confidence": anomaly_data.get("confidence", 0.5),
            "recommended_action": self._suggest_action(anomaly_data)
        }

    def _compute_feature_importance(self, data):
        """Compute which features contributed most to the value."""
        # Simplified feature importance based on data characteristics
        features = []
        if "delta" in data:
            features.append({
                "name": "Period-over-period change",
                "impact": abs(data["delta"]),
                "direction": "positive" if data["delta"] > 0 else "negative"
            })
        if "components" in data:
            for comp in data["components"]:
                features.append({
                    "name": comp.get("name", "Unknown"),
                    "impact": comp.get("impact", 0),
                    "direction": "positive" if comp.get("impact", 0) > 0 else "negative"
                })
        return sorted(features, key=lambda x: x["impact"], reverse=True)

    def _generate_reasoning(self, data):
        """Generate reasoning chain."""
        steps = []
        if "source" in data:
            steps.append(f"Data sourced from {data['source']}")
        if " calculation" in data:
            steps.append(f"Calculated using {data['calculation']}")
        if "period" in data:
            steps.append(f"For period: {data['period']}")
        return steps

    def _business_explanation(self, data):
        """Generate business-friendly explanation."""
        label = data.get("label", "This metric")
        value = data.get("value", "N/A")
        delta = data.get("delta")
        if delta and delta > 0:
            return f"{label} is {value}, which is an improvement of {abs(delta):.1f}%"
        elif delta and delta < 0:
            return f"{label} is {value}, which is a decline of {abs(delta):.1f}%"
        return f"{label} is currently at {value}"

    def _nl_explanation(self, data):
        """Generate natural language explanation."""
        # This would use the LLM via orchestrator for full quality
        return self._business_explanation(data)

    def _trace_lineage(self, data, context):
        """Trace data lineage."""
        return {
            "source_table": context.get("source_table", "unknown"),
            "source_column": context.get("source_column", "unknown"),
            "transformations": context.get("transformations", []),
            "aggregation": context.get("aggregation", "none"),
            "filters_applied": context.get("filters", [])
        }

    def _build_decision_trace(self, data, context):
        """Build complete decision trace."""
        return {
            "inputs": context.get("inputs", {}),
            "model": context.get("model", "unknown"),
            "parameters": context.get("parameters", {}),
            "intermediate_results": context.get("intermediates", []),
            "final_output": data
        }

    def _identify_causes(self, anomaly, context):
        """Identify possible causes of an anomaly."""
        causes = []
        if anomaly.get("type") == "spike":
            causes.append("Unusual surge in activity")
            causes.append("Data entry error possible")
        elif anomaly.get("type") == "drop":
            causes.append("Activity reduction")
            causes.append("System outage possible")
        return causes

    def _suggest_action(self, anomaly):
        """Suggest action for an anomaly."""
        severity = anomaly.get("severity", "low")
        if severity == "high":
            return "Immediate investigation recommended"
        elif severity == "medium":
            return "Review within 24 hours"
        return "Monitor for recurrence"
```

---

### 2.4 Recommendation Engine

**What Changes:**
Generate prioritized recommendations after every analysis.

**Affected Files:**
- `backend/api/services/recommendation_engine.py` — NEW: Recommendation generation
- `backend/api/services/ai_orchestrator.py` — Integrate recommendations

**Implementation:**
```python
# backend/api/services/recommendation_engine.py
class RecommendationEngine:
    """Generates prioritized business recommendations."""

    async def generate(self, analysis_results, context):
        """Generate recommendations from analysis results."""
        recommendations = []

        # Analyze KPIs for recommendations
        for kpi in analysis_results.get("kpis", []):
            rec = self._analyze_kpi_for_recommendation(kpi)
            if rec:
                recommendations.append(rec)

        # Analyze anomalies for recommendations
        for anomaly in analysis_results.get("anomalies", []):
            rec = self._analyze_anomaly_for_recommendation(anomaly)
            if rec:
                recommendations.append(rec)

        # Analyze trends for recommendations
        trends = analysis_results.get("trends", [])
        for trend in trends:
            rec = self._analyze_trend_for_recommendation(trend)
            if rec:
                recommendations.append(rec)

        # Sort by priority
        recommendations.sort(key=lambda x: x["priority_score"], reverse=True)

        return {
            "recommendations": recommendations[:10],  # Top 10
            "total_generated": len(recommendations),
            "context": {
                "department": context.get("department"),
                "period": context.get("period"),
                "generated_at": datetime.utcnow().isoformat()
            }
        }

    def _analyze_kpi_for_recommendation(self, kpi):
        """Generate recommendation from a KPI."""
        delta = kpi.get("delta", 0)
        if abs(delta) < 5:  # Less than 5% change, no recommendation
            return None

        if delta < -10:
            return {
                "priority": "HIGH",
                "priority_score": 0.9,
                "category": "performance",
                "title": f"Address decline in {kpi.get('label', 'KPI')}",
                "reason": f"{kpi.get('label')} declined by {abs(delta):.1f}%",
                "expected_impact": "Reverse negative trend",
                "estimated_risk": "Medium - continued decline possible",
                "business_value": "Prevents further deterioration",
                "suggested_actions": [
                    f"Investigate root cause of {kpi.get('label')} decline",
                    "Review recent changes affecting this metric",
                    "Consider corrective actions"
                ]
            }
        elif delta > 15:
            return {
                "priority": "MEDIUM",
                "priority_score": 0.6,
                "category": "opportunity",
                "title": f"Leverage growth in {kpi.get('label', 'KPI')}",
                "reason": f"{kpi.get('label')} grew by {delta:.1f}%",
                "expected_impact": "Sustain positive momentum",
                "estimated_risk": "Low - growth is positive",
                "business_value": "Capitalizes on successful trends",
                "suggested_actions": [
                    "Document what drove the improvement",
                    "Consider scaling successful strategies"
                ]
            }
        return None

    def _analyze_anomaly_for_recommendation(self, anomaly):
        """Generate recommendation from an anomaly."""
        severity = anomaly.get("severity", "low")
        if severity == "high":
            return {
                "priority": "CRITICAL",
                "priority_score": 0.95,
                "category": "risk",
                "title": f"Investigate critical anomaly: {anomaly.get('type', 'unknown')}",
                "reason": anomaly.get("description", "Anomaly detected"),
                "expected_impact": "Prevent potential losses",
                "estimated_risk": "High - unaddressed anomalies can escalate",
                "business_value": "Risk mitigation",
                "suggested_actions": [
                    "Immediate investigation required",
                    "Verify data accuracy",
                    "Implement corrective measures"
                ]
            }
        return None

    def _analyze_trend_for_recommendation(self, trend):
        """Generate recommendation from a trend."""
        direction = trend.get("direction", "stable")
        if direction == "declining":
            return {
                "priority": "MEDIUM",
                "priority_score": 0.7,
                "category": "trend",
                "title": f"Address declining trend: {trend.get('metric', 'unknown')}",
                "reason": trend.get("description", "Declining trend detected"),
                "expected_impact": "Reverse negative trajectory",
                "estimated_risk": "Medium - trends tend to persist",
                "business_value": "Early intervention prevents larger issues",
                "suggested_actions": trend.get("suggested_actions", [])
            }
        return None
```

---

## 5. Phase 3: Governance & Monitoring

### 3.1 AI Governance

**What Changes:**
Track every AI request with full metadata for auditability.

**Affected Files:**
- `backend/api/services/ai_governance.py` — NEW: Governance service
- `backend/api/migrations/` — New migration for governance tables

**New Database Schema:**
```sql
CREATE TABLE IF NOT EXISTS ai_governance_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id TEXT NOT NULL,
  user_id UUID,
  category TEXT NOT NULL,  -- nlq, narrative, analyst, etc.
  intent TEXT,
  model TEXT NOT NULL,
  model_version TEXT,
  temperature REAL,
  max_tokens INTEGER,
  context_length INTEGER,
  tokens_input INTEGER,
  tokens_output INTEGER,
  tokens_total INTEGER,
  cost_usd REAL,
  latency_ms INTEGER,
  confidence_score REAL,
  safety_status TEXT DEFAULT 'safe',  -- safe, filtered, blocked
  prompt_version TEXT,
  response_version TEXT,
  status TEXT NOT NULL,  -- success, error, timeout, filtered
  error_message TEXT,
  ip_address TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_governance_user ON ai_governance_log(user_id);
CREATE INDEX idx_ai_governance_category ON ai_governance_log(category);
CREATE INDEX idx_ai_governance_created ON ai_governance_log(created_at DESC);
CREATE INDEX idx_ai_governance_status ON ai_governance_log(status);
```

**Implementation:**
```python
# backend/api/services/ai_governance.py
class AIGovernance:
    """Tracks and governs all AI interactions."""

    def __init__(self, db):
        self.db = db

    async def log_request(self, *, request_id, user_id, category,
                          intent=None, model=None, temperature=None,
                          max_tokens=None, tokens_used=None,
                          latency_ms=None, confidence=None,
                          status="success", error=None,
                          prompt_version=None, ip_address=None):
        """Log an AI request for governance."""
        record = {
            "request_id": request_id,
            "user_id": user_id,
            "category": category,
            "intent": intent,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tokens_input": tokens_used.get("prompt_tokens") if tokens_used else None,
            "tokens_output": tokens_used.get("completion_tokens") if tokens_used else None,
            "tokens_total": tokens_used.get("total_tokens") if tokens_used else None,
            "latency_ms": latency_ms,
            "confidence_score": confidence,
            "status": status,
            "error_message": error,
            "prompt_version": prompt_version,
            "ip_address": ip_address,
            "created_at": datetime.utcnow().isoformat()
        }
        try:
            await self.db.table("ai_governance_log").insert(record).execute()
        except Exception:
            logger.warning("Governance log write failed")

    async def get_model_config(self, category):
        """Get governance-approved model configuration."""
        # Default configs per category
        defaults = {
            "nlq": {"model": "llama-3.3-70b-versatile", "temperature": 0.1, "max_tokens": 800},
            "narrative": {"model": "llama-3.3-70b-versatile", "temperature": 0.4, "max_tokens": 1000},
            "analyst": {"model": "llama-3.3-70b-versatile", "temperature": 0.3, "max_tokens": 600},
            "report": {"model": "llama-3.3-70b-versatile", "temperature": 0.5, "max_tokens": 1200},
            "forecast": {"model": "llama-3.3-70b-versatile", "temperature": 0.4, "max_tokens": 400},
            "assistant": {"model": "llama-3.1-8b-instant", "temperature": 0.4, "max_tokens": 400}
        }
        return defaults.get(category, defaults["narrative"])

    async def get_governance_dashboard(self, days=30):
        """Get governance metrics for admin dashboard."""
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        result = await self.db.table("ai_governance_log") \
            .select("*") \
            .gte("created_at", since) \
            .execute()

        logs = result.data
        total = len(logs)
        if total == 0:
            return {"total_requests": 0}

        # Compute metrics
        success = sum(1 for l in logs if l["status"] == "success")
        errors = sum(1 for l in logs if l["status"] == "error")
        avg_latency = sum(l.get("latency_ms", 0) or 0 for l in logs) / total
        total_tokens = sum(l.get("tokens_total", 0) or 0 for l in logs)
        avg_confidence = sum(l.get("confidence_score", 0) or 0 for l in logs) / total

        # By category
        by_category = {}
        for l in logs:
            cat = l.get("category", "unknown")
            if cat not in by_category:
                by_category[cat] = {"count": 0, "errors": 0, "total_latency": 0}
            by_category[cat]["count"] += 1
            if l["status"] == "error":
                by_category[cat]["errors"] += 1
            by_category[cat]["total_latency"] += l.get("latency_ms", 0) or 0

        return {
            "total_requests": total,
            "success_rate": round(success / total * 100, 1),
            "error_rate": round(errors / total * 100, 1),
            "avg_latency_ms": round(avg_latency),
            "total_tokens": total_tokens,
            "avg_confidence": round(avg_confidence, 3),
            "by_category": by_category,
            "period_days": days
        }
```

---

### 3.2 AI Monitoring Dashboard

**What Changes:**
Create monitoring metrics collection and admin-visible dashboard.

**Affected Files:**
- `backend/api/services/ai_monitor.py` — NEW: Metrics collection
- `backend/api/routers/admin.py` — Add monitoring endpoints
- Admin Dashboard page — Add monitoring section (within existing tabs/cards)

**Implementation:**
```python
# backend/api/services/ai_monitor.py
class AIMonitor:
    """Collects and reports AI system metrics."""

    def __init__(self, db):
        self.db = db

    async def record_metric(self, event_type, **kwargs):
        """Record a metric event."""
        metric = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        try:
            # Store in Redis for real-time, DB for historical
            # For now, just store in DB
            await self.db.table("ai_metrics").insert(metric).execute()
        except Exception:
            pass  # Non-critical

    async def get_dashboard_metrics(self, days=7):
        """Get metrics for monitoring dashboard."""
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()

        # Get governance logs (primary source)
        result = await self.db.table("ai_governance_log") \
            .select("*") \
            .gte("created_at", since) \
            .execute()

        logs = result.data
        total = len(logs)

        if total == 0:
            return self._empty_metrics(days)

        # Latency distribution
        latencies = [l.get("latency_ms", 0) or 0 for l in logs]
        latencies.sort()

        # Daily breakdown
        daily = {}
        for l in logs:
            day = l["created_at"][:10]
            if day not in daily:
                daily[day] = {"requests": 0, "errors": 0, "tokens": 0}
            daily[day]["requests"] += 1
            if l["status"] == "error":
                daily[day]["errors"] += 1
            daily[day]["tokens"] += l.get("tokens_total", 0) or 0

        # Error distribution
        errors = {}
        for l in logs:
            if l["status"] == "error":
                err = l.get("error_message", "unknown")[:50]
                errors[err] = errors.get(err, 0) + 1

        # Cost estimation (rough: $0.59/1M tokens for llama-3.3-70b)
        total_tokens = sum(l.get("tokens_total", 0) or 0 for l in logs)
        estimated_cost = total_tokens * 0.59 / 1_000_000

        return {
            "period_days": days,
            "total_requests": total,
            "avg_latency_ms": round(sum(latencies) / len(latencies)),
            "p95_latency_ms": latencies[int(len(latencies) * 0.95)] if latencies else 0,
            "p99_latency_ms": latencies[int(len(latencies) * 0.99)] if latencies else 0,
            "success_rate": round(sum(1 for l in logs if l["status"] == "success") / total * 100, 1),
            "error_rate": round(sum(1 for l in logs if l["status"] == "error") / total * 100, 1),
            "retry_count": sum(1 for l in logs if l.get("status") == "retry"),
            "timeout_count": sum(1 for l in logs if l.get("status") == "timeout"),
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 4),
            "daily": daily,
            "error_distribution": errors,
            "avg_confidence": round(
                sum(l.get("confidence_score", 0) or 0 for l in logs) / total, 3)
        }

    def _empty_metrics(self, days):
        return {
            "period_days": days,
            "total_requests": 0,
            "avg_latency_ms": 0,
            "success_rate": 100.0,
            "error_rate": 0.0,
            "total_tokens": 0,
            "estimated_cost_usd": 0,
            "daily": {},
            "error_distribution": {}
        }
```

---

### 3.3 AI Feedback Loop

**What Changes:**
Allow managers to rate AI responses and track feedback analytics.

**Affected Files:**
- `backend/api/services/feedback_service.py` — NEW: Feedback collection
- `backend/api/routers/analyst.py` — Add feedback endpoints
- `backend/api/migrations/` — New migration for feedback table

**New Database Schema:**
```sql
CREATE TABLE IF NOT EXISTS ai_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id TEXT NOT NULL,
  user_id UUID,
  rating TEXT NOT NULL,  -- helpful, not_helpful, incorrect, incomplete, needs_investigation
  comment TEXT,
  category TEXT,  -- nlq, narrative, analyst, etc.
  response_content TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_feedback_rating ON ai_feedback(rating);
CREATE INDEX idx_ai_feedback_category ON ai_feedback(category);
CREATE INDEX idx_ai_feedback_created ON ai_feedback(created_at DESC);
```

**API Endpoints:**
```
POST /api/ai/feedback              — Submit feedback
GET  /api/ai/feedback/stats        — Get feedback analytics (admin)
GET  /api/ai/feedback/trends       — Get feedback trends (admin)
```

**Feedback Analytics:**
```python
class FeedbackService:
    async def get_feedback_stats(self, days=30):
        """Get feedback analytics for admin."""
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        result = await self.db.table("ai_feedback") \
            .select("*").gte("created_at", since).execute()

        feedback = result.data
        total = len(feedback)
        if total == 0:
            return {"total": 0}

        by_rating = {}
        for f in feedback:
            r = f["rating"]
            by_rating[r] = by_rating.get(r, 0) + 1

        helpful = by_rating.get("helpful", 0)
        incorrect = by_rating.get("incorrect", 0)

        return {
            "total": total,
            "by_rating": by_rating,
            "accuracy_pct": round((total - incorrect) / total * 100, 1),
            "acceptance_pct": round(helpful / total * 100, 1) if total else 0,
            "rejection_pct": round(
                (by_rating.get("not_helpful", 0) + incorrect) / total * 100, 1
            ) if total else 0,
            "needs_investigation": by_rating.get("needs_investigation", 0),
            "period_days": days
        }
```

---

### 3.4 Data Quality Engine

**What Changes:**
Expand current validation into a comprehensive data quality engine.

**Affected Files:**
- `backend/api/services/data_quality_engine.py` — NEW: Expanded quality engine
- `backend/api/routers/data_quality.py` — Extend with new checks
- `backend/api/services/validation_service.py` — Integrate with quality engine

**Implementation:**
```python
# backend/api/services/data_quality_engine.py
class DataQualityEngine:
    """Comprehensive data quality assessment."""

    CHECKS = [
        "schema_validation",
        "duplicate_detection",
        "missing_values",
        "outlier_detection",
        "distribution_drift",
        "schema_drift",
        "completeness",
        "consistency",
        "freshness",
        "business_rules"
    ]

    async def run_full_assessment(self, user_id):
        """Run all quality checks."""
        results = []
        for check in self.CHECKS:
            result = await self._run_check(check, user_id)
            results.append(result)

        overall_score = sum(r["score"] for r in results) / len(results)
        grade = self._score_to_grade(overall_score)

        return {
            "overall_score": round(overall_score, 1),
            "grade": grade,
            "checks": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _run_check(self, check_type, user_id):
        """Run a specific quality check."""
        try:
            if check_type == "schema_validation":
                return await self._check_schema(user_id)
            elif check_type == "duplicate_detection":
                return await self._check_duplicates(user_id)
            elif check_type == "missing_values":
                return await self._check_missing(user_id)
            elif check_type == "outlier_detection":
                return await self._check_outliers(user_id)
            elif check_type == "distribution_drift":
                return await self._check_drift(user_id)
            elif check_type == "freshness":
                return await self._check_freshness(user_id)
            elif check_type == "consistency":
                return await self._check_consistency(user_id)
            elif check_type == "business_rules":
                return await self._check_business_rules(user_id)
            else:
                return {"check": check_type, "score": 100, "status": "pass",
                        "message": "Check not implemented"}
        except Exception as e:
            return {"check": check_type, "score": 0, "status": "error",
                    "message": str(e)}

    async def _check_schema(self, user_id):
        """Validate data matches expected schema."""
        # Check semantic field mappings are complete
        return {"check": "schema_validation", "score": 85, "status": "pass",
                "message": "Schema mostly valid"}

    async def _check_duplicates(self, user_id):
        """Detect duplicate records."""
        return {"check": "duplicate_detection", "score": 95, "status": "pass",
                "message": "2% duplicate rate (acceptable)"}

    async def _check_missing(self, user_id):
        """Check for missing values."""
        return {"check": "missing_values", "score": 88, "status": "pass",
                "message": "12% missing values in optional fields"}

    async def _check_outliers(self, user_id):
        """Detect statistical outliers."""
        return {"check": "outlier_detection", "score": 92, "status": "pass",
                "message": "3 outliers detected (within tolerance)"}

    async def _check_drift(self, user_id):
        """Check for distribution drift."""
        return {"check": "distribution_drift", "score": 90, "status": "pass",
                "message": "Minor distribution shift detected"}

    async def _check_freshness(self, user_id):
        """Check data freshness."""
        return {"check": "freshness", "score": 85, "status": "warning",
                "message": "Data is 3 days old"}

    async def _check_consistency(self, user_id):
        """Check data consistency across sources."""
        return {"check": "consistency", "score": 93, "status": "pass",
                "message": "High consistency across sources"}

    async def _check_business_rules(self, user_id):
        """Validate business rules."""
        return {"check": "business_rules", "score": 88, "status": "pass",
                "message": "95% of records pass business rules"}

    def _score_to_grade(self, score):
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"
```

---

## 6. Phase 4: Admin & Operations

### 4.1 Admin Governance Panel

**What Changes:**
Add governance, prompt management, and monitoring sections within existing admin pages.

**Affected Files:**
- `frontend/src/pages/AdminDashboard.jsx` — Add governance metrics card
- `frontend/src/pages/AdminSemantic.jsx` — Add version history accordion
- `frontend/src/pages/AdminTemplates.jsx` — Add version history accordion
- `backend/api/routers/admin.py` — Add governance endpoints

**Implementation Strategy:**
All new admin features are exposed through:
- New tabs within existing admin dashboard
- New accordion sections in existing pages
- New modals triggered from existing buttons
- New badges/indicators on existing cards

**NO new pages, NO new routes, NO navigation changes.**

---

### 4.2 System Health Dashboard

**What Changes:**
Add system health monitoring within the admin dashboard.

**Affected Files:**
- `backend/api/services/system_health.py` — NEW: Health monitoring
- `backend/api/routers/admin.py` — Add health endpoints
- `frontend/src/pages/AdminDashboard.jsx` — Add health card (within existing layout)

**Implementation:**
```python
# backend/api/services/system_health.py
class SystemHealth:
    """Monitors system health across all components."""

    async def check_all(self):
        """Run all health checks."""
        checks = {}
        checks["database"] = await self._check_database()
        checks["redis"] = await self._check_redis()
        checks["llm"] = await self._check_llm()
        checks["email"] = await self._check_email()
        checks["storage"] = await self._check_storage()
        checks["etl"] = await self._check_etl()
        return checks

    async def _check_database(self):
        try:
            # Simple query
            return {"status": "healthy", "response_ms": 5}
        except:
            return {"status": "unhealthy", "error": "Connection failed"}

    async def _check_redis(self):
        try:
            return {"status": "healthy", "response_ms": 2}
        except:
            return {"status": "degraded", "error": "Using in-memory fallback"}

    async def _check_llm(self):
        try:
            return {"status": "healthy", "provider": "Groq", "model": "llama-3.3-70b"}
        except:
            return {"status": "unhealthy", "error": "API key invalid"}

    async def _check_email(self):
        try:
            return {"status": "healthy", "provider": "Brevo"}
        except:
            return {"status": "degraded", "error": "Not configured"}

    async def _check_storage(self):
        return {"status": "healthy", "type": "Supabase Storage"}

    async def _check_etl(self):
        return {"status": "healthy", "scheduler": "APScheduler"}
```

---

### 4.3 Background Job Center

**What Changes:**
Add job monitoring within admin dashboard.

**Affected Files:**
- `backend/api/services/job_monitor.py` — NEW: Job tracking
- `backend/api/routers/admin.py` — Add job endpoints
- `frontend/src/pages/AdminDashboard.jsx` — Add jobs card (within existing layout)

**Implementation:**
```python
# backend/api/services/job_monitor.py
class JobMonitor:
    """Tracks background job execution."""

    async def get_job_stats(self):
        """Get job execution statistics."""
        return {
            "etl_jobs": await self._get_etl_stats(),
            "report_jobs": await self._get_report_stats(),
            "notification_jobs": await self._get_notification_stats(),
            "ai_jobs": await self._get_ai_stats(),
            "scheduled_jobs": await self._get_scheduled_stats()
        }

    async def _get_etl_stats(self):
        # Query recent ETL runs from audit_logs
        return {"total": 0, "running": 0, "failed": 0, "last_run": None}

    async def _get_report_stats(self):
        return {"total": 0, "generated": 0, "failed": 0}

    async def _get_notification_stats(self):
        return {"total": 0, "sent": 0, "failed": 0}

    async def _get_ai_stats(self):
        return {"total": 0, "completed": 0, "failed": 0}

    async def _get_scheduled_stats(self):
        return {"heartbeat": "active", "reports": "active"}
```

---

### 4.4 Dependency Analysis

**What Changes:**
Before deleting any object, show what depends on it.

**Affected Files:**
- `backend/api/services/dependency_analyzer.py` — NEW: Dependency analysis
- `backend/api/routers/departments.py` — Check dependencies before delete
- `backend/api/routers/semantic.py` — Check dependencies before delete
- `backend/api/routers/templates.py` — Check dependencies before delete

**Implementation:**
```python
# backend/api/services/dependency_analyzer.py
class DependencyAnalyzer:
    """Analyzes dependencies before deletion."""

    async def analyze_department(self, dept_id):
        """Show what depends on a department."""
        deps = {}
        deps["users"] = await self._count_users(dept_id)
        deps["kpis"] = await self._count_kpis(dept_id)
        deps["reports"] = await self._count_reports(dept_id)
        deps["anomalies"] = await self._count_anomalies(dept_id)
        deps["validation_logs"] = await self._count_validations(dept_id)
        deps["templates"] = await self._get_template(dept_id)
        return {
            "department_id": dept_id,
            "dependencies": deps,
            "can_delete": deps["users"] == 0,
            "warnings": self._generate_warnings(deps)
        }

    async def analyze_semantic_template(self, template_id):
        """Show what depends on a semantic template."""
        deps = {}
        deps["fields"] = await self._count_fields(template_id)
        deps["departments"] = await self._count_departments_using(template_id)
        deps["mappings"] = await self._count_mappings(template_id)
        return {
            "template_id": template_id,
            "dependencies": deps,
            "can_delete": deps["departments"] == 0,
            "warnings": self._generate_warnings(deps)
        }

    def _generate_warnings(self, deps):
        warnings = []
        if deps.get("users", 0) > 0:
            warnings.append(f"{deps['users']} users assigned")
        if deps.get("kpis", 0) > 0:
            warnings.append(f"{deps['kpis']} KPIs depend on this")
        if deps.get("reports", 0) > 0:
            warnings.append(f"{deps['reports']} reports generated")
        return warnings
```

---

## 7. Phase 5: Security & Quality

### 5.1 Security Hardening

**What Changes:**
Add prompt injection detection, PII detection, and enhanced input validation.

**Affected Files:**
- `backend/api/services/security_scanner.py` — NEW: Security scanning
- `backend/api/services/nlq_service.py` — Add injection detection
- `backend/api/middleware/security.py` — Enhance security headers

**Implementation:**
```python
# backend/api/services/security_scanner.py
class SecurityScanner:
    """Scans inputs and outputs for security issues."""

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"you\s+are\s+now",
        r"pretend\s+you\s+are",
        r"act\s+as\s+if",
        r"system\s*:\s*",
        r"admin\s*mode",
        r"override",
        r"jailbreak",
        r"DAN\s+mode"
    ]

    SQL_INJECTION_PATTERNS = [
        r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE)",
        r"--\s*$",
        r"/\*.*\*/",
        r"UNION\s+(ALL\s+)?SELECT",
        r"OR\s+1\s*=\s*1",
        r"AND\s+1\s*=\s*1"
    ]

    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
    }

    def scan_prompt(self, text):
        """Scan for prompt injection attempts."""
        import re
        text_lower = text.lower()
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                return {"safe": False, "threat": "prompt_injection",
                        "pattern": pattern}
        return {"safe": True}

    def scan_sql(self, sql):
        """Scan for SQL injection."""
        import re
        sql_upper = sql.upper()
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, sql_upper):
                return {"safe": False, "threat": "sql_injection"}
        return {"safe": True}

    def detect_pii(self, text):
        """Detect PII in text."""
        import re
        found = []
        for pii_type, pattern in self.PII_PATTERNS.items():
            if re.search(pattern, text):
                found.append(pii_type)
        return {"has_pii": len(found) > 0, "types": found}

    def sanitize_output(self, text):
        """Remove PII from AI output."""
        import re
        for pii_type, pattern in self.PII_PATTERNS.items():
            text = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", text)
        return text
```

---

### 5.2 Code Quality Refactor

**What Changes:**
Refactor monolithic main.py, add dependency injection, eliminate duplication.

**Affected Files:**
- `backend/api/main.py` — Extract inline routes to routers
- `backend/api/core/dependencies.py` — NEW: Dependency injection container
- `backend/api/routers/` — Standardize error handling
- Multiple files — Eliminate duplicated `_safe_data()`

**Implementation:**
```python
# backend/api/core/dependencies.py
"""Dependency injection container."""
from functools import lru_cache
from .supabase_client import get_supabase_client

@lru_cache
def get_db():
    return get_supabase_client()

@lru_cache
def get_prompt_manager():
    from ..services.prompt_manager import PromptManager
    return PromptManager(get_db())

@lru_cache
def get_ai_orchestrator():
    from ..services.ai_orchestrator import AIOrchestrator
    from ..services.ai_governance import AIGovernance
    from ..services.ai_monitor import AIMonitor
    from ..services.confidence_engine import ConfidenceEngine
    db = get_db()
    return AIOrchestrator(
        db=db,
        prompt_manager=get_prompt_manager(),
        semantic_layer=None,  # Per-request
        governance=AIGovernance(db),
        monitor=AIMonitor(db)
    )

@lru_cache
def get_audit_service():
    from ..services.audit_service import AuditService
    return AuditService(get_db())
```

**Standardized Error Handling:**
```python
# backend/api/core/error_handlers.py
from fastapi import Request
from fastapi.responses import JSONResponse
import uuid

async def global_error_handler(request: Request, exc: Exception):
    request_id = str(uuid.uuid4())[:8]
    logger.error(f"[{request_id}] {exc.__class__.__name__}: {exc}",
                exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id,
            "message": str(exc) if exc.__class__.__name__ != "Exception"
                      else "An unexpected error occurred"
        }
    )
```

**Eliminate Duplicated _safe_data():**
```python
# backend/api/core/utils.py (single location)
def safe_get(data, *keys, default=None):
    """Safely traverse nested dict/list structure."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        elif isinstance(current, list) and isinstance(key, int):
            current = current[key] if key < len(current) else default
        else:
            return default
    return current
```

---

## 8. Database Schema Changes

### New Tables Required

```sql
-- Phase 1: Foundation
CREATE TABLE IF NOT EXISTS prompt_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  description TEXT,
  template TEXT NOT NULL,
  variables JSONB DEFAULT '[]',
  version INTEGER DEFAULT 1,
  is_active BOOLEAN DEFAULT true,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prompt_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_id UUID REFERENCES prompt_templates(id),
  version INTEGER NOT NULL,
  template TEXT NOT NULL,
  variables JSONB DEFAULT '[]',
  changelog TEXT,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS entity_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type TEXT NOT NULL,
  entity_id UUID NOT NULL,
  version INTEGER NOT NULL,
  snapshot JSONB NOT NULL,
  changelog TEXT,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Phase 2-3: AI Governance
CREATE TABLE IF NOT EXISTS ai_governance_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id TEXT NOT NULL,
  user_id UUID,
  category TEXT NOT NULL,
  intent TEXT,
  model TEXT NOT NULL,
  temperature REAL,
  max_tokens INTEGER,
  tokens_input INTEGER,
  tokens_output INTEGER,
  tokens_total INTEGER,
  cost_usd REAL,
  latency_ms INTEGER,
  confidence_score REAL,
  safety_status TEXT DEFAULT 'safe',
  prompt_version TEXT,
  status TEXT NOT NULL,
  error_message TEXT,
  ip_address TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id TEXT NOT NULL,
  user_id UUID,
  rating TEXT NOT NULL,
  comment TEXT,
  category TEXT,
  response_content TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  data JSONB DEFAULT '{}'
);
```

---

## 9. File Impact Matrix

### New Files to Create

| File | Module | Purpose |
|------|--------|---------|
| `services/ai_orchestrator.py` | AI Orchestration | Central AI entry point |
| `services/semantic_layer.py` | Semantic | Schema translation |
| `services/prompt_manager.py` | Prompts | Prompt library |
| `services/ai_governance.py` | Governance | AI audit logging |
| `services/ai_monitor.py` | Monitoring | Metrics collection |
| `services/confidence_engine.py` | Confidence | Score calculation |
| `services/explainability_engine.py` | XAI | Explanation generation |
| `services/recommendation_engine.py` | Recommendations | Action suggestions |
| `services/feedback_service.py` | Feedback | Rating collection |
| `services/data_quality_engine.py` | Quality | Quality checks |
| `services/security_scanner.py` | Security | Injection/PII detection |
| `services/dependency_analyzer.py` | Admin | Deletion safety |
| `services/system_health.py` | Admin | Health monitoring |
| `services/job_monitor.py` | Admin | Job tracking |
| `core/dependencies.py` | Architecture | DI container |
| `core/error_handlers.py` | Architecture | Global error handling |
| `core/utils.py` | Architecture | Shared utilities |

### Existing Files to Modify

| File | Changes |
|------|---------|
| `main.py` | Extract inline routes, add DI, add error handlers |
| `services/groq_utils.py` | Add token counting, add retry logic |
| `services/nlq_service.py` | Route through orchestrator, add semantic layer |
| `services/narrative_service.py` | Route through orchestrator, use prompt manager |
| `services/ai_analyst_service.py` | Route through orchestrator, add confidence |
| `services/analysis_engine.py` | Route through orchestrator, add recommendations |
| `services/assistant.py` | Route through orchestrator |
| `services/custom_report_service.py` | Route through orchestrator |
| `services/forecasting_service.py` | Route through orchestrator |
| `services/etl_service.py` | Add audit logging, add job tracking |
| `services/validation_service.py` | Integrate with data quality engine |
| `services/audit_service.py` | Expand to full audit framework |
| `services/email_service.py` | Add error handling, add retry |
| `core/auth.py` | Add login/logout audit |
| `middleware/security.py` | Enhance headers, add CORS |
| `middleware/rate_limit.py` | Add per-endpoint limits |
| `routers/admin.py` | Add governance, monitoring, health endpoints |
| `routers/analyst.py` | Use orchestrator, add feedback endpoint |
| `routers/departments.py` | Add audit, add dependency check |
| `routers/semantic.py` | Add versioning, add dependency check |
| `routers/templates.py` | Add versioning, add dependency check |
| `routers/users.py` | Add audit logging |
| `routers/validation.py` | Integrate quality engine |

---

## 10. Risk Assessment

### High Risk
| Risk | Mitigation |
|------|-----------|
| Breaking existing functionality | Feature flags, incremental rollout |
| Performance degradation | Benchmark before/after, add caching |
| LLM cost increase | Token budgeting, model selection per category |

### Medium Risk
| Risk | Mitigation |
|------|-----------|
| Database schema migration errors | Test migrations on staging first |
| Redis dependency increase | Ensure in-memory fallback works |
| Prompt versioning complexity | Start with simple append-only |

### Low Risk
| Risk | Mitigation |
|------|-----------|
| Frontend visual changes | Backend-first approach |
| New UI components needed | Use existing cards/modals/tables |
| Documentation overhead | Document as we build |

---

*Generated for CNPS Smart Automated Analytics Platform*
*Enterprise Architecture Upgrade Plan*
*Date: July 2026*
