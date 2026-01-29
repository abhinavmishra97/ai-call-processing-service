import asyncio
import random
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class AIServiceUnavailable(Exception):
    pass

class MockAIService:
    def __init__(self):
        self.failure_rate = 0.25 # 25% failure rate

    async def _simulate_network_call(self):
        """Simulate flaky network latency and failure."""
        delay = random.uniform(1.0, 3.0) # 1-3 seconds latency
        await asyncio.sleep(delay)
        
        if random.random() < self.failure_rate:
            logger.warning("Mock AI Service failed (simulating 503)")
            raise AIServiceUnavailable("Service Unavailable")

    @retry(
        retry=retry_if_exception_type(AIServiceUnavailable),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def process_call_summary(self, call_text: str) -> str:
        """
        Processes text with simulated flakiness and exponential backoff retry.
        """
        logger.info(f"AI Service: Processing {len(call_text)} chars...")
        await self._simulate_network_call()
        return f"AI Summary: Processed content successfully. [{call_text[:20]}...]"

ai_service = MockAIService()
