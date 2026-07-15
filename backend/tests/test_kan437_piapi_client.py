import pytest

from app.core.services.piapi_client import PiAPIClient


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}: {self.payload}")


class FakeAsyncClient:
    def __init__(self, responses, calls):
        self.responses = responses
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, path, json, headers):
        self.calls.append(("POST", path, json, headers))
        return self.responses.pop(0)

    async def get(self, path, headers):
        self.calls.append(("GET", path, None, headers))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_create_and_poll_success(monkeypatch):
    calls = []
    responses = [
        FakeResponse({"data": {"task_id": "task-123"}}),
        FakeResponse({"data": {"status": "processing"}}),
        FakeResponse(
            {
                "data": {
                    "status": "completed",
                    "output": {"image_url": "https://cdn.piapi.ai/task-123.png"},
                }
            }
        ),
    ]

    def fake_client_factory(**kwargs):
        return FakeAsyncClient(responses, calls)

    monkeypatch.setattr("app.core.services.piapi_client.httpx.AsyncClient", fake_client_factory)

    client = PiAPIClient(api_key="secret-piapi-key", base_url="https://api.piapi.ai")
    result = await client.create_and_poll(
        model="flux-schnell",
        task_type="txt2img",
        input={"prompt": "a moonlit library"},
        poll_interval_seconds=0,
    )

    assert result["status"] == "success"
    assert result["url"] == "https://cdn.piapi.ai/task-123.png"
    assert result["metadata"]["task_id"] == "task-123"
    assert calls[0][1] == "/api/v1/task"
    assert calls[1][1] == "/api/v1/task/task-123"


@pytest.mark.asyncio
async def test_exception_messages_redact_api_key(monkeypatch):
    class FailingAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, path, json, headers):
            raise RuntimeError("upstream echoed secret-piapi-key")

    monkeypatch.setattr(
        "app.core.services.piapi_client.httpx.AsyncClient",
        lambda **kwargs: FailingAsyncClient(),
    )

    client = PiAPIClient(api_key="secret-piapi-key", base_url="https://api.piapi.ai")
    with pytest.raises(RuntimeError) as exc_info:
        await client.create_task(
            model="flux-schnell",
            task_type="txt2img",
            input={"prompt": "redacted"},
        )

    assert "secret-piapi-key" not in str(exc_info.value)
    assert "***" in str(exc_info.value)
