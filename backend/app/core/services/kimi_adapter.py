"""Kimi / Moonshot media adapter.

Kimi (Moonshot AI) provides chat-completion models only (K3, K2.7 Code, K2.6).
There is **no documented product API** for image generation, audio/TTS, or video
generation on the Kimi OpenPlatform (https://platform.kimi.ai/docs).

This adapter follows the existing additive-provider pattern.  Each modality
checks for real API support and, when no documented endpoint exists, returns an
explicit ``ProviderUnsupportedResult`` so the media router can fall through to
the next provider in the ladder — no fake entries, no silent no-ops.

If Kimi ships media-generation endpoints in the future, the corresponding
methods can be filled in without touching call sites.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderUnsupportedResult:
    """Returned when a provider has no documented API for the requested modality."""

    status: str = "unsupported"
    provider: str = "kimi"
    modality: str = ""
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "modality": self.modality,
            "message": self.message,
            "metadata": self.metadata,
        }


class KimiMediaAdapter:
    """Additive media adapter for Kimi / Moonshot.

    Currently no media-generation API is documented on the Kimi OpenPlatform.
    Every modality returns ``ProviderUnsupportedResult`` so the caller can
    transparently skip Kimi and continue down the provider ladder.
    """

    PROVIDER_NAME: str = "kimi"
    BASE_URL: str = "https://api.moonshot.cn/v1"

    # ------------------------------------------------------------------
    # Public modality methods — each returns a dict compatible with the
    # existing adapter interface (status / url / metadata / error).
    # ------------------------------------------------------------------

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Kimi has no documented image-generation API."""
        logger.info(
            "[KimiMediaAdapter] Image generation not supported "
            "(no documented Kimi image API)"
        )
        return ProviderUnsupportedResult(
            modality="image",
            message="Kimi does not provide a documented image-generation API",
        ).to_dict()

    async def generate_video(
        self,
        image_url: str,
        prompt: str,
        model_id: Optional[str] = None,
        duration: Optional[float] = None,
        aspect_ratio: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Kimi has no documented video-generation API."""
        logger.info(
            "[KimiMediaAdapter] Video generation not supported "
            "(no documented Kimi video API)"
        )
        return ProviderUnsupportedResult(
            modality="video",
            message="Kimi does not provide a documented video-generation API",
        ).to_dict()

    async def synthesize_tts(
        self,
        text: str,
        voice_id: str,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Kimi has no documented TTS / audio-synthesis API."""
        logger.info(
            "[KimiMediaAdapter] TTS not supported "
            "(no documented Kimi TTS API)"
        )
        return ProviderUnsupportedResult(
            modality="tts",
            message="Kimi does not provide a documented TTS API",
        ).to_dict()

    async def generate_audio(
        self,
        prompt: str,
        duration: float,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Kimi has no documented audio-generation API."""
        logger.info(
            "[KimiMediaAdapter] Audio generation not supported "
            "(no documented Kimi audio-generation API)"
        )
        return ProviderUnsupportedResult(
            modality="audio",
            message="Kimi does not provide a documented audio-generation API",
        ).to_dict()


# Module-level singleton (matches existing adapter convention)
kimi_media_adapter = KimiMediaAdapter()