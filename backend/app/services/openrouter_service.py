from typing import Dict, Any, Optional, List
import httpx
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from app.core.config import settings
from app.core.model_config import ModelTier, SCRIPT_MODEL_CONFIG, get_model_config
from app.services.model_fallback_manager import fallback_manager
import logging

logger = logging.getLogger(__name__)


class OpenRouterService:
    """
    OpenRouter integration for intelligent model routing
    Handles all LLM requests with automatic fallback and cost optimization
    Uses centralized model configuration and fallback manager
    """

    def __init__(self):
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is required")

        self.client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": settings.FRONTEND_URL,  # Optional, for rankings
                "X-Title": "LitinkAI",  # Optional, shows in OpenRouter dashboard
            },
        )

        # Initialize cost tracking
        self.cost_tracker = CostTracker()

    async def generate_script(
        self,
        content: str,
        user_tier: ModelTier,
        script_type: str = "cinematic",
        target_duration: Optional[int] = None,
        plot_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate script using tier-appropriate model with automatic fallback
        """
        tier_str = user_tier.value if isinstance(user_tier, ModelTier) else str(user_tier)

        config = get_model_config("script", tier_str)
        if not config:
            logger.warning(f"No config for tier {tier_str}, using FREE tier defaults")
            config = get_model_config("script", "free")

        async def _generate_with_model(model: str, **kwargs) -> Dict[str, Any]:
            return await self._execute_generation(
                model=model,
                content=content,
                script_type=script_type,
                target_duration=target_duration,
                plot_context=plot_context,
                config=config,
                tier_str=tier_str
            )

        return await fallback_manager.try_with_fallback(
            service_type="script",
            user_tier=tier_str,
            generation_function=_generate_with_model,
            request_params={"model": config.primary},
            model_param_name="model"
        )

    async def _execute_generation(
        self,
        model: str,
        content: str,
        script_type: str,
        target_duration: Optional[int],
        plot_context: Optional[Dict[str, Any]],
        config: Any,
        tier_str: str
    ) -> Dict[str, Any]:
        """
        Execute the actual script generation with specified model
        """

        # Prepare messages based on script type
        messages = self._prepare_script_messages(
            content, script_type, target_duration, plot_context
        )

        # Log the request
        logger.info(
            f"[OpenRouter] Generating {script_type} script with {model} for tier {tier_str}"
        )

        # Make the API call
        create_fn: Any = getattr(self.client.chat.completions, "create")
        response = await create_fn(
            model=model,
            messages=messages,
            max_tokens=config.max_tokens if config.max_tokens else 4000,
            temperature=config.temperature if config.temperature else 0.7,
            stream=False,
        )

        # Handle OpenAI client response (should always be parsed)
        try:
            # Check if response is properly parsed
            if hasattr(response, "choices") and response.choices:
                generated_content = response.choices[0].message.content
                usage_raw = response.usage
                logger.info(
                    f"[OpenRouter] Successfully parsed response for {model}"
                )
            else:
                # Fallback: try to parse as JSON string if response is raw
                if hasattr(response, "json"):
                    try:
                        parsed_response = response.json()
                        if isinstance(parsed_response, str):
                            # If json() returns a string, it might be double-encoded
                            import json

                            parsed_response = json.loads(parsed_response)
                        generated_content = parsed_response["choices"][0][
                            "message"
                        ]["content"]
                        usage_raw = parsed_response["usage"]
                        logger.info(
                            f"[OpenRouter] Parsed raw JSON response for {model}"
                        )
                    except Exception as json_error:
                        logger.error(
                            f"[OpenRouter] Failed to parse JSON response: {str(json_error)}"
                        )
                        raise ValueError(
                            f"Failed to parse JSON API response: {str(json_error)}"
                        )
                else:
                    raise ValueError(
                        "Invalid response format: no choices or json method available"
                    )
        except Exception as e:
            logger.error(
                f"[OpenRouter] Failed to parse response for {model}: {str(e)}"
            )
            raise ValueError(f"Failed to parse API response: {str(e)}")

        # Normalize usage to dict for consistent access
        if isinstance(usage_raw, dict):
            usage = usage_raw
        else:
            usage = {
                "prompt_tokens": usage_raw.prompt_tokens,
                "completion_tokens": usage_raw.completion_tokens,
                "total_tokens": usage_raw.total_tokens,
            }

        # Clean narrator elements from cinematic scripts
        if script_type == "cinematic_movie":
            # delegate cleaning to CostTracker which defines the helper
            generated_content = (
                self.cost_tracker._clean_narrator_from_cinematic_script(
                    generated_content
                )
            )

        # Calculate cost
        cost_per_1k_input = config.cost_per_1k_input if config.cost_per_1k_input else 0.0
        cost_per_1k_output = config.cost_per_1k_output if config.cost_per_1k_output else 0.0
        input_cost = (usage["prompt_tokens"] / 1000) * cost_per_1k_input
        output_cost = (usage["completion_tokens"] / 1000) * cost_per_1k_output
        total_cost = input_cost + output_cost

        # Track the cost
        tier_enum = ModelTier(tier_str) if tier_str in [t.value for t in ModelTier] else ModelTier.FREE
        await self.cost_tracker.track(
            user_tier=tier_enum,
            model=model,
            input_tokens=usage["prompt_tokens"],
            output_tokens=usage["completion_tokens"],
            cost=total_cost,
        )

        return {
            "status": "success",
            "content": generated_content,
            "model_used": model,
            "tier": tier_str,
            "usage": {
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"],
                "total_tokens": usage["total_tokens"],
                "estimated_cost": total_cost,
            },
        }

    def _prepare_script_messages(
        self,
        content: str,
        script_type: str,
        target_duration: Optional[int] = None,
        plot_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """
        Prepare messages for different script types
        """
        system_prompts = {
            "cinematic": """You are a professional screenwriter. Convert the provided content into a cinematic screenplay with proper THREE-ACT STRUCTURE:

**STRUCTURE REQUIREMENTS:**
- Divide the story into ACT I, ACT II, and ACT III
- Create 5-10 distinct SCENES per act (15-30 total scenes depending on content length)
- Each scene must have proper heading: INT./EXT. LOCATION - TIME
- Label each scene clearly (e.g., "ACT I - SCENE 1:", "ACT II - SCENE 5:")

**CRITICAL DIALOGUE FORMATTING:**
Show conversations between characters in proper screenplay format:

CHARACTER NAME
(optional direction)
What the character says directly.

ANOTHER CHARACTER
Their direct response.

**EXAMPLE:**
**ACT I - SCENE 1**
INT. DURSLEY HOUSE - DAY
A lonely boy sits on the curb.

DUDLEY
(mocking)
Look at the freak! No one wants you here.

HARRY
(quietly, looking down)
I just want to be left alone.

AUNT PETUNIA
(shouting from doorway)
Get inside this instant! And stop bothering Dudley.

**FORMATTING RULES:**
- Character names in UPPERCASE before their dialogue
- Write actual spoken words, not narrative descriptions
- NO voice-over or narrator commentary
- NO phrases like "The narrator says" or "Voice-over explains"
- Action descriptions in present tense between dialogue
- Parentheticals for actor directions only

**STORY COVERAGE:**
- Complete character arcs and development
- All key plot points through dialogue and action
- Full narrative from beginning to end
- Focus on character-to-character interactions and conversations""",
            "narration": """You are a professional narrator. Convert the content into an engaging narration script with:
                - Rich, descriptive voice-over text
                - Scene descriptions for visual context
                - Emotional and atmospheric descriptions
                - Clear pacing and transitions
                - Complete story coverage with all key elements
                - Narrative flow that captures the full story""",
            "educational": """You are an educational content creator. Convert the content into a clear, educational script with:
                - Clear learning objectives
                - Step-by-step explanations
                - Visual cues for graphics and demonstrations
                - Engaging but informative tone
                - Complete coverage of all educational content
                - Comprehensive explanations without omissions""",
            "marketing": """You are a marketing copywriter. Convert the content into a compelling marketing script with:
                - Hook in the first 3 seconds
                - Clear value proposition
                - Call-to-action
                - Emotional engagement
                - Complete product/service story
                - All key benefits and features covered""",
        }

        system_prompt = system_prompts.get(script_type, system_prompts["cinematic"])

        # Add plot context guidance to system prompt if available
        if plot_context and plot_context.get("enhanced_content"):
            plot_guidance = "\n\nIMPORTANT: Use the provided plot context as your primary guide for character development, story consistency, and thematic elements. Stay true to the established plot, characters, and story world without introducing conflicting elements or deviating from the core narrative."
            system_prompt += plot_guidance

        # Add duration guidance to system prompt if specified
        if target_duration and target_duration != "auto":
            duration_guidance = f"\n\nTarget duration: {target_duration} minutes. Aim for approximately 1 page per minute of content."
            system_prompt += duration_guidance
        elif target_duration == "auto":
            duration_guidance = "\n\nDuration: Auto - Create a comprehensive script that captures the complete story from each page. Include all key plot points, character development, story elements, and narrative details without time constraints."
            system_prompt += duration_guidance

        # Create user message with duration instructions
        user_content = f"Convert this content into a {script_type} script:"
        if target_duration and target_duration != "auto":
            user_content += f"\n\nTarget Duration: {target_duration} minutes - focus on the most essential story elements within this time frame."
        elif target_duration == "auto":
            user_content += "\n\nDuration: Auto - Create a comprehensive script that captures the FULL STORY from each page. Include:\n- All major plot points and story developments\n- Complete character arcs and interactions\n- Key descriptive elements and settings\n- Important dialogue and narrative moments\n- Full story coverage without omissions or shortcuts"

        # Add plot context to user message if available
        if plot_context and plot_context.get("enhanced_content"):
            user_content += f"\n\nPLOT CONTEXT (Use this as your guide - do not deviate from established characters, plot, or story elements):\n{plot_context['enhanced_content']}\n\nCHAPTER CONTENT:\n{content}"
        else:
            user_content += f"\n\nContent:\n{content}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    async def analyze_content(
        self, content: str, user_tier: ModelTier, analysis_type: str = "summary"
    ) -> Dict[str, Any]:
        """
        Analyze content for various purposes (summary, keywords, difficulty, etc.)
        """
        config = self.MODEL_CONFIGS[user_tier]
        model = config["primary"]

        # Special handling for plot generation and character creation
        if analysis_type in [
            "plot_overview",
            "characters",
            "archetype_analysis",
            "character_details",
        ]:
            system_prompt = self._get_special_system_prompt(analysis_type)
            user_message = content
            max_tokens = config["max_tokens"]  # Use full token limit for generation
            temperature = 0.7  # Higher temperature for creative generation
        else:
            analysis_prompts = {
                "summary": "Provide a concise summary of this content in 2-3 sentences.",
                "keywords": "Extract 5-10 key topics or themes from this content.",
                "difficulty": "Assess the reading difficulty level of this content (elementary, middle school, high school, college, professional).",
                "genre": "Identify the genre and style of this content.",
                "characters": "List all characters mentioned in this content with brief descriptions.",
            }

            prompt = analysis_prompts.get(analysis_type, analysis_prompts["summary"])
            system_prompt = "You are a content analyst."
            user_message = (
                f"{prompt}\n\nContent:\n{content[:3000]}"  # Limit content for analysis
            )
            max_tokens = 500
            temperature = 0.3  # Lower temperature for analysis

        try:
            create_fn: Any = getattr(self.client.chat.completions, "create")
            response = await create_fn(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Calculate cost
            usage = response.usage
            input_cost = (usage.prompt_tokens / 1000) * config["cost_per_1k_input"]
            output_cost = (usage.completion_tokens / 1000) * config[
                "cost_per_1k_output"
            ]
            total_cost = input_cost + output_cost

            # Track the cost
            await self.cost_tracker.track(
                user_tier=user_tier,
                model=model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                cost=total_cost,
            )

            return {
                "status": "success",
                "analysis_type": analysis_type,
                "result": response.choices[0].message.content,
                "model_used": model,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "estimated_cost": total_cost,
                },
            }

        except Exception as e:
            logger.error(f"[OpenRouter] Analysis error: {str(e)}")
            return {"status": "error", "error": str(e), "analysis_type": analysis_type}

    def _get_special_system_prompt(self, analysis_type: str) -> str:
        """
        Get specialized system prompts for different generation types
        """
        prompts = {
            "plot_overview": """You are a professional literary analyst and story consultant with extensive experience in narrative structure, character development, and thematic analysis. You excel at creating compelling plot overviews that capture the essence of stories.""",
            "characters": """You are an expert character developer and psychologist specializing in creating deep, multidimensional characters with clear motivations, arcs, and personality traits. You understand Jungian archetypes and narrative character functions.""",
            "archetype_analysis": """You are a Jungian psychology expert specializing in archetypal analysis of characters in literature. You can identify and explain how characters embody classic archetypes and their narrative functions.""",
            "character_details": """You are an expert character development analyst. Analyze the provided book content and generate comprehensive character details in valid JSON format. Always respond with properly formatted JSON containing all requested fields.""",
        }

        return prompts.get(analysis_type, "You are a content analyst.")

    async def get_available_models(self) -> Dict[str, Any]:
        """
        Get list of available models from OpenRouter
        """
        try:
            # Use OpenAI-compatible client to get models
            models_response = await self.client.models.list()

            # Convert Model objects to dicts
            models = []
            for model in models_response.data:
                models.append(
                    {
                        "id": model.id,
                        "name": getattr(model, "name", model.id) or model.id,
                        "context_length": getattr(model, "context_length", 4096)
                        or 4096,
                        "pricing": getattr(model, "pricing", {}) or {},
                        "supported": model.id
                        in [
                            config["primary"] for config in self.MODEL_CONFIGS.values()
                        ],
                    }
                )

            return {"status": "success", "models": models}

        except Exception as e:
            logger.error(f"Error fetching available models: {str(e)}")
            return {"status": "error", "error": str(e), "models": []}


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
        cost: float,
    ):
        """
        Track API usage and costs
        """
        # Store in database for billing
        # This is a simplified version - expand based on your needs
        logger.info(
            f"[Cost Tracking] Model: {model}, Tokens: {input_tokens + output_tokens}, Cost: ${cost:.6f}"
        )

        # You would typically:
        # 1. Store in database
        # 2. Update user's usage quota
        # 3. Check against limits
        # 4. Send alerts if needed

    def _clean_narrator_from_cinematic_script(self, script_content: str) -> str:
        """
        Remove narrator/voice-over elements from cinematic movie scripts
        """
        import re

        lines = script_content.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            # Skip narrator/voice-over indicators
            narrator_indicators = [
                r"^\s*NARRATOR\s*:",
                r"^\s*VOICE\s*OVER\s*:",
                r"^\s*V\.O\.\s*:",
                r"^\s*VOICE-OVER\s*:",
                r"^\s*NARRATOR\s*\(",
                r"^\s*VOICE\s*\(",
            ]

            # Check if line starts with narrator indicators (case insensitive)
            is_narrator_line = False
            for indicator in narrator_indicators:
                if re.match(indicator, line, re.IGNORECASE):
                    is_narrator_line = True
                    break

            # Skip narrator lines
            if is_narrator_line:
                continue

            # Also skip lines that contain narrator descriptions
            narrator_descriptions = [
                "narrator",
                "voice over",
                "voice-over",
                "v.o.",
                "voiceover",
            ]

            line_lower = line.lower()
            if any(desc in line_lower for desc in narrator_descriptions):
                # Check if it's actually a character name followed by dialogue
                # Only skip if it's clearly narrator-related and not a character name
                if not (line.isupper() and len(line.split()) <= 3):
                    continue

            cleaned_lines.append(line)

        # Join back and clean up extra blank lines
        cleaned_content = "\n".join(cleaned_lines)
        # Remove multiple consecutive blank lines
        cleaned_content = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned_content)

        return cleaned_content.strip()
