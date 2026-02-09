from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from app.core.logging import get_logger

logger = get_logger()


class ModelTier(Enum):
    FREE = "free"
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class ModelConfig:
    primary: str
    fallback: str
    fallback2: Optional[str] = None
    fallback3: Optional[str] = (
        None  # Added for additional fallback (Veo 3 direct, Grok AI)
    )
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    cost_per_1k_input: Optional[float] = None
    cost_per_1k_output: Optional[float] = None


# Text & Script Generation Strategy (LMSYS Creative Writing Leaderboard-based)
# All models accessed via OpenRouter for reliable connectivity and fallback handling
SCRIPT_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="deepseek/deepseek-chat",  # DeepSeek-v3.2-thinking
        fallback="qwen/qwen-2.5-72b-instruct",  # Qwen (Efficient)
        fallback2="openai/chatgpt-4o-latest",  # ChatGPT-4o-latest
        max_tokens=4000,
        temperature=0.7,
        cost_per_1k_input=0.0,  # Free tier - no cost tracking
        cost_per_1k_output=0.0,
    ),
    ModelTier.BASIC: ModelConfig(
        primary="qwen/qwen-2.5-72b-instruct",  # Qwen (Replacing Grok-4.1)
        fallback="openai/chatgpt-4o-latest",  # ChatGPT-4o-latest
        fallback2="baidu/ernie-4.5-21b-a3b-thinking",  # Ernie-5.0
        max_tokens=4000,
        temperature=0.7,
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="google/gemini-2.5-pro",  # # Gemini-2.5-pro
        fallback="openai/gpt-4.5-preview",  # GPT-4.5-preview
        fallback2="anthropic/claude-opus-4",  # Claude-Opus-4.1
        max_tokens=8000,
        temperature=0.7,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="anthropic/claude-sonnet-4.5",  # Claude-Sonnet-4.5
        fallback="google/gemini-3-flash-preview",  # Gemini-3-flash (Thinking)
        fallback2="qwen/qwen3-coder",  # Qwen-Thinking
        max_tokens=8000,
        temperature=0.75,
        cost_per_1k_input=0.00150,
        cost_per_1k_output=0.00600,
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="google/gemini-3-flash-preview",  # Gemini-3-flash
        fallback="google/gemini-2.5-pro",  # Gemini-2.5-pro
        fallback2="openai/gpt-5",  # GPT-5.1
        max_tokens=16000,
        temperature=0.8,
        cost_per_1k_input=0.00250,
        cost_per_1k_output=0.01000,
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="google/gemini-3-pro-preview",  # Gemini-3-pro (#1 Creative)
        fallback="anthropic/claude-opus-4.5",  # Claude-Opus-4.5
        fallback2="openai/gpt-5.2-pro",  # GPT-5.1-high
        max_tokens=16000,
        temperature=0.8,
        cost_per_1k_input=0.00500,
        cost_per_1k_output=0.02000,
    ),
}


# Image Generation Strategy
# Leveraging top performing models with optimal quality-to-cost ratios
# ModelsLab used as primary gateway; Direct API for specific high-end models
IMAGE_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="seedream-t2i",  # Seedream (ModelsLab V7) Per image generation will cost $0.033
        fallback="seedream-4",  # Seedream-4 (ModelsLab V7) Per image generation will cost $0.033
        fallback2="nano-banana-pro",  # nano-banana-pro (ModelsLab V7) working Your request will cost $0.18 per image
    ),
    ModelTier.BASIC: ModelConfig(
        primary="seedream-4",  # Seedream-4 (ModelsLab V7) Per image generation will cost $0.033
        fallback="imagen-4",  # imagen-4 (ModelsLab API) Per image generation will cost 0.044$
        fallback2="nano-banana-pro",  # nano-banana-pro (ModelsLab V7) working Your request will cost $0.18 per image
        # fallback2="qwen-image-2512",  # Qwen-Image-2512 (Direct API)
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="imagen-4",  # imagen-4 (ModelsLab API) Per image generation will cost 0.044$
        fallback="nano-banana-t2i",  # nano-banana-t2i (ModelsLab V7) working Your request will cost $0.046
        fallback2="nano-banana-pro",  # nano-banana-pro (ModelsLab V7) working Your request will cost $0.18 per image
        # fallback2="nano-banana",  # Nano Banana / Gemini-2.5 (Direct API)
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="nano-banana-t2i",  # nano-banana-t2i (ModelsLab V7) working Your request will cost $0.046
        fallback="seedream-4.5",  # seedream-4.5 (ModelsLab V7) working Your request will cost $0.06
        fallback2="nano-banana-pro",  #  nano-banana-pro (ModelsLab V7) working Your request will cost $0.18 per image
        # fallback="nano-banana-pro",  # Nano Banana Pro / Gemini-3 (Direct API)
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="seedream-4.5",  # seedream-4.5 (ModelsLab V7) working Your request will cost $0.06
        fallback="imagen-4.0-ultra",  #  imagen-4.0-ultra (ModelsLab API) Per image generation will cost 0.072$
        fallback2="nano-banana-pro",  # nano-banana-pro (ModelsLab V7) working Your request will cost $0.18 per image
        #  fallback2="gpt-image-1.5",  # GPT-Image-1.5 (Direct API
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="nano-banana-pro",  # nano-banana-pro (ModelsLab V7) working Your request will cost $0.18 per image
        fallback="gpt-image-1.5",  # GPT-Image-1.5 (Direct API)
        fallback2="nano-banana",  # Nano Banana / Gemini-2.5 (Direct API)
        # fallback3="nano-banana-pro",  # Nano Banana Pro / Gemini-3 (Direct API)
    ),
}


# Image-to-Image (Single Reference) Generation Strategy
IMAGE_I2I_SINGLE_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="seedream-4.0-i2i",  # Seedream (ModelsLab) $0.033
        fallback="seededit-i2i",  # seededit (ModelsLab) $0.04
        fallback2="nano-banana",  # Nano Banana (ModelsLab) $0.0468
    ),
    ModelTier.BASIC: ModelConfig(
        primary="seededit-i2i",  # seededit (ModelsLab) $0.04
        fallback="nano-banana",  # Nano Banana (ModelsLab) $0.0468
        fallback2="seedream-4.5-i2i",
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="nano-banana",  # Nano Banana (ModelsLab) $0.0468
        fallback="seedream-4.0-i2i",
        fallback2="seedream-4.5-i2i",  # seedream-4.5 (ModelsLab) $0.06
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="nano-banana",  # Nano Banana (ModelsLab) $0.0468
        fallback2="seedream-4.5-i2i",
        fallback="seededit-i2i",  # seededit (ModelsLab) $0.04
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="seedream-4.5-i2i",  # seedream-4.5 (ModelsLab) $0.06
        fallback="nano-banana",  # Nano Banana (ModelsLab) $0.0468
        fallback2="seededit-i2i",
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="seedream-4.5-i2i",  # seedream-4.5 (ModelsLab) $0.06
        fallback="nano-banana",  # Nano Banana (ModelsLab) $0.0468
        fallback2="seededit-i2i",
    ),
}


# Image-to-Image (Multi Reference) Generation Strategy
IMAGE_I2I_MULTI_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="seedream-4.0-i2i",  # Seedream (ModelsLab) $0.033
        fallback="nano-banana",  # Nano Banana (ModelsLab) $0.0468 (Limit 2)
        fallback2="seedream-4.5-i2i",
    ),
    ModelTier.BASIC: ModelConfig(
        primary="nano-banana",  # Seedream (ModelsLab) $0.033
        fallback="seedream-4.5-i2i",  # Nano Banana (ModelsLab) $0.0468 (Limit 2)
        fallback2="seedream-4.0-i2i",
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="seedream-4.5-i2i",  # Nano Banana (ModelsLab) $0.0468
        fallback="seedream-4.0-i2i",  # Seedream (ModelsLab) $0.033
        fallback2="nano-banana",
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="nano-banana",  # Nano Banana (ModelsLab) $0.0468
        fallback="seedream-4.0-i2i",  # Seedream (ModelsLab) $0.033
        fallback2="seedream-4.5-i2i",
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="seedream-4.5-i2i",  # seedream-4.5 (ModelsLab) $0.06
        fallback="nano-banana",  # Nano Banana (ModelsLab) $0.0468
        fallback2="seedream-4.0-i2i",
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="seedream-4.5-i2i",  # seedream-4.5 (ModelsLab) $0.06
        fallback="nano-banana",  # Nano Banana (ModelsLab) $0.0468
        fallback2="seedream-4.0-i2i",
    ),
}


# Video Generation Strategy
# UPDATED: All tiers now use ONLY models that accept audio input for lip-sync capability
# Supported models: wan2.5-i2v, wan2.6-i2v, omni-human, omni-human-1.5
# These models accept: image + audio + prompt → video with lip-sync
VIDEO_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="wan2.5-i2v",  # Wan2.5-I2V (ModelsLab) 480p - basic lip-sync capable
        fallback="wan2.6-i2v",  # Wan2.6-I2V (ModelsLab) - upgraded fallback
        fallback2=None,
        fallback3=None,
    ),
    ModelTier.BASIC: ModelConfig(
        primary="wan2.6-i2v",  # Wan2.6-I2V (ModelsLab) 720p - better audio sync
        fallback="wan2.5-i2v",  # Wan2.5-I2V (ModelsLab) 480p fallback
        fallback2=None,
        fallback3=None,
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="omni-human-1.5",  # Omni-Human-1.5 (ModelsLab) - talking head specialist
        fallback="wan2.6-i2v",  # Wan2.6-I2V fallback
        fallback2="wan2.5-i2v",  # Wan2.5-I2V fallback
        fallback3=None,
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="omni-human",  # Omni-Human (ModelsLab) - high quality talking head
        fallback="omni-human-1.5",  # Omni-Human-1.5 fallback
        fallback2="wan2.6-i2v",  # Wan2.6-I2V fallback
        fallback3=None,
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="omni-human",  # Omni-Human (ModelsLab) - professional quality
        fallback="omni-human-1.5",  # Omni-Human-1.5 fallback
        fallback2="wan2.6-i2v",  # Wan2.6-I2V fallback
        fallback3=None,
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="omni-human-1.5",  # Omni-Human-1.5 - best for enterprise (stable)
        fallback="omni-human",  # Omni-Human fallback
        fallback2="wan2.6-i2v",  # Wan2.6-I2V fallback
        fallback3=None,
    ),
}

# ============================================================================
# PREVIOUS VIDEO_MODEL_CONFIG (Commented out for reference)
# This config included models that don't accept audio (seedance, veo-3, grok-video)
# ============================================================================
# VIDEO_MODEL_CONFIG_PREVIOUS: Dict[ModelTier, ModelConfig] = {
#     ModelTier.FREE: ModelConfig(
#         primary="seedance-1-5-pro",  # Seedance-v1.5-Pro (ModelsLab) $0.044/s 12v cant pass or generate audio
#         fallback="wan2.6-i2v",  # Wan2.5-I2V (ModelsLab) 480p $0.05/s can record and pass audio
#         fallback2="kling-2.5-turbo", # can pass image and generate video but no audio
#         fallback3=None,
#     ),
#     ModelTier.BASIC: ModelConfig(
#         primary="wan2.6-i2v",  # Wan2.5-I2V (ModelsLab) 720p $0.10/s
#         fallback="seedance-1-5-pro",  # Seedance-v1.5-Pro (ModelsLab)
#         fallback2="wan2.5-i2v",
#         fallback3=None,
#     ),
#     ModelTier.STANDARD: ModelConfig(
#         primary="omni-human-1.5",  # Omni-Human-1.5 (ModelsLab) $0.14/s
#         fallback="wan2.6-i2v",
#         fallback2="seedance-1-5-pro",
#         fallback3="veo-3-direct",  # Veo 3 Direct API (no audio input needed)
#     ),
#     ModelTier.PREMIUM: ModelConfig(
#         primary="veo-3-direct",  # Veo 3 Direct API (Google AI Studio)
#         fallback="omni-human",
#         fallback2="omni-human-1.5",
#         fallback3="grok-video",
#     ),
#     ModelTier.PROFESSIONAL: ModelConfig(
#         primary="veo-3-direct",
#         fallback="veo-3.1-fast",
#         fallback2="omni-human",
#         fallback3="grok-video",
#     ),
#     ModelTier.ENTERPRISE: ModelConfig(
#         primary="veo-3-direct",  # Veo 3 Direct API (Google AI Studio) - highest quality
#         fallback="veo-3.1-fast",
#         fallback2="grok-video",
#         fallback3="omni-human",
#     ),
# }


AUDIO_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="eleven_turbo_v2",
        fallback="eleven_multilingual_v2",
        fallback2="eleven_english_v1",
    ),
    ModelTier.BASIC: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="eleven_turbo_v2",
        fallback2="eleven_english_v1",
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="elevenlabs/eleven_multilingual_v2",  # Direct ElevenLabs Fallback
        fallback2="eleven_english_v1",
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="elevenlabs/eleven_multilingual_v2",  # Direct ElevenLabs Fallback
        fallback2="eleven_english_v1",
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="elevenlabs/eleven_multilingual_v2",  # Direct ElevenLabs Fallback
        fallback2=None,
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="elevenlabs/eleven_multilingual_v2",  # Direct ElevenLabs Fallback
        fallback2=None,
    ),
}


# Image Upscaling Strategy (ModelsLab V6 API)
# Tier-based model selection for super resolution
# Higher tiers get higher quality upscaling with fallback options
UPSCALE_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="RealESRGAN_x2plus",  # 2x upscaling - basic
        fallback="realesr-general-x4v3",  # 4x general fallback
        fallback2=None,
    ),
    ModelTier.BASIC: ModelConfig(
        primary="realesr-general-x4v3",  # 4x general upscaling
        fallback="RealESRGAN_x4plus",  # 4x fallback
        fallback2="RealESRGAN_x2plus",  # 2x fallback
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="RealESRGAN_x4plus",  # 4x high quality
        fallback="realesr-general-x4v3",  # 4x general fallback
        fallback2="RealESRGAN_x2plus",  # 2x fallback
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="RealESRGAN_x4plus",  # 4x high quality
        fallback="ultra_resolution",  # 4K+ fallback
        fallback2="realesr-general-x4v3",  # 4x general fallback
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="ultra_resolution",  # 4K+ upscaling - best quality
        fallback="RealESRGAN_x4plus",  # 4x fallback
        fallback2="realesr-general-x4v3",  # 4x general fallback
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="ultra_resolution",  # 4K+ upscaling - best quality
        fallback="RealESRGAN_x4plus",  # 4x fallback
        fallback2="realesr-general-x4v3",  # 4x general fallback
    ),
}


def get_model_config(service_type: str, tier: str) -> Optional[ModelConfig]:
    try:
        model_tier = ModelTier(tier.lower())

        config_map = {
            "script": SCRIPT_MODEL_CONFIG,
            "image": IMAGE_MODEL_CONFIG,
            "video": VIDEO_MODEL_CONFIG,
            "audio": AUDIO_MODEL_CONFIG,
            "upscale": UPSCALE_MODEL_CONFIG,
        }

        config = config_map.get(service_type.lower())
        if not config:
            logger.error(f"Unknown service type: {service_type}")
            return None

        return config.get(model_tier)

    except (ValueError, KeyError) as e:
        logger.error(f"Error getting model config for {service_type}/{tier}: {e}")
        return None


def validate_model_configs():
    logger.info("Validating model configurations...")

    for tier in ModelTier:
        script_config = SCRIPT_MODEL_CONFIG.get(tier)
        image_config = IMAGE_MODEL_CONFIG.get(tier)
        video_config = VIDEO_MODEL_CONFIG.get(tier)
        audio_config = AUDIO_MODEL_CONFIG.get(tier)

        if not script_config:
            logger.error(f"Missing script config for tier: {tier.value}")
        if not image_config:
            logger.error(f"Missing image config for tier: {tier.value}")
        if not IMAGE_I2I_SINGLE_MODEL_CONFIG.get(tier):
            logger.error(f"Missing i2i single image config for tier: {tier.value}")
        if not IMAGE_I2I_MULTI_MODEL_CONFIG.get(tier):
            logger.error(f"Missing i2i multi image config for tier: {tier.value}")
        if not video_config:
            logger.error(f"Missing video config for tier: {tier.value}")
        if not audio_config:
            logger.error(f"Missing audio config for tier: {tier.value}")

    logger.info("Model configuration validation complete")


validate_model_configs()
