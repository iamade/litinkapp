"""
KAN-367 Regression Tests — chapter_detector off-by-N fix

Tests verify that front-matter/back-matter sections (etymology, extracts, epigraph,
acknowledgments, afterword, dedication) are correctly excluded from chapter counting.

Root cause: SPECIAL_SECTIONS didn't include these patterns, causing Moby Dick's
"ETYMOLOGY" and "EXTRACTS" sections to be counted as chapters 1-2, shifting real
Chapter 1 to position 3 (off-by-2).
"""

import pytest
from app.core.services.file import EPUBProcessor


class TestSpecialSectionsPattern:
    """Test that SPECIAL_SECTIONS correctly identifies front-matter/back-matter."""

    def setup_method(self):
        self.processor = EPUBProcessor()

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

    def test_special_sections_completeness(self):
        """Verify all expected special sections are present."""
        expected = [
            "preface", "introduction", "foreword", "prologue", "epilogue",
            "conclusion", "appendix", "etymology", "extracts", "epigraph",
            "acknowledgments", "afterword", "dedication", "notes",
            "suggested reading", "bibliography", "index", "references", "glossary"
        ]
        patterns = self.processor.SPECIAL_SECTIONS
        for section in expected:
            assert any(section in p.lower() for p in patterns), \
                f"Missing pattern for '{section}' in SPECIAL_SECTIONS"


class TestExtractFlatChapters:
    """Test that _extract_flat_chapters skips special sections."""

    def setup_method(self):
        self.processor = EPUBProcessor()

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
                chapters.append(chapter_match.group(0))

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
                    chapters.append(match.group(0))

        assert len(chapters) == 3
        assert "CHAPTER 1" in chapters[0]
        assert "CHAPTER 3" in chapters[2]
