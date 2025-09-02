from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from app.config import settings

DATABASE_URL = settings.database_url

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,  # set True while debugging
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

Base = declarative_base()


# Dependency for FastAPI
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
