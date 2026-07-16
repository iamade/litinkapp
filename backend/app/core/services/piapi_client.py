from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class PiAPIClient:
    """Async client for PiAPI unified task creation and polling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 60.0,
        poll_interval_seconds: float = 2.0,
    ) -> None:
        self.api_key = api_key or settings.PIAPI_API_KEY_LITINKAI
        self.base_url = (base_url or settings.PIAPI_BASE_URL or "https://api.piapi.ai").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    async def create_task(
        self, model: str, task_type: str, input: Dict[str, Any]
    ) -> str:
        if not self.api_key:
            raise RuntimeError("PIAPI_API_KEY_LITINKAI missing")

        payload = {"model": model, "task_type": task_type, "input": input}
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url_for_client(),
                timeout=self.timeout_seconds,
            ) as client:
                response = await client.post(
                    self._task_path(),
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise RuntimeError(self._redact(f"PiAPI create_task failed: {exc}")) from exc

        task_id = self._extract_task_id(data)
        if not task_id:
            raise RuntimeError(
                self._redact(f"PiAPI create_task response missing task id: {data}")
            )
        logger.info("[PiAPI] Created %s task %s with model %s", task_type, task_id, model)
        return task_id

    async def poll_task(
        self,
        task_id: str,
        *,
        max_wait_seconds: float = 300.0,
        poll_interval_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("PIAPI_API_KEY_LITINKAI missing")

        interval = poll_interval_seconds or self.poll_interval_seconds
        deadline = asyncio.get_event_loop().time() + max_wait_seconds
        last_result: Dict[str, Any] = {"status": "processing", "metadata": {}}

        while True:
            try:
                async with httpx.AsyncClient(
                    base_url=self._base_url_for_client(),
                    timeout=self.timeout_seconds,
                ) as client:
                    response = await client.get(
                        f"{self._task_path()}/{task_id}",
                        headers=self._headers(),
                    )
                    response.raise_for_status()
                    data = response.json()
            except Exception as exc:
                raise RuntimeError(self._redact(f"PiAPI poll_task failed: {exc}")) from exc

            last_result = self._standardize_task_response(data)
            if last_result["status"] in {"success", "error"}:
                return last_result

            if asyncio.get_event_loop().time() >= deadline:
                return {
                    "status": "error",
                    "url": None,
                    "metadata": last_result.get("metadata", data),
                    "error": f"PiAPI task {task_id} timed out",
                }
            await asyncio.sleep(interval)

    async def create_and_poll(
        self,
        model: str,
        task_type: str,
        input: Dict[str, Any],
        *,
        max_wait_seconds: float = 300.0,
        poll_interval_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        task_id = await self.create_task(model=model, task_type=task_type, input=input)
        result = await self.poll_task(
            task_id,
            max_wait_seconds=max_wait_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        result.setdefault("metadata", {})
        result["metadata"].setdefault("task_id", task_id)
        return result

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key or "",
            "Content-Type": "application/json",
        }

    def _base_url_for_client(self) -> str:
        if self.base_url.endswith("/api/v1"):
            return self.base_url[: -len("/api/v1")]
        if self.base_url.endswith("/v1"):
            return self.base_url[: -len("/v1")]
        return self.base_url

    def _task_path(self) -> str:
        return "/api/v1/task"

    @staticmethod
    def _extract_task_id(data: Dict[str, Any]) -> Optional[str]:
        task = data.get("data") if isinstance(data.get("data"), dict) else data
        return (
            task.get("task_id")
            or task.get("id")
            or task.get("task", {}).get("id")
            or task.get("task", {}).get("task_id")
        )

    def _standardize_task_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        task = data.get("data") if isinstance(data.get("data"), dict) else data
        raw_status = str(task.get("status") or task.get("state") or "").lower()

        if raw_status in {"success", "completed", "complete", "succeeded", "done"}:
            return {
                "status": "success",
                "url": self._extract_url(task),
                "metadata": task,
                "error": None,
            }
        if raw_status in {"error", "failed", "failure", "cancelled", "canceled"}:
            return {
                "status": "error",
                "url": self._extract_url(task),
                "metadata": task,
                "error": self._redact(
                    str(task.get("error") or task.get("message") or "PiAPI task failed")
                ),
            }
        return {
            "status": "processing",
            "url": self._extract_url(task),
            "metadata": task,
            "error": None,
        }

    def _extract_url(self, task: Dict[str, Any]) -> Optional[str]:
        output = task.get("output") or task.get("result") or task.get("outputs")
        if isinstance(output, list) and output:
            first = output[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                return first.get("url") or first.get("image_url")
        if isinstance(output, dict):
            for key in ("url", "image_url", "output_url", "audio_url", "video_url"):
                if output.get(key):
                    return output[key]
            images = output.get("images")
            if isinstance(images, list) and images:
                first_image = images[0]
                if isinstance(first_image, str):
                    return first_image
                if isinstance(first_image, dict):
                    return first_image.get("url") or first_image.get("image_url")
        for key in ("url", "image_url", "output_url", "audio_url", "video_url"):
            if task.get(key):
                return task[key]
        return None

    def _redact(self, value: str) -> str:
        if self.api_key:
            return value.replace(self.api_key, "***")
        return value


piapi_client = PiAPIClient()
