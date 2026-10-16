"""
KAN-445 Regression Tests — type-0 page items in EPUB spine

Great Expectations reports 0 chapters because the real EPUB spine is mostly
ITEM_PAGETEXT/type-0 XHTML page fragments. The parser now treats those spine
entries as document text, admits page-fragment sets to aggregate
reconstruction, and accepts a representative aggregate result instead of
rejecting it solely because it has no numbered chapter headings.

These tests cover direct type-0 chapters plus the real-artifact aggregate path:
359 type-0 fragments in -> non-zero chapter output.
"""

import os

# Test-safe env BEFORE app imports (mirrors backend/tests/test_kan470_471_auth_error_hardening.py).
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY", "dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY_SECRET", "dummy")
for _k in [
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
    "REDIS_URL", "CELERY_BROKER_URL",
]:
    os.environ.setdefault(_k, "dummy" if "PORT" not in _k else "0")

import pytest
from app.core.services.file import FileService


def _long_filler(word_count: int = 80) -> str:
    """Generate a block of text long enough to pass substantial-content checks."""
    words_per_line = 10
    line_count = (word_count // words_per_line) + 2
    return "\n".join(
        [" ".join([f"content{i}"] * words_per_line) for i in range(line_count)]
    )


class FakeSpineItem:
    def __init__(self, uid: str, name: str, media_type: str, content: str):
        self.uid = uid
        self.media_type = media_type
        self._name = name
        self._content = content.encode("utf-8")

    def get_id(self):
        return self.uid

    def get_name(self):
        return self._name

    def get_type(self):
        return 0

    def get_content(self):
        return self._content


class FakeBook:
    def __init__(self, page_count: int):
        self.items = {}
        for idx in range(1, page_count + 1):
            self.items[f"page_{idx}"] = FakeSpineItem(
                f"page_{idx}",
                f"text/page_{idx}.xhtml",
                "application/xhtml+xml",
                f"<html><body><h1>Chapter {idx}</h1><p>{_long_filler(90)}</p></body></html>",
            )
        self.items["cover"] = FakeSpineItem(
            "cover", "images/cover.jpg", "image/jpeg", "not html"
        )
        self.items["style"] = FakeSpineItem(
            "style", "styles/book.css", "text/css", "body {}"
        )
        self.spine = [
            *[(f"page_{idx}", "yes") for idx in range(1, page_count + 1)],
            ("cover", "no"),
            ("style", "no"),
        ]

    def get_metadata(self, *_args):
        return []

    def get_item_with_id(self, item_id):
        return self.items.get(item_id)

    def get_items(self):
        return [self.items["cover"], self.items["style"]]


class FakeAggregateFragmentBook:
    """Fake the c16691 real-artifact shape: 359 type-0 XHTML fragments."""

    def __init__(self, page_count: int = 359):
        self.items = {}
        for idx in range(1, page_count + 1):
            self.items[f"page_{idx}"] = FakeSpineItem(
                f"page_{idx}",
                f"text/page_{idx}.xhtml",
                "application/xhtml+xml",
                self._fragment_html(idx),
            )
        self.spine = [(f"page_{idx}", "yes") for idx in range(1, page_count + 1)]

    @staticmethod
    def _fragment_html(idx: int) -> str:
        # Keep every fragment untitled to force the page-fragment aggregate path.
        lines = [f"This is ongoing narrative page {idx} line {line_no}." for line_no in range(1, 8)]
        if idx == 1:
            lines.extend(
                [
                    "Introduction",
                    "Opening material begins here and carries the book text forward.",
                ]
            )
        lines.append(" ".join([f"fragment{idx}"] * 100))
        return "<html><body><p>" + "</p><p>".join(lines) + "</p></body></html>"

    def get_metadata(self, *_args):
        return []

    def get_item_with_id(self, item_id):
        return self.items.get(item_id)

    def get_items(self):
        return list(self.items.values())


class TestTypeZeroPageItems:
    @pytest.fixture
    def fake_book_factory(self):
        def _make(page_count: int):
            return FakeBook(page_count)

        return _make

    @pytest.mark.asyncio
    async def test_one_type_zero_page_item(self, monkeypatch, fake_book_factory):
        monkeypatch.setattr(
            "app.core.services.file.epub.read_epub",
            lambda _file_path: fake_book_factory(2),
        )

        file_service = FileService()
        chapters = file_service.extract_epub_chapters("great-expectations.epub")

        assert len(chapters) == 2
        assert chapters[0]["title"] == "Chapter 1"
        assert chapters[-1]["title"] == "Chapter 2"
        assert all(ch["content_type"] == "chapter" for ch in chapters)

    @pytest.mark.asyncio
    async def test_ten_type_zero_page_items(self, monkeypatch, fake_book_factory):
        monkeypatch.setattr(
            "app.core.services.file.epub.read_epub",
            lambda _file_path: fake_book_factory(10),
        )

        file_service = FileService()
        chapters = file_service.extract_epub_chapters("great-expectations.epub")

        assert len(chapters) == 10
        assert chapters[0]["title"] == "Chapter 1"
        assert chapters[-1]["title"] == "Chapter 10"

    @pytest.mark.asyncio
    async def test_one_hundred_type_zero_page_items(
        self, monkeypatch, fake_book_factory
    ):
        monkeypatch.setattr(
            "app.core.services.file.epub.read_epub",
            lambda _file_path: fake_book_factory(100),
        )

        file_service = FileService()
        chapters = file_service.extract_epub_chapters("great-expectations.epub")

        assert len(chapters) == 100
        assert chapters[0]["title"] == "Chapter 1"
        assert chapters[-1]["title"] == "Chapter 100"

    @pytest.mark.asyncio
    async def test_three_hundred_fifty_nine_type_zero_fragments_accept_representative_aggregate(
        self, monkeypatch
    ):
        fake_book = FakeAggregateFragmentBook(359)
        monkeypatch.setattr(
            "app.core.services.file.epub.read_epub",
            lambda _file_path: fake_book,
        )

        assert len(fake_book.spine) == 359
        assert all(
            fake_book.items[item_id].get_type() == 0 for item_id, _linear in fake_book.spine
        )

        file_service = FileService()
        chapters = file_service.extract_epub_chapters("great-expectations.epub")
        chapter_items = [ch for ch in chapters if ch.get("content_type") == "chapter"]

        assert len(chapters) == 1
        assert len(chapter_items) == 1
        assert chapter_items[0]["number"] == "1"
        assert chapter_items[0]["title"] == "Introduction"
        assert chapter_items[0]["use_in_generation"] is True
        assert "page 359" in chapter_items[0]["content"]
