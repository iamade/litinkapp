from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.auth import get_current_active_user
from app.core.database import get_supabase
from app.services.standalone_image_service import StandaloneImageService
from app.tasks.image_tasks import generate_character_image_task
from app.schemas.image import (
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
    ImageStatusResponse
)

router = APIRouter()


async def verify_chapter_access(chapter_id: str, user_id: str, supabase_client: Client) -> Dict[str, Any]:
    """Verify user has access to the chapter and return chapter data"""
    try:
        # Get chapter with book info
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()

        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")

        chapter_data = chapter_response.data
        book_data = chapter_data.get('books', {})

        # Check access permissions (published books or owned by user)
        if book_data.get('status') != 'READY' and book_data.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this chapter")

        return chapter_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying chapter access: {str(e)}")


def get_scene_description_from_chapter(chapter_data: Dict[str, Any], scene_number: int) -> str:
    """Extract scene description from chapter AI content"""
    ai_content = chapter_data.get('ai_generated_content', {})

    # Look for scene descriptions in AI content
    for key, content in ai_content.items():
        if isinstance(content, dict) and 'scene_descriptions' in content:
            scenes = content['scene_descriptions']
            if isinstance(scenes, list) and len(scenes) > scene_number - 1:
                return scenes[scene_number - 1]

    # Fallback: generate a basic scene description
    chapter_title = chapter_data.get('title', 'Unknown Chapter')
    return f"Scene from chapter: {chapter_title}. A visual representation of the events and setting described in this part of the story."


def get_character_info_from_chapter(chapter_data: Dict[str, Any], character_name: str) -> Optional[Dict[str, str]]:
    """Extract character information from chapter AI content"""
    ai_content = chapter_data.get('ai_generated_content', {})

    # Look for characters in AI content
    for key, content in ai_content.items():
        if isinstance(content, dict) and 'characters' in content and 'character_details' in content:
            characters = content['characters']
            character_details = content['character_details']

            if isinstance(characters, list) and character_name in characters:
                # Find detailed character info
                for detail in character_details:
                    if isinstance(detail, dict) and detail.get('name') == character_name:
                        return {
                            'name': character_name,
                            'description': detail.get('description', f"Character {character_name} from the story")
                        }

                # Fallback with basic info
                return {
                    'name': character_name,
                    'description': f"Character {character_name} appearing in the chapter"
                }

    return None


@router.get("/{chapter_id}/images", response_model=ChapterImagesResponse)
async def list_chapter_images(
    chapter_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """List all images associated with a chapter"""
    try:
        # Verify chapter access
        chapter_data = await verify_chapter_access(chapter_id, current_user['id'], supabase_client)

        # Get user's standalone images
        image_service = StandaloneImageService(supabase_client)
        user_images = await image_service.get_user_images(current_user['id'])

        # Filter images associated with this chapter (via metadata)
        chapter_images = []
        for img in user_images:
            metadata = img.get('metadata', {})
            if metadata.get('chapter_id') == chapter_id:
                chapter_images.append(ImageRecord(**img))

        return ChapterImagesResponse(
            chapter_id=chapter_id,
            images=chapter_images,
            total_count=len(chapter_images)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing chapter images: {str(e)}")


@router.post("/{chapter_id}/images/scenes/{scene_number}", response_model=ImageGenerationResponse)
async def generate_scene_image(
    chapter_id: str,
    scene_number: int,
    request: SceneImageRequest,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate an image for a specific scene in the chapter"""
    try:
        # Verify chapter access
        chapter_data = await verify_chapter_access(chapter_id, current_user['id'], supabase_client)

        # Get scene description
        scene_description = get_scene_description_from_chapter(chapter_data, scene_number)
        if not scene_description:
            raise HTTPException(status_code=400, detail=f"Scene {scene_number} not found in chapter")

        # Override with custom description if provided
        if request.scene_description:
            scene_description = request.scene_description

        # Generate image
        image_service = StandaloneImageService(supabase_client)
        result = await image_service.generate_scene_image(
            scene_description=scene_description,
            user_id=current_user['id'],
            style=request.style,
            aspect_ratio=request.aspect_ratio,
            custom_prompt=request.custom_prompt
        )

        # Add chapter association to metadata
        record_id = result['record_id']
        metadata_update = {
            "chapter_id": chapter_id,
            "scene_number": scene_number,
            "image_type": "scene"
        }

        # Update metadata in database
        supabase_client.table('image_generations').update({
            "metadata": metadata_update
        }).eq('id', record_id).execute()

        return ImageGenerationResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating scene image: {str(e)}")


@router.post("/{chapter_id}/images/characters", response_model=ImageGenerationQueuedResponse)
async def generate_character_image(
    chapter_id: str,
    request: CharacterImageRequest,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate an image for a character in the chapter (asynchronous)"""
    try:
        # Verify chapter access
        chapter_data = await verify_chapter_access(chapter_id, current_user['id'], supabase_client)

        # Get character info from chapter
        character_info = get_character_info_from_chapter(chapter_data, request.character_name)
        if not character_info:
            # Allow generation even if character not found in AI content
            character_info = {
                'name': request.character_name,
                'description': request.character_description or f"Character {request.character_name}"
            }

        # Override with provided description if given
        if request.character_description:
            character_info['description'] = request.character_description

        # Create initial record in database
        image_service = StandaloneImageService(supabase_client)
        record_data = {
            'user_id': current_user['id'],
            'image_type': 'character',
            'character_name': character_info['name'],
            'scene_description': character_info['description'],
            'status': 'pending',
            'metadata': {
                'chapter_id': chapter_id,
                'character_name': character_info['name'],
                'image_type': 'character'
            }
        }

        record_result = supabase_client.table('image_generations').insert(record_data).execute()
        record_id = record_result.data[0]['id'] if record_result.data else None

        if not record_id:
            raise HTTPException(status_code=500, detail="Failed to create image generation record")

        # Queue the character image generation task
        task = generate_character_image_task.delay(
            character_name=character_info['name'],
            character_description=character_info['description'],
            user_id=current_user['id'],
            chapter_id=chapter_id,
            style=request.style,
            aspect_ratio=request.aspect_ratio,
            custom_prompt=request.custom_prompt,
            record_id=record_id  # Pass the record_id to the task
        )

        return ImageGenerationQueuedResponse(
            task_id=task.id,
            status="queued",
            message="Character image generation has been queued and will be processed in the background",
            estimated_time_seconds=60,  # Estimated time for character image generation
            record_id=record_id  # Include record_id for polling
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error queuing character image generation: {str(e)}")


@router.delete("/{chapter_id}/images/scenes/{scene_number}", response_model=DeleteImageResponse)
async def delete_scene_image(
    chapter_id: str,
    scene_number: int,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a scene image for the chapter"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user['id'], supabase_client)

        # Find the image record
        image_service = StandaloneImageService(supabase_client)
        user_images = await image_service.get_user_images(current_user['id'])

        target_record = None
        for img in user_images:
            metadata = img.get('metadata', {})
            if (metadata.get('chapter_id') == chapter_id and
                metadata.get('scene_number') == scene_number and
                metadata.get('image_type') == 'scene'):
                target_record = img
                break

        if not target_record:
            raise HTTPException(status_code=404, detail="Scene image not found")

        # Delete the image
        success = await image_service.delete_image_record(target_record['id'], current_user['id'])

        return DeleteImageResponse(
            success=success,
            message="Scene image deleted successfully" if success else "Failed to delete scene image",
            record_id=target_record['id']
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting scene image: {str(e)}")


@router.delete("/{chapter_id}/images/characters/{character_name}", response_model=DeleteImageResponse)
async def delete_character_image(
    chapter_id: str,
    character_name: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a character image for the chapter"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user['id'], supabase_client)

        # Find the image record
        image_service = StandaloneImageService(supabase_client)
        user_images = await image_service.get_user_images(current_user['id'])

        target_record = None
        for img in user_images:
            metadata = img.get('metadata', {})
            if (metadata.get('chapter_id') == chapter_id and
                metadata.get('character_name') == character_name and
                metadata.get('image_type') == 'character'):
                target_record = img
                break

        if not target_record:
            raise HTTPException(status_code=404, detail="Character image not found")

        # Delete the image
        success = await image_service.delete_image_record(target_record['id'], current_user['id'])

        return DeleteImageResponse(
            success=success,
            message="Character image deleted successfully" if success else "Failed to delete character image",
            record_id=target_record['id']
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting character image: {str(e)}")


@router.post("/{chapter_id}/images/batch", response_model=BatchImageResponse)
async def batch_generate_images(
    chapter_id: str,
    request: BatchImageRequest,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate multiple images for a chapter in batch"""
    try:
        # Verify chapter access
        chapter_data = await verify_chapter_access(chapter_id, current_user['id'], supabase_client)

        # Prepare batch requests
        batch_requests = []
        for img_request in request.images:
            img_type = img_request.get('type', 'scene')

            if img_type == 'scene':
                scene_num = img_request.get('scene_number')
                scene_desc = get_scene_description_from_chapter(chapter_data, scene_num) if scene_num else img_request.get('description', '')
                if img_request.get('description'):
                    scene_desc = img_request.get('description')

                batch_requests.append({
                    'type': 'scene',
                    'scene_description': scene_desc,
                    'style': img_request.get('style', 'cinematic'),
                    'aspect_ratio': img_request.get('aspect_ratio', '16:9'),
                    'custom_prompt': img_request.get('custom_prompt')
                })

            elif img_type == 'character':
                char_name = img_request.get('character_name', '')
                char_info = get_character_info_from_chapter(chapter_data, char_name)
                char_desc = char_info['description'] if char_info else img_request.get('description', '')

                if img_request.get('description'):
                    char_desc = img_request.get('description')

                batch_requests.append({
                    'type': 'character',
                    'character_name': char_name,
                    'character_description': char_desc,
                    'style': img_request.get('style', 'realistic'),
                    'aspect_ratio': img_request.get('aspect_ratio', '3:4'),
                    'custom_prompt': img_request.get('custom_prompt')
                })

            else:
                # General image
                batch_requests.append({
                    'type': 'general',
                    'prompt': img_request.get('prompt', img_request.get('description', '')),
                    'aspect_ratio': img_request.get('aspect_ratio', '16:9'),
                    'model_id': img_request.get('model_id', 'gen4_image')
                })

        # Generate batch
        image_service = StandaloneImageService(supabase_client)
        batch_results = await image_service.batch_generate_images(
            image_requests=batch_requests,
            user_id=current_user['id']
        )

        # Update metadata for successful generations to include chapter_id
        for i, result in enumerate(batch_results):
            if result.get('status') == 'success' and result.get('record_id'):
                metadata_update = {
                    "chapter_id": chapter_id,
                    "batch_index": i
                }

                img_request = request.images[i]
                if img_request.get('type') == 'scene':
                    metadata_update.update({
                        "image_type": "scene",
                        "scene_number": img_request.get('scene_number')
                    })
                elif img_request.get('type') == 'character':
                    metadata_update.update({
                        "image_type": "character",
                        "character_name": img_request.get('character_name')
                    })

                supabase_client.table('image_generations').update({
                    "metadata": metadata_update
                }).eq('id', result['record_id']).execute()

        successful_count = sum(1 for r in batch_results if r.get('status') == 'success')

        return BatchImageResponse(
            results=batch_results,
            successful_count=successful_count,
            total_count=len(batch_results)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in batch image generation: {str(e)}")


@router.get("/{chapter_id}/images/batch/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    chapter_id: str,
    batch_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get status of a batch image generation (placeholder - batch tracking not implemented)"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user['id'], supabase_client)

        # For now, return a placeholder response since batch tracking isn't implemented
        # In a real implementation, you'd track batches with IDs
        return BatchStatusResponse(
            batch_id=batch_id,
            status="completed",  # Assume completed for now
            completed_count=0,
            total_count=0,
            results=[],
            created_at="2024-01-01T00:00:00Z"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting batch status: {str(e)}")


@router.get("/{chapter_id}/images/status/{record_id}", response_model=ImageStatusResponse)
async def get_image_generation_status(
    chapter_id: str,
    record_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get the status of an image generation by record ID"""
    try:
        # Verify chapter access
        await verify_chapter_access(chapter_id, current_user['id'], supabase_client)

        # Get the image record
        image_response = supabase_client.table('image_generations').select('*').eq('id', record_id).single().execute()

        if not image_response.data:
            raise HTTPException(status_code=404, detail="Image generation record not found")

        image_record = image_response.data

        # Verify the record belongs to the current user
        if image_record.get('user_id') != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this image generation")

        # Verify the record is associated with the chapter
        metadata = image_record.get('metadata', {})
        if metadata.get('chapter_id') != chapter_id:
            raise HTTPException(status_code=403, detail="Image generation is not associated with this chapter")

        # Map status values
        status = image_record.get('status', 'pending')
        if status == 'completed':
            status = 'completed'
        elif status == 'failed':
            status = 'failed'
        elif status in ['processing', 'generating']:
            status = 'processing'
        else:
            status = 'pending'

        return ImageStatusResponse(
            record_id=record_id,
            status=status,
            image_url=image_record.get('image_url'),
            error_message=image_record.get('error_message'),
            generation_time_seconds=image_record.get('generation_time_seconds'),
            created_at=image_record.get('created_at'),
            updated_at=image_record.get('updated_at')
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting image generation status: {str(e)}")