"""
FFmpeg Utility Functions for Video Post-Production

This module provides FFmpeg-based utilities for:
- Letterboxing: Adding black bars to achieve target aspect ratios
- Crossfade Transitions: Smooth transitions between video clips
- Video Scaling: Resize videos to target dimensions
- Color Correction: Basic color grading and filters

Usage:
    from app.core.services.ffmpeg_utils import (
        apply_letterbox,
        apply_crossfade_transition,
        concatenate_with_transitions,
        apply_fade_in_out,
    )
"""

import asyncio
import os
import subprocess
import tempfile
import uuid as uuid_lib
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse, urlunparse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger()


def _replace_url_origin(url: str, target_origin: Optional[str]) -> str:
    """Return url with scheme/netloc from target_origin, preserving path/query."""
    if not url or not target_origin:
        return url

    parsed_url = urlparse(url)
    parsed_target = urlparse(target_origin)
    if not parsed_url.scheme or not parsed_url.netloc or not parsed_target.scheme or not parsed_target.netloc:
        return url

    return urlunparse(parsed_url._replace(scheme=parsed_target.scheme, netloc=parsed_target.netloc))


def _normalize_minio_url_for_internal_download(url: Optional[str]) -> Optional[str]:
    """Use the internal MinIO endpoint for backend downloads of local public URLs."""
    if not url:
        return url

    parsed_url = urlparse(url)
    public_url = urlparse(getattr(settings, "MINIO_PUBLIC_URL", "") or "")
    endpoint_url = urlparse(getattr(settings, "MINIO_ENDPOINT", "") or "")

    if (
        parsed_url.scheme in {"http", "https"}
        and parsed_url.netloc
        and public_url.scheme in {"http", "https"}
        and public_url.netloc
        and endpoint_url.scheme in {"http", "https"}
        and endpoint_url.netloc
        and parsed_url.scheme == public_url.scheme
        and parsed_url.netloc == public_url.netloc
        and public_url.netloc != endpoint_url.netloc
    ):
        return _replace_url_origin(url, settings.MINIO_ENDPOINT)

    return url


async def extract_last_frame(
    video_url: str,
    user_id: Optional[str] = None,
    *,
    seek_offset_seconds: float = 0.1,
) -> Optional[str]:
    """Download a video, extract its last frame with ffmpeg, and upload it.

    Returns the uploaded JPEG URL, or ``None`` when extraction/upload fails. This
    utility is intentionally centralized so video generation tasks and API
    services use the same frame extraction behavior for Prompt 6 continuity.
    """
    import httpx
    from app.core.services.storage import get_storage_service

    video_path = None
    frame_path = None
    try:
        download_url = _normalize_minio_url_for_internal_download(video_url)
        logger.info("[LAST FRAME] Extracting last frame from %s", (video_url or "")[:80])
        if download_url != video_url:
            logger.info("[LAST FRAME] Using internal media URL for download")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(download_url)
            if response.status_code != 200:
                logger.warning("[LAST FRAME] Download failed with status %s", response.status_code)
                return None

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_file:
            video_file.write(response.content)
            video_path = video_file.name
        frame_path = video_path.replace(".mp4", "_last_frame.jpg")

        probe_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip()) if result.stdout.strip() else 0.0
        seek_time = max(0, duration - seek_offset_seconds)

        extract_cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(seek_time),
            "-i",
            video_path,
            "-vframes",
            "1",
            "-q:v",
            "2",
            frame_path,
        ]
        subprocess.run(extract_cmd, capture_output=True, check=True)

        if not os.path.exists(frame_path):
            logger.warning("[LAST FRAME] ffmpeg completed without frame output")
            return None

        storage_service = get_storage_service()
        frame_filename = f"frames/{user_id or 'system'}/last_frame_{uuid_lib.uuid4().hex[:8]}.jpg"
        return await storage_service.upload(
            frame_path,
            file_path=frame_filename,
            content_type="image/jpeg",
        )
    except Exception as exc:
        logger.warning("[LAST FRAME] Extraction failed: %s", exc)
        return None
    finally:
        for path in (video_path, frame_path):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass


# ============================================================================
# LETTERBOXING FUNCTIONS
# ============================================================================


def apply_letterbox(
    input_path: str,
    output_path: str,
    target_aspect_ratio: str = "16:9",
    background_color: str = "black",
) -> Dict[str, Any]:
    """
    Apply letterboxing to a video to achieve target aspect ratio.

    Letterboxing adds black bars (or custom color bars) to the top/bottom
    or left/right of the video to achieve the desired aspect ratio without
    cropping or distorting the original content.

    Args:
        input_path: Path to input video file
        output_path: Path for output video file
        target_aspect_ratio: Target aspect ratio (e.g., "16:9", "21:9", "4:3")
        background_color: Color for letterbox bars (default: "black")

    Returns:
        Dict with status, output_path, and metadata

    FFmpeg filter explanation:
        pad=width:height:(ow-iw)/2:(oh-ih)/2:color
        - width: Target width
        - height: Target height
        - (ow-iw)/2: Horizontal offset to center the video
        - (oh-ih)/2: Vertical offset to center the video
        - color: Background/letterbox color
    """
    try:
        logger.info(
            f"[LETTERBOX] Applying letterbox to {input_path}, target: {target_aspect_ratio}"
        )

        # Parse target aspect ratio
        target_w, target_h = _parse_aspect_ratio(target_aspect_ratio)

        # Get input video dimensions
        input_width, input_height = _get_video_dimensions(input_path)
        if not input_width or not input_height:
            raise Exception("Could not determine input video dimensions")

        # Calculate output dimensions
        output_width, output_height = _calculate_letterbox_dimensions(
            input_width, input_height, target_w, target_h
        )

        # Build FFmpeg command with pad filter
        # The pad filter centers the video in the new frame
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i",
            input_path,
            "-vf",
            f"pad={output_width}:{output_height}:(ow-iw)/2:(oh-ih)/2:{background_color}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-c:a",
            "copy",  # Copy audio without re-encoding
            output_path,
        ]

        logger.info(f"[LETTERBOX] Running FFmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"FFmpeg letterboxing failed: {result.stderr}")

        logger.info(
            f"[LETTERBOX] Successfully applied letterbox: {input_width}x{input_height} -> {output_width}x{output_height}"
        )

        return {
            "status": "success",
            "output_path": output_path,
            "original_dimensions": f"{input_width}x{input_height}",
            "output_dimensions": f"{output_width}x{output_height}",
            "target_aspect_ratio": target_aspect_ratio,
        }

    except Exception as e:
        logger.error(f"[LETTERBOX ERROR] {str(e)}")
        return {
            "status": "error",
            "error": str(e),
        }


def apply_letterbox_to_dimensions(
    input_path: str,
    output_path: str,
    target_width: int,
    target_height: int,
    background_color: str = "black",
) -> Dict[str, Any]:
    """
    Apply letterboxing to specific pixel dimensions.

    Args:
        input_path: Path to input video file
        output_path: Path for output video file
        target_width: Target width in pixels
        target_height: Target height in pixels
        background_color: Color for letterbox bars

    Returns:
        Dict with status and metadata
    """
    try:
        logger.info(
            f"[LETTERBOX] Applying letterbox to {target_width}x{target_height}"
        )

        # Get input video dimensions
        input_width, input_height = _get_video_dimensions(input_path)
        if not input_width or not input_height:
            raise Exception("Could not determine input video dimensions")

        # Calculate scale to fit within target while maintaining aspect ratio
        scale_w = target_width / input_width
        scale_h = target_height / input_height
        scale = min(scale_w, scale_h)

        new_width = int(input_width * scale)
        new_height = int(input_height * scale)

        # Ensure even dimensions (required by some codecs)
        new_width = new_width if new_width % 2 == 0 else new_width - 1
        new_height = new_height if new_height % 2 == 0 else new_height - 1

        # Build FFmpeg command: scale then pad
        filter_chain = f"scale={new_width}:{new_height},pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:{background_color}"

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vf",
            filter_chain,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-c:a",
            "copy",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"FFmpeg letterboxing failed: {result.stderr}")

        return {
            "status": "success",
            "output_path": output_path,
            "original_dimensions": f"{input_width}x{input_height}",
            "output_dimensions": f"{target_width}x{target_height}",
        }

    except Exception as e:
        logger.error(f"[LETTERBOX ERROR] {str(e)}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# CROSSFADE TRANSITION FUNCTIONS
# ============================================================================


def apply_crossfade_transition(
    video_a_path: str,
    video_b_path: str,
    output_path: str,
    transition_duration: float = 1.0,
) -> Dict[str, Any]:
    """
    Apply a crossfade transition between two video clips.

    Creates a smooth dissolve/crossfade effect from video_a to video_b.

    Args:
        video_a_path: Path to first video (outgoing)
        video_b_path: Path to second video (incoming)
        output_path: Path for output video file
        transition_duration: Duration of crossfade in seconds (default: 1.0)

    Returns:
        Dict with status, output_path, and metadata

    FFmpeg filter explanation:
        xfade filter creates transitions between two streams:
        - transition=fade: Use crossfade/dissolve effect
        - duration: Length of transition in seconds
        - offset: When to start the transition (at end of first video minus duration)
    """
    try:
        logger.info(
            f"[CROSSFADE] Creating {transition_duration}s crossfade transition"
        )

        # Get duration of first video to calculate offset
        video_a_duration = _get_video_duration(video_a_path)
        if not video_a_duration:
            raise Exception("Could not determine duration of first video")

        # Calculate transition offset (start fade near end of video_a)
        offset = max(0, video_a_duration - transition_duration)

        # Build FFmpeg command with xfade filter
        # xfade filter: [0:v][1:v]xfade=transition=fade:duration=1:offset=4[v]
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_a_path,
            "-i",
            video_b_path,
            "-filter_complex",
            f"[0:v][1:v]xfade=transition=fade:duration={transition_duration}:offset={offset}[v];"
            f"[0:a][1:a]acrossfade=d={transition_duration}[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            output_path,
        ]

        logger.info(f"[CROSSFADE] Running FFmpeg with xfade filter")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"FFmpeg crossfade failed: {result.stderr}")

        # Get output duration
        output_duration = _get_video_duration(output_path)

        logger.info(
            f"[CROSSFADE] Successfully created crossfade transition, output duration: {output_duration}s"
        )

        return {
            "status": "success",
            "output_path": output_path,
            "transition_duration": transition_duration,
            "output_duration": output_duration,
        }

    except Exception as e:
        logger.error(f"[CROSSFADE ERROR] {str(e)}")
        return {"status": "error", "error": str(e)}


def concatenate_with_transitions(
    video_paths: List[str],
    output_path: str,
    transition_type: str = "fade",
    transition_duration: float = 0.5,
) -> Dict[str, Any]:
    """
    Concatenate multiple videos with crossfade transitions between each.

    Args:
        video_paths: List of paths to video files in order
        output_path: Path for output video file
        transition_type: Type of transition (fade, wipeleft, wiperight, slideup, etc.)
        transition_duration: Duration of each transition in seconds

    Returns:
        Dict with status, output_path, and metadata

    Supported transition types (FFmpeg xfade):
        - fade: Crossfade/dissolve
        - wipeleft, wiperight, wipeup, wipedown: Wipe transitions
        - slideleft, slideright, slideup, slidedown: Slide transitions
        - circlecrop: Circle crop transition
        - rectcrop: Rectangle crop transition
        - distance: Distance-based transition
        - fadeblack, fadewhite: Fade through black/white
    """
    try:
        if len(video_paths) < 2:
            # Single video, just copy it
            if len(video_paths) == 1:
                subprocess.run(["cp", video_paths[0], output_path], check=True)
                return {
                    "status": "success",
                    "output_path": output_path,
                    "transitions_added": 0,
                }
            else:
                raise Exception("No videos provided for concatenation")

        logger.info(
            f"[CONCAT TRANSITIONS] Concatenating {len(video_paths)} videos with {transition_type} transitions"
        )

        # For complex multi-video transitions, we need to chain xfade filters
        # Build the filter complex string
        filter_parts = []
        audio_filter_parts = []

        # Get durations for offset calculations
        durations = []
        for vpath in video_paths:
            dur = _get_video_duration(vpath)
            if not dur:
                raise Exception(f"Could not get duration for {vpath}")
            durations.append(dur)

        # Build input specifications
        cmd = ["ffmpeg", "-y"]
        for vpath in video_paths:
            cmd.extend(["-i", vpath])

        # Build filter complex for chained xfade
        # For n videos, we need n-1 xfade operations
        cumulative_offset = 0
        for i in range(len(video_paths) - 1):
            # Calculate offset for this transition
            if i == 0:
                offset = durations[0] - transition_duration
                video_input = f"[{i}:v]"
            else:
                offset = cumulative_offset + durations[i] - transition_duration
                video_input = f"[v{i}]"

            next_video = f"[{i + 1}:v]"
            output_label = f"[v{i + 1}]" if i < len(video_paths) - 2 else "[outv]"

            filter_parts.append(
                f"{video_input}{next_video}xfade=transition={transition_type}:duration={transition_duration}:offset={offset}{output_label}"
            )

            cumulative_offset = offset

            # Audio crossfade
            if i == 0:
                audio_input = f"[{i}:a]"
            else:
                audio_input = f"[a{i}]"
            next_audio = f"[{i + 1}:a]"
            audio_output = f"[a{i + 1}]" if i < len(video_paths) - 2 else "[outa]"
            audio_filter_parts.append(
                f"{audio_input}{next_audio}acrossfade=d={transition_duration}{audio_output}"
            )

        filter_complex = ";".join(filter_parts + audio_filter_parts)

        cmd.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[outv]",
                "-map",
                "[outa]",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                output_path,
            ]
        )

        logger.info(f"[CONCAT TRANSITIONS] Running FFmpeg with chained xfade")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"FFmpeg concatenation failed: {result.stderr}")

        output_duration = _get_video_duration(output_path)
        transitions_added = len(video_paths) - 1

        logger.info(
            f"[CONCAT TRANSITIONS] Successfully concatenated with {transitions_added} transitions"
        )

        return {
            "status": "success",
            "output_path": output_path,
            "transitions_added": transitions_added,
            "transition_type": transition_type,
            "output_duration": output_duration,
        }

    except Exception as e:
        logger.error(f"[CONCAT TRANSITIONS ERROR] {str(e)}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# FADE IN/OUT FUNCTIONS
# ============================================================================


def apply_fade_in_out(
    input_path: str,
    output_path: str,
    fade_in_duration: float = 0.5,
    fade_out_duration: float = 0.5,
) -> Dict[str, Any]:
    """
    Apply fade in and fade out effects to a video.

    Args:
        input_path: Path to input video file
        output_path: Path for output video file
        fade_in_duration: Duration of fade in effect in seconds
        fade_out_duration: Duration of fade out effect in seconds

    Returns:
        Dict with status and metadata
    """
    try:
        logger.info(
            f"[FADE] Applying fade in ({fade_in_duration}s) and fade out ({fade_out_duration}s)"
        )

        # Get video duration for fade out start time
        video_duration = _get_video_duration(input_path)
        if not video_duration:
            raise Exception("Could not determine video duration")

        fade_out_start = max(0, video_duration - fade_out_duration)

        # Build filter string
        video_filter = f"fade=t=in:st=0:d={fade_in_duration},fade=t=out:st={fade_out_start}:d={fade_out_duration}"
        audio_filter = f"afade=t=in:st=0:d={fade_in_duration},afade=t=out:st={fade_out_start}:d={fade_out_duration}"

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vf",
            video_filter,
            "-af",
            audio_filter,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"FFmpeg fade failed: {result.stderr}")

        return {
            "status": "success",
            "output_path": output_path,
            "fade_in_duration": fade_in_duration,
            "fade_out_duration": fade_out_duration,
        }

    except Exception as e:
        logger.error(f"[FADE ERROR] {str(e)}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _parse_aspect_ratio(aspect_ratio: str) -> Tuple[int, int]:
    """Parse aspect ratio string (e.g., '16:9') into width and height components."""
    try:
        parts = aspect_ratio.split(":")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        logger.warning(f"Invalid aspect ratio '{aspect_ratio}', defaulting to 16:9")
        return 16, 9


def _get_video_dimensions(video_path: str) -> Tuple[Optional[int], Optional[int]]:
    """Get video dimensions using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            if len(parts) >= 2:
                return int(parts[0]), int(parts[1])
    except Exception as e:
        logger.error(f"[FFPROBE] Error getting dimensions: {e}")
    return None, None


def _get_video_duration(video_path: str) -> Optional[float]:
    """Get video duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"[FFPROBE] Error getting duration: {e}")
    return None


def _get_audio_duration(audio_path: str) -> Optional[float]:
    """Get audio duration in seconds using ffprobe (KAN-166).

    Works for local files and URLs. Returns None if probing fails.
    """
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            val = float(result.stdout.strip())
            if val > 0:
                return val
    except Exception as e:
        logger.error(f"[FFPROBE] Error getting audio duration: {e}")
    return None


async def probe_audio_duration_from_url(audio_url: str) -> Optional[float]:
    """Probe audio file duration from a URL using ffprobe (KAN-166).

    Downloads to a temp file first if the URL is remote, since ffprobe
    may not support all URL schemes directly. Returns None on failure.
    """
    import tempfile
    import requests as _requests

    if not audio_url:
        return None

    # Try direct probing first (ffprobe supports many URLs natively)
    duration = _get_audio_duration(audio_url)
    if duration is not None:
        return duration

    # Fallback: download to temp file and probe
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        resp = _requests.get(audio_url, timeout=15, stream=True)
        resp.raise_for_status()
        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        duration = _get_audio_duration(tmp_path)
        return duration
    except Exception as e:
        logger.error(f"[FFPROBE] Error probing audio duration from URL: {e}")
        return None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _calculate_letterbox_dimensions(
    input_width: int,
    input_height: int,
    target_aspect_w: int,
    target_aspect_h: int,
) -> Tuple[int, int]:
    """
    Calculate output dimensions for letterboxing.

    Returns dimensions that:
    - Have the target aspect ratio
    - Are at least as large as the input dimensions
    - Have even values (required by some codecs)
    """
    input_aspect = input_width / input_height
    target_aspect = target_aspect_w / target_aspect_h

    if target_aspect > input_aspect:
        # Target is wider - add horizontal padding
        output_height = input_height
        output_width = int(input_height * target_aspect)
    else:
        # Target is taller - add vertical padding
        output_width = input_width
        output_height = int(input_width / target_aspect)

    # Ensure even dimensions
    output_width = output_width if output_width % 2 == 0 else output_width + 1
    output_height = output_height if output_height % 2 == 0 else output_height + 1

    return output_width, output_height


# ============================================================================
# ASYNC WRAPPERS
# ============================================================================


async def async_apply_letterbox(
    input_path: str,
    output_path: str,
    target_aspect_ratio: str = "16:9",
    background_color: str = "black",
) -> Dict[str, Any]:
    """Async wrapper for apply_letterbox."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, apply_letterbox, input_path, output_path, target_aspect_ratio, background_color
    )


async def async_apply_crossfade_transition(
    video_a_path: str,
    video_b_path: str,
    output_path: str,
    transition_duration: float = 1.0,
) -> Dict[str, Any]:
    """Async wrapper for apply_crossfade_transition."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        apply_crossfade_transition,
        video_a_path,
        video_b_path,
        output_path,
        transition_duration,
    )


async def async_concatenate_with_transitions(
    video_paths: List[str],
    output_path: str,
    transition_type: str = "fade",
    transition_duration: float = 0.5,
) -> Dict[str, Any]:
    """Async wrapper for concatenate_with_transitions."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        concatenate_with_transitions,
        video_paths,
        output_path,
        transition_type,
        transition_duration,
    )


async def async_apply_fade_in_out(
    input_path: str,
    output_path: str,
    fade_in_duration: float = 0.5,
    fade_out_duration: float = 0.5,
) -> Dict[str, Any]:
    """Async wrapper for apply_fade_in_out."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        apply_fade_in_out,
        input_path,
        output_path,
        fade_in_duration,
        fade_out_duration,
    )
