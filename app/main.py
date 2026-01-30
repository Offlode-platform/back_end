"""
FastAPI Application Entry Point
Sentinel - Document Chasing System + AI Receptionist
"""
from contextlib import asynccontextmanager
from app.api.internal.xero_sync_debug import router as xero_sync_router
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time

from app.config import settings
from app.database import check_db_connection_async, close_db_connections_async
from app.api.internal import xero_debug

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Runs on startup and shutdown
    """
    # Startup
    print("🚀 Starting Sentinel API...")
    print(f"   Environment: {settings.environment}")
    print(f"   Debug Mode: {settings.debug}")
    print(f"   AWS Region: {settings.aws_region}")
    
    # Check database connection
    db_ok = await check_db_connection_async()
    if db_ok:
        print("✅ Database connection successful")
    else:
        print("❌ Database connection failed")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Sentinel API...")
    await close_db_connections_async()
    print("✅ Cleanup complete")




# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Document Chasing System + AI Receptionist for UK Accountants",
    docs_url=f"{settings.api_prefix}/docs" if settings.debug else None,
    redoc_url=f"{settings.api_prefix}/redoc" if settings.debug else None,
    openapi_url=f"{settings.api_prefix}/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# GZip Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted Host (Production only)
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.sentinel.com", "sentinel.com"]
    )


# Request Timing Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to all responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Organization Context Middleware
@app.middleware("http")
async def set_organization_context(request: Request, call_next):
    """
    Extract organization_id from request and set in context
    Can be from:
    - JWT token (preferred)
    - X-Organization-ID header (for service-to-service)
    - Query parameter (for magic links)
    """
    from app.database import TenantContext
    
    # Clear previous context
    TenantContext.clear()
    
    # TODO: Extract organization_id from JWT token or header
    # For now, this is a placeholder
    # org_id = extract_org_id_from_token(request)
    # if org_id:
    #     TenantContext.set_organization_id(org_id)
    
    response = await call_next(request)
    
    # Clear context after request
    TenantContext.clear()
    
    return response


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    print(f"❌ Unhandled exception: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error" if settings.is_production else str(exc),
            "type": "server_error"
        }
    )


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness check - checks dependencies"""
    from app.database import check_db_connection_async, get_pool_status
    
    db_ok = await check_db_connection_async()
    pool_status = get_pool_status()
    
    is_ready = db_ok
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content={
            "ready": is_ready,
            "checks": {
                "database": "ok" if db_ok else "failed",
            },
            "pool": pool_status
        }
    )


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """Liveness check - simple ping"""
    return {"status": "alive"}


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "message": "Sentinel API",
        "version": settings.app_version,
        "docs": f"{settings.api_prefix}/docs" if settings.debug else None,
        "environment": settings.environment,
    }


# ============================================================================
# API ROUTES
# ============================================================================

# Import all routers
from app.api.v1 import organizations, users, clients, client_assignments, audit_logs

# Organizations API
app.include_router(
    organizations.router,
    prefix=f"{settings.api_prefix}/organizations",
    tags=["Organizations"]
)

# Users API
app.include_router(
    users.router,
    prefix=f"{settings.api_prefix}/users",
    tags=["Users"]
)

# Clients API
app.include_router(
    clients.router,
    prefix=f"{settings.api_prefix}/clients",
    tags=["Clients"]
)

# Client Assignments API
app.include_router(
    client_assignments.router,
    prefix=f"{settings.api_prefix}/client-assignments",
    tags=["Client Assignments"]
)

# Audit Logs API (Read-only)
app.include_router(
    audit_logs.router,
    prefix=f"{settings.api_prefix}/audit-logs",
    tags=["Audit Logs"]
)

# TODO: Register additional API routers here
# from app.api.v1 import transactions, documents, chases
# app.include_router(transactions.router, prefix=f"{settings.api_prefix}/transactions", tags=["Transactions"])
# app.include_router(documents.router, prefix=f"{settings.api_prefix}/documents", tags=["Documents"])
# app.include_router(chases.router, prefix=f"{settings.api_prefix}/chases", tags=["Chases"])


# ============================================================================
# DEVELOPMENT HELPERS
# ============================================================================

if settings.debug:
    @app.get(f"{settings.api_prefix}/debug/config", tags=["Debug"])
    async def debug_config():
        """Show current configuration (development only)"""
        return {
            "environment": settings.environment,
            "database_pool_size": settings.database_pool_size,
            "redis_max_connections": settings.redis_max_connections,
            "cors_origins": settings.cors_origins,
            "aws_region": settings.aws_region,
        }
    
    @app.get(f"{settings.api_prefix}/debug/db-pool", tags=["Debug"])
    async def debug_db_pool():
        """Show database pool status (development only)"""
        from app.database import get_pool_status
        return get_pool_status()


# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
        log_level=settings.log_level.lower(),
    )



app.include_router(xero_debug.router)
app.include_router(xero_sync_router)