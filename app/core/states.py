from enum import Enum

class CallState(str, Enum):
    """
    Represents the lifecycle states of a call session in the system.
    
    States:
    - IN_PROGRESS: Call is currently active and ingesting packets.
    - COMPLETED: Call has finished successfully; ready for post-processing.
    - PROCESSING_AI: Call is currently being analyzed by the AI service.
    - FAILED: Call processing encountered an unrecoverable error.
    - ARCHIVED: Call analysis is complete and results are stored.
    """
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PROCESSING_AI = "PROCESSING_AI"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"
