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
import zipfile

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


# ---------------------------------------------------------------------------
# KAN-226 EPUB-path regression: synthetic equivalent of LC's kan226-valid.epub
# (fixture absent locally; built in-test with zipfile only, ~15 KB).
# Shape: cover + copyright/publisher page + title page + 3 sections all
# headed "Chapter 1" + real chapters 2-4.
# ---------------------------------------------------------------------------

def _xhtml(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml">'
        "<head><title>t</title></head><body>\n" + body + "\n</body></html>\n"
    )


def _chapter_body(head: str, n_paras: int, seed: str) -> str:
    paras = "\n".join(
        f"<p>Paragraph {seed} {i} of the narrative body text for {head}. "
        "The road continued past the hills into the wide valley beyond.</p>"
        for i in range(n_paras)
    )
    return f"<h1>{head}</h1>\n{paras}"


def build_kan226_epub(path) -> None:
    """Cover + copyright + title page + 3x 'Chapter 1' + chapters 2-4."""
    cover = _xhtml('<div class="cover"><h1 class="cover-title">KAN226 VALID</h1></div>')
    copyright_page = _xhtml(
        "<p>ACME PRESS</p>\n<p>New York</p>\n"
        "<p>Copyright &#169; 2026 by Jane Author</p>\n"
        "<p>All rights reserved. No part of this book may be reproduced.</p>\n"
        "<p>ISBN 978-0-000000-00-0</p>\n<p>First Edition</p>"
    )
    title_page = _xhtml(
        '<div class="titlepage"><h1>KAN226 VALID</h1>'
        "<p>A Novel of Duplicate Chapter Ones</p></div>"
    )
    docs = [
        ("cover.xhtml", cover),
        ("copyright.xhtml", copyright_page),
        ("titlepage.xhtml", title_page),
        # 3 fragments all headed Chapter 1 (short TOC-lift style) ...
        ("ch1a.xhtml", _chapter_body("Chapter 1", 4, "alpha")),
        ("ch1b.xhtml", _chapter_body("Chapter 1", 5, "beta")),
        # ... and the real Chapter 1 with the dominant body
        ("ch1.xhtml", _chapter_body("Chapter 1: The Beginning", 42, "real")),
        ("ch2.xhtml", _chapter_body("Chapter 2: The Road", 42, "two")),
        ("ch3.xhtml", _chapter_body("Chapter 3: The City", 42, "three")),
        ("ch4.xhtml", _chapter_body("Chapter 4: The End", 42, "four")),
    ]
    manifest = "".join(
        f'<item id="d{i}" href="{name}" media-type="application/xhtml+xml"/>'
        for i, (name, _) in enumerate(docs)
    )
    spine = "".join(f'<itemref idref="d{i}"/>' for i in range(len(docs)))
    opf = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        'unique-identifier="uid"><metadata '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:identifier id="uid">urn:uuid:kan226-synth</dc:identifier>'
        "<dc:title>KAN226 VALID</dc:title><dc:creator>Jane Author</dc:creator>"
        '<dc:language>en</dc:language></metadata>'
        f"<manifest>{manifest}</manifest><spine>{spine}</spine></package>"
    )
    with zipfile.ZipFile(path, "w") as z:
        info = zipfile.ZipInfo("mimetype")
        z.writestr(info, "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?><container '
            'xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">'
            '<rootfiles><rootfile full-path="OEBPS/content.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles></container>',
        )
        z.writestr("OEBPS/content.opf", opf)
        for name, content in docs:
            z.writestr(f"OEBPS/{name}", content)


class TestKan226EpubUploadFilterAndCh1Collapse:
    """End-to-end spine extraction: no non-chapter chapters, single Ch1."""

    def setup_method(self):
        self.service = FileService()

    def test_copyright_page_not_captured_and_ch1_collapsed(self, tmp_path):
        epub_path = tmp_path / "kan226_synth.epub"
        build_kan226_epub(epub_path)

        extracted = self.service.extract_epub_chapters(str(epub_path))
        chapters = [c for c in extracted if c.get("content_type") == "chapter"]

        # (a) No copyright/publisher/title content among the chapters.
        chapter_titles = [c["title"] for c in chapters]
        assert "ACME PRESS" not in chapter_titles
        assert "KAN226 VALID" not in chapter_titles
        assert all(c.get("use_in_generation") is True for c in chapters)

        # The copyright page is preserved but classified as non-chapter.
        non_chapter = [c for c in extracted if c.get("content_type") != "chapter"]
        assert any(
            c.get("title") == "ACME PRESS" and c.get("content_type") == "metadata"
            for c in non_chapter
        )
        assert all(c.get("number") in (None, "") for c in non_chapter)
        assert all(c.get("use_in_generation") is False for c in non_chapter)

        # (b) Exactly one Chapter 1 - the dominant real body - remains.
        ch1 = [c for c in chapters if str(c.get("number")) == "1"]
        assert len(ch1) == 1
        assert ch1[0]["title"] == "Chapter 1: The Beginning"
        assert len(ch1[0]["content"]) > 3000

        # Heading-derived sequence is intact: 1, 2, 3, 4 (not 2..7 drift).
        assert [str(c["number"]) for c in chapters] == ["1", "2", "3", "4"]
        assert [c["title"] for c in chapters] == [
            "Chapter 1: The Beginning",
            "Chapter 2: The Road",
            "Chapter 3: The City",
            "Chapter 4: The End",
        ]


class TestKan226DedupeDominanceRule:
    """Fragments collapse; comparable OCR-collided real chapters survive."""

    def setup_method(self):
        self.service = FileService()

    def test_dominant_real_chapter_collapses_fragments(self):
        chapters = [
            _mk("Chapter 1", "1", "fragment body text. " * 30),
            _mk("Chapter 1", "1", "slightly longer fragment body. " * 36),
            _mk("Chapter 1: The Beginning", "1", "real body. " * 400),
        ]
        result = self.service._dedupe_chapters_by_number(chapters)
        assert len(result) == 1
        assert result[0]["title"] == "Chapter 1: The Beginning"

    def test_comparable_duplicates_are_kept_for_unique_renumbering(self):
        # KAN-227 semantics: two full-length chapters whose OCR'd heading
        # numbers collided must both survive (renumbering disambiguates).
        chapters = [
            _mk("CHAPTER 1. First Voyage", "1", "real narrative body. " * 140),
            _mk("CHAPTER 1. Second Voyage", "1", "real narrative body. " * 133),
            _mk("CHAPTER 2. Third Voyage", "2", "real narrative body. " * 140),
        ]
        result = self.service._dedupe_chapters_by_number(chapters)
        assert len(result) == 3
        assert {c["title"] for c in result} == {
            "CHAPTER 1. First Voyage",
            "CHAPTER 1. Second Voyage",
            "CHAPTER 2. Third Voyage",
        }

    def test_ratio_boundary_drops_only_clear_fragments(self):
        # 100 vs 300 chars: 300 >= 2x100 -> fragment dropped.
        chapters = [
            _mk("Chapter 1: short", "1", "x" * 100),
            _mk("Chapter 1: real", "1", "y" * 300),
        ]
        result = self.service._dedupe_chapters_by_number(chapters)
        assert [c["title"] for c in result] == ["Chapter 1: real"]

        # 200 vs 300 chars: comparable -> both kept.
        chapters = [
            _mk("Chapter 1: near", "1", "x" * 200),
            _mk("Chapter 1: real", "1", "y" * 300),
        ]
        result = self.service._dedupe_chapters_by_number(chapters)
        assert len(result) == 2


class TestKan226CopyrightPageClassifier:
    """Publisher/copyright pages must classify as metadata, not chapters."""

    def setup_method(self):
        self.service = FileService()

    def test_copyright_href_classifies_as_metadata(self):
        result = self.service._classify_spine_item(
            "ACME PRESS", "OEBPS/copyright.xhtml", 30
        )
        assert result == "metadata"

    def test_boilerplate_content_classifies_as_metadata(self):
        # Publisher page at a non-obvious href, no keyword title: the legal
        # boilerplate in the body must flag it.
        content = (
            "ACME PRESS\nNew York\nCopyright \u00a9 2026 by Jane Author\n"
            "All rights reserved.\nISBN 978-0-000000-00-0"
        )
        result = self.service._classify_spine_item(
            "ACME PRESS", "OEBPS/press1.xhtml", 24, content=content
        )
        assert result == "metadata"

    def test_real_chapter_content_not_flagged(self):
        content = (
            "The morning brought news of the copyright dispute at the mill, "
            "and the town woke to the sound of bells. " * 40
        )
        result = self.service._classify_spine_item(
            "Chapter 5: The Mill", "OEBPS/ch5.xhtml", 880, content=content
        )
        assert result == "chapter"

    def test_no_content_argument_keeps_prior_behavior(self):
        # Callers without body text (structural filter re-classification)
        # still get title/href classification only.
        result = self.service._classify_spine_item("The Long Road", "ch5.xhtml", 900)
        assert result == "chapter"
