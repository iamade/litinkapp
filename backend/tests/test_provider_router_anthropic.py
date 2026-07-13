from types import SimpleNamespace

import pytest

from app.core.services.provider_router import (
    ProviderNotConfiguredError,
    ProviderRouter,
)


class FakeMessages:
    def __init__(self):
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="hello")],
            usage=SimpleNamespace(input_tokens=3, output_tokens=2),
        )


@pytest.mark.asyncio
async def test_anthropic_adapter_normalizes_response_shape():
    messages = FakeMessages()
    client = SimpleNamespace(messages=messages)
    response = await ProviderRouter._anthropic_chat_completion(
        client,
        "claude-haiku-4-5-20251001",
        [
            {"role": "system", "content": "Be concise"},
            {"role": "user", "content": "Hi"},
        ],
        max_tokens=8,
        temperature=0.2,
        stream=False,
    )

    assert messages.kwargs["system"] == "Be concise"
    assert messages.kwargs["messages"] == [{"role": "user", "content": "Hi"}]
    assert response.choices[0].message.content == "hello"
    assert response.usage.total_tokens == 5


def test_unknown_prefix_does_not_fall_through_to_openrouter():
    with pytest.raises(
        ProviderNotConfiguredError, match="No adapter for prefix unknown"
    ):
        ProviderRouter().get_client_and_model("unknown/model")
