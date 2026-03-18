"""
Credit cost constants for AI operations.
"""
from enum import Enum

# Credit costs per operation unit
IMAGE_GEN = 1           # per image generated
AUDIO_PER_SECOND = 1    # per second of audio
VIDEO_PER_SECOND = 5    # per second of video
SCRIPT_GEN = 2          # per script generation
IMAGE_UPSCALE = 1       # per image upscale


class OperationType(str, Enum):
    IMAGE_GEN = "image_gen"
    AUDIO_GEN = "audio_gen"
    VIDEO_GEN = "video_gen"
    SCRIPT_GEN = "script_gen"
    IMAGE_UPSCALE = "image_upscale"
    TEXT_GEN = "text_gen"
    VOICE_GEN = "voice_gen"
    EMOTIONAL_MAP = "emotional_map"
    EXPAND_SCRIPT = "expand_script"
    IMAGE_EXPAND = "image_expand"
