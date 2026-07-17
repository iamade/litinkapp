from app.core.model_config import ModelTier
from app.core.services.media_router import MediaRouter


def test_every_tier_image_ladder_has_modelslab_and_piapi():
    router = MediaRouter()

    for tier in ModelTier:
        ladder = router.resolve(tier=tier, media_type="image")

        assert ladder
        assert all("/" in model for model in ladder)
        assert any(model.startswith("modelslab/") for model in ladder)
        assert any(model.startswith("piapi/") for model in ladder)


def test_modelslab_and_elevenlabs_remain_in_approved_ladders():
    router = MediaRouter()

    video_ladder = router.resolve(tier="standard", media_type="video")
    audio_ladder = router.resolve(tier="standard", media_type="audio")

    assert "modelslab/wan2.6-i2v" in video_ladder
    assert any(model.startswith("modelslab/") for model in audio_ladder)
    assert "elevenlabs/eleven_multilingual_v2" in audio_ladder


def test_router_normalizes_provider_prefixes():
    router = MediaRouter()

    ladder = router.resolve(tier="free", media_type="image")

    assert ladder[0] == "modelslab/seedream-t2i"
    assert "piapi/Qubico/flux1-schnell" in ladder
