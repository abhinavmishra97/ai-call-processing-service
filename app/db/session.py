from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Handling SQLite specific args
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
    connect_args=connect_args
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
