"""
Nexus Miracle - LLM Service

Google Gemini 3 Flash integration for conversational AI.
Optimized for low-latency medical assistant responses.
Target: <200ms TTFT (Time to First Token).
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Literal

from loguru import logger
from pydantic import BaseModel

from app.config import get_settings
from app.exceptions import ContextLimitExceeded, GenerationError, LLMException


class ResponseSegment(BaseModel):
    """Single segment of LLM response."""
    
    speaker: Literal["sara", "nexus"] = "sara"
    text: str
    emotion: str = "neutral"
    action: str = "none"


@dataclass
class ConversationContext:
    """Context for LLM conversation."""
    
    doctors: list[dict] = field(default_factory=list)
    appointments: list[dict] = field(default_factory=list)
    insurance: list[dict] = field(default_factory=list)
    current_patient: dict | None = None


class LLMService:
    """
    Large Language Model service using Google Gemini.
    
    Handles conversation management and response generation
    for the medical contact center AI assistant.
    
    Features:
    - Dual persona support (Sara and Nexus)
    - Streaming response generation
    - JSON array output parsing
    - Database context integration
    
    Target: <200ms Time to First Token.
    """
    
    DEFAULT_SYSTEM_PROMPT = """أنتِ سارة، موظفة استقبال ذكية في عيادة نِكسوس مراكل الطبية في السعودية.

دورك:
- الترحيب بالمرضى ومساعدتهم في حجز المواعيد
- الإجابة على استفساراتهم حول الأطباء والتخصصات
- التحقق من تغطية التأمين الصحي
- تقديم معلومات عن العيادة

شخصيتك:
- ودودة ومهنية
- تتحدثين بالعربية السعودية
- تستخدمين عبارات مثل "إن شاء الله" و"ما شاء الله"
- صبورة ومتفهمة

عند الحاجة لمعلومات تقنية أو طبية متخصصة، قومي بتحويل المكالمة لنكسوس (المساعد الطبي).

يجب أن ترديّ بتنسيق JSON array كالتالي:
[
  {"speaker": "sara", "text": "النص هنا", "emotion": "happy", "action": "none"}
]

المشاعر المتاحة: neutral, happy, empathetic, concerned, professional
الإجراءات المتاحة: none, transfer_nexus, book_appointment, check_insurance, end_call"""
    
    def __init__(self) -> None:
        """Initialize the LLM service."""
        self._settings = get_settings()
        self._model: Any = None
        self._is_initialized = False
        
        # Statistics
        self._total_generations = 0
        self._total_ttft_ms = 0.0
        self._total_completion_ms = 0.0
        
        logger.info("LLMService created")
    
    async def initialize(self) -> None:
        """
        Initialize the Gemini client.
        
        Raises:
            LLMException: If initialization fails
        """
        if self._is_initialized:
            return
        
        try:
            import google.generativeai as genai
            
            api_key = self._settings.google_api_key
            if not api_key:
                raise LLMException(
                    message="Google API key not configured",
                    details={"setting": "google_api_key"},
                )
            
            genai.configure(api_key=api_key)
            
            # Use Gemini 3 Flash for lowest latency
            model_name = self._settings.gemini_model
            self._model = genai.GenerativeModel(
                model_name,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                },
            )
            
            self._is_initialized = True
            logger.info(f"LLMService initialized with model: {model_name}")
            
        except ImportError:
            logger.warning("google-generativeai package not installed")
            self._is_initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            raise LLMException(
                message="Failed to initialize LLM service",
                details={"error": str(e)},
            )
    
    async def generate_response(
        self,
        user_message: str,
        conversation_history: list[dict[str, str]],
        system_prompt: str | None = None,
        db_context: ConversationContext | None = None,
    ) -> list[ResponseSegment]:
        """
        Generate response segments for user message.
        
        Args:
            user_message: User's transcribed speech
            conversation_history: Previous conversation messages
            system_prompt: Custom system prompt (or use default)
            db_context: Database context (doctors, appointments, etc.)
        
        Returns:
            List of ResponseSegment for TTS synthesis
        """
        if not self._is_initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Build full prompt
            prompt = self._build_prompt(
                system_prompt or self.DEFAULT_SYSTEM_PROMPT,
                conversation_history,
                user_message,
                db_context,
            )
            
            # Generate response
            if self._model:
                response_text = await self._generate(prompt)
            else:
                # Placeholder response
                response_text = '[{"speaker": "sara", "text": "مرحباً! كيف أقدر أساعدك اليوم؟", "emotion": "happy", "action": "none"}]'
            
            # Parse JSON response
            segments = self._parse_response(response_text)
            
            # Log metrics
            total_ms = (time.time() - start_time) * 1000
            self._total_generations += 1
            self._total_completion_ms += total_ms
            
            logger.info(f"LLM ({total_ms:.0f}ms): {len(segments)} segments")
            
            return segments
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Return fallback response
            return [ResponseSegment(
                speaker="sara",
                text="عذراً، حصل خطأ. هل تقدر تعيد؟",
                emotion="concerned",
                action="none",
            )]
    
    async def generate_stream(
        self,
        user_message: str,
        conversation_history: list[dict[str, str]],
        system_prompt: str | None = None,
        db_context: ConversationContext | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response generation for lower latency.
        
        Yields tokens as they are generated.
        """
        if not self._is_initialized:
            await self.initialize()
        
        if not self._model:
            yield '[{"speaker": "sara", "text": "مرحباً!", "emotion": "happy"}]'
            return
        
        start_time = time.time()
        first_token_time = None
        
        try:
            prompt = self._build_prompt(
                system_prompt or self.DEFAULT_SYSTEM_PROMPT,
                conversation_history,
                user_message,
                db_context,
            )
            
            # Stream from Gemini
            response = await asyncio.to_thread(
                self._model.generate_content,
                prompt,
                stream=True,
            )
            
            for chunk in response:
                if first_token_time is None:
                    first_token_time = time.time()
                    ttft_ms = (first_token_time - start_time) * 1000
                    self._total_ttft_ms += ttft_ms
                    logger.debug(f"LLM TTFT: {ttft_ms:.0f}ms")
                
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            yield '[{"speaker": "sara", "text": "عذراً، حصل خطأ.", "emotion": "concerned"}]'
    
    async def _generate(self, prompt: str) -> str:
        """Generate complete response."""
        response = await asyncio.to_thread(
            self._model.generate_content,
            prompt,
        )
        return response.text
    
    def _build_prompt(
        self,
        system_prompt: str,
        conversation_history: list[dict[str, str]],
        user_message: str,
        db_context: ConversationContext | None,
    ) -> str:
        """Build the full prompt with context."""
        parts = [system_prompt, "\n\n"]
        
        # Add database context if available
        if db_context:
            parts.append("=== معلومات النظام ===\n")
            
            if db_context.doctors:
                parts.append("الأطباء المتاحون:\n")
                for doc in db_context.doctors[:5]:
                    parts.append(f"- د. {doc.get('name', 'غير معروف')} ({doc.get('specialty', 'عام')})\n")
                parts.append("\n")
            
            if db_context.appointments:
                parts.append("المواعيد المتاحة:\n")
                for apt in db_context.appointments[:5]:
                    parts.append(f"- {apt.get('date', '')} {apt.get('time', '')}\n")
                parts.append("\n")
            
            if db_context.insurance:
                parts.append("شركات التأمين المقبولة:\n")
                for ins in db_context.insurance[:5]:
                    parts.append(f"- {ins.get('name', '')}\n")
                parts.append("\n")
        
        # Add conversation history
        if conversation_history:
            parts.append("=== المحادثة السابقة ===\n")
            for msg in conversation_history[-10:]:  # Last 10 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    parts.append(f"المريض: {content}\n")
                else:
                    parts.append(f"المساعد: {content}\n")
            parts.append("\n")
        
        # Add current message
        parts.append(f"المريض: {user_message}\n\n")
        parts.append("الرد (بتنسيق JSON array):")
        
        return "".join(parts)
    
    def _parse_response(self, response_text: str) -> list[ResponseSegment]:
        """Parse JSON array response from LLM."""
        try:
            # Extract JSON from potential markdown code blocks
            json_match = re.search(r'\[[\s\S]*?\]', response_text)
            if json_match:
                json_str = json_match.group()
            else:
                json_str = response_text.strip()
            
            # Parse JSON
            data = json.loads(json_str)
            
            # Validate and convert
            segments = []
            for item in data:
                if isinstance(item, dict) and "text" in item:
                    segment = ResponseSegment(
                        speaker=item.get("speaker", "sara"),
                        text=item["text"],
                        emotion=item.get("emotion", "neutral"),
                        action=item.get("action", "none"),
                    )
                    segments.append(segment)
            
            return segments if segments else [
                ResponseSegment(text=response_text, speaker="sara")
            ]
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Return as single segment
            return [ResponseSegment(
                speaker="sara",
                text=response_text.strip(),
                emotion="neutral",
                action="none",
            )]
    
    def get_stats(self) -> dict[str, float]:
        """Get LLM performance statistics."""
        avg_ttft = 0.0
        avg_completion = 0.0
        
        if self._total_generations > 0:
            avg_ttft = self._total_ttft_ms / self._total_generations
            avg_completion = self._total_completion_ms / self._total_generations
        
        return {
            "total_generations": self._total_generations,
            "average_ttft_ms": avg_ttft,
            "average_completion_ms": avg_completion,
        }
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        self._is_initialized = False
        self._model = None
        logger.info("LLMService shutdown")


# Singleton instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get the LLM service singleton instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
