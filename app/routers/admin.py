"""
Nexus Miracle - Admin Router

Dashboard settings and administrative endpoints.
"""

from datetime import datetime
from pathlib import Path
from typing import Any
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import CallLog, FillerPhrase
from app.services.db_service import get_db

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


# Filler Phrase Models
class FillerPhraseCreate(BaseModel):
    """Create filler phrase request."""
    text: str = Field(min_length=1, max_length=500)
    category: str = Field(min_length=1, max_length=50)
    speaker: str = Field(default="سارة")


class FillerPhraseResponse(BaseModel):
    """Filler phrase response."""
    id: int
    text: str
    category: str
    speaker: str
    audio_url: str | None = None
    
    model_config = {"from_attributes": True}


# Call Log Models
class CallLogResponse(BaseModel):
    """Call log response."""
    id: int
    phone: str
    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: int | None = None
    status: str
    
    model_config = {"from_attributes": True}


class CallLogListResponse(BaseModel):
    """Paginated call logs response."""
    items: list[CallLogResponse]
    total: int
    page: int
    per_page: int
    pages: int


# Voice Config Models
class VoiceConfigItem(BaseModel):
    """Individual voice configuration."""
    voice_id: str
    stability: float = Field(ge=0.0, le=1.0)
    similarity_boost: float = Field(ge=0.0, le=1.0)
    style: float = Field(ge=0.0, le=1.0)
    speed: float = Field(ge=0.5, le=2.0)


class VoicesConfigResponse(BaseModel):
    """Voice settings for both personas."""
    sara: VoiceConfigItem
    nexus: VoiceConfigItem


# Prompt Models
class PromptResponse(BaseModel):
    """System prompt response."""
    prompt: str
    variables: list[dict[str, str]]


class PromptUpdateRequest(BaseModel):
    """Update system prompt request."""
    prompt: str


# Environment Models
class EnvironmentResponse(BaseModel):
    """Environment settings response."""
    telnyx_api_key: str = ""
    telnyx_connection_id: str
    telnyx_phone_number: str
    elevenlabs_api_key: str = ""
    elevenlabs_voice_sara: str
    elevenlabs_voice_nexus: str
    google_api_key: str = ""
    vad_silence_threshold: int
    filler_delay: int
    max_conversation_turns: int
    barge_in_enabled: bool
    debug_mode: bool
    call_recording: bool


# ===========================================
# Existing Endpoints
# ===========================================

@router.get(
    "/settings",
    response_model=SettingsResponse,
    summary="Get Settings",
    description="Retrieves current admin settings.",
)
async def get_admin_settings() -> dict[str, Any]:
    """Get current admin settings."""
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
    """Update admin settings."""
    logger.info(f"Updating settings: {request.model_dump_json()}")
    
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
    """Get system performance statistics."""
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
    """Get admin dashboard overview."""
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


# ===========================================
# Filler Phrases Endpoints
# ===========================================

@router.get(
    "/fillers",
    response_model=list[FillerPhraseResponse],
    summary="Get Filler Phrases",
    description="Returns all active filler phrases.",
)
async def get_fillers(
    session: AsyncSession = Depends(get_db),
) -> list[FillerPhrase]:
    """Get all active filler phrases."""
    result = await session.execute(
        select(FillerPhrase)
        .where(FillerPhrase.is_active == True)
        .order_by(FillerPhrase.category, FillerPhrase.id)
    )
    return list(result.scalars().all())


@router.post(
    "/fillers",
    response_model=FillerPhraseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Filler Phrase",
    description="Creates a new filler phrase.",
)
async def create_filler(
    request: FillerPhraseCreate,
    session: AsyncSession = Depends(get_db),
) -> FillerPhrase:
    """Create a new filler phrase."""
    filler = FillerPhrase(
        text=request.text,
        category=request.category,
        speaker=request.speaker,
    )
    session.add(filler)
    await session.commit()
    await session.refresh(filler)
    logger.info(f"Created filler phrase: {filler.id}")
    return filler


@router.delete(
    "/fillers/{filler_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Filler Phrase",
    description="Soft deletes a filler phrase.",
)
async def delete_filler(
    filler_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a filler phrase."""
    result = await session.execute(
        select(FillerPhrase).where(FillerPhrase.id == filler_id)
    )
    filler = result.scalar_one_or_none()
    
    if not filler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filler phrase not found"
        )
    
    filler.is_active = False
    await session.commit()
    logger.info(f"Deleted filler phrase: {filler_id}")


# ===========================================
# Call Logs Endpoints
# ===========================================

@router.get(
    "/calls",
    response_model=CallLogListResponse,
    summary="Get Call Logs",
    description="Returns paginated call logs.",
)
async def get_call_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    phone: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get paginated call logs."""
    # Build query
    query = select(CallLog).order_by(CallLog.start_time.desc())
    count_query = select(func.count(CallLog.id))
    
    if phone:
        query = query.where(CallLog.phone.contains(phone))
        count_query = count_query.where(CallLog.phone.contains(phone))
    
    if status_filter:
        query = query.where(CallLog.call_status == status_filter)
        count_query = count_query.where(CallLog.call_status == status_filter)
    
    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await session.execute(query)
    items = list(result.scalars().all())
    
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    return {
        "items": [
            {
                "id": call.id,
                "phone": call.phone,
                "start_time": call.start_time,
                "end_time": call.end_time,
                "duration_seconds": call.duration_seconds,
                "status": call.call_status,
            }
            for call in items
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


@router.get(
    "/calls/{call_id}/transcript",
    summary="Get Call Transcript",
    description="Returns the transcript for a specific call.",
)
async def get_call_transcript(
    call_id: int,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get transcript for a specific call."""
    result = await session.execute(
        select(CallLog).where(CallLog.id == call_id)
    )
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    return {
        "transcript": call.transcript,
        "summary": call.summary,
    }


# ===========================================
# Voice Settings Endpoints
# ===========================================

# Voice settings storage path
VOICE_SETTINGS_FILE = Path("data/voice_settings.json")


def load_voice_settings() -> dict[str, Any]:
    """Load voice settings from JSON file."""
    if VOICE_SETTINGS_FILE.exists():
        try:
            with open(VOICE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading voice settings: {e}")
    return {}


def save_voice_settings(settings_data: dict[str, Any]) -> None:
    """Save voice settings to JSON file."""
    try:
        VOICE_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(VOICE_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings_data, f, indent=2, ensure_ascii=False)
        logger.info("Voice settings saved successfully")
    except Exception as e:
        logger.error(f"Error saving voice settings: {e}")


@router.get(
    "/voices",
    response_model=VoicesConfigResponse,
    summary="Get Voice Settings",
    description="Returns voice configuration for both AI personas.",
)
async def get_voice_settings_endpoint() -> dict[str, Any]:
    """Get voice settings for Sara and Nexus."""
    settings = get_settings()
    saved = load_voice_settings()
    
    # Load saved environment settings for voice IDs
    env_settings = load_environment_settings()
    
    return {
        "sara": saved.get("sara", {
            "voice_id": env_settings.get("elevenlabs_voice_sara", settings.elevenlabs_voice_sara),
            "stability": settings.elevenlabs_stability,
            "similarity_boost": settings.elevenlabs_similarity_boost,
            "style": 0.0,
            "speed": 1.0,
        }),
        "nexus": saved.get("nexus", {
            "voice_id": env_settings.get("elevenlabs_voice_nexus", settings.elevenlabs_voice_nexus),
            "stability": settings.elevenlabs_stability,
            "similarity_boost": settings.elevenlabs_similarity_boost,
            "style": 0.0,
            "speed": 1.0,
        }),
    }


@router.put(
    "/voices",
    response_model=VoicesConfigResponse,
    summary="Update Voice Settings",
    description="Updates voice configuration for AI personas.",
)
async def update_voice_settings(
    request: VoicesConfigResponse,
) -> dict[str, Any]:
    """Update voice settings."""
    logger.info(f"Updating voice settings: {request.model_dump_json()}")
    
    # Save to JSON file
    save_voice_settings(request.model_dump())
    
    # Also update environment settings with voice IDs for TTS
    env_settings = load_environment_settings()
    env_settings["elevenlabs_voice_sara"] = request.sara.voice_id
    env_settings["elevenlabs_voice_nexus"] = request.nexus.voice_id
    save_environment_settings(env_settings)
    
    return request.model_dump()


# TTS Test Request Model
class TTSTestRequest(BaseModel):
    """TTS test request."""
    text: str = Field(min_length=1, max_length=500)
    voice: str = Field(description="Voice name: 'sara' or 'nexus'")
    stability: float = Field(default=0.5, ge=0.0, le=1.0)
    similarity_boost: float = Field(default=0.75, ge=0.0, le=1.0)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


@router.post(
    "/voices/test",
    summary="Test Voice TTS",
    description="Generate speech using ElevenLabs API for voice testing.",
)
async def test_voice_tts(
    request: TTSTestRequest,
):
    """Generate TTS audio for testing."""
    import httpx
    from fastapi.responses import Response
    
    settings = get_settings()
    
    # Load saved environment settings (which may have Voice IDs)
    saved_settings = load_environment_settings()
    
    # Get the voice ID - first check saved settings, then fall back to .env
    if request.voice.lower() == "sara":
        voice_id = saved_settings.get("elevenlabs_voice_sara") or settings.elevenlabs_voice_sara
    elif request.voice.lower() == "nexus":
        voice_id = saved_settings.get("elevenlabs_voice_nexus") or settings.elevenlabs_voice_nexus
    else:
        raise HTTPException(status_code=400, detail=f"Unknown voice: {request.voice}")
    
    if not voice_id:
        raise HTTPException(status_code=400, detail=f"Voice ID not configured for {request.voice}. Please set it in Environment settings.")
    
    # Get API key - first check saved settings, then fall back to .env
    api_key = saved_settings.get("elevenlabs_api_key") or settings.elevenlabs_api_key
    # Don't use masked values (strings starting with dots)
    if api_key and api_key.startswith("•"):
        api_key = settings.elevenlabs_api_key
    
    if not api_key:
        raise HTTPException(status_code=400, detail="ElevenLabs API key not configured in .env or Environment settings")
    
    logger.info(f"Testing TTS: voice={request.voice}, voice_id={voice_id}, text length={len(request.text)}")
    
    try:
        # Call ElevenLabs API directly
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": request.text,
                    "model_id": settings.elevenlabs_model,
                    "voice_settings": {
                        "stability": request.stability,
                        "similarity_boost": request.similarity_boost,
                        "speed": request.speed,
                    },
                },
            )
            
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"ElevenLabs API error: {response.status_code} - {error_detail}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ElevenLabs API error: {error_detail}"
                )
            
            # Return audio as MP3
            return Response(
                content=response.content,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"inline; filename=tts_test_{request.voice}.mp3"
                }
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="TTS request timed out")
    except Exception as e:
        logger.error(f"TTS test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# System Prompt Endpoints
# ===========================================

@router.get(
    "/prompt",
    response_model=PromptResponse,
    summary="Get System Prompt",
    description="Returns the current system prompt.",
)
async def get_system_prompt() -> dict[str, Any]:
    """Get current system prompt."""
    settings = get_settings()
    
    return {
        "prompt": settings.system_prompt,
        "variables": [
            {"name": "{CONTEXT_FROM_MOCK_DB}", "description": "بيانات الأطباء والتأمين من قاعدة البيانات"},
            {"name": "{CONVERSATION_HISTORY}", "description": "سجل المحادثة الحالية"},
            {"name": "{CURRENT_DATE}", "description": "التاريخ الحالي"},
            {"name": "{PATIENT_INFO}", "description": "معلومات المريض إن وجدت"},
        ],
    }


@router.put(
    "/prompt",
    response_model=PromptResponse,
    summary="Update System Prompt",
    description="Updates the system prompt.",
)
async def update_system_prompt(
    request: PromptUpdateRequest,
) -> dict[str, Any]:
    """Update system prompt."""
    logger.info(f"Updating system prompt (length: {len(request.prompt)})")
    
    # In production, persist to database
    return {
        "prompt": request.prompt,
        "variables": [
            {"name": "{CONTEXT_FROM_MOCK_DB}", "description": "بيانات الأطباء والتأمين من قاعدة البيانات"},
            {"name": "{CONVERSATION_HISTORY}", "description": "سجل المحادثة الحالية"},
            {"name": "{CURRENT_DATE}", "description": "التاريخ الحالي"},
            {"name": "{PATIENT_INFO}", "description": "معلومات المريض إن وجدت"},
        ],
    }


# ===========================================
# Environment Settings Endpoints
# ===========================================

# Environment settings storage path
ENVIRONMENT_SETTINGS_FILE = Path("data/environment_settings.json")


def load_environment_settings() -> dict[str, Any]:
    """Load environment settings from JSON file."""
    if ENVIRONMENT_SETTINGS_FILE.exists():
        try:
            with open(ENVIRONMENT_SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading environment settings: {e}")
    return {}


def save_environment_settings(settings: dict[str, Any]) -> None:
    """Save environment settings to JSON file."""
    try:
        ENVIRONMENT_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ENVIRONMENT_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        logger.info("Environment settings saved successfully")
    except Exception as e:
        logger.error(f"Error saving environment settings: {e}")


@router.get(
    "/environment",
    response_model=EnvironmentResponse,
    summary="Get Environment Settings",
    description="Returns environment configuration.",
)
async def get_environment() -> dict[str, Any]:
    """Get environment settings."""
    settings = get_settings()
    
    # Load saved settings from JSON file
    saved_settings = load_environment_settings()
    
    # Merge with defaults from config
    result = {
        "telnyx_api_key": mask_api_key(settings.telnyx_api_key),
        "telnyx_connection_id": saved_settings.get("telnyx_connection_id", settings.telnyx_connection_id or ""),
        "telnyx_phone_number": saved_settings.get("telnyx_phone_number", settings.telnyx_phone_number or ""),
        "elevenlabs_api_key": mask_api_key(settings.elevenlabs_api_key),
        "elevenlabs_voice_sara": saved_settings.get("elevenlabs_voice_sara", settings.elevenlabs_voice_sara),
        "elevenlabs_voice_nexus": saved_settings.get("elevenlabs_voice_nexus", settings.elevenlabs_voice_nexus),
        "google_api_key": mask_api_key(settings.google_api_key),
        "vad_silence_threshold": saved_settings.get("vad_silence_threshold", settings.vad_min_silence_ms),
        "filler_delay": saved_settings.get("filler_delay", 300),
        "max_conversation_turns": saved_settings.get("max_conversation_turns", 50),
        "barge_in_enabled": saved_settings.get("barge_in_enabled", True),
        "debug_mode": saved_settings.get("debug_mode", settings.app_env == "development"),
        "call_recording": saved_settings.get("call_recording", False),
    }
    
    return result


def mask_api_key(key: str) -> str:
    """Mask API key for display, showing first 4 and last 4 chars."""
    if not key or len(key) < 8:
        return "••••••••"
    return key[:4] + "••••" + key[-4:]


@router.put(
    "/environment",
    response_model=EnvironmentResponse,
    summary="Update Environment Settings",
    description="Updates environment configuration.",
)
async def update_environment(
    request: EnvironmentResponse,
) -> dict[str, Any]:
    """Update environment settings."""
    logger.info("Updating environment settings")
    
    # Get current saved settings
    current_settings = load_environment_settings()
    
    # Update with new values (skip masked API keys)
    new_settings = request.model_dump()
    
    # Don't save masked API keys - keep original values
    for key in ["telnyx_api_key", "elevenlabs_api_key", "google_api_key"]:
        if new_settings.get(key, "").startswith("••"):
            # Keep the old value or remove from save
            if key in current_settings:
                new_settings[key] = current_settings[key]
            else:
                del new_settings[key]
    
    # Merge and save
    current_settings.update(new_settings)
    save_environment_settings(current_settings)
    
    return request.model_dump()
