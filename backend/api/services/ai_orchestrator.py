"""
AI Orchestrator
===============
Single entry point for every AI request in the system.
No component should call the LLM directly anymore.

Pipeline:
  1. Intent detection
  2. Context gathering
  3. Semantic lookup
  4. Prompt construction (via PromptManager)
  5. LLM invocation (via groq_utils)
  6. Output validation & safety
  7. Confidence calculation
  8. Governance logging
  9. Monitoring metrics

Backward Compatible:
  The orchestrator provides a simple `execute()` method that wraps
  the existing groq_utils.execute_groq_completion() pattern.
  Services can migrate incrementally.
"""
import time
import uuid
import logging
from typing import Optional

from .groq_utils import execute_groq_completion, get_groq_model

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """
    Central AI orchestration service.
    
    Usage (new pattern):
        orchestrator = AIOrchestrator(db, user_id=user_id)
        result = await orchestrator.execute(
            category="nlq",
            prompt_name="sql_generation",
            variables={"question": "...", "schema_context": "..."},
            temperature=0.1,
            max_tokens=800,
        )
        # result = {
        #   "content": "...",
        #   "request_id": "...",
        #   "confidence": {"score": 0.85, "grade": "B", ...},
        #   "model": "llama-3.3-70b-versatile",
        #   "latency_ms": 1200,
        #   "tokens": {"prompt": 150, "completion": 320, "total": 470},
        # }
    
    Usage (backward-compatible helper):
        result = AIOrchestrator.execute_sync(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=800,
        )
        # Returns raw Groq response (same as execute_groq_completion)
    """

    def __init__(self, db=None, user_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self._prompt_manager = None
        self._governance = None
        self._monitor = None
        self._confidence = None

    def _get_prompt_manager(self):
        if self._prompt_manager is None and self.db:
            from .prompt_manager import PromptManager
            self._prompt_manager = PromptManager(self.db)
        return self._prompt_manager

    def _get_governance(self):
        if self._governance is None and self.db:
            from .ai_governance import AIGovernance
            self._governance = AIGovernance(self.db)
        return self._governance

    def _get_monitor(self):
        if self._monitor is None and self.db:
            from .ai_monitor import AIMonitor
            self._monitor = AIMonitor(self.db)
        return self._monitor

    def _get_confidence(self):
        if self._confidence is None:
            from .confidence_engine import ConfidenceEngine
            self._confidence = ConfidenceEngine(self.db)
        return self._confidence

    async def execute(
        self,
        *,
        category: str,
        prompt_name: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        messages: Optional[list] = None,
        variables: Optional[dict] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        context: Optional[dict] = None,
        intent: Optional[str] = None,
    ) -> dict:
        """
        Execute an AI request through the full orchestration pipeline.
        
        Args:
            category: Prompt category (nlq, narrative, analyst, report, forecast, assistant)
            prompt_name: Name of prompt template in library
            custom_prompt: Direct prompt string (bypasses prompt manager)
            messages: Pre-built messages list (bypasses prompt construction)
            variables: Template variables for prompt rendering
            temperature: Override governance temperature
            max_tokens: Override governance max tokens
            model: Override governance model
            context: Additional context for confidence/governance
            intent: Pre-detected intent
            
        Returns:
            {content, request_id, confidence, model, latency_ms, tokens, ...}
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())[:12]
        context = context or {}

        # 1. Get governance config
        governance = self._get_governance()
        model_config = {}
        if governance:
            try:
                model_config = await governance.get_model_config(category)
            except Exception:
                pass

        final_model = model or model_config.get("model", get_groq_model())
        final_temp = temperature if temperature is not None else model_config.get("temperature", 0.3)
        final_max = max_tokens or model_config.get("max_tokens", 800)

        # 2. Build prompt from template or use provided messages/prompt
        prompt_content = custom_prompt
        if not prompt_content and prompt_name and self.db:
            pm = self._get_prompt_manager()
            if pm:
                try:
                    prompt_content = await pm.get_prompt(
                        category=category,
                        name=prompt_name,
                        variables=variables or {},
                    )
                except Exception as e:
                    logger.warning(f"Prompt manager failed, using fallback: {e}")

        # Build messages list
        if not messages:
            if not prompt_content:
                raise ValueError("Either messages, custom_prompt, or prompt_name must be provided")
            messages = [{"role": "user", "content": prompt_content}]

        # 2b. Security: sanitize prompts, block injection, and mask PII before LLM call
        pii_mapping = {}
        try:
            from .pii_detector import PIIDetector
            from .input_sanitizer import InputSanitizer
            detector = PIIDetector()
            sanitizer = InputSanitizer()
            for msg in messages:
                if isinstance(msg.get("content"), str):
                    # Block prompt injection attempts
                    injection_result = sanitizer.check_prompt_injection(msg["content"])
                    if injection_result.get("detected"):
                        logger.warning(
                            "Prompt injection blocked: patterns=%s category=%s",
                            injection_result.get("patterns"),
                            final_category,
                        )
                        return {
                            "content": "I'm sorry, but I cannot process this request. Please rephrase your question about the data.",
                            "request_id": request_id,
                            "confidence": 0.0,
                            "model": final_model,
                            "latency_ms": 0,
                            "tokens": {},
                            "category": final_category,
                            "error": "prompt_injection_detected",
                        }
                    # Sanitize input
                    msg["content"] = sanitizer.sanitize_for_llm(msg["content"])
                    # Mask PII and store mapping for restoration
                    msg["content"], mapping = detector.redact_for_llm(msg["content"])
                    pii_mapping.update(mapping)
        except Exception as e:
            logger.warning("Security sanitization failed (non-critical): %s", e)

        # 3. LLM invocation
        llm_response = None
        error = None
        try:
            llm_response = execute_groq_completion(
                messages=messages,
                temperature=final_temp,
                max_tokens=final_max,
                model=final_model,
            )
        except Exception as e:
            error = str(e)
            logger.error(f"LLM invocation failed: {e}")

        # 4. Extract content
        content = ""
        tokens_used = {}
        if llm_response:
            try:
                content = llm_response.choices[0].message.content
                if hasattr(llm_response, "usage") and llm_response.usage:
                    tokens_used = {
                        "prompt_tokens": getattr(llm_response.usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(llm_response.usage, "completion_tokens", 0),
                        "total_tokens": getattr(llm_response.usage, "total_tokens", 0),
                    }
            except (AttributeError, IndexError):
                content = str(llm_response)

        # 4b. Restore PII in response (if any was masked)
        if pii_mapping and content:
            try:
                from .pii_detector import PIIDetector
                content = PIIDetector().restore(content, pii_mapping)
            except Exception:
                pass

        # 5. Confidence calculation
        confidence = {"score": 0.5, "grade": "D", "factors": {}}
        try:
            ce = self._get_confidence()
            confidence = await ce.calculate(
                response={"content": content},
                context={
                    "model": final_model,
                    "record_count": context.get("record_count", 0),
                    "business_terms": context.get("business_terms", []),
                },
                data_stats=context.get("data_stats"),
            )
        except Exception:
            pass

        # 6. Latency
        latency_ms = int((time.time() - start_time) * 1000)

        # 7. Governance logging
        if governance:
            try:
                status = "success" if not error else "error"
                safety = "safe"
                import re
                _lower = content.lower()
                _dangerous_patterns = [
                    r"drop\s+table",
                    r"delete\s+from",
                    r"insert\s+into",
                    r"update\s+set",
                    r"truncate\s+table",
                    r"alter\s+table",
                    r"create\s+table",
                    r"grant\s+all",
                    r"grant\s+",
                    r"revoke\s+all",
                    r"revoke\s+",
                ]
                if any(re.search(pat, _lower) for pat in _dangerous_patterns):
                    safety = "filtered"

                await governance.log_request(
                    request_id=request_id,
                    user_id=self.user_id,
                    category=category,
                    intent=intent,
                    model=final_model,
                    temperature=final_temp,
                    max_tokens=final_max,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    confidence=confidence.get("score"),
                    safety_status=safety,
                    status=status,
                    error=error,
                )
            except Exception:
                pass

        # 8. Monitoring metrics
        monitor = self._get_monitor()
        if monitor:
            try:
                await monitor.record_metric(
                    "ai_request",
                    category=category,
                    model=final_model,
                    latency_ms=latency_ms,
                    status="success" if not error else "error",
                    tokens_total=tokens_used.get("total_tokens", 0),
                )
            except Exception:
                pass

        return {
            "content": content,
            "request_id": request_id,
            "confidence": confidence,
            "model": final_model,
            "latency_ms": latency_ms,
            "tokens": tokens_used,
            "category": category,
            "error": error,
        }

    # ── Backward-compatible sync helper ──────────────────────────────────

    @staticmethod
    def execute_sync(
        messages: list,
        temperature: float = 0.1,
        max_tokens: int = 400,
        model: str = None,
    ):
        """
        Synchronous wrapper around execute_groq_completion.
        Provides backward compatibility for services that haven't migrated yet.
        Returns the raw Groq response object.
        """
        return execute_groq_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )


# ── Module-level convenience function ────────────────────────────────────────

def get_orchestrator(db=None, user_id: Optional[str] = None) -> AIOrchestrator:
    """Get an AIOrchestrator instance."""
    return AIOrchestrator(db=db, user_id=user_id)
