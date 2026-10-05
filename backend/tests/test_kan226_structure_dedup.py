"""KAN-226 regression tests.

Baron Trump's Marvellous Underground Journey (1893, poor OCR scan) surfaced two
related defects in the PDF/TOC chapter-extraction flow:

1. Front/back matter (Table of Contents, Preface, dedication, Appendix, etc.)
   returned by the various PDF TOC-extraction strategies was never classified
   or excluded — it could leak into the generated chapter list as if it were
   a real chapter.
2. OCR-garbled Roman numerals produced several short "chapter" fragments
   (titles lifted from TOC summary text) that all normalized to the same
   chapter number (e.g. five entries all resolving to "Chapter 1"), inflating
   the chapter count and burying the real chapter.

These tests exercise the two new/fixed FileService helpers directly:
``_dedupe_chapters_by_number`` and ``_filter_front_back_matter_structural``,
as applied together the way ``extract_chapters_with_new_flow`` now applies
them to any flat chapter list before deciding success/failure.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("MAIL_FROM", "qa@example.com")

import pytest

from app.core.services.file import FileService


def _mk(title, number, content, content_type="chapter"):
    return {
        "title": title,
        "number": number,
        "content": content,
        "summary": "",
        "content_type": content_type,
    }


@pytest.fixture
def file_service():
    return FileService()


class TestKan226DuplicateChapterNumberDedup:
    """OCR-garbled scans can emit several fragments that share a chapter number."""

    def test_keeps_longest_content_among_duplicate_numbers(self, file_service):
        chapters = [
            _mk("Chapter 1: RECEPTION", "1", "Short fragment lifted from TOC. " * 3),
            _mk("Chapter 1: BITTER", "1", "Another short fragment. " * 3),
            _mk("Chapter 1: ADIEU", "1", "Yet another short fragment. " * 3),
            _mk("Chapter 1: QUESTIONS", "1", "More TOC fragment text. " * 3),
            _mk(
                "Chapter 1: TERRIBLE",
                "1",
                "This is the real chapter body with substantial narrative content. " * 60,
            ),
            _mk("Chapter 9: DOCTOR", "9", "Real chapter nine body. " * 60),
        ]

        result = file_service._dedupe_chapters_by_number(chapters)

        chapter_1_entries = [c for c in result if c.get("number") == "1"]
        assert len(chapter_1_entries) == 1
        assert chapter_1_entries[0]["title"] == "Chapter 1: TERRIBLE"
        assert any(c["title"] == "Chapter 9: DOCTOR" for c in result)
        assert len(result) == 2

    def test_leaves_unique_numbers_untouched(self, file_service):
        chapters = [
            _mk("Chapter 1: A", "1", "body " * 200),
            _mk("Chapter 2: B", "2", "body " * 200),
            _mk("Chapter 3: C", "3", "body " * 200),
        ]
        result = file_service._dedupe_chapters_by_number(chapters)
        assert [c["number"] for c in result] == ["1", "2", "3"]

    def test_front_back_matter_not_affected_by_number_collisions(self, file_service):
        # Front/back matter entries typically carry number=None and must never
        # be treated as duplicates of a real numbered chapter.
        chapters = [
            _mk("Preface", None, "front matter " * 200, content_type="front_matter"),
            _mk("Chapter 1: REAL", "1", "body " * 200),
            _mk("Appendix", None, "back matter " * 200, content_type="back_matter"),
        ]
        result = file_service._dedupe_chapters_by_number(chapters)
        assert len(result) == 3


class TestKan226FrontBackMatterExclusion:
    """Front/back matter must be classified and excluded from generation."""

    def test_toc_preface_and_appendix_excluded_from_generation(self, file_service):
        chapters = [
            _mk("Table of Contents", None, "x " * 300, content_type="chapter"),
            _mk("Preface", None, "x " * 300, content_type="chapter"),
            _mk("Chapter 1: One", "1", "narrative body text here. " * 60, content_type="chapter"),
            _mk("Chapter 2: Two", "2", "narrative body text here. " * 60, content_type="chapter"),
            _mk("Appendix", None, "x " * 300, content_type="chapter"),
        ]

        result = file_service._filter_front_back_matter_structural(chapters)

        by_title = {c["title"]: c for c in result}
        assert by_title["Table of Contents"]["content_type"] == "front_matter"
        assert by_title["Table of Contents"]["use_in_generation"] is False
        assert by_title["Preface"]["content_type"] == "front_matter"
        assert by_title["Preface"]["use_in_generation"] is False
        assert by_title["Appendix"]["content_type"] == "back_matter"
        assert by_title["Appendix"]["use_in_generation"] is False

        assert by_title["Chapter 1: One"]["content_type"] == "chapter"
        assert by_title["Chapter 1: One"]["use_in_generation"] is True
        assert by_title["Chapter 2: Two"]["content_type"] == "chapter"
        assert by_title["Chapter 2: Two"]["use_in_generation"] is True

        # All 5 items are preserved (classified, not dropped outright) so the
        # combined pipeline can still choose to keep/hide them explicitly.
        assert len(result) == 5
        generated_titles = [c["title"] for c in result if c.get("use_in_generation")]
        assert generated_titles == ["Chapter 1: One", "Chapter 2: Two"]


class TestKan226CombinedPipeline:
    """Dedup must run BEFORE front/back-matter classification renumbers chapters."""

    def test_dedupe_then_classify_matches_extraction_flow_order(self, file_service):
        chapters = [
            _mk("Table of Contents", None, "x " * 300, content_type="chapter"),
            _mk("Chapter 1: RECEPTION", "1", "fragment " * 5),
            _mk("Chapter 1: BITTER", "1", "fragment " * 5),
            _mk(
                "Chapter 1: TERRIBLE",
                "1",
                "This is the real chapter one body text. " * 80,
            ),
            _mk("Chapter 9: DOCTOR", "9", "real chapter nine body text. " * 80),
            _mk("Appendix", None, "x " * 300, content_type="chapter"),
        ]

        deduped = file_service._dedupe_chapters_by_number(chapters)
        result = file_service._filter_front_back_matter_structural(deduped)

        real_chapters = [c for c in result if c.get("content_type") == "chapter"]
        assert len(real_chapters) == 2
        titles = [c["title"] for c in real_chapters]
        assert titles == ["Chapter 1: TERRIBLE", "Chapter 9: DOCTOR"]
        # KAN-227: numbers derive from detected headings — after dedupe the
        # survivors keep their real chapter numbers (sequential renumbering
        # caused the KAN-227 drift: CHAPTER 9 was displayed as 2).
        assert [c["number"] for c in real_chapters] == ["1", "9"]

        front_back = {c["title"]: c for c in result if c.get("content_type") != "chapter"}
        assert front_back["Table of Contents"]["use_in_generation"] is False
        assert front_back["Appendix"]["use_in_generation"] is False
