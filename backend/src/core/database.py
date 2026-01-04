from psycopg_pool import AsyncConnectionPool

from src.core.config import settings

# Global connection pool
pool = AsyncConnectionPool(conninfo=settings.database_url, open=False)
