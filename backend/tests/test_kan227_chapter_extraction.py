"""
KAN-227 reproduction + regression tests — book chapter extraction incomplete +
numbering mismatch.

Root causes pinned by this suite (BEFORE state on base 18dbe51):

1. COMPLETENESS (EPUB): ``FileService._split_spine_item_by_headings``
   (backend/app/core/services/file.py) collected chapter content by walking
   ``heading.next_sibling``. When an EPUB wraps each heading in its own
   container (Project-Gutenberg shape: ``<div class="chapter"><h2>…</h2></div>``
   followed by sibling ``<p>`` blocks), the heading's next sibling is ``None``,
   every sub-chapter gets empty content (< 100 chars) and is silently dropped
   ("Skipping short sub-chapter"). A 50-chapter book collapsed to 47 via the
   partial aggregate fallback; real books (Moby-Dick) collapse to ~11/136.

2. NUMBERING: bundled/derived extraction renumbered chapters by extraction
   order instead of deriving numbers from the detected headings, so a book
   whose headings read CHAPTER 9 / 49 / 131 was labelled 1 / 2 / 3 (drift), and
   OCR-noised duplicates produced repeated numbers (1,1,1,1,1).

Fixtures are synthetic EPUBs constructed IN-TEST via zipfile (no binaries
committed).
"""

import io
import re
import zipfile

import pytest

from app.core.services.file import FileService


# ---------------------------------------------------------------------------
# Synthetic EPUB fixture builder (in-test, zipfile-only)
# ---------------------------------------------------------------------------

_CONTAINER = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

_NCX = """<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/">
  <head><meta name="dtb:uid" content="kan227-test"/></head>
  <docTitle><text>KAN227 Synthetic</text></docTitle>
  <navMap></navMap>
</ncx>
"""

_OPF = """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="id" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="id">kan227-test</dc:identifier>
    <dc:title>KAN227 Synthetic</dc:title>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    {manifest_items}
  </manifest>
  <spine toc="ncx">
    {spine_items}
  </spine>
</package>
"""


def _chapter_paragraphs(tag: str) -> str:
    para = (
        f"This is the narrative body of {tag}. The whale swam onward through "
        "the pale green sea while the crew mended ropes and mended sails. "
        * 8
    )
    return f"<p>{para}</p><p>{para}</p>"


def build_synthetic_epub(path, items, wrapped: bool = True) -> int:
    """Build a synthetic EPUB at *path*.

    *items* is a list of spine documents; each document is a list of
    ``(heading_text, body_tag)`` tuples. ``wrapped=True`` reproduces the
    Project-Gutenberg/Moby-Dick shape where the heading lives inside its own
    ``<div class="chapter">`` wrapper and the narrative paragraphs follow as
    siblings of the wrapper (the KAN-227 completeness breaker).

    Returns the expected chapter count.
    """
    manifest_items, spine_items, files = [], [], []
    expected = 0

    for item_idx, headings in enumerate(items):
        fname = f"doc{item_idx}.xhtml"
        body = (
            '<?xml version="1.0"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml">'
            "<head><title>t</title></head><body>\n"
        )
        for heading_text, body_tag in headings:
            if wrapped:
                body += (
                    f'<div class="chapter"><h2>{heading_text}</h2></div>'
                    f"{_chapter_paragraphs(body_tag)}"
                )
            else:
                body += f"<h2>{heading_text}</h2>{_chapter_paragraphs(body_tag)}"
            expected += 1
        body += "\n</body></html>"
        files.append((f"OEBPS/{fname}", body))
        manifest_items.append(
            f'<item id="d{item_idx}" href="{fname}" '
            'media-type="application/xhtml+xml"/>'
        )
        spine_items.append(f'<itemref idref="d{item_idx}"/>')

    opf = _OPF.format(
        manifest_items="\n    ".join(manifest_items),
        spine_items="\n    ".join(spine_items),
    )

    with zipfile.ZipFile(path, "w") as z:
        info = zipfile.ZipInfo("mimetype")
        z.writestr(info, "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", _CONTAINER)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/toc.ncx", _NCX)
        for name, content in files:
            z.writestr(name, content)

    return expected


def _chapters_only(extracted):
    return [c for c in extracted if c.get("content_type") == "chapter"]


def _numbers(chapters):
    return [str(c.get("number")) for c in chapters]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBundledSpineCompleteness:
    """Defect (a): bundled spine items must not collapse real chapters."""

    def setup_method(self):
        self.service = FileService()

    _ROMAN = [
        "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
        "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX",
        "XX", "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI", "XXVII",
        "XXVIII", "XXIX", "XXX", "XXXI", "XXXII", "XXXIII", "XXXIV",
        "XXXV", "XXXVI", "XXXVII", "XXXVIII", "XXXIX", "XL", "XLI",
        "XLII", "XLIII", "XLIV", "XLV", "XLVI", "XLVII", "XLVIII",
        "XLIX", "L", "LI", "LII", "LIII", "LIV", "LV", "LVI", "LVII",
        "LVIII", "LIX",
    ]

    def test_canonical_ge_roman_bundled_full_set(self, tmp_path, capsys):
        """KAN-445 canonical shape: GE has 59 chapters (Chapter I..LIX).

        Bare trailing-dot roman headings (``Chapter I.``) bundled 15/15/15/14
        per spine item, each heading wrapped in its own div. BEFORE (base
        18dbe51): the prose-title filter rejected every heading, the split
        collapsed, and only 4 chapter-like items survived via the aggregate
        fallback — the exact Mac Retest c16876 symptom (1 recognized chapter).
        """
        epub_path = tmp_path / "canonical-ge.epub"
        per_item = [15, 15, 15, 14]
        roman = iter(self._ROMAN)
        items = [
            [(f"Chapter {next(roman)}.", f"chapter {n}") for n in range(lo, lo + cnt)]
            for lo, cnt in zip((1, 16, 31, 46), per_item)
        ]
        expected = build_synthetic_epub(epub_path, items, wrapped=True)
        assert expected == 59

        extracted = self.service.extract_epub_chapters(str(epub_path))
        chapters = _chapters_only(extracted)

        out = capsys.readouterr().out
        assert len(chapters) == 59, (
            f"expected 59 chapters, got {len(chapters)}\n"
            "--- extraction log tail ---\n"
            + "\n".join(out.splitlines()[-25:])
        )
        assert _numbers(chapters) == [str(n) for n in range(1, 60)]
        assert chapters[0]["title"] == "Chapter I."
        assert chapters[58]["title"] == "Chapter LIX."

    def test_wrapped_headings_extract_all_chapters(self, tmp_path, capsys):
        """Moby-Dick shape: 5 spine items x 10 wrapped-heading chapters = 50.

        BEFORE (base 18dbe51): split path produced empty-content sub-chapters,
        all 50 were skipped, aggregate fallback recovered only 47 chapters.
        """
        epub_path = tmp_path / "bundled.epub"
        items = [
            [(f"CHAPTER {n}. Voyage {n}", f"chapter {n}") for n in range(lo, lo + 10)]
            for lo in (1, 11, 21, 31, 41)
        ]
        expected = build_synthetic_epub(epub_path, items, wrapped=True)

        extracted = self.service.extract_epub_chapters(str(epub_path))
        chapters = _chapters_only(extracted)

        out = capsys.readouterr().out
        assert len(chapters) == expected, (
            f"expected {expected} chapters, got {len(chapters)}; numbers: "
            f"{_numbers(chapters)}\n--- extraction log tail ---\n"
            + "\n".join(out.splitlines()[-25:])
        )
        assert _numbers(chapters) == [str(n) for n in range(1, 51)]

    def test_flat_sibling_headings_still_split(self, tmp_path):
        """Control: original flat-sibling shape must keep working (50/50)."""
        epub_path = tmp_path / "flat.epub"
        items = [
            [(f"CHAPTER {n}. Voyage {n}", f"chapter {n}") for n in range(lo, lo + 10)]
            for lo in (1, 11, 21, 31, 41)
        ]
        expected = build_synthetic_epub(epub_path, items, wrapped=False)

        extracted = self.service.extract_epub_chapters(str(epub_path))
        chapters = _chapters_only(extracted)

        assert len(chapters) == expected
        assert _numbers(chapters) == [str(n) for n in range(1, 51)]


class TestNumberingDerivedFromHeadings:
    """Defect (b): numbers must come from detected headings, not drift."""

    def setup_method(self):
        self.service = FileService()

    def test_sparse_heading_numbers_do_not_drift(self, tmp_path):
        """Headings CHAPTER 9 / 49 / 131 must stay 9 / 49 / 131.

        Ticket symptom: App Ch2 was really CHAPTER 9, Ch5 really 49,
        Ch10 really 131 — sequential renumbering overwrote the real numbers.
        """
        epub_path = tmp_path / "sparse.epub"
        items = [
            [
                ("CHAPTER 9. The Lee Shore", "chapter nine"),
                ("CHAPTER 49. The Hyena", "chapter forty-nine"),
                ("CHAPTER 131. The Pequod Meets The Delight", "chapter 131"),
            ]
        ]
        build_synthetic_epub(epub_path, items, wrapped=True)

        extracted = self.service.extract_epub_chapters(str(epub_path))
        chapters = _chapters_only(extracted)

        assert _numbers(chapters) == ["9", "49", "131"]
        assert [c["title"] for c in chapters] == [
            "CHAPTER 9. The Lee Shore",
            "CHAPTER 49. The Hyena",
            "CHAPTER 131. The Pequod Meets The Delight",
        ]

    def test_flat_text_extraction_preserves_heading_numbers(self):
        """Flat-text path: detected heading numbers must not be renumbered away.

        Uses II / V / IX so a sequential overwrite (1, 2, 3) is unambiguous.
        """
        filler = "\n".join(
            f"Narrative line {i} of the chapter body text." for i in range(60)
        )
        content = (
            "CHAPTER II. The Carpet-Bag\n" + filler
            + "\nCHAPTER V. Breakfast\n" + filler
            + "\nCHAPTER IX. The Sermon\n" + filler
        )

        items = self.service.structure_detector._extract_flat_chapters(content)
        chapters = _chapters_only(items)

        assert _numbers(chapters) == ["2", "5", "9"]

    def test_flat_text_sequential_fallback_when_no_heading_numbers(self):
        """Fallback: chapters without heading numbers still get 1..N order."""
        filler = "\n".join(
            f"Narrative line {i} of the chapter body text." for i in range(60)
        )
        content = (
            "PROLOGUE\n" + filler
            + "\nCHAPTER II. The Carpet-Bag\n" + filler
            + "\nCHAPTER V. Breakfast\n" + filler
        )

        items = self.service.structure_detector._extract_flat_chapters(content)
        chapters = _chapters_only(items)

        # Detected numbers (2, 5) are kept verbatim; nothing may renumber them.
        assert _numbers(chapters) == ["2", "5"]
        front = [i for i in items if i.get("content_type") != "chapter"]
        assert all(i.get("number") in (None, "") for i in front)

    def test_duplicate_heading_numbers_do_not_repeat(self, tmp_path, capsys):
        """OCR-noised duplicate heading numbers must never emit 1,1,1.

        When heading-derived numbers collide, extraction order is the only
        trustworthy sequence — the final output numbers must be unique.
        """
        epub_path = tmp_path / "dupes.epub"
        items = [
            [
                ("CHAPTER 1. First Voyage", "first chapter"),
                ("CHAPTER 1. Second Voyage", "second chapter"),
                ("CHAPTER 2. Third Voyage", "third chapter"),
            ]
        ]
        build_synthetic_epub(epub_path, items, wrapped=True)

        extracted = self.service.extract_epub_chapters(str(epub_path))
        chapters = _chapters_only(extracted)

        numbers = _numbers(chapters)
        assert len(chapters) == 3
        assert len(set(numbers)) == len(numbers), (
            f"duplicate chapter numbers emitted: {numbers}"
        )


class TestProseFilterExemption:
    """Chapter-pattern headings must never be rejected as narrative prose."""

    def setup_method(self):
        self.service = FileService()

    def test_structural_chapter_heading_detection(self):
        """``Chapter I.`` is prose-filtered yet a real structural heading."""
        for title in (
            "Chapter I.",
            "CHAPTER XX.",
            "Chapter 3",
            "CHAPTER 9. The Lee Shore",
            "II.",
            "3. The Chase",
        ):
            assert self.service._is_structural_chapter_heading(title), title
        # Body text stays rejected.
        for title in (
            "It was the best of times, it was the worst of times",
            "And then the whale surfaced, and everyone shouted",
            "",
        ):
            assert not self.service._is_structural_chapter_heading(title), title

    def test_bare_roman_heading_survives_split(self, tmp_path):
        """Splitter keeps ``Chapter I.`` headings (KAN-445 canonical shape)."""
        from bs4 import BeautifulSoup

        html = (
            '<html><head><title>t</title></head><body>'
            '<div class="chapter"><h2>Chapter I.</h2></div><p>first body</p>'
            '<div class="chapter"><h2>Chapter II.</h2></div><p>second body</p>'
            "</body></html>"
        )
        soup = BeautifulSoup(html, "lxml")
        subs = self.service._split_spine_item_by_headings(soup, 0)
        assert subs is not None
        assert [s["title"] for s in subs] == ["Chapter I.", "Chapter II."]
        assert "first body" in subs[0]["content"]
        assert "second body" in subs[1]["content"]
