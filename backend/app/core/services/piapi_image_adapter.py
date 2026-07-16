from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from app.core.services.media_router import MediaRouter, media_router
from app.core.services.modelslab_v7_image import ModelsLabV7ImageService
from app.core.services.piapi_client import PiAPIClient, piapi_client
from app.core.services.storage import S3StorageService

logger = logging.getLogger(__name__)


class PiAPIImageAdapter:
    """Image generation adapter that falls back from ModelsLab to PiAPI."""

    def __init__(
        self,
        *,
        router: Optional[MediaRouter] = None,
        piapi: Optional[PiAPIClient] = None,
        modelslab_service: Optional[ModelsLabV7ImageService] = None,
        storage_service: Optional[S3StorageService] = None,
    ) -> None:
        self.router = router or media_router
        self.piapi = piapi or piapi_client
        self.modelslab_service = modelslab_service
        self.storage_service = storage_service

    async def generate(
        self, prompt: str, aspect_ratio: str, user_tier: str
    ) -> Dict[str, Any]:
        ladder = self.router.resolve(tier=user_tier, media_type="image")
        errors: list[str] = []

        for model in ladder:
            provider, provider_model = self.router.split_model(model)
            try:
                if provider == "modelslab":
                    result = await self._generate_modelslab(
                        prompt=prompt,
                        aspect_ratio=aspect_ratio,
                        model_id=provider_model,
                    )
                elif provider == "piapi":
                    result = await self._generate_piapi(
                        prompt=prompt,
                        aspect_ratio=aspect_ratio,
                        model_id=provider_model,
                    )
                else:
                    continue

                if result.get("status") != "success" or not result.get("image_url"):
                    raise RuntimeError(result.get("error") or "image generation failed")

                canonical_url = await self._persist_image(result["image_url"])
                return {
                    "status": "success",
                    "canonical_url": canonical_url,
                    "provider_url": result["image_url"],
                    "metadata": {
                        **(result.get("metadata") or {}),
                        "provider": provider,
                        "model": provider_model,
                        "model_ladder": ladder,
                    },
                }
            except Exception as exc:
                error = f"{model}: {exc}"
                errors.append(error)
                logger.warning("[KAN-437 image adapter] Provider attempt failed: %s", error)
                continue

        raise RuntimeError(f"All image providers failed: {'; '.join(errors)}")

    async def _generate_modelslab(
        self, prompt: str, aspect_ratio: str, model_id: str
    ) -> Dict[str, Any]:
        service = self.modelslab_service
        if service is None:
            service = ModelsLabV7ImageService()

        result = await service.generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            model_id=model_id,
            wait_for_completion=True,
        )
        return {
            "status": result.get("status"),
            "image_url": result.get("image_url")
            or (result.get("output") or [None])[0],
            "metadata": {
                "raw_response": result,
                "generation_time": result.get("generation_time"),
            },
            "error": result.get("error"),
        }

    async def _generate_piapi(
        self, prompt: str, aspect_ratio: str, model_id: str
    ) -> Dict[str, Any]:
        result = await self.piapi.create_and_poll(
            model=model_id,
            task_type="txt2img",
            input={"prompt": prompt, "aspect_ratio": aspect_ratio},
        )
        return {
            "status": result.get("status"),
            "image_url": result.get("url"),
            "metadata": result.get("metadata") or {},
            "error": result.get("error"),
        }

    async def _persist_image(self, source_url: str) -> str:
        storage = self.storage_service or S3StorageService()
        dest_path = S3StorageService.build_media_path(
            "system",
            "images",
            str(uuid.uuid4()),
            "png",
            scope_id="kan-437-piapi",
        )
        return await storage.persist_from_url(
            source_url,
            dest_path,
            content_type="image/png",
        )


piapi_image_adapter = PiAPIImageAdapter()
