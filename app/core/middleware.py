"""
Middleware for request tracing and correlation in SINPE Bridge API.

Provides:
- Correlation ID propagation
- Request ID generation
- Trace context management
- Structured logging
- Performance timing
"""

import logging
import uuid
import time
import json
from typing import Callable
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from contextvars import ContextVar

# Context variables for request tracing
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
device_id_var: ContextVar[str] = ContextVar("device_id", default="")

logger = logging.getLogger(__name__)


class TraceContext:
    """Context for distributed tracing across SINPE Bridge."""
    
    def __init__(
        self,
        request_id: str = None,
        correlation_id: str = None,
        trace_id: str = None,
        device_id: str = None,
        timestamp: str = None,
    ):
        self.request_id = request_id or str(uuid.uuid4())
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.trace_id = trace_id or str(uuid.uuid4())
        self.device_id = device_id or ""
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.start_time = time.time()
    
    @property
    def elapsed_ms(self) -> float:
        return (time.time() - self.start_time) * 1000
    
    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "device_id": self.device_id,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_headers(cls, headers: dict, timestamp: str = None) -> "TraceContext":
        """Extract trace context from request headers."""
        return cls(
            request_id=headers.get("x-request-id"),
            correlation_id=headers.get("x-correlation-id"),
            trace_id=headers.get("x-trace-id"),
            device_id=headers.get("x-device-id", ""),
            timestamp=timestamp or datetime.utcnow().isoformat(),
        )


def get_trace_context() -> TraceContext:
    """Get current trace context from context variables."""
    return TraceContext(
        request_id=request_id_var.get(),
        correlation_id=correlation_id_var.get(),
        trace_id=trace_id_var.get(),
        device_id=device_id_var.get(),
    )


def set_trace_context(context: TraceContext):
    """Set trace context in context variables."""
    request_id_var.set(context.request_id)
    correlation_id_var.set(context.correlation_id)
    trace_id_var.set(context.trace_id)
    device_id_var.set(context.device_id)


class TraceMiddleware(BaseHTTPMiddleware):
    """
    Middleware to propagate trace context across requests.
    
    Adds trace headers to responses and logs structured trace information.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or create trace context from request headers
        trace_context = TraceContext.from_headers(dict(request.headers))
        set_trace_context(trace_context)
        
        # Log request
        body_preview = ""
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    body_preview = body.decode()[:200]
            except:
                pass
        
        log_entry = {
            "type": "http_request",
            "method": request.method,
            "path": request.url.path,
            "query_string": str(request.url.query),
            "client_ip": request.client.host if request.client else "unknown",
            "body_preview": body_preview,
            **trace_context.to_dict(),
        }
        logger.info(json.dumps(log_entry))
        
        # Process request
        response = await call_next(request)
        
        # Add trace headers to response
        response.headers["x-request-id"] = trace_context.request_id
        response.headers["x-correlation-id"] = trace_context.correlation_id
        response.headers["x-trace-id"] = trace_context.trace_id
        response.headers["x-process-time"] = str(trace_context.elapsed_ms)
        
        # Log response
        log_entry = {
            "type": "http_response",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "elapsed_ms": trace_context.elapsed_ms,
            **trace_context.to_dict(),
        }
        logger.info(json.dumps(log_entry))
        
        return response


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Legacy middleware for correlation ID propagation.
    (New code should use TraceMiddleware)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
        correlation_id_var.set(correlation_id)
        
        response = await call_next(request)
        response.headers["x-correlation-id"] = correlation_id
        
        return response
