from app.core.model_config import ModelTier, SCRIPT_MODEL_CONFIG


def test_premium_script_ladder_order():
    assert SCRIPT_MODEL_CONFIG[ModelTier.PREMIUM].models == [
        "zai/glm-5.2",
        "ollama/kimi-k2.6:cloud",
        "featherless/zai-org/GLM-5.2",
        "piapi/gpt-4o-mini",
        "google/gemini-3.1-pro-preview",
        "openai/gpt-5.4",
        "anthropic/claude-sonnet-4-6",
        "anthropic/claude-opus-4-6",
    ]
