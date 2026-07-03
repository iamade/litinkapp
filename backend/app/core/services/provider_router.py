from typing import Any, Tuple
from openai import AsyncOpenAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Routes model requests to the correct provider based on model prefix.

    Routing rules:
        ollama/  → Ollama Cloud API (strip prefix)
        zai/     → Z.AI OpenAI-compatible API (strip prefix)
        piapi/   → PiAPI OpenAI-compatible API (strip prefix)
        featherless/ → Featherless OpenAI-compatible API (strip prefix)
        google/  → Google AI Studio (strip prefix)
        groq/    → Groq (strip prefix)
        *        → OpenRouter (keep full model string)
    """

    def __init__(self):
        # OpenRouter (default, handles most models)
        self.openrouter_client = None
        if settings.OPENROUTER_API_KEY:
            self.openrouter_client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
            )

        # Ollama Cloud API (for ollama/ prefixed models)
        self.ollama_client = None
        if settings.OLLAMA_API_KEY:
            self.ollama_client = AsyncOpenAI(
                api_key=settings.OLLAMA_API_KEY,
                base_url=settings.OLLAMA_BASE_URL,
            )

        # Z.AI (OpenAI-compatible, for zai/ prefixed models)
        self.zai_client = None
        if settings.z_ai_api_key:
            self.zai_client = AsyncOpenAI(
                api_key=settings.z_ai_api_key,
                base_url=settings.Z_AI_BASE_URL,
            )

        # PiAPI (OpenAI-compatible, for piapi/ prefixed models)
        self.piapi_client = None
        if settings.piapi_api_key:
            self.piapi_client = AsyncOpenAI(
                api_key=settings.piapi_api_key,
                base_url=settings.PIAPI_BASE_URL,
            )

        # Featherless (OpenAI-compatible, for featherless/ prefixed models)
        self.featherless_client = None
        if settings.featherless_api_key:
            self.featherless_client = AsyncOpenAI(
                api_key=settings.featherless_api_key,
                base_url=settings.FEATHERLESS_BASE_URL,
            )

        # Google AI Studio (direct, for google/ prefixed models)
        self.google_client = None
        if settings.GOOGLE_AI_STUDIO_API_KEY:
            self.google_client = AsyncOpenAI(
                api_key=settings.GOOGLE_AI_STUDIO_API_KEY,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )

        # Groq (direct, for groq/ prefixed models)
        self.groq_client = None
        if settings.GROQ_API_KEY:
            self.groq_client = AsyncOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
            )

    def get_client_and_model(self, model: str) -> Tuple[AsyncOpenAI, str]:
        """Returns (client, resolved_model) based on model prefix."""
        if model.startswith("ollama/") and self.ollama_client:
            resolved = model[len("ollama/") :]
            logger.info(
                f"[ProviderRouter] Routing {model} → Ollama Cloud as {resolved}"
            )
            return self.ollama_client, resolved

        if model.startswith("zai/"):
            if self.zai_client:
                resolved = model[len("zai/") :]
                logger.info(f"[ProviderRouter] Routing {model} → Z.AI as {resolved}")
                return self.zai_client, resolved
            raise ValueError(
                f"Z.AI routing unavailable for model '{model}'. "
                "Z_AI_API_KEY is not configured."
            )

        if model.startswith("piapi/"):
            if self.piapi_client:
                resolved = model[len("piapi/") :]
                logger.info(f"[ProviderRouter] Routing {model} → PiAPI as {resolved}")
                return self.piapi_client, resolved
            raise ValueError(
                f"PiAPI routing unavailable for model '{model}'. "
                "PIAPI_API_KEY_LITINKAI is not configured."
            )

        if model.startswith("featherless/"):
            if self.featherless_client:
                resolved = model[len("featherless/") :]
                logger.info(
                    f"[ProviderRouter] Routing {model} → Featherless as {resolved}"
                )
                return self.featherless_client, resolved
            raise ValueError(
                f"Featherless routing unavailable for model '{model}'. "
                "FEATHERLESS_API_KEY_LITINKAI is not configured."
            )

        if model.startswith("google/") and self.google_client:
            resolved = model[len("google/") :]
            logger.info(
                f"[ProviderRouter] Routing {model} → Google AI Studio as {resolved}"
            )
            return self.google_client, resolved

        if model.startswith("groq/") and self.groq_client:
            resolved = model[len("groq/") :]
            logger.info(f"[ProviderRouter] Routing {model} → Groq as {resolved}")
            return self.groq_client, resolved

        # Default: OpenRouter (keeps full model string including any prefix)
        if not self.openrouter_client:
            raise ValueError(
                f"No provider available for model '{model}'. "
                "OpenRouter API key is not configured."
            )
        logger.info(f"[ProviderRouter] Routing {model} → OpenRouter")
        return self.openrouter_client, model

    async def chat_completion(self, model: str, messages: list, **kwargs) -> Any:
        """Route a chat completion to the correct provider."""
        client, resolved_model = self.get_client_and_model(model)
        return await client.chat.completions.create(
            model=resolved_model, messages=messages, **kwargs
        )


# Module-level singleton
provider_router = ProviderRouter()
