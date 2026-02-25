"""Database helper module for async SQLAlchemy configuration."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from bot.settings import settings


# Create async engine
engine: AsyncEngine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    future=True,
)

# Create async session factory
async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """
    Get an async database session.

    Returns:
        AsyncSession: Async SQLAlchemy session
    """
    async with async_session_maker() as session:
        yield session


async def close_engine() -> None:
    """
    Close the database engine and dispose of all connections.

    Should be called when shutting down the application.
    """
    await engine.dispose()
