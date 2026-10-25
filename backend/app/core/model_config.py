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
    PRO = (
        "pro"  # KAN-tier-mapping: alias for PROFESSIONAL (SubscriptionTier uses "pro")
    )
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class ModelConfig:
    primary: str
    fallback: str
    fallback2: Optional[str] = None
    fallback3: Optional[
        str
    ] = None  # Added for additional fallback (Veo 3 direct, Grok AI)
    fallback4: Optional[str] = None  # 5th option — cross-provider safety net
    fallback5: Optional[str] = None
    fallback6: Optional[str] = None
    fallback7: Optional[str] = None
    fallback8: Optional[str] = None  # KAN-450: MiniMax extension
    fallback9: Optional[str] = None  # KAN-450: MiniMax extension
    fallback10: Optional[str] = None  # KAN-450: MiniMax extension
    fallback11: Optional[str] = None  # KAN-450: MiniMax extension
    fallback12: Optional[str] = None  # KAN-450: MiniMax extension
    fallback13: Optional[str] = None  # KAN-450: MiniMax extension
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    cost_per_1k_input: Optional[float] = None
    cost_per_1k_output: Optional[float] = None

    @property
    def models(self) -> List[str]:
        return [
            model
            for model in (
                self.primary,
                self.fallback,
                self.fallback2,
                self.fallback3,
                self.fallback4,
                self.fallback5,
                self.fallback6,
                self.fallback7,
                self.fallback8,
                self.fallback9,
                self.fallback10,
                self.fallback11,
                self.fallback12,
                self.fallback13,
            )
            if model
        ]

# Script ladders prefer the existing Ollama route; Z.ai is a later fallback.
# Featherless is excluded. A second account requires separate eligibility review.
# Token prices below are standard USD per 1M input/output tokens as of 2026-07-12.
# Subscription/proxy slots need their effective dashboard rate in the COGS audit.
#
# ============================================================================
# KAN-450: MiniMax Model Family — Pricing & Credential Notes
# ============================================================================
# MiniMax uses a SUBSCRIPTION CREDIT model, not per-token pricing like OpenAI/Anthropic.
# Credits are consumed per request and vary by model tier. Estimates below are
# approximate per-generation credit costs based on platform.minimax.io/docs/guides/pricing:
#   - MiniMax-M3:          ~$0.02-0.05/1k tokens equiv. (frontier tier, highest credit cost)
#   - MiniMax-M2.7:        ~$0.015-0.04/1k tokens equiv. (engineering quality)
#   - MiniMax-M2.7-highspeed: ~$0.012-0.03/1k tokens equiv. (lower latency, slightly cheaper)
#   - MiniMax-M2.5:        ~$0.008-0.02/1k tokens equiv. (legacy value)
#   - MiniMax-M2.1:        ~$0.006-0.015/1k tokens equiv. (MoE, efficient)
#   - MiniMax-M2:          ~$0.004-0.01/1k tokens equiv. (agentic, 200k ctx)
# Source: https://platform.minimax.io/docs/guides/pricing (accessed 2026-07-30)
#
# PRODUCTION CREDENTIALS: MINIMAX_API_KEY is present in the environment (.env) but
# the production credential decision must be made before using Ade's personal key
# for live customer-facing calls. Do NOT enable MiniMax as a live provider until
# LC/Ade approves the credential for production traffic.
# ============================================================================
SCRIPT_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary='ollama/gemma4:31b',
        fallback='piapi/gpt-4o-mini',
        fallback2='google/gemini-2.5-flash',
        fallback3='openai/gpt-5-mini',
        fallback4='anthropic/claude-haiku-4-5-20251001',
        fallback5='minimax/MiniMax-M2',
        fallback6='zai/glm-5.2',
        fallback7='zai/glm-5.1',
        max_tokens=4000,
        temperature=0.7,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
    ),
    ModelTier.BASIC: ModelConfig(
        primary='ollama/deepseek-v4-pro:cloud',
        fallback='piapi/gpt-4o-mini',
        fallback2='google/gemini-2.5-flash',
        fallback3='openai/gpt-5-mini',
        fallback4='anthropic/claude-haiku-4-5-20251001',
        fallback5='anthropic/claude-sonnet-4-6',
        fallback6='minimax/MiniMax-M2.5',
        fallback7='minimax/MiniMax-M2.1',
        fallback8='zai/glm-5.2',
        max_tokens=4000,
        temperature=0.7,
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
    ),
    ModelTier.STANDARD: ModelConfig(
        primary='ollama/deepseek-v4-pro:cloud',
        fallback='piapi/gpt-4o-mini',
        fallback2='google/gemini-2.5-pro',
        fallback3='openai/gpt-5.4',
        fallback4='anthropic/claude-sonnet-4-6',
        fallback5='anthropic/claude-opus-4-6',
        fallback6='minimax/MiniMax-M2.7-highspeed',
        fallback7='zai/glm-5.1',
        fallback8='zai/glm-5.2',
        max_tokens=8000,
        temperature=0.7,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary='ollama/kimi-k2.6:cloud',
        fallback='piapi/gpt-4o-mini',
        fallback2='google/gemini-3.1-pro-preview',
        fallback3='openai/gpt-5.4',
        fallback4='anthropic/claude-sonnet-4-6',
        fallback5='anthropic/claude-opus-4-6',
        fallback6='minimax/MiniMax-M2.7',
        fallback7='zai/glm-5.2',
        max_tokens=8000,
        temperature=0.75,
        cost_per_1k_input=0.00150,
        cost_per_1k_output=0.00600,
    ),
    ModelTier.PRO: ModelConfig(
        primary='ollama/kimi-k2.6:cloud',
        fallback='openai/gpt-5.5',
        fallback2='piapi/gpt-4o-mini',
        fallback3='google/gemini-3.1-pro-preview',
        fallback4='openai/gpt-5.4-pro',
        fallback5='anthropic/claude-sonnet-4-6',
        fallback6='anthropic/claude-opus-4-6',
        fallback7='minimax/MiniMax-M3',
        fallback8='zai/glm-5.2',
        max_tokens=16000,
        temperature=0.8,
        cost_per_1k_input=0.00250,
        cost_per_1k_output=0.01000,
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
        fallback3="piapi/Qubico/flux1-schnell",
        # KAN-447: GLM image (additive, not reordering existing)
        fallback4="glm/glm-image",
    ),
    ModelTier.BASIC: ModelConfig(
        primary="seedream-4",  # Seedream-4 (ModelsLab V7) Per image generation will cost $0.033
        fallback="imagen-4",  # imagen-4 (ModelsLab API) Per image generation will cost 0.044$
        fallback2="nano-banana-pro",  # nano-banana-pro (ModelsLab V7) working Your request will cost $0.18 per image
        fallback3="piapi/Qubico/flux1-schnell",
        # fallback2="qwen-image-2512",  # Qwen-Image-2512 (Direct API)
        # KAN-447: GLM image (additive, not reordering existing)
        fallback4="glm/glm-image",
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="imagen-4",  # imagen-4 (ModelsLab API) Per image generation will cost 0.044$
        fallback="nano-banana-t2i",  # nano-banana-t2i (ModelsLab V7) working Your request will cost $0.046
        fallback2="nano-banana-pro",  # nano-banana-pro (ModelsLab V7) working Your request will cost $0.18 per image
        fallback3="piapi/Qubico/flux1-schnell",
        # fallback2="nano-banana",  # Nano Banana / Gemini-2.5 (Direct API)
        # KAN-447: GLM image (additive)
        fallback4="glm/glm-image",
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="nano-banana-t2i",  # nano-banana-t2i (ModelsLab V7) working Your request will cost $0.046
        fallback="seedream-4.5",  # seedream-4.5 (ModelsLab V7) working Your request will cost $0.06
        fallback2="nano-banana-pro",  #  nano-banana-pro (ModelsLab V7) working Your request will cost $0.18 per image
        fallback3="piapi/Qubico/flux1-schnell",
        # fallback="nano-banana-pro",  # Nano Banana Pro / Gemini-3 (Direct API)
        # KAN-447: GLM image (additive)
        fallback4="glm/glm-image",
    ),
    ModelTier.PRO: ModelConfig(  # KAN-tier-mapping: "pro" alias for PROFESSIONAL
        primary="seedream-4.5",  # seedream-4.5 (ModelsLab V7) working Your request will cost $0.06
        fallback="imagen-4.0-ultra",  #  imagen-4.0-ultra (ModelsLab API) Per image generation will cost 0.072$
        fallback2="nano-banana-pro",  # nano-banana-pro (ModelsLab V7) working Your request will cost $0.18 per image
        fallback3="piapi/Qubico/flux1-schnell",
        #  fallback2="gpt-image-1.5",  # GPT-Image-1.5 (Direct API
        # KAN-447: GLM image (additive)
        fallback4="glm/glm-image",
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="seedream-4.5",  # seedream-4.5 (ModelsLab V7) working Your request will cost $0.06
        fallback="imagen-4.0-ultra",  #  imagen-4.0-ultra (ModelsLab API) Per image generation will cost 0.072$
        fallback2="nano-banana-pro",  # nano-banana-pro (ModelsLab V7) working Your request will cost $0.18 per image
        fallback3="piapi/Qubico/flux1-schnell",
        #  fallback2="gpt-image-1.5",  # GPT-Image-1.5 (Direct API
        # KAN-447: GLM image (additive)
        fallback4="glm/glm-image",
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="nano-banana-pro",  # nano-banana-pro (ModelsLab V7) working Your request will cost $0.18 per image
        fallback="gpt-image-1.5",  # GPT-Image-1.5 (Direct API)
        fallback2="nano-banana",  # Nano Banana / Gemini-2.5 (Direct API)
        fallback3="piapi/Qubico/flux1-schnell",
        # fallback3="nano-banana-pro",  # Nano Banana Pro / Gemini-3 (Direct API)
        # KAN-447: GLM image (additive)
        fallback4="glm/glm-image",
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
    ModelTier.PRO: ModelConfig(  # KAN-tier-mapping: "pro" alias for PROFESSIONAL
        primary="seedream-4.5-i2i",  # seedream-4.5 (ModelsLab) $0.06
        fallback="nano-banana",  # Nano Banana (ModelsLab) $0.0468
        fallback2="seededit-i2i",
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
    ModelTier.PRO: ModelConfig(  # KAN-tier-mapping: "pro" alias for PROFESSIONAL
        primary="seedream-4.5-i2i",  # seedream-4.5 (ModelsLab) $0.06
        fallback="nano-banana",  # Nano Banana (ModelsLab) $0.0468
        fallback2="seedream-4.0-i2i",
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
#
# KAN-450: MiniMax Hailuo video models (Hailuo-02, Hailuo-01, etc.) are EXCLUDED
# from Plus plan tiers (FREE/BASIC/STANDARD). They are only available on PREMIUM+
# tiers when video model expansion is approved. Do NOT add Hailuo models to
# FREE/BASIC/STANDARD VIDEO_MODEL_CONFIG entries.
VIDEO_MODEL_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="wan2.5-i2v",  # Wan2.5-I2V (ModelsLab) 480p - basic lip-sync capable
        fallback="wan2.6-i2v",  # Wan2.6-I2V (ModelsLab) - upgraded fallback
        fallback2="piapi/kling",
        fallback3="piapi/wan2.1-i2v",
        # KAN-447: GLM video (additive)
        fallback4="glm/cogvideox-3",
    ),
    ModelTier.BASIC: ModelConfig(
        primary="wan2.6-i2v",  # Wan2.6-I2V (ModelsLab) 720p - better audio sync
        fallback="wan2.5-i2v",  # Wan2.5-I2V (ModelsLab) 480p fallback
        fallback2="piapi/kling",
        fallback3="piapi/wan2.1-i2v",
        # KAN-447: GLM video (additive)
        fallback4="glm/cogvideox-3",
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="omni-human-1.5",  # Omni-Human-1.5 (ModelsLab) - talking head specialist
        fallback="wan2.6-i2v",  # Wan2.6-I2V fallback
        fallback2="wan2.5-i2v",  # Wan2.5-I2V fallback
        fallback3="piapi/kling",
        fallback4="piapi/wan2.1-i2v",
        # KAN-447: GLM video (additive)
        fallback5="glm/cogvideox-3",
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="omni-human",  # Omni-Human (ModelsLab) - high quality talking head
        fallback="omni-human-1.5",  # Omni-Human-1.5 fallback
        fallback2="wan2.6-i2v",  # Wan2.6-I2V fallback
        fallback3="piapi/kling",
        fallback4="piapi/wan2.1-i2v",
        # KAN-447: GLM video (additive)
        fallback5="glm/cogvideox-3",
    ),
    ModelTier.PRO: ModelConfig(  # KAN-tier-mapping: "pro" alias for PROFESSIONAL
        primary="omni-human",  # Omni-Human (ModelsLab) - professional quality
        fallback="omni-human-1.5",  # Omni-Human-1.5 fallback
        fallback2="wan2.6-i2v",  # Wan2.6-I2V fallback
        fallback3="piapi/kling",
        fallback4="piapi/wan2.1-i2v",
        # KAN-447: GLM video (additive)
        fallback5="glm/cogvideox-3",
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="omni-human",  # Omni-Human (ModelsLab) - professional quality
        fallback="omni-human-1.5",  # Omni-Human-1.5 fallback
        fallback2="wan2.6-i2v",  # Wan2.6-I2V fallback
        fallback3="piapi/kling",
        fallback4="piapi/wan2.1-i2v",
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="omni-human-1.5",  # Omni-Human-1.5 - best for enterprise (stable)
        fallback="omni-human",  # Omni-Human fallback
        fallback2="wan2.6-i2v",  # Wan2.6-I2V fallback
        fallback3="piapi/kling",
        fallback4="piapi/wan2.1-i2v",
        # KAN-447: GLM video (additive)
        fallback5="glm/cogvideox-3",
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
        fallback3="piapi/f5tts",
        fallback4="piapi/fx-musicgen",
        fallback5="piapi/Qubico/ace-step",
    ),
    ModelTier.BASIC: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="eleven_turbo_v2",
        fallback2="eleven_english_v1",
        fallback3="piapi/f5tts",
        fallback4="piapi/fx-musicgen",
        fallback5="piapi/Qubico/ace-step",
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="elevenlabs/eleven_multilingual_v2",  # Direct ElevenLabs Fallback
        fallback2="eleven_english_v1",
        fallback3="piapi/f5tts",
        fallback4="piapi/fx-musicgen",
        fallback5="piapi/Qubico/ace-step",
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="elevenlabs/eleven_multilingual_v2",  # Direct ElevenLabs Fallback
        fallback2="eleven_english_v1",
        fallback3="piapi/f5tts",
        fallback4="piapi/fx-musicgen",
        fallback5="piapi/Qubico/ace-step",
    ),
    ModelTier.PRO: ModelConfig(  # KAN-tier-mapping: "pro" alias for PROFESSIONAL
        primary="eleven_multilingual_v2",
        fallback="elevenlabs/eleven_multilingual_v2",  # Direct ElevenLabs Fallback
        fallback2="piapi/f5tts",
        fallback3="piapi/fx-musicgen",
        fallback4="piapi/Qubico/ace-step",
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="elevenlabs/eleven_multilingual_v2",  # Direct ElevenLabs Fallback
        fallback2="piapi/f5tts",
        fallback3="piapi/fx-musicgen",
        fallback4="piapi/Qubico/ace-step",
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="eleven_multilingual_v2",
        fallback="elevenlabs/eleven_multilingual_v2",  # Direct ElevenLabs Fallback
        fallback2="piapi/f5tts",
        fallback3="piapi/fx-musicgen",
        fallback4="piapi/Qubico/ace-step",
    ),
}


TTS_TIER_CONFIG: Dict[ModelTier, ModelConfig] = {
    ModelTier.FREE: ModelConfig(
        primary="elevenlabs/eleven_turbo_v2",
        fallback="openai/tts-1",
        fallback2="google/text-to-speech",
        fallback3="piapi/f5tts",
        fallback4="piapi/fx-musicgen",
        fallback5="piapi/Qubico/ace-step",
    ),
    ModelTier.BASIC: ModelConfig(
        primary="elevenlabs/eleven_multilingual_v2",
        fallback="openai/tts-1-hd",
        fallback2="google/text-to-speech",
        fallback3="piapi/f5tts",
        fallback4="piapi/fx-musicgen",
        fallback5="piapi/Qubico/ace-step",
    ),
    ModelTier.STANDARD: ModelConfig(
        primary="elevenlabs/eleven_multilingual_v2",
        fallback="openai/tts-1-hd",
        fallback2="google/text-to-speech",
        fallback3="fish-speech/default",
        fallback4="piapi/f5tts",
        fallback5="piapi/fx-musicgen",
        fallback6="piapi/Qubico/ace-step",
    ),
    ModelTier.PREMIUM: ModelConfig(
        primary="elevenlabs/eleven_multilingual_v2",
        fallback="openai/tts-1-hd",
        fallback2="google/text-to-speech",
        fallback3="fish-speech/default",
        fallback4="piapi/f5tts",
        fallback5="piapi/fx-musicgen",
        fallback6="piapi/Qubico/ace-step",
    ),
    ModelTier.PRO: ModelConfig(  # KAN-tier-mapping: "pro" alias for PROFESSIONAL
        primary="elevenlabs/eleven_multilingual_v2",
        fallback="openai/tts-1-hd",
        fallback2="fish-speech/default",
        fallback3="google/text-to-speech",
        fallback4="piapi/f5tts",
        fallback5="piapi/fx-musicgen",
        fallback6="piapi/Qubico/ace-step",
    ),
    ModelTier.PROFESSIONAL: ModelConfig(
        primary="elevenlabs/eleven_multilingual_v2",
        fallback="openai/tts-1-hd",
        fallback2="fish-speech/default",
        fallback3="google/text-to-speech",
        fallback4="piapi/f5tts",
        fallback5="piapi/fx-musicgen",
        fallback6="piapi/Qubico/ace-step",
    ),
    ModelTier.ENTERPRISE: ModelConfig(
        primary="elevenlabs/eleven_multilingual_v2",
        fallback="openai/tts-1-hd",
        fallback2="fish-speech/default",
        fallback3="google/text-to-speech",
        fallback4="kokoro/default",
        fallback5="piapi/f5tts",
        fallback6="piapi/fx-musicgen",
        fallback7="piapi/Qubico/ace-step",
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
    ModelTier.PRO: ModelConfig(  # KAN-tier-mapping: "pro" alias for PROFESSIONAL
        primary="ultra_resolution",  # 4K+ upscaling - best quality
        fallback="RealESRGAN_x4plus",  # 4x fallback
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

        if service_type.lower() == "script":
            if model_tier == ModelTier.PRO:
                # Historical subscription rows used `pro` for the Standard price.
                model_tier = ModelTier.STANDARD
            elif model_tier in {ModelTier.PROFESSIONAL, ModelTier.ENTERPRISE}:
                model_tier = ModelTier.PRO

        config_map = {
            "script": SCRIPT_MODEL_CONFIG,
            "image": IMAGE_MODEL_CONFIG,
            "video": VIDEO_MODEL_CONFIG,
            "audio": AUDIO_MODEL_CONFIG,
            "tts": TTS_TIER_CONFIG,
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
        script_config = get_model_config("script", tier.value)
        image_config = IMAGE_MODEL_CONFIG.get(tier)
        video_config = VIDEO_MODEL_CONFIG.get(tier)
        audio_config = AUDIO_MODEL_CONFIG.get(tier)
        tts_config = TTS_TIER_CONFIG.get(tier)

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
        if not tts_config:
            logger.error(f"Missing tts config for tier: {tier.value}")

    logger.info("Model configuration validation complete")


validate_model_configs()
