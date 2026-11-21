from app.core.model_config import ModelTier, SCRIPT_MODEL_CONFIG


def test_basic_script_ladder_order():
    # KAN-480: pin the complete Ollama-first ladder, including ZAI tail order.
    assert SCRIPT_MODEL_CONFIG[ModelTier.BASIC].models == [
        "ollama/deepseek-v4-pro:cloud",
        "piapi/gpt-4o-mini",
        "google/gemini-2.5-flash",
        "openai/gpt-5-mini",
        "anthropic/claude-haiku-4-5-20251001",
        "anthropic/claude-sonnet-4-6",
        "minimax/MiniMax-M2.5",
        "minimax/MiniMax-M2.1",
        "zai/glm-5.2",
    ]


def test_basic_script_ladder_existing_order_preserved():
    """KAN-480: preserve the complete approved order, not the superseded prefix."""
    models = SCRIPT_MODEL_CONFIG[ModelTier.BASIC].models
    assert models == [
        "ollama/deepseek-v4-pro:cloud",
        "piapi/gpt-4o-mini",
        "google/gemini-2.5-flash",
        "openai/gpt-5-mini",
        "anthropic/claude-haiku-4-5-20251001",
        "anthropic/claude-sonnet-4-6",
        "minimax/MiniMax-M2.5",
        "minimax/MiniMax-M2.1",
        "zai/glm-5.2",
    ]
    assert "minimax/MiniMax-M2.5" in models
    assert "minimax/MiniMax-M2.1" in models
