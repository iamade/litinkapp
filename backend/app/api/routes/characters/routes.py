from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

from app.plots.schemas import (
    CharacterResponse,
    CharacterUpdate,
    CharacterCreate,
    CharacterArchetypeResponse,
    ImageGenerationRequest,
)
from app.api.services.character import CharacterService
from app.core.database import get_session
from app.core.auth import get_current_active_user

router = APIRouter()


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get specific character details.

    - **character_id**: ID of the character to retrieve
    """
    try:
        character_service = CharacterService(session)
        character = await character_service.get_character_by_id(
            character_id, current_user.id
        )

        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        return character

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve character: {str(e)}"
        )


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    updates: CharacterUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Update character information.

    - **character_id**: ID of the character to update
    - **updates**: Fields to update
    """
    try:
        character_service = CharacterService(session)
        updated_character = await character_service.update_character(
            character_id=character_id, user_id=current_user.id, updates=updates
        )

        return updated_character

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update character: {str(e)}"
        )


@router.delete("/{character_id}")
async def delete_character(
    character_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Delete character.

    - **character_id**: ID of the character to delete
    """
    try:
        character_service = CharacterService(session)
        success = await character_service.delete_character(
            character_id, current_user.id
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete character")

        return {"message": "Character deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete character: {str(e)}"
        )


@router.post("/bulk-delete")
async def bulk_delete_characters(
    character_ids: List[str],
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Delete multiple characters at once.

    - **character_ids**: List of character IDs to delete
    """
    try:
        if not character_ids:
            raise HTTPException(status_code=400, detail="No character IDs provided")

        character_service = CharacterService(session)
        deleted_count = 0
        failed_count = 0

        for character_id in character_ids:
            try:
                success = await character_service.delete_character(
                    character_id, current_user.id
                )
                if success:
                    deleted_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1

        return {
            "message": f"Bulk delete completed",
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "total_requested": len(character_ids),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to bulk delete characters: {str(e)}"
        )


@router.post("/generate-details")
async def generate_character_details_with_ai(
    character_name: str,
    book_id: str,
    role: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Generate character details using AI by analyzing book content.
    Uses tier-appropriate AI models based on user subscription.

    - **character_name**: Name of the character to generate details for
    - **book_id**: ID of the book to analyze
    - **role**: Optional character role (protagonist, antagonist, supporting, etc.)

    Returns detailed character information including physical description, personality,
    character arc, want, need, lie, and ghost.
    """
    try:
        if not character_name or not character_name.strip():
            raise HTTPException(status_code=400, detail="Character name is required")

        character_service = CharacterService(session)

        character_details = (
            await character_service.generate_character_details_from_book(
                character_name=character_name.strip(),
                book_id=book_id,
                user_id=current_user.id,
                role=role,
            )
        )

        return {
            "success": True,
            "character_details": character_details,
            "message": "Character details generated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate character details: {str(e)}"
        )


@router.post("/plot/{plot_overview_id}", response_model=CharacterResponse)
async def create_character(
    plot_overview_id: str,
    character_data: CharacterCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Create a new character manually.

    - **plot_overview_id**: ID of the plot overview to add character to
    - **character_data**: Character information
    """
    try:
        character_service = CharacterService(session)
        character = await character_service.create_character(
            plot_overview_id=plot_overview_id,
            user_id=str(
                current_user.id
            ),  # Convert to string to avoid asyncpg UUID issues
            character_data=character_data,
        )

        return character

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create character: {str(e)}"
        )


@router.get("/plot/{plot_overview_id}", response_model=List[CharacterResponse])
async def get_characters_by_plot(
    plot_overview_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get all characters for a plot.

    - **plot_overview_id**: ID of the plot overview
    """
    try:
        character_service = CharacterService(session)
        characters = await character_service.get_characters_by_plot(
            plot_overview_id, current_user.id
        )

        return characters

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve characters: {str(e)}"
        )


@router.post("/{character_id}/analyze-archetypes")
async def analyze_character_archetypes(
    character_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Analyze character archetypes.

    - **character_id**: ID of the character to analyze
    """
    try:
        # Get character data first
        character_service = CharacterService(session)
        character = await character_service.get_character_by_id(
            character_id, current_user.id
        )

        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Analyze archetypes
        archetype_match = await character_service.analyze_character_archetypes(
            character_description=f"{character.name}: {character.physical_description or ''}",
            personality=character.personality or "",
        )

        # Update character with archetype analysis
        await character_service.update_character(
            character_id=character_id,
            user_id=current_user.id,
            updates=CharacterUpdate(archetypes=archetype_match.archetype_id),
        )

        return {
            "character_id": character_id,
            "archetype_match": archetype_match.dict(),
            "message": "Archetype analysis completed",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze archetypes: {str(e)}"
        )


@router.post("/{character_id}/generate-image")
async def generate_character_image(
    character_id: str,
    request: ImageGenerationRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Queue character portrait generation (async).

    Returns task information for status tracking.

    - **character_id**: ID of the character
    - **request**: Image generation parameters (prompt, style, aspect_ratio)

    Response includes:
    - task_id: Celery task ID for status tracking
    - record_id: Image generation record ID
    - status: Current status (queued)
    - estimated_time_seconds: Estimated completion time
    """
    try:
        character_service = CharacterService(session)

        style = getattr(request, "style", "realistic")
        aspect_ratio = getattr(request, "aspect_ratio", "3:4")

        result = await character_service.generate_character_image(
            character_id=character_id,
            user_id=current_user.id,
            custom_prompt=request.prompt,
            style=style,
            aspect_ratio=aspect_ratio,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue character image generation: {str(e)}",
        )


@router.get("/{character_id}/image-status")
async def get_character_image_status(
    character_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get character image generation status.

    Returns current status of image generation including:
    - status: none, pending, generating, completed, failed
    - task_id: Celery task ID (if available)
    - image_url: Generated image URL (if completed)
    - error: Error message (if failed)

    - **character_id**: ID of the character
    """
    try:
        character_service = CharacterService(session)
        status = await character_service.get_character_image_status(
            character_id=character_id, user_id=current_user.id
        )

        return status

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get image status: {str(e)}"
        )


@router.get("/archetypes", response_model=List[CharacterArchetypeResponse])
async def get_all_archetypes(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get all available character archetypes.
    """
    try:
        character_service = CharacterService(session)
        archetypes = await character_service.get_all_archetypes()

        return archetypes

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve archetypes: {str(e)}"
        )


@router.get(
    "/archetypes/category/{category}", response_model=List[CharacterArchetypeResponse]
)
async def get_archetypes_by_category(
    category: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get archetypes by category.

    - **category**: Archetype category (e.g., "Ego", "Shadow", "Soul", "Self")
    """
    try:
        character_service = CharacterService(session)
        archetypes = await character_service.get_archetypes_by_category(category)

        return archetypes

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve archetypes by category: {str(e)}",
        )
