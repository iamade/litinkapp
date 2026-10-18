"""
KAN-448: Periodic Celery task for the model deprecation watcher.

Registered for explicit Celery invocation; no beat schedule is enabled. Executes
one watcher sweep and writes the resulting report to a JSON status artifact
on disk so that operators / other tooling can query the latest state without
re-running the check.

Fail-safe: any unexpected exception is caught and logged; the task never
raises (a watcher failure must not poison the beat worker).
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

#: Location of the queryable status artifact.  Overridable via env so tests
#: and non-production deploys can redirect it.
STATUS_ARTIFACT_PATH = os.getenv(
    "MODEL_WATCHER_STATUS_PATH",
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "var",
        "model_deprecation_status.json",
    ),
)


@celery_app.task(
    bind=True, name="app.tasks.model_watcher_tasks.run_model_deprecation_check"
)
def run_model_deprecation_check(self):
    """Explicit model deprecation sweep; writes JSON status artifact."""

    try:
        return asyncio.run(_async_run_check())
    except Exception as exc:  # noqa: BLE001 - fail-safe by design
        logger.exception("[model-watcher] daily check failed: %s", exc)
        return {"status": "error", "error": str(exc)}


async def _async_run_check():
    # Local import avoids a hard import of httpx / model_config at celery
    # worker startup for tasks that never run the watcher.
    from app.core.services.model_deprecation_watcher import check_models

    report = await check_models()
    artifact_path = _write_status_artifact(report)
    deprecated = report["summary"].get("deprecated_or_missing", 0)
    unreachable = len(report["provider_unreachable_providers"])
    logger.info(
        "[model-watcher] daily check complete: deprecated=%d unreachable_providers=%d artifact=%s",
        deprecated,
        unreachable,
        artifact_path,
    )
    return {
        "status": "ok",
        "deprecated": deprecated,
        "provider_unreachable_providers": report[
            "provider_unreachable_providers"
        ],
        "artifact": artifact_path,
    }


def _write_status_artifact(report: dict) -> str:
    path = os.path.abspath(STATUS_ARTIFACT_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = dict(report)
    payload["artifact_written_at"] = datetime.now(timezone.utc).isoformat()
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
    os.replace(tmp_path, path)  # atomic swap; readers never see partial json
    return path
