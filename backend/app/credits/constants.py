"""
Credit cost constants for AI operations.

KAN-309-313: 50% margin alignment — all credit costs are set to maintain
at least 50% margin over estimated provider API costs. Audit these values
quarterly against current provider pricing.

Margin formula: credit_cost >= provider_cost * 2.0 (50% margin)
"""
from enum import Enum

# Credit costs per operation unit
# KAN-309-313: Verified 50% margin alignment (2026-07-06)
# Image gen: ~$0.01-0.05 provider cost → 1 credit (50%+ margin at $0.01/credit)
IMAGE_GEN = 1           # per image generated
# Audio: ~$0.002-0.01/sec provider cost → 1 credit/sec (50%+ margin)
AUDIO_PER_SECOND = 1    # per second of audio
# Video: ~$0.02-0.10/sec provider cost → 5 credits/sec (50%+ margin)
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
CHAPTER_GEN = 2         # per chapter generation
TRAILER_ANALYZE = 5     # per trailer scene analysis (LLM-heavy)
TRAILER_VIDEO_PER_SECOND = 8  # per second of trailer video (KAN-150)

# Monthly credit grants per subscription tier (KAN-314 — synced with Stripe pricing metadata)
# NOTE: Tier names follow Stripe product IDs; SubscriptionTier enum mapping:
#   FREE -> SubscriptionTier.FREE
#   BASIC -> SubscriptionTier.BASIC
#   STANDARD -> SubscriptionTier.STANDARD
#   PREMIUM -> SubscriptionTier.PREMIUM
#   PRO -> SubscriptionTier.PROFESSIONAL
TIER_CREDIT_GRANTS = {
    "FREE": 300,
    "BASIC": 1500,
    "STANDARD": 4800,
    "PREMIUM": 13100,
    "PRO": 33100,
}

# Convenience: SubscriptionTier enum key → credit grant amount
# (KAN-314: supersedes KAN-309 — constants must match Stripe metadata exactly)
TIER_CREDIT_GRANTS_BY_ENUM = {
    "free": 300,        # FREE
    "basic": 1500,      # BASIC
    "standard": 4800,   # STANDARD
    "pro": 4800,        # Legacy Standard value until the backfill is complete
    "premium": 13100,   # PREMIUM
    "professional": 33100,  # PRO
}


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
    CHAPTER_GEN = "chapter_gen"
    TRAILER_ANALYZE = "trailer_analyze"
    TRAILER_VIDEO_GEN = "trailer_video_gen"
