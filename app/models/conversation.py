"""
Nexus Miracle - Conversation Models

Data models for call state and conversation management.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ConversationRole(str, Enum):
    """Role in the conversation."""
    
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class CallState(str, Enum):
    """State of an active call."""
    
    RINGING = "ringing"
    ANSWERED = "answered"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    TRANSFERRING = "transferring"
    ENDED = "ended"
    FAILED = "failed"


class ConversationMessage(BaseModel):
    """A single message in the conversation."""
    
    id: UUID = Field(default_factory=uuid4, description="Message ID")
    role: ConversationRole = Field(description="Message role")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Message timestamp"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    # Audio-specific fields
    audio_duration_ms: int | None = Field(
        default=None,
        description="Duration of audio in ms"
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="ASR confidence score"
    )


class ConversationSession(BaseModel):
    """
    Complete conversation session for a phone call.
    
    Tracks the full state of an AI-assisted phone conversation.
    """
    
    # Identifiers
    id: UUID = Field(default_factory=uuid4, description="Session ID")
    call_control_id: str = Field(description="Telnyx call control ID")
    
    # Call metadata
    caller_phone: str = Field(description="Caller's phone number")
    called_phone: str = Field(description="Called phone number")
    
    # State
    state: CallState = Field(
        default=CallState.RINGING,
        description="Current call state"
    )
    
    # Timestamps
    started_at: datetime = Field(
        default_factory=datetime.now,
        description="Call start time"
    )
    answered_at: datetime | None = Field(
        default=None,
        description="Call answer time"
    )
    ended_at: datetime | None = Field(
        default=None,
        description="Call end time"
    )
    
    # Conversation
    messages: list[ConversationMessage] = Field(
        default_factory=list,
        description="Conversation history"
    )
    system_prompt: str = Field(
        default="",
        description="System prompt for LLM"
    )
    
    # Active voice
    active_voice: str = Field(
        default="sara",
        description="Currently active voice (sara or nexus)"
    )
    
    # Context and state
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted conversation context"
    )
    intent: str | None = Field(
        default=None,
        description="Current detected intent"
    )
    
    # Performance metrics
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Performance metrics"
    )
    
    @property
    def duration_seconds(self) -> float | None:
        """Calculate call duration in seconds."""
        if self.answered_at is None:
            return None
        
        end = self.ended_at or datetime.now()
        return (end - self.answered_at).total_seconds()
    
    @property
    def message_count(self) -> int:
        """Get total message count."""
        return len(self.messages)
    
    def add_message(
        self,
        role: ConversationRole,
        content: str,
        **kwargs: Any,
    ) -> ConversationMessage:
        """
        Add a message to the conversation.
        
        Args:
            role: Message role
            content: Message content
            **kwargs: Additional message fields
        
        Returns:
            Created message
        """
        message = ConversationMessage(
            role=role,
            content=content,
            **kwargs,
        )
        self.messages.append(message)
        return message
    
    def get_conversation_for_llm(self) -> list[dict[str, str]]:
        """
        Get conversation history formatted for LLM API.
        
        Returns:
            List of message dicts with role and content
        """
        result = []
        
        if self.system_prompt:
            result.append({
                "role": "system",
                "content": self.system_prompt,
            })
        
        for msg in self.messages:
            result.append({
                "role": msg.role.value,
                "content": msg.content,
            })
        
        return result
    
    def update_state(self, new_state: CallState) -> None:
        """
        Update call state with timestamp handling.
        
        Args:
            new_state: New call state
        """
        if new_state == CallState.ANSWERED and self.answered_at is None:
            self.answered_at = datetime.now()
        elif new_state == CallState.ENDED and self.ended_at is None:
            self.ended_at = datetime.now()
        
        self.state = new_state
