from typing import Any, Tuple
from openai import AsyncOpenAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Routes model requests to the correct provider based on model prefix.

    Routing rules:
        ollama/  → Ollama Cloud API (strip prefix)
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
        if settings.OLLAMA_CLOUD_API_KEY:
            self.ollama_client = AsyncOpenAI(
                api_key=settings.OLLAMA_CLOUD_API_KEY,
                base_url=settings.OLLAMA_CLOUD_BASE_URL,
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
            resolved = model[len("ollama/"):]
            logger.info(f"[ProviderRouter] Routing {model} → Ollama Cloud as {resolved}")
            return self.ollama_client, resolved

        if model.startswith("google/") and self.google_client:
            resolved = model[len("google/"):]
            logger.info(f"[ProviderRouter] Routing {model} → Google AI Studio as {resolved}")
            return self.google_client, resolved

        if model.startswith("groq/") and self.groq_client:
            resolved = model[len("groq/"):]
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
