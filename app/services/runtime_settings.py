"""
Nexus Miracle - Runtime Settings Service

Dynamic settings that can be updated at runtime without server restart.
Settings are loaded from database/JSON and can be modified via Admin API.
"""

import json
from pathlib import Path
from typing import Any
from threading import Lock

from loguru import logger

from app.config import get_settings


class RuntimeSettings:
    """
    Singleton service for dynamic runtime settings.
    
    These settings can be updated via the Admin API and take effect immediately
    for new calls/sessions.
    """
    
    _instance = None
    _lock = Lock()
    
    # Settings storage path
    SETTINGS_FILE = Path("data/runtime_settings.json")
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._settings_lock = Lock()
        
        # Load defaults from config
        config = get_settings()
        
        # VAD Settings
        self._vad_threshold: float = config.vad_threshold
        self._vad_min_silence_ms: int = config.vad_min_silence_ms
        self._vad_min_speech_ms: int = 500
        
        # TTS Settings
        self._tts_stability: float = config.elevenlabs_stability
        self._tts_similarity_boost: float = config.elevenlabs_similarity_boost
        self._tts_speed: float = 1.0
        
        # LLM Settings
        self._system_prompt: str = config.system_prompt
        
        # Voice IDs
        self._voice_sara_id: str = config.elevenlabs_voice_sara
        self._voice_nexus_id: str = config.elevenlabs_voice_nexus
        
        # Behavior Settings
        self._barge_in_enabled: bool = True
        self._filler_delay_ms: int = 300
        self._max_conversation_turns: int = 50
        
        # Load saved settings from file
        self._load_from_file()
        
        logger.info("RuntimeSettings initialized")
    
    def _load_from_file(self) -> None:
        """Load settings from JSON file if exists."""
        if self.SETTINGS_FILE.exists():
            try:
                with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Apply saved settings
                if "vad_threshold" in data:
                    self._vad_threshold = data["vad_threshold"]
                if "vad_min_silence_ms" in data:
                    self._vad_min_silence_ms = data["vad_min_silence_ms"]
                if "vad_min_speech_ms" in data:
                    self._vad_min_speech_ms = data["vad_min_speech_ms"]
                if "tts_stability" in data:
                    self._tts_stability = data["tts_stability"]
                if "tts_similarity_boost" in data:
                    self._tts_similarity_boost = data["tts_similarity_boost"]
                if "tts_speed" in data:
                    self._tts_speed = data["tts_speed"]
                if "system_prompt" in data:
                    self._system_prompt = data["system_prompt"]
                if "voice_sara_id" in data:
                    self._voice_sara_id = data["voice_sara_id"]
                if "voice_nexus_id" in data:
                    self._voice_nexus_id = data["voice_nexus_id"]
                if "barge_in_enabled" in data:
                    self._barge_in_enabled = data["barge_in_enabled"]
                if "filler_delay_ms" in data:
                    self._filler_delay_ms = data["filler_delay_ms"]
                if "max_conversation_turns" in data:
                    self._max_conversation_turns = data["max_conversation_turns"]
                
                logger.info("RuntimeSettings loaded from file")
                
            except Exception as e:
                logger.error(f"Error loading runtime settings: {e}")
    
    def _save_to_file(self) -> None:
        """Save current settings to JSON file."""
        try:
            self.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "vad_threshold": self._vad_threshold,
                "vad_min_silence_ms": self._vad_min_silence_ms,
                "vad_min_speech_ms": self._vad_min_speech_ms,
                "tts_stability": self._tts_stability,
                "tts_similarity_boost": self._tts_similarity_boost,
                "tts_speed": self._tts_speed,
                "system_prompt": self._system_prompt,
                "voice_sara_id": self._voice_sara_id,
                "voice_nexus_id": self._voice_nexus_id,
                "barge_in_enabled": self._barge_in_enabled,
                "filler_delay_ms": self._filler_delay_ms,
                "max_conversation_turns": self._max_conversation_turns,
            }
            
            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info("RuntimeSettings saved to file")
            
        except Exception as e:
            logger.error(f"Error saving runtime settings: {e}")
    
    # ===========================================
    # VAD Settings Properties
    # ===========================================
    
    @property
    def vad_threshold(self) -> float:
        return self._vad_threshold
    
    @vad_threshold.setter
    def vad_threshold(self, value: float) -> None:
        with self._settings_lock:
            self._vad_threshold = max(0.0, min(1.0, value))
            self._save_to_file()
            logger.info(f"VAD threshold updated to: {self._vad_threshold}")
    
    @property
    def vad_min_silence_ms(self) -> int:
        return self._vad_min_silence_ms
    
    @vad_min_silence_ms.setter
    def vad_min_silence_ms(self, value: int) -> None:
        with self._settings_lock:
            self._vad_min_silence_ms = max(100, min(5000, value))
            self._save_to_file()
            logger.info(f"VAD min silence updated to: {self._vad_min_silence_ms}ms")
    
    @property
    def vad_min_speech_ms(self) -> int:
        return self._vad_min_speech_ms
    
    @vad_min_speech_ms.setter
    def vad_min_speech_ms(self, value: int) -> None:
        with self._settings_lock:
            self._vad_min_speech_ms = max(100, min(2000, value))
            self._save_to_file()
            logger.info(f"VAD min speech updated to: {self._vad_min_speech_ms}ms")
    
    # ===========================================
    # TTS Settings Properties
    # ===========================================
    
    @property
    def tts_stability(self) -> float:
        return self._tts_stability
    
    @tts_stability.setter
    def tts_stability(self, value: float) -> None:
        with self._settings_lock:
            self._tts_stability = max(0.0, min(1.0, value))
            self._save_to_file()
            logger.info(f"TTS stability updated to: {self._tts_stability}")
    
    @property
    def tts_similarity_boost(self) -> float:
        return self._tts_similarity_boost
    
    @tts_similarity_boost.setter
    def tts_similarity_boost(self, value: float) -> None:
        with self._settings_lock:
            self._tts_similarity_boost = max(0.0, min(1.0, value))
            self._save_to_file()
            logger.info(f"TTS similarity boost updated to: {self._tts_similarity_boost}")
    
    @property
    def tts_speed(self) -> float:
        return self._tts_speed
    
    @tts_speed.setter
    def tts_speed(self, value: float) -> None:
        with self._settings_lock:
            self._tts_speed = max(0.5, min(2.0, value))
            self._save_to_file()
            logger.info(f"TTS speed updated to: {self._tts_speed}")
    
    # ===========================================
    # Voice ID Properties
    # ===========================================
    
    @property
    def voice_sara_id(self) -> str:
        return self._voice_sara_id
    
    @voice_sara_id.setter
    def voice_sara_id(self, value: str) -> None:
        with self._settings_lock:
            self._voice_sara_id = value
            self._save_to_file()
            logger.info(f"Sara voice ID updated")
    
    @property
    def voice_nexus_id(self) -> str:
        return self._voice_nexus_id
    
    @voice_nexus_id.setter
    def voice_nexus_id(self, value: str) -> None:
        with self._settings_lock:
            self._voice_nexus_id = value
            self._save_to_file()
            logger.info(f"Nexus voice ID updated")
    
    # ===========================================
    # LLM Settings Properties
    # ===========================================
    
    @property
    def system_prompt(self) -> str:
        return self._system_prompt
    
    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        with self._settings_lock:
            self._system_prompt = value
            self._save_to_file()
            logger.info(f"System prompt updated (length: {len(value)})")
    
    # ===========================================
    # Behavior Settings Properties
    # ===========================================
    
    @property
    def barge_in_enabled(self) -> bool:
        return self._barge_in_enabled
    
    @barge_in_enabled.setter
    def barge_in_enabled(self, value: bool) -> None:
        with self._settings_lock:
            self._barge_in_enabled = value
            self._save_to_file()
            logger.info(f"Barge-in enabled: {self._barge_in_enabled}")
    
    @property
    def filler_delay_ms(self) -> int:
        return self._filler_delay_ms
    
    @filler_delay_ms.setter
    def filler_delay_ms(self, value: int) -> None:
        with self._settings_lock:
            self._filler_delay_ms = max(0, min(2000, value))
            self._save_to_file()
            logger.info(f"Filler delay updated to: {self._filler_delay_ms}ms")
    
    # ===========================================
    # Utility Methods
    # ===========================================
    
    def get_all(self) -> dict[str, Any]:
        """Get all settings as a dictionary."""
        return {
            "vad": {
                "threshold": self._vad_threshold,
                "min_silence_ms": self._vad_min_silence_ms,
                "min_speech_ms": self._vad_min_speech_ms,
            },
            "tts": {
                "stability": self._tts_stability,
                "similarity_boost": self._tts_similarity_boost,
                "speed": self._tts_speed,
            },
            "voices": {
                "sara_id": self._voice_sara_id,
                "nexus_id": self._voice_nexus_id,
            },
            "llm": {
                "system_prompt_length": len(self._system_prompt),
            },
            "behavior": {
                "barge_in_enabled": self._barge_in_enabled,
                "filler_delay_ms": self._filler_delay_ms,
                "max_conversation_turns": self._max_conversation_turns,
            },
        }
    
    def update_from_dict(self, data: dict[str, Any]) -> None:
        """Update multiple settings from a dictionary."""
        with self._settings_lock:
            if "vad_threshold" in data:
                self._vad_threshold = max(0.0, min(1.0, data["vad_threshold"]))
            if "vad_min_silence_ms" in data:
                self._vad_min_silence_ms = max(100, min(5000, data["vad_min_silence_ms"]))
            if "tts_stability" in data:
                self._tts_stability = max(0.0, min(1.0, data["tts_stability"]))
            if "tts_similarity_boost" in data:
                self._tts_similarity_boost = max(0.0, min(1.0, data["tts_similarity_boost"]))
            if "system_prompt" in data:
                self._system_prompt = data["system_prompt"]
            if "voice_sara_id" in data:
                self._voice_sara_id = data["voice_sara_id"]
            if "voice_nexus_id" in data:
                self._voice_nexus_id = data["voice_nexus_id"]
            if "barge_in_enabled" in data:
                self._barge_in_enabled = data["barge_in_enabled"]
            
            self._save_to_file()
            logger.info("RuntimeSettings batch updated")


# Singleton getter
_runtime_settings: RuntimeSettings | None = None


def get_runtime_settings() -> RuntimeSettings:
    """Get the RuntimeSettings singleton instance."""
    global _runtime_settings
    if _runtime_settings is None:
        _runtime_settings = RuntimeSettings()
    return _runtime_settings
