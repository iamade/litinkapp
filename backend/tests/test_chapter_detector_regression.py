"""
KAN-367 Regression Tests — chapter_detector off-by-N fix

Tests verify that front-matter/back-matter sections (etymology, extracts, epigraph,
acknowledgments, afterword, dedication) are correctly excluded from chapter counting.

Root cause: SPECIAL_SECTIONS didn't include these patterns, causing Moby Dick's
"ETYMOLOGY" and "EXTRACTS" sections to be counted as chapters 1-2, shifting real
Chapter 1 to position 3 (off-by-2).
"""

import pytest
import re
from app.core.services.file import BookStructureDetector


def _long_filler(word_count: int = 80) -> str:
    """Generate a block of text long enough to pass substantial-content checks."""
    words_per_line = 10
    line_count = (word_count // words_per_line) + 2
    return "\n".join([" ".join([f"content{i}"] * words_per_line) for i in range(line_count)])


class TestSpecialSectionsPattern:
    """Test that SPECIAL_SECTIONS correctly identifies front-matter/back-matter."""

    def setup_method(self):
        self.processor = BookStructureDetector()

    def test_etymology_matched(self):
        """Etymology section should be recognized as special (not a chapter)."""
        assert self.processor._match_special_sections("ETYMOLOGY")
        assert self.processor._match_special_sections("Etymology")
        assert self.processor._match_special_sections("etymology")

    def test_extracts_matched(self):
        """Extracts section should be recognized as special (not a chapter)."""
        assert self.processor._match_special_sections("EXTRACTS")
        assert self.processor._match_special_sections("Extracts")
        assert self.processor._match_special_sections("Extract")

    def test_epigraph_matched(self):
        """Epigraph section should be recognized as special."""
        assert self.processor._match_special_sections("EPIGRAPH")
        assert self.processor._match_special_sections("Epigraph")

    def test_acknowledgments_matched(self):
        """Acknowledgments section should be recognized as special."""
        assert self.processor._match_special_sections("ACKNOWLEDGMENTS")
        assert self.processor._match_special_sections("Acknowledgments")
        assert self.processor._match_special_sections("Acknowledgment")

    def test_afterword_matched(self):
        """Afterword section should be recognized as special."""
        assert self.processor._match_special_sections("AFTERWORD")
        assert self.processor._match_special_sections("Afterword")

    def test_dedication_matched(self):
        """Dedication section should be recognized as special."""
        assert self.processor._match_special_sections("DEDICATION")
        assert self.processor._match_special_sections("Dedication")

    def test_preface_still_matched(self):
        """Preface should still be recognized (existing functionality)."""
        assert self.processor._match_special_sections("PREFACE")
        assert self.processor._match_special_sections("Preface")

    def test_prologue_still_matched(self):
        """Prologue should still be recognized (existing functionality)."""
        assert self.processor._match_special_sections("PROLOGUE")
        assert self.processor._match_special_sections("Prologue")

    def test_epilogue_still_matched(self):
        """Epilogue should still be recognized (existing functionality)."""
        assert self.processor._match_special_sections("EPILOGUE")
        assert self.processor._match_special_sections("Epilogue")

    def test_chapter_not_matched(self):
        """Regular chapter headers should NOT be recognized as special sections."""
        assert not self.processor._match_special_sections("Chapter 1")
        assert not self.processor._match_special_sections("CHAPTER I")
        assert not self.processor._match_special_sections("1. The Looming Crisis")

    def test_special_section_matching_is_stateless(self):
        """Repeated special headings should still match during nested parser scans."""
        assert self.processor._match_special_sections("ACKNOWLEDGMENTS")
        assert self.processor._match_special_sections("ACKNOWLEDGMENTS")

    def test_special_sections_completeness(self):
        """Verify all expected special sections are present."""
        import re

        expected = [
            "preface", "introduction", "foreword", "prologue", "epilogue",
            "conclusion", "appendix", "etymology", "extracts", "epigraph",
            "acknowledgments", "afterword", "dedication", "notes",
            "suggested reading", "bibliography", "index", "references", "glossary"
        ]
        patterns = self.processor.SPECIAL_SECTIONS
        for section in expected:
            section_words = section.split()
            assert any(
                all(word in p.lower() for word in section_words)
                for p in patterns
            ), f"Missing pattern for '{section}' in SPECIAL_SECTIONS"


class TestExtractFlatChapters:
    """Test that _extract_flat_chapters skips special sections."""

    def setup_method(self):
        self.processor = BookStructureDetector()

    def test_moby_dick_frontmatter_skipped(self):
        """
        Moby Dick simulation: ETYMOLOGY + EXTRACTS should be skipped,
        real Chapter 1 should be first in output.
        """
        # Simulate TOC-like content with front-matter
        test_content = """
ETYMOLOGY
Suppose you're a whale expert...

EXTRACTS
Whales are fish. — NED LAND

CHAPTER 1. Loomings.
Call me Ishmael.

CHAPTER 2. The Carpet-Bag.
I stuffed my shirt...
""".strip().split('\n')

        chapters = []
        for line in test_content:
            if self.processor._match_special_sections(line):
                continue  # Skip special sections (KAN-367 fix)
            chapter_match = self.processor._match_chapter_patterns(line)
            if chapter_match:
                chapters.append(line)

        # Chapter 1 should be first, not Chapter 3
        assert len(chapters) >= 2
        assert "CHAPTER 1" in chapters[0]
        assert "CHAPTER 2" in chapters[1]

    def test_regular_chapters_not_affected(self):
        """Regular chapter extraction should still work correctly."""
        test_lines = [
            "CHAPTER 1. The Beginning",
            "CHAPTER 2. The Middle",
            "CHAPTER 3. The End"
        ]

        chapters = []
        for line in test_lines:
            if not self.processor._match_special_sections(line):
                match = self.processor._match_chapter_patterns(line)
                if match:
                    chapters.append(line)

        assert len(chapters) == 3
        assert "CHAPTER 1" in chapters[0]
        assert "CHAPTER 3" in chapters[2]


class TestSpecialSectionExtraction:
    """Special-section books should stay sectioned in preview extraction."""

    def setup_method(self):
        from app.core.services.file import FileService
        self.processor = FileService()

    @pytest.mark.asyncio
    async def test_special_only_book_preserves_sections(self):
        content = "\n\n".join(
            f"{title}\n{_long_filler()} for {title}."
            for title in [
                "ETYMOLOGY",
                "EXTRACTS",
                "EPIGRAPH",
                "ACKNOWLEDGMENTS",
                "AFTERWORD",
                "DEDICATION",
                "NOTES",
            ]
        )

        result = await self.processor.extract_chapters_with_new_flow(
            content=content,
            book_type="entertainment",
            original_filename="special-sections.txt",
            storage_path="",
        )

        assert len(result) == 7
        assert all("chapters" in section for section in result)
        assert [section["title"] for section in result] == [
            "ETYMOLOGY",
            "EXTRACTS",
            "EPIGRAPH",
            "ACKNOWLEDGMENTS",
            "AFTERWORD",
            "DEDICATION",
            "NOTES",
        ]


class TestHierarchicalSectionAssignment:
    """
    KAN-367 v3: Special sections (ETYMOLOGY, EPILOGUE, etc.) must not swallow
    real chapters. Real chapters should be extracted into a separate group and
    special sections should be tagged with front_matter/back_matter content_type.
    """

    def setup_method(self):
        self.processor = BookStructureDetector()

    def _book(self, lines: list) -> str:
        return "\n\n".join(lines)

    def test_book_a_etymology_then_chapters(self):
        """Book A: ETYMOLOGY special section, then Chapter 1-3."""
        etymology_body = " whales are big fish. " + _long_filler(80)
        content = self._book([
            "ETYMOLOGY",
            etymology_body,
            "CHAPTER 1. Loomings.",
            _long_filler(),
            "CHAPTER 2. The Carpet-Bag.",
            _long_filler(),
            "CHAPTER 3. The Spouter-Inn.",
            _long_filler(),
        ])

        result = self.processor.detect_structure(content)

        assert result["has_sections"] is True
        sections = result["sections"]
        assert [s["title"] for s in sections] == ["ETYMOLOGY", "Chapters"]
        assert sections[0]["type"] == "special"
        assert sections[0]["chapters"] == []
        assert sections[0].get("content_type") == "front_matter"
        # ETYMOLOGY content must not bleed into chapter text
        assert "Carpet-Bag" not in sections[0]["content"]
        assert [c["number"] for c in sections[1]["chapters"]] == ["1", "2", "3"]
        assert all(c.get("content_type") == "chapter" for c in sections[1]["chapters"])

    def test_book_b_chapters_then_epilogue(self):
        """Book B: Chapter 1-2 first, then EPILOGUE special section."""
        epilogue_body = "iris lived to be ninety-three. " + _long_filler(80)
        content = self._book([
            "CHAPTER 1. The Beginning.",
            _long_filler(),
            "CHAPTER 2. The Middle.",
            _long_filler(),
            "EPILOGUE",
            epilogue_body,
        ])

        result = self.processor.detect_structure(content)

        assert result["has_sections"] is True
        sections = result["sections"]
        assert [s["title"] for s in sections] == ["Chapters", "EPILOGUE"]
        assert [c["number"] for c in sections[0]["chapters"]] == ["1", "2"]
        assert sections[1]["type"] == "special"
        assert sections[1].get("content_type") == "back_matter"
        # Chapter 2 must not contain EPILOGUE body text
        assert "iris" not in sections[0]["chapters"][1]["content"].lower()
        assert "ninety-three" not in sections[0]["chapters"][1]["content"].lower()

    def test_book_c_etymology_chapters_epilogue(self):
        """Book C: ETYMOLOGY, Chapter 1-2, EPILOGUE."""
        epilogue_body = "iris lived to be ninety-three. " + _long_filler(80)
        content = self._book([
            "ETYMOLOGY",
            _long_filler(),
            "CHAPTER 1. Loomings.",
            _long_filler(),
            "CHAPTER 2. The Carpet-Bag.",
            _long_filler(),
            "EPILOGUE",
            epilogue_body,
        ])

        result = self.processor.detect_structure(content)

        assert result["has_sections"] is True
        sections = result["sections"]
        assert [s["title"] for s in sections] == ["ETYMOLOGY", "Chapters", "EPILOGUE"]
        assert sections[0]["type"] == "special"
        assert sections[0].get("content_type") == "front_matter"
        assert [c["number"] for c in sections[1]["chapters"]] == ["1", "2"]
        assert sections[2]["type"] == "special"
        assert sections[2].get("content_type") == "back_matter"
        # Chapters must not contain ETYMOLOGY or EPILOGUE body text
        for ch in sections[1]["chapters"]:
            assert "iris" not in ch["content"].lower()
            assert "ninety-three" not in ch["content"].lower()
        assert "Carpet-Bag" not in sections[0]["content"]

    def test_garbage_year_not_chapter(self):
        """Standalone 4-digit years like '2026.' must not be treated as chapters."""
        assert not self.processor._match_chapter_patterns("2026.")
        assert not self.processor._match_chapter_patterns("2026")

    def test_normal_section_with_chapters_still_nests(self):
        """Non-special sections (PART I, BOOK I) continue to nest their chapters."""
        content = self._book([
            "PART I The Departure",
            _long_filler(),
            "CHAPTER 1. Leaving Home.",
            _long_filler(),
            "CHAPTER 2. On the Road.",
            _long_filler(),
            "PART II The Return",
            _long_filler(),
            "CHAPTER 3. Arrival.",
            _long_filler(),
        ])

        result = self.processor.detect_structure(content)

        assert result["has_sections"] is True
        sections = result["sections"]
        assert len(sections) == 2
        assert [s["type"] for s in sections] == ["part", "part"]
        assert len(sections[0]["chapters"]) == 2
        assert len(sections[1]["chapters"]) == 1

    @pytest.mark.asyncio
    async def test_extract_hierarchical_chapters_content_type_and_number(self):
        """Special sections carry front_matter/back_matter content_type and real chapters keep raw numbers."""
        from app.core.services.file import FileService
        file_service = FileService()
        etymology_body = " whales are big fish. " + _long_filler(80)
        content = self._book([
            "ETYMOLOGY",
            etymology_body,
            "CHAPTER 1. Loomings.",
            _long_filler(),
            "CHAPTER 2. The Carpet-Bag.",
            _long_filler(),
            "EPILOGUE",
            _long_filler(),
        ])

        structure = self.processor.detect_structure(content)
        chapters = await file_service._extract_hierarchical_chapters(
            structure, book_type="entertainment", book_content=content
        )

        # ETYMOLOGY = front_matter, Chapters = chapter, EPILOGUE = back_matter
        assert chapters[0]["content_type"] == "front_matter"
        assert chapters[0]["chapter_number"] == 1
        assert chapters[1]["content_type"] == "chapter"
        assert chapters[1]["chapter_number"] == 2
        assert chapters[1]["number"] == "1"
        assert chapters[2]["content_type"] == "chapter"
        assert chapters[2]["chapter_number"] == 3
        assert chapters[2]["number"] == "2"
        assert chapters[3]["content_type"] == "back_matter"
        assert chapters[3]["chapter_number"] == 4

        # ETYMOLOGY content must not contain chapter body text
        assert "Carpet-Bag" not in chapters[0]["content"]
