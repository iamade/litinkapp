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
        primary="qwen/qwen3-coder",  # Qwen-Thinking (Replacing Grok-Thinking)
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
        primary="hunyuan-image-3.0",  # Hunyuan-Image-3.0 (Direct API)
        fallback="seedream-4.5",  # Seedream-4.5 (ModelsLab)
        fallback2="flux-2-dev",  # Flux-2-Dev (ModelsLab)
    ),
    ModelTier.BASIC: ModelConfig(
        primary="nano-banana",  # Nano Banana / Gemini-2.5 (Direct API)
        fallback="flux-2-dev",  # Flux-2-Dev (ModelsLab)
        fallback2="hunyuan-image-3.0",  # Hunyuan-Image-3.0 (Direct API)
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="flux-2-pro",  # Flux-2-Pro (ModelsLab)
        fallback="flux-2-flex",  # Flux-2-Flex (Direct API)
        fallback2="nano-banana",  # Nano Banana / Gemini-2.5 (Direct API)
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="flux-2-max",  # Flux-2-Max (ModelsLab)
        fallback="nano-banana-pro",  # Nano Banana Pro / Gemini-3 (Direct API)
        fallback2="flux-2-pro",  # Flux-2-Pro (ModelsLab)
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="nano-banana-pro",  # Nano Banana Pro / Gemini-3 (Direct API)
        fallback="flux-2-max",  # Flux-2-Max (ModelsLab)
        fallback2="gpt-image-1.5",  # GPT-Image-1.5 (Direct API)
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="gpt-image-1.5",  # GPT-Image-1.5 (Direct API)
        fallback="nano-banana-pro",  # Nano Banana Pro / Gemini-3 (Direct API)
        fallback2="flux-2-max",  # Flux-2-Max (ModelsLab)
    ),
}


# Video Generation Strategy
# Optimizing for high-fidelity motion and consistency while managing compute costs
# ModelsLab aggregates top video models; Google's Veo accessed directly for enterprise-grade performance
VIDEO_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="seedance-v1-pro",  # Seedance-v1-Pro (ModelsLab)
        fallback="veo-3-fast",  # Veo-3-Fast (Direct API)
        fallback2="kling-2.5-turbo",  # Kling-2.5-Turbo (ModelsLab)
    ),
    ModelTier.BASIC: ModelConfig(
        primary="kling-2.5-turbo-1080p",  # Kling-2.5-Turbo-1080p (ModelsLab)
        fallback="seedance-v1-pro",  # Seedance-v1-Pro (ModelsLab)
        fallback2="veo-3-fast",  # Veo-3-Fast (Direct API)
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="veo-3-fast-audio",  # Veo-3-Fast-Audio (Direct API)
        fallback="kling-2.6-pro",  # Kling-2.6-Pro (ModelsLab)
        fallback2="wan2.5-i2v-preview",  # Wan2.5-I2V-Preview (ModelsLab)
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="veo-3-audio",  # Veo-3-Audio (Direct API)
        fallback="wan2.5-i2v-preview",  # Wan2.5-I2V-Preview (ModelsLab)
        fallback2="veo-3-fast-audio",  # Veo-3-Fast-Audio (Direct API)
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="veo-3.1-fast-audio",  # Veo-3.1-Fast-Audio (Direct API)
        fallback="veo-3-audio",  # Veo-3-Audio (Direct API)
        fallback2="wan2.5-i2v-preview",  # Wan2.5-I2V-Preview (ModelsLab)
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="veo-3.1-audio",  # Veo-3.1-Audio (Direct API)
        fallback="veo-3.1-fast-audio",  # Veo-3.1-Fast-Audio (Direct API)
        fallback2="wan2.5-i2v-preview",  # Wan2.5-I2V-Preview (ModelsLab)
    ),
}


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
        fallback="eleven_turbo_v2",
        fallback2="eleven_english_v1",
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="eleven_turbo_v2",
        fallback2="eleven_english_v1",
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="eleven_turbo_v2",
        fallback2=None,
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="eleven_turbo_v2",
        fallback2=None,
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
        if not video_config:
            logger.error(f"Missing video config for tier: {tier.value}")
        if not audio_config:
            logger.error(f"Missing audio config for tier: {tier.value}")

    logger.info("Model configuration validation complete")


validate_model_configs()
