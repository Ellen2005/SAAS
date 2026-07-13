"""
Circuit Breaker for LLM Providers
Prevents cascading failures when LLM services are unavailable.
"""
import asyncio
import time
import logging
from enum import Enum
from typing import Optional, Callable, Any, Dict, List
from dataclasses import dataclass, field
from collections import deque
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation, requests pass through
    OPEN = "open"           # Failing, requests blocked
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 2          # Successes in half-open before closing
    timeout_seconds: float = 30.0       # Time before attempting half-open
    half_open_max_requests: int = 3     # Max concurrent requests in half-open
    excluded_exceptions: tuple = ()     # Exceptions that don't count as failures


@dataclass
class CircuitBreakerStats:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: List[Dict[str, Any]] = field(default_factory=list)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for LLM providers.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests rejected immediately
    - HALF_OPEN: Testing recovery, limited requests allowed
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.fallback = fallback
        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._failure_count = 0
        self._success_count = 0
        self._half_open_requests = 0
        self._last_state_change = time.time()
        self._lock = asyncio.Lock()
        
    @property
    def state(self) -> CircuitState:
        return self._state
    
    @property
    def stats(self) -> CircuitBreakerStats:
        return self._stats
    
    def _record_state_change(self, old_state: CircuitState, new_state: CircuitState):
        self._stats.state_changes.append({
            "from": old_state.value,
            "to": new_state.value,
            "timestamp": time.time(),
            "failure_count": self._failure_count,
            "success_count": self._success_count,
        })
        logger.info(f"Circuit breaker '{self.name}': {old_state.value} -> {new_state.value}")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset from OPEN."""
        return (time.time() - self._last_state_change) >= self.config.timeout_seconds
    
    async def _transition_to(self, new_state: CircuitState):
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()
        self._record_state_change(old_state, new_state)
        
        if new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
            self._half_open_requests = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
    
    def _is_excluded_exception(self, exc: Exception) -> bool:
        """Check if exception should be excluded from failure count."""
        return isinstance(exc, self.config.excluded_exceptions)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with circuit breaker protection."""
        async with self._lock:
            self._stats.total_requests += 1
            
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    await self._transition_to(CircuitState.HALF_OPEN)
                else:
                    self._stats.rejected_requests += 1
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Retry after {self.config.timeout_seconds}s."
                    )
            
            # Check half-open request limit
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_requests >= self.config.half_open_max_requests:
                    self._stats.rejected_requests += 1
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is HALF_OPEN. "
                        f"Max concurrent requests ({self.config.half_open_max_requests}) reached."
                    )
                self._half_open_requests += 1
        
        # Execute the function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            await self._on_success()
            return result
            
        except Exception as exc:
            await self._on_failure(exc)
            raise
    
    async def _on_success(self):
        async with self._lock:
            self._stats.successful_requests += 1
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success in closed state
                self._failure_count = 0
    
    async def _on_failure(self, exc: Exception):
        async with self._lock:
            if self._is_excluded_exception(exc):
                return
            
            self._stats.failed_requests += 1
            self._failure_count += 1
            self._stats.last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open immediately opens the circuit
                await self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "stats": {
                "total_requests": self._stats.total_requests,
                "successful_requests": self._stats.successful_requests,
                "failed_requests": self._stats.failed_requests,
                "rejected_requests": self._stats.rejected_requests,
                "failure_rate": (
                    self._stats.failed_requests / self._stats.total_requests
                    if self._stats.total_requests > 0 else 0
                ),
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout_seconds": self.config.timeout_seconds,
            },
            "last_state_change": self._last_state_change,
        }
    
    def reset(self):
        """Manually reset the circuit breaker to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_requests = 0
        self._last_state_change = time.time()
        logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is OPEN and rejects a request."""
    pass


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable] = None
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config, fallback)
        return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        return self._breakers.get(name)
    
    def remove(self, name: str):
        if name in self._breakers:
            del self._breakers[name]
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        return {name: cb.get_metrics() for name, cb in self._breakers.items()}
    
    async def reset_all(self):
        async with self._lock:
            for cb in self._breakers.values():
                cb.reset()


# Global registry instance
_circuit_breaker_registry = CircuitBreakerRegistry()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    return _circuit_breaker_registry


# Pre-configured breakers for common LLM providers
def get_groq_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker configured for Groq API."""
    config = CircuitBreakerConfig(
        failure_threshold=3,           # Open after 3 failures
        success_threshold=2,           # Close after 2 successes
        timeout_seconds=60.0,          # Wait 60s before half-open
        half_open_max_requests=2,      # Allow 2 test requests
        excluded_exceptions=(asyncio.TimeoutError,),  # Don't count timeouts
    )
    return _circuit_breaker_registry.get_or_create("groq", config)


def get_ollama_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker configured for Ollama."""
    config = CircuitBreakerConfig(
        failure_threshold=5,           # More tolerant for local
        success_threshold=2,
        timeout_seconds=30.0,          # Faster recovery attempt
        half_open_max_requests=3,
        excluded_exceptions=(ConnectionRefusedError, asyncio.TimeoutError),
    )
    return _circuit_breaker_registry.get_or_create("ollama", config)


@asynccontextmanager
async def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Context manager for using a circuit breaker."""
    cb = _circuit_breaker_registry.get_or_create(name, config)
    try:
        yield cb
    finally:
        pass  # No cleanup needed


# Decorator for easy circuit breaker usage
def with_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator to add circuit breaker to a function."""
    def decorator(func: Callable) -> Callable:
        cb = _circuit_breaker_registry.get_or_create(name, config)
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await cb.call(func, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return asyncio.run(cb.call(func, *args, **kwargs))
            return sync_wrapper
    return decorator