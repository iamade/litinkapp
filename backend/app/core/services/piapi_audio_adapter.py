from __future__ import annotations

import inspect
import logging
import time
import uuid
from typing import Any, Callable, Dict, Optional

from app.core.config import settings
from app.core.services.media_router import MediaRouter, media_router
from app.core.services.modelslab_v7_audio import ModelsLabV7AudioService
from app.core.services.piapi_client import PiAPIClient, piapi_client
from app.core.services.storage import S3StorageService

logger = logging.getLogger(__name__)


class PiAPIAudioAdapter:
    """Audio adapter that falls back from ElevenLabs/ModelsLab to PiAPI."""

    def __init__(
        self,
        *,
        router: Optional[MediaRouter] = None,
        piapi: Optional[PiAPIClient] = None,
        tts_router: Optional[Any] = None,
        modelslab_service: Optional[ModelsLabV7AudioService] = None,
        storage_service: Optional[S3StorageService] = None,
        charge_credits: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.router = router or media_router
        self.piapi = piapi or piapi_client
        self.tts_router = tts_router
        self.modelslab_service = modelslab_service
        self.storage_service = storage_service
        self.charge_credits = charge_credits

    async def synthesize_text(
        self,
        text: str,
        voice_id: str,
        user_tier: str,
        speed: float = 1.0,
        emotion: str = "neutral",
    ) -> Dict[str, Any]:
        ladder = self.router.resolve(tier=user_tier, media_type="audio")
        return await self._try_ladder(
            operation="tts",
            ladder=ladder,
            call_by_provider={
                "elevenlabs": lambda model: self._generate_elevenlabs_tts(
                    text=text,
                    voice_id=voice_id,
                    user_tier=user_tier,
                    model_id=model,
                    speed=speed,
                    emotion=emotion,
                ),
                "modelslab": lambda model: self._generate_modelslab_tts(
                    text=text,
                    voice_id=voice_id,
                    model_id=model,
                    speed=speed,
                    emotion=emotion,
                ),
                "piapi": lambda model: self._generate_piapi_tts(
                    text=text,
                    voice_id=voice_id,
                    model_id=model,
                    speed=speed,
                    emotion=emotion,
                ),
            },
        )

    async def generate_sound_effect(
        self, prompt: str, duration: float, intensity: str, user_tier: str
    ) -> Dict[str, Any]:
        ladder = self.router.resolve(tier=user_tier, media_type="audio")
        return await self._try_ladder(
            operation="sound-effect",
            ladder=ladder,
            call_by_provider={
                "modelslab": lambda model: self._generate_modelslab_sound_effect(
                    prompt=prompt,
                    duration=duration,
                    model_id=model,
                ),
                "piapi": lambda model: self._generate_piapi_sound_effect(
                    prompt=prompt,
                    duration=duration,
                    intensity=intensity,
                    model_id=model,
                ),
            },
        )

    async def generate_music(
        self,
        prompt: str,
        duration: float,
        user_tier: str,
        style: Optional[str] = None,
    ) -> Dict[str, Any]:
        ladder = self.router.resolve(tier=user_tier, media_type="audio")
        return await self._try_ladder(
            operation="music",
            ladder=ladder,
            call_by_provider={
                "modelslab": lambda model: self._generate_modelslab_music(
                    prompt=prompt,
                    duration=duration,
                    model_id=model,
                ),
                "piapi": lambda model: self._generate_piapi_music(
                    prompt=prompt,
                    duration=duration,
                    style=style,
                    model_id=model,
                ),
            },
        )

    async def _try_ladder(
        self,
        *,
        operation: str,
        ladder: list[str],
        call_by_provider: Dict[str, Callable[[str], Any]],
    ) -> Dict[str, Any]:
        attempted_models: list[str] = []
        errors: list[str] = []
        storage = self._storage()

        for model in ladder:
            provider, provider_model = self.router.split_model(model)
            if provider not in call_by_provider:
                continue
            if not self._model_matches_operation(provider, provider_model, operation):
                continue

            attempted_models.append(model)
            start = time.monotonic()
            logger.info("[PiAPI audio adapter] Attempting %s for %s", model, operation)

            try:
                maybe_result = call_by_provider[provider](provider_model)
                result = await maybe_result if inspect.isawaitable(maybe_result) else maybe_result

                provider_url = self._extract_audio_url(result)
                if result.get("status") != "success" or not provider_url:
                    raise RuntimeError(result.get("error") or f"{operation} generation failed")

                canonical_url = await self._persist_audio(storage, provider_url)
                elapsed = time.monotonic() - start
                task_id = (result.get("metadata") or {}).get("task_id")
                logger.info(
                    "[PiAPI audio adapter] %s %s success task_id=%s elapsed=%.2fs canonical_url=%s",
                    model,
                    operation,
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
                    "[PiAPI audio adapter] %s %s failed elapsed=%.2fs error=%s",
                    model,
                    operation,
                    elapsed,
                    error,
                )

        return self._all_failed(operation, errors, attempted_models)

    async def _generate_elevenlabs_tts(
        self,
        *,
        text: str,
        voice_id: str,
        user_tier: str,
        model_id: str,
        speed: float,
        emotion: str,
    ) -> Dict[str, Any]:
        router = self.tts_router
        if router is None:
            from app.core.services.tts.router import TTSRouter

            router = TTSRouter()

        result = await router.synthesize(
            text=text,
            user_tier=user_tier,
            voice_id=voice_id,
            model=f"elevenlabs/{model_id}",
            speed=speed,
            emotion=emotion,
        )
        return {
            "status": result.get("status"),
            "audio_url": self._extract_audio_url(result),
            "metadata": {
                **(result.get("metadata") or {}),
                "task_id": result.get("task_id"),
                "voice_id": result.get("voice_id") or voice_id,
            },
            "error": result.get("error"),
        }

    async def _generate_modelslab_tts(
        self,
        *,
        text: str,
        voice_id: str,
        model_id: str,
        speed: float,
        emotion: str,
    ) -> Dict[str, Any]:
        service = self.modelslab_service or ModelsLabV7AudioService()
        style = 0.0 if emotion == "neutral" else 0.5
        result = await service.generate_tts_audio(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            speed=speed,
            style=style,
        )
        return self._standardize_modelslab_result(result)

    async def _generate_modelslab_sound_effect(
        self, *, prompt: str, duration: float, model_id: str
    ) -> Dict[str, Any]:
        service = self.modelslab_service or ModelsLabV7AudioService()
        result = await service.generate_sound_effect(
            description=prompt,
            duration=duration,
            model_id=model_id,
        )
        return self._standardize_modelslab_result(result)

    async def _generate_modelslab_music(
        self, *, prompt: str, duration: float, model_id: str
    ) -> Dict[str, Any]:
        service = self.modelslab_service or ModelsLabV7AudioService()
        result = await service.generate_background_music(
            description=prompt,
            duration=duration,
            model_id=model_id,
        )
        return self._standardize_modelslab_result(result)

    async def _generate_piapi_tts(
        self,
        *,
        text: str,
        voice_id: str,
        model_id: str,
        speed: float,
        emotion: str,
    ) -> Dict[str, Any]:
        result = await self.piapi.create_and_poll(
            model=model_id,
            task_type="text2audio",
            input={
                "text": text,
                "voice_id": voice_id,
                "speed": speed,
                "emotion": emotion,
            },
        )
        return self._standardize_piapi_result(result)

    async def _generate_piapi_sound_effect(
        self, *, prompt: str, duration: float, intensity: str, model_id: str
    ) -> Dict[str, Any]:
        result = await self.piapi.create_and_poll(
            model=model_id,
            task_type="sound-effect",
            input={
                "prompt": prompt,
                "duration": duration,
                "intensity": intensity,
            },
        )
        return self._standardize_piapi_result(result)

    async def _generate_piapi_music(
        self,
        *,
        prompt: str,
        duration: float,
        style: Optional[str],
        model_id: str,
    ) -> Dict[str, Any]:
        style_prompt = f"{style}: {prompt}" if style else prompt
        input_payload: Dict[str, Any] = {
            "style_prompt": style_prompt,
            "negative_prompt": "low quality, distorted, clipping",
            "lyrics": "[Instrumental]",
            "duration": duration,
        }

        result = await self.piapi.create_and_poll(
            model=model_id,
            task_type="txt2audio",
            input=input_payload,
        )
        return self._standardize_piapi_result(result)

    @staticmethod
    def _model_matches_operation(provider: str, model_id: str, operation: str) -> bool:
        if provider == "piapi":
            lowered = model_id.lower()
            if operation == "tts":
                return "tts" in lowered or "f5" in lowered
            if operation == "sound-effect":
                return "fx" in lowered or "sfx" in lowered or "sound" in lowered
            if operation == "music":
                return "ace-step" in lowered or lowered == "musicgen"
        return True

    @staticmethod
    def _standardize_modelslab_result(result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": result.get("status"),
            "audio_url": PiAPIAudioAdapter._extract_audio_url(result),
            "metadata": {
                "raw_response": result,
                "task_id": result.get("request_id") or result.get("id"),
                "audio_time": result.get("audio_time"),
                "generation_time": result.get("generation_time"),
            },
            "error": result.get("error"),
        }

    @staticmethod
    def _standardize_piapi_result(result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": result.get("status"),
            "audio_url": PiAPIAudioAdapter._extract_audio_url(result),
            "metadata": result.get("metadata") or {},
            "error": result.get("error"),
        }

    async def _persist_audio(self, storage: S3StorageService, provider_url: str) -> str:
        dest_path = S3StorageService.build_media_path(
            "system",
            "audio",
            str(uuid.uuid4()),
            "mp3",
            scope_id="kan-437-piapi",
        )
        return await storage.persist_from_url(
            provider_url,
            dest_path,
            content_type="audio/mpeg",
        )

    def _storage(self) -> S3StorageService:
        return self.storage_service or S3StorageService()

    @staticmethod
    def provider_input_url(storage: S3StorageService, source: str) -> str:
        if source.startswith(("http://", "https://")):
            return source
        return storage.presigned_url(source)

    @staticmethod
    def _extract_audio_url(result: Dict[str, Any]) -> Optional[str]:
        if result.get("audio_url"):
            return result["audio_url"]
        if result.get("url"):
            return result["url"]
        output = result.get("output")
        if isinstance(output, list) and output:
            first = output[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                return first.get("audio_url") or first.get("url")
        if isinstance(output, dict):
            return output.get("audio_url") or output.get("url") or output.get("output_url")
        return None

    def _safe_error(self, exc: Exception) -> str:
        message = str(exc) or exc.__class__.__name__
        for secret in (
            getattr(settings, "MODELSLAB_API_KEY", None),
            getattr(settings, "PIAPI_API_KEY_LITINKAI", None),
            getattr(settings, "ELEVENLABS_API_KEY", None),
            getattr(self.piapi, "api_key", None),
            getattr(self.modelslab_service, "api_key", None),
        ):
            if secret:
                message = message.replace(str(secret), "***")
        return message

    def _all_failed(
        self, operation: str, errors: list[str], attempted_models: list[str]
    ) -> Dict[str, Any]:
        error = "; ".join(errors) if errors else "No supported providers attempted"
        error = self._safe_error(RuntimeError(error))
        logger.error("[PiAPI audio adapter] All %s providers failed: %s", operation, error)
        return {
            "status": "error",
            "error": error,
            "attempted_models": attempted_models,
        }


piapi_audio_adapter = PiAPIAudioAdapter()
