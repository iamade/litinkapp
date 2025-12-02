from datetime import datetime
from typing import Optional, List
import uuid
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
from fastapi.responses import StreamingResponse
from app.merges.schemas import (
    MergeRequest,
    MergeResponse,
    MergeStatus,
    MergeHistoryResponse,
    MergePreviewRequest,
    MergePreviewResponse,
    MergeConflictResolution,
    MergeOperation,
    MergeError,
)
from app.core.database import get_supabase
from app.core.auth import get_current_active_user
from app.core.config import settings
from supabase import Client
import json
import os
import mimetypes
import io

router = APIRouter()


def validate_ffmpeg_params(ffmpeg_params: dict) -> None:
    """Validate FFmpeg parameters for security"""
    if not ffmpeg_params:
        return

    # Dangerous parameters that should not be allowed
    dangerous_params = [
        "f",
        "format",  # Format specification
        "i",  # Input file (should be controlled)
        "y",  # Overwrite (handled internally)
        "n",  # No overwrite
        "stream_loop",  # Infinite loops
        "loop",  # Infinite loops
        "t",
        "to",
        "ss",
        "sseof",  # Time-based parameters (controlled)
    ]

    for param in dangerous_params:
        if param in ffmpeg_params:
            raise HTTPException(
                status_code=400,
                detail=f"FFmpeg parameter '{param}' is not allowed for security reasons",
            )

    # Validate custom filters for dangerous operations
    custom_filters = ffmpeg_params.get("custom_filters", [])
    dangerous_filters = ["eval", "sendcmd", "zmq", "frei0r"]

    for filter_str in custom_filters:
        for dangerous in dangerous_filters:
            if dangerous in filter_str.lower():
                raise HTTPException(
                    status_code=400,
                    detail=f"FFmpeg filter containing '{dangerous}' is not allowed",
                )


def validate_file_upload(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check file size (max 500MB)
    max_size = 500 * 1024 * 1024  # 500MB
    if hasattr(file, "size") and file.size > max_size:
        raise HTTPException(
            status_code=400, detail="File size exceeds maximum allowed size (500MB)"
        )

    # Check file type
    allowed_types = [
        "video/mp4",
        "video/webm",
        "video/mov",
        "video/avi",
        "audio/mp3",
        "audio/wav",
        "audio/m4a",
        "audio/aac",
    ]

    if hasattr(file, "content_type") and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed. Allowed types: {', '.join(allowed_types)}",
        )


@router.post("/manual", response_model=MergeManualResponse)
async def start_manual_merge(
    request: MergeManualRequest,
    background_tasks: BackgroundTasks,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
):
    """Start a manual merge operation with user-controlled parameters"""
    try:
        # Validate FFmpeg parameters
        if request.ffmpeg_params:
            validate_ffmpeg_params(request.ffmpeg_params.dict())

        # If video_generation_id is provided, verify access
        if request.video_generation_id:
            video_gen = (
                supabase_client.table("video_generations")
                .select("*")
                .eq("id", request.video_generation_id)
                .eq("user_id", current_user["id"])
                .single()
                .execute()
            )

            if not video_gen.data:
                raise HTTPException(
                    status_code=404,
                    detail="Video generation not found or access denied",
                )

        # Generate merge ID
        merge_id = str(uuid.uuid4())

        # Create merge operation record
        merge_data = {
            "id": merge_id,
            "user_id": current_user["id"],
            "video_generation_id": request.video_generation_id,
            "merge_status": "PENDING",
            "progress": 0,
            "input_sources": [source.dict() for source in request.input_sources],
            "quality_tier": request.quality_tier.value,
            "output_format": request.output_format.value,
            "ffmpeg_params": (
                request.ffmpeg_params.dict() if request.ffmpeg_params else None
            ),
            "merge_name": request.merge_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        # Store in database
        supabase_client.table("merge_operations").insert(merge_data).execute()

        # Start background merge task
        background_tasks.add_task(
            process_manual_merge, merge_id, request, current_user["id"]
        )

        # Estimate processing time based on input sources
        estimated_duration = (
            len(request.input_sources) * 30
        )  # Rough estimate: 30s per source

        return MergeManualResponse(
            merge_id=merge_id,
            status=MergeStatus.PENDING,
            message="Manual merge operation started",
            estimated_duration=estimated_duration,
            queue_position=1,  # TODO: Implement proper queue management
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview", response_model=MergePreviewResponse)
async def generate_merge_preview(
    request: MergePreviewRequest,
    background_tasks: BackgroundTasks,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
):
    """Generate a preview of the merge operation without full processing"""
    try:
        # Validate FFmpeg parameters
        if request.ffmpeg_params:
            validate_ffmpeg_params(request.ffmpeg_params.dict())

        # Generate preview ID
        preview_id = str(uuid.uuid4())

        # Start background preview task
        background_tasks.add_task(
            process_merge_preview, preview_id, request, current_user["id"]
        )

        return MergePreviewResponse(
            preview_url="",  # Will be updated when processing completes
            preview_duration=request.preview_duration,
            status="processing",
            message="Preview generation started",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{merge_id}", response_model=MergeStatusResponse)
async def get_merge_status(
    merge_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
):
    """Check the status and progress of a merge operation"""
    try:
        print(
            f"[MERGE STATUS] Checking status for merge_id: {merge_id}, user: {current_user.get('id')}"
        )

        # Query merge operation from database
        merge_result = (
            supabase_client.table("merge_operations")
            .select("*")
            .eq("id", merge_id)
            .eq("user_id", current_user["id"])
            .single()
            .execute()
        )

        if not merge_result.data:
            raise HTTPException(
                status_code=404, detail="Merge operation not found or access denied"
            )

        merge_data = merge_result.data

        # Map database status to enum
        status_map = {
            "PENDING": MergeStatus.PENDING,
            "IN_PROGRESS": MergeStatus.PROCESSING,
            "COMPLETED": MergeStatus.COMPLETED,
            "FAILED": MergeStatus.FAILED,
        }

        status = status_map.get(
            merge_data.get("merge_status", "PENDING"), MergeStatus.PENDING
        )

        # Determine current step based on status and progress
        current_step = "Initializing"
        if status == MergeStatus.PROCESSING:
            progress = merge_data.get("progress", 0)
            if progress < 25:
                current_step = "Preparing input files"
            elif progress < 50:
                current_step = "Processing files"
            elif progress < 85:
                current_step = "Merging content"
            else:
                current_step = "Finalizing upload"
        elif status == MergeStatus.COMPLETED:
            current_step = "Complete"
        elif status == MergeStatus.FAILED:
            current_step = "Failed"

        response = MergeStatusResponse(
            merge_id=merge_id,
            status=status,
            progress_percentage=float(merge_data.get("progress", 0)),
            current_step=current_step,
            output_url=merge_data.get("output_file_url"),
            preview_url=merge_data.get("preview_url"),
            error_message=merge_data.get("error_message"),
            processing_stats=merge_data.get("processing_stats", {}),
            created_at=datetime.fromisoformat(
                merge_data.get("created_at", datetime.now().isoformat())
            ),
            updated_at=datetime.fromisoformat(
                merge_data.get("updated_at", datetime.now().isoformat())
            ),
        )

        print(f"[MERGE STATUS] Response: {response.dict()}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"[MERGE STATUS ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{merge_id}/download")
async def download_merge_result(
    merge_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
):
    """Download the completed merge result"""
    try:
        print(
            f"[MERGE DOWNLOAD] Downloading merge result for merge_id: {merge_id}, user: {current_user.get('id')}"
        )

        # Validate merge_id format
        try:
            uuid.UUID(merge_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid merge ID format")

        # Query merge operation from database
        merge_result = (
            supabase_client.table("merge_operations")
            .select("*")
            .eq("id", merge_id)
            .eq("user_id", current_user["id"])
            .single()
            .execute()
        )

        if not merge_result.data:
            raise HTTPException(
                status_code=404, detail="Merge operation not found or access denied"
            )

        merge_data = merge_result.data

        # Check if merge operation is completed
        if merge_data.get("merge_status") != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail=f"Merge operation is not completed. Current status: {merge_data.get('merge_status')}",
            )

        # Get output file URL
        output_file_url = merge_data.get("output_file_url")
        if not output_file_url:
            raise HTTPException(
                status_code=404,
                detail="Output file URL not found for completed merge operation",
            )

        # Extract storage path from Supabase URL
        # Supabase URLs typically look like: https://[project].supabase.co/storage/v1/object/public/[bucket]/[path]
        try:
            # Parse the URL to extract the file path
            from urllib.parse import urlparse

            parsed_url = urlparse(output_file_url)
            path_parts = parsed_url.path.split("/")

            # Find the bucket name and extract the path after it
            bucket_index = -1
            for i, part in enumerate(path_parts):
                if part == settings.SUPABASE_BUCKET_NAME:
                    bucket_index = i
                    break

            if bucket_index == -1:
                raise ValueError("Bucket name not found in URL")

            storage_path = "/".join(path_parts[bucket_index + 1 :])

        except Exception as e:
            print(
                f"[MERGE DOWNLOAD] Error parsing storage path from URL {output_file_url}: {str(e)}"
            )
            raise HTTPException(
                status_code=500, detail="Invalid output file URL format"
            )

        # Download file from Supabase Storage
        try:
            file_content = supabase_client.storage.from_(
                settings.SUPABASE_BUCKET_NAME
            ).download(storage_path)
            if file_content is None:
                raise HTTPException(status_code=404, detail="File not found in storage")
        except Exception as e:
            print(f"[MERGE DOWNLOAD] Error downloading from Supabase Storage: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Failed to download file from storage"
            )

        # Determine content type and filename
        content_type, _ = mimetypes.guess_type(storage_path)
        if not content_type:
            # Default to video/mp4 for merge operations
            content_type = "video/mp4"

        # Extract filename from storage path
        filename = os.path.basename(storage_path)
        if not filename:
            filename = f"merge_{merge_id}.mp4"

        # Create file-like object for streaming
        file_like = io.BytesIO(file_content)

        # Return streaming response
        return StreamingResponse(
            file_like,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_content)),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[MERGE DOWNLOAD ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def upload_file_to_supabase(
    file: UploadFile, file_type: str, user_id: str, supabase_client: Client
) -> tuple[str, int]:
    """Upload file to Supabase Storage and return public URL and file size"""
    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Create storage path with user organization
        if file_type == "video":
            folder = "videos"
            content_type = "video/mp4"
        elif file_type == "audio":
            folder = "audio"
            content_type = "audio/mp3"
        else:
            folder = "files"
            content_type = file.content_type or "application/octet-stream"

        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".bin"
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        storage_path = f"users/{user_id}/merge/{folder}/{unique_filename}"

        # Upload to Supabase Storage
        supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
            path=storage_path,
            file=file_content,
            file_options={"content-type": content_type},
        )

        # Get public URL
        public_url = supabase_client.storage.from_(
            settings.SUPABASE_BUCKET_NAME
        ).get_public_url(storage_path)

        print(f"[FILE UPLOAD] File uploaded to Supabase: {public_url}")
        return public_url, file_size

    except Exception as e:
        print(f"[FILE UPLOAD ERROR] Failed to upload to Supabase: {str(e)}")
        raise


@router.post("/upload")
async def upload_merge_file(
    file: UploadFile = File(...),
    file_type: str = Form(..., description="Type of file: video or audio"),
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
):
    """Upload a file for use in merge operations"""
    try:
        print(
            f"[FILE UPLOAD] Starting upload for file: {file.filename}, type: {file_type}, user: {current_user.get('id')}"
        )

        # Validate file type
        if file_type not in ["video", "audio"]:
            raise HTTPException(
                status_code=400, detail="File type must be 'video' or 'audio'"
            )

        # Validate file
        validate_file_upload(file)
        print(f"[FILE UPLOAD] File validation passed")

        # Upload file to Supabase Storage
        file_url, file_size = await upload_file_to_supabase(
            file, file_type, current_user["id"], supabase_client
        )

        # Create merge operation record
        merge_id = str(uuid.uuid4())
        merge_data = {
            "id": merge_id,
            "user_id": current_user["id"],
            "merge_status": "PENDING",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        # Set the appropriate file URL based on type
        if file_type == "video":
            merge_data["video_file_url"] = file_url
        elif file_type == "audio":
            merge_data["audio_file_url"] = file_url

        # Insert merge operation record
        supabase_client.table("merge_operations").insert(merge_data).execute()

        response = {
            "merge_id": merge_id,
            "file_url": file_url,
            "file_type": file_type,
            "file_size": file_size,
            "status": "uploaded",
            "message": f"{file_type.capitalize()} file uploaded successfully for merge operation",
        }

        print(f"[FILE UPLOAD] Upload completed: {response}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"[FILE UPLOAD ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task functions
async def process_manual_merge(
    merge_id: str, request: MergeManualRequest, user_id: str
):
    """Process the manual merge operation in the background"""
    try:
        from app.tasks.merge_tasks import (
            process_manual_merge as task_process_manual_merge,
        )

        print(f"Processing manual merge {merge_id} for user {user_id}")

        # Prepare merge data
        merge_data = {
            "input_sources": [source.dict() for source in request.input_sources],
            "quality_tier": request.quality_tier.value,
            "output_format": request.output_format.value,
            "ffmpeg_params": (
                request.ffmpeg_params.dict() if request.ffmpeg_params else None
            ),
            "merge_name": request.merge_name,
        }

        # Call the actual merge task
        task_process_manual_merge.delay(merge_id, user_id)

        # TODO: Store merge_data in database for the task to retrieve

    except Exception as e:
        print(f"Error processing manual merge {merge_id}: {str(e)}")
        # TODO: Update status to failed


async def process_merge_preview(
    preview_id: str, request: MergePreviewRequest, user_id: str
):
    """Process the merge preview in the background"""
    try:
        from app.tasks.merge_tasks import (
            process_merge_preview as task_process_merge_preview,
        )

        print(f"Processing merge preview {preview_id} for user {user_id}")

        # Prepare preview data
        preview_data = {
            "input_sources": [source.dict() for source in request.input_sources],
            "quality_tier": request.quality_tier.value,
            "preview_duration": request.preview_duration,
            "ffmpeg_params": (
                request.ffmpeg_params.dict() if request.ffmpeg_params else None
            ),
        }

        # Call the actual preview task
        task_process_merge_preview.delay(preview_id, user_id)

        # TODO: Store preview_data in database for the task to retrieve

    except Exception as e:
        print(f"Error processing merge preview {preview_id}: {str(e)}")
