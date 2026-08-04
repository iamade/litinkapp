"""
KAN-50: Normalized cumulative-tier model catalog.

Wraps the existing per-modality ModelTier configs in `backend/app/core/model_config.py`
and exposes a single, modality-agnostic catalog. Enforces the invariant:

    FREE ⊆ BASIC ⊆ STANDARD ⊆ PREMIUM ⊆ PRO ⊆ ENTERPRISE

Every model exposed for a tier must also be exposed for every strictly-higher paid
tier of the same modality (cumulative entitlement). Provider credentials, subscription
state, and feature flags still gate runtime availability; this module does not enforce
runtime gating — `provider_router.py` and `model_fallback.py` do that.

Ade-approved direction locked 2026-07-16 (KAN-50 description, Ade 2026-07-16 14:35 MDT).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional, Tuple

from app.core.model_config import (
    AUDIO_MODEL_CONFIG,
    IMAGE_MODEL_CONFIG,
    SCRIPT_MODEL_CONFIG,
    UPSCALE_MODEL_CONFIG,
    VIDEO_MODEL_CONFIG,
    ModelConfig,
    ModelTier,
)

# Aliases: ticket description groups narration/TTS, dialogue/lip-sync, music/SFX
# under "audio"-family modalities. Map those to the AUDIO_MODEL_CONFIG table.
TTS_MODEL_CONFIG = AUDIO_MODEL_CONFIG
DIALOGUE_MODEL_CONFIG = AUDIO_MODEL_CONFIG
MUSIC_SFX_MODEL_CONFIG = AUDIO_MODEL_CONFIG
IMAGE_I2I_SINGLE_MODEL_CONFIG = IMAGE_MODEL_CONFIG  # single-ref i2i lives in IMAGE for now
IMAGE_I2I_SINGLE_VIDEO_MODEL_CONFIG = VIDEO_MODEL_CONFIG

logger = logging.getLogger(__name__)


# Ordered tier ladder — strictly increasing cost/capability.
TIER_LADDER: Tuple[ModelTier, ...] = (
    ModelTier.FREE,
    ModelTier.BASIC,
    ModelTier.STANDARD,
    ModelTier.PREMIUM,
    ModelTier.PROFESSIONAL,  # PRO in the ticket description
    ModelTier.ENTERPRISE,
)

# Map ticket-tier names → internal enum. "PRO" maps to PROFESSIONAL.
TICKET_TO_TIER: Dict[str, ModelTier] = {
    "FREE": ModelTier.FREE,
    "BASIC": ModelTier.BASIC,
    "STANDARD": ModelTier.STANDARD,
    "PREMIUM": ModelTier.PREMIUM,
    "PRO": ModelTier.PROFESSIONAL,
    "PROFESSIONAL": ModelTier.PROFESSIONAL,
    "ENTERPRISE": ModelTier.ENTERPRISE,
}


@dataclass(frozen=True)
class CatalogEntry:
    """One row in the normalized catalog."""

    modality: str
    tier: ModelTier
    primary: str
    fallbacks: Tuple[str, ...] = field(default_factory=tuple)
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    cost_per_1k_input: Optional[float] = None
    cost_per_1k_output: Optional[float] = None

    def all_models(self) -> Tuple[str, ...]:
        return (self.primary,) + tuple(self.fallbacks)


@dataclass(frozen=True)
class SelectionRequest:
    """User-supplied model selection that should win before defaults."""

    requested_provider: Optional[str] = None  # e.g. "anthropic"
    requested_model: Optional[str] = None     # prefixed ID, e.g. "anthropic/claude-sonnet-4.5"


@dataclass(frozen=True)
class ResolvedSelection:
    """Output of catalog resolution."""

    primary: str
    fallbacks: Tuple[str, ...]
    selected_via: str  # "user_explicit", "default_quality_first", "fallback_chain"
    reason: str


def _row_for(modality: str, tier: ModelTier) -> CatalogEntry:
    """Pull one ModelConfig row and normalize to a CatalogEntry."""
    table: Dict[str, Dict[ModelTier, ModelConfig]] = {
        "script": SCRIPT_MODEL_CONFIG,
        "image": IMAGE_MODEL_CONFIG,
        "image_i2i_single": IMAGE_I2I_SINGLE_MODEL_CONFIG,
        "image_i2i_single_video": IMAGE_I2I_SINGLE_VIDEO_MODEL_CONFIG,
        "video": VIDEO_MODEL_CONFIG,
        "audio": AUDIO_MODEL_CONFIG,
        "tts": TTS_MODEL_CONFIG,
        "narration": TTS_MODEL_CONFIG,
        "dialogue": DIALOGUE_MODEL_CONFIG,
        "music_sfx": MUSIC_SFX_MODEL_CONFIG,
        "upscale": UPSCALE_MODEL_CONFIG,
    }
    if modality not in table:
        raise KeyError(f"unknown modality: {modality!r}")
    cfg = table[modality].get(tier)
    if cfg is None:
        raise KeyError(f"no catalog row for {modality}/{tier.value}")
    return CatalogEntry(
        modality=modality,
        tier=tier,
        primary=cfg.primary,
        fallbacks=tuple(
            m for m in (cfg.fallback, cfg.fallback2, cfg.fallback3, getattr(cfg, "fallback4", None)) if m
        ),
        max_tokens=cfg.max_tokens,
        temperature=cfg.temperature,
        cost_per_1k_input=cfg.cost_per_1k_input,
        cost_per_1k_output=cfg.cost_per_1k_output,
    )


def get_catalog(modality: str, tier: str | ModelTier) -> CatalogEntry:
    """Public accessor used by `model_fallback.py` and the new selector."""
    if isinstance(tier, str):
        t = TICKET_TO_TIER.get(tier.upper())
        if t is None:
            raise KeyError(f"unknown tier name: {tier!r}")
        tier = t
    return _row_for(modality, tier)


# ----------------------------- cumulative invariant -----------------------------

def _all_models_in_or_below(modality: str, tier: ModelTier) -> FrozenSet[str]:
    """Union of every model exposed at `tier` or any strictly-lower tier."""
    seen: set[str] = set()
    for t in TIER_LADDER:
        if t == tier:
            break
        try:
            seen.update(_row_for(modality, t).all_models())
        except KeyError:
            continue
    return frozenset(seen)


def cumulative_entitlement_invariant(modality: str) -> Tuple[bool, List[str]]:
    """
    Validate FREE ⊆ BASIC ⊆ STANDARD ⊆ PREMIUM ⊆ PRO ⊆ ENTERPRISE for `modality`.

    Tiers not configured for this modality are skipped silently — only the tiers
    present in the per-modality catalog participate in the invariant. Returns
    (ok, violations). A violation is a string of the form
    "<lower_tier>::<model_id> not exposed at <higher_tier>".
    """
    violations: List[str] = []
    lower_union = frozenset()
    for tier in TIER_LADDER:
        try:
            row = _row_for(modality, tier)
        except KeyError:
            # tier not configured for this modality yet — treat as a gap, not a violation
            continue
        current = set(row.all_models())
        missing = lower_union - current
        for m in sorted(missing):
            for low_tier in TIER_LADDER:
                if low_tier == tier:
                    break
                low_row = None
                try:
                    low_row = _row_for(modality, low_tier)
                except KeyError:
                    continue
                if m in low_row.all_models():
                    violations.append(f"{low_tier.value}::{m} not exposed at {tier.value}")
                    break
        lower_union = lower_union | current
    return (not violations, violations)


# --------------------------- default routing policy ---------------------------

def provider_prefix(model_id: str) -> str:
    """Return provider prefix (e.g. 'anthropic' from 'anthropic/claude-sonnet-4.5')."""
    prefix, sep, _ = model_id.partition("/")
    return prefix if sep else "unknown"


def default_routing_for_tier(
    modality: str, tier: ModelTier, anthropic_priority: bool = False
) -> ResolvedSelection:
    """
    Quality-first automatic default for `modality`/`tier`.

    Default policy uses the existing primary from the per-modality table.
    If `anthropic_priority=True` (required for paid script/text per Ade
    2026-07-16 direction), and the row has an Anthropic entry anywhere in
    primary+fallbacks, prefer the strongest Anthropic option.
    """
    row = _row_for(modality, tier)
    chosen_primary = row.primary
    chosen_fallbacks = list(row.fallbacks)
    reason = "primary from per-modality table"

    if anthropic_priority and modality == "script" and tier != ModelTier.FREE:
        for m in row.all_models():
            if provider_prefix(m) == "anthropic":
                chosen_primary = m
                chosen_fallbacks = [
                    x for x in row.all_models() if x != chosen_primary
                ]
                reason = "Anthropic high-priority per Ade 2026-07-16"
                break

    return ResolvedSelection(
        primary=chosen_primary,
        fallbacks=tuple(chosen_fallbacks),
        selected_via="default_quality_first",
        reason=reason,
    )


# ------------------------------- explicit selection -------------------------------

def resolve_selection(
    modality: str,
    tier: ModelTier,
    selection: SelectionRequest,
) -> ResolvedSelection:
    """
    Resolution order (Ade 2026-07-16 §2 + §3):

      1. If user explicitly requested a model and it's in their tier catalog, use it
         (`requested_provider`/`requested_model`) — `selected_via=user_explicit`.
      2. Otherwise fall back to `default_routing_for_tier(...)`.

    `requested_model` MUST appear in the tier catalog when supplied; otherwise we
    raise `ValueError` rather than silently substitute.
    """
    row = _row_for(modality, tier)
    catalog_models = set(row.all_models())

    if selection.requested_model:
        if selection.requested_provider:
            wanted = f"{selection.requested_provider}/{selection.requested_model}"
        else:
            # Allow passing fully-prefixed IDs in `requested_model`.
            wanted = selection.requested_model
            if "/" not in wanted:
                raise ValueError(
                    "requested_model without provider prefix and no requested_provider"
                )

        if wanted not in catalog_models:
            raise ValueError(
                f"requested model {wanted!r} not in tier {tier.value} catalog for {modality}"
            )

        fallbacks = tuple(m for m in row.all_models() if m != wanted)
        return ResolvedSelection(
            primary=wanted,
            fallbacks=fallbacks,
            selected_via="user_explicit",
            reason="requested_provider/requested_model honored",
        )

    return default_routing_for_tier(
        modality, tier, anthropic_priority=(modality == "script" and tier != ModelTier.FREE)
    )


__all__ = [
    "TIER_LADDER",
    "TICKET_TO_TIER",
    "CatalogEntry",
    "SelectionRequest",
    "ResolvedSelection",
    "get_catalog",
    "cumulative_entitlement_invariant",
    "default_routing_for_tier",
    "resolve_selection",
    "provider_prefix",
]
