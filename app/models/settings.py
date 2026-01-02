"""
Nexus Miracle - Settings Models

Data models for admin and system settings.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class VoiceSettings(BaseModel):
    """Voice configuration settings for TTS."""
    
    # Voice IDs
    primary_voice_id: str = Field(
        description="Primary voice ID (Sara - Arabic female)"
    )
    secondary_voice_id: str = Field(
        description="Secondary voice ID (Nexus - Arabic male)"
    )
    
    # Voice parameters
    model: str = Field(
        default="eleven_flash_v2_5",
        description="ElevenLabs TTS model"
    )
    stability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Voice stability (0-1)"
    )
    similarity_boost: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Voice similarity boost (0-1)"
    )
    style: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Voice style exaggeration (0-1)"
    )
    use_speaker_boost: bool = Field(
        default=True,
        description="Enable speaker boost"
    )


class SystemSettings(BaseModel):
    """System performance and behavior settings."""
    
    # Call handling
    max_concurrent_calls: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum concurrent calls"
    )
    call_timeout_seconds: int = Field(
        default=1800,  # 30 minutes
        ge=60,
        le=7200,
        description="Maximum call duration"
    )
    
    # Response timing
    response_timeout_ms: int = Field(
        default=800,
        ge=100,
        le=5000,
        description="Target response latency"
    )
    
    # VAD settings
    vad_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="VAD confidence threshold"
    )
    vad_min_silence_ms: int = Field(
        default=500,
        ge=100,
        le=5000,
        description="Minimum silence for end of speech"
    )
    vad_min_speech_ms: int = Field(
        default=250,
        ge=50,
        le=2000,
        description="Minimum speech duration to process"
    )
    
    # Audio settings
    audio_sample_rate: int = Field(
        default=16000,
        description="Audio sample rate in Hz"
    )
    audio_chunk_ms: int = Field(
        default=20,
        ge=10,
        le=100,
        description="Audio chunk size in ms"
    )


class LLMSettings(BaseModel):
    """LLM configuration settings."""
    
    model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model name"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Generation temperature"
    )
    max_tokens: int = Field(
        default=500,
        ge=1,
        le=8192,
        description="Maximum response tokens"
    )
    top_p: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Top-p sampling"
    )


class GreetingSettings(BaseModel):
    """Greeting and prompt settings."""
    
    # Initial greeting
    greeting_arabic: str = Field(
        default="مرحباً بك في نيكسوس ميراكل. كيف يمكنني مساعدتك اليوم؟",
        description="Arabic greeting message"
    )
    greeting_english: str = Field(
        default="Welcome to Nexus Miracle. How can I help you today?",
        description="English greeting message"
    )
    
    # System prompt
    system_prompt: str = Field(
        default=(
            "You are a helpful medical assistant at Nexus Miracle healthcare center "
            "in Saudi Arabia. You help patients book appointments, answer general "
            "health questions, and provide information about our services. "
            "Be professional, empathetic, and concise. Respond in the same language "
            "the patient uses (Arabic or English)."
        ),
        description="System prompt for LLM"
    )


class AdminSettings(BaseModel):
    """
    Complete admin settings combining all configuration categories.
    
    Used for persisting and retrieving admin-configurable settings.
    """
    
    id: UUID = Field(default_factory=uuid4, description="Settings ID")
    
    # Settings categories
    voice: VoiceSettings = Field(
        default_factory=VoiceSettings,
        description="Voice settings"
    )
    system: SystemSettings = Field(
        default_factory=SystemSettings,
        description="System settings"
    )
    llm: LLMSettings = Field(
        default_factory=LLMSettings,
        description="LLM settings"
    )
    greeting: GreetingSettings = Field(
        default_factory=GreetingSettings,
        description="Greeting settings"
    )
    
    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp"
    )
    updated_by: str | None = Field(
        default=None,
        description="Last updater identifier"
    )
    
    # Feature flags
    features: dict[str, bool] = Field(
        default_factory=lambda: {
            "dual_voice": True,
            "language_detection": True,
            "appointment_booking": True,
            "call_recording": False,
            "sentiment_analysis": False,
        },
        description="Feature flags"
    )
    
    def update(self, updates: dict[str, Any], updated_by: str | None = None) -> None:
        """
        Apply partial updates to settings.
        
        Args:
            updates: Dictionary of updates to apply
            updated_by: Identifier of who made the update
        """
        for key, value in updates.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        
        self.updated_at = datetime.now()
        self.updated_by = updated_by
