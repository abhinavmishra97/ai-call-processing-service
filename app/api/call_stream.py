from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from app.db.models import Call, Packet
from app.core.states import CallState
from app.services.processor import ai_processor
from typing import Optional
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
    """
    Ingests a single packet of call data.
    """
    # 1. Check/Create Session
    # Optimization: Try to get it first
    result = await db.execute(select(Call).where(Call.call_id == call_id))
    call = result.scalars().first()
    
    if not call:
        try:
            call = Call(call_id=call_id, status=CallState.IN_PROGRESS)
            db.add(call)
            await db.commit()
            await db.refresh(call)
        except IntegrityError:
            # Race condition: Another request created it just now
            logger.warning(f">>> RACE CONDITION CAUGHT! handling concurrency for {call_id} <<<")
            await db.rollback()
            result = await db.execute(select(Call).where(Call.call_id == call_id))
            call = result.scalars().first()
            if not call:
                # Should practically never happen unless deleted immediately
                raise HTTPException(status_code=500, detail="Concurrency Error: Could not fetch call after uniqueness failure")
    
    # 2. Validation (Non-blocking warning)
    expected_sequence = call.last_sequence + 1
    if payload.sequence != expected_sequence:
         logger.warning(f"Packet Sequence Mismatch for {call_id}: Expected {expected_sequence}, Got {payload.sequence}")
    
    # 3. Store Packet
    packet = Packet(
        call_id=call.call_id,
        sequence=payload.sequence,
        data=payload.data,
        timestamp=payload.timestamp
    )
    db.add(packet)
    
    # Update sequence tracking
    if payload.sequence > call.last_sequence:
        call.last_sequence = payload.sequence
        
    await db.commit()
    
    return {"status": "accepted"}

@router.post("/call/{call_id}/end", status_code=status.HTTP_200_OK)
async def end_call(
    call_id: str, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Marks a call as COMPLETED and triggers background AI processing.
    """
    result = await db.execute(select(Call).where(Call.call_id == call_id))
    call = result.scalars().first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
        
    if call.status in [CallState.COMPLETED, CallState.ARCHIVED, CallState.FAILED]:
        return {"status": "already_completed", "state": call.status}

    # Transition: IN_PROGRESS -> COMPLETED
    call.status = CallState.COMPLETED
    await db.commit()
    
    # Trigger Background AI Processing
    # We pass the ID, not the object, to avoid async session attachment issues in the background task
    background_tasks.add_task(ai_processor.process_call_background, call_id)
    
    return {"status": "processing_initiated", "call_id": call_id}
