# app/db_engine.py
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.config import DATABASE_URL
from app.models import SQLModel

print(f"DATABASE_URL: {DATABASE_URL}")

# --- Database Engine Creation ---
async_engine = create_async_engine(
    DATABASE_URL,
    echo=True, # Set to True for debugging
    pool_recycle=1800,
)

AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# --- Table Creation (remains the same) ---
async def create_db_and_tables():
    async with async_engine.begin() as conn:
        print("Creating database tables...")
        await conn.run_sync(SQLModel.metadata.create_all)
        print("Database tables created (if they didn't exist).")
