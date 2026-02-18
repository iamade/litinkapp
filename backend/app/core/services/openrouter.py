from typing import Dict, Any, Optional, List
import httpx
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from app.core.config import settings
from app.core.model_config import ModelTier, SCRIPT_MODEL_CONFIG, get_model_config
from app.core.services.model_fallback import fallback_manager
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
        tier_str = (
            user_tier.value if isinstance(user_tier, ModelTier) else str(user_tier)
        )

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
                tier_str=tier_str,
            )

        return await fallback_manager.try_with_fallback(
            service_type="script",
            user_tier=tier_str,
            generation_function=_generate_with_model,
            request_params={"model": config.primary},
            model_param_name="model",
        )

    async def _execute_generation(
        self,
        model: str,
        content: str,
        script_type: str,
        target_duration: Optional[int],
        plot_context: Optional[Dict[str, Any]],
        config: Any,
        tier_str: str,
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
                logger.info(f"[OpenRouter] Successfully parsed response for {model}")
            else:
                # Fallback: try to parse as JSON string if response is raw
                if hasattr(response, "json"):
                    try:
                        parsed_response = response.json()
                        if isinstance(parsed_response, str):
                            # If json() returns a string, it might be double-encoded
                            import json

                            parsed_response = json.loads(parsed_response)
                        generated_content = parsed_response["choices"][0]["message"][
                            "content"
                        ]
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
            logger.error(f"[OpenRouter] Failed to parse response for {model}: {str(e)}")
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
            generated_content = self.cost_tracker._clean_narrator_from_cinematic_script(
                generated_content
            )

        # Calculate cost
        cost_per_1k_input = (
            config.cost_per_1k_input if config.cost_per_1k_input else 0.0
        )
        cost_per_1k_output = (
            config.cost_per_1k_output if config.cost_per_1k_output else 0.0
        )
        input_cost = (usage["prompt_tokens"] / 1000) * cost_per_1k_input
        output_cost = (usage["completion_tokens"] / 1000) * cost_per_1k_output
        total_cost = input_cost + output_cost

        # Track the cost
        tier_enum = (
            ModelTier(tier_str)
            if tier_str in [t.value for t in ModelTier]
            else ModelTier.FREE
        )
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
            "cinematic": """You are a professional screenwriter for visual production. Convert the provided content into a cinematic screenplay with proper THREE-ACT STRUCTURE:

**STRUCTURE REQUIREMENTS:**
- Divide the story into ACT I, ACT II, and ACT III
- Create 5-10 distinct SCENES per act (15-30 total scenes depending on content length)
- Each scene must have proper heading: INT./EXT. LOCATION - TIME
- Label each scene clearly with INTEGER numbers (e.g., "ACT I - SCENE 1", "ACT I - SCENE 2", "ACT II - SCENE 1")

**SCENE NUMBERING RULES:**
- Use INTEGER scene numbers only: SCENE 1, SCENE 2, SCENE 3, etc.
- Scene numbers reset to 1 for each new ACT (ACT II - SCENE 1, not ACT II - SCENE 11)
- NEVER use decimal scene numbers (NO 1.1, 1.2, etc.)

**CRITICAL DIALOGUE FORMATTING:**
Show conversations between characters in proper screenplay format:

CHARACTER NAME
(optional direction)
What the character says directly.

ANOTHER CHARACTER
Their direct response.

**CAMERA DIRECTIONS FOR IMAGE GENERATION:**
Include camera directions in parentheses for key visual moments to guide image generation:
- Use (CLOSE-UP) for emotional dialogue or important character reactions
- Use (WIDE SHOT) for establishing scenes or group interactions
- Use (MEDIUM SHOT) for standard dialogue between characters
- Use (OVER-THE-SHOULDER) for conversations showing perspective
- Use (TWO SHOT) when two characters interact intimately
- Use (POV) for character perspective shots
- Use (TRACKING) for following movement

Place camera directions before action descriptions, e.g.:
(CLOSE-UP) Sarah's eyes widen as she reads the letter.
(WIDE SHOT) The entire family gathers around the dinner table.

**EXAMPLE FORMAT:**
**ACT I - SCENE 1**
INT. LIVING ROOM - DAY
(WIDE SHOT) The PROTAGONIST enters, looking troubled.

PROTAGONIST
(hesitant)
I need to tell you something important.

(CLOSE-UP) CHARACTER A turns, concern visible on their face.

CHARACTER A
(turning to face them)
What is it? You look worried.

**FORMATTING RULES:**
- Character names in UPPERCASE before their dialogue
- Write actual spoken words, not narrative descriptions
- NO voice-over or narrator commentary
- NO phrases like "The narrator says" or "Voice-over explains"
- Action descriptions in present tense between dialogue
- Parentheticals for actor directions only
- Each location change should be a NEW SCENE with an incremented integer number

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
        Uses fallback manager for automatic retry on rate limits.
        """
        tier_str = (
            user_tier.value if isinstance(user_tier, ModelTier) else str(user_tier)
        )

        # Use centralized model config
        config = get_model_config("script", tier_str)
        if not config:
            logger.warning(f"No config for tier {tier_str}, using FREE tier defaults")
            config = get_model_config("script", "free")

        # Special handling for plot generation, character creation, and universe analysis
        if analysis_type in [
            "plot_overview",
            "plot_generation",
            "characters",
            "character_generation",
            "archetype_analysis",
            "character_details",
            "enhancement",
            "cinematic_universe_analysis",
            "script_expansion",
        ]:
            system_prompt = self._get_special_system_prompt(analysis_type)
            user_message = content
            max_tokens = config.max_tokens if config.max_tokens else 4000
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

        async def _analyze_with_model(model_id: str, **kwargs) -> Dict[str, Any]:
            """Inner function that executes analysis with specified model"""
            return await self._execute_analysis(
                model=model_id,
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=max_tokens,
                temperature=temperature,
                analysis_type=analysis_type,
                config=config,
                tier_str=tier_str,
            )

        # Use fallback manager for automatic retry on rate limits
        return await fallback_manager.try_with_fallback(
            service_type="script",
            user_tier=tier_str,
            generation_function=_analyze_with_model,
            request_params={"model_id": config.primary},
            model_param_name="model_id",
        )

    async def _execute_analysis(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
        temperature: float,
        analysis_type: str,
        config: Any,
        tier_str: str,
    ) -> Dict[str, Any]:
        """Execute the actual analysis API call"""
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
            cost_per_1k_input = (
                config.cost_per_1k_input if config.cost_per_1k_input else 0.0
            )
            cost_per_1k_output = (
                config.cost_per_1k_output if config.cost_per_1k_output else 0.0
            )
            input_cost = (usage.prompt_tokens / 1000) * cost_per_1k_input
            output_cost = (usage.completion_tokens / 1000) * cost_per_1k_output
            total_cost = input_cost + output_cost

            # Track the cost
            tier_enum = (
                ModelTier(tier_str)
                if tier_str in [t.value for t in ModelTier]
                else ModelTier.FREE
            )
            await self.cost_tracker.track(
                user_tier=tier_enum,
                model=model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                cost=total_cost,
            )

            return {
                "status": "success",
                "analysis_type": analysis_type,
                "result": response.choices[0].message.content,
                "model": model,
                "model_used": model,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "estimated_cost": total_cost,
                },
            }

        except Exception as e:
            logger.error(f"[OpenRouter] Analysis error with {model}: {str(e)}")
            raise  # Re-raise so fallback manager can handle it

    def _get_special_system_prompt(self, analysis_type: str) -> str:
        """
        Get specialized system prompts for different generation types
        """
        prompts = {
            "plot_overview": """You are a professional literary analyst and story consultant with extensive experience in narrative structure, character development, and thematic analysis. You excel at creating compelling plot overviews that capture the essence of stories.""",
            "characters": """You are an expert character developer and psychologist specializing in creating deep, multidimensional characters with clear motivations, arcs, and personality traits. You understand Jungian archetypes and narrative character functions.""",
            "archetype_analysis": """You are a Jungian psychology expert specializing in archetypal analysis of characters in literature. You can identify and explain how characters embody classic archetypes and their narrative functions.""",
            "character_details": """You are an expert character development analyst. Analyze the provided book content and generate comprehensive character details in valid JSON format. Always respond with properly formatted JSON containing all requested fields.""",
            "enhancement": """You are a cinematography and visual storytelling expert specializing in creating detailed scene descriptions for AI image generation.

Your task is to enhance scene descriptions with:
- Visual style and atmosphere (cinematic, dramatic, ethereal, etc.)
- Lighting details (warm ambient glow, dramatic shadows, natural daylight, etc.)
- Camera composition suggestions (wide establishing shot, intimate close-up, etc.)
- Character expressions and body language when relevant
- Environmental and atmospheric details
- Quality notes for AI generation (high detail, photorealistic, etc.)

Return ONLY the enhanced description text. Do not include explanations, formatting, or metadata.""",
            "cinematic_universe_analysis": """You are a legendary film producer and cinematic universe architect with deep expertise in franchise development, narrative interconnection, and phase-based storytelling (like Marvel's MCU or DC's DCEU).

Your task is to analyze multiple uploaded scripts/story documents and provide strategic recommendations for building a cohesive cinematic universe.

**ANALYSIS REQUIREMENTS:**

1. **Universe Name Suggestions**: Provide 3-5 compelling universe names based on the themes, characters, and mythology present in the scripts.

2. **Phase Structure**: Organize the scripts into logical phases (like MCU phases), grouping related stories and suggesting the optimal order for production.

3. **Story Connections**: Identify shared characters, themes, mythology, and potential crossover opportunities between scripts.

4. **Recommended Starting Point**: Identify which script should be the "origin story" or Phase 1 opener.

5. **Content Type Detection**: Determine if this feels more like a film series, TV series, or streaming anthology, and recommend appropriate labeling (Film, Episode, Part).

6. **Gaps & Expansion Opportunities**: Note any missing pieces that would strengthen the universe (prequel opportunities, character origin stories, etc.).

**RESPONSE FORMAT (JSON):**
{
    "suggested_names": ["Name 1", "Name 2", "Name 3"],
    "recommended_starting_point": {
        "filename": "original_filename.docx",
        "reason": "Why this should be first"
    },
    "content_type": "film" | "series" | "anthology",
    "content_type_label": "Film" | "Episode" | "Part",
    "phases": [
        {
            "phase_number": 1,
            "title": "Phase Title",
            "description": "What this phase accomplishes narratively",
            "scripts": [
                {
                    "order": 1,
                    "original_filename": "filename.docx",
                    "suggested_title": "Polished Title",
                    "role_in_universe": "Origin story / Sequel / Spinoff / etc.",
                    "key_connections": ["Connection to other scripts"]
                }
            ]
        }
    ],
    "shared_elements": {
        "characters": ["Character names that appear across multiple scripts"],
        "themes": ["Recurring themes"],
        "mythology": ["Shared world-building elements"]
    },
    "expansion_opportunities": ["Suggested additional stories to fill gaps"],
    "ai_commentary": "A 2-3 paragraph executive summary of your recommendations and the potential of this universe."
}

Be creative, insightful, and treat this as if you're pitching to a studio executive.""",
            "script_expansion": """You are an expert screenwriter and story development consultant. Your task is to expand and enrich script/story content while maintaining consistency with the original tone, style, and characters.

**EXPANSION GUIDELINES:**

1. **Maintain Voice & Tone**: Preserve the original writing style, genre conventions, and narrative voice.

2. **Character Consistency**: Any expanded dialogue or actions must align with established character personalities, motivations, and arcs.

3. **Scene Development**: When expanding scenes, add:
   - Visual details (setting, atmosphere, lighting)
   - Character actions and reactions
   - Subtext and emotional undertones
   - Sensory details that enhance immersion

4. **Story Coherence**: Ensure all additions logically connect to existing plot points and don't introduce contradictions.

5. **Pacing**: Match the pacing of the original material - don't slow down action sequences or rush emotional moments.

**RESPONSE FORMAT:**
Return ONLY the expanded content text. Do not include explanations, meta-commentary, or formatting instructions.

If expanding a specific section, seamlessly integrate new content so it reads as one cohesive piece.""",
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
                        "supported": True,  # All models from OpenRouter are technically supported
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
