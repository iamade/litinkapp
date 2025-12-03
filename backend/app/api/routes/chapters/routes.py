from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, col, or_
from supabase import Client

from app.core.auth import get_current_active_user
from app.core.database import get_session
from app.core.services.standalone_image import StandaloneImageService
from app.core.services.elevenlabs import ElevenLabsService
from app.core.services.modelslab_v7_audio import ModelsLabV7AudioService
from app.tasks.image_tasks import (
    generate_character_image_task,
    generate_scene_image_task,
)
from app.images.schemas import (
    SceneImageRequest,
    CharacterImageRequest,
    BatchImageRequest,
    ImageGenerationResponse,
    ImageGenerationQueuedResponse,
    BatchImageResponse,
    ChapterImagesResponse,
    BatchStatusResponse,
    DeleteImageResponse,
    ImageRecord,
    ImageStatusResponse,
)
from app.audio.schemas import (
    AudioGenerationRequest,
    AudioGenerationResponse,
    AudioGenerationQueuedResponse,
    AudioRecord,
    ChapterAudioResponse,
    AudioExportRequest,
    AudioExportResponse,
    DeleteAudioResponse,
    AudioStatusResponse,
)
from app.books.models import Book, Chapter
from app.videos.models import ImageGeneration
from app.api.services.subscription import SubscriptionManager

router = APIRouter()


async def verify_chapter_access(
    chapter_id: str, user_id: str, session: AsyncSession
) -> Dict[str, Any]:
    """Verify user has access to the chapter and return chapter data"""
    try:
        # Get chapter with book info
        stmt = select(Chapter, Book).join(Book).where(Chapter.id == chapter_id)
        result = await session.exec(stmt)
        chapter_book = result.first()

        if not chapter_book:
            raise HTTPException(status_code=404, detail="Chapter not found")

        chapter, book = chapter_book

        # Check access permissions (published books or owned by user)
        if book.status != "READY" and str(book.user_id) != user_id:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this chapter"
            )

        # Convert to dict for compatibility with existing code
        chapter_data = chapter.model_dump()
        # Add book data if needed, or just return chapter_data
        # The original code returned chapter_data with nested books
        # We can simulate that or update callers.
        # Callers use: chapter_data.get("ai_generated_content")
        # So model_dump is fine.
        return chapter_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error verifying chapter access: {str(e)}"
        )


def get_scene_description_from_chapter(
    chapter_data: Dict[str, Any], scene_number: int
) -> str:
    """Extract scene description from chapter AI content"""
    ai_content = chapter_data.get("ai_generated_content", {}) or {}

    # Look for scene descriptions in AI content
    for key, content in ai_content.items():
        if isinstance(content, dict) and "scene_descriptions" in content:
            scenes = content["scene_descriptions"]
            if isinstance(scenes, list) and len(scenes) > scene_number - 1:
                return scenes[scene_number - 1]

    # Fallback: generate a basic scene description
    chapter_title = chapter_data.get("title", "Unknown Chapter")
    return f"Scene from chapter: {chapter_title}. A visual representation of the events and setting described in this part of the story."


def get_character_info_from_chapter(
    chapter_data: Dict[str, Any], character_name: str
) -> Optional[Dict[str, str]]:
    """Extract character information from chapter AI content"""
    ai_content = chapter_data.get("ai_generated_content", {}) or {}

    # Look for characters in AI content
    for key, content in ai_content.items():
        if (
            isinstance(content, dict)
            and "characters" in content
            and "character_details" in content
        ):
            characters = content["characters"]
            character_details = content["character_details"]

            if isinstance(characters, list) and character_name in characters:
                # Find detailed character info
                for detail in character_details:
                    if (
                        isinstance(detail, dict)
                        and detail.get("name") == character_name
                    ):
                        return {
                            "name": character_name,
                            "description": detail.get(
                                "description",
                                f"Character {character_name} from the story",
                            ),
                        }

                # Fallback with basic info
                return {
                    "name": character_name,
                    "description": f"Character {character_name} appearing in the chapter",
                }

    return None


@router.get("/{chapter_id}/images", response_model=ChapterImagesResponse)
async def list_chapter_images(
    chapter_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """List all images associated with a chapter"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user["id"], session)

        # Get user's standalone images
        image_service = StandaloneImageService(session)
        user_images = await image_service.get_user_images(current_user["id"])

        # Filter images associated with this chapter (check both metadata and root-level chapter_id)
        chapter_images = []
        for img in user_images:
            metadata = img.get("metadata", {}) or {}
            # Check root-level chapter_id (if added to model) or metadata
            root_chapter_id = img.get("chapter_id")

            # Convert UUID to str for comparison if needed
            if root_chapter_id:
                root_chapter_id = str(root_chapter_id)

            # Check both metadata.chapter_id and root-level chapter_id field
            if (
                metadata.get("chapter_id") == chapter_id
                or root_chapter_id == chapter_id
            ):
                chapter_images.append(ImageRecord(**img))

        return ChapterImagesResponse(
            chapter_id=chapter_id,
            images=chapter_images,
            total_count=len(chapter_images),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing chapter images: {str(e)}"
        )


@router.post(
    "/{chapter_id}/images/scenes/{scene_number}",
    response_model=ImageGenerationQueuedResponse,
)
async def generate_scene_image(
    chapter_id: str,
    scene_number: int,
    request: SceneImageRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Generate an image for a specific scene in the chapter (asynchronous)"""
    try:
        # Verify chapter access
        chapter_data = await verify_chapter_access(
            chapter_id, current_user["id"], session
        )

        # Get scene description
        scene_description = get_scene_description_from_chapter(
            chapter_data, scene_number
        )
        if not scene_description:
            raise HTTPException(
                status_code=400, detail=f"Scene {scene_number} not found in chapter"
            )

        # Override with custom description if provided
        if request.scene_description:
            scene_description = request.scene_description

        # Get user tier for model selection
        subscription_manager = SubscriptionManager(session)
        usage_check = await subscription_manager.check_usage_limits(
            uuid.UUID(current_user["id"]), "image"
        )
        user_tier = usage_check["tier"]

        # Create pending record in database
        # We use ImageGeneration model directly via session
        metadata = {
            "chapter_id": chapter_id,
            "scene_number": scene_number,
            "script_id": request.script_id,
            "image_type": "scene",
            "style": request.style,
            "aspect_ratio": request.aspect_ratio,
        }

        record = ImageGeneration(
            user_id=uuid.UUID(current_user["id"]),
            image_type="scene",
            scene_description=scene_description,
            scene_number=scene_number,
            chapter_id=uuid.UUID(chapter_id),
            script_id=uuid.UUID(request.script_id) if request.script_id else None,
            status="pending",
            progress=0,
            meta=metadata,
        )

        try:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            record_id = str(record.id)

        except Exception as db_error:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create image generation record: {str(db_error)}",
            )

        # Queue the scene image generation task
        try:
            print(
                f"[DEBUG] [generate_scene_image] About to queue task for record_id={record_id}, scene={scene_number}"
            )
            task = generate_scene_image_task.delay(
                record_id=record_id,
                scene_description=scene_description,
                scene_number=scene_number,
                user_id=current_user["id"],
                chapter_id=chapter_id,
                script_id=request.script_id,
                style=request.style,
                aspect_ratio=request.aspect_ratio,
                custom_prompt=request.custom_prompt,
                user_tier=user_tier,
                retry_count=0,
            )

            print(
                f"[DEBUG] [generate_scene_image] Task queued successfully with task_id={task.id}"
            )
            return ImageGenerationQueuedResponse(
                task_id=task.id,
                status="queued",
                message="Scene image generation has been queued and will be processed in the background",
                estimated_time_seconds=60,
                record_id=record_id,
                scene_number=scene_number,
                retry_count=0,
            )

        except Exception as task_error:
            # If task queueing fails, mark the DB record as failed
            print(
                f"[ERROR] [generate_scene_image] Failed to queue task: {str(task_error)}"
            )

            try:
                record.status = "failed"
                record.error_message = f"Failed to queue task: {str(task_error)}"
                session.add(record)
                await session.commit()
            except Exception as update_error:
                print(
                    f"[ERROR] [generate_scene_image] Failed to update DB record: {str(update_error)}"
                )
                pass

            raise HTTPException(
                status_code=500,
                detail=f"Failed to queue scene image generation: {str(task_error)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error queuing scene image generation: {str(e)}"
        )


@router.post(
    "/{chapter_id}/images/characters", response_model=ImageGenerationQueuedResponse
)
async def generate_character_image(
    chapter_id: str,
    request: CharacterImageRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Generate an image for a character in the chapter (asynchronous)"""
    try:
        # Verify chapter access
        chapter_data = await verify_chapter_access(
            chapter_id, current_user["id"], session
        )

        # Get character info from chapter
        character_info = get_character_info_from_chapter(
            chapter_data, request.character_name
        )
        if not character_info:
            # Allow generation even if character not found in AI content
            character_info = {
                "name": request.character_name,
                "description": request.character_description
                or f"Character {request.character_name}",
            }

        # Override with provided description if given
        if request.character_description:
            character_info["description"] = request.character_description

        # Create initial record in database
        metadata = {
            "chapter_id": chapter_id,
            "character_name": character_info["name"],
            "image_type": "character",
        }

        record = ImageGeneration(
            user_id=uuid.UUID(current_user["id"]),
            image_type="character",
            character_name=character_info["name"],
            scene_description=character_info["description"],
            script_id=uuid.UUID(request.script_id) if request.script_id else None,
            chapter_id=uuid.UUID(chapter_id),
            status="pending",
            meta=metadata,
        )

        session.add(record)
        await session.commit()
        await session.refresh(record)
        record_id = str(record.id)

        # Queue the character image generation task
        task = generate_character_image_task.delay(
            character_name=character_info["name"],
            character_description=character_info["description"],
            user_id=current_user["id"],
            chapter_id=chapter_id,
            style=request.style,
            aspect_ratio=request.aspect_ratio,
            custom_prompt=request.custom_prompt,
            record_id=record_id,  # Pass the record_id to the task
        )

        return ImageGenerationQueuedResponse(
            task_id=task.id,
            status="queued",
            message="Character image generation has been queued and will be processed in the background",
            estimated_time_seconds=60,  # Estimated time for character image generation
            record_id=record_id,  # Include record_id for polling
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error queuing character image generation: {str(e)}",
        )


@router.post("/{chapter_id}/images/characters/link")
async def link_character_image(
    chapter_id: str,
    request: Dict[str, Any],
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Link an existing character image (e.g., from plot overview) to a script"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user["id"], session)

        character_name = request.get("character_name")
        image_url = request.get("image_url")
        script_id = request.get("script_id")
        prompt = request.get("prompt", "")

        if not character_name or not image_url:
            raise HTTPException(
                status_code=400, detail="character_name and image_url are required"
            )

        # Create record in database
        metadata = {
            "chapter_id": chapter_id,
            "character_name": character_name,
            "image_type": "character",
            "image_prompt": prompt,
            "linked_from_plot": True,
        }

        record = ImageGeneration(
            user_id=uuid.UUID(current_user["id"]),
            image_type="character",
            character_name=character_name,
            image_url=image_url,
            image_prompt=prompt,
            script_id=uuid.UUID(script_id) if script_id else None,
            chapter_id=uuid.UUID(chapter_id),
            status="completed",
            meta=metadata,
        )

        session.add(record)
        await session.commit()
        await session.refresh(record)

        return {
            "success": True,
            "record_id": str(record.id),
            "message": "Character image linked successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error linking character image: {str(e)}"
        )


@router.delete(
    "/{chapter_id}/images/scenes/{scene_number}", response_model=DeleteImageResponse
)
async def delete_scene_image(
    chapter_id: str,
    scene_number: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete a scene image for the chapter"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user["id"], session)

        # Find the image record
        image_service = StandaloneImageService(session)
        user_images = await image_service.get_user_images(current_user["id"])

        target_record = None
        for img in user_images:
            metadata = img.get("metadata", {}) or {}
            root_chapter_id = img.get("chapter_id")
            if root_chapter_id:
                root_chapter_id = str(root_chapter_id)

            if (
                (
                    metadata.get("chapter_id") == chapter_id
                    or root_chapter_id == chapter_id
                )
                and (
                    metadata.get("scene_number") == scene_number
                    or img.get("scene_number") == scene_number
                )
                and img.get("image_type") == "scene"
            ):
                target_record = img
                break

        if not target_record:
            raise HTTPException(status_code=404, detail="Scene image not found")

        # Delete the image
        success = await image_service.delete_image_record(
            target_record["id"], current_user["id"]
        )

        return DeleteImageResponse(
            success=success,
            message=(
                "Scene image deleted successfully"
                if success
                else "Failed to delete scene image"
            ),
            record_id=target_record["id"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting scene image: {str(e)}"
        )


@router.delete(
    "/{chapter_id}/images/characters/{character_name}",
    response_model=DeleteImageResponse,
)
async def delete_character_image(
    chapter_id: str,
    character_name: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete a character image for the chapter"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user["id"], session)

        # Find the image record
        image_service = StandaloneImageService(session)
        user_images = await image_service.get_user_images(current_user["id"])

        target_record = None
        for img in user_images:
            metadata = img.get("metadata", {}) or {}
            root_chapter_id = img.get("chapter_id")
            if root_chapter_id:
                root_chapter_id = str(root_chapter_id)

            if (
                (
                    metadata.get("chapter_id") == chapter_id
                    or root_chapter_id == chapter_id
                )
                and (
                    metadata.get("character_name") == character_name
                    or img.get("character_name") == character_name
                )
                and img.get("image_type") == "character"
            ):
                target_record = img
                break

        if not target_record:
            raise HTTPException(status_code=404, detail="Character image not found")

        # Delete the image
        success = await image_service.delete_image_record(
            target_record["id"], current_user["id"]
        )

        return DeleteImageResponse(
            success=success,
            message=(
                "Character image deleted successfully"
                if success
                else "Failed to delete character image"
            ),
            record_id=target_record["id"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting character image: {str(e)}"
        )


@router.post("/{chapter_id}/images/batch", response_model=BatchImageResponse)
async def batch_generate_images(
    chapter_id: str,
    request: BatchImageRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Generate multiple images for a chapter in batch"""
    try:
        # Verify chapter access
        chapter_data = await verify_chapter_access(
            chapter_id, current_user["id"], session
        )

        # Prepare batch requests
        batch_requests = []
        for img_request in request.images:
            img_type = img_request.get("type", "scene")

            # Common fields
            req_data = {
                "chapter_id": chapter_id,  # Pass chapter_id for metadata
                "style": img_request.get("style"),
                "aspect_ratio": img_request.get("aspect_ratio"),
                "custom_prompt": img_request.get("custom_prompt"),
            }

            if img_type == "scene":
                scene_num = img_request.get("scene_number")
                scene_desc = (
                    get_scene_description_from_chapter(chapter_data, scene_num)
                    if scene_num
                    else img_request.get("description", "")
                )
                if img_request.get("description"):
                    scene_desc = img_request.get("description")

                req_data.update(
                    {
                        "type": "scene",
                        "scene_description": scene_desc,
                        "scene_number": scene_num,
                        "style": img_request.get("style", "cinematic"),
                        "aspect_ratio": img_request.get("aspect_ratio", "16:9"),
                    }
                )

            elif img_type == "character":
                char_name = img_request.get("character_name", "")
                char_info = get_character_info_from_chapter(chapter_data, char_name)
                char_desc = (
                    char_info["description"]
                    if char_info
                    else img_request.get("description", "")
                )

                if img_request.get("description"):
                    char_desc = img_request.get("description")

                req_data.update(
                    {
                        "type": "character",
                        "character_name": char_name,
                        "character_description": char_desc,
                        "style": img_request.get("style", "realistic"),
                        "aspect_ratio": img_request.get("aspect_ratio", "3:4"),
                    }
                )

            else:
                # General image
                req_data.update(
                    {
                        "type": "general",
                        "prompt": img_request.get(
                            "prompt", img_request.get("description", "")
                        ),
                        "aspect_ratio": img_request.get("aspect_ratio", "16:9"),
                        "model_id": img_request.get("model_id", "gen4_image"),
                    }
                )

            batch_requests.append(req_data)

        # Generate batch
        image_service = StandaloneImageService(session)
        batch_results = await image_service.batch_generate_images(
            image_requests=batch_requests, user_id=current_user["id"]
        )

        successful_count = sum(1 for r in batch_results if r.get("status") == "success")

        return BatchImageResponse(
            results=batch_results,
            successful_count=successful_count,
            total_count=len(batch_results),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error in batch image generation: {str(e)}"
        )


@router.get("/{chapter_id}/images/batch/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    chapter_id: str,
    batch_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Get status of a batch image generation (placeholder - batch tracking not implemented)"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user["id"], session)

        # For now, return a placeholder response since batch tracking isn't implemented
        # In a real implementation, you'd track batches with IDs
        return BatchStatusResponse(
            batch_id=batch_id,
            status="completed",  # Assume completed for now
            completed_count=0,
            total_count=0,
            results=[],
            created_at="2024-01-01T00:00:00Z",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting batch status: {str(e)}"
        )


@router.get(
    "/{chapter_id}/images/status/{record_id}", response_model=ImageStatusResponse
)
async def get_image_generation_status(
    chapter_id: str,
    record_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Get the status of an image generation by record ID"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user["id"], session)

        # Get the image record
        stmt = select(ImageGeneration).where(ImageGeneration.id == record_id)
        result = await session.exec(stmt)
        image_record = result.first()

        if not image_record:
            raise HTTPException(
                status_code=404, detail="Image generation record not found"
            )

        # Verify the record belongs to the current user
        if str(image_record.user_id) != current_user["id"]:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this image generation"
            )

        # Verify the record is associated with the chapter
        metadata = image_record.meta or {}
        root_chapter_id = (
            str(image_record.chapter_id) if image_record.chapter_id else None
        )

        if metadata.get("chapter_id") != chapter_id and root_chapter_id != chapter_id:
            raise HTTPException(
                status_code=403,
                detail="Image generation is not associated with this chapter",
            )

        # Map status values
        status = image_record.status
        if status == "completed":
            status = "completed"
        elif status == "failed":
            status = "failed"
        elif status in ["processing", "generating"]:
            status = "processing"
        else:
            status = "pending"

        return ImageStatusResponse(
            record_id=record_id,
            status=status,
            image_url=image_record.image_url,
            prompt=image_record.image_prompt or image_record.text_prompt,
            script_id=str(image_record.script_id) if image_record.script_id else None,
            error_message=image_record.error_message,
            generation_time_seconds=image_record.generation_time_seconds,
            created_at=image_record.get("created_at"),
            updated_at=image_record.get("updated_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting image generation status: {str(e)}"
        )


@router.get(
    "/{chapter_id}/images/scenes/{scene_number}/status",
    response_model=ImageStatusResponse,
)
async def get_scene_image_status(
    chapter_id: str,
    scene_number: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Get the status of a scene image generation by chapter ID and scene number"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user["id"], supabase_client)

        # Query for the scene image record
        # Primary filter: chapter_id and scene_number (root-level)
        # Secondary filter: fallback to metadata->>'scene_number' if root-level is NULL
        print(
            f"[DEBUG] [get_scene_image_status] Querying for chapter_id={chapter_id}, scene_number={scene_number}"
        )

        # Try root-level scene_number first
        image_response = (
            supabase_client.table("image_generations")
            .select("*")
            .eq("chapter_id", chapter_id)
            .eq("scene_number", scene_number)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        # If no results, try metadata-based scene_number as fallback
        if not image_response.data:
            print(
                f"[DEBUG] [get_scene_image_status] No root-level scene_number match, trying metadata fallback"
            )
            # Use PostgreSQL JSONB operator to extract scene_number from metadata
            # Note: Supabase Python client doesn't support direct JSONB operations,
            # so we'll fetch all records for this chapter and filter in Python
            all_chapter_images = (
                supabase_client.table("image_generations")
                .select("*")
                .eq("chapter_id", chapter_id)
                .is_("scene_number", None)  # Only check records with NULL scene_number
                .order("created_at", desc=True)
                .execute()
            )

            # Filter by metadata scene_number in Python
            for record in all_chapter_images.data or []:
                metadata = record.get("metadata", {})
                metadata_scene_number = metadata.get("scene_number")
                if metadata_scene_number == scene_number:
                    image_response.data = [record]
                    print(
                        f"[DEBUG] [get_scene_image_status] Found match via metadata scene_number"
                    )
                    break

        if not image_response.data:
            print(
                f"[WARNING] [get_scene_image_status] No record found for chapter_id={chapter_id}, scene_number={scene_number}"
            )
            raise HTTPException(
                status_code=404,
                detail=f"No image generation found for scene {scene_number}",
            )

        image_record = image_response.data[0]

        # Verify the record belongs to the current user
        if image_record.get("user_id") != current_user["id"]:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this image generation"
            )

        # Extract scene_number from root-level or metadata
        record_scene_number = image_record.get("scene_number")
        if record_scene_number is None:
            metadata = image_record.get("metadata", {})
            record_scene_number = metadata.get("scene_number")

        # Map status values
        status = image_record.get("status", "pending")
        if status == "completed":
            status = "completed"
        elif status == "failed":
            status = "failed"
        elif status in ["processing", "generating"]:
            status = "processing"
        else:
            status = "pending"

        # Extract retry_count safely (ensure it's an int)
        retry_count = image_record.get("retry_count", 0)
        if retry_count is None:
            retry_count = 0
        retry_count = int(retry_count)

        return ImageStatusResponse(
            record_id=image_record.get("id"),
            status=status,
            image_url=image_record.get("image_url"),
            prompt=image_record.get("prompt") or image_record.get("image_prompt"),
            script_id=image_record.get("script_id"),
            scene_number=record_scene_number,
            retry_count=retry_count,
            error_message=image_record.get("error_message"),
            generation_time_seconds=image_record.get("generation_time_seconds"),
            created_at=image_record.get("created_at"),
            updated_at=image_record.get("updated_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(
            f"[ERROR] [get_scene_image_status] Error getting scene image status: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error getting scene image status: {str(e)}"
        )


@router.get("/{chapter_id}/audio", response_model=ChapterAudioResponse)
async def list_chapter_audio(
    chapter_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """List all audio files associated with a chapter"""
    try:
        # Verify chapter access
        chapter_data = await verify_chapter_access(
            chapter_id, current_user["id"], supabase_client
        )

        # Get user's audio files for this chapter
        print(
            f"[DEBUG] Querying audio_generations for user_id: {current_user['id']}, chapter_id: {chapter_id}"
        )
        audio_response = (
            supabase_client.table("audio_generations")
            .select("*")
            .eq("user_id", current_user["id"])
            .eq("chapter_id", chapter_id)
            .execute()
        )
        chapter_audio = [AudioRecord(**audio) for audio in (audio_response.data or [])]
        print(
            f"[DEBUG] Retrieved {len(chapter_audio)} audio records for chapter {chapter_id}"
        )
        return ChapterAudioResponse(
            chapter_id=chapter_id,
            audio_files=chapter_audio,
            total_count=len(chapter_audio),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Error listing chapter audio: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error listing chapter audio: {str(e)}"
        )


@router.post(
    "/{chapter_id}/audio/{audio_type}/{scene_number}",
    response_model=AudioGenerationQueuedResponse,
)
async def generate_chapter_audio(
    chapter_id: str,
    audio_type: str,
    scene_number: int,
    request: AudioGenerationRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Generate audio for a specific type and scene in the chapter (asynchronous)"""
    try:
        # Verify chapter access
        chapter_data = await verify_chapter_access(
            chapter_id, current_user["id"], supabase_client
        )

        # Validate audio type against old frontend enum values (for error message)
        old_valid_types = [
            "narration",
            "music",
            "effects",
            "ambiance",
            "dialogue",
            "sound_effects",
            "background_music",
            "sound_effect",
        ]
        if audio_type not in old_valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid audio type. Must be one of: {', '.join(old_valid_types)}",
            )

        # Map old frontend enum values to new database enum values
        audio_type_mapping = {
            "narration": "narrator",
            "music": "music",
            "effects": "sound_effect",
            "ambiance": "background_music",
            "dialogue": "character",
            "sound_effects": "sound_effect",
            "background_music": "background_music",
            "sound_effect": "sound_effect",
        }

        # Apply mapping if needed
        if audio_type in audio_type_mapping:
            audio_type = audio_type_mapping[audio_type]

        # Check script style validation for narrator audio
        if audio_type == "narrator":
            # Get the most recent script for this chapter
            script_response = (
                supabase_client.table("scripts")
                .select("script_style")
                .eq("chapter_id", chapter_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if script_response.data:
                script_style = script_response.data[0].get("script_style")
                # Reject narrator audio generation for cinematic scripts (character dialogue)
                if script_style == "cinematic":
                    raise HTTPException(
                        status_code=400,
                        detail="Narration audio cannot be generated for cinematic scripts. This script style contains character dialogue and is not suitable for narrator voice-over.",
                    )

        # Get content based on audio type
        text_content = None
        if audio_type == "narrator":
            # Get scene description for narration
            scene_description = get_scene_description_from_chapter(
                chapter_data, scene_number
            )
            text_content = (
                request.text
                or scene_description
                or f"Narration for scene {scene_number}"
            )
        elif audio_type == "character":
            # For character dialogue, text should be provided
            text_content = request.text
            if not text_content:
                raise HTTPException(
                    status_code=400, detail="Text content required for character audio"
                )
        else:
            # For music, sound_effect, background_music, sfx - use description or generate based on scene
            scene_description = get_scene_description_from_chapter(
                chapter_data, scene_number
            )
            text_content = (
                request.text
                or f"{audio_type} for scene {scene_number}: {scene_description}"
            )

        # Create initial record in database
        print(
            f"[DEBUG] Creating audio record with audio_type: {audio_type}, user_id: {current_user['id']}, chapter_id: {chapter_id}"
        )
        audio_record_data = {
            "user_id": current_user["id"],
            "chapter_id": chapter_id,
            "audio_type": audio_type,
            "text_content": text_content,
            "script_id": request.script_id,
            "generation_status": "pending",
            "metadata": {
                "scene_number": scene_number,
                "audio_type": audio_type,
                "voice_id": request.voice_id,
                "emotion": request.emotion,
                "speed": request.speed,
                "duration": request.duration,
            },
        }

        record_result = (
            supabase_client.table("audio_generations")
            .insert(audio_record_data)
            .execute()
        )
        record_id = record_result.data[0]["id"] if record_result.data else None

        if not record_id:
            raise HTTPException(
                status_code=500, detail="Failed to create audio generation record"
            )

        print(f"[DEBUG] Created audio record {record_id} for user {current_user['id']}")

        # Queue the audio generation task
        from app.tasks.audio_tasks import generate_chapter_audio_task

        task = generate_chapter_audio_task.delay(
            audio_type=audio_type,
            text_content=text_content,
            user_id=current_user["id"],
            chapter_id=chapter_id,
            scene_number=scene_number,
            voice_id=request.voice_id,
            emotion=request.emotion,
            speed=request.speed,
            duration=request.duration,
            record_id=record_id,
        )

        return AudioGenerationQueuedResponse(
            task_id=task.id,
            status="queued",
            message=f"{audio_type.title()} audio generation has been queued and will be processed in the background",
            estimated_time_seconds=30,  # Estimated time for audio generation
            record_id=record_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error queuing audio generation: {str(e)}"
        )


@router.delete("/{chapter_id}/audio/{audio_id}", response_model=DeleteAudioResponse)
async def delete_chapter_audio(
    chapter_id: str,
    audio_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete an audio file for the chapter"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user["id"], supabase_client)

        # Find the audio record
        audio_response = (
            supabase_client.table("audio_generations")
            .select("*")
            .eq("id", audio_id)
            .single()
            .execute()
        )

        if not audio_response.data:
            raise HTTPException(status_code=404, detail="Audio file not found")

        audio_record = audio_response.data

        # Verify the record belongs to the current user
        if audio_record.get("user_id") != current_user["id"]:
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this audio file"
            )

        # Verify the record is associated with the chapter
        metadata = audio_record.get("metadata", {})
        if metadata.get("chapter_id") != chapter_id:
            raise HTTPException(
                status_code=403, detail="Audio file is not associated with this chapter"
            )

        # Delete the audio record
        supabase_client.table("audio_generations").delete().eq("id", audio_id).execute()

        return DeleteAudioResponse(
            success=True, message="Audio file deleted successfully", record_id=audio_id
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting audio file: {str(e)}"
        )


@router.post("/{chapter_id}/audio/export", response_model=AudioExportResponse)
async def export_chapter_audio_mix(
    chapter_id: str,
    request: AudioExportRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Export a mixed audio file for the chapter (asynchronous)"""
    try:
        # Verify chapter access
        chapter_data = await verify_chapter_access(
            chapter_id, current_user["id"], supabase_client
        )

        # Get all audio files for this chapter
        audio_response = (
            supabase_client.table("audio_generations")
            .select("*")
            .eq("user_id", current_user["id"])
            .eq("chapter_id", chapter_id)
            .execute()
        )
        chapter_audio = audio_response.data or []

        if not chapter_audio:
            raise HTTPException(
                status_code=404, detail="No audio files found for this chapter"
            )

        # Filter audio by types based on request
        filtered_audio = []
        for audio in chapter_audio:
            audio_type = audio.get("audio_type")
            if (
                (audio_type == "narrator" and request.include_narration)
                or (
                    (audio_type in ["music", "background_music"])
                    and request.include_music
                )
                or ((audio_type in ["sound_effect", "sfx"]) and request.include_effects)
                or (audio_type == "background_music" and request.include_ambiance)
                or (audio_type == "character" and request.include_dialogue)
            ):
                filtered_audio.append(audio)

        if not filtered_audio:
            raise HTTPException(
                status_code=400, detail="No audio files match the export criteria"
            )

        # Create export record
        export_record_data = {
            "user_id": current_user["id"],
            "chapter_id": chapter_id,
            "export_format": request.format,
            "status": "pending",
            "audio_files": [audio["id"] for audio in filtered_audio],
            "mix_settings": request.mix_settings or {},
            "metadata": {
                "chapter_id": chapter_id,
                "include_narration": request.include_narration,
                "include_music": request.include_music,
                "include_effects": request.include_effects,
                "include_ambiance": request.include_ambiance,
                "include_dialogue": request.include_dialogue,
            },
        }

        export_result = (
            supabase_client.table("audio_exports").insert(export_record_data).execute()
        )
        export_id = export_result.data[0]["id"] if export_result.data else None

        if not export_id:
            raise HTTPException(
                status_code=500, detail="Failed to create audio export record"
            )

        # Queue the audio export task
        from app.tasks.audio_tasks import export_chapter_audio_mix_task

        task = export_chapter_audio_mix_task.delay(
            export_id=export_id,
            chapter_id=chapter_id,
            user_id=current_user["id"],
            audio_files=filtered_audio,
            export_format=request.format,
            mix_settings=request.mix_settings,
        )

        return AudioExportResponse(
            export_id=export_id,
            status="queued",
            message="Audio export has been queued and will be processed in the background",
            estimated_time_seconds=60,  # Estimated time for audio mixing
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error queuing audio export: {str(e)}"
        )


@router.get(
    "/{chapter_id}/audio/status/{record_id}", response_model=AudioStatusResponse
)
async def get_audio_generation_status(
    chapter_id: str,
    record_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Get the status of an audio generation by record ID"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user["id"], supabase_client)

        # Get the audio record
        audio_response = (
            supabase_client.table("audio_generations")
            .select("*")
            .eq("id", record_id)
            .single()
            .execute()
        )

        if not audio_response.data:
            raise HTTPException(
                status_code=404, detail="Audio generation record not found"
            )

        audio_record = audio_response.data

        # Verify the record belongs to the current user
        if audio_record.get("user_id") != current_user["id"]:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this audio generation"
            )

        # Verify the record is associated with the chapter
        metadata = audio_record.get("metadata", {})
        if metadata.get("chapter_id") != chapter_id:
            raise HTTPException(
                status_code=403,
                detail="Audio generation is not associated with this chapter",
            )

        # Map status values
        status = audio_record.get("generation_status", "pending")
        if status == "completed":
            status = "completed"
        elif status == "failed":
            status = "failed"
        elif status in ["processing", "generating"]:
            status = "processing"
        else:
            status = "pending"

        return AudioStatusResponse(
            record_id=record_id,
            status=status,
            audio_url=audio_record.get("audio_url"),
            error_message=audio_record.get("error_message"),
            duration=audio_record.get("duration"),
            created_at=audio_record.get("created_at"),
            updated_at=audio_record.get("updated_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting audio generation status: {str(e)}"
        )
