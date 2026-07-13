"""Backward-compatible import shim for the renamed script model router."""

from app.core.services.script_model_router import ModelTier, ScriptModelRouter

OpenRouterService = ScriptModelRouter

__all__ = ["ModelTier", "OpenRouterService", "ScriptModelRouter"]
