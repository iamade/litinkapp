from app.core.model_config import ModelTier, SCRIPT_MODEL_CONFIG


def test_pro_script_ladder_order():
    assert SCRIPT_MODEL_CONFIG[ModelTier.PRO].models == [
        "openai/gpt-5.5",
        "zai/glm-5.2",
        "featherless/zai-org/GLM-5.2",
        "piapi/gpt-4o-mini",
        "google/gemini-3.1-pro-preview",
        "openai/gpt-5.4-pro",
        "anthropic/claude-sonnet-4-6",
        "anthropic/claude-opus-4-6",
    ]
