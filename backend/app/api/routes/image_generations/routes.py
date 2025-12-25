from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth import get_current_active_user
from app.core.database import get_session
from app.core.services.standalone_image import StandaloneImageService
from app.images.schemas import DeleteImageResponse
from app.videos.models import ImageGeneration

router = APIRouter()


@router.post("/delete", response_model=DeleteImageResponse)
async def delete_image_generations(
    request: dict,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete multiple image generation records and their associated storage objects"""
    try:
        ids = request.get("ids", [])
        if not ids or not isinstance(ids, list):
            raise HTTPException(
                status_code=400, detail="ids must be a non-empty list of strings"
            )

        print(f"[DELETE] Attempting to delete {len(ids)} images: {ids}")

        image_service = StandaloneImageService(session)

        # Delete each image record (the service handles storage cleanup)
        deleted_count = 0
        failed_ids = []
        for record_id in ids:
            print(f"[DELETE] Processing deletion for record_id: {record_id}")
            success = await image_service.delete_image_record(
                record_id, current_user["id"]
            )
            if success:
                deleted_count += 1
                print(f"[DELETE] Successfully deleted: {record_id}")
            else:
                failed_ids.append(record_id)
                print(f"[DELETE] Failed to delete: {record_id}")

        # Verify deletion
        print(f"[DELETE] Verifying deletion - checking if records still exist")
        statement = select(ImageGeneration.id).where(col(ImageGeneration.id).in_(ids))
        result = await session.exec(statement)
        remaining_ids = result.all()

        if remaining_ids:
            print(
                f"[DELETE] WARNING: {len(remaining_ids)} records still exist after deletion: {remaining_ids}"
            )

        print(
            f"[DELETE] Deletion complete: {deleted_count} deleted, {len(failed_ids)} failed"
        )

        return DeleteImageResponse(
            success=deleted_count > 0,
            message=f"Successfully deleted {deleted_count} out of {len(ids)} image(s)",
            record_id=None,  # Not applicable for bulk operations
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
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete all scene image generation records for a script and their associated storage objects"""
    try:
        script_id = request.get("script_id")
        if not script_id:
            raise HTTPException(status_code=400, detail="script_id is required")

        print(
            f"[DELETE-ALL] Attempting to delete all scene images for script: {script_id}"
        )

        image_service = StandaloneImageService(session)

        # Get all scene images for this script
        user_images = await image_service.get_user_images(current_user["id"], "scene")
        print(f"[DELETE-ALL] Found {len(user_images)} total scene images for user")

        # Filter by script_id (check both root-level and metadata fields)
        script_images = [
            img
            for img in user_images
            if img.get("script_id") == script_id
            or img.get("metadata", {}).get("script_id") == script_id
        ]
        print(
            f"[DELETE-ALL] Filtered to {len(script_images)} images for script {script_id}"
        )

        ids_to_delete = [img["id"] for img in script_images]
        print(f"[DELETE-ALL] Image IDs to delete: {ids_to_delete}")

        # Delete each image record
        deleted_count = 0
        for image_record in script_images:
            success = await image_service.delete_image_record(
                image_record["id"], current_user["id"]
            )
            if success:
                deleted_count += 1

        # Verify deletion
        if ids_to_delete:
            statement = select(ImageGeneration.id).where(
                col(ImageGeneration.id).in_(ids_to_delete)
            )
            result = await session.exec(statement)
            remaining_ids = result.all()

            if remaining_ids:
                print(
                    f"[DELETE-ALL] WARNING: {len(remaining_ids)} records still exist after deletion: {remaining_ids}"
                )

        print(
            f"[DELETE-ALL] Deletion complete: {deleted_count} deleted out of {len(script_images)} attempted"
        )

        return DeleteImageResponse(
            success=deleted_count > 0,
            message=f"Successfully deleted {deleted_count} scene image(s) for script {script_id}",
            record_id=None,  # Not applicable for bulk operations
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting all scene generations: {str(e)}"
        )
