"""KAN-435 — backend DEBUG/INFO logs must not emit uploaded book body text.

Acceptance:
- Any log message at level INFO or below must contain only metadata
  (file name, size, SHA-256, UUIDs, counts, stage timing) when describing
  uploaded book content.
- A known marker injected into body text must be absent from captured
  stdout/log output after redaction.
"""

import io
import re
import sys

from app.core.services.text_utils import LogSanitizer


KAN435_MARKER = "KAN435_SECRET_MARKER_INJECT_REDACT"


def _capture_stdout(func, *args, **kwargs):
    """Run func and return everything written to stdout."""
    old_stdout = sys.stdout
    captured = io.StringIO()
    sys.stdout = captured
    try:
        func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout
    return captured.getvalue()


def test_log_sanitizer_redacts_full_body_text():
    body = f"Chapter One. It was the best of times, it was the worst of times. {KAN435_MARKER}"
    redacted = LogSanitizer.redact(body, label="page_text")
    assert KAN435_MARKER not in redacted
    assert "len=" in redacted
    assert body not in redacted


def test_log_sanitizer_preview_zero_max_len_redacts():
    body = f"Long uploaded book paragraph containing {KAN435_MARKER}"
    preview = LogSanitizer.preview(body, max_len=0, label="search_text")
    assert KAN435_MARKER not in preview
    assert f"len={len(body)}" in preview


def test_log_sanitizer_preview_short_max_len_keeps_prefix_only():
    body = f"abc {KAN435_MARKER} def"
    preview = LogSanitizer.preview(body, max_len=3, label="snippet")
    assert KAN435_MARKER not in preview
    assert "[+" in preview


def test_redaction_applied_through_stdout_print():
    """Simulate the patched file.py print sites: marker must not reach stdout."""
    body = f"Page text with {KAN435_MARKER}"

    def patched_site():
        print(f"[SIMPLE TOC] First 500 chars: {LogSanitizer.redact(body, label='page_text')}")
        print(f"[DEBUG TOC] Page 10 preview: {LogSanitizer.redact(body, label='page_text')}")

    stdout = _capture_stdout(patched_site)
    assert KAN435_MARKER not in stdout
    assert "len=" in stdout


def test_file_py_no_direct_content_prints():
    """Static guard: file.py must not contain direct text[:N] prints that leak body text."""
    from pathlib import Path

    file_py = Path(__file__).parent.parent / "app" / "core" / "services" / "file.py"
    source = file_py.read_text(encoding="utf-8")

    # Find print statements that reference text/content/matched_line and ensure they are wrapped in LogSanitizer.
    suspicious = []
    for line in source.splitlines():
        if "print(" not in line:
            continue
        if any(token in line for token in ["text[:", "content[:", "search_text[:", "matched_line", "repr(text"]):
            if "LogSanitizer" not in line:
                suspicious.append(line.strip())
    assert not suspicious, f"file.py still contains unredacted content print: {suspicious[:5]}"


def test_log_sanitizer_redacts_nested_dict():
    data = {
        "filename": "book.epub",
        "content": f"body {KAN435_MARKER}",
        "nested": {"text": f"nested {KAN435_MARKER}"},
        "list": [{"text": f"item {KAN435_MARKER}"}],
    }
    redacted = LogSanitizer.redact_mapping(data, allowed_keys={"filename"})
    assert KAN435_MARKER not in str(redacted)
    assert redacted["filename"] == "book.epub"
    assert "len=" in redacted["content"]
