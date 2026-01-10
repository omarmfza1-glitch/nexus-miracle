"""
Nexus Miracle - Filler Service

Pre-cached filler phrases for masking AI processing latency.
Supports category-based selection and empathy detection.
"""

import asyncio
import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from app.config import get_settings


@dataclass
class FillerPhrase:
    """Single filler phrase with audio."""
    
    id: str
    text: str
    category: str
    audio_file: str | None = None
    duration_ms: int = 0


@dataclass
class FillerCategory:
    """Category of filler phrases."""
    
    name: str
    phrases: list[FillerPhrase] = field(default_factory=list)
    trigger_keywords: list[str] = field(default_factory=list)


class FillerService:
    """
    Filler phrase management service.
    
    Provides pre-cached audio files for common filler phrases
    to mask AI processing latency during calls.
    
    Categories:
    - thinking: "حطني على لحظة" (Just a moment)
    - searching: "أبحث لك الآن" (Searching for you)
    - empathy: "أفهم شعورك" (I understand)
    - acknowledgment: "تمام" (Okay)
    """
    
    # Default filler phrases (Arabic Saudi dialect)
    DEFAULT_FILLERS = {
        "thinking": {
            "keywords": [],
            "phrases": [
                {"id": "think_1", "text": "لحظة من فضلك"},
                {"id": "think_2", "text": "حطني على السماعة لحظة"},
                {"id": "think_3", "text": "دقيقة وحدة"},
            ]
        },
        "searching": {
            "keywords": ["موعد", "دكتور", "طبيب", "حجز"],
            "phrases": [
                {"id": "search_1", "text": "أبحث لك عن المواعيد المتاحة"},
                {"id": "search_2", "text": "خليني أشوف الجدول"},
                {"id": "search_3", "text": "أتحقق من البيانات"},
            ]
        },
        "empathy": {
            "keywords": ["تعبان", "مريض", "ألم", "صعب", "مشكلة", "زعلان"],
            "phrases": [
                {"id": "emp_1", "text": "أفهم شعورك تماماً"},
                {"id": "emp_2", "text": "الله يشفيك ويعافيك"},
                {"id": "emp_3", "text": "إن شاء الله خير"},
            ]
        },
        "acknowledgment": {
            "keywords": [],
            "phrases": [
                {"id": "ack_1", "text": "تمام"},
                {"id": "ack_2", "text": "ممتاز"},
                {"id": "ack_3", "text": "حسناً"},
            ]
        },
    }
    
    def __init__(self, fillers_path: str | None = None) -> None:
        """
        Initialize the filler service.
        
        Args:
            fillers_path: Path to fillers directory (default: data/fillers)
        """
        self._settings = get_settings()
        self._fillers_path = Path(fillers_path or "data/fillers")
        
        # Loaded fillers by category
        self._categories: dict[str, FillerCategory] = {}
        
        # Pre-loaded audio cache: phrase_id -> audio_bytes
        self._audio_cache: dict[str, bytes] = {}
        
        # Statistics
        self._total_uses = 0
        self._category_uses: dict[str, int] = {}
        
        self._is_initialized = False
        logger.info("FillerService created")
    
    async def initialize(self) -> None:
        """Load fillers from config and preload audio files."""
        if self._is_initialized:
            return
        
        # Load filler definitions
        await self._load_fillers()
        
        # Preload audio files
        await self._preload_audio()
        
        self._is_initialized = True
        logger.info(
            f"FillerService initialized: {len(self._categories)} categories, "
            f"{len(self._audio_cache)} audio files cached"
        )
    
    async def _load_fillers(self) -> None:
        """Load filler definitions from JSON or defaults."""
        config_file = self._fillers_path / "filler_phrases.json"
        
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                for cat_name, cat_data in data.items():
                    phrases = [
                        FillerPhrase(
                            id=p.get("id", f"{cat_name}_{i}"),
                            text=p["text"],
                            category=cat_name,
                            audio_file=p.get("audio_file"),
                            duration_ms=p.get("duration_ms", 0),
                        )
                        for i, p in enumerate(cat_data.get("phrases", []))
                    ]
                    
                    self._categories[cat_name] = FillerCategory(
                        name=cat_name,
                        phrases=phrases,
                        trigger_keywords=cat_data.get("keywords", []),
                    )
                
                logger.info(f"Loaded fillers from {config_file}")
                return
                
            except Exception as e:
                logger.warning(f"Failed to load fillers from file: {e}")
        
        # Use defaults
        for cat_name, cat_data in self.DEFAULT_FILLERS.items():
            phrases = [
                FillerPhrase(
                    id=p["id"],
                    text=p["text"],
                    category=cat_name,
                )
                for p in cat_data["phrases"]
            ]
            
            self._categories[cat_name] = FillerCategory(
                name=cat_name,
                phrases=phrases,
                trigger_keywords=cat_data.get("keywords", []),
            )
        
        logger.info("Using default filler phrases")
    
    async def _preload_audio(self) -> None:
        """Preload all filler audio files into memory."""
        audio_dir = self._fillers_path / "audio"
        
        if not audio_dir.exists():
            logger.warning(f"Filler audio directory not found: {audio_dir}")
            return
        
        for category in self._categories.values():
            for phrase in category.phrases:
                if phrase.audio_file:
                    audio_path = audio_dir / phrase.audio_file
                    
                    if audio_path.exists():
                        try:
                            audio_bytes = await asyncio.to_thread(
                                audio_path.read_bytes
                            )
                            self._audio_cache[phrase.id] = audio_bytes
                            logger.debug(f"Cached audio: {phrase.id}")
                        except Exception as e:
                            logger.warning(f"Failed to load audio {phrase.id}: {e}")
    
    def get_random_filler(
        self,
        category: str = "thinking",
    ) -> tuple[FillerPhrase, bytes | None]:
        """
        Get a random filler phrase from a category.
        
        Args:
            category: Category name (thinking, searching, empathy, acknowledgment)
        
        Returns:
            Tuple of (FillerPhrase, audio_bytes or None)
        """
        if category not in self._categories:
            logger.warning(f"Unknown filler category: {category}")
            category = "thinking"
        
        cat = self._categories[category]
        if not cat.phrases:
            logger.warning(f"No phrases in category: {category}")
            return FillerPhrase(id="default", text="لحظة", category=category), None
        
        # Select random phrase
        phrase = random.choice(cat.phrases)
        audio = self._audio_cache.get(phrase.id)
        
        # Update stats
        self._total_uses += 1
        self._category_uses[category] = self._category_uses.get(category, 0) + 1
        
        return phrase, audio
    
    def get_empathy_filler(
        self,
        user_text: str,
    ) -> tuple[FillerPhrase, bytes | None] | None:
        """
        Get empathy filler if user text contains trigger keywords.
        
        Args:
            user_text: User's transcribed speech
        
        Returns:
            Tuple of (FillerPhrase, audio_bytes) or None if no match
        """
        if "empathy" not in self._categories:
            return None
        
        cat = self._categories["empathy"]
        
        # Check for trigger keywords
        user_lower = user_text.lower()
        for keyword in cat.trigger_keywords:
            if keyword in user_lower:
                logger.debug(f"Empathy keyword matched: {keyword}")
                return self.get_random_filler("empathy")
        
        return None
    
    def get_contextual_filler(
        self,
        user_text: str,
    ) -> tuple[FillerPhrase, bytes | None]:
        """
        Get contextually appropriate filler based on user text.
        
        Args:
            user_text: User's transcribed speech
        
        Returns:
            Tuple of (FillerPhrase, audio_bytes or None)
        """
        user_lower = user_text.lower()
        
        # Check each category's keywords
        for cat_name, cat in self._categories.items():
            for keyword in cat.trigger_keywords:
                if keyword in user_lower:
                    return self.get_random_filler(cat_name)
        
        # Default to thinking
        return self.get_random_filler("thinking")
    
    def get_all_categories(self) -> list[str]:
        """Get list of all category names."""
        return list(self._categories.keys())
    
    def get_category_phrases(self, category: str) -> list[FillerPhrase]:
        """Get all phrases in a category."""
        if category not in self._categories:
            return []
        return self._categories[category].phrases
    
    def get_stats(self) -> dict[str, Any]:
        """Get filler usage statistics."""
        return {
            "total_uses": self._total_uses,
            "by_category": dict(self._category_uses),
            "cached_audio_count": len(self._audio_cache),
            "total_categories": len(self._categories),
        }
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        self._audio_cache.clear()
        self._is_initialized = False
        logger.info("FillerService shutdown")


# Singleton instance
_filler_service: FillerService | None = None


def get_filler_service() -> FillerService:
    """Get the filler service singleton instance."""
    global _filler_service
    if _filler_service is None:
        _filler_service = FillerService()
    return _filler_service
