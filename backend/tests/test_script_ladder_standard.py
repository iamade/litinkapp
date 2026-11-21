from app.core.model_config import ModelTier, SCRIPT_MODEL_CONFIG, get_model_config


def test_standard_script_ladder_order():
    # KAN-480: pin the complete Ollama-first ladder, including ZAI tail order.
    assert SCRIPT_MODEL_CONFIG[ModelTier.STANDARD].models == [
        "ollama/deepseek-v4-pro:cloud",
        "piapi/gpt-4o-mini",
        "google/gemini-2.5-pro",
        "openai/gpt-5.4",
        "anthropic/claude-sonnet-4-6",
        "anthropic/claude-opus-4-6",
        "minimax/MiniMax-M2.7-highspeed",
        "zai/glm-5.1",
        "zai/glm-5.2",
    ]


def test_professional_and_enterprise_use_pro_script_ladder():
    pro = SCRIPT_MODEL_CONFIG[ModelTier.PRO]
    assert get_model_config("script", "professional") is pro
    assert get_model_config("script", "enterprise") is pro


def test_legacy_pro_value_uses_standard_script_ladder():
    assert get_model_config("script", "pro") is SCRIPT_MODEL_CONFIG[ModelTier.STANDARD]


def test_every_script_ladder_has_at_least_eight_slots_and_at_most_two_ollama_models():
    # KAN-450: MiniMax fallbacks extend beyond original 8-slot ladder
    for tier, config in SCRIPT_MODEL_CONFIG.items():
        assert len(config.models) >= 8, tier
        assert sum(model.startswith("ollama/") for model in config.models) <= 2, tier
