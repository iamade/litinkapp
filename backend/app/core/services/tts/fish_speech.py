from __future__ import annotations

from typing import Any, List, Optional

from app.core.config import settings
from .base import TTSProvider, TTSResult, VoiceOption


class FishSpeechTTSProvider(TTSProvider):
    provider_name = "fish-speech"

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> TTSResult:
        if not settings.FISH_SPEECH_API_KEY:
            return TTSResult(
                status="error",
                provider=self.provider_name,
                model=model or "default",
                voice_id=voice_id,
                error="FISH_SPEECH_API_KEY is not configured",
            )

        return TTSResult(
            status="error",
            provider=self.provider_name,
            model=model or "default",
            voice_id=voice_id,
            characters_used=len(text or ""),
            estimated_cost=self.get_cost_estimate(text, model=model),
            error="Fish Speech provider not fully implemented yet",
        )

    async def list_voices(self, **kwargs: Any) -> List[VoiceOption]:
        return [VoiceOption(id="fish-default", name="Fish Default", provider=self.provider_name)]

    def get_cost_estimate(self, text: str, model: Optional[str] = None, **kwargs: Any) -> float:
        chars = max(len(text or ""), 0)
        return round((chars / 1000) * 0.012, 4)

    def max_chars_per_request(self, model: Optional[str] = None) -> int:
        return 3000
