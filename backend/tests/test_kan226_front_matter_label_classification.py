"""KAN-226: the product's own 'Front Matter' label must classify as front_matter.

The preview emitters set title="Front Matter" (file.py hierarchical/flat/recovery
paths) with content_type="front_matter", but the frontend save call posts
{title, content, summary, chapter_number} with NO content_type (BookUpload.tsx,
both branches). On trees carrying the GAP B save loop (staging lineage,
6b08a41/1e71b00), _resolve_content_type then re-derives the type with
_classify_spine_item, whose FRONT_MATTER_TITLES keyword set does not contain the
product's own label, so the row persists as a real chapter and consumes a
chapter number (observed at served f34bf5de: book d32bca30, 'Front Matter'
persisted chapter/1, duplicating Chapter 1).

The classifier-level tests run on every tree (dev and staging both define
_classify_spine_item). The resolve-level tests run only where GAP B exists and
SKIP nowhere silently: absence of _resolve_content_type on dev is reported as a
skip with the reason, because that machinery is staged, not dev, and the
defect's persistence surface is therefore staging-only.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("STRIPE_SECRET_KEY", "test-key-placeholder")
os.environ.setdefault("MAIL_FROM", "test@litinkai.dev")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")

import app.projects.models  # noqa: F401,E402
import app.plots.models  # noqa: F401,E402
from app.core.services.file import FileService  # noqa: E402


def _words(n: int) -> str:
    return " ".join(["word"] * n)


def make_service() -> FileService:
    return FileService()


HAS_RESOLVE = hasattr(FileService, "_resolve_content_type")


class TestFrontMatterLabelClassifier:
    def test_front_matter_label_classifies_front_matter(self):
        svc = make_service()
        for title in ("Front Matter", "front matter", "Front matter"):
            for n in (40, 357):
                got = svc._classify_spine_item(title, "", n, _words(n))
                assert got == "front_matter", (title, n, got)

    def test_real_chapter_titles_still_chapter(self):
        svc = make_service()
        for title in ("Chapter 1", "Chapter 17", "Chapter LI", "Complete Story"):
            got = svc._classify_spine_item(title, "", 3000, _words(3000))
            assert got == "chapter", (title, got)

    def test_known_front_matter_keywords_still_front_matter(self):
        svc = make_service()
        for title in ("Preface", "Introduction", "Dedication"):
            got = svc._classify_spine_item(title, "", 200, _words(200))
            assert got == "front_matter", (title, got)

    def test_known_back_matter_still_back_matter(self):
        svc = make_service()
        got = svc._classify_spine_item("Copyright", "", 50, _words(50))
        assert got in ("back_matter", "metadata"), got


@pytest.mark.skipif(
    not HAS_RESOLVE,
    reason="GAP B save loop (_resolve_content_type) is on the staging lineage, not dev",
)
class TestFrontMatterLabelResolve:
    def test_resolve_without_client_value_at_preview_size(self):
        svc = make_service()
        item = {"title": "Front Matter", "content": _words(357), "word_count": 357}
        assert svc._resolve_content_type(item) == "front_matter"

    def test_client_sent_content_type_is_honoured(self):
        svc = make_service()
        item = {
            "title": "Front Matter", "content": _words(357), "word_count": 357,
            "content_type": "front_matter",
        }
        assert svc._resolve_content_type(item) == "front_matter"
