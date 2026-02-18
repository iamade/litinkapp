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
from typing import Dict, Any, Optional, List, Tuple
from app.core.logging import get_logger

logger = get_logger()


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
