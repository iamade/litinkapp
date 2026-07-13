from app.core.services.openrouter import OpenRouterService
from app.core.services.script_model_router import ScriptModelRouter


def test_openrouter_service_is_one_release_compatibility_alias():
    assert OpenRouterService is ScriptModelRouter
