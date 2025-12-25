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


SCRIPT_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="google/gemini-2.0-flash-exp:free",
        fallback="meta-llama/llama-3.3-70b-instruct:free",
        fallback2="deepseek/deepseek-chat",
        max_tokens=2000,
        temperature=0.7,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
    ),
    ModelTier.BASIC: ModelConfig(
        primary="deepseek/deepseek-chat",
        fallback="mistralai/mistral-nemo",
        fallback2="meta-llama/llama-3.3-70b-instruct:free",
        max_tokens=3000,
        temperature=0.7,
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="anthropic/claude-3-haiku-20240307",
        fallback="openai/gpt-3.5-turbo",
        fallback2="deepseek/deepseek-chat",
        max_tokens=4000,
        temperature=0.7,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="openai/gpt-4o-mini",
        fallback="anthropic/claude-3.5-sonnet",
        fallback2="anthropic/claude-3-haiku-20240307",
        max_tokens=8000,
        temperature=0.7,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.00060,
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="openai/gpt-4o",
        fallback="anthropic/claude-3-opus-20240229",
        fallback2="openai/gpt-4o-mini",
        max_tokens=16000,
        temperature=0.8,
        cost_per_1k_input=0.00250,
        cost_per_1k_output=0.01000,
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="openai/gpt-4o",
        fallback="anthropic/claude-3-opus-20240229",
        fallback2="anthropic/claude-3.5-sonnet",
        max_tokens=16000,
        temperature=0.8,
        cost_per_1k_input=0.00250,
        cost_per_1k_output=0.01000,
    ),
}


IMAGE_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="gen4_image",
        fallback="nano-banana",
        fallback2="runway_image",
    ),
    ModelTier.BASIC: ModelConfig(
        primary="gen4_image",
        fallback="runway_image",
        fallback2="nano-banana",
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="runway_image",
        fallback="gen4_image",
        fallback2="nano-banana",
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="runway_image",
        fallback="gen4_image",
        fallback2="nano-banana",
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="runway_image",
        fallback="gen4_image",
        fallback2=None,
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="runway_image",
        fallback="gen4_image",
        fallback2=None,
    ),
}


VIDEO_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="veo2",
        fallback="seedance-i2v",
        fallback2=None,
    ),
    ModelTier.BASIC: ModelConfig(
        primary="veo2",
        fallback="seedance-i2v",
        fallback2=None,
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="veo2",
        fallback="veo2_pro",
        fallback2="seedance-i2v",
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="veo2_pro",
        fallback="veo2",
        fallback2="seedance-i2v",
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="veo2_pro",
        fallback="veo2",
        fallback2="seedance-i2v",
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="veo2_pro",
        fallback="veo2",
        fallback2="seedance-i2v",
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
