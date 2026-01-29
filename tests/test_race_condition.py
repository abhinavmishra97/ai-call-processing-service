import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select
from app.main import app
from app.db.session import engine, get_db
from app.db.base import Base
from app.db.models import Call
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
import pytest_asyncio

# Setup test database
@pytest_asyncio.fixture(scope="module")
async def test_db():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_race_condition_concurrent_packets(test_db, async_client):
    """
    Test prevents race conditions when creating a new call session from simultaneous packets.
    Scenario: 
    - 2 packets for NEW call_id arrive at the exact same moment.
    - Validate that only 1 Call row is created.
    - Validate that both packets are accepted (202).
    """
    call_id = "race-test-call-001"
    
    # Prepare payloads
    payload1 = {"sequence": 1, "data": "Packet 1 Data", "timestamp": 100.0}
    payload2 = {"sequence": 2, "data": "Packet 2 Data", "timestamp": 100.1}
    
    # Execute simultaneous requests
    # asyncio.gather runs them concurrently
    response1, response2 = await asyncio.gather(
        async_client.post(f"/v1/call/stream/{call_id}", json=payload1),
        async_client.post(f"/v1/call/stream/{call_id}", json=payload2)
    )
    
    # 1. Assert Responses are Successful
    assert response1.status_code == 202
    assert response2.status_code == 202
    
    # 2. Check Database State
    async with AsyncSession(engine) as session: # Direct session for verification
        # Verify only ONE Call object exists
        result = await session.execute(select(Call).where(Call.call_id == call_id))
        calls = result.scalars().all()
        assert len(calls) == 1, f"Expected 1 call session, found {len(calls)}"
        
        call_obj = calls[0]
        
        # Verify sequence tracking (should be 2, assuming sequence 2 arrived or was processed)
        # Note: In a true race, 2 might process before 1, but max should be 2.
        assert call_obj.last_sequence == 2
        
        # Verify Total Packets
        # We need to query the Packet table to ensure we have 2 packets
        # (This requires importing Packet model, adding it to the select)
        from app.db.models import Packet
        packet_res = await session.execute(select(Packet).where(Packet.call_id == call_id))
        packets = packet_res.scalars().all()
        
        assert len(packets) == 2, f"Expected 2 packets, found {len(packets)}"
