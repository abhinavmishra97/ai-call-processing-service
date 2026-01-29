import logging
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_log, after_log
from sqlalchemy.future import select
from app.services.mock_ai import ai_service, AIServiceUnavailable
from app.db.models import Call
from app.core.states import CallState
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

class AIProcessor:
    """
    Handles buffering and processing of call data with robust retries.
    """
    
    @retry(
        retry=retry_if_exception_type(AIServiceUnavailable),
        stop=stop_after_attempt(5),  # Limit max retries to 5
        wait=wait_exponential(multiplier=1, min=2, max=60), # 2^n logic: 2s, 4s, 8s...
        before=before_log(logger, logging.INFO),
        after=after_log(logger, logging.WARNING),
        reraise=True # Let the exception bubble up if max retries reached so we can handle failure state
    )
    async def _call_ai_service_with_retry(self, text: str):
        return await ai_service.transcribe(text)

    async def process_call_background(self, call_id: str):
        """
        Background task to process the call content.
        Fetches call packets (mock logic), sends to AI, and updates DB.
        """
        async with AsyncSessionLocal() as session:
            try:
                # 1. Fetch Call
                result = await session.execute(select(Call).where(Call.call_id == call_id))
                call = result.scalars().first()
                if not call:
                    logger.error(f"Call {call_id} not found for processing")
                    return

                # Transition State: PROCESSING_AI
                call.status = CallState.PROCESSING_AI
                await session.commit()
                
                # 2. Simulate aggregating packet data
                # In a real app, you'd fetch all packets from the DB
                # query = select(Packet).where(Packet.call_id == call_id).order_by(Packet.sequence)
                # packets = (await session.execute(query)).scalars().all()
                # full_text = "".join([p.data for p in packets])
                
                # Mock aggregation for now since we are just testing the processing flow
                full_text = "Simulated aggregated call content for analysis."

                # 3. Call AI Service with Retry
                ai_result = await self._call_ai_service_with_retry(full_text)
                
                # 4. Success: Update Call with result and COMPLETE/ARCHIVE
                call.transcript = ai_result["transcript"]
                call.sentiment = ai_result["sentiment"]
                call.status = CallState.ARCHIVED # Or COMPLETED, per requirement
                
                logger.info(f"Successfully processed call {call_id}")
                
            except AIServiceUnavailable:
                logger.error(f"Failed to process call {call_id} after retries")
                call.status = CallState.FAILED
            
            except Exception as e:
                logger.exception(f"Unexpected error processing call {call_id}: {e}")
                call.status = CallState.FAILED
            
            finally:
                await session.commit()

# Singleton
ai_processor = AIProcessor()
