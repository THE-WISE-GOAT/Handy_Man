import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

# Production URL uses the +asyncpg driver for async operations
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:password@localhost:5432/handyman_db"
)

# Engine manages a high-performance concurrent pool of connections
engine = create_async_engine(DATABASE_URL, echo=True)

# Session factory for route-level transactions
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Request lifecycle dependency to avoid memory leaks
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()