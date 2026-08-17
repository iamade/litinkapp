from __future__ import annotations

from typing import Dict, Iterable, List

from app.core.model_config import (
    AUDIO_MODEL_CONFIG,
    IMAGE_MODEL_CONFIG,
    TTS_TIER_CONFIG,
    VIDEO_MODEL_CONFIG,
    ModelConfig,
    ModelTier,
)


class MediaRouter:
    """Resolve tiered media model config into provider-prefixed ladders."""

    CONFIG_BY_MEDIA_TYPE: Dict[str, Dict[ModelTier, ModelConfig]] = {
        "image": IMAGE_MODEL_CONFIG,
        "video": VIDEO_MODEL_CONFIG,
        "audio": AUDIO_MODEL_CONFIG,
        "tts": TTS_TIER_CONFIG,
    }

    SUPPORTED_PROVIDERS = {
        "image": {"modelslab", "piapi"},
        "video": {"modelslab", "piapi"},
        "audio": {"modelslab", "piapi", "elevenlabs"},
        "tts": {"modelslab", "piapi", "elevenlabs"},
        # KAN-447: kimi and glm added additively — no existing providers reordered
        "image": {"modelslab", "piapi", "glm"},
        "video": {"modelslab", "piapi", "glm"},
        "audio": {"modelslab", "piapi", "elevenlabs", "kimi", "glm"},
        "tts": {"modelslab", "piapi", "elevenlabs", "kimi", "glm"},
    }

    def resolve(self, tier: str | ModelTier, media_type: str) -> List[str]:
        """Return an ordered provider-prefixed ladder for a tier and media type."""
        normalized_media_type = media_type.lower()
        config_map = self.CONFIG_BY_MEDIA_TYPE.get(normalized_media_type)
        if config_map is None:
            raise ValueError(f"Unsupported media type: {media_type}")

        model_tier = self._normalize_tier(tier)
        config = config_map.get(model_tier)
        if config is None:
            raise ValueError(f"No {normalized_media_type} config for tier: {tier}")

        ladder = [
            self._normalize_model(model, normalized_media_type)
            for model in config.models
        ]
        if normalized_media_type in {"audio", "tts"}:
            ladder = self._ensure_elevenlabs_audio_fallback(ladder)

        return self._dedupe_supported(ladder, normalized_media_type)

    def get_ladder(self, tier: str | ModelTier, media_type: str) -> List[str]:
        return self.resolve(tier=tier, media_type=media_type)

    @staticmethod
    def split_model(model: str) -> tuple[str, str]:
        provider, _, provider_model = model.partition("/")
        if not provider_model:
            raise ValueError(f"Model is not provider-prefixed: {model}")
        return provider.lower(), provider_model

    @staticmethod
    def _normalize_tier(tier: str | ModelTier) -> ModelTier:
        if isinstance(tier, ModelTier):
            return tier
        return ModelTier(str(tier).lower())

    def _normalize_model(self, model: str, media_type: str) -> str:
        raw_model = model.strip()
        provider, separator, provider_model = raw_model.partition("/")
        if separator:
            return f"{provider.lower()}/{provider_model}"

        if media_type in {"audio", "tts"}:
            return f"modelslab/{raw_model}"
        return f"modelslab/{raw_model}"

    def _ensure_elevenlabs_audio_fallback(self, ladder: List[str]) -> List[str]:
        if any(model.startswith("elevenlabs/") for model in ladder):
            return ladder

        for model in ladder:
            provider, provider_model = self.split_model(model)
            if provider == "modelslab" and provider_model.startswith("eleven_"):
                return [*ladder, f"elevenlabs/{provider_model}"]
        return ladder

    def _dedupe_supported(self, models: Iterable[str], media_type: str) -> List[str]:
        supported = self.SUPPORTED_PROVIDERS[media_type]
        seen: set[str] = set()
        ladder: List[str] = []
        for model in models:
            provider, _ = self.split_model(model)
            if provider not in supported:
                continue
            if model not in seen:
                seen.add(model)
                ladder.append(model)
        return ladder


media_router = MediaRouter()
