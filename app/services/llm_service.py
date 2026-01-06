"""
Nexus Miracle - LLM Service

Google Gemini 3 Flash integration for conversational AI.
Optimized for low-latency medical assistant responses.
"""

from typing import Any, AsyncGenerator

from loguru import logger

from app.config import get_settings
from app.exceptions import ContextLimitExceeded, GenerationError, LLMException


class LLMService:
    """
    Large Language Model service using Google Gemini.
    
    Handles conversation management and response generation
    for the medical contact center AI assistant.
    """
    
    # System prompt for the medical assistant
    DEFAULT_SYSTEM_PROMPT = """You are a professional medical assistant at Nexus Miracle, 
a healthcare center in Saudi Arabia. Your role is to:

1. Help patients book, reschedule, or cancel appointments
2. Answer general questions about services and departments
3. Provide clinic information (hours, locations)
4. Triage inquiries and direct to appropriate departments

Guidelines:
- Be professional, empathetic, and concise
- Respond in the same language the patient uses (Arabic or English)
- Never provide medical diagnoses or treatment advice
- For emergencies, always direct to emergency services (997 in KSA)
- Confirm patient information when booking appointments
- Keep responses brief for voice delivery (2-3 sentences max)"""
    
    def __init__(self) -> None:
        """Initialize the LLM service."""
        self._settings = get_settings()
        self._client: Any = None
        self._model: Any = None
        self._is_initialized = False
        
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
            # TODO: Initialize Gemini client
            # import google.generativeai as genai
            # genai.configure(api_key=self._settings.google_api_key)
            # self._model = genai.GenerativeModel(self._settings.gemini_model)
            
            self._is_initialized = True
            logger.info(f"LLMService initialized with model: {self._settings.gemini_model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            raise LLMException(
                message="Failed to initialize LLM service",
                details={"error": str(e)},
            )
    
    async def generate_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """
        Generate a response for the conversation.
        
        Args:
            messages: Conversation history as list of {role, content} dicts
            system_prompt: Optional custom system prompt
            temperature: Generation temperature (0-2)
            max_tokens: Maximum response tokens
        
        Returns:
            Generated response text
        
        Raises:
            GenerationError: If generation fails
            ContextLimitExceeded: If context is too long
        """
        if not self._is_initialized:
            await self.initialize()
        
        try:
            prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
            
            logger.debug(
                f"Generating response: {len(messages)} messages, "
                f"temp={temperature}, max_tokens={max_tokens}"
            )
            
            # TODO: Implement actual generation
            # full_prompt = self._build_prompt(prompt, messages)
            # response = await self._model.generate_content_async(
            #     full_prompt,
            #     generation_config={
            #         "temperature": temperature,
            #         "max_output_tokens": max_tokens,
            #     },
            # )
            # return response.text
            
            # Placeholder response
            last_message = messages[-1]["content"] if messages else ""
            return f"[LLM Response placeholder for: {last_message[:50]}...]"
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "context" in error_msg or "token" in error_msg:
                logger.warning(f"Context limit exceeded: {e}")
                raise ContextLimitExceeded(
                    message="Conversation context too long",
                    details={"error": str(e), "message_count": len(messages)},
                )
            
            logger.error(f"Response generation failed: {e}")
            raise GenerationError(
                message="Failed to generate response",
                details={"error": str(e)},
            )
    
    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response generation for lower latency.
        
        Yields tokens as they are generated, enabling
        early TTS synthesis for faster time-to-first-audio.
        
        Args:
            messages: Conversation history
            system_prompt: Optional custom system prompt
            temperature: Generation temperature
            max_tokens: Maximum response tokens
        
        Yields:
            Response text chunks
        
        Raises:
            GenerationError: If generation fails
        """
        if not self._is_initialized:
            await self.initialize()
        
        try:
            prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
            
            logger.debug(f"Starting streaming generation: {len(messages)} messages")
            
            # TODO: Implement streaming generation
            # full_prompt = self._build_prompt(prompt, messages)
            # response = await self._model.generate_content_async(
            #     full_prompt,
            #     stream=True,
            #     generation_config={
            #         "temperature": temperature,
            #         "max_output_tokens": max_tokens,
            #     },
            # )
            # async for chunk in response:
            #     yield chunk.text
            
            # Placeholder
            yield "[Streaming response "
            yield "placeholder]"
            
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            raise GenerationError(
                message="Streaming generation failed",
                details={"error": str(e)},
            )
    
    def _build_prompt(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> str:
        """
        Build the full prompt from system prompt and messages.
        
        Args:
            system_prompt: System instructions
            messages: Conversation messages
        
        Returns:
            Formatted prompt string
        """
        parts = [f"System: {system_prompt}\n"]
        
        for msg in messages:
            role = msg["role"].capitalize()
            content = msg["content"]
            parts.append(f"{role}: {content}")
        
        parts.append("Assistant:")
        
        return "\n".join(parts)
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        self._is_initialized = False
        self._client = None
        self._model = None
        logger.info("LLMService shutdown")


# Singleton instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """
    Get the LLM service singleton instance.
    
    Returns:
        LLMService instance
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
