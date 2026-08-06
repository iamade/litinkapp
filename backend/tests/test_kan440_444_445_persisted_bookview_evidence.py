"""
KAN-440, KAN-444, KAN-445: Persisted BookView Hierarchy Evidence Tests

This test suite provides end-to-end evidence that the save-structure pipeline
preserves section hierarchy from detection through persistence entries.

KAN-440: PDF front/back matter preservation (page numbers not treated as chapters)
KAN-444: Sectioned PDF hierarchy persistence (section_key non-null for body chapters)
KAN-445: EPUB type-0 page items handled (Great Expectations returns chapters)
"""

import contextlib
import hashlib
import io
from pathlib import Path

import fitz
import pytest

from app.core.services.file import FileService


FIXTURE_DIR = Path("/opt/openclaw/fixtures/litinkai/KAN-440-444")
ORWELL_PDF = FIXTURE_DIR / "orwell1984.pdf"
FRANK_PDF = FIXTURE_DIR / "frank-a5.pdf"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pdf_text(path: Path) -> str:
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)


def _detect_quietly(service: FileService, text: str) -> dict:
    with contextlib.redirect_stdout(io.StringIO()):
        return service.structure_detector.detect_structure(text)


def _long_filler(word_count: int = 80) -> str:
    """Generate a block of text long enough to pass substantial-content checks."""
    words_per_line = 10
    line_count = (word_count // words_per_line) + 2
    return "\n".join([" ".join([f"content{i}"] * words_per_line) for i in range(line_count)])


class TestKan440PdfFrontBackMatterPreservation:
    """KAN-440: PDF direct detector preserves front/back matter, doesn't treat page numbers as chapters."""

    def test_orwell_pdf_front_matter_preserved(self):
        """Orwell 1984 PDF: front matter preserved with content_type=front_matter."""
        service = FileService()
        result = _detect_quietly(service, _pdf_text(ORWELL_PDF))

        sections = result["sections"]
        front_matter_sections = [s for s in sections if s.get("content_type") == "front_matter"]
        
        assert len(front_matter_sections) >= 1
        # Front Matter section should exist
        assert any("Front Matter" in s["title"] or s["title"] in {"Dedication", "PREFACE"} for s in front_matter_sections)

    def test_orwell_pdf_back_matter_preserved(self):
        """Orwell 1984 PDF: back matter (APPENDIX) preserved with content_type=back_matter."""
        service = FileService()
        result = _detect_quietly(service, _pdf_text(ORWELL_PDF))

        sections = result["sections"]
        back_matter_sections = [s for s in sections if s.get("content_type") == "back_matter"]
        
        assert len(back_matter_sections) >= 1
        appendix_titles = [s["title"] for s in back_matter_sections if "appendix" in s["title"].lower()]
        assert len(appendix_titles) >= 1

    def test_orwell_pdf_page_numbers_not_chapters(self):
        """Orwell 1984 PDF: page number runs not treated as chapters."""
        service = FileService()
        result = _detect_quietly(service, _pdf_text(ORWELL_PDF))

        sections = result["sections"]
        all_chapter_numbers = []
        for section in sections:
            for chapter in section.get("chapters", []):
                num = chapter.get("number", "")
                if num:
                    all_chapter_numbers.append(num)

        # Orwell should have chapters 1-23 (8+9+6)
        assert len(all_chapter_numbers) == 23, f"Expected 23 chapters, got {len(all_chapter_numbers)}"
        
        # Page numbers should not appear as chapter numbers
        # The actual chapter numbers should be 1-8, 1-9, 1-6 for the three parts
        part_one_chapters = sections[1].get("chapters", [])
        part_two_chapters = sections[2].get("chapters", [])
        part_three_chapters = sections[3].get("chapters", [])
        
        assert len(part_one_chapters) == 8
        assert len(part_two_chapters) == 9
        assert len(part_three_chapters) == 6


class TestKan444SectionedPdfHierarchyPersistence:
    """KAN-444: save-structure preserves sectioned PDF hierarchy with section_key for body chapters."""

    def test_orwell_pdf_persisted_entries_have_section_keys(self):
        """Orwell 1984 PDF: persisted BookView entries have section_key for body chapters, null for front/back."""
        service = FileService()
        
        # Orwell PDF has no bookmarks, use text-based detection
        result = _detect_quietly(service, _pdf_text(ORWELL_PDF))
        sections = result["sections"]
        
        entries = list(service._iter_confirmed_structure_entries(sections))

        section_entries = [e for e in entries if e["kind"] == "section"]
        chapter_entries = [e for e in entries if e["kind"] == "chapter"]
        body_chapters = [
            e for e in chapter_entries
            if e["data"].get("content_type", "chapter") == "chapter"
        ]
        front_back_matter = [
            e for e in chapter_entries
            if e["data"].get("content_type") in {"front_matter", "back_matter"}
        ]

        # Orwell has PART ONE, PART TWO, PART THREE as sections
        assert len(section_entries) == 3, f"Expected 3 sections, got {len(section_entries)}"
        
        # Body chapters must have non-null section_key
        assert len(body_chapters) == 23, f"Expected 23 body chapters, got {len(body_chapters)}"
        assert all(e["section_key"] is not None for e in body_chapters), "Body chapters must have section_key"

        # Front/back matter must have null section_key
        assert len(front_back_matter) >= 1, f"Expected front/back matter entries, got {len(front_back_matter)}"
        assert all(e["section_key"] is None for e in front_back_matter), "Front/back matter must have null section_key"

    def test_frank_a5_pdf_persisted_entries_have_section_keys(self):
        """Frankenstein A5 PDF: persisted BookView entries preserve volume hierarchy with section_key."""
        service = FileService()
        doc = fitz.open(FRANK_PDF)

        with contextlib.redirect_stdout(io.StringIO()):
            chapters = service._process_pdf_bookmarks(doc, doc.get_toc())
            sections = service._organize_chapters_into_sections(chapters)
            entries = list(service._iter_confirmed_structure_entries(sections))

        section_entries = [e for e in entries if e["kind"] == "section"]
        chapter_entries = [e for e in entries if e["kind"] == "chapter"]
        body_chapters = [
            e for e in chapter_entries
            if e["data"].get("content_type", "chapter") == "chapter"
        ]

        # Volume sections should exist
        volume_sections = [e for e in section_entries if "Volume" in e["data"]["title"]]
        assert len(volume_sections) >= 3, f"Expected 3 volumes, got {len(volume_sections)}"

        # Body chapters must have section_key linking to volumes
        assert len(body_chapters) == 27, f"Expected 27 body chapters, got {len(body_chapters)}"
        assert all(e["section_key"] is not None for e in body_chapters)

    def test_synthetic_tale_two_cities_hierarchy_preserved(self):
        """Tale of Two Cities: synthetic test for BOOK THE FIRST/SECOND/THIRD hierarchy."""
        service = FileService()

        # Simulate Tale of Two Cities structure
        synthetic_structure = [
            {
                "title": "BOOK THE FIRST",
                "section_type": "part",
                "section_number": "I",
                "content_type": "chapter",
                "chapters": [
                    {"title": "Chapter I", "content": "The Period", "content_type": "chapter"},
                    {"title": "Chapter II", "content": "The Mail", "content_type": "chapter"},
                    {"title": "Chapter III", "content": "The Night Shadows", "content_type": "chapter"},
                ],
            },
            {
                "title": "BOOK THE SECOND",
                "section_type": "part",
                "section_number": "II",
                "content_type": "chapter",
                "chapters": [
                    {"title": "Chapter IV", "content": "The Preparation", "content_type": "chapter"},
                    {"title": "Chapter V", "content": "The Wine-shop", "content_type": "chapter"},
                ],
            },
            {
                "title": "BOOK THE THIRD",
                "section_type": "part",
                "section_number": "III",
                "content_type": "chapter",
                "chapters": [
                    {"title": "Chapter VI", "content": "In Secret", "content_type": "chapter"},
                ],
            },
        ]

        entries = list(service._iter_confirmed_structure_entries(synthetic_structure))

        section_entries = [e for e in entries if e["kind"] == "section"]
        chapter_entries = [e for e in entries if e["kind"] == "chapter"]
        body_chapters = [
            e for e in chapter_entries
            if e["data"].get("content_type", "chapter") == "chapter"
        ]

        assert len(section_entries) == 3
        assert [e["data"]["title"] for e in section_entries] == [
            "BOOK THE FIRST",
            "BOOK THE SECOND",
            "BOOK THE THIRD",
        ]
        assert len(body_chapters) == 6
        assert all(e["section_key"] is not None for e in body_chapters)

    def test_synthetic_pride_prejudice_hierarchy_preserved(self):
        """Pride and Prejudice: synthetic test for Volume I/II/III hierarchy."""
        service = FileService()

        synthetic_structure = [
            {
                "title": "Volume I",
                "section_type": "part",
                "section_number": "I",
                "content_type": "chapter",
                "chapters": [
                    {"title": "Chapter 1", "content": "Opening", "content_type": "chapter"},
                    {"title": "Chapter 2", "content": "Continuation", "content_type": "chapter"},
                ],
            },
            {
                "title": "Volume II",
                "section_type": "part",
                "section_number": "II",
                "content_type": "chapter",
                "chapters": [
                    {"title": "Chapter 3", "content": "Middle", "content_type": "chapter"},
                ],
            },
            {
                "title": "Volume III",
                "section_type": "part",
                "section_number": "III",
                "content_type": "chapter",
                "chapters": [
                    {"title": "Chapter 4", "content": "End", "content_type": "chapter"},
                ],
            },
        ]

        entries = list(service._iter_confirmed_structure_entries(synthetic_structure))

        section_entries = [e for e in entries if e["kind"] == "section"]
        chapter_entries = [e for e in entries if e["kind"] == "chapter"]
        body_chapters = [
            e for e in chapter_entries
            if e["data"].get("content_type", "chapter") == "chapter"
        ]

        assert len(section_entries) == 3
        assert len(body_chapters) == 4
        assert all(e["section_key"] is not None for e in body_chapters)

    def test_synthetic_david_copperfield_hierarchy_preserved(self):
        """David Copperfield: synthetic test for chapter hierarchy preservation."""
        service = FileService()

        synthetic_structure = [
            {
                "title": "Chapter 1",
                "content": "I Am Born",
                "content_type": "chapter",
            },
            {
                "title": "Chapter 2",
                "content": "I Observe",
                "content_type": "chapter",
            },
            {
                "title": "Chapter 3",
                "content": "I Have a Change",
                "content_type": "chapter",
            },
        ]

        entries = list(service._iter_confirmed_structure_entries(synthetic_structure))

        chapter_entries = [e for e in entries if e["kind"] == "chapter"]
        body_chapters = [
            e for e in chapter_entries
            if e["data"].get("content_type", "chapter") == "chapter"
        ]

        # Flat chapters (no sections) should have null section_key
        assert len(body_chapters) == 3
        assert all(e["section_key"] is None for e in body_chapters)

    def test_synthetic_great_expectations_hierarchy_preserved(self):
        """Great Expectations: synthetic test for chapter hierarchy preservation."""
        service = FileService()

        # Great Expectations has 59 chapters, no volume sections
        synthetic_structure = [
            {
                "title": f"Chapter {i}",
                "content": f"Content {i}",
                "content_type": "chapter",
            }
            for i in range(1, 60)
        ]

        entries = list(service._iter_confirmed_structure_entries(synthetic_structure))

        chapter_entries = [e for e in entries if e["kind"] == "chapter"]
        body_chapters = [
            e for e in chapter_entries
            if e["data"].get("content_type", "chapter") == "chapter"
        ]

        assert len(body_chapters) == 59
        assert all(e["section_key"] is None for e in body_chapters)


class TestKan445EpubType0Handling:
    """KAN-445: EPUB parser handles type-0 page items, Great Expectations returns chapters."""

    @pytest.mark.asyncio
    async def test_great_expectations_epub_type0_chapter_count(self, tmp_path, monkeypatch):
        """Great Expectations EPUB: type-0 page items yield 59 chapters."""
        from ebooklib import epub
        from app.core.services.file import FileService

        # Create synthetic Great Expectations EPUB with type-0 page items
        epub_path = tmp_path / "great-expectations.epub"
        book = epub.EpubBook()
        book.set_identifier("great-expectations-kan445")
        book.set_title("Great Expectations")
        book.set_language("en")

        # Create 59 chapters as type-0 items with substantial content
        for i in range(1, 60):
            page = epub.EpubItem(
                uid=f"chapter_{i}",
                file_name=f"text/chapter_{i}.xhtml",
                media_type="application/xhtml+xml",
                content=f"<html><body><h1>Chapter {i}</h1><p>{_long_filler(100)}</p></body></html>".encode("utf-8"),
            )
            book.add_item(page)

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = [(f"chapter_{i}", "yes") for i in range(1, 60)]
        epub.write_epub(str(epub_path), book)

        file_service = FileService()
        chapters = file_service.extract_epub_chapters(str(epub_path))
        chapter_items = [c for c in chapters if c.get("content_type") == "chapter"]

        assert len(chapter_items) == 59, f"Expected 59 chapters, got {len(chapter_items)}"
        assert chapter_items[0]["title"] == "Chapter 1"
        assert chapter_items[-1]["title"] == "Chapter 59"

    @pytest.mark.asyncio
    async def test_frankenstein_epub_type0_chapter_count(self, tmp_path, monkeypatch):
        """Frankenstein EPUB: type-0 page items yield correct chapter count."""
        from ebooklib import epub
        from app.core.services.file import FileService

        # Frankenstein has 24 chapters + front/back matter
        epub_path = tmp_path / "frankenstein.epub"
        book = epub.EpubBook()
        book.set_identifier("frankenstein-kan445")
        book.set_title("Frankenstein")
        book.set_language("en")

        # Front matter with substantial content
        preface = epub.EpubItem(
            uid="preface",
            file_name="text/preface.xhtml",
            media_type="application/xhtml+xml",
            content=f"<html><body><h1>PREFACE</h1><p>{_long_filler(100)}</p></body></html>".encode("utf-8"),
        )
        book.add_item(preface)

        # 24 chapters with substantial content
        for i in range(1, 25):
            chapter = epub.EpubItem(
                uid=f"chapter_{i}",
                file_name=f"text/chapter_{i}.xhtml",
                media_type="application/xhtml+xml",
                content=f"<html><body><h1>Chapter {i}</h1><p>{_long_filler(100)}</p></body></html>".encode("utf-8"),
            )
            book.add_item(chapter)

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = [("preface", "yes")] + [(f"chapter_{i}", "yes") for i in range(1, 25)]
        epub.write_epub(str(epub_path), book)

        file_service = FileService()
        chapters = file_service.extract_epub_chapters(str(epub_path))
        chapter_items = [c for c in chapters if c.get("content_type") == "chapter"]
        front_matter = [c for c in chapters if c.get("content_type") == "front_matter"]

        assert len(chapter_items) == 24, f"Expected 24 chapters, got {len(chapter_items)}"
        assert len(front_matter) == 1, f"Expected 1 front matter, got {len(front_matter)}"

    @pytest.mark.asyncio
    async def test_type0_items_preserve_chapter_order(self, tmp_path, monkeypatch):
        """EPUB type-0 items: chapter order preserved from spine."""
        from ebooklib import epub
        from app.core.services.file import FileService

        epub_path = tmp_path / "ordered-chapters.epub"
        book = epub.EpubBook()
        book.set_identifier("ordered-kan445")
        book.set_title("Ordered Chapters")
        book.set_language("en")

        # Create chapters in specific order with substantial content
        chapter_order = ["Chapter 3", "Chapter 1", "Chapter 2"]
        for i, title in enumerate(chapter_order, start=1):
            page = epub.EpubItem(
                uid=f"page_{i}",
                file_name=f"text/page_{i}.xhtml",
                media_type="application/xhtml+xml",
                content=f"<html><body><h1>{title}</h1><p>{_long_filler(100)}</p></body></html>".encode("utf-8"),
            )
            book.add_item(page)

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = [(f"page_{i}", "yes") for i in range(1, 4)]
        epub.write_epub(str(epub_path), book)

        file_service = FileService()
        chapters = file_service.extract_epub_chapters(str(epub_path))

        # Chapters should be in spine order
        assert len(chapters) == 3
        assert chapters[0]["title"] == "Chapter 3"
        assert chapters[1]["title"] == "Chapter 1"
        assert chapters[2]["title"] == "Chapter 2"
