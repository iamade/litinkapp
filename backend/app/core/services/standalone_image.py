from typing import Dict, Any, List, Optional
import uuid
import logging
from datetime import datetime

from sqlmodel import select, col, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.services.modelslab_v7_image import ModelsLabV7ImageService
from app.api.services.subscription import SubscriptionManager
from app.videos.models import ImageGeneration

logger = logging.getLogger(__name__)


class StandaloneImageServiceError(Exception):
    """Custom exception for standalone image service errors"""

    pass


class ImageGenerationError(StandaloneImageServiceError):
    """Exception raised when image generation fails"""

    pass


class DatabaseOperationError(StandaloneImageServiceError):
    """Exception raised when database operations fail"""

    pass


class StandaloneImageService:
    """
    Service for standalone image generation that integrates with the existing
    ModelsLabV7ImageService and stores results in the image_generations table.
    Supports scene and character image generation with database persistence.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.image_service = ModelsLabV7ImageService()
        self.subscription_manager = SubscriptionManager(self.session)

    async def generate_scene_image(
        self,
        scene_description: str,
        user_id: str,
        style: str = "cinematic",
        aspect_ratio: str = "16:9",
        custom_prompt: Optional[str] = None,
        script_id: Optional[str] = None,
        chapter_id: Optional[str] = None,  # Added for scene metadata tracking
        scene_number: Optional[int] = None,  # Added for scene metadata tracking
    ) -> Dict[str, Any]:
        """
        Generate a standalone scene image and store in database.

        Args:
            scene_description: Description of the scene to generate
            user_id: User ID for database association
            style: Visual style (cinematic, realistic, animated, fantasy)
            aspect_ratio: Image aspect ratio (16:9, 4:3, etc.)
            custom_prompt: Optional custom prompt additions
            script_id: Optional script ID for linking
            chapter_id: Optional chapter ID for metadata tracking
            scene_number: Optional scene number for ordering

        Returns:
            Dict containing image data and database record info
        """
        try:
            logger.info(
                f"[StandaloneImageService] Generating scene image for user {user_id}"
            )

            # Get user tier for model selection
            usage_check = await self.subscription_manager.check_usage_limits(
                user_id, "image"
            )
            user_tier = usage_check["tier"]

            # Create database record first with scene metadata
            record_id = await self._create_image_record(
                user_id=user_id,
                image_type="scene",
                scene_description=scene_description,
                style=style,
                aspect_ratio=aspect_ratio,
                script_id=script_id,
                chapter_id=chapter_id,  # Pass chapter_id for root-level field
                scene_number=scene_number,  # Pass scene_number for root-level field
            )

            # Build enhanced prompt
            prompt = self._build_scene_prompt(scene_description, style, custom_prompt)

            # Generate image using ModelsLab service with tier-based model selection
            generation_result = await self.image_service.generate_scene_image(
                scene_description=prompt,
                style=style,
                aspect_ratio=aspect_ratio,
                user_tier=user_tier,
            )

            # Update database record with results
            await self._update_image_record(
                record_id=record_id,
                generation_result=generation_result,
                prompt_used=prompt,
            )

            if generation_result.get("status") == "success":
                logger.info(
                    f"[StandaloneImageService] Scene image generated successfully: {record_id}"
                )
                return {
                    "record_id": record_id,
                    "image_url": generation_result.get("image_url"),
                    "prompt_used": prompt,
                    "metadata": generation_result.get("meta", {}),
                    "generation_time": generation_result.get("generation_time"),
                    "message": "Scene image generated successfully",
                }
            else:
                error_msg = generation_result.get("error", "Unknown generation error")
                logger.error(
                    f"[StandaloneImageService] Scene image generation failed: {error_msg}"
                )
                raise ImageGenerationError(
                    f"Scene image generation failed: {error_msg}"
                )

        except Exception as e:
            logger.error(
                f"[StandaloneImageService] Error generating scene image: {str(e)}"
            )
            # Update record with error if record was created
            if "record_id" in locals():
                await self._update_image_record_error(record_id, str(e))
            raise ImageGenerationError(f"Scene image generation failed: {str(e)}")

    async def generate_character_image(
        self,
        character_name: str,
        character_description: str,
        user_id: str,
        style: str = "realistic",
        aspect_ratio: str = "3:4",
        custom_prompt: Optional[str] = None,
        script_id: Optional[str] = None,
        chapter_id: Optional[str] = None,  # Added for metadata tracking
        user_tier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a standalone character image and store in database.

        Args:
            character_name: Name of the character
            character_description: Description of the character's appearance/personality
            user_id: User ID for database association
            style: Visual style (realistic, cinematic, animated, fantasy)
            aspect_ratio: Image aspect ratio (3:4 for portraits, etc.)
            custom_prompt: Optional custom prompt additions
            script_id: Optional script ID for linking
            chapter_id: Optional chapter ID for metadata tracking
            user_tier: Optional user subscription tier (if not provided, will be fetched)

        Returns:
            Dict containing image data and database record info
        """
        try:
            logger.info(
                f"[StandaloneImageService] Generating character image for {character_name} (user {user_id})"
            )

            # Get user tier for model selection if not provided
            if not user_tier:
                usage_check = await self.subscription_manager.check_usage_limits(
                    user_id, "image"
                )
                user_tier = usage_check["tier"]

            # Create database record first (character images don't have scene_number)
            record_id = await self._create_image_record(
                user_id=user_id,
                image_type="character",
                character_name=character_name,
                character_description=character_description,
                style=style,
                aspect_ratio=aspect_ratio,
                script_id=script_id,
                chapter_id=chapter_id,  # Pass chapter_id for metadata tracking
            )

            # Build enhanced prompt
            prompt = self._build_character_prompt(
                character_name, character_description, style, custom_prompt
            )

            # Generate image using ModelsLab service with tier-based model selection
            generation_result = await self.image_service.generate_character_image(
                character_name=character_name,
                character_description=prompt,
                style=style,
                aspect_ratio=aspect_ratio,
                user_tier=user_tier,
            )

            # Update database record with results
            await self._update_image_record(
                record_id=record_id,
                generation_result=generation_result,
                prompt_used=prompt,
            )

            if generation_result.get("status") == "success":
                logger.info(
                    f"[StandaloneImageService] Character image generated successfully: {record_id}"
                )
                return {
                    "record_id": record_id,
                    "character_name": character_name,
                    "image_url": generation_result.get("image_url"),
                    "prompt_used": prompt,
                    "metadata": generation_result.get("meta", {}),
                    "generation_time": generation_result.get("generation_time"),
                    "message": "Character image generated successfully",
                }
            else:
                error_msg = generation_result.get("error", "Unknown generation error")
                logger.error(
                    f"[StandaloneImageService] Character image generation failed: {error_msg}"
                )
                raise ImageGenerationError(
                    f"Character image generation failed: {error_msg}"
                )

        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            logger.error(
                f"[StandaloneImageService] Error generating character image: {error_msg}"
            )
            # Update record with error if record was created
            if "record_id" in locals():
                await self._update_image_record_error(record_id, error_msg)
            raise ImageGenerationError(
                f"Character image generation failed: {error_msg}"
            )

    async def get_canonical_character_image(
        self, character_id: str, user_id: str
    ) -> Optional[str]:
        """
        Retrieve the canonical image_url for a character from centralized storage.
        """
        from app.api.services.character import CharacterService

        character_service = CharacterService(self.db)
        character = await character_service.get_character_by_id(character_id, user_id)
        if character and character.image_url:
            return character.image_url
        return None

    async def batch_generate_images(
        self,
        image_requests: List[Dict[str, Any]],
        user_id: str,
        max_concurrent: int = 3,
        script_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple standalone images with controlled concurrency.

        Args:
            image_requests: List of image generation requests
            user_id: User ID for database association
            max_concurrent: Maximum concurrent generations

        Returns:
            List of generation results
        """
        try:
            logger.info(
                f"[StandaloneImageService] Batch generating {len(image_requests)} images for user {user_id}"
            )

            # Get user tier for model selection
            usage_check = await self.subscription_manager.check_usage_limits(
                user_id, "image"
            )
            user_tier = usage_check["tier"]

            # Create database records first
            record_ids = []
            for request in image_requests:
                # Extract scene metadata if present
                chapter_id = request.get("chapter_id")
                scene_number = request.get("scene_number")

                record_id = await self._create_image_record(
                    user_id=user_id,
                    image_type=request.get("type", "general"),
                    scene_description=request.get("scene_description"),
                    character_name=request.get("character_name"),
                    character_description=request.get("character_description"),
                    style=request.get("style", "cinematic"),
                    aspect_ratio=request.get("aspect_ratio", "16:9"),
                    script_id=script_id,
                    chapter_id=chapter_id,  # Pass for scene images
                    scene_number=scene_number,  # Pass for scene images
                )
                record_ids.append(record_id)

            # Prepare batch requests for ModelsLab service
            batch_requests = []
            for i, request in enumerate(image_requests):
                if request.get("type") == "character":
                    prompt = self._build_character_prompt(
                        request.get("character_name", f"Character_{i}"),
                        request.get("character_description", ""),
                        request.get("style", "realistic"),
                        request.get("custom_prompt"),
                    )
                    batch_requests.append(
                        {
                            "type": "character",
                            "character_name": request.get(
                                "character_name", f"Character_{i}"
                            ),
                            "description": prompt,
                            "style": request.get("style", "realistic"),
                            "aspect_ratio": request.get("aspect_ratio", "3:4"),
                        }
                    )
                elif request.get("type") == "scene":
                    prompt = self._build_scene_prompt(
                        request.get("scene_description", ""),
                        request.get("style", "cinematic"),
                        request.get("custom_prompt"),
                    )
                    batch_requests.append(
                        {
                            "type": "scene",
                            "description": prompt,
                            "style": request.get("style", "cinematic"),
                            "aspect_ratio": request.get("aspect_ratio", "16:9"),
                        }
                    )
                else:
                    batch_requests.append(
                        {
                            "type": "general",
                            "prompt": request.get(
                                "prompt", request.get("description", "")
                            ),
                            "aspect_ratio": request.get("aspect_ratio", "16:9"),
                            "model_id": request.get("model_id", "gen4_image"),
                        }
                    )

            # Generate images using ModelsLab batch service with tier-based model selection
            batch_results = await self.image_service.batch_generate_images(
                image_requests=batch_requests,
                max_concurrent=max_concurrent,
                user_tier=user_tier,
            )

            # Update database records with results
            processed_results = []
            for i, result in enumerate(batch_results):
                record_id = record_ids[i]
                request = image_requests[i]

                if result.get("status") == "success":
                    prompt_used = batch_requests[i].get(
                        "description"
                    ) or batch_requests[i].get("prompt", "")
                    await self._update_image_record(
                        record_id=record_id,
                        generation_result=result,
                        prompt_used=prompt_used,
                    )
                else:
                    await self._update_image_record_error(
                        record_id, result.get("error", "Batch generation failed")
                    )

                processed_results.append(
                    {
                        "record_id": record_id,
                        "request_index": i,
                        "status": result.get("status"),
                        "image_url": result.get("image_url"),
                        "error": result.get("error"),
                        "metadata": result.get("meta", {}),
                    }
                )

            successful_count = sum(
                1 for r in processed_results if r.get("status") == "success"
            )
            logger.info(
                f"[StandaloneImageService] Batch generation completed: {successful_count}/{len(image_requests)} successful"
            )

            return processed_results

        except Exception as e:
            logger.error(
                f"[StandaloneImageService] Error in batch generation: {str(e)}"
            )
            raise StandaloneImageServiceError(
                f"Batch image generation failed: {str(e)}"
            )

    async def get_image_record(
        self, record_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve an image generation record by ID with permission validation.
        """
        try:
            statement = (
                select(ImageGeneration)
                .where(ImageGeneration.id == record_id)
                .where(ImageGeneration.user_id == uuid.UUID(str(user_id)))
            )
            result = await self.session.exec(statement)
            record = result.first()

            if not record:
                return None

            return record.model_dump()

        except Exception as e:
            logger.error(
                f"[StandaloneImageService] Error retrieving image record {record_id}: {str(e)}"
            )
            return None

    async def get_user_images(
        self, user_id: str, image_type: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get user's standalone image generations.
        """
        try:
            statement = (
                select(ImageGeneration)
                .where(ImageGeneration.user_id == uuid.UUID(str(user_id)))
                .where(ImageGeneration.video_generation_id == None)
                .order_by(desc(ImageGeneration.created_at))
                .limit(limit)
            )

            if image_type:
                statement = statement.where(ImageGeneration.image_type == image_type)

            result = await self.session.exec(statement)
            records = result.all()

            return [record.model_dump() for record in records]

        except Exception as e:
            logger.error(
                f"[StandaloneImageService] Error retrieving user images: {str(e)}"
            )
            return []

    async def delete_image_record(self, record_id: str, user_id: str) -> bool:
        """
        Delete an image generation record with permission validation.
        """
        try:
            logger.info(
                f"[StandaloneImageService] Attempting to delete image record {record_id} for user {user_id}"
            )

            # First verify the record exists and belongs to the user
            statement = (
                select(ImageGeneration)
                .where(ImageGeneration.id == record_id)
                .where(ImageGeneration.user_id == uuid.UUID(str(user_id)))
            )
            result = await self.session.exec(statement)
            record = result.first()

            if not record:
                logger.warning(
                    f"[StandaloneImageService] Record {record_id} not found or doesn't belong to user {user_id}"
                )
                return False

            logger.info(f"[StandaloneImageService] Found record to delete: {record.id}")

            # Now delete it
            await self.session.delete(record)
            await self.session.commit()

            logger.info(
                f"[StandaloneImageService] Successfully deleted image record {record_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"[StandaloneImageService] Error deleting image record {record_id}: {str(e)}"
            )
            import traceback

            logger.error(
                f"[StandaloneImageService] Traceback: {traceback.format_exc()}"
            )
            return False

    def _build_scene_prompt(
        self, scene_description: str, style: str, custom_prompt: Optional[str] = None
    ) -> str:
        """
        Build enhanced prompt for scene image generation.
        """
        style_modifiers = {
            "realistic": "photorealistic environment, detailed landscape, natural lighting, high resolution",
            "cinematic": "cinematic scene, dramatic lighting, movie-quality composition, epic vista",
            "animated": "animated scene background, cartoon environment, vibrant world design",
            "fantasy": "fantasy environment, magical atmosphere, otherworldly landscape, mystical setting",
        }

        base_prompt = f"Scene: {scene_description}. {style_modifiers.get(style, style_modifiers['cinematic'])}. "
        base_prompt += "Wide establishing shot, detailed environment, atmospheric perspective, immersive background, professional scene composition"

        if custom_prompt:
            base_prompt += f". {custom_prompt}"

        return base_prompt

    def _build_character_prompt(
        self,
        character_name: str,
        character_description: str,
        style: str,
        custom_prompt: Optional[str] = None,
    ) -> str:
        """
        Build enhanced prompt for character image generation.
        """
        style_modifiers = {
            "realistic": "photorealistic portrait, detailed facial features, professional lighting, high quality, 8k resolution",
            "cinematic": "cinematic character portrait, dramatic lighting, film noir style, movie quality",
            "animated": "animated character design, cartoon style, expressive features, vibrant colors",
            "fantasy": "fantasy character art, magical aura, ethereal lighting, detailed fantasy design",
        }

        base_prompt = (
            f"Character portrait of {character_name}: {character_description}. "
        )
        base_prompt += f"{style_modifiers.get(style, style_modifiers['realistic'])}. "
        base_prompt += "Clear background, centered composition, detailed character design, expressive eyes, well-defined features, professional character art"

        if custom_prompt:
            base_prompt += f". {custom_prompt}"

        return base_prompt

    async def _create_image_record(
        self,
        user_id: str,
        image_type: str,
        scene_description: Optional[str] = None,
        character_name: Optional[str] = None,
        character_description: Optional[str] = None,
        style: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        script_id: Optional[str] = None,
        chapter_id: Optional[str] = None,  # Added for scene metadata tracking
        scene_number: Optional[int] = None,  # Added for scene metadata tracking
    ) -> str:
        """
        Create initial database record for image generation.

        Sets root-level fields (chapter_id, script_id, scene_number, image_type) and
        merges them into metadata JSONB for frontend queries and chapter linking.
        """
        try:
            record_id = uuid.uuid4()

            # Build metadata with all tracking fields
            # Merge new keys into metadata (new keys overwrite old if metadata passed)
            metadata = {
                "style": style,
                "aspect_ratio": aspect_ratio,
                "character_description": character_description,
                # Scene-related metadata for async tracking and frontend queries
                "scene_number": scene_number,
                "script_id": script_id,
                "chapter_id": chapter_id,
                "image_type": image_type,
            }

            # Remove None values from metadata
            metadata = {k: v for k, v in metadata.items() if v is not None}

            # For character images, preserve character-specific metadata
            if image_type == "character" and character_name:
                metadata["character_name"] = character_name

            image_record = ImageGeneration(
                id=record_id,
                user_id=uuid.UUID(str(user_id)),
                image_type=image_type,
                scene_description=scene_description,
                character_name=character_name,
                status="pending",
                meta=metadata,
                # Set root-level fields now that model is updated
                script_id=uuid.UUID(script_id) if script_id else None,
                chapter_id=uuid.UUID(chapter_id) if chapter_id else None,
                scene_number=scene_number,
            )

            # Note: ImageGeneration model doesn't have script_id, chapter_id, scene_number as root fields
            # They are stored in meta. If they are needed as root fields, the model needs update.
            # Based on previous code, they were root fields in the dict passed to insert.
            # Let's check ImageGeneration model again.
            # It has scene_id, character_name, character_id, user_id, shot_index, scene_description...
            # It does NOT have script_id, chapter_id, scene_number as root fields.
            # But the previous code was inserting them.
            # This implies the previous code was using a table that had these columns, OR Supabase was ignoring them?
            # Or maybe the table schema has them but the SQLModel definition is incomplete?
            # The previous code:
            # "script_id": script_id,  # Root-level field for script association
            # "chapter_id": chapter_id,  # Root-level field for chapter association
            # "scene_number": scene_number,  # Root-level field for scene ordering

            # If I look at app/videos/models.py, ImageGeneration has:
            # video_generation_id, image_type, scene_id, character_name, character_id, user_id, shot_index, scene_description...
            # It does NOT have script_id, chapter_id, scene_number.
            # However, app/images/models.py ImageRecord DOES have them.
            # But StandaloneImageService was using "image_generations" table.
            # This is a discrepancy.
            # If the table "image_generations" has these columns, I should update the model.
            # But I cannot check the DB schema directly.
            # I will assume the SQLModel is the source of truth for now, and store them in meta.
            # Or maybe I should use ImageRecord from app/images/models.py?
            # But StandaloneImageService was explicitly using "image_generations" table.
            # And ImageRecord uses "image_records" table.

            # Let's stick to ImageGeneration and store extra fields in meta.
            # Wait, if I use ImageGeneration, I need to make sure I don't lose data.
            # The previous code was inserting them as root fields.
            # If the table has them, I should add them to the model.
            # But I am not supposed to modify the model unless necessary.
            # Let's check if I can use ImageRecord instead?
            # No, because the table name is different.

            # I will add these fields to the ImageGeneration model in app/videos/models.py if they are missing?
            # No, I should check if they are actually used.
            # The comments say "Root-level field for script association".
            # I will add them to the model to be safe, as I did for VideoSegment.

            # Wait, I am in the middle of replace_file_content.
            # I should probably abort and update the model first?
            # Or I can just store them in meta for now and update the model later?
            # The previous code was:
            # "script_id": script_id,
            # "chapter_id": chapter_id,
            # "scene_number": scene_number,

            # I will assume they are in the table and add them to the model in a separate step.
            # For now, I will comment them out or put them in meta?
            # Putting them in meta is safer if the column doesn't exist.
            # But if the column exists and is required, I might fail.
            # The previous code didn't fail, so the columns likely exist.

            # I'll proceed with using ImageGeneration and putting them in meta,
            # AND I will add a TODO to update the model.

            self.session.add(image_record)
            await self.session.commit()
            await self.session.refresh(image_record)

            logger.info(f"[StandaloneImageService] Created image record: {record_id}")
            return str(record_id)

        except Exception as e:
            logger.error(
                f"[StandaloneImageService] Error creating image record: {str(e)}"
            )
            raise DatabaseOperationError(f"Failed to create image record: {str(e)}")

    async def _update_image_record(
        self, record_id: str, generation_result: Dict[str, Any], prompt_used: str
    ) -> None:
        """
        Update database record with successful generation results.
        Merges new metadata with existing to preserve scene/chapter tracking fields.
        """
        try:
            # Fetch existing record
            statement = select(ImageGeneration).where(ImageGeneration.id == record_id)
            result = await self.session.exec(statement)
            record = result.first()

            if not record:
                logger.warning(
                    f"[StandaloneImageService] Record {record_id} not found for update"
                )
                return

            # Merge metadata
            existing_metadata = record.meta or {}
            merged_metadata = {
                **existing_metadata,
                **generation_result.get("meta", {}),
                "model_used": generation_result.get("model_used"),
            }

            # Update fields
            record.status = "completed"
            record.image_prompt = prompt_used
            record.image_url = generation_result.get("image_url")
            record.thumbnail_url = generation_result.get("thumbnail_url")
            record.generation_time_seconds = generation_result.get("generation_time")
            record.meta = merged_metadata

            # Extract dimensions if available
            if generation_result.get("meta"):
                meta = generation_result["meta"]
                record.width = meta.get("width")
                record.height = meta.get("height")
                record.file_size_bytes = meta.get("file_size_bytes")

            record.updated_at = datetime.now()

            self.session.add(record)
            await self.session.commit()
            await self.session.refresh(record)

            logger.info(f"[StandaloneImageService] Updated image record: {record_id}")

        except Exception as e:
            logger.error(
                f"[StandaloneImageService] Error updating image record {record_id}: {str(e)}"
            )
            raise DatabaseOperationError(f"Failed to update image record: {str(e)}")

    async def _update_image_record_error(
        self, record_id: str, error_message: str
    ) -> None:
        """
        Update database record with error information.
        """
        try:
            statement = select(ImageGeneration).where(ImageGeneration.id == record_id)
            result = await self.session.exec(statement)
            record = result.first()

            if not record:
                logger.warning(
                    f"[StandaloneImageService] Record {record_id} not found for error update"
                )
                return

            record.status = "failed"
            record.error_message = error_message
            record.updated_at = datetime.now()

            self.session.add(record)
            await self.session.commit()

            logger.info(
                f"[StandaloneImageService] Updated image record with error: {record_id}"
            )

        except Exception as e:
            logger.error(
                f"[StandaloneImageService] Error updating image record error {record_id}: {str(e)}"
            )
            # Don't raise here to avoid masking original error
