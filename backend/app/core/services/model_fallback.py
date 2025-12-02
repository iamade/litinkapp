from typing import Dict, Any, Callable, Optional, List
import asyncio
import logging
from datetime import datetime, timedelta
from app.core.model_config import get_model_config, ModelTier

logger = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failures: Dict[str, List[datetime]] = {}

    def record_failure(self, model_name: str):
        if model_name not in self.failures:
            self.failures[model_name] = []

        now = datetime.now()
        self.failures[model_name].append(now)

        cutoff = now - timedelta(seconds=self.timeout_seconds)
        self.failures[model_name] = [
            f for f in self.failures[model_name] if f > cutoff
        ]

    def is_open(self, model_name: str) -> bool:
        if model_name not in self.failures:
            return False

        now = datetime.now()
        cutoff = now - timedelta(seconds=self.timeout_seconds)
        recent_failures = [f for f in self.failures[model_name] if f > cutoff]

        return len(recent_failures) >= self.failure_threshold

    def reset(self, model_name: str):
        if model_name in self.failures:
            self.failures[model_name] = []


class ModelFallbackManager:
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=60)

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
                f"No model config found for {service_type}/{tier_normalized}, using defaults"
            )
            return await generation_function(**request_params)

        models_to_try = [config.primary]
        if config.fallback:
            models_to_try.append(config.fallback)
        if config.fallback2:
            models_to_try.append(config.fallback2)

        attempted_models = []
        last_error = None

        for i, model in enumerate(models_to_try):
            if self.circuit_breaker.is_open(model):
                logger.warning(
                    f"[FALLBACK] Circuit breaker open for {model}, skipping"
                )
                attempted_models.append(
                    {"model": model, "status": "skipped", "reason": "circuit_breaker"}
                )
                continue

            model_type = "primary" if i == 0 else f"fallback{i if i == 1 else '2'}"

            try:
                logger.info(
                    f"[FALLBACK] Attempting {model_type} model: {model} for {service_type}/{tier_normalized}"
                )

                updated_params = request_params.copy()
                updated_params[model_param_name] = model

                if service_type == "script" and config.max_tokens:
                    updated_params["max_tokens"] = config.max_tokens
                if service_type == "script" and config.temperature:
                    updated_params["temperature"] = config.temperature

                result = await generation_function(**updated_params)

                if result and result.get("status") in ["success", "processing"]:
                    logger.info(
                        f"[FALLBACK] ✅ Success with {model_type} model: {model}"
                    )

                    self.circuit_breaker.reset(model)

                    if "model_used" not in result:
                        result["model_used"] = model
                    result["model_tier_used"] = model_type
                    result["tier"] = tier_normalized
                    result["attempted_models"] = attempted_models + [
                        {"model": model, "status": "success"}
                    ]

                    return result
                else:
                    error_msg = result.get("error", "Unknown error") if result else "No result"
                    raise Exception(f"Generation failed: {error_msg}")

            except Exception as e:
                error_msg = str(e) if str(e) else repr(e)
                logger.error(
                    f"[FALLBACK] ❌ {model_type} model {model} failed: {error_msg}"
                )

                self.circuit_breaker.record_failure(model)

                attempted_models.append(
                    {
                        "model": model,
                        "status": "failed",
                        "error": error_msg,
                        "model_type": model_type,
                    }
                )
                last_error = e

                if i < len(models_to_try) - 1:
                    backoff_time = 2**i
                    logger.info(
                        f"[FALLBACK] Waiting {backoff_time}s before trying next model"
                    )
                    await asyncio.sleep(backoff_time)

        logger.error(
            f"[FALLBACK] All models failed for {service_type}/{tier_normalized}"
        )

        return {
            "status": "error",
            "error": f"All models failed. Last error: {str(last_error)}",
            "attempted_models": attempted_models,
            "tier": tier_normalized,
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
        attempted_models = []
        last_error = None

        for i, model in enumerate(models):
            if self.circuit_breaker.is_open(model):
                logger.warning(
                    f"[FALLBACK] Circuit breaker open for {model}, skipping"
                )
                attempted_models.append(
                    {"model": model, "status": "skipped", "reason": "circuit_breaker"}
                )
                continue

            model_type = "primary" if i == 0 else f"fallback{i}"

            try:
                logger.info(
                    f"[FALLBACK] Attempting {model_type} model: {model} for {service_type}"
                )

                updated_params = request_params.copy()
                updated_params[model_param_name] = model

                result = await generation_function(**updated_params)

                if result and result.get("status") in ["success", "processing"]:
                    logger.info(
                        f"[FALLBACK] ✅ Success with {model_type} model: {model}"
                    )

                    self.circuit_breaker.reset(model)

                    if "model_used" not in result:
                        result["model_used"] = model
                    result["model_tier_used"] = model_type
                    result["attempted_models"] = attempted_models + [
                        {"model": model, "status": "success"}
                    ]

                    return result
                else:
                    error_msg = result.get("error", "Unknown error") if result else "No result"
                    raise Exception(f"Generation failed: {error_msg}")

            except Exception as e:
                error_msg = str(e) if str(e) else repr(e)
                logger.error(
                    f"[FALLBACK] ❌ {model_type} model {model} failed: {error_msg}"
                )

                self.circuit_breaker.record_failure(model)

                attempted_models.append(
                    {
                        "model": model,
                        "status": "failed",
                        "error": error_msg,
                        "model_type": model_type,
                    }
                )
                last_error = e

                if i < len(models) - 1:
                    backoff_time = 2**i
                    logger.info(
                        f"[FALLBACK] Waiting {backoff_time}s before trying next model"
                    )
                    await asyncio.sleep(backoff_time)

        logger.error(f"[FALLBACK] All models failed for {service_type}")

        return {
            "status": "error",
            "error": f"All models failed. Last error: {str(last_error)}",
            "attempted_models": attempted_models,
            "service_type": service_type,
        }


fallback_manager = ModelFallbackManager()
