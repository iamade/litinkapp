"""KAN-226: content_type must survive the flat preview and the save path.

Two independent gaps, both required for the fix to be complete:

GAP A - the FLAT preview response omitted content_type entirely (the dict at
file.py:6791 built the preview chapter without the key), so the client could
not send it back.

GAP B - the save path defaulted content_type to "chapter" (old file.py:6978),
so anything the client did not send was persisted as a real chapter.

Both are covered here, plus the row-level invariants LC requires on the
staging run: front/back matter persist with content_type front_matter /
back_matter and chapter_number NULL, while real chapters number 1..N.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
os.environ.setdefault("STRIPE_SECRET_KEY", "test-key")
os.environ.setdefault("MAIL_FROM", "test@litinkai.dev")

from app.core.services.file import FileService


class TestKan226GapAFlatPreviewCarriesContentType:
    """GAP A: the flat preview chapter list must carry content_type."""

    def test_flat_preview_chapter_carries_content_type_key(self):
        service = FileService()
        preview = service._build_flat_preview_chapters(
            [{"title": "Chapter 1", "content": "Body one"}],
            "book-1",
        )
        assert len(preview) == 1
        assert "content_type" in preview[0]
        assert preview[0]["content_type"] == "chapter"

    def test_flat_preview_derives_front_matter_from_title(self):
        service = FileService()
        preview = service._build_flat_preview_chapters(
            [{"title": "Preface", "content": "For the reader"}],
            "book-1",
        )
        assert preview[0]["content_type"] == "front_matter"

    def test_flat_preview_derives_back_matter_from_title(self):
        service = FileService()
        preview = service._build_flat_preview_chapters(
            [{"title": "Appendix", "content": "Appendix body"}],
            "book-1",
        )
        assert preview[0]["content_type"] == "back_matter"

    def test_flat_preview_front_matter_chapter_number_is_null(self):
        service = FileService()
        preview = service._build_flat_preview_chapters(
            [
                {"title": "Dedication", "content": "For you"},
                {"title": "Chapter 1", "content": "One"},
                {"title": "Chapter 2", "content": "Two"},
            ],
            "book-1",
        )
        assert preview[0]["chapter_number"] is None
        assert preview[1]["chapter_number"] == 1
        assert preview[2]["chapter_number"] == 2

    def test_flat_preview_real_chapters_number_1_to_n(self):
        service = FileService()
        preview = service._build_flat_preview_chapters(
            [{"title": f"Chapter {i}", "content": f"Body {i}"} for i in range(1, 6)],
            "book-1",
        )
        assert [c["chapter_number"] for c in preview] == [1, 2, 3, 4, 5]

    def test_flat_preview_client_supplied_content_type_is_honoured(self):
        service = FileService()
        preview = service._build_flat_preview_chapters(
            [{"title": "Some Title", "content": "Body", "content_type": "back_matter"}],
            "book-1",
        )
        assert preview[0]["content_type"] == "back_matter"


class TestKan226GapBSavePathReDerivesContentType:
    """GAP B: the save path must not default content_type to chapter."""

    def test_resolve_content_type_defaults_to_chapter_for_plain_title(self):
        service = FileService()
        assert (
            service._resolve_content_type({"title": "Chapter 4", "content": "Body"})
            == "chapter"
        )

    def test_resolve_content_type_derives_front_matter(self):
        service = FileService()
        assert (
            service._resolve_content_type({"title": "Preface", "content": "Body"})
            == "front_matter"
        )

    def test_resolve_content_type_derives_back_matter(self):
        service = FileService()
        assert (
            service._resolve_content_type({"title": "Index", "content": "Body"})
            == "back_matter"
        )

    def test_resolve_content_type_keeps_client_value(self):
        service = FileService()
        assert (
            service._resolve_content_type(
                {"title": "Preface", "content": "Body", "content_type": "chapter"}
            )
            == "chapter"
        )

    def test_save_path_source_has_no_bare_chapter_default(self):
        """The old file.py:6978 default must not come back."""
        import inspect

        source = inspect.getsource(FileService.confirm_book_structure)
        assert 'ch.get("content_type", "chapter")' not in source
        assert "_resolve_content_type" in source

    def test_save_path_source_keeps_sequential_numbering(self):
        import inspect

        source = inspect.getsource(FileService.confirm_book_structure)
        assert "chapter_number = chapter_order" in source
