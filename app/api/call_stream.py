from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import CallSession, CallPacket
from app.core.states import CallState
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class PacketPayload(BaseModel):
    sequence: int
    data: str
    timestamp: float

@router.post("/call/stream/{call_id}", status_code=status.HTTP_202_ACCEPTED)
async def ingest_packet(
    call_id: str, 
    payload: PacketPayload, 
    db: AsyncSession = Depends(get_db)
):
    # Non-blocking check for session existence
    # Note: For extreme high performance, might use Redis here to avoid DB hit every packet.
    # For this simulation, we check DB.
    
    result = await db.execute(select(CallSession).where(CallSession.session_id == call_id))
    session = result.scalars().first()
    
    if not session:
        # Create on fly if first packet? Or 404? 
        # Usually stream starts with a setup call, but let's auto-create for simplicity of the prompt
        session = CallSession(session_id=call_id, status=CallState.IN_PROGRESS)
        db.add(session)
        await db.commit()
        await db.refresh(session)
    
    # "Twist": Validate Order
    expected_sequence = session.last_sequence_id + 1
    if payload.sequence != expected_sequence:
         # Log warning, but do NOT block (we still accept it)
         # In a real system we might buffer out-of-order packets.
         # Requirement says: "Log warning, but do not block... return 202"
         logger.warning(f"Packet Sequence Mismatch for {call_id}: Expected {expected_sequence}, Got {payload.sequence}")
         
         # Logic decision: Do we update last_sequence_id? 
         # If we receive 5 then 4, we shouldn't set last=5 then last=4.
         # For simplicity, we track the max sequence or just the last received.
         # Let's assume we just log it as the requirement only highlights logging.
    
    # Store Packet
    packet = CallPacket(
        call_session_id=session.id,
        sequence_id=payload.sequence,
        packet_data=payload.data
    )
    db.add(packet)
    
    # Update state if needed
    if payload.sequence > session.last_sequence_id:
        session.last_sequence_id = payload.sequence
        
    await db.commit()
    
    return {"status": "accepted"}

@router.post("/call/{call_id}/end", status_code=status.HTTP_200_OK)
async def result(
    call_id: str, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CallSession).where(CallSession.session_id == call_id))
    session = result.scalars().first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Call not found")
        
    # Transition: IN_PROGRESS -> COMPLETED -> UP NEXT: PROCESSING_AI
    session.status = CallState.COMPLETED
    await db.commit()
    
    # Trigger Background AI Processing
    background_tasks.add_task(process_call_ai, session.id, db)
    
    return {"status": "processing_initiated"}

from app.services.mock_ai import ai_service, AIServiceUnavailable

async def process_call_ai(session_id: int, db: AsyncSession):
    # Need a new DB session for background task usually, 
    # but here we might need to handle dependency injection manually or use a scoped session factory.
    # The 'db' passed from endpoint closes after request. 
    # We should instantiate a new session here. 
    
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        call = await session.get(CallSession, session_id)
        if not call:
            return
            
        call.status = CallState.PROCESSING_AI
        await session.commit()
        
        # Fetch all packets
        # In real world, use a more efficient query or vector DB
        stmt = select(CallPacket).where(CallPacket.call_session_id == call.id).order_by(CallPacket.sequence_id)
        result = await session.execute(stmt)
        packets = result.scalars().all()
        
        full_text = " ".join([p.packet_data for p in packets])
        
        try:
            summary = await ai_service.process_call_summary(full_text)
            
            # Save Result
            from app.db.models import AnalysisResult
            analysis = AnalysisResult(call_session_id=call.id, content=summary)
            session.add(analysis)
            call.status = CallState.ARCHIVED # Success + Done
            
        except Exception as e:
            logger.error(f"AI Processing Failed after retries: {e}")
            call.status = CallState.FAILED
            
        await session.commit()
