from app.core.model_config import ModelTier, SCRIPT_MODEL_CONFIG


def test_free_script_ladder_order():
    assert SCRIPT_MODEL_CONFIG[ModelTier.FREE].models == [
        "zai/glm-5.2",
        "ollama/gemma4:31b",
        "featherless/zai-org/GLM-5.2",
        "piapi/gpt-4o-mini",
        "google/gemini-2.5-flash",
        "openai/gpt-5-mini",
        "anthropic/claude-haiku-4-5-20251001",
        "zai/glm-5.1",
    ]
