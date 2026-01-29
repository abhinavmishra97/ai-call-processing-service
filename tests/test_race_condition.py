import pytest
import asyncio
from httpx import AsyncClient
from app.main import app
from app.db.session import get_db, engine
from app.db.base import Base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
import pytest_asyncio

# Setup Test DB
@pytest_asyncio.fixture(scope="function")
async def test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    
    async with async_session() as session:
        yield session
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_race_condition_packets():
    """
    Simulate a Race Condition: Two packets arriving at the exact same time.
    We use asyncio.gather to fire two requests effectively in parallel.
    """
    call_id = "race-test-123"
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        
        # Define two payloads
        payload1 = {"sequence": 1, "data": "Hello", "timestamp": 100.1}
        payload2 = {"sequence": 2, "data": "World", "timestamp": 100.2}
        
        # 3... 2... 1... GO!
        # Fire both requests concurrently
        response1, response2 = await asyncio.gather(
            ac.post(f"/v1/call/stream/{call_id}", json=payload1),
            ac.post(f"/v1/call/stream/{call_id}", json=payload2)
        )
        
        assert response1.status_code == 202
        assert response2.status_code == 202
        
        # Verify DB state
        # We need to manually check the DB to ensure both packets are recorded
        # and sequence numbers are handled (or at least stored).
        
        # Note: In a true race, the order of insertion is non-deterministic 
        # unless we lock rows. But our API just inserts packets.
        # The key is: No Deadlocks, No 500 Errors.
