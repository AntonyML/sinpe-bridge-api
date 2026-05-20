from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Use SQLite for development if DATABASE_URL not provided
database_url = settings.DATABASE_URL or "sqlite+aiosqlite:///./sinpe_bridge.db"

# statement_cache_size=0 is required for Supabase
engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=0,
    pool_pre_ping=True,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
