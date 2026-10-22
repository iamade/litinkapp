"""Focused unit tests for the explicitly-confirmed support password reset script."""
import ast
import asyncio
import builtins
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
SCRIPT = BACKEND / "reset_support_pw.py"
ARGON2_LITERAL = re.compile(r"\$argon2(?:id|i|d)\$[^\s'\"]+")
RUNTIME_SENTINEL = "synthetic-runtime-password-sentinel"
HASH_SENTINEL = "synthetic-hash-sentinel"
OPERATION_SENTINEL = "synthetic-operation-sentinel"
GENERIC_FAILURE = "Support password reset failed."


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
        if self.recorder["failure"] == "exec":
            raise RuntimeError(OPERATION_SENTINEL)
        self.recorder["executed"].append(statement)
        return types.SimpleNamespace(rowcount=1)

    async def commit(self):
        if self.recorder["failure"] == "commit":
            raise RuntimeError(OPERATION_SENTINEL)
        self.recorder["commits"] += 1


class FakeSessionFactory:
    def __init__(self, recorder):
        self.recorder = recorder

    def __call__(self):
        self.recorder["factory_calls"] += 1
        return FakeSession(self.recorder)


def fake_modules(monkeypatch, failure=None):
    recorder = {
        "failure": failure,
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
        if failure == "hash":
            raise RuntimeError(f"{RUNTIME_SENTINEL}:{HASH_SENTINEL}")
        recorder["hash_inputs"].append(value)
        return "fake-hash-output"

    def fake_text(query):
        statement = Statement(query)
        recorder["statements"].append(statement)
        return statement

    if failure != "import":
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
    return recorder


def load_script(monkeypatch, failure=None):
    """Load only against fake app/DB modules; never import the real app."""
    recorder = fake_modules(monkeypatch, failure)
    module_name = "kan499_reset_support_pw_under_test"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, recorder


def load_without_app(monkeypatch):
    """Import safely while asserting no app package is imported at module load."""
    for name in tuple(sys.modules):
        if name == "app" or name.startswith("app."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    calls = []
    original_import = builtins.__import__

    def block_app_import(name, *args, **kwargs):
        if name == "app" or name.startswith("app."):
            calls.append(name)
            raise AssertionError("app import attempted before an approved gate")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_app_import)
    module_name = "kan499_reset_support_pw_without_app"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, calls


def run_main(monkeypatch, module, args, password):
    monkeypatch.setattr(sys, "argv", ["reset_support_pw.py", *args])
    if password is None:
        monkeypatch.delenv("SUPPORT_PW_RESET_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("SUPPORT_PW_RESET_PASSWORD", password)
    return asyncio.run(module.main())


def captured_output(capsys):
    captured = capsys.readouterr()
    return captured.out + captured.err


def test_baseline_static_proves_script_absent_before_harvest():
    """A graft on the clean base fails this positive static availability assertion."""
    assert SCRIPT.is_file()
    assert not bool(ARGON2_LITERAL.search(SCRIPT.read_text())), "argon2 literal syntax detected"


def test_import_and_help_need_no_app_or_database_configuration(monkeypatch, capsys):
    monkeypatch.delenv("SUPPORT_PW_RESET_PASSWORD", raising=False)
    module, calls = load_without_app(monkeypatch)
    assert module.main
    assert calls == []
    monkeypatch.setattr(sys, "argv", ["reset_support_pw.py", "--help"])
    with pytest.raises(SystemExit) as exit_info:
        asyncio.run(module.main())
    captured = captured_output(capsys)
    assert exit_info.value.code == 0
    assert calls == []
    assert "--confirm" in captured


def test_without_confirm_fails_before_any_session_use(monkeypatch, capsys):
    module, recorder = load_script(monkeypatch)
    result = run_main(monkeypatch, module, [], RUNTIME_SENTINEL)
    captured = captured_output(capsys)
    assert result != 0
    assert recorder["factory_calls"] == 0
    assert recorder["entered"] == 0
    assert recorder["executed"] == []
    assert recorder["commits"] == 0
    assert RUNTIME_SENTINEL not in captured


@pytest.mark.parametrize("password", [None, "", "   "])
def test_missing_or_blank_runtime_password_fails_before_connection(monkeypatch, capsys, password):
    module, recorder = load_script(monkeypatch)
    result = run_main(monkeypatch, module, ["--confirm"], password)
    captured = captured_output(capsys)
    assert result != 0
    assert recorder["factory_calls"] == 0
    assert recorder["entered"] == 0
    assert recorder["executed"] == []
    assert recorder["commits"] == 0
    assert HASH_SENTINEL not in captured


def test_confirmed_runtime_password_hashes_and_updates_exact_support_account(monkeypatch, capsys):
    module, recorder = load_script(monkeypatch)
    result = run_main(monkeypatch, module, ["--confirm"], RUNTIME_SENTINEL)
    captured = captured_output(capsys)
    assert result == 0
    assert recorder["hash_inputs"] == [RUNTIME_SENTINEL]
    assert recorder["factory_calls"] == 1
    assert recorder["entered"] == 1
    assert recorder["exited"] == 1
    assert recorder["commits"] == 1
    assert len(recorder["executed"]) == 1
    statement = recorder["executed"][0]
    query = " ".join(statement.query.split()).lower()
    assert query.startswith('update "user" set')
    assert query.count(" where ") == 1
    assert "where email = :e" in query
    assert statement.params == {"h": "fake-hash-output", "e": "support@litinkai.com"}
    assert '"--email"' not in SCRIPT.read_text()
    assert RUNTIME_SENTINEL not in captured
    assert HASH_SENTINEL not in captured


@pytest.mark.parametrize("failure", ["import", "hash", "exec", "commit"])
def test_operational_failures_are_generic_and_do_not_disclose_sentinels(monkeypatch, capsys, failure):
    module, recorder = load_script(monkeypatch, failure=failure)
    try:
        result = run_main(monkeypatch, module, ["--confirm"], RUNTIME_SENTINEL)
    except Exception:
        result = None
    captured = captured_output(capsys)
    assert result == 1
    assert captured == GENERIC_FAILURE + "\n"
    assert RUNTIME_SENTINEL not in captured
    assert HASH_SENTINEL not in captured
    assert OPERATION_SENTINEL not in captured
    assert "updated " not in captured
    if failure in {"import", "hash"}:
        assert recorder["factory_calls"] == 0
    if failure == "exec":
        assert recorder["commits"] == 0


def test_main_entry_hash_failure_is_generic_without_traceback(tmp_path):
    (tmp_path / "app" / "auth").mkdir(parents=True)
    (tmp_path / "app" / "core").mkdir(parents=True)
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "auth" / "__init__.py").write_text("")
    (tmp_path / "app" / "core" / "__init__.py").write_text("")
    (tmp_path / "app" / "auth" / "utils.py").write_text(
        "def generate_password_hash(value):\n    raise RuntimeError('synthetic-hash-sentinel')\n"
    )
    (tmp_path / "app" / "core" / "database.py").write_text("async_session = None\n")
    (tmp_path / "sqlalchemy.py").write_text("def text(query):\n    return query\n")
    command = (
        "import runpy; "
        f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')"
    )
    environment = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(tmp_path), "SUPPORT_PW_RESET_PASSWORD": RUNTIME_SENTINEL}
    completed = subprocess.run(
        [sys.executable, "-c", command, "--confirm"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    captured = completed.stdout + completed.stderr
    assert completed.returncode == 1
    assert captured == GENERIC_FAILURE + "\n"
    assert RUNTIME_SENTINEL not in captured
    assert HASH_SENTINEL not in captured
    assert "Traceback" not in captured


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
        and any(item.value == "__main__" for item in node.test.comparators if isinstance(item, ast.Constant))
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
