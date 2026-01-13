from typing import Dict, Any, List, Optional
import uuid
import json
import re
from datetime import datetime, timezone

from app.core.database import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, update, delete
from app.core.services.openrouter import OpenRouterService, ModelTier
from app.api.services.subscription import SubscriptionManager
from app.core.services.modelslab_v7_image import ModelsLabV7ImageService
from app.core.services.embeddings import EmbeddingsService
from app.plots.models import Character, PlotOverview, CharacterArchetype
from app.books.models import Book
from app.videos.models import Script, ImageGeneration
from app.plots.schemas import (
    CharacterResponse,
    CharacterCreate,
    CharacterUpdate,
    CharacterArchetypeResponse,
    CharacterArchetypeMatch,
)
from app.core.logging import get_logger

logger = get_logger()


class CharacterServiceError(Exception):
    """Custom exception for character service errors"""

    pass


class CharacterNotFoundError(CharacterServiceError):
    """Exception raised when character is not found"""

    pass


class PermissionDeniedError(CharacterServiceError):
    """Exception raised when user doesn't have permission"""

    pass


class ImageGenerationError(CharacterServiceError):
    """Exception raised when image generation fails"""

    pass


class ArchetypeAnalysisError(CharacterServiceError):
    """Exception raised when archetype analysis fails"""

    pass


class CharacterService:
    """
    Core character management service that handles character archetype analysis,
    image generation, character data management for the plot generation system,
    and non-fiction persona generation for Phase 1B readiness.
    Adds support for linking characters to scripts, managing image URLs, retrieving all book characters, and handling character-to-voice mappings.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.openrouter = OpenRouterService()
        self.subscription_manager = SubscriptionManager(self.session)
        self.image_service = ModelsLabV7ImageService()
        self.embeddings_service = EmbeddingsService(self.session)

        # Default archetypes for initial setup
        self._default_archetypes = self._get_default_archetypes()

    async def generate_character_details_from_book(
        self,
        character_name: str,
        book_id: str,
        user_id: str,
        role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate detailed character information by analyzing book content.
        Uses AI to extract or infer character details based on the character name and book context.
        Respects user tier for AI model selection.
        """
        try:
            logger.info(
                f"[CharacterService] Generating AI-assisted details for character: {character_name}"
            )

            # Get user tier for AI model selection
            user_tier = await self.subscription_manager.get_user_tier(user_id)
            model_tier = self._map_subscription_to_model_tier(user_tier)

            logger.info(
                f"[CharacterService] Using model tier: {model_tier.value} for user tier: {user_tier.value}"
            )

            # Get book context (uses RAG if available)
            book_context = await self._get_book_context_for_character(
                book_id=book_id, character_name=character_name
            )
            if not book_context:
                raise CharacterServiceError("Unable to retrieve book context")

            # Build AI prompt for character detail generation
            prompt = self._build_character_detail_prompt(
                character_name=character_name, book_context=book_context, role=role
            )

            # Use OpenRouter to generate character details
            response = await self.openrouter.analyze_content(
                content=prompt, user_tier=model_tier, analysis_type="character_details"
            )

            if response["status"] != "success":
                raise CharacterServiceError(
                    f"AI character generation failed: {response.get('error', 'Unknown error')}"
                )

            # Parse the AI response
            character_details = self._parse_character_details_response(
                response["result"], character_name, role
            )

            logger.info(
                f"[CharacterService] Successfully generated details for character: {character_name}"
            )

            return character_details

        except Exception as e:
            logger.error(
                f"[CharacterService] Error generating character details: {str(e)}"
            )
            raise CharacterServiceError(
                f"Failed to generate character details: {str(e)}"
            )

    async def generate_non_fiction_personas(
        self,
        content: str,
        genre: str = "educational",
        num_personas: int = 5,
        user_tier: str = "free",
    ) -> List[Dict[str, Any]]:
        """
        Generate fictional personas based on non-fiction content.
        Returns structured persona data with appropriate archetypes.
        """
        try:
            logger.info(
                "[CharacterService] Starting fictional persona generation for non-fiction content"
            )
            # Define fictional archetypes for non-fiction adaptation
            fictional_archetypes = [
                {
                    "name": "Protagonist",
                    "description": "The central character driving the story forward",
                    "category": "Fiction",
                    "traits": {
                        "leadership": 0.9,
                        "determination": 0.8,
                        "charisma": 0.7,
                    },
                    "typical_roles": ["hero", "main character"],
                    "is_active": True,
                },
                {
                    "name": "Mentor",
                    "description": "A wise figure offering guidance and support",
                    "category": "Fiction",
                    "traits": {"wisdom": 0.9, "guidance": 0.8, "experience": 0.7},
                    "typical_roles": ["teacher", "guide"],
                    "is_active": True,
                },
                {
                    "name": "Antagonist",
                    "description": "The opposing force creating conflict in the story",
                    "category": "Fiction",
                    "traits": {"ambition": 0.9, "opposition": 0.8, "power": 0.7},
                    "typical_roles": ["villain", "rival"],
                    "is_active": True,
                },
                {
                    "name": "Sidekick",
                    "description": "A loyal companion supporting the protagonist",
                    "category": "Fiction",
                    "traits": {"loyalty": 0.9, "support": 0.8, "friendship": 0.7},
                    "typical_roles": ["companion", "ally"],
                    "is_active": True,
                },
                {
                    "name": "Comic Relief",
                    "description": "Provides humor and lightens the mood",
                    "category": "Fiction",
                    "traits": {"humor": 0.9, "wit": 0.8, "charm": 0.7},
                    "typical_roles": ["jester", "funny friend"],
                    "is_active": True,
                },
            ]
            # Compose AI prompt for fictional persona analysis
            prompt = f"""
            Analyze the following non-fiction content and generate {num_personas} fictional personas suitable for the genre '{genre}'.
            Each persona should be one of: Protagonist, Mentor, Antagonist, Sidekick, Comic Relief.
            For each persona, provide:
            - Persona type (from the list above)
            - Name (invented)
            - Brief description
            - Key traits
            - Archetype match (from the fictional archetypes)
            Return a JSON array of persona objects.
            Content:
            {content}
            """
            # Use OpenRouterService for AI analysis
            response = await self.openrouter.analyze_content(
                content=prompt,
                user_tier=getattr(ModelTier, user_tier.upper(), ModelTier.FREE),
                analysis_type="characters",
            )
            if response["status"] == "success":
                try:
                    personas = json.loads(response["result"])
                    # Attach archetype details to each persona
                    for persona in personas:
                        match = next(
                            (
                                a
                                for a in fictional_archetypes
                                if a["name"].lower()
                                == persona.get("persona_type", "").lower()
                            ),
                            None,
                        )
                        persona["archetype"] = match if match else {}
                    return personas
                except Exception as e:
                    logger.warning(
                        f"[CharacterService] AI response not valid JSON for fictional personas: {str(e)}"
                    )
                    return []
            else:
                logger.warning(
                    f"[CharacterService] Fictional persona generation failed: {response.get('error')}"
                )
                return []
        except Exception as e:
            logger.error(
                f"[CharacterService] Error generating fictional personas: {str(e)}"
            )
            return []

    async def analyze_character_archetypes(
        self, character_description: str, personality: str
    ) -> CharacterArchetypeMatch:
        """
        Analyzes character description using AI to match against Jungian archetypes.
        Returns archetype matches with confidence scores.
        """
        try:
            logger.info("[CharacterService] Starting archetype analysis")

            # Check if user has premium access for archetype analysis
            # This would be checked in the calling context

            # Get all available archetypes
            archetypes = await self._get_all_archetypes()

            # Use AI to analyze character against archetypes
            analysis_result = await self._analyze_archetype_match(
                {"description": character_description, "personality": personality},
                archetypes,
            )

            # Find the best match
            if analysis_result:
                best_match = max(analysis_result, key=lambda x: x.get("confidence", 0))
                return CharacterArchetypeMatch(
                    character_id="",  # Will be set by caller
                    archetype_id=best_match["archetype_id"],
                    match_score=best_match["confidence"],
                    matched_traits=best_match.get("matched_traits", []),
                    analysis=best_match.get("analysis", ""),
                )
            else:
                # Return fallback match
                return CharacterArchetypeMatch(
                    character_id="",
                    archetype_id="",
                    match_score=0.0,
                    matched_traits=[],
                    analysis="No archetype match found",
                )

        except Exception as e:
            logger.error(f"[CharacterService] Error analyzing archetypes: {str(e)}")
            raise ArchetypeAnalysisError(f"Archetype analysis failed: {str(e)}")

    async def generate_character_image(
        self,
        character_id: str,
        user_id: str,
        custom_prompt: Optional[str] = None,
        style: str = "realistic",
        aspect_ratio: str = "3:4",
    ) -> Dict[str, Any]:
        """
        Generates character portrait using async Celery task.
        Returns task information for status tracking instead of blocking.
        """
        try:
            logger.info(
                f"[CharacterService] Queueing image generation for character {character_id}"
            )

            # Check subscription limits for image generation
            usage_check = await self.subscription_manager.check_usage_limits(
                user_id, "image"
            )
            if not usage_check["can_generate"]:
                raise CharacterServiceError(
                    f"Image generation limit exceeded for {usage_check['tier']} tier"
                )

            # Get user tier for model selection
            user_tier = usage_check["tier"]

            # Get character data
            character = await self.get_character_by_id(character_id, user_id)
            if not character:
                raise CharacterNotFoundError(f"Character {character_id} not found")

            # Build character description for image generation
            character_description = (
                character.physical_description
                or character.personality
                or f"Character portrait of {character.name}"
            )

            # Adjust prompt based on entity type
            if character.entity_type == "object":
                character_description = (
                    character.physical_description
                    or f"A detailed image of {character.name}"
                )
                if not custom_prompt:
                    # For objects, we want object-centric prompts
                    custom_prompt = (
                        f"Product shot, detailed, photorealistic, {style} style"
                    )

            # Create initial record in image_generations table
            from datetime import datetime, timezone
            import uuid

            image_record = ImageGeneration(
                user_id=uuid.UUID(str(user_id)),
                image_type="character",
                character_name=character.name,
                character_id=character_id,
                scene_description=character_description,
                status="pending",
                style=style,
                aspect_ratio=aspect_ratio,
                image_prompt=self._build_character_image_prompt(
                    character, custom_prompt
                ),
                meta={
                    "character_id": str(character_id),
                    "image_type": "character_portrait",
                    "created_via": "character_service",
                },
                video_generation_id=None,
            )
            self.session.add(image_record)
            await self.session.commit()
            await self.session.refresh(image_record)
            record_id = str(image_record.id)

            if not record_id:
                raise CharacterServiceError("Failed to create image generation record")

            # Queue the async task
            from app.tasks.image_tasks import generate_character_image_task
            from app.tasks.celery_app import celery_app

            # Debug: Log Celery configuration
            logger.info(
                f"[CharacterService] Celery broker URL: {celery_app.conf.broker_url}"
            )
            logger.info(
                f"[CharacterService] Celery default queue: {celery_app.conf.task_default_queue}"
            )

            try:
                task = generate_character_image_task.delay(
                    character_name=character.name,
                    character_description=character_description,
                    user_id=str(user_id),
                    character_id=str(character_id),
                    style=style,
                    aspect_ratio=aspect_ratio,
                    custom_prompt=custom_prompt,
                    record_id=record_id,
                    user_tier=user_tier,
                )
                logger.info(
                    f"[CharacterService] Task dispatched successfully! Task ID: {task.id}"
                )
            except Exception as dispatch_error:
                logger.error(
                    f"[CharacterService] FAILED to dispatch task: {dispatch_error}"
                )
                raise

            # Record usage immediately (image generation is queued)
            try:
                await self.subscription_manager.record_usage(
                    user_id=user_id,
                    resource_type="image",
                    cost_usd=0.0,
                    metadata={
                        "character_id": str(character_id),
                        "image_type": "character_portrait",
                        "task_id": task.id,
                    },
                )
            except Exception as usage_error:
                logger.warning(
                    f"[CharacterService] Failed to record usage: {str(usage_error)}"
                )

            logger.info(
                f"[CharacterService] Queued image generation task {task.id} for character {character_id}"
            )

            return {
                "character_id": character_id,
                "task_id": task.id,
                "record_id": record_id,
                "status": "queued",
                "message": "Character image generation has been queued",
                "estimated_time_seconds": 60,
            }

        except CharacterNotFoundError:
            raise
        except CharacterServiceError:
            raise
        except Exception as e:
            logger.error(
                f"[CharacterService] Error queueing character image generation: {str(e)}"
            )
            raise ImageGenerationError(f"Failed to queue image generation: {str(e)}")

    async def get_character_image_status(
        self, character_id: str, user_id: str
    ) -> Dict[str, Any]:
        """
        Get the current status of character image generation.
        """
        try:
            await self._validate_character_permissions(character_id, str(user_id))

            stmt = select(Character).where(Character.id == character_id)
            result = await self.session.exec(stmt)
            character = result.first()

            if not character:
                raise CharacterNotFoundError(f"Character {character_id} not found")

            # Get status directly from Character model
            status = character.image_generation_status or "none"
            task_id = character.image_generation_task_id
            image_url = character.image_url
            metadata = character.image_metadata or {}

            response = {
                "character_id": str(character_id),
                "status": status,
                "task_id": task_id,
                "image_url": image_url,
                "metadata": metadata,
                "model_used": character.model_used,
                "generation_method": character.generation_method,
            }

            if status == "failed" and metadata:
                response["error"] = metadata.get("error")

            return response

        except CharacterNotFoundError:
            raise
        except Exception as e:
            logger.error(f"[CharacterService] Error getting image status: {str(e)}")
            raise CharacterServiceError(f"Failed to get image status: {str(e)}")

    async def get_character_by_id(
        self, character_id: str, user_id: str
    ) -> Optional[CharacterResponse]:
        """
        Retrieve a character by ID with permission validation.
        """
        try:
            # Validate permissions
            await self._validate_character_permissions(character_id, user_id)

            stmt = select(Character).where(Character.id == character_id)
            result = await self.session.exec(stmt)
            character = result.first()

            if not character:
                return None

            # Fetch recent images for this character
            from app.videos.models import ImageGeneration

            # Ensure character_id is string for query if column is string
            char_id_str = str(character_id)

            stmt_images = (
                select(ImageGeneration)
                .where(ImageGeneration.character_id == char_id_str)
                .order_by(ImageGeneration.created_at.desc())
                .limit(50)
            )
            images_result = await self.session.exec(stmt_images)
            images = images_result.all()

            response = CharacterResponse.model_validate(character)
            response.images = [
                {
                    "id": str(img.id),
                    "image_url": img.image_url,
                    "status": img.status,
                    "created_at": img.created_at,
                    "model_used": img.model_id if hasattr(img, "model_id") else None,
                    "generation_method": "async",
                }
                for img in images
            ]
            return response

        except Exception as e:
            logger.error(
                f"[CharacterService] Error retrieving character {character_id}: {str(e)}"
            )
            return None

    async def update_character(
        self, character_id: str, user_id: str, updates: CharacterUpdate
    ) -> CharacterResponse:
        """
        Update character data with permission validation.
        """
        try:
            # Validate permissions
            await self._validate_character_permissions(character_id, user_id)

            # Prepare update data
            update_data = {}
            for field in [
                "name",
                "role",
                "character_arc",
                "physical_description",
                "personality",
                "archetypes",
                "want",
                "need",
                "lie",
                "ghost",
                "image_url",
                "image_generation_prompt",
                "image_metadata",
                "generation_method",
                "model_used",
                "entity_type",
            ]:
                if hasattr(updates, field) and getattr(updates, field) is not None:
                    update_data[field] = getattr(updates, field)

            if update_data:
                update_data["updated_at"] = datetime.now(timezone.utc)

                stmt = (
                    update(Character)
                    .where(Character.id == character_id)
                    .values(**update_data)
                    .execution_options(synchronize_session="fetch")
                )
                await self.session.exec(stmt)
                await self.session.commit()

                # Fetch updated character
                stmt = select(Character).where(Character.id == character_id)
                result = await self.session.exec(stmt)
                character = result.first()

                if character:
                    return CharacterResponse.model_validate(character)
                else:
                    raise CharacterNotFoundError(f"Character {character_id} not found")

            # No updates provided, return current data
            return await self.get_character_by_id(character_id, user_id)

        except CharacterNotFoundError:
            raise
        except PermissionDeniedError:
            raise
        except Exception as e:
            logger.error(
                f"[CharacterService] Error updating character {character_id}: {str(e)}"
            )
            raise CharacterServiceError(f"Failed to update character: {str(e)}")

    async def get_characters_by_plot(
        self, plot_overview_id: str, user_id: str
    ) -> List[CharacterResponse]:
        """
        Get all characters for a specific plot overview.
        """
        try:
            # First verify user has access to the plot overview
            stmt = select(PlotOverview.user_id).where(
                PlotOverview.id == plot_overview_id
            )
            result = await self.session.exec(stmt)
            plot_user_id = result.first()

            if not plot_user_id or str(plot_user_id) != user_id:
                raise PermissionDeniedError("Access denied to plot overview")

            stmt = select(Character).where(
                Character.plot_overview_id == plot_overview_id
            )
            result = await self.session.exec(stmt)
            characters = result.all()

            characters = result.all()

            # Collect all character IDs
            char_ids = [str(char.id) for char in characters]

            # Fetch images for all characters in one query (optimization)
            images_map = {}
            if char_ids:
                stmt_images = (
                    select(ImageGeneration)
                    .where(ImageGeneration.character_id.in_(char_ids))
                    .order_by(ImageGeneration.created_at.desc())
                )
                images_result = await self.session.exec(stmt_images)
                all_images = images_result.all()

                # Group by character_id
                for img in all_images:
                    c_id = img.character_id
                    if c_id not in images_map:
                        images_map[c_id] = []
                    images_map[c_id].append(img)

            results = []
            for char in characters:
                resp = CharacterResponse.model_validate(char)
                char_images = images_map.get(str(char.id), [])
                resp.images = [
                    {
                        "id": str(img.id),
                        "image_url": img.image_url,
                        "status": img.status,
                        "created_at": img.created_at,
                        "model_used": img.model_id,
                        "generation_method": "async",
                    }
                    for img in char_images[:20]  # Limit to 20 recent
                ]
                results.append(resp)

            return results

        except PermissionDeniedError:
            raise
        except Exception as e:
            logger.error(
                f"[CharacterService] Error retrieving characters for plot {plot_overview_id}: {str(e)}"
            )
            return []

    async def link_characters_to_script(
        self, script_id: str, character_ids: List[str], user_id: str
    ) -> bool:
        """
        Link characters to a script using the character_ids column in the scripts table.
        """
        try:
            # Validate all character IDs belong to the user
            for char_id in character_ids:
                char = await self.get_character_by_id(char_id, user_id)
                if not char:
                    raise CharacterNotFoundError(
                        f"Character {char_id} not found or access denied"
                    )

            # Update the script record
            stmt = (
                update(Script)
                .where(Script.id == script_id)
                .values(
                    characters=character_ids,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await self.session.exec(stmt)
            await self.session.commit()
            return True
        except Exception as e:
            logger.error(
                f"[CharacterService] Error linking characters to script {script_id}: {str(e)}"
            )
            return False

    async def update_character_image_url(
        self, character_id: str, image_url: str, user_id: str
    ) -> bool:
        """
        Update the image URL for a character.
        """
        try:
            await self._validate_character_permissions(character_id, user_id)

            stmt = (
                update(Character)
                .where(Character.id == character_id)
                .values(
                    image_url=image_url,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await self.session.exec(stmt)
            await self.session.commit()
            return True

        except Exception as e:
            logger.error(
                f"[CharacterService] Error updating character image URL: {str(e)}"
            )
            return False

    async def delete_character_image(
        self, character_id: str, image_id: str, user_id: str
    ) -> bool:
        """
        Delete a specific generated image for a character.
        If the image is the current default image, clears the default image.
        """
        try:
            await self._validate_character_permissions(character_id, user_id)

            # Get the image to verify ownership and existence
            stmt = select(ImageGeneration).where(
                ImageGeneration.id == image_id,
                ImageGeneration.character_id == str(character_id),
            )
            result = await self.session.exec(stmt)
            image = result.first()

            if not image:
                raise CharacterServiceError("Image not found")

            # Check if this is the current profile image
            char_stmt = select(Character).where(Character.id == character_id)
            char_result = await self.session.exec(char_stmt)
            character = char_result.first()

            if character and character.image_url == image.image_url:
                # Clear the default image if we're deleting it
                # Optionally, we could set it to the next available image
                character.image_url = None
                self.session.add(character)

            # Delete the image record
            await self.session.delete(image)
            await self.session.commit()
            return True

        except Exception as e:
            logger.error(
                f"[CharacterService] Error deleting character image {image_id}: {str(e)}"
            )
            return False

    async def get_all_characters_for_book(
        self, book_id: str, user_id: str
    ) -> List[CharacterResponse]:
        """
        Retrieve all characters for a given book.
        """
        try:
            # Validate user has access to the book
            stmt = select(Book.user_id).where(Book.id == book_id)
            result = await self.session.exec(stmt)
            book_user_id = result.first()

            if not book_user_id or str(book_user_id) != user_id:
                raise PermissionDeniedError("Access denied to book")

            stmt = select(Character).where(Character.book_id == book_id)
            result = await self.session.exec(stmt)
            characters = result.all()

            return [CharacterResponse.model_validate(char) for char in characters]
        except Exception as e:
            logger.error(
                f"[CharacterService] Error retrieving all characters for book {book_id}: {str(e)}"
            )
            return []

    async def set_character_voice_mapping(
        self, character_id: str, voice_id: str, user_id: str
    ) -> bool:
        """
        Set the voice mapping for a character.
        """
        try:
            await self._validate_character_permissions(character_id, user_id)

            stmt = (
                update(Character)
                .where(Character.id == character_id)
                .values(
                    voice_id=voice_id,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await self.session.exec(stmt)
            await self.session.commit()
            return True
        except Exception as e:
            logger.error(
                f"[CharacterService] Error setting voice mapping for character {character_id}: {str(e)}"
            )
            return False

    async def get_character_voice_mapping(
        self, character_id: str, user_id: str
    ) -> Optional[str]:
        """
        Get the voice mapping for a character.
        """
        try:
            await self._validate_character_permissions(character_id, user_id)

            stmt = select(Character.voice_id).where(Character.id == character_id)
            result = await self.session.exec(stmt)
            voice_id = result.first()

            return voice_id
        except Exception as e:
            logger.error(
                f"[CharacterService] Error retrieving voice mapping for character {character_id}: {str(e)}"
            )
            return None

    async def delete_character(self, character_id: str, user_id: str) -> bool:
        """
        Delete a character with permission validation.
        """
        try:
            # Validate permissions
            await self._validate_character_permissions(character_id, user_id)

            stmt = delete(Character).where(Character.id == character_id)
            await self.session.exec(stmt)
            await self.session.commit()

            return True

        except PermissionDeniedError:
            raise
        except Exception as e:
            logger.error(
                f"[CharacterService] Error deleting character {character_id}: {str(e)}"
            )
            return False

    async def create_character(
        self, plot_overview_id: str, user_id: str, character_data: CharacterCreate
    ) -> CharacterResponse:
        """
        Create a new character manually.
        """
        try:
            # Validate plot overview exists and user owns it
            stmt = select(PlotOverview).where(
                PlotOverview.id == plot_overview_id, PlotOverview.user_id == user_id
            )
            result = await self.session.exec(stmt)
            plot_overview = result.first()

            if not plot_overview:
                raise PermissionDeniedError("Plot overview not found or access denied")

            # Convert asyncpg UUID to Python UUID for proper serialization
            book_id = (
                uuid.UUID(str(plot_overview.book_id)) if plot_overview.book_id else None
            )

            # Create character record
            character = Character(
                id=uuid.uuid4(),
                plot_overview_id=uuid.UUID(plot_overview_id),
                book_id=book_id,
                user_id=uuid.UUID(user_id),
                name=character_data.name,
                entity_type=character_data.entity_type or "character",
                role=character_data.role or "",
                character_arc=character_data.character_arc or "",
                physical_description=character_data.physical_description or "",
                personality=character_data.personality or "",
                archetypes=character_data.archetypes or [],
                want=character_data.want or "",
                need=character_data.need or "",
                lie=character_data.lie or "",
                ghost=character_data.ghost or "",
                image_url=character_data.image_url,
                image_generation_prompt=character_data.image_generation_prompt,
                image_metadata=character_data.image_metadata or {},
                generation_method=character_data.generation_method or "manual",
                model_used=character_data.model_used,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            self.session.add(character)
            await self.session.commit()
            await self.session.refresh(character)

            # Manually construct response to handle asyncpg UUID conversion
            return CharacterResponse(
                id=str(character.id),
                plot_overview_id=str(character.plot_overview_id),
                book_id=str(character.book_id) if character.book_id else None,
                user_id=str(character.user_id),
                name=character.name,
                role=character.role or "",
                character_arc=character.character_arc or "",
                physical_description=character.physical_description or "",
                personality=character.personality or "",
                archetypes=character.archetypes or [],
                want=character.want or "",
                need=character.need or "",
                lie=character.lie or "",
                ghost=character.ghost or "",
                image_url=character.image_url,
                image_generation_prompt=character.image_generation_prompt,
                image_metadata=character.image_metadata or {},
                generation_method=character.generation_method or "manual",
                model_used=character.model_used,
                created_at=character.created_at,
                updated_at=character.updated_at,
            )

        except PermissionDeniedError:
            raise
        except Exception as e:
            logger.error(f"[CharacterService] Error creating character: {str(e)}")
            raise CharacterServiceError(f"Failed to create character: {str(e)}")

    async def get_all_archetypes(self) -> List[CharacterArchetypeResponse]:
        """
        Get all available character archetypes.
        """
        try:
            archetypes = await self._get_all_archetypes()
            return [CharacterArchetypeResponse(**arch) for arch in archetypes]

        except Exception as e:
            logger.error(f"[CharacterService] Error retrieving archetypes: {str(e)}")
            return []

    async def get_archetypes_by_category(
        self, category: str
    ) -> List[CharacterArchetypeResponse]:
        """
        Get archetypes filtered by category.
        """
        try:
            all_archetypes = await self._get_all_archetypes()
            filtered = [
                arch
                for arch in all_archetypes
                if arch.get("category", "").lower() == category.lower()
            ]
            return [CharacterArchetypeResponse(**arch) for arch in filtered]

        except Exception as e:
            logger.error(
                f"[CharacterService] Error retrieving archetypes by category {category}: {str(e)}"
            )
            return []

    async def populate_default_archetypes(self) -> int:
        """
        Populate the database with default archetype definitions.
        Returns the number of archetypes created.
        """
        try:
            created_count = 0

            for archetype_data in self._default_archetypes:
                # Check if archetype already exists
                existing = (
                    self.db.table("character_archetypes")
                    .select("id")
                    .eq("name", archetype_data["name"])
                    .execute()
                )

                if not existing.data:
                    archetype_data["id"] = str(uuid.uuid4())
                    archetype_data["created_at"] = datetime.now().isoformat()
                    archetype_data["updated_at"] = datetime.now().isoformat()

                    self.db.table("character_archetypes").insert(
                        archetype_data
                    ).execute()
                    created_count += 1

            logger.info(
                f"[CharacterService] Created {created_count} default archetypes"
            )
            return created_count

        except Exception as e:
            logger.error(
                f"[CharacterService] Error populating default archetypes: {str(e)}"
            )
            raise CharacterServiceError(f"Failed to populate archetypes: {str(e)}")

    def _build_character_image_prompt(
        self, character: CharacterResponse, custom_prompt: Optional[str] = None
    ) -> str:
        """
        Build optimized prompt for character image generation.
        """
        base_prompt = f"Professional character portrait of {character.name}"

        if character.physical_description:
            base_prompt += f", {character.physical_description}"

        if character.role:
            base_prompt += f", {character.role} in the story"

        if character.personality:
            # Extract key visual traits from personality
            visual_traits = []
            if "confident" in character.personality.lower():
                visual_traits.append("confident posture")
            if "mysterious" in character.personality.lower():
                visual_traits.append("enigmatic expression")
            if "wise" in character.personality.lower():
                visual_traits.append("wise eyes")
            if "young" in character.personality.lower():
                visual_traits.append("youthful appearance")
            if "old" in character.personality.lower():
                visual_traits.append("aged features")

            if visual_traits:
                base_prompt += f", showing {', '.join(visual_traits[:2])}"

        if custom_prompt:
            base_prompt += f", {custom_prompt}"

        # Add style modifiers for consistency
        base_prompt += ". Photorealistic, detailed facial features, professional lighting, high quality, 8k resolution, centered composition, clear background"

        return base_prompt

    async def _analyze_archetype_match(
        self, character_data: Dict[str, Any], archetypes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use AI to analyze character against archetypes and return matches with confidence scores.
        """
        try:
            # Prepare analysis prompt
            prompt = f"""
Analyze this character against the following Jungian archetypes and determine the best matches:

CHARACTER:
Description: {character_data.get('description', '')}
Personality: {character_data.get('personality', '')}

ARCHETYPES:
{json.dumps(archetypes, indent=2)}

For each archetype, provide:
1. Match confidence (0.0 to 1.0)
2. Key traits that match
3. Brief analysis of why it fits

Return a JSON array of matches sorted by confidence:
[
  {{
    "archetype_id": "id",
    "archetype_name": "name",
    "confidence": 0.85,
    "matched_traits": ["trait1", "trait2"],
    "analysis": "brief explanation"
  }}
]
"""

            # Use OpenRouter for analysis (assuming free tier for basic analysis)
            response = await self.openrouter.analyze_content(
                content=prompt,
                user_tier=ModelTier.FREE,  # Use free tier for archetype analysis
                analysis_type="archetype_analysis",
            )

            if response["status"] == "success":
                try:
                    matches = json.loads(response["result"])
                    return matches[:3]  # Return top 3 matches
                except json.JSONDecodeError:
                    logger.warning(
                        "[CharacterService] AI response not valid JSON for archetype analysis"
                    )
                    return []
            else:
                logger.warning(
                    f"[CharacterService] Archetype analysis failed: {response.get('error')}"
                )
                return []

        except Exception as e:
            logger.error(f"[CharacterService] Error in archetype matching: {str(e)}")
            return []

    async def _validate_character_permissions(
        self, character_id: str, user_id: str
    ) -> bool:
        """
        Validate that user has permission to access/modify the character.
        """
        try:
            stmt = select(Character.user_id).where(Character.id == character_id)
            result = await self.session.exec(stmt)
            character_user_id = result.first()

            if not character_user_id:
                logger.error(
                    f"[CharacterService] Character {character_id} not found in database or has no user_id"
                )
                # Also log if the ID exists but somehow query failed (sanity check)
                # But here we just know it's not found by ID
                raise CharacterNotFoundError(f"Character {character_id} not found")

            if str(character_user_id) != str(user_id):
                logger.error(
                    f"[CharacterService] Access denied: Character {character_id} owned by {character_user_id} but requested by {user_id}"
                )
                raise PermissionDeniedError("Access denied to character")

            return True

        except CharacterNotFoundError:
            raise
        except PermissionDeniedError:
            raise
        except Exception as e:
            logger.error(
                f"[CharacterService] Error validating permissions for character {character_id}: {str(e)}"
            )
            raise PermissionDeniedError("Permission validation failed")

    async def _update_character_image_metadata(
        self, character_id: str, image_data: Dict[str, Any]
    ) -> None:
        """
        Update character record with image metadata.
        """

        try:
            image_url = image_data.get("image_url")
            update_data = {
                "image_url": image_url,
                "image_generation_prompt": image_data.get("image_generation_prompt"),
                "image_metadata": image_data.get("image_metadata", {}),
                "updated_at": datetime.now(timezone.utc),
            }

            logger.info(f"[CharacterService] Updating character {character_id}")
            logger.info(f"[CharacterService] Update data: {update_data}")

            stmt = (
                update(Character)
                .where(Character.id == character_id)
                .values(**update_data)
                .execution_options(synchronize_session="fetch")
            )
            await self.session.exec(stmt)
            await self.session.commit()

            # Verify update
            stmt = select(Character).where(Character.id == character_id)
            result = await self.session.exec(stmt)
            updated_char = result.first()

            if not updated_char:
                logger.error(
                    f"[CharacterService] No character found to update with ID: {character_id}"
                )
                raise CharacterServiceError(
                    f"Character {character_id} not found for image update"
                )

            logger.info(
                f"[CharacterService] Successfully updated character {character_id} with image_url: {image_url}"
            )

        except Exception as e:
            logger.error(
                f"[CharacterService] Error updating character image metadata: {str(e)}"
            )
            logger.error(f"[CharacterService] Exception type: {type(e).__name__}")
            import traceback

            logger.error(f"[CharacterService] Traceback: {traceback.format_exc()}")
            raise CharacterServiceError(f"Failed to update image metadata: {str(e)}")

    async def _get_all_archetypes(self) -> List[Dict[str, Any]]:
        """
        Get all archetypes from database, falling back to defaults if empty.
        """
        try:
            stmt = select(CharacterArchetype).where(
                CharacterArchetype.is_active == True
            )
            result = await self.session.exec(stmt)
            archetypes = result.all()

            if archetypes:
                return [archetype.model_dump() for archetype in archetypes]
            else:
                # Return default archetypes if database is empty
                return self._default_archetypes

        except Exception as e:
            logger.error(
                f"[CharacterService] Error retrieving archetypes from database: {str(e)}"
            )
            return self._default_archetypes

    def _get_default_archetypes(self) -> List[Dict[str, Any]]:
        """
        Get the default set of Jungian and non-fiction archetypes.
        """
        return [
            # Non-fiction archetypes for Phase 1B
            {
                "name": "Narrator",
                "description": "Explains concepts and guides the audience",
                "category": "NonFiction",
                "traits": {"clarity": 0.9, "guidance": 0.8, "engagement": 0.7},
                "typical_roles": ["narrator", "guide"],
                "is_active": True,
            },
            {
                "name": "Expert",
                "description": "Provides authoritative insights and analysis",
                "category": "NonFiction",
                "traits": {"authority": 0.9, "insight": 0.8, "analysis": 0.7},
                "typical_roles": ["expert", "analyst"],
                "is_active": True,
            },
            {
                "name": "Interviewer",
                "description": "Asks questions and facilitates discussion",
                "category": "NonFiction",
                "traits": {"curiosity": 0.9, "facilitation": 0.8, "communication": 0.7},
                "typical_roles": ["interviewer", "host"],
                "is_active": True,
            },
            {
                "name": "Subject Matter Expert",
                "description": "Specialized knowledge in specific topics",
                "category": "NonFiction",
                "traits": {"expertise": 0.9, "depth": 0.8, "specialization": 0.7},
                "typical_roles": ["specialist", "consultant"],
                "is_active": True,
            },
            {
                "name": "Historical Figure",
                "description": "Represents real people from the content",
                "category": "NonFiction",
                "traits": {
                    "authenticity": 0.9,
                    "historical": 0.8,
                    "representation": 0.7,
                },
                "typical_roles": ["historical figure", "real person"],
                "is_active": True,
            },
            # Fiction archetypes (existing)
            {
                "name": "The Hero",
                "description": "The brave protagonist who embarks on a journey of growth and transformation",
                "category": "Ego",
                "traits": {
                    "bravery": 0.9,
                    "determination": 0.8,
                    "growth": 0.7,
                    "leadership": 0.6,
                },
                "typical_roles": ["protagonist", "warrior", "explorer"],
                "example_characters": "Luke Skywalker, Harry Potter, Frodo Baggins",
                "is_active": True,
            },
            {
                "name": "The Mentor",
                "description": "The wise guide who provides knowledge and support to the hero",
                "category": "Ego",
                "traits": {
                    "wisdom": 0.9,
                    "guidance": 0.8,
                    "experience": 0.8,
                    "support": 0.7,
                },
                "typical_roles": ["teacher", "guide", "elder"],
                "example_characters": "Obi-Wan Kenobi, Dumbledore, Gandalf",
                "is_active": True,
            },
            {
                "name": "The Shadow",
                "description": "The dark aspect representing repressed emotions and instincts",
                "category": "Shadow",
                "traits": {
                    "darkness": 0.9,
                    "opposition": 0.8,
                    "power": 0.7,
                    "threat": 0.7,
                },
                "typical_roles": ["antagonist", "villain", "tempter"],
                "example_characters": "Darth Vader, Voldemort, Sauron",
                "is_active": True,
            },
            {
                "name": "The Ally",
                "description": "The loyal companion who supports the hero's journey",
                "category": "Ego",
                "traits": {
                    "loyalty": 0.9,
                    "support": 0.8,
                    "friendship": 0.7,
                    "skill": 0.6,
                },
                "typical_roles": ["sidekick", "friend", "companion"],
                "example_characters": "Samwise Gamgee, Ron Weasley, Han Solo",
                "is_active": True,
            },
            {
                "name": "The Threshold Guardian",
                "description": "The gatekeeper who tests the hero and blocks the path",
                "category": "Ego",
                "traits": {
                    "testing": 0.8,
                    "blocking": 0.7,
                    "caution": 0.7,
                    "protection": 0.6,
                },
                "typical_roles": ["guardian", "challenger", "obstacle"],
                "example_characters": "The Doorkeeper, Border Guards, Cerberus",
                "is_active": True,
            },
            {
                "name": "The Shapeshifter",
                "description": "The mysterious figure who changes appearance and allegiance",
                "category": "Soul",
                "traits": {
                    "mystery": 0.9,
                    "change": 0.8,
                    "unpredictability": 0.7,
                    "complexity": 0.7,
                },
                "typical_roles": ["trickster", "spy", "enigma"],
                "example_characters": "Loki, Severus Snape, Catwoman",
                "is_active": True,
            },
            {
                "name": "The Trickster",
                "description": "The humorous disruptor who challenges the status quo",
                "category": "Soul",
                "traits": {
                    "humor": 0.8,
                    "disruption": 0.8,
                    "wisdom": 0.6,
                    "unconventional": 0.7,
                },
                "typical_roles": ["jester", "fool", "disruptor"],
                "example_characters": "The Joker, Puck, Loki",
                "is_active": True,
            },
            {
                "name": "The Anima/Animus",
                "description": "The representation of the opposite gender qualities within",
                "category": "Soul",
                "traits": {
                    "balance": 0.8,
                    "attraction": 0.7,
                    "integration": 0.7,
                    "wholeness": 0.6,
                },
                "typical_roles": ["love interest", "soul mate", "complement"],
                "example_characters": "Princess Leia, Ginny Weasley, Arwen",
                "is_active": True,
            },
            {
                "name": "The Self",
                "description": "The representation of wholeness and integration of all aspects",
                "category": "Self",
                "traits": {
                    "wholeness": 0.9,
                    "integration": 0.8,
                    "enlightenment": 0.8,
                    "unity": 0.7,
                },
                "typical_roles": ["sage", "enlightened one", "unified being"],
                "example_characters": "The Buddha, Jesus Christ, King Arthur",
                "is_active": True,
            },
        ]

    async def _get_book_context_for_character(
        self, book_id: str, character_name: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get book context including chapters for character detail generation.
        Uses RAG with vector embeddings for semantic search when available,
        falls back to simple chapter retrieval otherwise.
        """
        try:
            # Convert book_id to UUID if it's a string
            book_uuid = uuid.UUID(book_id) if isinstance(book_id, str) else book_id

            logger.info(f"[CharacterService] Looking up book with ID: {book_uuid}")

            # Get book information - first try by book.id
            book_stmt = select(Book).where(Book.id == book_uuid)
            book_result = await self.session.exec(book_stmt)
            book = book_result.first()

            # If not found by book.id, try by project_id (Creator mode)
            if not book:
                logger.info(
                    f"[CharacterService] Book not found by ID, trying project_id: {book_uuid}"
                )
                book_stmt = select(Book).where(Book.project_id == book_uuid)
                book_result = await self.session.exec(book_stmt)
                book = book_result.first()

            if not book:
                logger.warning(
                    f"[CharacterService] Book not found with ID or project_id: {book_uuid}"
                )
                return None

            book_info = {
                "id": str(book.id),
                "title": book.title,
                "author": book.author_name or "",
                "genre": getattr(book, "genre", "") or "",
                "description": book.description or "",
                "book_type": book.book_type or "fiction",
            }

            # Try RAG-based semantic search first if character name provided
            if character_name:
                try:
                    rag_context = await self._get_rag_context_for_character(
                        book_id=book_id, character_name=character_name
                    )
                    if rag_context:
                        logger.info(
                            f"[CharacterService] Using RAG context for character: {character_name} "
                            f"(found {len(rag_context)} relevant chunks)"
                        )
                        return {
                            "book": book_info,
                            "chapters_summary": rag_context,
                            "total_chapters": -1,  # Indicates RAG mode
                            "context_source": "rag",
                        }
                except Exception as rag_error:
                    logger.warning(
                        f"[CharacterService] RAG search failed, falling back to simple method: {rag_error}"
                    )

            # Fallback: Get chapter summaries (limit to first 5 chapters for context)
            from app.books.models import Chapter

            chapters_stmt = (
                select(Chapter)
                .where(Chapter.book_id == book_uuid)
                .order_by(Chapter.chapter_number)
                .limit(5)
            )
            chapters_result = await self.session.exec(chapters_stmt)
            chapters = chapters_result.all()

            # Extract key content snippets
            context_parts = []
            for chapter in chapters:
                content_preview = chapter.content[:800] if chapter.content else ""
                context_parts.append(
                    f"Chapter {chapter.chapter_number}: {chapter.title}\n{content_preview}"
                )

            logger.info(
                f"[CharacterService] Using simple context for character (no embeddings or RAG failed)"
            )

            return {
                "book": book_info,
                "chapters_summary": "\n\n".join(context_parts),
                "total_chapters": len(chapters),
                "context_source": "simple",
            }

        except Exception as e:
            logger.error(f"[CharacterService] Error getting book context: {str(e)}")
            return None

    async def _get_rag_context_for_character(
        self, book_id: str, character_name: str
    ) -> Optional[str]:
        """
        Use vector embeddings to semantically search for content mentioning the character.
        Returns combined context from the most relevant text chunks.
        """
        try:
            # Create search query that focuses on finding character mentions
            search_query = (
                f"{character_name} character description personality appearance role"
            )

            # Use EmbeddingsService to search similar chapters
            similar_chunks = await self.embeddings_service.search_similar_chapters(
                query=search_query,
                book_id=uuid.UUID(book_id),
                limit=10,  # Get top 10 most relevant chunks
                threshold=0.5,  # Lower threshold to get more results
            )

            if not similar_chunks:
                logger.info(
                    f"[CharacterService] No embeddings found for book {book_id}, "
                    "will use fallback method"
                )
                return None

            # Build context from relevant chunks
            context_parts = []
            seen_chunks = set()  # Avoid duplicate content

            for chunk in similar_chunks:
                content = chunk.get("content_chunk", "")
                # Deduplicate by first 100 chars
                chunk_signature = content[:100] if content else ""
                if chunk_signature in seen_chunks:
                    continue
                seen_chunks.add(chunk_signature)

                chapter_info = chunk.get("chapter", {})
                chapter_title = chapter_info.get("title", "Unknown Chapter")
                chapter_number = chapter_info.get("chapter_number", "?")

                context_parts.append(
                    f"[From Chapter {chapter_number}: {chapter_title}]\n{content}"
                )

            if not context_parts:
                return None

            # Combine all relevant context
            combined_context = "\n\n---\n\n".join(context_parts)

            logger.info(
                f"[CharacterService] RAG found {len(context_parts)} relevant chunks "
                f"for character '{character_name}'"
            )

            return combined_context

        except Exception as e:
            logger.error(f"[CharacterService] RAG context error: {str(e)}")
            return None

    def _build_character_detail_prompt(
        self,
        character_name: str,
        book_context: Dict[str, Any],
        role: Optional[str] = None,
    ) -> str:
        """
        Build AI prompt for generating detailed character information.
        """
        book = book_context["book"]
        chapters_summary = book_context.get("chapters_summary", "")

        role_context = f"\nRole: {role}" if role else ""

        prompt_parts = [
            f'You are an expert character development analyst. Based on the book content below, generate detailed character information for "{character_name}".',
            "",
            "BOOK INFORMATION:",
            f"Title: {book['title']}",
            f"Author: {book.get('author', 'Unknown')}",
            f"Genre: {book.get('genre', 'Unknown')}",
            f"Description: {book.get('description', '')}",
            "",
            "CHAPTER CONTENT:",
            f"{chapters_summary}",
            "",
            "CHARACTER TO ANALYZE:",
            f"Name: {character_name}{role_context}",
            "",
            "TASK:",
            f'Analyze the book content and generate comprehensive character details for "{character_name}". If the character appears in the book, extract their details. If not mentioned, infer appropriate details that would fit the book\'s world and tone.',
            "",
            "Provide the following information:",
            "1. Physical Description: Appearance, age, distinctive features (2-3 sentences)",
            "2. Personality: Core personality traits, behavior patterns, temperament (2-3 sentences)",
            "3. Character Arc: How they grow or change throughout the story (1-2 sentences)",
            "4. Want: External goal or desire (1 sentence)",
            "5. Need: Internal emotional need (1 sentence)",
            "6. Lie They Believe: False belief holding them back (1 sentence)",
            "7. Ghost (Past Trauma): Past wound or trauma affecting them (1 sentence)",
            "",
            "RESPONSE FORMAT:",
            "Return ONLY a valid JSON object with these exact keys:",
            "{",
            '    "physical_description": "string",',
            '    "personality": "string",',
            '    "character_arc": "string",',
            '    "want": "string",',
            '    "need": "string",',
            '    "lie": "string",',
            '    "ghost": "string"',
            "}",
            "",
            "IMPORTANT: Keep descriptions concise but meaningful. Focus on details that make the character unique and interesting.",
        ]

        return "\n".join(prompt_parts)

    def _parse_character_details_response(
        self, ai_response: str, character_name: str, role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse AI response and extract character details with robust JSON extraction.
        """
        logger.info(
            f"[CharacterService] Parsing AI response (length: {len(ai_response)})"
        )
        logger.debug(f"[CharacterService] AI response content: {ai_response[:500]}")

        try:
            json_str = None

            # Try multiple extraction strategies
            # Strategy 1: Extract from markdown code blocks (```json ... ```)
            json_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```",
                ai_response,
                re.DOTALL | re.IGNORECASE,
            )
            if json_match:
                json_str = json_match.group(1)
                logger.info("[CharacterService] Found JSON in markdown code block")

            # Strategy 2: Extract JSON object with proper brace matching
            if not json_str:
                # Find first { and match all the way to its closing }
                start_idx = ai_response.find("{")
                if start_idx != -1:
                    brace_count = 0
                    for i in range(start_idx, len(ai_response)):
                        if ai_response[i] == "{":
                            brace_count += 1
                        elif ai_response[i] == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = ai_response[start_idx : i + 1]
                                logger.info(
                                    "[CharacterService] Extracted JSON with brace matching"
                                )
                                break

            # Strategy 3: Try entire response if no JSON delimiters found
            if not json_str:
                json_str = ai_response.strip()
                logger.info("[CharacterService] Using entire response as JSON")

            # Try to parse as JSON
            character_data = json.loads(json_str)

            # Validate all required fields are present
            result = {
                "name": character_name,
                "role": role or "supporting",
                "physical_description": character_data.get("physical_description", ""),
                "personality": character_data.get("personality", ""),
                "character_arc": character_data.get("character_arc", ""),
                "want": character_data.get("want", ""),
                "need": character_data.get("need", ""),
                "lie": character_data.get("lie", ""),
                "ghost": character_data.get("ghost", ""),
            }

            logger.info(
                f"[CharacterService] Successfully parsed JSON response with {sum(1 for v in result.values() if v)} non-empty fields"
            )
            return result

        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            logger.warning(
                f"[CharacterService] JSON parsing failed: {str(e)}, attempting text extraction"
            )

            # Fallback: extract information from text using pattern matching
            result = {
                "name": character_name,
                "role": role or "supporting",
                "physical_description": self._extract_field_from_ai_text(
                    ai_response, "physical_description"
                )
                or "",
                "personality": self._extract_field_from_ai_text(
                    ai_response, "personality"
                )
                or "",
                "character_arc": self._extract_field_from_ai_text(
                    ai_response, "character_arc"
                )
                or "",
                "want": self._extract_field_from_ai_text(ai_response, "want") or "",
                "need": self._extract_field_from_ai_text(ai_response, "need") or "",
                "lie": self._extract_field_from_ai_text(ai_response, "lie") or "",
                "ghost": self._extract_field_from_ai_text(ai_response, "ghost") or "",
            }

            extracted_count = sum(
                1
                for v in result.values()
                if v and v not in [character_name, role or "supporting"]
            )
            logger.info(
                f"[CharacterService] Text parsing extracted {extracted_count} character detail fields"
            )

            if extracted_count == 0:
                logger.error(
                    f"[CharacterService] Failed to extract any character details from response"
                )

            return result

    def _extract_field_from_ai_text(self, text: str, field_name: str) -> Optional[str]:
        """
        Extract a specific field value from AI text response.
        Handles both single-line and multi-line values.
        """
        import re

        # Try various patterns with multi-line support
        patterns = [
            # Pattern 1: Field with colon and value on same or next lines
            rf"{field_name}:\s*(.+?)(?:\n\n|\n[A-Z]|\n\d+\.|\Z)",
            rf"{field_name.replace('_', ' ')}:\s*(.+?)(?:\n\n|\n[A-Z]|\n\d+\.|\Z)",
            rf"{field_name.replace('_', ' ').title()}:\s*(.+?)(?:\n\n|\n[A-Z]|\n\d+\.|\Z)",
            # Pattern 2: Numbered list format
            rf"\d+\.\s+{field_name.replace('_', ' ').title()}:\s*(.+?)(?:\n\n|\n\d+\.|\Z)",
            # Pattern 3: Single line format
            rf"{field_name}:\s*([^\n]+)",
            rf"{field_name.replace('_', ' ')}:\s*([^\n]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.group(1).strip()
                # Clean up common artifacts
                value = re.sub(r'^["\']\s*', "", value)
                value = re.sub(r'\s*["\']$', "", value)
                # Remove trailing punctuation from section markers
                value = re.sub(r"\s*\n\s*$", "", value)
                # Collapse multiple spaces and newlines
                value = re.sub(r"\s+", " ", value)

                if value and len(value) > 5:  # Ensure we have meaningful content
                    return value

        return None

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
            "pro": ModelTier.PREMIUM,
            "enterprise": ModelTier.PROFESSIONAL,
        }

        # Handle both enum and string inputs
        tier_key = (
            subscription_tier.value
            if hasattr(subscription_tier, "value")
            else str(subscription_tier).lower()
        )

        return tier_mapping.get(tier_key, ModelTier.FREE)
