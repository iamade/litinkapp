from typing import Dict, Any, List, Optional
import uuid
import json
import logging
from datetime import datetime

from app.core.database import get_supabase
from app.services.openrouter_service import OpenRouterService, ModelTier
from app.services.subscription_manager import SubscriptionManager
from app.services.modelslab_v7_image_service import ModelsLabV7ImageService
from app.schemas.plot import (
    CharacterResponse,
    CharacterCreate,
    CharacterUpdate,
    CharacterArchetypeResponse,
    CharacterArchetypeMatch
)

logger = logging.getLogger(__name__)


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

    def __init__(self, supabase_client=None):
        self.db = supabase_client or get_supabase()
        self.openrouter = OpenRouterService()
        self.subscription_manager = SubscriptionManager(self.db)
        self.image_service = ModelsLabV7ImageService()

        # Default archetypes for initial setup
        self._default_archetypes = self._get_default_archetypes()

    async def generate_non_fiction_personas(
        self,
        content: str,
        genre: str = "educational",
        num_personas: int = 5,
        user_tier: str = "free"
    ) -> List[Dict[str, Any]]:
        """
        Generate fictional personas based on non-fiction content.
        Returns structured persona data with appropriate archetypes.
        """
        try:
            logger.info("[CharacterService] Starting fictional persona generation for non-fiction content")
            # Define fictional archetypes for non-fiction adaptation
            fictional_archetypes = [
                {
                    "name": "Protagonist",
                    "description": "The central character driving the story forward",
                    "category": "Fiction",
                    "traits": {"leadership": 0.9, "determination": 0.8, "charisma": 0.7},
                    "typical_roles": ["hero", "main character"],
                    "is_active": True
                },
                {
                    "name": "Mentor",
                    "description": "A wise figure offering guidance and support",
                    "category": "Fiction",
                    "traits": {"wisdom": 0.9, "guidance": 0.8, "experience": 0.7},
                    "typical_roles": ["teacher", "guide"],
                    "is_active": True
                },
                {
                    "name": "Antagonist",
                    "description": "The opposing force creating conflict in the story",
                    "category": "Fiction",
                    "traits": {"ambition": 0.9, "opposition": 0.8, "power": 0.7},
                    "typical_roles": ["villain", "rival"],
                    "is_active": True
                },
                {
                    "name": "Sidekick",
                    "description": "A loyal companion supporting the protagonist",
                    "category": "Fiction",
                    "traits": {"loyalty": 0.9, "support": 0.8, "friendship": 0.7},
                    "typical_roles": ["companion", "ally"],
                    "is_active": True
                },
                {
                    "name": "Comic Relief",
                    "description": "Provides humor and lightens the mood",
                    "category": "Fiction",
                    "traits": {"humor": 0.9, "wit": 0.8, "charm": 0.7},
                    "typical_roles": ["jester", "funny friend"],
                    "is_active": True
                }
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
                analysis_type="characters"
            )
            if response["status"] == "success":
                try:
                    personas = json.loads(response["result"])
                    # Attach archetype details to each persona
                    for persona in personas:
                        match = next((a for a in fictional_archetypes if a["name"].lower() == persona.get("persona_type", "").lower()), None)
                        persona["archetype"] = match if match else {}
                    return personas
                except Exception as e:
                    logger.warning(f"[CharacterService] AI response not valid JSON for fictional personas: {str(e)}")
                    return []
            else:
                logger.warning(f"[CharacterService] Fictional persona generation failed: {response.get('error')}")
                return []
        except Exception as e:
            logger.error(f"[CharacterService] Error generating fictional personas: {str(e)}")
            return []

    async def analyze_character_archetypes(
        self,
        character_description: str,
        personality: str
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
                archetypes
            )

            # Find the best match
            if analysis_result:
                best_match = max(analysis_result, key=lambda x: x.get("confidence", 0))
                return CharacterArchetypeMatch(
                    character_id="",  # Will be set by caller
                    archetype_id=best_match["archetype_id"],
                    match_score=best_match["confidence"],
                    matched_traits=best_match.get("matched_traits", []),
                    analysis=best_match.get("analysis", "")
                )
            else:
                # Return fallback match
                return CharacterArchetypeMatch(
                    character_id="",
                    archetype_id="",
                    match_score=0.0,
                    matched_traits=[],
                    analysis="No archetype match found"
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
        aspect_ratio: str = "3:4"
    ) -> Dict[str, Any]:
        """
        Generates character portrait using async Celery task.
        Returns task information for status tracking instead of blocking.
        """
        try:
            logger.info(f"[CharacterService] Queueing image generation for character {character_id}")

            # Check subscription limits for image generation
            usage_check = await self.subscription_manager.check_usage_limits(user_id, "image")
            if not usage_check["can_generate"]:
                raise CharacterServiceError(f"Image generation limit exceeded for {usage_check['tier']} tier")

            # Get user tier for model selection
            user_tier = usage_check["tier"]

            # Get character data
            character = await self.get_character_by_id(character_id, user_id)
            if not character:
                raise CharacterNotFoundError(f"Character {character_id} not found")

            # Build character description for image generation
            character_description = character.physical_description or character.personality or f"Character portrait of {character.name}"

            # Create initial record in image_generations table
            from datetime import datetime
            image_record_data = {
                'user_id': user_id,
                'image_type': 'character',
                'character_name': character.name,
                'character_id': character_id,
                'scene_description': character_description,
                'status': 'pending',
                'style': style,
                'aspect_ratio': aspect_ratio,
                'prompt': self._build_character_image_prompt(character, custom_prompt),
                'metadata': {
                    'character_id': character_id,
                    'image_type': 'character_portrait',
                    'created_via': 'character_service'
                }
            }

            record_result = self.db.table('image_generations').insert(image_record_data).execute()
            record_id = record_result.data[0]['id'] if record_result.data else None

            if not record_id:
                raise CharacterServiceError("Failed to create image generation record")

            # Update character status to pending
            self.db.table('characters').update({
                'image_generation_status': 'pending',
                'updated_at': datetime.now().isoformat()
            }).eq('id', character_id).execute()

            # Queue the async task
            from app.tasks.image_tasks import generate_character_image_task
            task = generate_character_image_task.delay(
                character_name=character.name,
                character_description=character_description,
                user_id=user_id,
                character_id=character_id,
                style=style,
                aspect_ratio=aspect_ratio,
                custom_prompt=custom_prompt,
                record_id=record_id,
                user_tier=user_tier
            )

            # Record usage immediately (image generation is queued)
            try:
                await self.subscription_manager.record_usage(
                    user_id=user_id,
                    resource_type="image",
                    cost_usd=0.0,
                    metadata={
                        "character_id": character_id,
                        "image_type": "character_portrait",
                        "task_id": task.id
                    }
                )
            except Exception as usage_error:
                logger.warning(f"[CharacterService] Failed to record usage: {str(usage_error)}")

            logger.info(f"[CharacterService] Queued image generation task {task.id} for character {character_id}")

            return {
                "character_id": character_id,
                "task_id": task.id,
                "record_id": record_id,
                "status": "queued",
                "message": "Character image generation has been queued",
                "estimated_time_seconds": 60
            }

        except CharacterNotFoundError:
            raise
        except CharacterServiceError:
            raise
        except Exception as e:
            logger.error(f"[CharacterService] Error queueing character image generation: {str(e)}")
            raise ImageGenerationError(f"Failed to queue image generation: {str(e)}")

    async def get_character_image_status(
        self,
        character_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get the current status of character image generation.
        """
        try:
            await self._validate_character_permissions(character_id, user_id)

            result = self.db.table('characters').select(
                'image_generation_status, image_generation_task_id, image_url, image_metadata'
            ).eq('id', character_id).single().execute()

            if not result.data:
                raise CharacterNotFoundError(f"Character {character_id} not found")

            data = result.data
            status = data.get('image_generation_status', 'none')
            task_id = data.get('image_generation_task_id')
            image_url = data.get('image_url')
            metadata = data.get('image_metadata', {})

            response = {
                "character_id": character_id,
                "status": status,
                "task_id": task_id,
                "image_url": image_url,
                "metadata": metadata
            }

            if status == 'failed' and metadata:
                response["error"] = metadata.get('error')

            return response

        except CharacterNotFoundError:
            raise
        except Exception as e:
            logger.error(f"[CharacterService] Error getting image status: {str(e)}")
            raise CharacterServiceError(f"Failed to get image status: {str(e)}")

    async def get_character_by_id(self, character_id: str, user_id: str) -> Optional[CharacterResponse]:
        """
        Retrieve a character by ID with permission validation.
        """
        try:
            # Validate permissions
            await self._validate_character_permissions(character_id, user_id)

            result = self.db.table('characters').select('*').eq('id', character_id).single().execute()

            if not result.data:
                return None

            character_data = result.data
            return CharacterResponse(**character_data)

        except Exception as e:
            logger.error(f"[CharacterService] Error retrieving character {character_id}: {str(e)}")
            return None

    async def update_character(
        self,
        character_id: str,
        user_id: str,
        updates: CharacterUpdate
    ) -> CharacterResponse:
        """
        Update character data with permission validation.
        """
        try:
            # Validate permissions
            await self._validate_character_permissions(character_id, user_id)

            # Prepare update data
            update_data = {}
            for field in ['name', 'role', 'character_arc', 'physical_description', 'personality',
                         'archetypes', 'want', 'need', 'lie', 'ghost', 'image_url',
                         'image_generation_prompt', 'image_metadata', 'generation_method', 'model_used']:
                if hasattr(updates, field) and getattr(updates, field) is not None:
                    update_data[field] = getattr(updates, field)

            if update_data:
                update_data['updated_at'] = datetime.now().isoformat()

                result = self.db.table('characters').update(update_data).eq('id', character_id).execute()

                if result.data:
                    return CharacterResponse(**result.data[0])
                else:
                    raise CharacterNotFoundError(f"Character {character_id} not found")

            # No updates provided, return current data
            return await self.get_character_by_id(character_id, user_id)

        except CharacterNotFoundError:
            raise
        except PermissionDeniedError:
            raise
        except Exception as e:
            logger.error(f"[CharacterService] Error updating character {character_id}: {str(e)}")
            raise CharacterServiceError(f"Failed to update character: {str(e)}")

    async def get_characters_by_plot(self, plot_overview_id: str, user_id: str) -> List[CharacterResponse]:
        """
        Get all characters for a specific plot overview.
        """
        try:
            # First verify user has access to the plot overview
            plot_result = self.db.table('plot_overviews').select('user_id').eq('id', plot_overview_id).single().execute()
            if not plot_result.data or plot_result.data['user_id'] != user_id:
                raise PermissionDeniedError("Access denied to plot overview")

            result = self.db.table('characters').select('*').eq('plot_overview_id', plot_overview_id).execute()

            characters = []
            for char_data in result.data or []:
                characters.append(CharacterResponse(**char_data))

            return characters

        except PermissionDeniedError:
            raise
        except Exception as e:
            logger.error(f"[CharacterService] Error retrieving characters for plot {plot_overview_id}: {str(e)}")
            return []

    async def link_characters_to_script(self, script_id: str, character_ids: List[str], user_id: str) -> bool:
        """
        Link characters to a script using the character_ids column in the scripts table.
        """
        try:
            # Validate all character IDs belong to the user
            for char_id in character_ids:
                char = await self.get_character_by_id(char_id, user_id)
                if not char:
                    raise CharacterNotFoundError(f"Character {char_id} not found or access denied")

            # Update the script record
            update_data = {
                "character_ids": character_ids,
                "updated_at": datetime.now().isoformat()
            }
            result = self.db.table('scripts').update(update_data).eq('id', script_id).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"[CharacterService] Error linking characters to script {script_id}: {str(e)}")
            return False

    async def update_character_image_url(self, character_id: str, image_url: str, user_id: str) -> bool:
        """
        Update the image URL for a character.
        """
        try:
            await self._validate_character_permissions(character_id, user_id)
            update_data = {
                "image_url": image_url,
                "updated_at": datetime.now().isoformat()
            }
            result = self.db.table('characters').update(update_data).eq('id', character_id).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"[CharacterService] Error updating image URL for character {character_id}: {str(e)}")
            return False

    async def get_all_characters_for_book(self, book_id: str, user_id: str) -> List[CharacterResponse]:
        """
        Retrieve all characters for a given book.
        """
        try:
            # Validate user has access to the book
            book_result = self.db.table('books').select('user_id').eq('id', book_id).single().execute()
            if not book_result.data or book_result.data['user_id'] != user_id:
                raise PermissionDeniedError("Access denied to book")
            result = self.db.table('characters').select('*').eq('book_id', book_id).execute()
            return [CharacterResponse(**char_data) for char_data in result.data or []]
        except Exception as e:
            logger.error(f"[CharacterService] Error retrieving all characters for book {book_id}: {str(e)}")
            return []

    async def set_character_voice_mapping(self, character_id: str, voice_id: str, user_id: str) -> bool:
        """
        Set the voice mapping for a character.
        """
        try:
            await self._validate_character_permissions(character_id, user_id)
            update_data = {
                "voice_id": voice_id,
                "updated_at": datetime.now().isoformat()
            }
            result = self.db.table('characters').update(update_data).eq('id', character_id).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"[CharacterService] Error setting voice mapping for character {character_id}: {str(e)}")
            return False

    async def get_character_voice_mapping(self, character_id: str, user_id: str) -> Optional[str]:
        """
        Get the voice mapping for a character.
        """
        try:
            await self._validate_character_permissions(character_id, user_id)
            result = self.db.table('characters').select('voice_id').eq('id', character_id).single().execute()
            if result.data:
                return result.data.get("voice_id")
            return None
        except Exception as e:
            logger.error(f"[CharacterService] Error retrieving voice mapping for character {character_id}: {str(e)}")
            return None

    async def delete_character(self, character_id: str, user_id: str) -> bool:
        """
        Delete a character with permission validation.
        """
        try:
            # Validate permissions
            await self._validate_character_permissions(character_id, user_id)

            result = self.db.table('characters').delete().eq('id', character_id).execute()

            return len(result.data) > 0

        except PermissionDeniedError:
            raise
        except Exception as e:
            logger.error(f"[CharacterService] Error deleting character {character_id}: {str(e)}")
            return False

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

    async def get_archetypes_by_category(self, category: str) -> List[CharacterArchetypeResponse]:
        """
        Get archetypes filtered by category.
        """
        try:
            all_archetypes = await self._get_all_archetypes()
            filtered = [arch for arch in all_archetypes if arch.get('category', '').lower() == category.lower()]
            return [CharacterArchetypeResponse(**arch) for arch in filtered]

        except Exception as e:
            logger.error(f"[CharacterService] Error retrieving archetypes by category {category}: {str(e)}")
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
                existing = self.db.table('character_archetypes').select('id').eq('name', archetype_data['name']).execute()

                if not existing.data:
                    archetype_data['id'] = str(uuid.uuid4())
                    archetype_data['created_at'] = datetime.now().isoformat()
                    archetype_data['updated_at'] = datetime.now().isoformat()

                    self.db.table('character_archetypes').insert(archetype_data).execute()
                    created_count += 1

            logger.info(f"[CharacterService] Created {created_count} default archetypes")
            return created_count

        except Exception as e:
            logger.error(f"[CharacterService] Error populating default archetypes: {str(e)}")
            raise CharacterServiceError(f"Failed to populate archetypes: {str(e)}")

    def _build_character_image_prompt(self, character: CharacterResponse, custom_prompt: Optional[str] = None) -> str:
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

    async def _analyze_archetype_match(self, character_data: Dict[str, Any], archetypes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
                analysis_type="archetype_analysis"
            )

            if response["status"] == "success":
                try:
                    matches = json.loads(response["result"])
                    return matches[:3]  # Return top 3 matches
                except json.JSONDecodeError:
                    logger.warning("[CharacterService] AI response not valid JSON for archetype analysis")
                    return []
            else:
                logger.warning(f"[CharacterService] Archetype analysis failed: {response.get('error')}")
                return []

        except Exception as e:
            logger.error(f"[CharacterService] Error in archetype matching: {str(e)}")
            return []

    async def _validate_character_permissions(self, character_id: str, user_id: str) -> bool:
        """
        Validate that user has permission to access/modify the character.
        """
        try:
            result = self.db.table('characters').select('user_id').eq('id', character_id).single().execute()

            if not result.data:
                raise CharacterNotFoundError(f"Character {character_id} not found")

            if result.data['user_id'] != user_id:
                raise PermissionDeniedError("Access denied to character")

            return True

        except CharacterNotFoundError:
            raise
        except PermissionDeniedError:
            raise
        except Exception as e:
            logger.error(f"[CharacterService] Error validating permissions for character {character_id}: {str(e)}")
            raise PermissionDeniedError("Permission validation failed")

    async def _update_character_image_metadata(self, character_id: str, image_data: Dict[str, Any]) -> None:
        """
        Update character record with image metadata.
        """
        try:
            # Extract and validate image_url
            image_url = image_data.get('image_url')
            if not image_url:
                logger.error(f"[CharacterService] No image_url provided in image_data: {image_data}")
                raise CharacterServiceError("image_url is required")

            update_data = {
                'image_url': image_url,
                'image_generation_prompt': image_data.get('image_generation_prompt'),
                'image_metadata': image_data.get('image_metadata', {}),
                'updated_at': datetime.now().isoformat()
            }

            logger.info(f"[CharacterService] Updating character {character_id}")
            logger.info(f"[CharacterService] Update data: {update_data}")

            result = self.db.table('characters').update(update_data).eq('id', character_id).execute()

            logger.info(f"[CharacterService] Update result: {result}")

            if not result.data:
                logger.error(f"[CharacterService] No character found to update with ID: {character_id}")
                raise CharacterServiceError(f"Character {character_id} not found for image update")

            logger.info(f"[CharacterService] Successfully updated character {character_id} with image_url: {image_url}")
            logger.info(f"[CharacterService] Updated character data: {result.data[0]}")

        except Exception as e:
            logger.error(f"[CharacterService] Error updating character image metadata: {str(e)}")
            logger.error(f"[CharacterService] Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"[CharacterService] Traceback: {traceback.format_exc()}")
            raise CharacterServiceError(f"Failed to update image metadata: {str(e)}")

    async def _get_all_archetypes(self) -> List[Dict[str, Any]]:
        """
        Get all archetypes from database, falling back to defaults if empty.
        """
        try:
            result = self.db.table('character_archetypes').select('*').eq('is_active', True).execute()

            if result.data and len(result.data) > 0:
                return result.data
            else:
                # Return default archetypes if database is empty
                return self._default_archetypes

        except Exception as e:
            logger.error(f"[CharacterService] Error retrieving archetypes from database: {str(e)}")
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
                "is_active": True
            },
            {
                "name": "Expert",
                "description": "Provides authoritative insights and analysis",
                "category": "NonFiction",
                "traits": {"authority": 0.9, "insight": 0.8, "analysis": 0.7},
                "typical_roles": ["expert", "analyst"],
                "is_active": True
            },
            {
                "name": "Interviewer",
                "description": "Asks questions and facilitates discussion",
                "category": "NonFiction",
                "traits": {"curiosity": 0.9, "facilitation": 0.8, "communication": 0.7},
                "typical_roles": ["interviewer", "host"],
                "is_active": True
            },
            {
                "name": "Subject Matter Expert",
                "description": "Specialized knowledge in specific topics",
                "category": "NonFiction",
                "traits": {"expertise": 0.9, "depth": 0.8, "specialization": 0.7},
                "typical_roles": ["specialist", "consultant"],
                "is_active": True
            },
            {
                "name": "Historical Figure",
                "description": "Represents real people from the content",
                "category": "NonFiction",
                "traits": {"authenticity": 0.9, "historical": 0.8, "representation": 0.7},
                "typical_roles": ["historical figure", "real person"],
                "is_active": True
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
                    "leadership": 0.6
                },
                "typical_roles": ["protagonist", "warrior", "explorer"],
                "example_characters": "Luke Skywalker, Harry Potter, Frodo Baggins",
                "is_active": True
            },
            {
                "name": "The Mentor",
                "description": "The wise guide who provides knowledge and support to the hero",
                "category": "Ego",
                "traits": {
                    "wisdom": 0.9,
                    "guidance": 0.8,
                    "experience": 0.8,
                    "support": 0.7
                },
                "typical_roles": ["teacher", "guide", "elder"],
                "example_characters": "Obi-Wan Kenobi, Dumbledore, Gandalf",
                "is_active": True
            },
            {
                "name": "The Shadow",
                "description": "The dark aspect representing repressed emotions and instincts",
                "category": "Shadow",
                "traits": {
                    "darkness": 0.9,
                    "opposition": 0.8,
                    "power": 0.7,
                    "threat": 0.7
                },
                "typical_roles": ["antagonist", "villain", "tempter"],
                "example_characters": "Darth Vader, Voldemort, Sauron",
                "is_active": True
            },
            {
                "name": "The Ally",
                "description": "The loyal companion who supports the hero's journey",
                "category": "Ego",
                "traits": {
                    "loyalty": 0.9,
                    "support": 0.8,
                    "friendship": 0.7,
                    "skill": 0.6
                },
                "typical_roles": ["sidekick", "friend", "companion"],
                "example_characters": "Samwise Gamgee, Ron Weasley, Han Solo",
                "is_active": True
            },
            {
                "name": "The Threshold Guardian",
                "description": "The gatekeeper who tests the hero and blocks the path",
                "category": "Ego",
                "traits": {
                    "testing": 0.8,
                    "blocking": 0.7,
                    "caution": 0.7,
                    "protection": 0.6
                },
                "typical_roles": ["guardian", "challenger", "obstacle"],
                "example_characters": "The Doorkeeper, Border Guards, Cerberus",
                "is_active": True
            },
            {
                "name": "The Shapeshifter",
                "description": "The mysterious figure who changes appearance and allegiance",
                "category": "Soul",
                "traits": {
                    "mystery": 0.9,
                    "change": 0.8,
                    "unpredictability": 0.7,
                    "complexity": 0.7
                },
                "typical_roles": ["trickster", "spy", "enigma"],
                "example_characters": "Loki, Severus Snape, Catwoman",
                "is_active": True
            },
            {
                "name": "The Trickster",
                "description": "The humorous disruptor who challenges the status quo",
                "category": "Soul",
                "traits": {
                    "humor": 0.8,
                    "disruption": 0.8,
                    "wisdom": 0.6,
                    "unconventional": 0.7
                },
                "typical_roles": ["jester", "fool", "disruptor"],
                "example_characters": "The Joker, Puck, Loki",
                "is_active": True
            },
            {
                "name": "The Anima/Animus",
                "description": "The representation of the opposite gender qualities within",
                "category": "Soul",
                "traits": {
                    "balance": 0.8,
                    "attraction": 0.7,
                    "integration": 0.7,
                    "wholeness": 0.6
                },
                "typical_roles": ["love interest", "soul mate", "complement"],
                "example_characters": "Princess Leia, Ginny Weasley, Arwen",
                "is_active": True
            },
            {
                "name": "The Self",
                "description": "The representation of wholeness and integration of all aspects",
                "category": "Self",
                "traits": {
                    "wholeness": 0.9,
                    "integration": 0.8,
                    "enlightenment": 0.8,
                    "unity": 0.7
                },
                "typical_roles": ["sage", "enlightened one", "unified being"],
                "example_characters": "The Buddha, Jesus Christ, King Arthur",
                "is_active": True
            }
        ]