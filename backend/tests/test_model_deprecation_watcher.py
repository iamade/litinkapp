"""
KAN-448: Model deprecation watcher tests.

Three required scenarios, all with mocked provider catalogs (no network):

1. deprecated-detected      — catalog lacks one configured model -> flagged
2. all-current              — catalog contains every configured model -> none flagged
3. provider-unreachable     — fetcher returns None -> fail-safe, nothing flagged
"""

import asyncio

import pytest

from app.core.services import model_deprecation_watcher as watcher


def _run_check(fetchers):
    return asyncio.run(watcher.check_models(fetchers=fetchers))


def _checkable_entries(report):
    return [
        e for e in report["entries"] if e["provider"] in watcher.CHECKABLE_PROVIDERS
    ]


class TestModelDeprecationWatcher:
    def test_inventory_covers_registry(self):
        """Every registry config contributes at least one model ref."""
        refs = watcher.inventory_models()
        service_types = {r.service_type for r in refs}
        assert set(watcher.CONFIG_REGISTRY.keys()) <= service_types
        # sanity: script config alone has many models
        script_refs = [r for r in refs if r.service_type == "script"]
        assert len(script_refs) > 10

    def test_default_fetchers_are_offline(self):
        """The default sweep is safe without provider clients or credentials."""
        report = _run_check(None)

        assert report["summary"].get(watcher.STATUS_DEPRECATED, 0) == 0
        assert sorted(report["provider_unreachable_providers"]) == sorted(
            watcher.CHECKABLE_PROVIDERS
        )

    def test_all_current(self):
        """Scenario 2: every checkable configured model exists in catalogs."""
        refs = watcher.inventory_models()
        # Build catalogs containing every configured bare model id per provider
        catalogs = {p: set() for p in watcher.CHECKABLE_PROVIDERS}
        for r in refs:
            if r.provider in catalogs:
                catalogs[r.provider].add(r.model_id.split("/", 1)[-1])

        async def make_fetch(values):
            return set(values)

        fetchers = {}
        for provider, values in catalogs.items():
            # bind loop var
            async def _f(values=values):
                return set(values)

            fetchers[provider] = _f

        report = _run_check(fetchers)

        assert report["summary"].get(watcher.STATUS_DEPRECATED, 0) == 0
        assert report["deprecated"] == []
        assert report["provider_unreachable_providers"] == []
        for entry in _checkable_entries(report):
            assert entry["status"] == watcher.STATUS_CURRENT

    def test_deprecated_detected(self):
        """Scenario 1: a configured model absent from its provider catalog
        is flagged deprecated_or_missing in the report."""
        refs = watcher.inventory_models()
        catalogs = {p: set() for p in watcher.CHECKABLE_PROVIDERS}
        for r in refs:
            if r.provider in catalogs:
                catalogs[r.provider].add(r.model_id.split("/", 1)[-1])

        # Remove one known configured model from the openai catalog
        victim = None
        for r in refs:
            if r.provider == "openai":
                victim = r.model_id.split("/", 1)[-1]
                break
        assert victim is not None, "expected at least one openai/* model in config"
        catalogs["openai"].discard(victim)

        fetchers = {}
        for provider, values in catalogs.items():

            async def _f(values=values):
                return set(values)

            fetchers[provider] = _f

        report = _run_check(fetchers)

        assert report["summary"].get(watcher.STATUS_DEPRECATED, 0) >= 1
        deprecated_ids = {e["model_id"] for e in report["deprecated"]}
        assert f"openai/{victim}" in deprecated_ids
        # nothing unreachable in this scenario
        assert report["provider_unreachable_providers"] == []

    def test_provider_unreachable_failsafe(self):
        """Scenario 3: provider catalog fetch fails (returns None) -> refs are
        marked provider_unreachable, NOT deprecated, and the check completes."""

        async def _unreachable():
            return None

        fetchers = {p: _unreachable for p in watcher.CHECKABLE_PROVIDERS}

        report = _run_check(fetchers)

        assert report["summary"].get(watcher.STATUS_DEPRECATED, 0) == 0
        assert report["deprecated"] == []
        assert sorted(report["provider_unreachable_providers"]) == sorted(
            watcher.CHECKABLE_PROVIDERS
        )
        for entry in _checkable_entries(report):
            assert entry["status"] == watcher.STATUS_PROVIDER_UNREACHABLE

    def test_fetcher_exception_is_contained(self):
        """A fetcher that raises must not crash the sweep."""

        async def _boom():
            raise RuntimeError("network blew up")

        fetchers = {p: _boom for p in watcher.CHECKABLE_PROVIDERS}
        report = _run_check(fetchers)

        assert report["summary"].get(watcher.STATUS_DEPRECATED, 0) == 0
        assert sorted(report["provider_unreachable_providers"]) == sorted(
            watcher.CHECKABLE_PROVIDERS
        )

    def test_report_shape(self):
        """Report carries the queryable fields the artifact depends on."""

        async def _none():
            return None

        report = _run_check({p: _none for p in watcher.CHECKABLE_PROVIDERS})

        assert "checked_at" in report
        assert isinstance(report["summary"], dict)
        assert isinstance(report["entries"], list)
        assert isinstance(report["deprecated"], list)
        assert isinstance(report["provider_unreachable_providers"], list)
        for entry in report["entries"]:
            for key in ("service_type", "tier", "slot", "model_id", "provider", "status"):
                assert key in entry


class TestWatcherTaskArtifact:
    def test_status_artifact_written(self, tmp_path, monkeypatch):
        """The celery task writes a JSON status artifact to the configured path."""

        from app.tasks import model_watcher_tasks

        artifact = tmp_path / "model_deprecation_status.json"
        monkeypatch.setattr(
            model_watcher_tasks, "STATUS_ARTIFACT_PATH", str(artifact)
        )

        async def _none():
            return None

        # Force the fetchers used inside the task to be unreachable (no network).
        monkeypatch.setattr(
            watcher,
            "DEFAULT_FETCHERS",
            {p: _none for p in watcher.CHECKABLE_PROVIDERS},
        )

        result = model_watcher_tasks.run_model_deprecation_check.run()
        assert result["status"] == "ok"
        assert artifact.exists()

        import json

        payload = json.loads(artifact.read_text())
        assert "checked_at" in payload
        assert "artifact_written_at" in payload
        assert payload["summary"].get(watcher.STATUS_DEPRECATED, 0) == 0
