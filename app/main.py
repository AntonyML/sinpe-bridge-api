from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
from datetime import datetime

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.middleware import TraceMiddleware, get_trace_context

# Configure structured logging
if settings.STRUCTURED_LOGGING:
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format='%(message)s',
    )

logger = logging.getLogger(__name__)

# ============================================================================
# APPLICATION SETUP
# ============================================================================

app = FastAPI(
    title="SINPE Bridge API",
    description="Valida pagos SINPE Móvil y los concilia con órdenes del POS.",
    version="1.0.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    redoc_url=None,
)

# ============================================================================
# MIDDLEWARE STACK
# ============================================================================

# 1. Trace middleware (must be first for proper context)
app.add_middleware(TraceMiddleware)

# 2. CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "x-api-key",
        "x-correlation-id",
        "x-request-id",
        "x-trace-id",
        "x-device-id",
        "x-signature",
    ],
)

# ============================================================================
# ROUTERS
# ============================================================================

app.include_router(api_router, prefix="/api/v1")

# ============================================================================
# HEALTH & READINESS ENDPOINTS
# ============================================================================

@app.get("/", tags=["Health"])
def root():
    """Root endpoint."""
    return {
        "service": "SINPE Bridge API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/ready", tags=["Health"])
def readiness():
    """Readiness check endpoint."""
    try:
        # TODO: Check database connectivity
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "reason": str(e)},
        )


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    trace_context = get_trace_context()
    
    logger.error(
        json.dumps({
            "type": "unhandled_exception",
            "error": str(exc),
            "path": request.url.path,
            "method": request.method,
            **trace_context.to_dict(),
        })
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "request_id": trace_context.request_id,
            "correlation_id": trace_context.correlation_id,
        },
    )


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    logger.info(
        json.dumps({
            "type": "startup",
            "service": "SINPE Bridge API",
            "environment": "production" if not settings.DEBUG else "development",
            "timestamp": datetime.utcnow().isoformat(),
        })
    )


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(
        json.dumps({
            "type": "shutdown",
            "service": "SINPE Bridge API",
            "timestamp": datetime.utcnow().isoformat(),
        })
    )

