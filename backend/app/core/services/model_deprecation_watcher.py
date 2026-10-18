"""
KAN-448: Model deprecation watcher.

Inventories every model identifier referenced by the backend model
configuration (script / image / i2i / video / audio / tts / upscale) and
checks each one against an explicitly supplied provider catalog.

Design notes
------------
* Strictly offline: this module never calls provider APIs. Callers inject
  provider-catalog fetchers; without them, providers are marked unavailable.
* Fail-safe: an unavailable or failed fetcher for a provider marks that
  provider's models as "unknown" instead of crashing or flagging them
  deprecated. The check as a whole always returns a report.
* Provider catalog fetchers are plain async callables returning either a set
  of known model ids or ``None`` when the catalog could not be retrieved.
  Tests substitute these callables (no network in unit tests).
* The report is a plain dict so the celery task can JSON-serialize it into
  a queryable status artifact on disk.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple

from app.core.model_config import (
    AUDIO_MODEL_CONFIG,
    IMAGE_I2I_MULTI_MODEL_CONFIG,
    IMAGE_I2I_SINGLE_MODEL_CONFIG,
    IMAGE_MODEL_CONFIG,
    SCRIPT_MODEL_CONFIG,
    TTS_TIER_CONFIG,
    UPSCALE_MODEL_CONFIG,
    VIDEO_MODEL_CONFIG,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

#: service_type -> tier -> ModelConfig registry.  Uses the same maps that
#: ``get_model_config`` consults, plus the i2i single/multi variants which
#: are part of the generation config surface.
CONFIG_REGISTRY: Dict[str, Any] = {
    "script": SCRIPT_MODEL_CONFIG,
    "image": IMAGE_MODEL_CONFIG,
    "image_i2i_single": IMAGE_I2I_SINGLE_MODEL_CONFIG,
    "image_i2i_multi": IMAGE_I2I_MULTI_MODEL_CONFIG,
    "video": VIDEO_MODEL_CONFIG,
    "audio": AUDIO_MODEL_CONFIG,
    "tts": TTS_TIER_CONFIG,
    "upscale": UPSCALE_MODEL_CONFIG,
}

#: Providers whose catalogs the watcher can live-check today.  Any other
#: prefix (ollama, featherless, minimax, modelslab-by-bare-id, etc.) is
#: reported as ``not_checked`` so the report remains honest about coverage.
CHECKABLE_PROVIDERS: Tuple[str, ...] = ("openai", "google", "anthropic")


@dataclass
class ModelRef:
    """One configured model occurrence."""

    service_type: str
    tier: str
    slot: str  # primary | fallback | fallback2 | ...
    model_id: str
    provider: str  # prefix before first '/', or "" when there is none


def inventory_models() -> List[ModelRef]:
    """Collect every configured model id across the registry."""

    refs: List[ModelRef] = []
    slot_names = ["primary", "fallback"] + [f"fallback{i}" for i in range(2, 14)]

    for service_type, tier_map in CONFIG_REGISTRY.items():
        for tier, config in tier_map.items():
            tier_value = getattr(tier, "value", str(tier))
            for slot in slot_names:
                model_id = getattr(config, slot, None)
                if not model_id:
                    continue
                provider = model_id.split("/", 1)[0] if "/" in model_id else ""
                refs.append(
                    ModelRef(
                        service_type=service_type,
                        tier=tier_value,
                        slot=slot,
                        model_id=model_id,
                        provider=provider,
                    )
                )
    return refs


# ---------------------------------------------------------------------------
# Provider catalog fetchers (fail-safe)
# ---------------------------------------------------------------------------

CatalogFetcher = Callable[[], Awaitable[Optional[Set[str]]]]


async def fetch_openai_catalog() -> Optional[Set[str]]:
    """Offline default; inject a catalog fetcher to check OpenAI models."""
    return None


async def fetch_google_catalog() -> Optional[Set[str]]:
    """Offline default; inject a catalog fetcher to check Google models."""
    return None


async def fetch_anthropic_catalog() -> Optional[Set[str]]:
    """Offline default; inject a catalog fetcher to check Anthropic models."""
    return None


DEFAULT_FETCHERS: Dict[str, CatalogFetcher] = {
    "openai": fetch_openai_catalog,
    "google": fetch_google_catalog,
    "anthropic": fetch_anthropic_catalog,
}


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------

STATUS_CURRENT = "current"
STATUS_DEPRECATED = "deprecated_or_missing"
STATUS_PROVIDER_UNREACHABLE = "provider_unreachable"
STATUS_NOT_CHECKED = "not_checked"


async def check_models(
    fetchers: Optional[Dict[str, CatalogFetcher]] = None,
) -> Dict[str, Any]:
    """Run one deprecation sweep.

    ``fetchers`` maps provider prefix -> async callable returning the set of
    known model ids or None.  Injectable for tests.
    """

    fetchers = fetchers if fetchers is not None else DEFAULT_FETCHERS
    refs = inventory_models()

    # Fetch each checkable provider catalog once.
    catalogs: Dict[str, Optional[Set[str]]] = {}
    for provider in CHECKABLE_PROVIDERS:
        fetch = fetchers.get(provider)
        if fetch is None:
            catalogs[provider] = None
            continue
        try:
            catalogs[provider] = await fetch()
        except Exception as exc:  # noqa: BLE001 - fetcher bug must not crash sweep
            logger.warning(
                "[model-watcher] catalog fetcher for %s raised: %s", provider, exc
            )
            catalogs[provider] = None

    entries: List[Dict[str, Any]] = []
    for ref in refs:
        if ref.provider not in CHECKABLE_PROVIDERS:
            status = STATUS_NOT_CHECKED
        else:
            catalog = catalogs.get(ref.provider)
            if catalog is None:
                status = STATUS_PROVIDER_UNREACHABLE
            else:
                # Compare on the bare model id (segment after first '/').
                bare_id = ref.model_id.split("/", 1)[-1]
                status = (
                    STATUS_CURRENT if bare_id in catalog else STATUS_DEPRECATED
                )
        entries.append(
            {
                "service_type": ref.service_type,
                "tier": ref.tier,
                "slot": ref.slot,
                "model_id": ref.model_id,
                "provider": ref.provider,
                "status": status,
            }
        )

    summary: Dict[str, int] = {}
    for entry in entries:
        summary[entry["status"]] = summary.get(entry["status"], 0) + 1

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "deprecated": [
            e for e in entries if e["status"] == STATUS_DEPRECATED
        ],
        "provider_unreachable_providers": [
            p for p, cat in catalogs.items() if cat is None
        ],
        "entries": entries,
    }

    deprecated_count = summary.get(STATUS_DEPRECATED, 0)
    unreachable_count = summary.get(STATUS_PROVIDER_UNREACHABLE, 0)
    if deprecated_count:
        logger.warning(
            "[model-watcher] %d configured model refs deprecated/missing: %s",
            deprecated_count,
            [e["model_id"] for e in report["deprecated"]],
        )
    else:
        logger.info("[model-watcher] all checkable configured models current")
    if unreachable_count:
        logger.info(
            "[model-watcher] %d refs unchecked (provider unreachable): %s",
            unreachable_count,
            report["provider_unreachable_providers"],
        )
    return report
