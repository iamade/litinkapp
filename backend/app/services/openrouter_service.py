from typing import Dict, Any, Optional, List
import httpx
from openai import AsyncOpenAI
from app.core.config import settings
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class ModelTier(Enum):
    FREE = "free"
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    PROFESSIONAL = "professional"

class OpenRouterService:
    """
    OpenRouter integration for intelligent model routing
    Handles all LLM requests with automatic fallback and cost optimization
    """

    # Model configurations with costs (per 1K tokens)
    MODEL_CONFIGS = {
        ModelTier.FREE: {
            "primary": "ArliAI: QwQ 32B RpR v1",
            "fallback": "meta-llama/llama-3.2-3b-instruct",
            "max_tokens": 2000,
            "temperature": 0.7,
            "cost_per_1k_input": 0.00006,
            "cost_per_1k_output": 0.00006
        },
        ModelTier.BASIC: {
            "primary": "deepseek-chat-v3-0324:free",
            "fallback": "mistralai/mistral-7b-instruct",
            "max_tokens": 3000,
            "temperature": 0.7,
            "cost_per_1k_input": 0.00014,
            "cost_per_1k_output": 0.00028
        },
        ModelTier.STANDARD: {
            "primary": "anthropic/claude-3-haiku-20240307",
            "fallback": "openai/gpt-3.5-turbo",
            "max_tokens": 4000,
            "temperature": 0.7,
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.00125
        },
        ModelTier.PREMIUM: {
            "primary": "openai/gpt-4o-mini",
            "fallback": "anthropic/claude-3.5-sonnet",
            "max_tokens": 8000,
            "temperature": 0.7,
            "cost_per_1k_input": 0.00015,
            "cost_per_1k_output": 0.00060
        },
        ModelTier.PROFESSIONAL: {
            "primary": "openai/gpt-4o",
            "fallback": "anthropic/claude-3-opus-20240229",
            "max_tokens": 16000,
            "temperature": 0.8,
            "cost_per_1k_input": 0.00250,
            "cost_per_1k_output": 0.01000
        }
    }

    def __init__(self):
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is required")

        self.client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": settings.FRONTEND_URL,  # Optional, for rankings
                "X-Title": "LitinkAI"  # Optional, shows in OpenRouter dashboard
            }
        )

        # Initialize cost tracking
        self.cost_tracker = CostTracker()

    async def generate_script(
        self,
        content: str,
        user_tier: ModelTier,
        script_type: str = "cinematic",
        use_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Generate script using tier-appropriate model
        """
        config = self.MODEL_CONFIGS[user_tier]
        model = config["fallback"] if use_fallback else config["primary"]

        try:
            # Prepare messages based on script type
            messages = self._prepare_script_messages(content, script_type)

            # Log the request
            logger.info(f"[OpenRouter] Generating {script_type} script with {model} for {user_tier.value} tier")

            # Make the API call
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=config["max_tokens"],
                temperature=config["temperature"],
                stream=False
            )

            # Extract content and usage
            generated_content = response.choices[0].message.content
            usage = response.usage

            # Calculate cost
            input_cost = (usage.prompt_tokens / 1000) * config["cost_per_1k_input"]
            output_cost = (usage.completion_tokens / 1000) * config["cost_per_1k_output"]
            total_cost = input_cost + output_cost

            # Track the cost
            await self.cost_tracker.track(
                user_tier=user_tier,
                model=model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                cost=total_cost
            )

            return {
                "status": "success",
                "content": generated_content,
                "model_used": model,
                "tier": user_tier.value,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "estimated_cost": total_cost
                }
            }

        except Exception as e:
            logger.error(f"[OpenRouter] Error with {model}: {str(e)}")

            # Try fallback if not already using it
            if not use_fallback:
                logger.info(f"[OpenRouter] Attempting fallback model")
                return await self.generate_script(
                    content=content,
                    user_tier=user_tier,
                    script_type=script_type,
                    use_fallback=True
                )

            # If fallback also failed, return error
            return {
                "status": "error",
                "error": str(e),
                "model_attempted": model,
                "tier": user_tier.value
            }

    def _prepare_script_messages(self, content: str, script_type: str) -> List[Dict[str, str]]:
        """
        Prepare messages for different script types
        """
        system_prompts = {
            "cinematic": """You are a professional screenwriter. Convert the provided content into a cinematic screenplay format with:
                - Proper scene headings (INT./EXT. LOCATION - TIME)
                - Character names in uppercase when introduced
                - Dialogue and action descriptions
                - Visual descriptions for scene generation""",

            "narration": """You are a professional narrator. Convert the content into an engaging narration script with:
                - Rich, descriptive voice-over text
                - Scene descriptions for visual context
                - Emotional and atmospheric descriptions
                - Clear pacing and transitions""",

            "educational": """You are an educational content creator. Convert the content into a clear, educational script with:
                - Clear learning objectives
                - Step-by-step explanations
                - Visual cues for graphics and demonstrations
                - Engaging but informative tone""",

            "marketing": """You are a marketing copywriter. Convert the content into a compelling marketing script with:
                - Hook in the first 3 seconds
                - Clear value proposition
                - Call-to-action
                - Emotional engagement"""
        }

        system_prompt = system_prompts.get(script_type, system_prompts["cinematic"])

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Convert this content into a {script_type} script:\n\n{content}"}
        ]

    async def analyze_content(
        self,
        content: str,
        user_tier: ModelTier,
        analysis_type: str = "summary"
    ) -> Dict[str, Any]:
        """
        Analyze content for various purposes (summary, keywords, difficulty, etc.)
        """
        config = self.MODEL_CONFIGS[user_tier]
        model = config["primary"]

        analysis_prompts = {
            "summary": "Provide a concise summary of this content in 2-3 sentences.",
            "keywords": "Extract 5-10 key topics or themes from this content.",
            "difficulty": "Assess the reading difficulty level of this content (elementary, middle school, high school, college, professional).",
            "genre": "Identify the genre and style of this content.",
            "characters": "List all characters mentioned in this content with brief descriptions."
        }

        prompt = analysis_prompts.get(analysis_type, analysis_prompts["summary"])

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a content analyst."},
                    {"role": "user", "content": f"{prompt}\n\nContent:\n{content[:3000]}"}  # Limit content for analysis
                ],
                max_tokens=500,
                temperature=0.3  # Lower temperature for analysis
            )

            return {
                "status": "success",
                "analysis_type": analysis_type,
                "result": response.choices[0].message.content,
                "model_used": model
            }

        except Exception as e:
            logger.error(f"[OpenRouter] Analysis error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "analysis_type": analysis_type
            }

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get list of available models from OpenRouter
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}
                )

                if response.status_code == 200:
                    models = response.json()["data"]
                    # Filter and format models
                    return [
                        {
                            "id": model["id"],
                            "name": model.get("name", model["id"]),
                            "context_length": model.get("context_length", 4096),
                            "pricing": model.get("pricing", {}),
                            "supported": model["id"] in [
                                config["primary"] for config in self.MODEL_CONFIGS.values()
                            ]
                        }
                        for model in models
                    ]
                else:
                    logger.error(f"Failed to fetch models: {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching available models: {str(e)}")
            return []


class CostTracker:
    """
    Track costs for OpenRouter API usage
    """

    def __init__(self):
        self.redis_client = None  # Initialize with Redis connection
        self.supabase_client = None  # Initialize with Supabase connection

    async def track(
        self,
        user_tier: ModelTier,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ):
        """
        Track API usage and costs
        """
        # Store in database for billing
        # This is a simplified version - expand based on your needs
        logger.info(f"[Cost Tracking] Model: {model}, Tokens: {input_tokens + output_tokens}, Cost: ${cost:.6f}")

        # You would typically:
        # 1. Store in database
        # 2. Update user's usage quota
        # 3. Check against limits
        # 4. Send alerts if needed