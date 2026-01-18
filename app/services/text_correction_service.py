"""
Nexus Miracle - Text Correction Service

Post-processes ASR transcription output to correct common errors:
1. Common STT errors (phonetic confusion)
2. Saudi dialect normalization
3. Medical terminology corrections
4. Filler word cleanup
"""

import re
from loguru import logger


class TextCorrectionService:
    """
    Corrects and normalizes ASR transcription output.
    
    Features:
    - Common Arabic STT error corrections
    - Saudi dialect normalization
    - Medical terminology fixes
    - Filler word and noise removal
    """
    
    # Common STT errors and their corrections (Saudi dialect)
    CORRECTION_MAP = {
        # Phonetic confusions
        "اه": "أنا",
        "اهه": "أنا",
        "هلا": "حياك",
        "هلاا": "حياك",
        "ايه": "نعم",
        "ايوه": "نعم",
        "أيوه": "نعم",
        "لا لا": "لا",
        "اوكي": "حسناً",
        "اوك": "حسناً",
        "يب": "نعم",
        "يس": "نعم",
        
        # Common mishearings
        "دكتور": "طبيب",
        "دكتوره": "طبيبة",
        "اسبتاليه": "مستشفى",
        "كلينيك": "عيادة",
        "ابوينتمنت": "موعد",
        "ابوينت منت": "موعد",
        
        # Numbers (common confusions)
        "تو": "اثنين",
        "ثري": "ثلاثة",
        "فور": "أربعة",
        "فايف": "خمسة",
        "سيكس": "ستة",
        "سفن": "سبعة",
        "ايت": "ثمانية",
        "ناين": "تسعة",
        "تن": "عشرة",
        
        # Medical terms
        "اكسري": "أشعة",
        "اكس ري": "أشعة",
        "سي تي سكان": "أشعة مقطعية",
        "ام ار اي": "رنين مغناطيسي",
        "تحليل": "تحليل",
        "لاب": "مختبر",
        
        # Saudi dialect to standard
        "وش": "ماذا",
        "ايش": "ماذا",
        "ليش": "لماذا",
        "كذا": "هكذا",
        "كيذا": "هكذا",
        "حق": "ملك",
        "يبي": "يريد",
        "ابي": "أريد",
        "ابغى": "أريد",
        "شلون": "كيف",
        "منو": "من",
        "شنو": "ماذا",
    }
    
    # Filler words and noise to remove
    FILLER_PATTERNS = [
        r"\bاممم+\b",
        r"\bامم+\b",
        r"\bهممم+\b",
        r"\bههه+\b",
        r"\bاه+\b",
        r"\bيعني\s+يعني\b",  # repeated "يعني"
        r"\[\w+\]",  # Bracketed annotations like [inaudible]
        r"\(\w+\)",  # Parenthetical noise markers
    ]
    
    # Patterns for normalizing Arabic text
    NORMALIZATION_PATTERNS = [
        # Multiple spaces to single
        (r"\s+", " "),
        # Normalize alef variations
        (r"[أإآ]", "ا"),
        # Normalize taa marbouta at end
        (r"ة(?=\s|$)", "ه"),
    ]
    
    def __init__(self, apply_normalization: bool = False):
        """
        Initialize the text correction service.
        
        Args:
            apply_normalization: Whether to apply Arabic text normalization
                               (may change meaning, use with caution)
        """
        self._apply_normalization = apply_normalization
        self._corrections_applied: dict[str, int] = {}
        
        # Compile filler patterns
        self._filler_regex = [re.compile(p, re.IGNORECASE) for p in self.FILLER_PATTERNS]
        
        # Compile normalization patterns
        self._norm_regex = [(re.compile(p), r) for p, r in self.NORMALIZATION_PATTERNS]
        
        logger.info("TextCorrectionService initialized")
    
    def correct(self, text: str) -> str:
        """
        Apply all corrections to transcribed text.
        
        Args:
            text: Raw ASR transcription
            
        Returns:
            Corrected and cleaned text
        """
        if not text or not text.strip():
            return ""
        
        original = text
        
        # Step 1: Remove fillers and noise
        text = self._remove_fillers(text)
        
        # Step 2: Apply word corrections
        text = self._apply_word_corrections(text)
        
        # Step 3: Normalize whitespace
        text = " ".join(text.split())
        
        # Step 4: Optional Arabic normalization (for matching purposes)
        if self._apply_normalization:
            text = self._normalize_arabic(text)
        
        if text != original:
            logger.debug(f"Correction: '{original}' -> '{text}'")
        
        return text.strip()
    
    def _remove_fillers(self, text: str) -> str:
        """Remove filler words and noise markers."""
        for pattern in self._filler_regex:
            text = pattern.sub("", text)
        return text
    
    def _apply_word_corrections(self, text: str) -> str:
        """Apply word-by-word corrections from the correction map."""
        words = text.split()
        corrected_words = []
        
        for word in words:
            clean_word = word.strip()
            if clean_word.lower() in self.CORRECTION_MAP:
                corrected = self.CORRECTION_MAP[clean_word.lower()]
                self._track_correction(clean_word, corrected)
                corrected_words.append(corrected)
            else:
                corrected_words.append(word)
        
        return " ".join(corrected_words)
    
    def _normalize_arabic(self, text: str) -> str:
        """Apply Arabic text normalization."""
        for pattern, replacement in self._norm_regex:
            text = pattern.sub(replacement, text)
        return text
    
    def _track_correction(self, original: str, corrected: str) -> None:
        """Track correction statistics."""
        key = f"{original}->{corrected}"
        self._corrections_applied[key] = self._corrections_applied.get(key, 0) + 1
    
    def add_correction(self, wrong: str, correct: str) -> None:
        """
        Add a new correction rule.
        
        Args:
            wrong: Incorrect word/phrase
            correct: Corrected word/phrase
        """
        self.CORRECTION_MAP[wrong.lower()] = correct
        logger.info(f"Added correction: '{wrong}' -> '{correct}'")
    
    def get_stats(self) -> dict:
        """
        Get correction statistics.
        
        Returns:
            Dictionary of corrections applied with counts
        """
        return {
            "corrections_applied": self._corrections_applied.copy(),
            "total_corrections": sum(self._corrections_applied.values()),
            "unique_corrections": len(self._corrections_applied),
        }
    
    def reset_stats(self) -> None:
        """Reset correction statistics."""
        self._corrections_applied.clear()


# Singleton instance
_text_correction_service: TextCorrectionService | None = None


def get_text_correction_service() -> TextCorrectionService:
    """
    Get the text correction service singleton instance.
    
    Returns:
        TextCorrectionService instance
    """
    global _text_correction_service
    if _text_correction_service is None:
        _text_correction_service = TextCorrectionService()
    return _text_correction_service
