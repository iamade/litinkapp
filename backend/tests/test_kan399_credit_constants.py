from app.credits.constants import (
    estimate_book_pipeline_duration_credits,
    estimate_book_pipeline_script_credits,
    get_book_pipeline_credit_rate,
    normalize_book_pipeline_mode,
)


def test_free_tier_is_forced_to_draft_mode():
    assert normalize_book_pipeline_mode("cinematic", "free") == "draft"
    assert get_book_pipeline_credit_rate("image", "draft", "free") == 12


def test_paid_cinematic_rates_are_model_tier_aware():
    assert normalize_book_pipeline_mode("cinematic", "premium") == "cinematic"
    assert get_book_pipeline_credit_rate("image", "cinematic", "premium") == 17
    assert get_book_pipeline_credit_rate("image", "cinematic", "enterprise") == 65


def test_script_and_duration_estimators_match_kan399_rates():
    assert estimate_book_pipeline_script_credits(1200, "draft", "basic") == 6
    assert estimate_book_pipeline_script_credits(1200, "cinematic", "professional") == 30
    assert estimate_book_pipeline_duration_credits(2.1, "audio_per_second", "draft", "basic") == 6
    assert estimate_book_pipeline_duration_credits(2.1, "video_per_second", "cinematic", "pro") == 147
