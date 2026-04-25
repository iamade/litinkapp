from app.core.model_config import ModelTier, get_model_config


DISALLOWED_TTS_PROVIDERS = (
    "google",
    "openai",
    "fish-speech",
    "kokoro",
)

EXPECTED_TTS_CHAINS = {
    "free": ["eleven_turbo_v2", "eleven_multilingual_v2", "eleven_english_v1"],
    "basic": ["eleven_multilingual_v2", "eleven_turbo_v2", "eleven_english_v1"],
    "standard": [
        "eleven_multilingual_v2",
        "elevenlabs/eleven_multilingual_v2",
        "eleven_english_v1",
    ],
    "premium": [
        "eleven_multilingual_v2",
        "elevenlabs/eleven_multilingual_v2",
        "eleven_english_v1",
    ],
    "professional": ["eleven_multilingual_v2", "elevenlabs/eleven_multilingual_v2"],
    "enterprise": ["eleven_multilingual_v2", "elevenlabs/eleven_multilingual_v2"],
}


def _configured_chain(config):
    return [
        model
        for model in (
            config.primary,
            config.fallback,
            config.fallback2,
            config.fallback3,
            config.fallback4,
        )
        if model
    ]


def test_tts_tier_config_uses_elevenlabs_only_chains():
    for tier in ModelTier:
        config = get_model_config("tts", tier.value)
        assert config is not None

        chain = _configured_chain(config)
        assert chain == EXPECTED_TTS_CHAINS[tier.value]
        assert all(
            model == "eleven_english_v1"
            or model.startswith("eleven_")
            or model.startswith("elevenlabs/")
            for model in chain
        )
        assert not any(
            blocked in model
            for model in chain
            for blocked in DISALLOWED_TTS_PROVIDERS
        )


def test_professional_and_enterprise_stop_after_direct_elevenlabs_fallback():
    for tier in ("professional", "enterprise"):
        config = get_model_config("tts", tier)
        assert config is not None
        assert config.primary == "eleven_multilingual_v2"
        assert config.fallback == "elevenlabs/eleven_multilingual_v2"
        assert config.fallback2 is None
        assert config.fallback3 is None
        assert config.fallback4 is None
