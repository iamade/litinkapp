"""
Watermark service for embedded LitInkAI branding.
Uses backend/static/assets/watermark.png and burns watermark directly into media.
"""

import math
import os
import subprocess
import tempfile
import uuid
from typing import Optional, Tuple

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.subscriptions.models import SubscriptionStatus, UserSubscription


WATERMARK_ASSET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "static",
    "assets",
    "watermark.png",
)


def _assert_source_is_image_content_type(source_url: str, content_type_header: Optional[str]) -> None:
    actual_content_type = (content_type_header or '').split(';', 1)[0].strip().lower()
    if not actual_content_type:
        return
    if not actual_content_type.startswith('image/'):
        raise ValueError(
            f"Invalid source Content-Type for image persistence ({source_url}): {actual_content_type}"
        )


def _probe_video_dimensions(media_path: str) -> Optional[Tuple[int, int]]:
    """Return width/height of first video stream using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=s=x:p=0",
        media_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        print(f"[WATERMARK] ffprobe failed for {media_path}: {result.stderr}")
        return None

    try:
        width_str, height_str = result.stdout.strip().split("x", 1)
        return int(width_str), int(height_str)
    except Exception as exc:
        print(f"[WATERMARK] Failed parsing dimensions '{result.stdout.strip()}': {exc}")
        return None


def _embedded_overlay_filter(width: int, height: int) -> str:
    """
    Build a subtle bottom-right corner watermark overlay.
    Single placement, low opacity — noticeable but not intrusive.
    """
    # Scale watermark to ~15% of image width, min 80px for readability
    scaled_w = max(80, int(width * 0.15))
    # Margin from edge: ~2% of image dimensions
    margin_x = max(8, int(width * 0.02))
    margin_y = max(8, int(height * 0.02))
    return (
        f"[1:v]format=rgba,colorchannelmixer=aa=0.18,"
        f"scale={scaled_w}:-1[wm];"
        f"[0:v][wm]overlay=W-w-{margin_x}:H-h-{margin_y}[outv]"
    )


async def check_has_watermark(user_id: str, session: AsyncSession) -> bool:
    """Check if the user's subscription tier requires a watermark."""
    try:
        stmt = select(UserSubscription).where(
            UserSubscription.user_id == uuid.UUID(user_id),
            UserSubscription.status == SubscriptionStatus.ACTIVE,
        )
        result = await session.exec(stmt)
        subscription = result.first()
        if not subscription:
            return True
        return subscription.has_watermark
    except Exception as e:
        print(f"[WATERMARK] Error checking watermark status: {e}")
        return True


def apply_watermark_sync(input_path: str, output_path: str) -> bool:
    """
    Burn embedded watermark into video output using the real watermark asset.
    """
    if not os.path.exists(WATERMARK_ASSET_PATH):
        print(f"[WATERMARK] Watermark asset not found at {WATERMARK_ASSET_PATH}")
        return False

    dimensions = _probe_video_dimensions(input_path)
    if not dimensions:
        return False
    width, height = dimensions
    filter_complex = _embedded_overlay_filter(width, height)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-i",
        WATERMARK_ASSET_PATH,
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        output_path,
    ]

    print("[WATERMARK] Applying embedded watermark to video")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WATERMARK] Failed to apply video watermark: {result.stderr}")
        return False

    print("[WATERMARK] Video watermark applied successfully")
    return True


def apply_image_watermark_sync(input_path: str, output_path: str) -> bool:
    """Burn embedded watermark into image output using ffmpeg."""
    if not os.path.exists(WATERMARK_ASSET_PATH):
        print(f"[WATERMARK] Watermark asset not found at {WATERMARK_ASSET_PATH}")
        return False

    dimensions = _probe_video_dimensions(input_path)
    if not dimensions:
        return False
    width, height = dimensions
    filter_complex = _embedded_overlay_filter(width, height)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-i",
        WATERMARK_ASSET_PATH,
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-frames:v",
        "1",
        output_path,
    ]

    print("[WATERMARK] Applying embedded watermark to image")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WATERMARK] Failed to apply image watermark: {result.stderr}")
        return False

    print("[WATERMARK] Image watermark applied successfully")
    return True


async def persist_image_with_embedded_watermark(
    source_url: str,
    dest_path: str,
    storage,
    content_type: str = "image/png",
    timeout_seconds: int = 120,
) -> str:
    """
    Download image, embed watermark asset into pixels, and upload to storage.
    Raises on failure to avoid silently leaking clean assets.
    """
    if not os.path.exists(WATERMARK_ASSET_PATH):
        raise RuntimeError(f"Watermark asset missing at {WATERMARK_ASSET_PATH}")

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "source_image")
        output_path = os.path.join(temp_dir, "watermarked.png")

        async with httpx.AsyncClient(
            timeout=float(timeout_seconds), follow_redirects=True
        ) as client:
            async with client.stream("GET", source_url) as response:
                response.raise_for_status()
                _assert_source_is_image_content_type(
                    source_url,
                    response.headers.get("content-type"),
                )
                with open(input_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

        if not apply_image_watermark_sync(input_path, output_path):
            raise RuntimeError("Embedded image watermark processing failed")

        with open(output_path, "rb") as f:
            return await storage.upload_stream(f, dest_path, content_type=content_type)


async def persist_clean_image(
    source_url: str,
    dest_path: str,
    storage,
    content_type: str = "image/png",
    timeout_seconds: int = 120,
) -> str:
    """Download image and upload to storage without watermark (clean copy)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "source_image")

        async with httpx.AsyncClient(
            timeout=float(timeout_seconds), follow_redirects=True
        ) as client:
            async with client.stream("GET", source_url) as response:
                response.raise_for_status()
                _assert_source_is_image_content_type(
                    source_url,
                    response.headers.get("content-type"),
                )
                with open(input_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

        with open(input_path, "rb") as f:
            return await storage.upload_stream(f, dest_path, content_type=content_type)


async def persist_image_with_both_versions(
    source_url: str,
    watermarked_dest_path: str,
    clean_dest_path: str,
    storage,
    content_type: str = "image/png",
    timeout_seconds: int = 120,
) -> Tuple[str, str]:
    """
    Download image, create watermarked and clean versions, upload both.
    Returns (watermarked_url, clean_url).
    Single download, two uploads.
    """
    if not os.path.exists(WATERMARK_ASSET_PATH):
        raise RuntimeError(f"Watermark asset missing at {WATERMARK_ASSET_PATH}")

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "source_image")
        output_path = os.path.join(temp_dir, "watermarked.png")

        async with httpx.AsyncClient(
            timeout=float(timeout_seconds), follow_redirects=True
        ) as client:
            async with client.stream("GET", source_url) as response:
                response.raise_for_status()
                _assert_source_is_image_content_type(
                    source_url,
                    response.headers.get("content-type"),
                )
                with open(input_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

        # Upload clean version first
        with open(input_path, "rb") as f:
            clean_url = await storage.upload_stream(
                f, clean_dest_path, content_type=content_type
            )

        # Apply watermark and upload
        if not apply_image_watermark_sync(input_path, output_path):
            raise RuntimeError("Embedded image watermark processing failed")

        with open(output_path, "rb") as f:
            watermarked_url = await storage.upload_stream(
                f, watermarked_dest_path, content_type=content_type
            )

        return watermarked_url, clean_url


async def apply_watermark(
    input_path: str,
    output_path: str,
    user_id: str,
    session: AsyncSession,
) -> str:
    """
    Check if the user requires watermark and apply it.
    Returns output_path on success, input_path when watermark is disabled by policy.
    """
    has_watermark = await check_has_watermark(user_id, session)
    if not has_watermark:
        print(f"[WATERMARK] User {user_id} requested clean asset")
        return input_path

    success = apply_watermark_sync(input_path, output_path)
    if success:
        return output_path

    # Keep compatibility with existing callers.
    print("[WATERMARK] Falling back to unwatermarked video")
    return input_path
