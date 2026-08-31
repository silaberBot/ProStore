"""
اتصال به دیتابیس با SQLAlchemy 2.0 Async
Database connection and session management
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """کلاس پایه برای تمام مدل‌های دیتابیس"""
    pass


# Engine و Session factory (بعد از import settings ایجاد می‌شوند)
_engine = None
_AsyncSessionLocal = None


def init_engine(database_url: str) -> None:
    """ایجاد engine دیتابیس"""
    global _engine, _AsyncSessionLocal

    connect_args = {}
    if "sqlite" in database_url:
        connect_args = {"check_same_thread": False}
        _engine = create_async_engine(
            database_url,
            echo=False,
            connect_args=connect_args,
        )
    else:
        # PostgreSQL with connection pool
        _engine = create_async_engine(
            database_url,
            pool_size=20,
            max_overflow=40,
            pool_timeout=30,
            pool_recycle=3600,
            echo=False,
        )

    _AsyncSessionLocal = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    logger.info("✅ Database engine initialized")


async def init_db() -> None:
    """ایجاد تمام جدول‌های دیتابیس"""
    if _engine is None:
        raise RuntimeError("Engine not initialized. Call init_engine() first.")

    # import تمام مدل‌ها تا در Base.metadata ثبت شوند
    import models  # noqa: F401

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("✅ All database tables created successfully")


async def close_db() -> None:
    """بستن اتصال دیتابیس"""
    if _engine is not None:
        await _engine.dispose()
        logger.info("Database connection closed")


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Context manager برای دریافت session دیتابیس"""
    if _AsyncSessionLocal is None:
        raise RuntimeError("Session factory not initialized.")
    async with _AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Generator برای dependency injection"""
    async with get_db() as session:
        yield session


async def check_db_health() -> bool:
    """بررسی سلامت اتصال دیتابیس"""
    try:
        from sqlalchemy import text
        async with get_db() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
