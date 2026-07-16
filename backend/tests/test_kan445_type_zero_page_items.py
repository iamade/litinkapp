"""
KAN-445 Regression Tests — type-0 page items in EPUB spine

Great Expectations reports 0 chapters because the spine contains 368 items,
of which 366 are ebooklib ITEM_PAGETEXT (type=0) XHTML documents. Earlier
code only treated ITEM_DOCUMENT (type=1) spine entries as candidate chapters,
so every chapter was discarded.

These tests cover 1, 10, and 100 type-0 page items to ensure the parser
treats XHTML spine entries as documents regardless of their ebooklib item type.
"""

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
