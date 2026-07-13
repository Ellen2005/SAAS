"""
Structured logging with correlation IDs for request tracing.
"""
import logging
import json
import uuid
import time
import sys
from contextvars import ContextVar
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# Context variable to store correlation ID across async boundaries
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
request_start_time_var: ContextVar[Optional[float]] = ContextVar("request_start_time", default=None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter that includes correlation ID and structured fields."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Get correlation ID from context
        correlation_id = correlation_id_var.get()
        
        # Base log structure
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add any extra fields attached to the record
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "name", "pathname", "process", "processName",
                "relativeCreated", "thread", "threadName", "exc_info",
                "exc_text", "stack_info", "getMessage"
            }:
                log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


class CorrelationLogger:
    """Logger wrapper that automatically includes correlation ID."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def _log(self, level: int, message: str, **kwargs):
        """Log with extra fields."""
        self.logger.log(level, message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        self._log(logging.ERROR, message, exc_info=True, **kwargs)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set a new correlation ID or generate one."""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())[:8]
    correlation_id_var.set(correlation_id)
    return correlation_id


def clear_correlation_id():
    """Clear the correlation ID from context."""
    correlation_id_var.set(None)


def get_request_start_time() -> Optional[float]:
    """Get the request start time."""
    return request_start_time_var.get()


def set_request_start_time(start_time: Optional[float] = None):
    """Set the request start time."""
    if start_time is None:
        start_time = time.perf_counter()
    request_start_time_var.set(start_time)


def clear_request_start_time():
    """Clear the request start time."""
    request_start_time_var.set(None)


def get_elapsed_ms() -> Optional[float]:
    """Get elapsed time in milliseconds since request start."""
    start = get_request_start_time()
    if start is None:
        return None
    return round((time.perf_counter() - start) * 1000, 2)


def setup_structured_logging(level: int = logging.INFO):
    """Configure structured JSON logging for the application."""
    # Create formatter
    formatter = StructuredFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler with structured formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)
    
    return root_logger


class RequestLoggingMiddleware:
    """Middleware to log request/response with correlation IDs."""
    
    def __init__(self, app, logger: Optional[logging.Logger] = None):
        self.app = app
        self.logger = logger or logging.getLogger("request")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Generate or extract correlation ID
        correlation_id = None
        headers = dict(scope.get("headers", []))
        
        # Check for existing correlation ID in headers
        if b"x-correlation-id" in headers:
            correlation_id = headers[b"x-correlation-id"].decode()
        elif b"x-request-id" in headers:
            correlation_id = headers[b"x-request-id"].decode()
        
        # Set up context
        correlation_id = set_correlation_id(correlation_id)
        set_request_start_time()
        
        # Log request start
        self.logger.info(
            "Request started",
            method=scope.get("method"),
            path=scope.get("path"),
            query_string=scope.get("query_string", b"").decode(),
            client=scope.get("client"),
        )
        
        start_time = time.perf_counter()
        
        # Wrap send to capture response
        response_status = None
        response_headers = {}
        
        async def send_wrapper(message):
            nonlocal response_status, response_headers
            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = dict(message.get("headers", []))
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            elapsed = round((time.perf_counter() - start_time) * 1000, 2)
            self.logger.exception(
                "Request failed",
                status_code=500,
                elapsed_ms=elapsed,
                error=str(e)
            )
            raise
        finally:
            elapsed = round((time.perf_counter() - start_time) * 1000, 2)
            self.logger.info(
                "Request completed",
                status_code=response_status,
                elapsed_ms=elapsed,
            )
            clear_correlation_id()
            clear_request_start_time()


def get_correlation_logger(name: str) -> CorrelationLogger:
    """Get a correlation-aware logger instance."""
    return CorrelationLogger(logging.getLogger(name))


# Convenience function for getting a logger with correlation ID
def get_logger(name: str) -> CorrelationLogger:
    """Get a correlation-aware logger."""
    return get_correlation_logger(name)