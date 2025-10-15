from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.auth import get_current_active_user
from app.core.database import get_supabase
from app.services.standalone_image_service import StandaloneImageService
from app.schemas.image import DeleteImageResponse

router = APIRouter()


@router.post("/delete", response_model=DeleteImageResponse)
async def delete_image_generations(
    request: dict,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete multiple image generation records and their associated storage objects"""
    try:
        ids = request.get("ids", [])
        if not ids or not isinstance(ids, list):
            raise HTTPException(
                status_code=400, detail="ids must be a non-empty list of strings"
            )

        image_service = StandaloneImageService(supabase_client)

        # Delete each image record (the service handles storage cleanup)
        deleted_count = 0
        for record_id in ids:
            success = await image_service.delete_image_record(record_id, current_user["id"])
            if success:
                deleted_count += 1

        return DeleteImageResponse(
            success=deleted_count > 0,
            message=f"Successfully deleted {deleted_count} out of {len(ids)} image(s)",
            record_id=None  # Not applicable for bulk operations
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting image generations: {str(e)}"
        )


@router.post("/delete-all", response_model=DeleteImageResponse)
async def delete_all_scene_generations(
    request: dict,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete all scene image generation records for a script and their associated storage objects"""
    try:
        script_id = request.get("script_id")
        if not script_id:
            raise HTTPException(
                status_code=400, detail="script_id is required"
            )

        image_service = StandaloneImageService(supabase_client)

        # Get all scene images for this script
        user_images = await image_service.get_user_images(current_user["id"], "scene")

        # Filter by script_id (check both root-level and metadata fields)
        script_images = [
            img for img in user_images
            if img.get("script_id") == script_id or img.get("metadata", {}).get("script_id") == script_id
        ]

        # Delete each image record
        deleted_count = 0
        for image_record in script_images:
            success = await image_service.delete_image_record(image_record["id"], current_user["id"])
            if success:
                deleted_count += 1

        return DeleteImageResponse(
            success=deleted_count > 0,
            message=f"Successfully deleted {deleted_count} scene image(s) for script {script_id}",
            record_id=None  # Not applicable for bulk operations
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting all scene generations: {str(e)}"
        )