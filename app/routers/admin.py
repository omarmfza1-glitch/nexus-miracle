"""
Nexus Miracle - Admin Router

Dashboard settings and administrative endpoints.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from app.config import get_settings

router = APIRouter()


# ===========================================
# Request/Response Models
# ===========================================

class VoiceSettings(BaseModel):
    """Voice configuration settings."""
    
    primary_voice: str = Field(description="Primary voice ID (Sara)")
    secondary_voice: str = Field(description="Secondary voice ID (Nexus)")
    stability: float = Field(ge=0.0, le=1.0, description="Voice stability")
    similarity_boost: float = Field(ge=0.0, le=1.0, description="Similarity boost")


class SystemSettings(BaseModel):
    """System configuration settings."""
    
    max_concurrent_calls: int = Field(ge=1, le=1000)
    response_timeout_ms: int = Field(ge=100, le=5000)
    vad_threshold: float = Field(ge=0.0, le=1.0)
    vad_min_silence_ms: int = Field(ge=100, le=5000)


class SettingsResponse(BaseModel):
    """Combined settings response."""
    
    voice: VoiceSettings
    system: SystemSettings
    environment: str


class UpdateSettingsRequest(BaseModel):
    """Request to update settings."""
    
    voice: VoiceSettings | None = None
    system: SystemSettings | None = None


# ===========================================
# Endpoints
# ===========================================

@router.get(
    "/settings",
    response_model=SettingsResponse,
    summary="Get Settings",
    description="Retrieves current admin settings.",
)
async def get_admin_settings() -> dict[str, Any]:
    """
    Get current admin settings.
    
    Returns:
        Current voice and system settings.
    """
    settings = get_settings()
    
    return {
        "voice": {
            "primary_voice": settings.elevenlabs_voice_sara,
            "secondary_voice": settings.elevenlabs_voice_nexus,
            "stability": settings.elevenlabs_stability,
            "similarity_boost": settings.elevenlabs_similarity_boost,
        },
        "system": {
            "max_concurrent_calls": settings.max_concurrent_calls,
            "response_timeout_ms": settings.response_timeout_ms,
            "vad_threshold": settings.vad_threshold,
            "vad_min_silence_ms": settings.vad_min_silence_ms,
        },
        "environment": settings.app_env,
    }


@router.put(
    "/settings",
    response_model=SettingsResponse,
    summary="Update Settings",
    description="Updates admin settings. Changes take effect immediately.",
)
async def update_admin_settings(
    request: UpdateSettingsRequest,
) -> dict[str, Any]:
    """
    Update admin settings.
    
    Note: In production, settings would be persisted to a database.
    Currently returns placeholder response.
    
    Args:
        request: Settings update request
    
    Returns:
        Updated settings
    """
    logger.info(f"Updating settings: {request.model_dump_json()}")
    
    # TODO: Persist settings to database
    # TODO: Notify services of setting changes
    
    settings = get_settings()
    
    return {
        "voice": {
            "primary_voice": request.voice.primary_voice if request.voice else settings.elevenlabs_voice_sara,
            "secondary_voice": request.voice.secondary_voice if request.voice else settings.elevenlabs_voice_nexus,
            "stability": request.voice.stability if request.voice else settings.elevenlabs_stability,
            "similarity_boost": request.voice.similarity_boost if request.voice else settings.elevenlabs_similarity_boost,
        },
        "system": {
            "max_concurrent_calls": request.system.max_concurrent_calls if request.system else settings.max_concurrent_calls,
            "response_timeout_ms": request.system.response_timeout_ms if request.system else settings.response_timeout_ms,
            "vad_threshold": request.system.vad_threshold if request.system else settings.vad_threshold,
            "vad_min_silence_ms": request.system.vad_min_silence_ms if request.system else settings.vad_min_silence_ms,
        },
        "environment": settings.app_env,
    }


@router.get(
    "/stats",
    summary="Get System Statistics",
    description="Returns system performance statistics.",
)
async def get_system_stats() -> dict[str, Any]:
    """
    Get system performance statistics.
    
    Returns:
        Performance metrics including call counts, latencies, etc.
    """
    # TODO: Implement actual metrics collection
    return {
        "calls": {
            "total_today": 0,
            "active": 0,
            "average_duration_seconds": 0,
        },
        "performance": {
            "average_latency_ms": 0,
            "p95_latency_ms": 0,
            "p99_latency_ms": 0,
        },
        "services": {
            "asr_healthy": True,
            "llm_healthy": True,
            "tts_healthy": True,
            "vad_healthy": True,
        },
    }


@router.get(
    "",
    summary="Admin Dashboard",
    description="Returns admin dashboard data.",
)
async def get_admin_dashboard() -> dict[str, Any]:
    """
    Get admin dashboard overview.
    
    Returns:
        Dashboard data including status and quick stats.
    """
    settings = get_settings()
    
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.app_env,
        "quick_stats": {
            "active_calls": 0,
            "calls_today": 0,
            "average_satisfaction": 0.0,
        },
    }
