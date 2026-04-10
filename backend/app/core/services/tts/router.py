from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.core.model_config import get_model_config
from app.core.services.model_fallback import fallback_manager
from .base import TTSProvider, TTSResult, VoiceOption
from .chatterbox import ChatterboxTTSProvider
from .elevenlabs import ElevenLabsTTSProvider
from .fish_speech import FishSpeechTTSProvider
from .google_tts import GoogleTTSProvider
from .kokoro import KokoroTTSProvider
from .openai_tts import OpenAITTSProvider


class TTSRouter:
    def __init__(self) -> None:
        self.providers: Dict[str, TTSProvider] = {
            "elevenlabs": ElevenLabsTTSProvider(),
            "openai": OpenAITTSProvider(),
            "google": GoogleTTSProvider(),
            "fish-speech": FishSpeechTTSProvider(),
            "kokoro": KokoroTTSProvider(),
            "chatterbox": ChatterboxTTSProvider(),
        }

    def _parse_model(self, model: str) -> Tuple[str, str]:
        if "/" in model:
            provider, provider_model = model.split("/", 1)
            return provider, provider_model
        return "elevenlabs", model

    def get_provider_for_model(self, model: str) -> TTSProvider:
        provider_name, _ = self._parse_model(model)
        if provider_name not in self.providers:
            raise ValueError(f"Unknown TTS provider: {provider_name}")
        return self.providers[provider_name]

    async def synthesize(
        self,
        text: str,
        user_tier: str,
        voice_id: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        config = get_model_config("tts", user_tier)
        if not config and not model:
            raise ValueError(f"No TTS config found for tier: {user_tier}")

        requested_model = model or config.primary

        async def _generate_with_model(model: str, **inner_kwargs: Any) -> Dict[str, Any]:
            provider_name, provider_model = self._parse_model(model)
            provider = self.providers[provider_name]
            result = await provider.synthesize(
                text=text,
                voice_id=voice_id,
                model=provider_model,
                **kwargs,
                **inner_kwargs,
            )
            return result.to_dict()

        return await fallback_manager.try_with_fallback(
            service_type="tts",
            user_tier=user_tier,
            generation_function=_generate_with_model,
            request_params={"model": requested_model},
            model_param_name="model",
        )

    async def list_voices(self, user_tier: str, model: Optional[str] = None, **kwargs: Any) -> List[VoiceOption]:
        config = get_model_config("tts", user_tier)
        resolved_model = model or (config.primary if config else "elevenlabs/eleven_turbo_v2")
        provider_name, _ = self._parse_model(resolved_model)
        return await self.providers[provider_name].list_voices(**kwargs)

    def get_cost_estimate(self, text: str, user_tier: str, model: Optional[str] = None, **kwargs: Any) -> float:
        config = get_model_config("tts", user_tier)
        resolved_model = model or (config.primary if config else "elevenlabs/eleven_turbo_v2")
        provider_name, provider_model = self._parse_model(resolved_model)
        provider = self.providers[provider_name]
        return provider.get_cost_estimate(text=text, model=provider_model, **kwargs)

    def max_chars_per_request(self, user_tier: str, model: Optional[str] = None) -> int:
        config = get_model_config("tts", user_tier)
        resolved_model = model or (config.primary if config else "elevenlabs/eleven_turbo_v2")
        provider_name, provider_model = self._parse_model(resolved_model)
        provider = self.providers[provider_name]
        return provider.max_chars_per_request(model=provider_model)


tts_router = TTSRouter()
