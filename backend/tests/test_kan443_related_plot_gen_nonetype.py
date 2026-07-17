"""Regression tests for KAN-443-related plot generation NoneType crash.

PSQ hit a 500 during plot overview generation:
    'NoneType' object is not subscriptable

The root cause was in ScriptModelRouter's raw-JSON fallback path and in
_execute_analysis, where response/usage fields were dereferenced without
None/missing-key guards.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.model_config import ModelTier
from app.core.services.script_model_router import ScriptModelRouter


class _FakeResponse:
    """A fake httpx/openai response that only exposes .json()."""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _fake_fallback(generation_function, request_params, **kwargs):
    return generation_function(**request_params)


@pytest.fixture
def router():
    r = ScriptModelRouter()
    r.cost_tracker = SimpleNamespace(track=AsyncMock())
    return r


@pytest.mark.asyncio
async def test_generate_script_handles_raw_json_response_with_missing_usage(router):
    """KAN-443 regression: raw JSON response without usage must not crash."""
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"scenes": [{"text": "hello"}]}),
                }
            }
        ],
        # usage intentionally absent
    }

    with patch.object(
        router, "_prepare_script_messages", return_value=([], "cinematic")
    ), patch(
        "app.core.services.script_model_router.provider_router.chat_completion",
        new_callable=AsyncMock,
        return_value=_FakeResponse(payload),
    ), patch(
        "app.core.services.script_model_router.fallback_manager.try_with_fallback",
        new=_fake_fallback,
    ):
        result = await router.generate_script(
            content="test",
            user_tier=ModelTier.FREE,
            script_type="cinematic",
        )

    assert result["status"] == "success"
    assert result["content"] is not None
    assert result["usage"]["prompt_tokens"] == 0
    assert result["usage"]["completion_tokens"] == 0


@pytest.mark.asyncio
async def test_generate_script_rejects_raw_json_response_without_choices(router):
    payload = {"usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}}

    with patch.object(
        router, "_prepare_script_messages", return_value=([], "cinematic")
    ), patch(
        "app.core.services.script_model_router.provider_router.chat_completion",
        new_callable=AsyncMock,
        return_value=_FakeResponse(payload),
    ), patch(
        "app.core.services.script_model_router.fallback_manager.try_with_fallback",
        new=_fake_fallback,
    ):
        with pytest.raises(ValueError, match="choices"):
            await router.generate_script(
                content="test",
                user_tier=ModelTier.FREE,
                script_type="cinematic",
            )


@pytest.mark.asyncio
async def test_execute_analysis_handles_parsed_response_without_usage(router):
    """KAN-443 regression: analysis response without usage must not crash."""
    payload = {
        "choices": [
            {"message": {"content": json.dumps({"summary": "a story"})}}
        ],
    }

    with patch(
        "app.core.services.script_model_router.provider_router.chat_completion",
        new_callable=AsyncMock,
        return_value=_FakeResponse(payload),
    ):
        result = await router._execute_analysis(
            model="ollama/gemma3:4b",
            system_prompt="sys",
            user_message="user",
            max_tokens=100,
            temperature=0.5,
            analysis_type="summary",
            config=SimpleNamespace(
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
            ),
            tier_str="free",
        )

    assert result["status"] == "success"
    assert result["result"] is not None
    assert result["usage"]["prompt_tokens"] == 0
    assert result["usage"]["completion_tokens"] == 0


@pytest.mark.asyncio
async def test_execute_analysis_handles_object_response_without_usage(router):
    """KAN-443 regression: parsed object response with None usage must not crash."""
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
        usage=None,
    )

    with patch(
        "app.core.services.script_model_router.provider_router.chat_completion",
        new_callable=AsyncMock,
        return_value=response,
    ):
        result = await router._execute_analysis(
            model="ollama/gemma3:4b",
            system_prompt="sys",
            user_message="user",
            max_tokens=100,
            temperature=0.5,
            analysis_type="summary",
            config=SimpleNamespace(
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
            ),
            tier_str="free",
        )

    assert result["status"] == "success"
    assert result["result"] == '{"ok": true}'
    assert result["usage"]["prompt_tokens"] == 0


@pytest.mark.asyncio
async def test_execute_analysis_rejects_response_without_choices_or_json(router):
    response = SimpleNamespace(choices=None, usage=None)

    with patch(
        "app.core.services.script_model_router.provider_router.chat_completion",
        new_callable=AsyncMock,
        return_value=response,
    ):
        with pytest.raises(ValueError, match="Invalid response format"):
            await router._execute_analysis(
                model="ollama/gemma3:4b",
                system_prompt="sys",
                user_message="user",
                max_tokens=100,
                temperature=0.5,
                analysis_type="summary",
                config=SimpleNamespace(
                    cost_per_1k_input=0.0,
                    cost_per_1k_output=0.0,
                ),
                tier_str="free",
            )
