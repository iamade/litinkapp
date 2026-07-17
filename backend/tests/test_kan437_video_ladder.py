from app.core.model_config import ModelTier
from app.core.services.media_router import MediaRouter


def test_every_tier_video_ladder_has_modelslab_and_piapi():
    router = MediaRouter()

    for tier in ModelTier:
        ladder = router.resolve(tier=tier, media_type="video")

        assert ladder
        assert any(model.startswith("modelslab/") for model in ladder)
        assert any(model.startswith("piapi/") for model in ladder)


def test_modelslab_video_models_remain_in_ladders():
    router = MediaRouter()

    standard_ladder = router.resolve(tier="standard", media_type="video")
    premium_ladder = router.resolve(tier="premium", media_type="video")
    free_ladder = router.resolve(tier="free", media_type="video")

    assert "modelslab/wan2.6-i2v" in standard_ladder
    assert "modelslab/wan2.5-i2v" in free_ladder
    assert "modelslab/omni-human" in premium_ladder
    assert "modelslab/omni-human-1.5" in premium_ladder
