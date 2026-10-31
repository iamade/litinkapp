"""
KAN-445 regression — inline/garbled heading admission (LC ruling 2026-10-31 08:05Z).

The byte-exact Great Expectations scan (sha256 7a6e741a...) renders chapter
headings INLINE after running headers ("GREAT EXPECTATIONS. CHAPTER I. My
father's...") with OCR-garbled numerals (VL, VIL, XVIIL). The line-anchored
explicit-sequence fallback finds 0, the semantic gate sees 1 chapter-like
item, and extract_epub_chapters returns [] -> clean 500. The admission path
must admit these headings. Fix admission, not error handling.
"""

import os

os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "***")
os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_dummy")
for _k in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
           "REDIS_URL", "CELERY_BROKER_URL"]:
    os.environ.setdefault(_k, "dummy" if "PORT" not in _k else "0")

import hashlib
import pytest

FIXTURE = "/opt/openclaw/fixtures/litinkai/realbooks/great-expectations.epub"
FIXTURE_SHA = "7a6e741a6ea8762a8f0a837526f0cf8fecda92d0384b54f53565c2f531590791"


def _fixture_ok() -> bool:
    try:
        with open(FIXTURE, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest() == FIXTURE_SHA
    except OSError:
        return False


@pytest.mark.skipif(not _fixture_ok(), reason="byte-exact fixture not present")
def test_great_expectations_inline_headings_admitted():
    from app.core.services.file import FileService

    chapters = FileService().extract_epub_chapters(FIXTURE)
    assert chapters, "KAN-445: extraction returned 0 chapters for the real scan"
    chapter_items = [c for c in chapters if c.get("content_type") == "chapter"]
    assert len(chapter_items) >= 10, (
        f"expected >=10 admitted chapters from inline headings, got {len(chapter_items)}"
    )
    numbers = [c.get("number") for c in chapter_items]
    assert str(numbers[0]) == "1"


@pytest.mark.skipif(not _fixture_ok(), reason="byte-exact fixture not present")
def test_great_expectations_inline_headings_not_degraded():
    """Admitted chapters are real heading-split content, not page fragments."""
    from app.core.services.file import FileService

    chapters = FileService().extract_epub_chapters(FIXTURE)
    chapter_items = [c for c in chapters if c.get("content_type") == "chapter"]
    assert chapter_items
    total = sum(len((c.get("content") or "").strip()) for c in chapter_items)
    assert total > 50000, f"admitted chapters carry no real body text ({total} chars)"
