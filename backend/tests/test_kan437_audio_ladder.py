from app.core.model_config import AUDIO_MODEL_CONFIG, TTS_TIER_CONFIG, ModelTier
from app.core.services.media_router import MediaRouter


def test_every_tier_audio_and_tts_ladders_include_piapi():
    router = MediaRouter()

    for tier in ModelTier:
        audio_ladder = router.resolve(tier=tier, media_type="audio")
        tts_ladder = router.resolve(tier=tier, media_type="tts")

        assert any(model.startswith("piapi/") for model in audio_ladder)
        assert any(model.startswith("piapi/") for model in tts_ladder)


def test_audio_ladders_preserve_modelslab_and_elevenlabs_entries():
    router = MediaRouter()

    for tier in ModelTier:
        ladder = router.resolve(tier=tier, media_type="audio")

        assert any(model.startswith("modelslab/") for model in ladder)
        assert any(model.startswith("elevenlabs/") for model in ladder)


def test_tts_ladders_preserve_elevenlabs_entries():
    router = MediaRouter()

    for tier in ModelTier:
        ladder = router.resolve(tier=tier, media_type="tts")

        assert any(model.startswith("elevenlabs/") for model in ladder)


def test_piapi_audio_fallbacks_are_appended_to_raw_configs():
    for tier in ModelTier:
        audio_models = AUDIO_MODEL_CONFIG[tier].models
        tts_models = TTS_TIER_CONFIG[tier].models

        assert "piapi/f5tts" in audio_models
        assert "piapi/fx-musicgen" in audio_models
        assert "piapi/Qubico/ace-step" in audio_models
        assert "piapi/f5tts" in tts_models
        assert "piapi/fx-musicgen" in tts_models
        assert "piapi/Qubico/ace-step" in tts_models
