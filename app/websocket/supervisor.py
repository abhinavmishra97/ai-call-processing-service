from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import CallSession, CallPacket
import logging
import json
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    
    # Create a new call session
    session_id = str(uuid.uuid4())
    call_session = CallSession(session_id=session_id, customer_phonenumber=client_id)
    db.add(call_session)
    await db.commit()
    await db.refresh(call_session)
    
    logger.info(f"New call session started: {session_id} for client {client_id}")

    try:
        while True:
            data = await websocket.receive_text()
            # Expecting JSON data for simulation simplicity
            try:
                packet_data = json.loads(data)
            except json.JSONDecodeError:
                packet_data = {"raw": data}
            
            # Store packet
            packet = CallPacket(
                call_session_id=call_session.id,
                packet_data=packet_data,
                packet_type=packet_data.get("type", "unknown")
            )
            db.add(packet)
            # We might not want to commit every single packet immediately in high throughput real scenarios,
            # but for this simulation, it's fine.
            await db.commit() 
            
            # Trigger background AI processing here if needed (e.g. on silence or specific interval)
            # For now, just echo state
            await websocket.send_text(f"Packet received: {packet_data.get('type', 'unknown')}")
            
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
        # Update session status
        call_session.status = "completed"
        # call_session.end_time = func.now() # handled by DB triggers or explicit update
        await db.commit()
