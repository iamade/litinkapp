from __future__ import annotations

from typing import Any, List, Optional

from app.core.services.elevenlabs import ElevenLabsService
from .base import TTSProvider, TTSResult, VoiceOption


class ElevenLabsTTSProvider(TTSProvider):
    provider_name = "elevenlabs"

    def __init__(self) -> None:
        self.service = ElevenLabsService()

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> TTSResult:
        resolved_voice = voice_id or "21m00Tcm4TlvDq8ikWAM"
        result = await self.service.generate_enhanced_speech(
            text=text,
            voice_id=resolved_voice,
            user_id=kwargs.get("user_id"),
            emotion=kwargs.get("emotion", "neutral"),
            speed=kwargs.get("speed", 1.0),
        )

        if result.get("audio_url"):
            return TTSResult(
                status="success",
                provider=self.provider_name,
                model=model or "eleven_turbo_v2",
                audio_url=result.get("audio_url"),
                voice_id=resolved_voice,
                characters_used=len(text),
                estimated_cost=self.get_cost_estimate(text, model=model),
                metadata={"local_path": result.get("local_path")},
            )

        return TTSResult(
            status="error",
            provider=self.provider_name,
            model=model or "eleven_turbo_v2",
            voice_id=resolved_voice,
            error=result.get("error") or "Failed to synthesize speech",
        )

    async def list_voices(self, **kwargs: Any) -> List[VoiceOption]:
        voices = await self.service.get_available_voices()
        return [
            VoiceOption(
                id=voice.get("voice_id") or voice.get("id") or voice.get("name", "unknown"),
                name=voice.get("name", "Unknown"),
                provider=self.provider_name,
                language=voice.get("language"),
                gender=voice.get("gender"),
                preview_url=voice.get("preview_url"),
                metadata=voice,
            )
            for voice in voices
        ]

    def get_cost_estimate(self, text: str, model: Optional[str] = None, **kwargs: Any) -> float:
        chars = max(len(text or ""), 0)
        rate_per_1k = 0.30 if "hd" in (model or "") else 0.18
        return round((chars / 1000) * rate_per_1k, 4)

    def max_chars_per_request(self, model: Optional[str] = None) -> int:
        return 5000
