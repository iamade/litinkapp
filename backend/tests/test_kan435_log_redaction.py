"""KAN-435: backend DEBUG/INFO logs must never emit uploaded book body text.

The production regression is that `print()` calls inside `file.py` emit full
page/chapter text to stdout, which is captured by the container runtime at INFO
level. This test injects a known marker string into synthetic book content,
invokes the extraction paths that previously logged the text, and asserts the
marker never appears in captured stdout/stderr at INFO/DEBUG level.
"""

import ast
import inspect
import io
import re
import sys
import zipfile
from contextlib import redirect_stdout, redirect_stderr
from typing import Any

import pytest

from app.core.services.file import FileService
from app.core.services.text_utils import LogSanitizer

MARKER = "KAN435_REDACTION_MARKER_7f8a9b2c"


def _capture_prints(fn, *args, **kwargs) -> tuple[str, str]:
    """Run a callable and return everything written to stdout/stderr."""
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            import asyncio
            if asyncio.iscoroutinefunction(fn):
                asyncio.run(fn(*args, **kwargs))
            else:
                fn(*args, **kwargs)
        except Exception:
            # Some paths intentionally raise; we still want the log output.
            pass
    return out.getvalue(), err.getvalue()


def test_log_sanitizer_redacts_body_text() -> None:
    """LogSanitizer must never echo the actual text."""
    body = f"The quick brown fox jumps over the lazy dog. {MARKER} secret text."
    redacted = LogSanitizer.redact(body, label="book_text")
    assert MARKER not in redacted
    assert "secret text" not in redacted
    assert "len=" in redacted


def test_log_sanitizer_preview_redacts_by_default() -> None:
    """Preview with max_len=0 must fully redact."""
    body = f"Chapter one begins with {MARKER}."
    preview = LogSanitizer.preview(body, max_len=0, label="chapter_text")
    assert MARKER not in preview
    assert "len=" in preview


def test_log_sanitizer_preview_always_redacts_text() -> None:
    """preview must always be metadata-only, regardless of max_len."""
    body = f"Start of book. {MARKER} end of snippet." + " padding " * 100
    preview = LogSanitizer.preview(body, max_len=50, label="book_text")
    assert MARKER not in preview
    assert "REDACTED" in preview
    assert "Start of book" not in preview
    match = re.search(r"len=(\d+)", preview)
    assert match is not None
    assert int(match.group(1)) == len(body)


def _build_single_page_epub(path: str, title: str, body_html: str) -> None:
    container = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>"""
    package = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">kan435-test-id</dc:identifier>
    <dc:title>KAN-435 Test Book</dc:title><dc:language>en</dc:language>
  </metadata>
  <manifest><item id="page" href="page.xhtml" media-type="application/xhtml+xml"/></manifest>
  <spine><itemref idref="page"/></spine>
</package>"""
    page = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{title}</title></head>
<body><h1>{title}</h1>{body_html}</body></html>"""

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("OEBPS/content.opf", package)
        archive.writestr("OEBPS/page.xhtml", page)


def test_epub_extraction_path_does_not_leak_marker_in_prints(tmp_path) -> None:
    """Extracting an EPUB that contains the marker must not print the marker."""
    path = str(tmp_path / "marker.epub")
    body_html = f"<p>{MARKER} This page has body text that must not leak.</p>"
    _build_single_page_epub(path, "Page 1", body_html)

    fs = FileService()
    stdout, stderr = _capture_prints(fs.extract_epub_chapters, path)
    combined = stdout + stderr
    assert MARKER not in combined, "Marker leaked via print() in EPUB extraction"


def test_text_extraction_path_does_not_leak_marker_in_prints() -> None:
    """The fallback text parsing path must not print the marker either."""
    body = f"Chapter 1\n\n{MARKER} This is the secret body text. " * 200
    fs = FileService()
    stdout, stderr = _capture_prints(
        fs.extract_chapters, body, "entertainment"
    )
    combined = stdout + stderr
    assert MARKER not in combined, "Marker leaked via print() in text extraction"


def test_extract_chapters_with_new_flow_text_path_does_not_leak_marker() -> None:
    """The new-flow text path must not print the marker even when chunking."""
    body = f"{MARKER} " * 500 + "word " * 10000  # long enough to trigger chunking
    fs = FileService()

    async def run() -> None:
        await fs.extract_chapters_with_new_flow(
            content=body,
            book_type="entertainment",
            original_filename="marker-book.txt",
            storage_path="/tmp/marker-book.txt",
        )

    stdout, stderr = _capture_prints(run)
    combined = stdout + stderr
    assert MARKER not in combined, "Marker leaked via print() in new-flow extraction"


def test_file_service_print_calls_do_not_emit_user_text() -> None:
    """Inspect complete print-call AST nodes, including multiline f-strings."""
    from pathlib import Path

    source_path = Path(inspect.getsourcefile(FileService) or "")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    sensitive_names = {
        "chapter_title",
        "clean_title",
        "full_title",
        "special_title",
        "section_title",
        "normalized_title",
        "sub_title",
        "title",
        "title_str",
        "matched_line",
        "line",
        "content_preview",
        "search_text",
        "text",
        "reason",
        "groups",
    }
    sensitive_keys = {"content", "raw_title", "reasoning", "text", "title"}

    def is_sanitized(expr: ast.AST) -> bool:
        return any(
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "LogSanitizer"
            for node in ast.walk(expr)
        )

    def is_length_metadata(expr: ast.AST) -> bool:
        return (
            isinstance(expr, ast.Call)
            and isinstance(expr.func, ast.Name)
            and expr.func.id in {"len", "type"}
        )

    def contains_user_text(expr: ast.AST) -> bool:
        if is_sanitized(expr) or is_length_metadata(expr):
            return False
        for node in ast.walk(expr):
            if isinstance(node, ast.Name) and node.id in sensitive_names:
                return True
            if isinstance(node, ast.Subscript):
                key = node.slice
                if isinstance(key, ast.Constant) and key.value in sensitive_keys:
                    return True
            if (
                isinstance(node, ast.Attribute)
                and node.attr in {"content", "text", "title"}
            ):
                return True
        return False

    failures = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ):
            continue
        expressions = []
        for arg in node.args:
            if isinstance(arg, ast.JoinedStr):
                expressions.extend(
                    value.value
                    for value in arg.values
                    if isinstance(value, ast.FormattedValue)
                )
            elif not isinstance(arg, ast.Constant):
                expressions.append(arg)
        if any(contains_user_text(expr) for expr in expressions):
            failures.append(
                (node.lineno, (ast.get_source_segment(source, node) or "").replace("\n", " "))
            )

    assert not failures, f"Unsanitized user text in print calls: {failures[:10]}"


def test_redacted_output_contains_length_metadata() -> None:
    """Sanitized logs should still contain useful metadata like length/count."""
    body = f"{MARKER} some text" * 50
    redacted = LogSanitizer.redact(body, label="chapter_text")
    match = re.search(r"len=(\d+)", redacted)
    assert match is not None
    assert int(match.group(1)) == len(body)
