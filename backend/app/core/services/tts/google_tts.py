from __future__ import annotations

from typing import Any, List, Optional

from app.core.config import settings
from .base import TTSProvider, TTSResult, VoiceOption


class GoogleTTSProvider(TTSProvider):
    provider_name = "google"

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> TTSResult:
        if not settings.GOOGLE_TTS_API_KEY and not settings.GOOGLE_AI_STUDIO_API_KEY:
            return TTSResult(
                status="error",
                provider=self.provider_name,
                model=model or "text-to-speech",
                voice_id=voice_id,
                error="Google TTS API key is not configured",
            )

        return TTSResult(
            status="error",
            provider=self.provider_name,
            model=model or "text-to-speech",
            voice_id=voice_id,
            characters_used=len(text or ""),
            estimated_cost=self.get_cost_estimate(text, model=model),
            error="Google TTS provider not fully implemented yet",
        )

    async def list_voices(self, **kwargs: Any) -> List[VoiceOption]:
        return [
            VoiceOption(id="en-US-Neural2-J", name="English Neural 2 J", provider=self.provider_name, language="en-US"),
            VoiceOption(id="en-US-Studio-O", name="English Studio O", provider=self.provider_name, language="en-US"),
        ]

    def get_cost_estimate(self, text: str, model: Optional[str] = None, **kwargs: Any) -> float:
        chars = max(len(text or ""), 0)
        return round((chars / 1000) * 0.016, 4)

    def max_chars_per_request(self, model: Optional[str] = None) -> int:
        return 5000
