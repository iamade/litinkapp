from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable, Dict, Optional

from app.core.config import settings
from app.core.services.media_router import MediaRouter, media_router
from app.core.services.modelslab_v7_video import ModelsLabV7VideoService
from app.core.services.piapi_client import PiAPIClient, piapi_client
from app.core.services.storage import S3StorageService

logger = logging.getLogger(__name__)


class PiAPIVideoAdapter:
    """Video adapter that falls back from ModelsLab to PiAPI unified tasks."""

    def __init__(
        self,
        *,
        router: Optional[MediaRouter] = None,
        piapi: Optional[PiAPIClient] = None,
        modelslab_service: Optional[ModelsLabV7VideoService] = None,
        storage_service: Optional[S3StorageService] = None,
        charge_credits: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.router = router or media_router
        self.piapi = piapi or piapi_client
        self.modelslab_service = modelslab_service
        self.storage_service = storage_service
        self.charge_credits = charge_credits

    async def generate_image_to_video(
        self,
        image_url: str,
        prompt: str,
        user_tier: str,
        duration: Optional[float] = None,
        aspect_ratio: Optional[str] = None,
    ) -> Dict[str, Any]:
        ladder = self.router.resolve(tier=user_tier, media_type="video")
        attempted_models: list[str] = []
        errors: list[str] = []
        storage = self._storage()
        provider_input_url = self._provider_input_url(storage, image_url)

        for model in ladder:
            provider, provider_model = self.router.split_model(model)
            attempted_models.append(model)
            start = time.monotonic()
            logger.info("[PiAPI video adapter] Attempting %s image-to-video", model)

            try:
                if provider == "modelslab":
                    result = await self._generate_modelslab_image_to_video(
                        image_url=provider_input_url,
                        prompt=prompt,
                        model_id=provider_model,
                        duration=duration,
                    )
                elif provider == "piapi":
                    result = await self._generate_piapi_image_to_video(
                        image_url=provider_input_url,
                        prompt=prompt,
                        model_id=provider_model,
                        duration=duration,
                        aspect_ratio=aspect_ratio,
                    )
                else:
                    continue

                provider_url = self._extract_video_url(result)
                if result.get("status") != "success" or not provider_url:
                    raise RuntimeError(result.get("error") or "video generation failed")

                canonical_url = await self._persist_video(storage, provider_url)
                elapsed = time.monotonic() - start
                task_id = (result.get("metadata") or {}).get("task_id")
                logger.info(
                    "[PiAPI video adapter] %s image-to-video success task_id=%s elapsed=%.2fs canonical_url=%s",
                    model,
                    task_id,
                    elapsed,
                    canonical_url,
                )
                return {
                    "status": "success",
                    "canonical_url": canonical_url,
                    "provider_url": provider_url,
                    "metadata": {
                        **(result.get("metadata") or {}),
                        "provider": provider,
                        "model": provider_model,
                        "task_id": task_id,
                        "model_ladder": ladder,
                    },
                }
            except Exception as exc:
                elapsed = time.monotonic() - start
                error = self._safe_error(exc)
                errors.append(f"{model}: {error}")
                logger.warning(
                    "[PiAPI video adapter] %s image-to-video failed elapsed=%.2fs error=%s",
                    model,
                    elapsed,
                    error,
                )

        return self._all_failed(errors, attempted_models)

    async def generate_lip_sync(
        self, video_url: str, audio_url: str, user_tier: str
    ) -> Dict[str, Any]:
        ladder = self.router.resolve(tier=user_tier, media_type="video")
        attempted_models: list[str] = []
        errors: list[str] = []
        storage = self._storage()
        provider_video_url = self._provider_input_url(storage, video_url)
        provider_audio_url = self._provider_input_url(storage, audio_url)

        for model in ladder:
            provider, provider_model = self.router.split_model(model)
            attempted_models.append(model)
            start = time.monotonic()
            logger.info("[PiAPI video adapter] Attempting %s lip-sync", model)

            try:
                if provider == "modelslab":
                    result = await self._generate_modelslab_lip_sync(
                        video_url=provider_video_url,
                        audio_url=provider_audio_url,
                    )
                elif provider == "piapi":
                    result = await self._generate_piapi_lip_sync(
                        video_url=provider_video_url,
                        audio_url=provider_audio_url,
                        model_id=provider_model,
                    )
                else:
                    continue

                provider_url = self._extract_video_url(result)
                if result.get("status") != "success" or not provider_url:
                    raise RuntimeError(result.get("error") or "lip-sync failed")

                canonical_url = await self._persist_video(storage, provider_url)
                elapsed = time.monotonic() - start
                task_id = (result.get("metadata") or {}).get("task_id")
                logger.info(
                    "[PiAPI video adapter] %s lip-sync success task_id=%s elapsed=%.2fs canonical_url=%s",
                    model,
                    task_id,
                    elapsed,
                    canonical_url,
                )
                return {
                    "status": "success",
                    "canonical_url": canonical_url,
                    "provider_url": provider_url,
                    "metadata": {
                        **(result.get("metadata") or {}),
                        "provider": provider,
                        "model": provider_model,
                        "task_id": task_id,
                        "model_ladder": ladder,
                    },
                }
            except Exception as exc:
                elapsed = time.monotonic() - start
                error = self._safe_error(exc)
                errors.append(f"{model}: {error}")
                logger.warning(
                    "[PiAPI video adapter] %s lip-sync failed elapsed=%.2fs error=%s",
                    model,
                    elapsed,
                    error,
                )

        return self._all_failed(errors, attempted_models)

    async def _generate_modelslab_image_to_video(
        self,
        *,
        image_url: str,
        prompt: str,
        model_id: str,
        duration: Optional[float],
    ) -> Dict[str, Any]:
        service = self.modelslab_service or ModelsLabV7VideoService()
        result = await service.generate_image_to_video(
            image_url=image_url,
            prompt=prompt,
            model_id=model_id,
            duration=duration or 5.0,
        )
        return {
            "status": result.get("status"),
            "video_url": self._extract_video_url(result),
            "metadata": {
                "raw_response": result,
                "task_id": result.get("request_id") or result.get("id"),
            },
            "error": result.get("error"),
        }

    async def _generate_modelslab_lip_sync(
        self, *, video_url: str, audio_url: str
    ) -> Dict[str, Any]:
        service = self.modelslab_service or ModelsLabV7VideoService()
        result = await service.generate_lip_sync(
            video_url=video_url,
            audio_url=audio_url,
            model_id="lipsync-2",
        )
        return {
            "status": result.get("status"),
            "video_url": self._extract_video_url(result),
            "metadata": {
                "raw_response": result,
                "task_id": result.get("request_id") or result.get("id"),
            },
            "error": result.get("error"),
        }

    async def _generate_piapi_image_to_video(
        self,
        *,
        image_url: str,
        prompt: str,
        model_id: str,
        duration: Optional[float],
        aspect_ratio: Optional[str],
    ) -> Dict[str, Any]:
        input_payload: Dict[str, Any] = {"image_url": image_url, "prompt": prompt}
        if duration is not None:
            input_payload["duration"] = duration
        if aspect_ratio:
            input_payload["aspect_ratio"] = aspect_ratio

        result = await self.piapi.create_and_poll(
            model=model_id,
            task_type="image2video",
            input=input_payload,
        )
        return {
            "status": result.get("status"),
            "video_url": result.get("url"),
            "metadata": result.get("metadata") or {},
            "error": result.get("error"),
        }

    async def _generate_piapi_lip_sync(
        self, *, video_url: str, audio_url: str, model_id: str
    ) -> Dict[str, Any]:
        result = await self.piapi.create_and_poll(
            model=model_id,
            task_type="lipsync",
            input={"video_url": video_url, "audio_url": audio_url},
        )
        return {
            "status": result.get("status"),
            "video_url": result.get("url"),
            "metadata": result.get("metadata") or {},
            "error": result.get("error"),
        }

    async def _persist_video(self, storage: S3StorageService, provider_url: str) -> str:
        dest_path = S3StorageService.build_media_path(
            "system",
            "videos",
            str(uuid.uuid4()),
            "mp4",
            scope_id="kan-437-piapi",
        )
        return await storage.persist_from_url(
            provider_url,
            dest_path,
            content_type="video/mp4",
        )

    def _storage(self) -> S3StorageService:
        return self.storage_service or S3StorageService()

    @staticmethod
    def _provider_input_url(storage: S3StorageService, source: str) -> str:
        if source.startswith(("http://", "https://")):
            return source
        return storage.presigned_url(source)

    @staticmethod
    def _extract_video_url(result: Dict[str, Any]) -> Optional[str]:
        if result.get("video_url"):
            return result["video_url"]
        if result.get("url"):
            return result["url"]
        output = result.get("output")
        if isinstance(output, list) and output:
            first = output[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                return first.get("video_url") or first.get("url")
        if isinstance(output, dict):
            return output.get("video_url") or output.get("url") or output.get("output_url")
        return None

    def _safe_error(self, exc: Exception) -> str:
        message = str(exc) or exc.__class__.__name__
        for secret in (
            getattr(settings, "MODELSLAB_API_KEY", None),
            getattr(settings, "PIAPI_API_KEY_LITINKAI", None),
            getattr(self.piapi, "api_key", None),
            getattr(self.modelslab_service, "api_key", None),
        ):
            if secret:
                message = message.replace(str(secret), "***")
        return message

    def _all_failed(self, errors: list[str], attempted_models: list[str]) -> Dict[str, Any]:
        error = "; ".join(errors) if errors else "No supported providers attempted"
        logger.error("[PiAPI video adapter] All providers failed: %s", error)
        return {
            "status": "error",
            "error": error,
            "attempted_models": attempted_models,
        }


piapi_video_adapter = PiAPIVideoAdapter()
