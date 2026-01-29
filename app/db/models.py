from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.states import CallState

class Call(Base):
    """
    Represents a phone call lifecycle.
    """
    __tablename__ = "calls"

    # Primary key: call_id (string)
    call_id = Column(String, primary_key=True, index=True)
    
    # State field using the CallState enum
    status = Column(SQLAlchemyEnum(CallState), default=CallState.IN_PROGRESS, nullable=False)
    
    # last_sequence integer field to track packet order
    last_sequence = Column(Integer, default=0, nullable=False)
    
    # Optional transcript and sentiment fields (AI results)
    transcript = Column(Text, nullable=True)
    sentiment = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    packets = relationship("Packet", back_populates="call", cascade="all, delete-orphan")


class Packet(Base):
    """
    Represents streamed chunks of call data.
    """
    __tablename__ = "packets"

    # Auto-increment primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to call_id, Indexed
    call_id = Column(String, ForeignKey("calls.call_id"), nullable=False, index=True)
    
    # sequence, data, timestamp fields
    sequence = Column(Integer, nullable=False)
    data = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=False)

    # Relationships
    call = relationship("Call", back_populates="packets")
