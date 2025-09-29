from typing import Dict, Any, List, Optional
import uuid
import json
import logging
from datetime import datetime

from app.core.database import get_supabase
from app.services.openrouter_service import OpenRouterService, ModelTier
from app.services.subscription_manager import SubscriptionManager
from app.services.rag_service import RAGService
from app.schemas.plot import (
    PlotGenerationRequest,
    PlotGenerationResponse,
    PlotOverviewResponse,
    PlotOverviewUpdate,
    CharacterResponse,
    CharacterCreate,
    PlotOverviewCreate
)

logger = logging.getLogger(__name__)


class PlotGenerationError(Exception):
    """Custom exception for plot generation errors"""
    pass


class SubscriptionLimitError(Exception):
    """Custom exception for subscription limit exceeded"""
    pass


class PlotService:
    """
    Core plot generation service that orchestrates AI-powered plot overview generation,
    character creation with archetype analysis, and integration with existing services.
    """

    def __init__(self, supabase_client=None):
        self.db = supabase_client or get_supabase()
        self.openrouter = OpenRouterService()
        self.subscription_manager = SubscriptionManager(self.db)
        self.rag_service = RAGService(self.db)

    async def generate_plot_overview(
        self,
        user_id: str,
        book_id: str,
        request: PlotGenerationRequest
    ) -> PlotGenerationResponse:
        """
        Main method that coordinates the entire plot generation process.
        Checks user subscription limits and permissions, gets book context using RAG service,
        generates plot overview using OpenRouter service, creates characters with archetype analysis,
        stores all data in database, and returns comprehensive response.
        """
        try:
            logger.info(f"[PlotService] Starting plot generation for user {user_id}, book {book_id}")

            # 1. Check subscription limits and permissions
            user_tier = await self.subscription_manager.get_user_tier(user_id)
            usage_check = await self.subscription_manager.check_usage_limits(user_id, "plot")

            if not usage_check["can_generate"]:
                raise SubscriptionLimitError(f"Plot generation limit exceeded for {user_tier.value} tier")

            # 2. Get book context using RAG service
            book_context = await self._get_book_context_for_plot(book_id)
            if not book_context:
                raise PlotGenerationError("Unable to retrieve book context for plot generation")

            # 3. Map subscription tier to model tier
            model_tier = self._map_subscription_to_model_tier(user_tier)

            # 4. Generate plot overview using OpenRouter service
            plot_data = await self._generate_plot_overview_with_ai(
                book_context, request, model_tier
            )

            # 5. Generate characters with archetype analysis
            characters_data = await self._generate_characters_with_archetypes(
                plot_data, book_context, model_tier
            )
            logger.info(f"[PlotService] Characters generated: {len(characters_data)} characters")

            # 6. Store plot overview and characters in database
            stored_data = await self._store_plot_overview(
                plot_data, characters_data, user_id, book_id, book_context
            )

            # 7. Record usage for billing
            await self.subscription_manager.record_usage(
                user_id=user_id,
                resource_type="plot",
                cost_usd=plot_data.get("generation_cost", 0.0),
                metadata={
                    "book_id": book_id,
                    "model_used": plot_data.get("model_used"),
                    "characters_generated": len(characters_data)
                }
            )

            # 8. Return comprehensive response
            response = PlotGenerationResponse(
                plot_overview=stored_data["plot_overview"],
                characters=stored_data["characters"],
                message="Plot overview generated successfully"
            )

            logger.info(f"[PlotService] Plot generation completed for user {user_id}, plot_id: {stored_data['plot_overview'].id}")
            return response

        except SubscriptionLimitError:
            logger.warning(f"[PlotService] Subscription limit exceeded for user {user_id}")
            raise
        except Exception as e:
            logger.error(f"[PlotService] Error generating plot overview: {str(e)}")
            raise PlotGenerationError(f"Plot generation failed: {str(e)}")

    async def _get_book_context_for_plot(self, book_id: str) -> Dict[str, Any]:
        """
        RAG integration for book analysis to provide context for plot generation.
        """
        try:
            # Get basic book information
            book_response = self.db.table('books').select('*').eq('id', book_id).single().execute()
            if not book_response.data:
                return None

            book = book_response.data

            # Get chapter summaries for context (limit to avoid token limits)
            chapters_response = self.db.table('chapters').select(
                'id, title, chapter_number, content'
            ).eq('book_id', book_id).order('chapter_number').limit(10).execute()

            chapters = chapters_response.data or []

            # Extract key content snippets
            context_parts = []
            for chapter in chapters:
                # Take first 500 characters of each chapter for context
                content_preview = chapter['content'][:500] if chapter['content'] else ""
                context_parts.append(f"Chapter {chapter['chapter_number']}: {chapter['title']}\n{content_preview}")

            return {
                "book": {
                    "id": book["id"],
                    "title": book["title"],
                    "author": book.get("author", ""),
                    "genre": book.get("genre", ""),
                    "description": book.get("description", ""),
                    "book_type": book.get("book_type", "fiction")
                },
                "chapters_summary": "\n\n".join(context_parts),
                "total_chapters": len(chapters),
                "context_length": sum(len(part) for part in context_parts)
            }

        except Exception as e:
            logger.error(f"[PlotService] Error getting book context: {str(e)}")
            return None

    async def _generate_plot_overview_with_ai(
        self,
        book_context: Dict[str, Any],
        request: PlotGenerationRequest,
        model_tier: ModelTier
    ) -> Dict[str, Any]:
        """
        Generate plot overview using OpenRouter service with AI analysis.
        """
        try:
            # Prepare the prompt for plot generation
            prompt = self._build_plot_generation_prompt(book_context, request)

            # Use OpenRouter to generate the plot
            response = await self.openrouter.analyze_content(
                content=prompt,
                user_tier=model_tier,
                analysis_type="plot_overview"
            )

            if response["status"] != "success":
                raise PlotGenerationError(f"AI plot generation failed: {response.get('error', 'Unknown error')}")

            # Parse the AI response
            plot_data = self._parse_plot_generation_response(response["result"])

            # Add metadata
            plot_data.update({
                "generation_method": "openrouter",
                "model_used": response.get("model_used", "unknown"),
                "generation_cost": response.get("usage", {}).get("estimated_cost", 0.0),
                "status": "completed"
            })

            return plot_data

        except Exception as e:
            logger.error(f"[PlotService] Error generating plot with AI: {str(e)}")
            raise PlotGenerationError(f"AI plot generation failed: {str(e)}")

    def _build_plot_generation_prompt(
        self,
        book_context: Dict[str, Any],
        request: PlotGenerationRequest
    ) -> str:
        """
        Build the prompt for plot generation based on book context and user request.
        """
        book = book_context["book"]
        chapters_summary = book_context.get("chapters_summary", "")

        base_prompt = f"""
You are a professional literary analyst and story consultant. Analyze the following book and generate a comprehensive plot overview.

BOOK INFORMATION:
Title: {book['title']}
Author: {book.get('author', 'Unknown')}
Genre: {book.get('genre', 'Unknown')}
Type: {book.get('book_type', 'Fiction')}
Description: {book.get('description', '')}

CHAPTER SUMMARIES:
{chapters_summary}

TASK:
Generate a detailed plot overview that includes:
1. Logline: A one-sentence summary (under 1000 characters)
2. Themes: Key themes as a JSON array
3. Story Type: The narrative structure (e.g., "hero's journey", "coming of age", "quest", "redemption")
4. Genre: Primary genre classification
5. Tone: Overall emotional tone (e.g., "dark", "hopeful", "humorous", "serious")
6. Audience: Target audience (e.g., "young adult", "adult", "children")
7. Setting: Time period and location description

{f"ADDITIONAL INSTRUCTIONS: {request.prompt}" if request.prompt else ""}

RESPONSE FORMAT:
Return ONLY a valid JSON object with these exact keys:
{{
    "logline": "string",
    "themes": ["theme1", "theme2"],
    "story_type": "string",
    "genre": "string",
    "tone": "string",
    "audience": "string",
    "setting": "string"
}}
"""

        return base_prompt.strip()

    def _parse_plot_generation_response(self, ai_response: str) -> Dict[str, Any]:
        """
        Parse the AI response and extract plot data.
        """
        logger.info(f"[PlotService] Raw AI response: {ai_response[:500]}...")  # Log first 500 chars

        try:
            # Try to parse as JSON first
            plot_data = json.loads(ai_response.strip())
            logger.info(f"[PlotService] Parsed JSON successfully. Themes type: {type(plot_data.get('themes'))}, value: {plot_data.get('themes')}")

            # Validate required fields
            required_fields = ["logline", "themes", "story_type", "genre", "tone", "audience", "setting"]
            for field in required_fields:
                if field not in plot_data:
                    plot_data[field] = None

            return plot_data

        except json.JSONDecodeError:
            # Fallback: extract information from text response
            logger.warning("[PlotService] AI response not valid JSON, attempting text parsing")

            plot_data = {
                "logline": self._extract_field_from_text(ai_response, "logline"),
                "themes": self._extract_themes_from_text(ai_response),
                "story_type": self._extract_field_from_text(ai_response, "story_type"),
                "genre": self._extract_field_from_text(ai_response, "genre"),
                "tone": self._extract_field_from_text(ai_response, "tone"),
                "audience": self._extract_field_from_text(ai_response, "audience"),
                "setting": self._extract_field_from_text(ai_response, "setting")
            }

            logger.info(f"[PlotService] Text parsing completed. Themes type: {type(plot_data.get('themes'))}, value: {plot_data.get('themes')}")
            return plot_data

    def _extract_field_from_text(self, text: str, field_name: str) -> Optional[str]:
        """
        Extract a specific field value from text response.
        """
        import re

        # Look for patterns like "Field Name: value"
        patterns = [
            rf"{field_name}:\s*([^\n\r]+)",
            rf"{field_name.capitalize()}:\s*([^\n\r]+)",
            rf"{field_name.upper()}:\s*([^\n\r]+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_themes_from_text(self, text: str) -> List[str]:
        """
        Extract themes from text response.
        """
        import re

        logger.debug(f"[PlotService] Extracting themes from text: {text[:200]}...")

        # Look for themes section
        themes_match = re.search(r"themes?:?\s*\[([^\]]+)\]", text, re.IGNORECASE | re.DOTALL)
        if themes_match:
            themes_str = themes_match.group(1)
            logger.debug(f"[PlotService] Found bracketed themes: {themes_str}")
            # Split by comma and clean up
            themes = [t.strip().strip('"\'') for t in themes_str.split(',')]
            result = [t for t in themes if t]
            logger.info(f"[PlotService] Extracted themes from brackets: {result}")
            return result

        # Fallback: look for themes in a list format
        themes_match = re.search(r"themes?:?\s*(.+?)(?=\n\n|\n[A-Z]|$)", text, re.IGNORECASE | re.DOTALL)
        if themes_match:
            themes_text = themes_match.group(1)
            logger.debug(f"[PlotService] Found themes text: {themes_text}")
            themes = re.split(r'[,;]\s*', themes_text)
            result = [t.strip() for t in themes if t.strip()]
            logger.info(f"[PlotService] Extracted themes from text: {result}")
            return result

        logger.warning("[PlotService] No themes found in text response")
        return []

    async def _generate_characters_with_archetypes(
        self,
        plot_context: Dict[str, Any],
        book_context: Dict[str, Any],
        model_tier: ModelTier
    ) -> List[Dict[str, Any]]:
        """
        Generate characters with archetype analysis using AI.
        """
        try:
            # Prepare character generation prompt
            prompt = self._build_character_generation_prompt(plot_context, book_context)

            # Generate characters using OpenRouter
            response = await self.openrouter.analyze_content(
                content=prompt,
                user_tier=model_tier,
                analysis_type="characters"
            )

            if response["status"] != "success":
                logger.warning(f"[PlotService] Character generation failed, using fallback")
                return []

            # Parse character data
            characters_data = self._parse_character_generation_response(response["result"])

            # Analyze archetypes for each character
            for character in characters_data:
                archetype_analysis = await self._analyze_character_archetypes(
                    character, model_tier
                )
                character["archetypes"] = archetype_analysis.get("archetypes", [])
                character["archetype_analysis"] = archetype_analysis

            return characters_data

        except Exception as e:
            logger.error(f"[PlotService] Error generating characters: {str(e)}")
            return []

    def _build_character_generation_prompt(
        self,
        plot_context: Dict[str, Any],
        book_context: Dict[str, Any]
    ) -> str:
        """
        Build prompt for character generation.
        """
        book = book_context["book"]

        prompt = f"""
You are a character development expert. Based on the book and plot overview below, create 3-5 main characters.

BOOK: {book['title']}
PLOT OVERVIEW:
- Logline: {plot_context.get('logline', '')}
- Genre: {plot_context.get('genre', '')}
- Story Type: {plot_context.get('story_type', '')}
- Themes: {', '.join(plot_context.get('themes', []))}

CHAPTER CONTEXT:
{book_context.get('chapters_summary', '')[:1000]}

TASK:
Create 3-5 compelling characters that fit this story. For each character, provide:

1. Name: Character's full name
2. Role: protagonist/antagonist/supporting/minor
3. Character Arc: How they change/develop
4. Physical Description: Appearance details
5. Personality: Key personality traits
6. Want: External goal/motivation
7. Need: Internal emotional need
8. Lie: False belief they hold
9. Ghost: Past trauma or wound

RESPONSE FORMAT:
Return ONLY a valid JSON array of character objects:
[
    {{
        "name": "Character Name",
        "role": "protagonist",
        "character_arc": "Description of development",
        "physical_description": "Appearance details",
        "personality": "Personality traits",
        "want": "External goal",
        "need": "Internal need",
        "lie": "False belief",
        "ghost": "Past trauma"
    }}
]
"""

        return prompt.strip()

    def _parse_character_generation_response(self, ai_response: str) -> List[Dict[str, Any]]:
        """
        Parse the AI response for character generation.
        """
        try:
            characters = json.loads(ai_response.strip())

            if not isinstance(characters, list):
                characters = [characters]

            # Validate and clean character data
            validated_characters = []
            for char in characters:
                if isinstance(char, dict) and char.get('name'):
                    validated_characters.append({
                        "name": char.get('name', ''),
                        "role": char.get('role', 'supporting'),
                        "character_arc": char.get('character_arc', ''),
                        "physical_description": char.get('physical_description', ''),
                        "personality": char.get('personality', ''),
                        "want": char.get('want', ''),
                        "need": char.get('need', ''),
                        "lie": char.get('lie', ''),
                        "ghost": char.get('ghost', ''),
                        "archetypes": [],
                        "generation_method": "openrouter"
                    })

            return validated_characters[:5]  # Limit to 5 characters

        except json.JSONDecodeError:
            # Fallback: extract information from text response
            logger.warning("[PlotService] Character response not valid JSON, attempting text parsing")
            return self._parse_character_generation_text_response(ai_response)

    def _parse_character_generation_text_response(self, ai_response: str) -> List[Dict[str, Any]]:
        """
        Parse character generation response from text when JSON parsing fails.
        """
        import re

        logger.info(f"[PlotService] Parsing character text response: {ai_response[:500]}...")

        characters = []

        # Split response into character sections
        # Look for patterns like "Character 1:", "1.", or just numbered sections
        character_sections = re.split(r'(?:^|\n)(?:Character\s*\d+:?|^\d+\.|\n\d+\.)\s*', ai_response.strip(), flags=re.MULTILINE | re.IGNORECASE)

        # Remove empty sections
        character_sections = [section.strip() for section in character_sections if section.strip()]

        for section in character_sections[:5]:  # Limit to 5 characters
            character_data = {
                "name": self._extract_character_field_from_text(section, "name"),
                "role": self._extract_character_field_from_text(section, "role"),
                "character_arc": self._extract_character_field_from_text(section, "character_arc"),
                "physical_description": self._extract_character_field_from_text(section, "physical_description"),
                "personality": self._extract_character_field_from_text(section, "personality"),
                "want": self._extract_character_field_from_text(section, "want"),
                "need": self._extract_character_field_from_text(section, "need"),
                "lie": self._extract_character_field_from_text(section, "lie"),
                "ghost": self._extract_character_field_from_text(section, "ghost"),
                "archetypes": [],
                "generation_method": "openrouter_text_fallback"
            }

            # Only include characters that have at least a name
            if character_data["name"]:
                characters.append(character_data)

        logger.info(f"[PlotService] Extracted {len(characters)} characters from text")
        return characters

    def _extract_character_field_from_text(self, text: str, field_name: str) -> Optional[str]:
        """
        Extract a specific character field value from text.
        """
        import re

        # Look for patterns like "Field Name: value"
        patterns = [
            rf"{field_name}:\s*([^\n\r]+)",
            rf"{field_name.capitalize()}:\s*([^\n\r]+)",
            rf"{field_name.upper()}:\s*([^\n\r]+)",
            rf"{field_name.replace('_', ' ')}:\s*([^\n\r]+)",
            rf"{field_name.replace('_', ' ').capitalize()}:\s*([^\n\r]+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Clean up common artifacts
                value = re.sub(r'^[-•*]\s*', '', value)  # Remove bullets
                value = re.sub(r'\s*$', '', value)  # Remove trailing whitespace
                return value if value else None

        return None

    async def _analyze_character_archetypes(
        self,
        character: Dict[str, Any],
        model_tier: ModelTier
    ) -> Dict[str, Any]:
        """
        Analyze character against Jungian archetypes using AI.
        """
        try:
            prompt = f"""
Analyze this character against Jungian archetypes and identify the best matches:

CHARACTER:
Name: {character['name']}
Role: {character['role']}
Personality: {character['personality']}
Character Arc: {character['character_arc']}
Want: {character['want']}
Need: {character['need']}

COMMON ARCHETYPES:
- The Hero: Brave, determined, flawed, growing
- The Mentor: Wise, experienced, supportive, mysterious
- The Shadow: Dark, opposing, powerful, threatening
- The Ally: Loyal, supportive, skilled, brave
- The Threshold Guardian: Testing, blocking, protective, cautious
- The Shapeshifter: Mysterious, changing, unpredictable, complex
- The Trickster: Humorous, wise, disruptive, unconventional

Return a JSON object with:
- archetypes: Array of matching archetype names (max 3)
- analysis: Brief explanation of why these archetypes fit
"""

            response = await self.openrouter.analyze_content(
                content=prompt,
                user_tier=model_tier,
                analysis_type="archetype_analysis"
            )

            if response["status"] == "success":
                try:
                    analysis = json.loads(response["result"])
                    return {
                        "archetypes": analysis.get("archetypes", []),
                        "analysis": analysis.get("analysis", "")
                    }
                except json.JSONDecodeError:
                    pass

            # Fallback: return basic archetype based on role
            role_archetypes = {
                "protagonist": ["The Hero"],
                "antagonist": ["The Shadow"],
                "mentor": ["The Mentor"],
                "supporting": ["The Ally"]
            }

            return {
                "archetypes": role_archetypes.get(character.get('role', 'supporting'), ["The Ally"]),
                "analysis": f"Basic archetype assignment based on character role: {character.get('role', 'supporting')}"
            }

        except Exception as e:
            logger.error(f"[PlotService] Error analyzing archetypes: {str(e)}")
            return {"archetypes": [], "analysis": "Archetype analysis failed"}

    async def _store_plot_overview(
        self,
        plot_data: Dict[str, Any],
        characters: List[Dict[str, Any]],
        user_id: str,
        book_id: str,
        book_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store plot overview and characters in database.
        """
        try:
            # Generate plot overview ID
            plot_id = str(uuid.uuid4())

            # Query current maximum version for this book and user
            max_version_response = self.db.table('plot_overviews').select('version').eq('book_id', book_id).eq('user_id', user_id).order('version', desc=True).limit(1).execute()
            if max_version_response.data:
                max_version = max_version_response.data[0]['version']
                version = max_version + 1
            else:
                version = 1

            # Prepare plot overview data with defaults for missing fields
            themes_value = plot_data.get("themes", [])
            if not themes_value:
                themes_value = ["adventure", "growth"]  # Default themes

            logger.info(f"[PlotService] Storing themes - type: {type(themes_value)}, value: {themes_value}")

            plot_overview_data = {
                "id": plot_id,
                "book_id": book_id,
                "user_id": user_id,
                "logline": plot_data.get("logline") or f"A compelling {plot_data.get('genre', 'fiction')} story about personal growth and discovery.",
                "themes": themes_value,
                "story_type": plot_data.get("story_type") or "hero's journey",
                "genre": plot_data.get("genre") or book_context.get("book", {}).get("genre", "fiction"),
                "tone": plot_data.get("tone") or "hopeful",
                "audience": plot_data.get("audience") or "adult",
                "setting": plot_data.get("setting") or "Contemporary world",
                "generation_method": plot_data.get("generation_method", "openrouter"),
                "model_used": plot_data.get("model_used"),
                "generation_cost": plot_data.get("generation_cost", 0.0),
                "status": plot_data.get("status", "completed"),
                "version": version
            }

            # Insert plot overview
            plot_result = self.db.table('plot_overviews').insert(plot_overview_data).execute()

            # Store characters
            stored_characters = []
            for char_data in characters:
                char_id = str(uuid.uuid4())

                character_data = {
                    "id": char_id,
                    "plot_overview_id": plot_id,
                    "book_id": book_id,
                    "user_id": user_id,
                    "name": char_data["name"],
                    "role": char_data["role"],
                    "character_arc": char_data["character_arc"],
                    "physical_description": char_data["physical_description"],
                    "personality": char_data["personality"],
                    "archetypes": char_data.get("archetypes", []),
                    "want": char_data["want"],
                    "need": char_data["need"],
                    "lie": char_data["lie"],
                    "ghost": char_data["ghost"],
                    "generation_method": char_data.get("generation_method", "openrouter"),
                    "model_used": plot_data.get("model_used")
                }

                # Insert character
                char_result = self.db.table('characters').insert(character_data).execute()

                # Create response object
                stored_char = CharacterResponse(
                    id=char_id,
                    plot_overview_id=plot_id,
                    book_id=book_id,
                    user_id=user_id,
                    name=char_data["name"],
                    role=char_data["role"],
                    character_arc=char_data["character_arc"],
                    physical_description=char_data["physical_description"],
                    personality=char_data["personality"],
                    archetypes=char_data.get("archetypes", []),
                    want=char_data["want"],
                    need=char_data["need"],
                    lie=char_data["lie"],
                    ghost=char_data["ghost"],
                    generation_method=char_data.get("generation_method", "openrouter"),
                    model_used=plot_data.get("model_used"),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

                stored_characters.append(stored_char)

            # Debug: Log characters data before creating response
            logger.info(f"[PlotService] Creating PlotOverviewResponse - stored_characters count: {len(stored_characters)}")
            if stored_characters:
                logger.info(f"[PlotService] First character: {stored_characters[0].name if stored_characters[0] else 'None'}")

            # Create plot overview response with defaults
            plot_response = PlotOverviewResponse(
                id=plot_id,
                book_id=book_id,
                user_id=user_id,
                logline=plot_overview_data["logline"],
                themes=plot_overview_data["themes"],
                story_type=plot_overview_data["story_type"],
                genre=plot_overview_data["genre"],
                tone=plot_overview_data["tone"],
                audience=plot_overview_data["audience"],
                setting=plot_overview_data["setting"],
                generation_method=plot_overview_data["generation_method"],
                model_used=plot_overview_data["model_used"],
                generation_cost=plot_overview_data["generation_cost"],
                status=plot_overview_data["status"],
                version=version,
                characters=stored_characters,  # Add missing characters field
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            logger.info(f"[PlotService] PlotOverviewResponse created with characters field: {len(plot_response.characters) if hasattr(plot_response, 'characters') else 'MISSING'}")

            return {
                "plot_overview": plot_response,
                "characters": stored_characters
            }

        except Exception as e:
            logger.error(f"[PlotService] Error storing plot overview: {str(e)}")
            raise PlotGenerationError(f"Failed to store plot data: {str(e)}")

    def _map_subscription_to_model_tier(self, subscription_tier) -> ModelTier:
        """
        Map subscription tier to OpenRouter model tier.
        """
        tier_mapping = {
            "free": ModelTier.FREE,
            "basic": ModelTier.BASIC,
            "standard": ModelTier.STANDARD,
            "premium": ModelTier.PREMIUM,
            "professional": ModelTier.PROFESSIONAL
        }

        # Handle both enum and string inputs
        tier_key = subscription_tier.value if hasattr(subscription_tier, 'value') else str(subscription_tier).lower()

        return tier_mapping.get(tier_key, ModelTier.FREE)

    async def enhance_script_with_plot(
        self,
        chapter_id: str,
        plot_overview_id: str,
        existing_script: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance existing script with plot context and character information.
        """
        try:
            # Get plot overview and characters
            plot_response = self.db.table('plot_overviews').select('*').eq('id', plot_overview_id).single().execute()
            if not plot_response.data:
                raise ValueError(f"Plot overview {plot_overview_id} not found")

            plot_overview = plot_response.data

            # Get characters for this plot
            characters_response = self.db.table('characters').select('*').eq('plot_overview_id', plot_overview_id).execute()
            characters = characters_response.data or []

            # Get chapter information
            chapter_response = self.db.table('chapters').select('*').eq('id', chapter_id).single().execute()
            if not chapter_response.data:
                raise ValueError(f"Chapter {chapter_id} not found")

            chapter = chapter_response.data

            # Build enhancement prompt
            enhancement_prompt = self._build_script_enhancement_prompt(
                existing_script, plot_overview, characters, chapter
            )

            # Use RAG service to enhance the script
            enhanced_script = await self.rag_service.generate_video_script(
                chapter_context={"chapter": chapter, "book": {"title": "Unknown"}},  # Simplified context
                video_style="cinematic",
                script_style="cinematic_movie"
            )

            # Store enhanced script in chapter_scripts table
            script_data = {
                "chapter_id": chapter_id,
                "plot_overview_id": plot_overview_id,
                "user_id": plot_overview["user_id"],
                "plot_enhanced": True,
                "character_enhanced": True,
                "scenes": existing_script.get("scenes", []),
                "character_details": [char["name"] for char in characters],
                "character_arcs": {char["name"]: char.get("character_arc", "") for char in characters},
                "status": "enhanced",
                "version": existing_script.get("version", 1) + 1,
                "generation_metadata": {
                    "plot_overview_used": plot_overview_id,
                    "characters_integrated": len(characters),
                    "enhancement_type": "plot_aware"
                }
            }

            # Insert or update chapter script
            result = self.db.table('chapter_scripts').upsert(script_data).execute()

            return {
                "enhanced_script": enhanced_script.get("script", existing_script),
                "plot_integration": {
                    "plot_overview_id": plot_overview_id,
                    "characters_used": len(characters),
                    "themes_integrated": plot_overview.get("themes", [])
                },
                "status": "enhanced"
            }

        except Exception as e:
            logger.error(f"[PlotService] Error enhancing script: {str(e)}")
            return existing_script

    def _build_script_enhancement_prompt(
        self,
        existing_script: Dict[str, Any],
        plot_overview: Dict[str, Any],
        characters: List[Dict[str, Any]],
        chapter: Dict[str, Any]
    ) -> str:
        """
        Build prompt for script enhancement with plot context.
        """
        characters_text = "\n".join([
            f"- {char['name']}: {char.get('role', 'unknown')} - {char.get('personality', '')}"
            for char in characters
        ])

        prompt = f"""
Enhance this script with plot context and character development:

PLOT OVERVIEW:
Logline: {plot_overview.get('logline', '')}
Themes: {', '.join(plot_overview.get('themes', []))}
Genre: {plot_overview.get('genre', '')}
Tone: {plot_overview.get('tone', '')}

CHARACTERS:
{characters_text}

EXISTING SCRIPT:
{existing_script.get('script', '')}

CHAPTER CONTEXT:
{chapter.get('content', '')[:500]}

TASK:
Enhance the script by:
1. Integrating plot themes and character motivations
2. Adding character development moments
3. Ensuring consistency with overall plot
4. Maintaining the original script's structure

Return the enhanced script.
"""

        return prompt.strip()

    async def get_plot_overview(self, user_id: str, book_id: str) -> Optional[PlotOverviewResponse]:
        """
        Retrieve existing plot overview for a book.
        """
        try:
            # Get plot overview
            plot_response = self.db.table('plot_overviews').select('*').eq(
                'book_id', book_id
            ).eq('user_id', user_id).order('version', desc=True).limit(1).execute()

            if not plot_response.data:
                return None

            plot_data = plot_response.data[0]

            # Get associated characters
            characters_response = self.db.table('characters').select('*').eq(
                'plot_overview_id', plot_data['id']
            ).execute()

            characters = []
            for char_data in characters_response.data or []:
                char_response = CharacterResponse(
                    id=char_data['id'],
                    plot_overview_id=char_data['plot_overview_id'],
                    book_id=char_data['book_id'],
                    user_id=char_data['user_id'],
                    name=char_data['name'],
                    role=char_data['role'],
                    character_arc=char_data['character_arc'],
                    physical_description=char_data['physical_description'],
                    personality=char_data['personality'],
                    archetypes=char_data['archetypes'],
                    want=char_data['want'],
                    need=char_data['need'],
                    lie=char_data['lie'],
                    ghost=char_data['ghost'],
                    generation_method=char_data['generation_method'],
                    model_used=char_data['model_used'],
                    created_at=char_data['created_at'],
                    updated_at=char_data['updated_at']
                )
                characters.append(char_response)

            # Create plot overview response
            plot_overview = PlotOverviewResponse(
                id=plot_data['id'],
                book_id=plot_data['book_id'],
                user_id=plot_data['user_id'],
                logline=plot_data['logline'],
                themes=plot_data['themes'],
                story_type=plot_data['story_type'],
                genre=plot_data['genre'],
                tone=plot_data['tone'],
                audience=plot_data['audience'],
                setting=plot_data['setting'],
                generation_method=plot_data['generation_method'],
                model_used=plot_data['model_used'],
                generation_cost=plot_data['generation_cost'],
                status=plot_data['status'],
                version=plot_data['version'],
                characters=characters,
                created_at=plot_data['created_at'],
                updated_at=plot_data['updated_at']
            )

            return plot_overview

        except Exception as e:
            logger.error(f"[PlotService] Error retrieving plot overview: {str(e)}")
            return None

    async def update_plot_overview(
        self,
        user_id: str,
        plot_id: str,
        updates: PlotOverviewUpdate
    ) -> PlotOverviewResponse:
        """
        Update existing plot overview.
        """
        try:
            # Get current plot overview
            current_response = self.db.table('plot_overviews').select('*').eq(
                'id', plot_id
            ).eq('user_id', user_id).single().execute()

            if not current_response.data:
                raise ValueError(f"Plot overview {plot_id} not found or access denied")

            current_data = current_response.data

            # Prepare update data
            update_data = {}
            for field in ['logline', 'themes', 'story_type', 'genre', 'tone', 'audience', 'setting',
                         'generation_method', 'model_used', 'generation_cost', 'status', 'version']:
                if hasattr(updates, field) and getattr(updates, field) is not None:
                    update_data[field] = getattr(updates, field)

            if update_data:
                update_data['updated_at'] = datetime.now().isoformat()

                # Update the record
                result = self.db.table('plot_overviews').update(update_data).eq('id', plot_id).execute()

                # Return updated plot overview
                updated_data = result.data[0] if result.data else current_data

                return PlotOverviewResponse(
                    id=updated_data['id'],
                    book_id=updated_data['book_id'],
                    user_id=updated_data['user_id'],
                    logline=updated_data['logline'],
                    themes=updated_data['themes'],
                    story_type=updated_data['story_type'],
                    genre=updated_data['genre'],
                    tone=updated_data['tone'],
                    audience=updated_data['audience'],
                    setting=updated_data['setting'],
                    generation_method=updated_data['generation_method'],
                    model_used=updated_data['model_used'],
                    generation_cost=updated_data['generation_cost'],
                    status=updated_data['status'],
                    version=updated_data['version'],
                    created_at=updated_data['created_at'],
                    updated_at=updated_data['updated_at']
                )
            else:
                # No updates provided, return current data
                return PlotOverviewResponse(**current_data)

        except Exception as e:
            logger.error(f"[PlotService] Error updating plot overview: {str(e)}")
            raise PlotGenerationError(f"Failed to update plot overview: {str(e)}")