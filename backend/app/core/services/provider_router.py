import logging
from types import SimpleNamespace
from typing import Any, Tuple

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.services.redis import redis_client

logger = logging.getLogger(__name__)


class ProviderNotConfiguredError(RuntimeError):
    """A model prefix is known, but its provider is not configured."""


class ProviderSkipError(RuntimeError):
    """A provider is intentionally unavailable and should be skipped for free."""


def provider_name_for_model(model: str) -> str:
    prefix, separator, _ = model.partition("/")
    return prefix if separator else "unknown"


class ProviderRouter:
    """Route prefixed script models to explicit provider adapters."""

    def __init__(self) -> None:
        self.ollama_client = self._openai_client(
            settings.OLLAMA_API_KEY, settings.OLLAMA_BASE_URL
        )
        self.zai_client = self._openai_client(
            settings.Z_AI_API_KEY or settings.ZAI_API_KEY, settings.Z_AI_BASE_URL
        )
        self.google_client = self._openai_client(
            settings.GOOGLE_AI_STUDIO_API_KEY,
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.groq_client = self._openai_client(
            settings.GROQ_API_KEY, settings.GROQ_BASE_URL
        )
        self.openai_client = self._openai_client(
            settings.OPENAI_API_KEY, "https://api.openai.com/v1"
        )
        self.piapi_client = self._openai_client(
            settings.PIAPI_API_KEY_LITINKAI, settings.PIAPI_BASE_URL
        )
        self.featherless_client = self._openai_client(
            settings.FEATHERLESS_API_KEY_LITINKAI, settings.FEATHERLESS_BASE_URL
        )
        self.anthropic_client = (
            AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            if settings.ANTHROPIC_API_KEY
            else None
        )

    @staticmethod
    def _openai_client(api_key: str | None, base_url: str | None) -> AsyncOpenAI | None:
        if not api_key or not base_url:
            return None
        return AsyncOpenAI(api_key=api_key, base_url=base_url)

    def get_client_and_model(
        self, model: str, featherless_active: bool | None = None
    ) -> Tuple[Any, str]:
        """Return the explicitly configured client and prefix-stripped model ID."""
        provider = provider_name_for_model(model)
        resolved = model.split("/", 1)[1] if "/" in model else model

        if (
            provider == "featherless"
            and featherless_active is not True
            and not settings.FEATHERLESS_SUB_ACTIVE
        ):
            raise ProviderSkipError("featherless sub lapsed, awaiting renewal")

        client = {
            "ollama": self.ollama_client,
            "zai": self.zai_client,
            "google": self.google_client,
            "groq": self.groq_client,
            "openai": self.openai_client,
            "piapi": self.piapi_client,
            "featherless": self.featherless_client,
            "anthropic": self.anthropic_client,
        }.get(provider)

        if provider not in {
            "ollama",
            "zai",
            "google",
            "groq",
            "openai",
            "piapi",
            "featherless",
            "anthropic",
        }:
            raise ProviderNotConfiguredError(f"No adapter for prefix {provider}")
        if client is None:
            env_name = {
                "ollama": "OLLAMA_API_KEY",
                "zai": "Z_AI_API_KEY",
                "google": "GOOGLE_AI_STUDIO_API_KEY",
                "groq": "GROQ_API_KEY",
                "openai": "OPENAI_API_KEY",
                "piapi": "PIAPI_API_KEY_LITINKAI",
                "featherless": "FEATHERLESS_API_KEY_LITINKAI",
                "anthropic": "ANTHROPIC_API_KEY",
            }[provider]
            raise ProviderNotConfiguredError(f"{env_name} missing")

        logger.info(
            "[ProviderRouter] Routing %s to %s as %s", model, provider, resolved
        )
        return client, resolved

    async def _featherless_active(self) -> bool:
        if settings.FEATHERLESS_SUB_ACTIVE:
            return True
        try:
            if not redis_client.is_connected:
                await redis_client.connect()
            redis_override = await redis_client.get("provider:featherless:sub_active")
            return redis_override in (True, 1, "1", "true", "True")
        except Exception as exc:
            logger.warning("[ProviderRouter] Featherless re-arm check failed: %s", exc)
            return False

    async def chat_completion(self, model: str, messages: list, **kwargs) -> Any:
        """Route a chat completion and normalize Anthropic to the OpenAI shape."""
        featherless_active = None
        if model.startswith("featherless/"):
            featherless_active = await self._featherless_active()
            if not featherless_active:
                raise ProviderSkipError("featherless sub lapsed, awaiting renewal")

        client, resolved_model = self.get_client_and_model(
            model, featherless_active=featherless_active
        )
        if model.startswith("anthropic/"):
            return await self._anthropic_chat_completion(
                client, resolved_model, messages, **kwargs
            )
        return await client.chat.completions.create(
            model=resolved_model, messages=messages, **kwargs
        )

    @staticmethod
    async def _anthropic_chat_completion(
        client: AsyncAnthropic, model: str, messages: list, **kwargs
    ) -> Any:
        request_kwargs = dict(kwargs)
        request_kwargs.pop("stream", None)
        system = "\n\n".join(
            str(message.get("content", ""))
            for message in messages
            if message.get("role") == "system"
        )
        anthropic_messages = [
            {
                "role": message.get("role", "user"),
                "content": message.get("content", ""),
            }
            for message in messages
            if message.get("role") in {"user", "assistant"}
        ]
        if system:
            request_kwargs["system"] = system

        response = await client.messages.create(
            model=model,
            messages=anthropic_messages,
            **request_kwargs,
        )
        content = "".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        )
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            raw_response=response,
        )


provider_router = ProviderRouter()
