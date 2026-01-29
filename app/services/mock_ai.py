import asyncio
import random
import logging

logger = logging.getLogger(__name__)

class AIServiceUnavailable(Exception):
    """Raised when the AI service is simulated to be down."""
    pass

class MockAIService:
    def __init__(self):
        self.failure_rate = 0.25 # 25% failure probability

    async def transcribe(self, audio_data: str) -> dict:
        """
        Simulates transcribing audio data.
        
        Args:
            audio_data: The input string (mocking audio bytes or reference).
            
        Returns:
            dict: { "transcript": str, "sentiment": str }
            
        Raises:
            AIServiceUnavailable: If the service simulation fails (25% chance).
        """
        # Simulate variable latency (1-3 seconds)
        latency = random.uniform(1.0, 3.0)
        logger.info(f"Mock AI processing started. Latency: {latency:.2f}s")
        await asyncio.sleep(latency)

        # Simulate random failure
        if random.random() < self.failure_rate:
            logger.error("Mock AI simulation failed (random 25%)")
            raise AIServiceUnavailable("AI Service temporarily unavailable")

        # Return fake success result
        return {
            "transcript": "This is a simulated transcription of the call segment.",
            "sentiment": random.choice(["positive", "neutral", "negative"])
        }

# Singleton instance
ai_service = MockAIService()
