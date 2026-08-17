from app.core.model_config import ModelTier, SCRIPT_MODEL_CONFIG


def test_basic_script_ladder_order():
    # KAN-450: MiniMax fallbacks (M2.5, M2.1) appended after existing 8-slot ladder
    assert SCRIPT_MODEL_CONFIG[ModelTier.BASIC].models == [
        "zai/glm-5.2",
        "ollama/deepseek-v4-pro:cloud",
        "featherless/zai-org/GLM-5.2",
        "piapi/gpt-4o-mini",
        "google/gemini-2.5-flash",
        "openai/gpt-5-mini",
        "anthropic/claude-haiku-4-5-20251001",
        "anthropic/claude-sonnet-4-6",
        "minimax/MiniMax-M2.5",
        "minimax/MiniMax-M2.1",
    ]


def test_basic_script_ladder_existing_order_preserved():
    """KAN-450: MiniMax models are appended; existing 8-slot chain must remain unchanged."""
    models = SCRIPT_MODEL_CONFIG[ModelTier.BASIC].models
    assert models[:8] == [
        "zai/glm-5.2",
        "ollama/deepseek-v4-pro:cloud",
        "featherless/zai-org/GLM-5.2",
        "piapi/gpt-4o-mini",
        "google/gemini-2.5-flash",
        "openai/gpt-5-mini",
        "anthropic/claude-haiku-4-5-20251001",
        "anthropic/claude-sonnet-4-6",
    ]
    assert "minimax/MiniMax-M2.5" in models
    assert "minimax/MiniMax-M2.1" in models
