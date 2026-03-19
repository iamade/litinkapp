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
TEXT_GEN = 1            # per text generation
VOICE_GEN = 1           # per voice generation
EMOTIONAL_MAP = 2       # per emotional map generation
EXPAND_SCRIPT = 2       # per script expansion
IMAGE_EXPAND = 1        # per image expand
PLOT_GEN = 2            # per plot generation
CHARACTER_GEN = 1       # per character generation
SOUND_EFFECT_GEN = 1    # per sound effect
AUDIO_NARRATION = 1     # per narration generation
SCREENPLAY_GEN = 2      # per screenplay generation
VIDEO_AVATAR_GEN = 5    # per avatar video (expensive)
SCENE_IMAGE_GEN = 1     # per scene image
CHARACTER_IMAGE_GEN = 1 # per character image
ENHANCED_SPEECH = 1     # per enhanced speech


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
    PLOT_GEN = "plot_gen"
    CHARACTER_GEN = "character_gen"
    SOUND_EFFECT_GEN = "sound_effect_gen"
    AUDIO_NARRATION = "audio_narration"
    SCREENPLAY_GEN = "screenplay_gen"
    VIDEO_AVATAR_GEN = "video_avatar_gen"
    SCENE_IMAGE_GEN = "scene_image_gen"
    CHARACTER_IMAGE_GEN = "character_image_gen"
    ENHANCED_SPEECH = "enhanced_speech"
