from psycopg_pool import AsyncConnectionPool

from core.config import settings

# Global connection pool
pool = AsyncConnectionPool(conninfo=settings.database_url, open=False)
