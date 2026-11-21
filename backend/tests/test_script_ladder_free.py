from app.core.model_config import ModelTier, SCRIPT_MODEL_CONFIG


def test_free_script_ladder_order():
    # KAN-480: pin the complete Ollama-first ladder, including ZAI tail order.
    assert SCRIPT_MODEL_CONFIG[ModelTier.FREE].models == [
        "ollama/gemma4:31b",
        "piapi/gpt-4o-mini",
        "google/gemini-2.5-flash",
        "openai/gpt-5-mini",
        "anthropic/claude-haiku-4-5-20251001",
        "minimax/MiniMax-M2",
        "zai/glm-5.2",
        "zai/glm-5.1",
    ]
