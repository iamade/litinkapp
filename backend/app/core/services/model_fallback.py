import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List

from app.core.model_config import get_model_config
from app.core.services.provider_router import (
    ProviderNotConfiguredError,
    ProviderSkipError,
    provider_name_for_model,
)
from app.core.services.redis import redis_client

logger = logging.getLogger(__name__)

PROVIDER_COOLDOWN_SECONDS = 60 * 60


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failures: Dict[str, List[datetime]] = {}

    def record_failure(self, model_name: str) -> None:
        now = datetime.now()
        failures = self.failures.setdefault(model_name, [])
        failures.append(now)
        cutoff = now - timedelta(seconds=self.timeout_seconds)
        self.failures[model_name] = [
            failure for failure in failures if failure > cutoff
        ]

    def is_open(self, model_name: str) -> bool:
        cutoff = datetime.now() - timedelta(seconds=self.timeout_seconds)
        recent = [
            failure for failure in self.failures.get(model_name, []) if failure > cutoff
        ]
        return len(recent) >= self.failure_threshold

    def reset(self, model_name: str) -> None:
        self.failures.pop(model_name, None)


class ModelFallbackManager:
    def __init__(self, redis_service=redis_client, sleep=asyncio.sleep):
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=60)
        self.redis = redis_service
        self.sleep = sleep
        self.local_cooldowns: Dict[str, float] = {}

    async def _ensure_redis(self) -> None:
        if not getattr(self.redis, "is_connected", False):
            await self.redis.connect()

    @staticmethod
    def cooldown_key(provider: str) -> str:
        return f"provider:{provider}:cooldown_until"

    async def _cooldown_until(self, provider: str) -> float | None:
        local_until = self.local_cooldowns.get(provider)
        if local_until:
            if local_until > time.time():
                return local_until
            self.local_cooldowns.pop(provider, None)
        try:
            await self._ensure_redis()
            value = await self.redis.get(self.cooldown_key(provider))
            if value is None:
                return None
            cooldown_until = float(value)
            if cooldown_until <= time.time():
                await self.redis.delete(self.cooldown_key(provider))
                return None
            return cooldown_until
        except Exception as exc:
            logger.warning("[FALLBACK] Redis cooldown read failed open: %s", exc)
            return None

    async def _set_cooldown(self, provider: str) -> None:
        cooldown_until = time.time() + PROVIDER_COOLDOWN_SECONDS
        self.local_cooldowns[provider] = cooldown_until
        try:
            await self._ensure_redis()
            await self.redis.set(
                self.cooldown_key(provider),
                str(cooldown_until),
                expire=PROVIDER_COOLDOWN_SECONDS,
            )
            logger.warning(
                "[FALLBACK] Provider %s cooling down for %s seconds",
                provider,
                PROVIDER_COOLDOWN_SECONDS,
            )
        except Exception as exc:
            logger.warning("[FALLBACK] Redis cooldown write failed open: %s", exc)

    @staticmethod
    def _status_code(error: Exception) -> int | None:
        status_code = getattr(error, "status_code", None)
        if status_code is None and getattr(error, "response", None) is not None:
            status_code = getattr(error.response, "status_code", None)
        if status_code in {429, 503}:
            return status_code
        text = str(error).lower()
        if "429" in text or "rate limit" in text or "too many requests" in text:
            return 429
        if "503" in text or "service unavailable" in text:
            return 503
        return None

    @staticmethod
    def _is_timeout(error: Exception) -> bool:
        text = str(error).lower()
        return any(token in text for token in ("timed out", "timeout", "time out"))

    async def try_with_fallback(
        self,
        service_type: str,
        user_tier: str,
        generation_function: Callable,
        request_params: Dict[str, Any],
        model_param_name: str = "model_id",
    ) -> Dict[str, Any]:
        tier_normalized = user_tier.lower() if user_tier else "free"
        config = get_model_config(service_type, tier_normalized)
        if not config:
            logger.error(
                "No model config found for %s/%s, using request defaults",
                service_type,
                tier_normalized,
            )
            return await generation_function(**request_params)

        return await self._try_models(
            models=config.models,
            generation_function=generation_function,
            request_params=request_params,
            model_param_name=model_param_name,
            service_type=service_type,
            tier=tier_normalized,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )

    async def _try_models(
        self,
        models: List[str],
        generation_function: Callable,
        request_params: Dict[str, Any],
        model_param_name: str,
        service_type: str,
        tier: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Dict[str, Any]:
        attempted_models: List[Dict[str, Any]] = []
        last_error: Exception | None = None
        actual_attempts = 0

        for index, model in enumerate(models):
            provider = provider_name_for_model(model)
            model_type = "primary" if index == 0 else f"fallback{index}"

            cooldown_until = (
                await self._cooldown_until(provider) if provider != "unknown" else None
            )
            if cooldown_until:
                attempted_models.append(
                    {
                        "model": model,
                        "status": "skipped",
                        "reason": "provider_cooldown",
                        "provider": provider,
                    }
                )
                continue

            if self.circuit_breaker.is_open(model):
                attempted_models.append(
                    {"model": model, "status": "skipped", "reason": "circuit_breaker"}
                )
                continue

            updated_params = dict(request_params)
            updated_params[model_param_name] = model
            if service_type == "script" and max_tokens:
                updated_params["max_tokens"] = max_tokens
            if service_type == "script" and temperature is not None:
                updated_params["temperature"] = temperature

            try:
                logger.info(
                    "[FALLBACK] Attempting %s model %s for %s/%s",
                    model_type,
                    model,
                    service_type,
                    tier or "n/a",
                )
                actual_attempts += 1
                result = await generation_function(**updated_params)
                if not result or result.get("status") not in {"success", "processing"}:
                    error = (
                        result.get("error", "Unknown error") if result else "No result"
                    )
                    raise RuntimeError(f"Generation failed: {error}")

                self.circuit_breaker.reset(model)
                result.setdefault("model_used", model)
                result["model_tier_used"] = model_type
                if tier:
                    result["tier"] = tier
                result["attempted_models"] = attempted_models + [
                    {"model": model, "status": "success", "provider": provider}
                ]
                result["attempts"] = actual_attempts
                return result

            except ProviderSkipError as exc:
                actual_attempts -= 1
                logger.info("[ScriptModelRouter] featherless skipped (sub lapsed)")
                attempted_models.append(
                    {
                        "model": model,
                        "status": "skipped",
                        "reason": "provider_soft_skip",
                        "error": str(exc),
                    }
                )
                continue
            except ProviderNotConfiguredError as exc:
                actual_attempts -= 1
                logger.info("[FALLBACK] Provider not configured for %s: %s", model, exc)
                attempted_models.append(
                    {
                        "model": model,
                        "status": "skipped",
                        "reason": "provider_not_configured",
                        "error": str(exc),
                    }
                )
                last_error = exc
                continue
            except Exception as exc:
                last_error = exc
                self.circuit_breaker.record_failure(model)
                status_code = self._status_code(exc)
                attempted_models.append(
                    {
                        "model": model,
                        "status": "failed",
                        "provider": provider,
                        "error": str(exc) or repr(exc),
                        "status_code": status_code,
                        "model_type": model_type,
                    }
                )
                if status_code in {429, 503} and provider != "unknown":
                    await self._set_cooldown(provider)

                # Preserve the existing safety rule for requests that may still be
                # processing at the provider. Retrying could double-bill or duplicate
                # media generation.
                if self._is_timeout(exc):
                    break

                if index < len(models) - 1 and status_code not in {429, 503}:
                    await self.sleep(min(2**index, 3))

        logger.error(
            "[FALLBACK] All models failed for %s/%s", service_type, tier or "n/a"
        )
        return {
            "status": "error",
            "error": f"All models failed. Last error: {last_error}",
            "attempted_models": attempted_models,
            "attempts": actual_attempts,
            "tier": tier,
            "service_type": service_type,
        }

    async def try_model_list_with_fallback(
        self,
        models: List[str],
        generation_function: Callable,
        request_params: Dict[str, Any],
        model_param_name: str = "model_id",
        service_type: str = "generic",
    ) -> Dict[str, Any]:
        return await self._try_models(
            models=models,
            generation_function=generation_function,
            request_params=request_params,
            model_param_name=model_param_name,
            service_type=service_type,
        )


fallback_manager = ModelFallbackManager()
