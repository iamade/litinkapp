"""Focused unit tests for the explicitly-confirmed support password reset script."""
import argparse
import ast
import asyncio
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import types

import pytest

BASE = "2975d2e9ba1c687825f59c05dc9ff963973a4f4d"
BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
SCRIPT = BACKEND / "reset_support_pw.py"
ARGON2_LITERAL = re.compile(r"\$argon2(?:id|i|d)\$[^\s'\"]+")


class Statement:
    def __init__(self, query):
        self.query = query
        self.params = {}

    def bindparams(self, **kwargs):
        self.params.update(kwargs)
        return self


class FakeSession:
    def __init__(self, recorder):
        self.recorder = recorder

    async def __aenter__(self):
        self.recorder["entered"] += 1
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.recorder["exited"] += 1

    async def exec(self, statement):
        self.recorder["executed"].append(statement)
        return types.SimpleNamespace(rowcount=1)

    async def commit(self):
        self.recorder["commits"] += 1


class FakeSessionFactory:
    def __init__(self, recorder):
        self.recorder = recorder

    def __call__(self):
        self.recorder["factory_calls"] += 1
        return FakeSession(self.recorder)


def load_script(monkeypatch):
    """Load only against fake app/DB modules; never import the real app."""
    recorder = {
        "factory_calls": 0,
        "entered": 0,
        "exited": 0,
        "executed": [],
        "commits": 0,
        "hash_inputs": [],
        "statements": [],
    }

    app = types.ModuleType("app")
    auth = types.ModuleType("app.auth")
    auth_utils = types.ModuleType("app.auth.utils")
    core = types.ModuleType("app.core")
    database = types.ModuleType("app.core.database")
    sqlalchemy = types.ModuleType("sqlalchemy")

    def fake_hash(value):
        recorder["hash_inputs"].append(value)
        return "fake-hash-output"

    def fake_text(query):
        statement = Statement(query)
        recorder["statements"].append(statement)
        return statement

    auth_utils.generate_password_hash = fake_hash
    database.async_session = FakeSessionFactory(recorder)
    sqlalchemy.text = fake_text
    app.auth = auth
    app.core = core
    auth.utils = auth_utils
    core.database = database

    for name, module in {
        "app": app,
        "app.auth": auth,
        "app.auth.utils": auth_utils,
        "app.core": core,
        "app.core.database": database,
        "sqlalchemy": sqlalchemy,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_name = "kan499_reset_support_pw_under_test"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, recorder


def run_main(monkeypatch, module, args, password):
    monkeypatch.setattr(sys, "argv", ["reset_support_pw.py", *args])
    if password is None:
        monkeypatch.delenv("SUPPORT_PW_RESET_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("SUPPORT_PW_RESET_PASSWORD", password)
    return asyncio.run(module.main())


def test_baseline_static_proves_script_absent_before_harvest():
    """A graft on the clean base fails this positive static availability assertion."""
    assert SCRIPT.is_file()
    assert not bool(ARGON2_LITERAL.search(SCRIPT.read_text())), "argon2 literal syntax detected"


def test_import_is_safe_without_runtime_env_or_real_app(monkeypatch):
    monkeypatch.delenv("SUPPORT_PW_RESET_PASSWORD", raising=False)
    module, recorder = load_script(monkeypatch)
    assert module.main
    assert recorder["factory_calls"] == 0
    assert recorder["entered"] == 0
    assert recorder["executed"] == []
    assert recorder["commits"] == 0


def test_without_confirm_fails_before_any_session_use(monkeypatch, capsys):
    module, recorder = load_script(monkeypatch)
    runtime_value = "deterministic-test-runtime-password"
    result = run_main(monkeypatch, module, [], runtime_value)
    captured_result = capsys.readouterr()
    captured = captured_result.out + captured_result.err
    assert result != 0
    assert recorder["factory_calls"] == 0
    assert recorder["entered"] == 0
    assert recorder["executed"] == []
    assert recorder["commits"] == 0
    assert runtime_value not in captured


@pytest.mark.parametrize("password", [None, "   "])
def test_missing_or_blank_runtime_password_fails_before_connection(monkeypatch, capsys, password):
    module, recorder = load_script(monkeypatch)
    result = run_main(monkeypatch, module, ["--confirm"], password)
    captured_result = capsys.readouterr()
    captured = captured_result.out + captured_result.err
    assert result != 0
    assert recorder["factory_calls"] == 0
    assert recorder["entered"] == 0
    assert recorder["executed"] == []
    assert recorder["commits"] == 0
    assert "fake-hash-output" not in captured
    if password:
        assert password not in captured


def test_confirmed_runtime_password_hashes_and_updates_only_support_account(monkeypatch, capsys):
    module, recorder = load_script(monkeypatch)
    runtime_value = "deterministic-test-runtime-password"
    result = run_main(monkeypatch, module, ["--confirm"], runtime_value)
    captured_result = capsys.readouterr()
    captured = captured_result.out + captured_result.err
    assert result == 0

    assert recorder["hash_inputs"] == [runtime_value]
    assert recorder["factory_calls"] == 1
    assert recorder["entered"] == 1
    assert recorder["exited"] == 1
    assert recorder["commits"] == 1
    assert len(recorder["executed"]) == 1
    assert len(recorder["statements"]) == 1
    statement = recorder["executed"][0]
    query = " ".join(statement.query.split()).lower()
    assert query.startswith('update "user" set')
    assert query.count(" where ") == 1
    assert "where email = :e" in query
    assert set(statement.params) == {"h", "e"}
    assert statement.params["h"] == "fake-hash-output"
    assert re.fullmatch(r"support@[A-Za-z0-9.-]+", statement.params["e"])
    assert '"--email"' not in SCRIPT.read_text()
    assert runtime_value not in captured
    assert "fake-hash-output" not in captured


def test_entrypoint_guard_and_hash_hygiene_cover_entire_script():
    source = SCRIPT.read_text()
    tree = ast.parse(source)
    guards = [
        node
        for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        and any(isinstance(item, ast.Constant) and item.value == "__main__" for item in node.test.comparators)
    ]
    assert len(guards) == 1
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "asyncio"
        and node.func.attr == "run"
        for node in ast.walk(guards[0])
    )
    assert ARGON2_LITERAL.search(source) is None
