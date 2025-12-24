from typing import Dict, Any, List, Optional
import uuid
import json
import logging
from datetime import datetime
from sqlmodel import select, col, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.services.openrouter import OpenRouterService, ModelTier
from app.api.services.subscription import SubscriptionManager
from app.core.services.rag import RAGService
from app.plots.schemas import (
    PlotOverviewCreate,
    PlotOverviewUpdate,
    PlotOverviewResponse,
    CharacterResponse,
)
from app.books.models import Book, Chapter
from app.plots.models import PlotOverview, Character, ChapterScript

logger = logging.getLogger(__name__)


class PlotGenerationError(Exception):
    """Custom exception for plot generation errors"""

    pass


class PlotService:
    """Service for AI-powered plot generation and management"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.openrouter = OpenRouterService()
        self.subscription_manager = SubscriptionManager(session)
        self.rag_service = RAGService(session)

    async def generate_plot_overview(
        self, user_id: uuid.UUID, book_id: uuid.UUID, plot_data: PlotOverviewCreate
    ) -> Dict[str, Any]:
        """
        Generate a plot overview based on book content and user input.
        """
        try:
            # 1. Check subscription limits
            user_tier = await self.subscription_manager.get_user_tier(user_id)
            model_tier = self._map_subscription_to_model_tier(user_tier)

            # 2. Get book context
            book_context = await self._get_book_context_for_plot(book_id)
            if not book_context:
                raise ValueError(f"Book {book_id} not found")

            # 3. Generate plot points using AI
            # If story_type is not provided, generate one for non-fiction
            if not plot_data.story_type and book_context.get("book", {}).get(
                "book_type"
            ) in ["non-fiction", "educational"]:
                plot_data.story_type = (
                    await self._generate_fictional_story_type_for_nonfiction(
                        book_context, plot_data.model_dump(), model_tier
                    )
                )

            # Generate plot overview
            generated_plot = await self._generate_plot_content(
                book_context, plot_data.model_dump(), model_tier
            )

            # 4. Generate characters
            generated_characters = await self._generate_characters(
                book_context, generated_plot, model_tier
            )

            # 5. Store results
            result = await self._store_plot_overview(
                generated_plot,
                generated_characters,
                user_id,
                book_id,
                book_context,
            )

            return result

        except Exception as e:
            logger.error(f"[PlotService] Error generating plot: {str(e)}")
            raise PlotGenerationError(f"Failed to generate plot: {str(e)}")

    async def generate_plot_from_prompt(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        input_prompt: str,
        project_type: Optional[str] = None,
        story_type: Optional[str] = None,
        genre: Optional[str] = None,
        tone: Optional[str] = None,
        audience: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a plot overview from a user prompt (for projects without books).
        """
        try:
            # 1. Check subscription limits
            user_tier = await self.subscription_manager.get_user_tier(user_id)
            model_tier = self._map_subscription_to_model_tier(user_tier)

            # 2. Create a prompt-based context (no book/chapters)
            prompt_context = {
                "prompt": input_prompt,
                "project_type": project_type or "entertainment",
                "project_id": str(project_id),
            }

            # 3. Generate plot content from prompt
            generated_plot = await self._generate_plot_from_prompt_content(
                prompt_context=prompt_context,
                story_type=story_type,
                genre=genre,
                tone=tone,
                audience=audience,
                model_tier=model_tier,
            )

            # 4. Generate characters from the prompt
            generated_characters = await self._generate_characters_from_prompt(
                prompt_context=prompt_context,
                plot_data=generated_plot,
                model_tier=model_tier,
            )

            # 5. Store results (using project_id as a pseudo book_id for now)
            # Note: We're storing with project_id in the book_id field - may need to update model later
            result = await self._store_plot_overview(
                generated_plot,
                generated_characters,
                user_id,
                project_id,  # Using project_id where book_id would go
                {
                    "book": {
                        "title": input_prompt[:100],
                        "genre": genre or "entertainment",
                    }
                },
            )

            return result

        except Exception as e:
            logger.error(f"[PlotService] Error generating plot from prompt: {str(e)}")
            raise PlotGenerationError(f"Failed to generate plot from prompt: {str(e)}")

    async def _generate_plot_from_prompt_content(
        self,
        prompt_context: Dict[str, Any],
        story_type: Optional[str],
        genre: Optional[str],
        tone: Optional[str],
        audience: Optional[str],
        model_tier: ModelTier,
    ) -> Dict[str, Any]:
        """
        Generate plot content from a user prompt (no book context).
        """
        user_prompt = prompt_context.get("prompt", "")
        project_type = prompt_context.get("project_type", "entertainment")

        prompt = f"""
You are a creative director generating a plot overview for a {project_type} project.

USER PROMPT:
{user_prompt}

PROJECT TYPE: {project_type}
STORY TYPE: {story_type or "engaging narrative"}
GENRE: {genre or "general"}
TONE: {tone or "professional"}
TARGET AUDIENCE: {audience or "general"}

TASK:
Generate a comprehensive plot overview for this creative project including:
1. Logline (1-2 sentences capturing the essence)
2. Themes (list of 3-5 major themes)
3. Setting Description
4. Story Arc Summary

RESPONSE FORMAT:
Return ONLY a valid JSON object:
{{
    "logline": "...",
    "themes": ["theme1", "theme2", ...],
    "story_type": "{story_type or 'engaging narrative'}",
    "script_story_type": "{project_type}",
    "genre": "{genre or 'general'}",
    "tone": "{tone or 'professional'}",
    "audience": "{audience or 'general'}",
    "setting": "...",
    "status": "completed"
}}
"""

        response = await self.openrouter.analyze_content(
            content=prompt, user_tier=model_tier, analysis_type="plot_generation"
        )

        if response.get("status") == "success":
            try:
                result = json.loads(response.get("result", "{}"))
                result["generation_method"] = "openrouter"
                result["model_used"] = response.get("model")
                result["generation_cost"] = response.get("cost", 0.0)
                return result
            except json.JSONDecodeError:
                logger.error("[PlotService] Failed to parse prompt plot JSON response")
                return {
                    "logline": f"A creative {project_type} based on: {user_prompt[:100]}",
                    "themes": ["creativity", "engagement"],
                    "story_type": story_type or "engaging narrative",
                    "genre": genre or "general",
                    "tone": tone or "professional",
                    "audience": audience or "general",
                    "setting": "Contemporary",
                    "status": "completed",
                    "generation_method": "openrouter_fallback",
                }
        else:
            raise PlotGenerationError(
                f"AI generation failed: {response.get('error', 'Unknown error')}"
            )

    async def _generate_characters_from_prompt(
        self,
        prompt_context: Dict[str, Any],
        plot_data: Dict[str, Any],
        model_tier: ModelTier,
    ) -> List[Dict[str, Any]]:
        """
        Generate character profiles from a prompt-based project.
        """
        user_prompt = prompt_context.get("prompt", "")
        project_type = prompt_context.get("project_type", "entertainment")

        prompt = f"""
Based on this creative project, identify and profile any key characters or personas.

PROJECT PROMPT: {user_prompt}
PROJECT TYPE: {project_type}
LOGLINE: {plot_data.get('logline', '')}

RESPONSE FORMAT:
Return ONLY a valid JSON array of character objects:
[
    {{
        "name": "Character/Persona Name",
        "role": "protagonist",
        "character_arc": "Brief description",
        "physical_description": "Appearance if relevant",
        "personality": "Key traits",
        "want": "Goal",
        "need": "Internal need",
        "lie": "False belief",
        "ghost": "Background"
    }}
]

If no specific characters are needed (e.g., for a product ad), return an empty array: []
"""

        response = await self.openrouter.analyze_content(
            content=prompt, user_tier=model_tier, analysis_type="character_generation"
        )

        if response.get("status") == "success":
            return self._parse_character_generation_response(response.get("result", ""))
        else:
            logger.warning("[PlotService] Character generation from prompt failed")
            return []

    async def _get_book_context_for_plot(self, book_id: uuid.UUID) -> Dict[str, Any]:
        """
        Retrieve book and chapter summaries for context.
        """
        try:
            # Get book
            statement = select(Book).where(Book.id == book_id)
            result = await self.session.exec(statement)
            book = result.first()

            if not book:
                return {}

            # Get chapters
            statement = (
                select(Chapter)
                .where(Chapter.book_id == book_id)
                .order_by(Chapter.chapter_number)
            )
            result = await self.session.exec(statement)
            chapters = result.all()

            # Create summary of chapters
            chapters_summary = ""
            for chapter in chapters:
                summary = chapter.summary or chapter.content[:500]
                chapters_summary += (
                    f"Chapter {chapter.chapter_number}: {chapter.title}\n{summary}\n\n"
                )

            return {
                "book": book.model_dump(),
                "chapters_summary": chapters_summary,
                "chapter_count": len(chapters),
            }

        except Exception as e:
            logger.error(f"[PlotService] Error getting book context: {str(e)}")
            return {}

    async def _generate_plot_content(
        self,
        book_context: Dict[str, Any],
        plot_data: Dict[str, Any],
        model_tier: ModelTier,
    ) -> Dict[str, Any]:
        """
        Generate the plot overview content using AI.
        """
        book = book_context.get("book", {})
        chapters_summary = book_context.get("chapters_summary", "")[:2000]

        prompt = f"""
Analyze the following book content and generate a comprehensive plot overview.

BOOK INFORMATION:
Title: {book.get('title', '')}
Genre: {plot_data.get('genre') or book.get('genre', 'General')}
Story Type: {plot_data.get('story_type', 'Hero\'s Journey')}
Tone: {plot_data.get('tone', 'Engaging')}
Target Audience: {plot_data.get('audience', 'General')}

CONTENT SUMMARY:
{chapters_summary}

USER NOTES:
{plot_data.get('logline', '')}

TASK:
Generate a structured plot overview including:
1. Logline (1-2 sentences)
2. Themes (list of 3-5 major themes)
3. Story Arc Summary (3 paragraphs: Setup, Confrontation, Resolution)
4. Setting Description

RESPONSE FORMAT:
Return ONLY a valid JSON object with the following keys:
{{
    "logline": "...",
    "themes": ["theme1", "theme2", ...],
    "story_type": "{plot_data.get('story_type', 'Hero\'s Journey')}",
    "script_story_type": "fiction",
    "genre": "{plot_data.get('genre') or book.get('genre', 'General')}",
    "tone": "{plot_data.get('tone', 'Engaging')}",
    "audience": "{plot_data.get('audience', 'General')}",
    "setting": "...",
    "status": "completed"
}}
"""

        response = await self.openrouter.analyze_content(
            content=prompt, user_tier=model_tier, analysis_type="plot_generation"
        )

        model_used = response.get("model") or response.get("model_used")

        if response.get("status") == "success":
            raw_result = response.get("result", "{}")

            try:
                result = json.loads(raw_result)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                logger.warning(
                    "[PlotService] Initial JSON parse failed, trying to extract from markdown"
                )
                import re

                json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_result)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                        logger.info(
                            "[PlotService] Successfully extracted JSON from markdown"
                        )
                    except json.JSONDecodeError:
                        result = None
                else:
                    result = None

            if result:
                # Ensure defaults
                result["generation_method"] = "openrouter"
                result["model_used"] = model_used
                result["generation_cost"] = response.get("cost", 0.0)
                return result
            else:
                logger.error(
                    f"[PlotService] Failed to parse plot JSON response. Raw: {raw_result[:500]}"
                )
                # Fallback to basic structure - still include model info
                return {
                    "logline": "AI generated a plot but response format was unexpected. Please try again.",
                    "themes": ["General"],
                    "status": "completed",
                    "generation_method": "openrouter_fallback",
                    "model_used": model_used,
                }
        else:
            error_msg = response.get("error", "Unknown error")
            logger.error(f"[PlotService] Plot generation failed: {error_msg}")
            raise PlotGenerationError(f"AI generation failed: {error_msg}")

    async def _generate_characters(
        self,
        book_context: Dict[str, Any],
        plot_data: Dict[str, Any],
        model_tier: ModelTier,
    ) -> List[Dict[str, Any]]:
        """
        Generate character profiles based on the book and plot.
        """
        book = book_context.get("book", {})
        chapters_summary = book_context.get("chapters_summary", "")[:2000]

        prompt = f"""
Based on the book content and plot overview, identify and profile the key characters.

BOOK: {book.get('title', '')}
PLOT LOGLINE: {plot_data.get('logline', '')}

CONTENT SUMMARY:
{chapters_summary}

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

Extract main and important supporting characters (aim for 5-10 key characters).
Focus on characters who actually appear in the story, not locations or objects.
"""

        response = await self.openrouter.analyze_content(
            content=prompt, user_tier=model_tier, analysis_type="character_generation"
        )

        if response.get("status") == "success":
            result = response.get("result", "")
            if result:
                return self._parse_character_generation_response(result)
            else:
                logger.warning(
                    "[PlotService] Character generation returned empty result"
                )
                return []
        else:
            error_msg = response.get("error", "Unknown error")
            logger.warning(f"[PlotService] Character generation failed: {error_msg}")
            return []

    def _parse_character_generation_response(
        self, ai_response: str
    ) -> List[Dict[str, Any]]:
        """
        Parse the AI response for character generation.
        """
        import re

        # First try direct JSON parsing
        try:
            characters = json.loads(ai_response.strip())
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", ai_response)
            if json_match:
                try:
                    characters = json.loads(json_match.group(1))
                    logger.info(
                        "[PlotService] Successfully extracted character JSON from markdown"
                    )
                except json.JSONDecodeError:
                    characters = None
            else:
                characters = None

        if characters is None:
            # Fallback: extract information from text response
            logger.warning(
                "[PlotService] Character response not valid JSON, attempting text parsing"
            )
            return self._parse_character_generation_text_response(ai_response)

        if not isinstance(characters, list):
            characters = [characters]

        # Validate and clean character data
        validated_characters = []
        for char in characters:
            if isinstance(char, dict) and char.get("name"):
                validated_characters.append(
                    {
                        "name": char.get("name", ""),
                        "role": char.get("role", "supporting"),
                        "character_arc": char.get("character_arc", ""),
                        "physical_description": char.get("physical_description", ""),
                        "personality": char.get("personality", ""),
                        "want": char.get("want", ""),
                        "need": char.get("need", ""),
                        "lie": char.get("lie", ""),
                        "ghost": char.get("ghost", ""),
                        "archetypes": [],
                        "generation_method": "openrouter",
                    }
                )

        return validated_characters[:5]  # Limit to 5 characters

    def _parse_character_generation_text_response(
        self, ai_response: str
    ) -> List[Dict[str, Any]]:
        """
        Parse character generation response from text when JSON parsing fails.
        """
        import re

        logger.info(
            f"[PlotService] Parsing character text response: {ai_response[:500]}..."
        )

        characters = []

        # Split response into character sections
        # Look for patterns like "Character 1:", "1.", or just numbered sections
        character_sections = re.split(
            r"(?:^|\n)(?:Character\s*\d+:?|^\d+\.|\n\d+\.)\s*",
            ai_response.strip(),
            flags=re.MULTILINE | re.IGNORECASE,
        )

        # Remove empty sections
        character_sections = [
            section.strip() for section in character_sections if section.strip()
        ]

        for section in character_sections[:5]:  # Limit to 5 characters
            character_data = {
                "name": self._extract_character_field_from_text(section, "name"),
                "role": self._extract_character_field_from_text(section, "role"),
                "character_arc": self._extract_character_field_from_text(
                    section, "character_arc"
                ),
                "physical_description": self._extract_character_field_from_text(
                    section, "physical_description"
                ),
                "personality": self._extract_character_field_from_text(
                    section, "personality"
                ),
                "want": self._extract_character_field_from_text(section, "want"),
                "need": self._extract_character_field_from_text(section, "need"),
                "lie": self._extract_character_field_from_text(section, "lie"),
                "ghost": self._extract_character_field_from_text(section, "ghost"),
                "archetypes": [],
                "generation_method": "openrouter_text_fallback",
            }

            # Only include characters that have at least a name
            if character_data["name"]:
                characters.append(character_data)

        logger.info(f"[PlotService] Extracted {len(characters)} characters from text")
        return characters

    def _extract_character_field_from_text(
        self, text: str, field_name: str
    ) -> Optional[str]:
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
            rf"{field_name.replace('_', ' ').capitalize()}:\s*([^\n\r]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Clean up common artifacts
                value = re.sub(r"^[-•*]\s*", "", value)  # Remove bullets
                value = re.sub(r"\s*$", "", value)  # Remove trailing whitespace
                return value if value else None

        return None

    async def _generate_fictional_story_type_for_nonfiction(
        self,
        book_context: Dict[str, Any],
        plot_data: Dict[str, Any],
        model_tier: ModelTier,
    ) -> str:
        """
        Generate an interesting fictional story type for non-fiction content.
        Uses AI to create a compelling narrative framework.
        """
        try:
            book = book_context.get("book", {})
            chapters_summary = book_context.get("chapters_summary", "")[:1000]

            prompt = f"""Based on this non-fiction content, suggest ONE interesting fictional story type that would make an engaging video narrative.

BOOK INFORMATION:
Title: {book.get('title', '')}
Genre: Non-fiction
Description: {book.get('description', '')}

CONTENT PREVIEW:
{chapters_summary}

TASK:
Suggest a single compelling fictional story type that could frame this non-fiction content (e.g., "detective investigation", "hero's journey", "underdog story", "mystery thriller", "exploration adventure", "transformation story", "conflict and resolution", "quest narrative").

Return ONLY the story type name (2-4 words maximum), no explanation."""

            response = await self.openrouter.analyze_content(
                content=prompt, user_tier=model_tier, analysis_type="summary"
            )

            if response.get("status") == "success":
                story_type = response.get("result", "documentary narrative").strip()
                # Clean up any extra text, keep only first line
                story_type = story_type.split("\n")[0].strip("\"'").strip()
                # Limit length
                if len(story_type) > 50:
                    story_type = "documentary narrative"
                return story_type.lower()
            else:
                return "documentary narrative"

        except Exception as e:
            logger.error(
                f"[PlotService] Error generating fictional story type: {str(e)}"
            )
            return "documentary narrative"

    async def _analyze_character_archetypes(
        self, character: Dict[str, Any], model_tier: ModelTier
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
                content=prompt, user_tier=model_tier, analysis_type="archetype_analysis"
            )

            if response["status"] == "success":
                try:
                    analysis = json.loads(response["result"])
                    return {
                        "archetypes": analysis.get("archetypes", []),
                        "analysis": analysis.get("analysis", ""),
                    }
                except json.JSONDecodeError:
                    pass

            # Fallback: return basic archetype based on role
            role_archetypes = {
                "protagonist": ["The Hero"],
                "antagonist": ["The Shadow"],
                "mentor": ["The Mentor"],
                "supporting": ["The Ally"],
            }

            return {
                "archetypes": role_archetypes.get(
                    character.get("role", "supporting"), ["The Ally"]
                ),
                "analysis": f"Basic archetype assignment based on character role: {character.get('role', 'supporting')}",
            }

        except Exception as e:
            logger.error(f"[PlotService] Error analyzing archetypes: {str(e)}")
            return {"archetypes": [], "analysis": "Archetype analysis failed"}

    async def _store_plot_overview(
        self,
        plot_data: Dict[str, Any],
        characters: List[Dict[str, Any]],
        user_id: uuid.UUID,
        book_id: uuid.UUID,
        book_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Store plot overview and characters in database.
        """
        try:
            # Query current maximum version for this book and user
            statement = (
                select(PlotOverview)
                .where(PlotOverview.book_id == book_id, PlotOverview.user_id == user_id)
                .order_by(desc(PlotOverview.version))
                .limit(1)
            )

            result = await self.session.exec(statement)
            existing_plot = result.first()

            if existing_plot:
                version = existing_plot.version + 1
            else:
                version = 1

            # Prepare plot overview data with defaults for missing fields
            themes_value = plot_data.get("themes", [])
            if not themes_value:
                themes_value = ["adventure", "growth"]  # Default themes

            logger.info(
                f"[PlotService] Storing themes - type: {type(themes_value)}, value: {themes_value}"
            )

            plot_overview = PlotOverview(
                book_id=book_id,
                user_id=user_id,
                logline=plot_data.get("logline")
                or f"A compelling {plot_data.get('genre', 'fiction')} story about personal growth and discovery.",
                themes=themes_value,
                story_type=plot_data.get("story_type") or "hero's journey",
                script_story_type=plot_data.get("script_story_type")
                or plot_data.get("story_type")
                or "hero's journey",
                genre=plot_data.get("genre")
                or book_context.get("book", {}).get("genre", "fiction"),
                tone=plot_data.get("tone") or "hopeful",
                audience=plot_data.get("audience") or "adult",
                setting=plot_data.get("setting") or "Contemporary world",
                generation_method=plot_data.get("generation_method", "openrouter"),
                model_used=plot_data.get("model_used"),
                status=plot_data.get("status", "completed"),
                version=version,
            )

            # Insert plot overview
            self.session.add(plot_overview)
            await self.session.commit()
            await self.session.refresh(plot_overview)
            plot_id = plot_overview.id

            # Store characters
            stored_characters = []
            for char_data in characters:
                character = Character(
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
                )

                # Insert character
                self.session.add(character)
                await self.session.commit()
                await self.session.refresh(character)

                # Create response object - convert UUIDs to strings
                stored_char = CharacterResponse(
                    id=str(character.id),
                    plot_overview_id=str(plot_id),
                    book_id=str(book_id),
                    user_id=str(user_id),
                    name=character.name,
                    role=character.role,
                    character_arc=character.character_arc,
                    physical_description=character.physical_description,
                    personality=character.personality,
                    archetypes=character.archetypes,
                    want=character.want,
                    need=character.need,
                    lie=character.lie,
                    ghost=character.ghost,
                    generation_method="openrouter",
                    model_used=plot_data.get("model_used"),
                    created_at=character.created_at,
                    updated_at=character.updated_at,
                )

                stored_characters.append(stored_char)

            # Debug: Log characters data before creating response
            logger.info(
                f"[PlotService] Creating PlotOverviewResponse - stored_characters count: {len(stored_characters)}"
            )
            if stored_characters:
                logger.info(
                    f"[PlotService] First character: {stored_characters[0].name if stored_characters[0] else 'None'}"
                )

            # Create plot overview response with defaults - convert UUIDs to strings
            plot_response = PlotOverviewResponse(
                id=str(plot_overview.id),
                book_id=str(plot_overview.book_id),
                user_id=str(plot_overview.user_id),
                logline=plot_overview.logline,
                themes=plot_overview.themes,
                story_type=plot_overview.story_type,
                script_story_type=plot_overview.script_story_type,
                genre=plot_overview.genre,
                tone=plot_overview.tone,
                audience=plot_overview.audience,
                setting=plot_overview.setting,
                generation_method=plot_overview.generation_method,
                model_used=plot_overview.model_used,
                generation_cost=0.0,  # Not stored in model currently
                status=plot_overview.status,
                version=plot_overview.version,
                characters=stored_characters,  # Add missing characters field
                created_at=plot_overview.created_at,
                updated_at=plot_overview.updated_at,
            )

            logger.info(
                f"[PlotService] PlotOverviewResponse created with characters field: {len(plot_response.characters) if hasattr(plot_response, 'characters') else 'MISSING'}"
            )

            return {
                "plot_overview": plot_response,
                "characters": stored_characters,
                "message": f"Successfully generated plot overview with {len(stored_characters)} characters",
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
            "professional": ModelTier.PROFESSIONAL,
        }

        # Handle both enum and string inputs
        tier_key = (
            subscription_tier.value
            if hasattr(subscription_tier, "value")
            else str(subscription_tier).lower()
        )

        return tier_mapping.get(tier_key, ModelTier.FREE)

    async def enhance_script_with_plot(
        self,
        chapter_id: uuid.UUID,
        plot_overview_id: uuid.UUID,
        existing_script: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enhance existing script with plot context and character information.
        """
        try:
            # Get plot overview and characters
            statement = select(PlotOverview).where(PlotOverview.id == plot_overview_id)
            result = await self.session.exec(statement)
            plot_overview = result.first()

            if not plot_overview:
                raise ValueError(f"Plot overview {plot_overview_id} not found")

            # Get characters for this plot
            statement = select(Character).where(
                Character.plot_overview_id == plot_overview_id
            )
            result = await self.session.exec(statement)
            characters = result.all()

            # Get chapter information
            statement = select(Chapter).where(Chapter.id == chapter_id)
            result = await self.session.exec(statement)
            chapter = result.first()

            if not chapter:
                raise ValueError(f"Chapter {chapter_id} not found")

            # Build enhancement prompt
            enhancement_prompt = self._build_script_enhancement_prompt(
                existing_script,
                plot_overview.model_dump(),
                [c.model_dump() for c in characters],
                chapter.model_dump(),
            )

            # Use RAG service to enhance the script
            # Note: RAGService.generate_video_script expects chapter_context
            enhanced_script_result = await self.rag_service.generate_video_script(
                chapter_context={
                    "chapter": chapter.model_dump(),
                    "book": {
                        "title": "Unknown"
                    },  # Simplified context, ideally fetch book
                    "plot_overview": plot_overview.model_dump(),
                },
                video_style="cinematic",
                script_style="cinematic_movie",
            )

            enhanced_script = enhanced_script_result.get(
                "script", existing_script.get("script", "")
            )

            # Store enhanced script in chapter_scripts table
            # Check if exists
            statement = select(ChapterScript).where(
                ChapterScript.chapter_id == chapter_id
            )
            result = await self.session.exec(statement)
            chapter_script = result.first()

            if not chapter_script:
                chapter_script = ChapterScript(
                    chapter_id=chapter_id,
                    plot_overview_id=plot_overview_id,
                    user_id=plot_overview.user_id,
                    version=existing_script.get("version", 0) + 1,
                )
            else:
                chapter_script.version += 1
                chapter_script.updated_at = datetime.now()

            chapter_script.plot_enhanced = True
            chapter_script.character_enhanced = True
            chapter_script.scenes = existing_script.get("scenes", {})
            chapter_script.character_details = {
                c.name: c.character_arc for c in characters
            }  # Simplified mapping
            chapter_script.character_arcs = {
                c.name: c.character_arc for c in characters
            }
            chapter_script.status = "enhanced"
            chapter_script.generation_metadata = {
                "plot_overview_used": str(plot_overview_id),
                "characters_integrated": len(characters),
                "enhancement_type": "plot_aware",
            }

            self.session.add(chapter_script)
            await self.session.commit()

            return {
                "enhanced_script": enhanced_script,
                "plot_integration": {
                    "plot_overview_id": plot_overview_id,
                    "characters_used": len(characters),
                    "themes_integrated": plot_overview.themes,
                },
                "status": "enhanced",
            }

        except Exception as e:
            logger.error(f"[PlotService] Error enhancing script: {str(e)}")
            return existing_script

    def _build_script_enhancement_prompt(
        self,
        existing_script: Dict[str, Any],
        plot_overview: Dict[str, Any],
        characters: List[Dict[str, Any]],
        chapter: Dict[str, Any],
    ) -> str:
        """
        Build prompt for script enhancement with plot context.
        """
        characters_text = "\n".join(
            [
                f"- {char['name']}: {char.get('role', 'unknown')} - {char.get('personality', '')}"
                for char in characters
            ]
        )

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

    async def get_plot_overview(
        self, user_id: uuid.UUID, book_id: uuid.UUID
    ) -> Optional[PlotOverviewResponse]:
        """
        Retrieve existing plot overview for a book.
        """
        try:
            # Get plot overview
            statement = (
                select(PlotOverview)
                .where(PlotOverview.book_id == book_id, PlotOverview.user_id == user_id)
                .order_by(desc(PlotOverview.version))
                .limit(1)
            )

            result = await self.session.exec(statement)
            plot_data = result.first()

            if not plot_data:
                return None

            # Get associated characters (ordered by creation time for consistent display)
            statement = (
                select(Character)
                .where(Character.plot_overview_id == plot_data.id)
                .order_by(Character.created_at)
            )
            result = await self.session.exec(statement)
            characters_data = result.all()

            characters = []
            for char_data in characters_data:
                char_response = CharacterResponse(
                    id=str(char_data.id),
                    plot_overview_id=str(char_data.plot_overview_id),
                    book_id=str(char_data.book_id),
                    user_id=str(char_data.user_id),
                    name=char_data.name,
                    role=char_data.role,
                    character_arc=char_data.character_arc,
                    physical_description=char_data.physical_description,
                    personality=char_data.personality,
                    archetypes=char_data.archetypes,
                    want=char_data.want,
                    need=char_data.need,
                    lie=char_data.lie,
                    ghost=char_data.ghost,
                    generation_method="openrouter",
                    model_used=plot_data.model_used,
                    created_at=char_data.created_at,
                    updated_at=char_data.updated_at,
                )
                characters.append(char_response)

            # Create plot overview response - convert UUIDs to strings
            plot_overview = PlotOverviewResponse(
                id=str(plot_data.id),
                book_id=str(plot_data.book_id),
                user_id=str(plot_data.user_id),
                logline=plot_data.logline,
                themes=plot_data.themes,
                story_type=plot_data.story_type,
                script_story_type=plot_data.script_story_type,
                genre=plot_data.genre,
                tone=plot_data.tone,
                audience=plot_data.audience,
                setting=plot_data.setting,
                generation_method=plot_data.generation_method,
                model_used=plot_data.model_used,
                generation_cost=0.0,
                status=plot_data.status,
                version=plot_data.version,
                characters=characters,
                created_at=plot_data.created_at,
                updated_at=plot_data.updated_at,
            )

            return plot_overview

        except Exception as e:
            logger.error(f"[PlotService] Error retrieving plot overview: {str(e)}")
            return None

    async def update_plot_overview(
        self, user_id: uuid.UUID, plot_id: uuid.UUID, updates: PlotOverviewUpdate
    ) -> PlotOverviewResponse:
        """
        Update existing plot overview.
        """
        try:
            # Get current plot overview
            statement = select(PlotOverview).where(
                PlotOverview.id == plot_id, PlotOverview.user_id == user_id
            )
            result = await self.session.exec(statement)
            current_data = result.first()

            if not current_data:
                raise ValueError(f"Plot overview {plot_id} not found or access denied")

            # Prepare update data
            has_updates = False
            for field in [
                "logline",
                "themes",
                "story_type",
                "script_story_type",
                "genre",
                "tone",
                "audience",
                "setting",
                "generation_method",
                "model_used",
                "status",
                "version",
            ]:
                if hasattr(updates, field) and getattr(updates, field) is not None:
                    setattr(current_data, field, getattr(updates, field))
                    has_updates = True

            # Get associated characters
            statement = select(Character).where(Character.plot_overview_id == plot_id)
            result = await self.session.exec(statement)
            characters_data = result.all()

            characters = []
            for char_data in characters_data:
                char_response = CharacterResponse(
                    id=char_data.id,
                    plot_overview_id=char_data.plot_overview_id,
                    book_id=char_data.book_id,
                    user_id=char_data.user_id,
                    name=char_data.name,
                    role=char_data.role,
                    character_arc=char_data.character_arc,
                    physical_description=char_data.physical_description,
                    personality=char_data.personality,
                    archetypes=char_data.archetypes,
                    want=char_data.want,
                    need=char_data.need,
                    lie=char_data.lie,
                    ghost=char_data.ghost,
                    generation_method="openrouter",
                    model_used=current_data.model_used,
                    created_at=char_data.created_at,
                    updated_at=char_data.updated_at,
                )
                characters.append(char_response)

            if has_updates:
                current_data.updated_at = datetime.now()
                self.session.add(current_data)
                await self.session.commit()
                await self.session.refresh(current_data)

            return PlotOverviewResponse(
                id=current_data.id,
                book_id=current_data.book_id,
                user_id=current_data.user_id,
                logline=current_data.logline,
                themes=current_data.themes,
                story_type=current_data.story_type,
                script_story_type=current_data.script_story_type,
                genre=current_data.genre,
                tone=current_data.tone,
                audience=current_data.audience,
                setting=current_data.setting,
                generation_method=current_data.generation_method,
                model_used=current_data.model_used,
                generation_cost=0.0,
                status=current_data.status,
                version=current_data.version,
                characters=characters,
                created_at=current_data.created_at,
                updated_at=current_data.updated_at,
            )

        except Exception as e:
            logger.error(f"[PlotService] Error updating plot overview: {str(e)}")
            raise PlotGenerationError(f"Failed to update plot overview: {str(e)}")
