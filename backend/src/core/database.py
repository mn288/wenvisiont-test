from psycopg_pool import AsyncConnectionPool

# SQLModel / SQLAlchemy Async Engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import settings

# Make sure the URL is asyncpg compatible (e.g. postgresql+asyncpg://)
# If settings.database_url is postgres://, we might need to patch it, but usually standard lib handles it.
# We'll assume settings.database_url is correct or patch it if needed.
# For async sqlalchemy, the driver is usually part of the URL.
# Global connection pool (Legacy raw usage)
pool = AsyncConnectionPool(conninfo=settings.database_url, open=False)
database_url = settings.database_url.replace("postgresql://", "postgresql+psycopg://")

engine = create_async_engine(database_url, echo=False, future=True)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
