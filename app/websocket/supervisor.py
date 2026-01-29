from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import logging
import json

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages active WebSocket connections for supervisor monitoring.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Supervisor client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("Supervisor client disconnected")

    async def broadcast_state_change(self, call_id: str, state: str, data: Dict[str, Any] = None):
        """
        Broadcasts a state change event to all connected supervisors.
        """
        message = {
            "type": "state_change",
            "call_id": call_id,
            "state": state,
            "data": data or {}
        }
        
        # Determine disconnected sockets to remove
        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client, removing: {e}")
                to_remove.append(connection)
        
        for conn in to_remove:
            self.disconnect(conn)

# Global Manager Instance
manager = ConnectionManager()

router = APIRouter()

@router.websocket("/ws/supervisor")
async def websocket_supervisor(websocket: WebSocket):
    """
    WebSocket endpoint for supervisors to listen to real-time events.
    """
    await manager.connect(websocket)
    try:
        while True:
            # We explicitly wait for messages to keep the connection open
            # Clients might send heartbeats or commands in the future
            data = await websocket.receive_text()
            # Optional: handle incoming commands if needed
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Unexpected WebSocket error: {e}")
        manager.disconnect(websocket)
