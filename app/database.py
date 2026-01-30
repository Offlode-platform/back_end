"""
Database Configuration
SQLAlchemy setup with connection pooling and multi-tenant support
"""
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator
from uuid import UUID

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.config import settings

# Base class for models
Base = declarative_base()

# Synchronous Engine (for migrations)
sync_engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_recycle=settings.database_pool_recycle,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.debug,
)

# Async Engine (for FastAPI)
async_database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
async_engine = create_async_engine(
    async_database_url,
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_recycle=settings.database_pool_recycle,
    pool_pre_ping=True,
    echo=settings.debug,
)

# Session factories
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
    expire_on_commit=False,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Multi-tenant context variable
class TenantContext:
    """Thread-local storage for current organization_id"""
    _organization_id: UUID | None = None

    @classmethod
    def set_organization_id(cls, organization_id: UUID | None):
        """Set current organization ID"""
        cls._organization_id = organization_id

    @classmethod
    def get_organization_id(cls) -> UUID | None:
        """Get current organization ID"""
        return cls._organization_id

    @classmethod
    def clear(cls):
        """Clear organization context"""
        cls._organization_id = None


# Row-Level Security (RLS) Setup
@event.listens_for(sync_engine, "connect")
def set_postgresql_search_path(dbapi_conn, connection_record):
    """Set PostgreSQL search path and RLS context on connection"""
    cursor = dbapi_conn.cursor()
    # Set search path to public schema
    cursor.execute("SET search_path TO public")
    cursor.close()


def set_tenant_context(session: Session, organization_id: UUID):
    """Set PostgreSQL session variable for Row-Level Security"""
    session.execute(
        text("SET LOCAL app.current_organization_id = :org_id"),
        {"org_id": str(organization_id)}
    )


async def set_tenant_context_async(session: AsyncSession, organization_id: UUID):
    """Set PostgreSQL session variable for Row-Level Security (async)"""
    await session.execute(
        text("SET LOCAL app.current_organization_id = :org_id"),
        {"org_id": str(organization_id)}
    )


# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI routes (synchronous)
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        # Set tenant context if available
        org_id = TenantContext.get_organization_id()
        if org_id:
            set_tenant_context(db, org_id)
        yield db
    finally:
        db.close()


async def get_db_async() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes (asynchronous)
    Usage: db: AsyncSession = Depends(get_db_async)
    """
    async with AsyncSessionLocal() as session:
        try:
            # Set tenant context if available
            org_id = TenantContext.get_organization_id()
            if org_id:
                await set_tenant_context_async(session, org_id)
            yield session
        finally:
            await session.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions (synchronous)
    Usage: with get_db_context() as db: ...
    """
    db = SessionLocal()
    try:
        org_id = TenantContext.get_organization_id()
        if org_id:
            set_tenant_context(db, org_id)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_db_context_async() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions (asynchronous)
    Usage: async with get_db_context_async() as db: ...
    """
    async with AsyncSessionLocal() as session:
        try:
            org_id = TenantContext.get_organization_id()
            if org_id:
                await set_tenant_context_async(session, org_id)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Database initialization
def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=sync_engine)


async def init_db_async():
    """Initialize database - create all tables (async)"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Database health check
def check_db_connection() -> bool:
    """Check if database connection is working"""
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_db_connection_async() -> bool:
    """Check if database connection is working (async)"""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# Connection pool monitoring
def get_pool_status() -> dict:
    """Get connection pool status for monitoring"""
    pool = sync_engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "max_overflow": settings.database_max_overflow,
    }


# Cleanup on shutdown
def close_db_connections():
    """Close all database connections"""
    sync_engine.dispose()


async def close_db_connections_async():
    """Close all database connections (async)"""
    await async_engine.dispose()
