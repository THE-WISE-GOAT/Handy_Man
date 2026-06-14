import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Fallback updated to target your Handy Man database name
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:password@localhost:5432/handy_man_db"
)

# 1. Create the Asynchronous Database Engine
engine = create_async_engine(DATABASE_URL, echo=True)

# 2. Modern Session Factory optimized for async execution loops
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 3. Modern Declarative Base Class required for Mapped[...] columns to resolve types properly
class Base(DeclarativeBase):
    pass

# 4. Dependency Injection Provider for FastAPI routes
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # The context manager ('async with') handles closing automatically, 
            # but explicit closing provides an extra layer of protection against connection leaks.
            await session.close()