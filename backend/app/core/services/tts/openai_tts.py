from __future__ import annotations

from typing import Any, List, Optional

from app.core.config import settings
from .base import TTSProvider, TTSResult, VoiceOption


class OpenAITTSProvider(TTSProvider):
    provider_name = "openai"

    async def synthesize(self, text: str, voice_id: Optional[str] = None, model: Optional[str] = None, **kwargs: Any) -> TTSResult:
        if not settings.OPENAI_API_KEY:
            return TTSResult(status="error", provider=self.provider_name, model=model or "tts-1", voice_id=voice_id, error="OPENAI_API_KEY is not configured")
        return TTSResult(status="error", provider=self.provider_name, model=model or "tts-1", voice_id=voice_id, characters_used=len(text or ""), estimated_cost=self.get_cost_estimate(text, model=model), error="OpenAI TTS provider not fully implemented yet")

    async def list_voices(self, **kwargs: Any) -> List[VoiceOption]:
        voices = ["alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer"]
        return [VoiceOption(id=v, name=v.title(), provider=self.provider_name) for v in voices]

    def get_cost_estimate(self, text: str, model: Optional[str] = None, **kwargs: Any) -> float:
        chars = max(len(text or ""), 0)
        rate_per_1k = 0.03 if (model or "tts-1") == "tts-1" else 0.06
        return round((chars / 1000) * rate_per_1k, 4)

    def max_chars_per_request(self, model: Optional[str] = None) -> int:
        return 4096
