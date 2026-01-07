"""
Nexus Miracle - Application Configuration

Pydantic-settings based configuration with environment variable validation.
All settings are loaded from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Use get_settings() to access the singleton instance.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ===========================================
    # Application Settings
    # ===========================================
    app_name: str = Field(default="Nexus Miracle", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )
    debug: bool = Field(default=True, description="Debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="DEBUG",
        description="Logging level"
    )
    
    # ===========================================
    # Server Configuration
    # ===========================================
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    
    # ===========================================
    # Database Configuration
    # ===========================================
    database_url: str = Field(
        default="sqlite+aiosqlite:///data/nexus.db",
        description="Database connection URL"
    )
    database_echo: bool = Field(
        default=False,
        description="Echo SQL statements for debugging"
    )
    timezone: str = Field(
        default="Asia/Riyadh",
        description="Application timezone"
    )
    
    # ===========================================
    # Telnyx Configuration
    # ===========================================
    telnyx_api_key: str = Field(default="", description="Telnyx API key")
    telnyx_api_secret: str = Field(default="", description="Telnyx API secret")
    telnyx_connection_id: str = Field(default="", description="Telnyx connection ID")
    telnyx_phone_number: str = Field(default="", description="Telnyx phone number")
    telnyx_webhook_url: str = Field(default="", description="Telnyx webhook URL")
    webhook_base_url: str = Field(
        default="",
        description="Base URL for webhooks (e.g., https://your-app.railway.app)"
    )
    
    # ===========================================
    # ElevenLabs Configuration
    # ===========================================
    elevenlabs_api_key: str = Field(default="", description="ElevenLabs API key")
    elevenlabs_voice_sara: str = Field(default="", description="Sara voice ID")
    elevenlabs_voice_nexus: str = Field(default="", description="Nexus voice ID")
    elevenlabs_model: str = Field(
        default="eleven_flash_v2_5",
        description="ElevenLabs TTS model"
    )
    elevenlabs_stability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Voice stability"
    )
    elevenlabs_similarity_boost: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Voice similarity boost"
    )
    
    # ===========================================
    # Google Gemini Configuration
    # ===========================================
    google_api_key: str = Field(default="", description="Google API key")
    gemini_model: str = Field(
        default="gemini-3.0-flash",
        description="Gemini model name"
    )
    system_prompt: str = Field(
        default="""أنتِ سارة، موظفة استقبال ذكية في عيادة نِكسوس مراكل الطبية.
مهمتك مساعدة المرضى في حجز المواعيد والاستفسارات الطبية.
تحدثي بأسلوب مهني وودود باللغة العربية.""",
        description="System prompt for AI assistant"
    )
    
    # ===========================================
    # Audio Processing Settings
    # ===========================================
    audio_sample_rate: int = Field(
        default=16000,
        description="Audio sample rate in Hz"
    )
    audio_channels: int = Field(default=1, ge=1, le=2, description="Audio channels")
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
        description="Minimum silence duration in ms"
    )
    
    # ===========================================
    # Performance Settings
    # ===========================================
    max_concurrent_calls: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum concurrent calls"
    )
    response_timeout_ms: int = Field(
        default=800,
        ge=100,
        le=5000,
        description="Response timeout in ms"
    )
    
    @field_validator("log_level", mode="before")
    @classmethod
    def uppercase_log_level(cls, v: str) -> str:
        """Ensure log level is uppercase."""
        return v.upper() if isinstance(v, str) else v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance (singleton pattern).
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()
