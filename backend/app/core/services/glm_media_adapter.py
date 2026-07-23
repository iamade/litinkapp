"""GLM / Z.AI media adapter.

Z.AI provides documented REST APIs for:
  - **Image generation**: ``POST /paas/v4/images/generations`` (sync)
    and ``POST /paas/v4/async/images/generations`` (async).
    Models: ``glm-image``, ``cogview-4-250304``.
  - **Video generation (async)**: ``POST /paas/v4/videos/generations``.
    Models: ``cogvideox-3``, Vidu variants.
  - **Audio transcription (ASR)**: ``POST /paas/v4/audio/transcriptions``
    (speech-to-text only — *not* TTS or audio generation).

There is **no** documented Z.AI TTS or audio-generation API, so those
modalities return an explicit ``ProviderUnsupportedResult``.

Auth uses the existing ``Z_AI_API_KEY`` / ``ZAI_API_KEY`` already in
``Settings`` (see ``config.py``).  The adapter keeps OpenClaw agent
credentials separate from product/API credentials by reading from
``settings`` rather than hard-coding keys.

References
----------
- Image: https://docs.z.ai/api-reference/image/generate-image.md
- Async image: https://docs.z.ai/api-reference/image/generate-image-async.md
- Async result: https://docs.z.ai/api-reference/image/get-image-status.md
- Video: https://docs.z.ai/api-reference/video/generate-video.md
- Audio (ASR): https://docs.z.ai/api-reference/audio/audio-transcriptions.md
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Z.AI media endpoints (relative to ``Z_AI_BASE_URL`` or the default)
_DEFAULT_BASE_URL = "https://api.z.ai/api/paas/v4"
_IMAGE_SYNC_PATH = "/images/generations"
_IMAGE_ASYNC_PATH = "/async/images/generations"
_VIDEO_ASYNC_PATH = "/videos/generations"
_ASYNC_RESULT_PATH = "/async-result/{task_id}"

# Polling configuration for async jobs
_POLL_INTERVAL_SECONDS = 5
_POLL_MAX_ATTEMPTS = 60  # 5 min at 5 s intervals


@dataclass
class ProviderUnsupportedResult:
    """Returned when a provider has no documented API for the requested modality."""

    status: str = "unsupported"
    provider: str = "glm"
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


class GLMMediaAdapter:
    """Additive media adapter for Z.AI / GLM.

    Supports image (sync + async) and video (async) generation using the
    documented Z.AI REST API.  TTS and audio generation return
    ``ProviderUnsupportedResult`` because Z.AI does not offer those endpoints.
    """

    PROVIDER_NAME: str = "glm"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._api_key = api_key  # resolved lazily via settings
        self._base_url = base_url
        self._http_client = http_client

    # ------------------------------------------------------------------
    # Lazy property accessors — keep OpenClaw agent creds separate from
    # product API creds by reading from ``settings`` at call time.
    # ------------------------------------------------------------------

    @property
    def api_key(self) -> str:
        key = self._api_key or settings.z_ai_api_key
        if not key:
            raise RuntimeError("Z_AI_API_KEY (or ZAI_API_KEY) is not configured")
        return key

    @property
    def base_url(self) -> str:
        return self._base_url or _DEFAULT_BASE_URL

    @property
    def http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=120)
        return self._http_client

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept-Language": "en-US,en",
        }

    # ------------------------------------------------------------------
    # Image generation (sync + async)
    # ------------------------------------------------------------------

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str,
        model_id: str = "glm-image",
        quality: str = "standard",
    ) -> Dict[str, Any]:
        """Generate an image via the Z.AI image API.

        Uses the sync endpoint for smaller models (``cogview-4-250304``)
        and the async endpoint for ``glm-image`` which may take ~20 s.
        """
        size = self._aspect_ratio_to_size(aspect_ratio)

        if model_id == "glm-image":
            return await self._generate_image_async(prompt, size, model_id, quality)
        return await self._generate_image_sync(prompt, size, model_id, quality)

    async def _generate_image_sync(
        self,
        prompt: str,
        size: str,
        model_id: str,
        quality: str,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{_IMAGE_SYNC_PATH}"
        payload = {
            "model": model_id,
            "prompt": prompt,
            "size": size,
            "quality": quality,
        }
        logger.info("[GLMMediaAdapter] Sync image request model=%s size=%s", model_id, size)
        start = time.monotonic()

        resp = await self.http_client.post(url, json=payload, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        elapsed = time.monotonic() - start

        image_url = self._extract_image_url(data)
        if not image_url:
            return {
                "status": "error",
                "error": data.get("error", {}).get("message", "No image URL in response"),
                "metadata": {"raw_response": data, "provider": self.PROVIDER_NAME, "model": model_id},
            }

        logger.info(
            "[GLMMediaAdapter] Sync image success model=%s elapsed=%.2fs",
            model_id,
            elapsed,
        )
        return {
            "status": "success",
            "image_url": image_url,
            "metadata": {
                "provider": self.PROVIDER_NAME,
                "model": model_id,
                "raw_response": data,
            },
        }

    async def _generate_image_async(
        self,
        prompt: str,
        size: str,
        model_id: str,
        quality: str,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{_IMAGE_ASYNC_PATH}"
        payload = {
            "model": model_id,
            "prompt": prompt,
            "size": size,
            "quality": quality,
        }
        logger.info("[GLMMediaAdapter] Async image request model=%s size=%s", model_id, size)
        start = time.monotonic()

        resp = await self.http_client.post(url, json=payload, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("id")
        if not task_id:
            return {
                "status": "error",
                "error": "No task id returned from async image request",
                "metadata": {"raw_response": data, "provider": self.PROVIDER_NAME, "model": model_id},
            }

        # Poll for completion
        result = await self._poll_async_result(task_id)
        elapsed = time.monotonic() - start

        if result.get("task_status") != "SUCCESS":
            return {
                "status": "error",
                "error": f"Async image task {task_id} did not succeed: {result.get('task_status')}",
                "metadata": {
                    "task_id": task_id,
                    "provider": self.PROVIDER_NAME,
                    "model": model_id,
                    "raw_response": result,
                },
            }

        image_url = self._extract_image_url(result)
        if not image_url:
            return {
                "status": "error",
                "error": "No image URL in async result",
                "metadata": {
                    "task_id": task_id,
                    "provider": self.PROVIDER_NAME,
                    "model": model_id,
                    "raw_response": result,
                },
            }

        logger.info(
            "[GLMMediaAdapter] Async image success task_id=%s model=%s elapsed=%.2fs",
            task_id,
            model_id,
            elapsed,
        )
        return {
            "status": "success",
            "image_url": image_url,
            "metadata": {
                "task_id": task_id,
                "provider": self.PROVIDER_NAME,
                "model": model_id,
                "raw_response": result,
            },
        }

    # ------------------------------------------------------------------
    # Video generation (async)
    # ------------------------------------------------------------------

    async def generate_video(
        self,
        image_url: str,
        prompt: str,
        model_id: str = "cogvideox-3",
        duration: Optional[float] = None,
        aspect_ratio: Optional[str] = None,
        with_audio: bool = True,
    ) -> Dict[str, Any]:
        """Generate a video via the Z.AI async video API.

        Supports image-to-video and text-to-video depending on whether
        ``image_url`` is provided.
        """
        url = f"{self.base_url}{_VIDEO_ASYNC_PATH}"
        size = self._aspect_ratio_to_size(aspect_ratio) if aspect_ratio else "1920x1080"
        payload: Dict[str, Any] = {
            "model": model_id,
            "prompt": prompt,
            "size": size,
            "with_audio": with_audio,
        }
        if image_url:
            payload["image_url"] = image_url

        logger.info("[GLMMediaAdapter] Async video request model=%s", model_id)
        start = time.monotonic()

        resp = await self.http_client.post(url, json=payload, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("id")
        if not task_id:
            return {
                "status": "error",
                "error": "No task id returned from async video request",
                "metadata": {"raw_response": data, "provider": self.PROVIDER_NAME, "model": model_id},
            }

        result = await self._poll_async_result(task_id)
        elapsed = time.monotonic() - start

        if result.get("task_status") != "SUCCESS":
            return {
                "status": "error",
                "error": f"Async video task {task_id} did not succeed: {result.get('task_status')}",
                "metadata": {
                    "task_id": task_id,
                    "provider": self.PROVIDER_NAME,
                    "model": model_id,
                    "raw_response": result,
                },
            }

        video_url = self._extract_video_url(result)
        if not video_url:
            return {
                "status": "error",
                "error": "No video URL in async result",
                "metadata": {
                    "task_id": task_id,
                    "provider": self.PROVIDER_NAME,
                    "model": model_id,
                    "raw_response": result,
                },
            }

        logger.info(
            "[GLMMediaAdapter] Async video success task_id=%s model=%s elapsed=%.2fs",
            task_id,
            model_id,
            elapsed,
        )
        return {
            "status": "success",
            "video_url": video_url,
            "metadata": {
                "task_id": task_id,
                "provider": self.PROVIDER_NAME,
                "model": model_id,
                "raw_response": result,
            },
        }

    # ------------------------------------------------------------------
    # Unsupported modalities — Z.AI has no TTS or audio generation API
    # ------------------------------------------------------------------

    async def synthesize_tts(
        self,
        text: str,
        voice_id: str,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Z.AI has no documented TTS API — returns unsupported."""
        logger.info(
            "[GLMMediaAdapter] TTS not supported (no documented Z.AI TTS API)"
        )
        return ProviderUnsupportedResult(
            provider="glm",
            modality="tts",
            message="Z.AI does not provide a documented TTS API",
        ).to_dict()

    async def generate_audio(
        self,
        prompt: str,
        duration: float,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Z.AI has no documented audio-generation API — returns unsupported.

        Note: Z.AI *does* offer audio *transcription* (ASR) but that is
        speech-to-text, not audio generation / TTS.
        """
        logger.info(
            "[GLMMediaAdapter] Audio generation not supported "
            "(no documented Z.AI audio-generation API; ASR is transcription only)"
        )
        return ProviderUnsupportedResult(
            provider="glm",
            modality="audio",
            message="Z.AI does not provide a documented audio-generation API (ASR is transcription only)",
        ).to_dict()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _poll_async_result(self, task_id: str) -> Dict[str, Any]:
        """Poll the Z.AI async-result endpoint until completion."""
        url = f"{self.base_url}{_ASYNC_RESULT_PATH.format(task_id=task_id)}"
        for attempt in range(_POLL_MAX_ATTEMPTS):
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            resp = await self.http_client.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            status = data.get("task_status")
            logger.debug(
                "[GLMMediaAdapter] Poll task_id=%s attempt=%d status=%s",
                task_id,
                attempt + 1,
                status,
            )
            if status in ("SUCCESS", "FAIL"):
                return data
        return {"task_status": "TIMEOUT", "id": task_id}

    @staticmethod
    def _aspect_ratio_to_size(aspect_ratio: str) -> str:
        """Map common aspect-ratio strings to Z.AI-supported image sizes."""
        mapping = {
            "1:1": "1280x1280",
            "3:2": "1568x1056",
            "2:3": "1056x1568",
            "4:3": "1472x1088",
            "3:4": "1088x1472",
            "16:9": "1728x960",
            "9:16": "960x1728",
        }
        return mapping.get(aspect_ratio, "1280x1280")

    @staticmethod
    def _extract_image_url(data: Dict[str, Any]) -> Optional[str]:
        """Extract the image URL from a Z.AI image response."""
        # Sync response: {"data": [{"url": "..."}]}
        image_result = data.get("image_result")
        if isinstance(image_result, list) and image_result:
            first = image_result[0]
            if isinstance(first, dict):
                return first.get("url")
            if isinstance(first, str):
                return first
        # Sync response shape
        data_list = data.get("data")
        if isinstance(data_list, list) and data_list:
            first = data_list[0]
            if isinstance(first, dict):
                return first.get("url")
            if isinstance(first, str):
                return first
        # Direct url field
        return data.get("url")

    @staticmethod
    def _extract_video_url(data: Dict[str, Any]) -> Optional[str]:
        """Extract the video URL from a Z.AI video response."""
        video_result = data.get("video_result")
        if isinstance(video_result, list) and video_result:
            first = video_result[0]
            if isinstance(first, dict):
                return first.get("url")
            if isinstance(first, str):
                return first
        return data.get("url")


# Module-level singleton (matches existing adapter convention)
glm_media_adapter = GLMMediaAdapter()