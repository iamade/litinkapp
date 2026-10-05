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


def test_exact_fixture_checksums_are_the_psq_gate_files():
    assert _sha256(ORWELL_PDF) == (
        "6067532ebccc52462efd067f8983785cd6c3c1b07259180963863ca51383cb42"
    )
    assert _sha256(FRANK_PDF) == (
        "2acdebda2e0111d3f5460fb3a1f63e00a617d8e6a10dfa68924081a37af6bd9a"
    )


def test_orwell_exact_pdf_preserves_front_body_parts_and_appendix():
    service = FileService()
    result = _detect_quietly(service, _pdf_text(ORWELL_PDF))

    sections = result["sections"]
    assert result["has_sections"] is True
    assert [section["title"] for section in sections] == [
        "Front Matter",
        "PART ONE",
        "PART TWO",
        "PART THREE",
        "APPENDIX.",
    ]

    assert sections[0]["content_type"] == "front_matter"
    assert sections[-1]["content_type"] == "back_matter"
    assert [len(section.get("chapters") or []) for section in sections] == [
        0,
        8,
        9,
        6,
        0,
    ]
    assert sum(len(section.get("chapters") or []) for section in sections) == 23

    titles = [section["title"] for section in sections]
    assert not any("book is indestructible" in title for title in titles)
    assert not any("content with negative obedience" in title for title in titles)


def test_frank_exact_pdf_rejects_gappy_page_number_direct_detection():
    service = FileService()
    lines = _pdf_text(FRANK_PDF).split("\n")

    with contextlib.redirect_stdout(io.StringIO()):
        direct_headers = service.structure_detector._find_chapter_number_and_title(lines)

    assert direct_headers == []


def test_frank_exact_pdf_bookmarks_preserve_volume_hierarchy_for_save():
    service = FileService()
    doc = fitz.open(FRANK_PDF)

    with contextlib.redirect_stdout(io.StringIO()):
        chapters = service._process_pdf_bookmarks(doc, doc.get_toc())
        sections = service._organize_chapters_into_sections(chapters)
        entries = service._iter_confirmed_structure_entries(sections)

    body_chapters = [
        chapter for chapter in chapters if chapter.get("content_type") == "chapter"
    ]
    front_matter = [
        chapter for chapter in chapters if chapter.get("content_type") == "front_matter"
    ]
    section_entries = [entry for entry in entries if entry["kind"] == "section"]
    persisted_body = [
        entry
        for entry in entries
        if entry["kind"] == "chapter"
        and entry["data"].get("content_type", "chapter") == "chapter"
    ]
    persisted_front = [
        entry
        for entry in entries
        if entry["kind"] == "chapter"
        and entry["data"].get("content_type") == "front_matter"
    ]

    assert [section["title"] for section in sections] == [
        "Main Content",
        "Volume I",
        "Volume II",
        "Volume III",
    ]
    assert [len(section["chapters"]) for section in sections] == [1, 11, 9, 7]
    assert len(body_chapters) == 27
    assert len(front_matter) == 1
    assert len(section_entries) == 3
    assert len(persisted_body) == 27
    assert len(persisted_front) == 1
    assert all(entry["section_key"] for entry in persisted_body)
    assert all(entry["section_key"] is None for entry in persisted_front)

def _last_president_like_text() -> str:
    romans = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    titles = [
        "The Reign of Confusion",
        "A Strange Message",
        "The Great Election",
        "The People Awake",
        "Dark Counsel",
        "The March Begins",
        "A Nation Trembles",
        "The Hidden Hand",
        "The Last President",
        "After the Storm",
    ]

    def prose(label: str, lines: int = 14) -> list[str]:
        return [
            f"{label} narrative line {idx} carries enough production-shaped text for the detector to treat it as body content."
            for idx in range(lines)
        ]

    lines = [
        "THE LAST PRESIDENT",
        "PREFACE",
        *prose("front matter", 12),
    ]
    page_number = 1
    for idx, (roman, title) in enumerate(zip(romans, titles), start=1):
        lines.extend([str(page_number), f"CHAPTER {roman}", title, *prose(f"chapter {idx}", 14)])
        page_number += 1
        if idx <= 4:
            lines.extend([
                str(page_number),
                f"Continuation fragment {idx}",
                *prose(f"chapter {idx} continuation", 14),
            ])
            page_number += 1
    lines.extend(["AFTERWORD", *prose("back matter", 12)])
    return "\n".join(lines)


def test_last_president_like_pdf_text_keeps_roman_chapters_and_continuations():
    service = FileService()
    result = _detect_quietly(service, _last_president_like_text())

    sections = result["sections"] or []
    chapters = [chapter for section in sections for chapter in section.get("chapters") or []]

    assert result["has_sections"] is True
    assert [chapter["number"] for chapter in chapters] == [str(i) for i in range(1, 11)]
    assert [chapter["title"] for chapter in chapters] == [
        "Chapter I: The Reign of Confusion",
        "Chapter II: A Strange Message",
        "Chapter III: The Great Election",
        "Chapter IV: The People Awake",
        "Chapter V: Dark Counsel",
        "Chapter VI: The March Begins",
        "Chapter VII: A Nation Trembles",
        "Chapter VIII: The Hidden Hand",
        "Chapter IX: The Last President",
        "Chapter X: After the Storm",
    ]
    assert any(section.get("content_type") == "front_matter" for section in sections)
    assert any(section.get("content_type") == "back_matter" for section in sections)
    assert not any("Continuation fragment" in chapter["title"] for chapter in chapters)
    assert "chapter 1 continuation narrative line 13" in chapters[0]["content"]


# --- KAN-440 regression tests: section-scoped dedupe + matter numbering +
# bare-heading title cap ---


def test_kan440_cross_part_duplicate_numbers_are_section_scoped():
    """Per-PART numbering restarts must not collide in _dedupe_chapters_by_number.

    The real defect: orwell1984.pdf PART bodies with the same number were
    compared across sections — a near-tie (21365*2=42730 <= 42828) dropped a
    real chapter, losing 5 of 23. Intra-section dominance must still fire,
    and flat/section-less lists keep KAN-226 behavior byte-for-byte.
    """
    service = FileService()

    def _mk(title, number, body, section_title=None, section_number=None):
        chapter = {
            "title": title,
            "number": number,
            "content": body,
            "content_type": "chapter",
        }
        if section_title is not None:
            chapter["section_title"] = section_title
            chapter["section_number"] = section_number
        return chapter

    cross_part = [
        _mk("Chapter 8", "8", "x" * 21365, "PART ONE", "1"),
        _mk("Chapter 8", "8", "y" * 42828, "PART THREE", "3"),
        _mk("Chapter 5", "5", "z" * 8492, "PART TWO", "2"),
        _mk("Chapter 5", "5", "w" * 29118, "PART THREE", "3"),
    ]
    with contextlib.redirect_stdout(io.StringIO()):
        kept = service._dedupe_chapters_by_number(cross_part)
    assert [c["title"] for c in kept] == ["Chapter 8", "Chapter 8", "Chapter 5", "Chapter 5"]

    intra_section = [
        _mk("Chapter 2", "2", "frag " * 40, "PART ONE", "1"),
        _mk("Chapter 2", "2", "real " * 400, "PART ONE", "1"),
    ]
    with contextlib.redirect_stdout(io.StringIO()):
        kept_intra = service._dedupe_chapters_by_number(intra_section)
    assert len(kept_intra) == 1
    assert kept_intra[0]["title"] == "Chapter 2"

    flat = [
        {"title": "Chapter 1", "number": "1", "content": "frag " * 40, "content_type": "chapter"},
        {"title": "Chapter 1", "number": "1", "content": "real " * 400, "content_type": "chapter"},
    ]
    with contextlib.redirect_stdout(io.StringIO()):
        kept_flat = service._dedupe_chapters_by_number(flat)
    assert len(kept_flat) == 1


@pytest.mark.asyncio
async def test_kan440_front_back_matter_hierarchical_numbering_is_none():
    """Front/back matter sections must surface chapter_number=None.

    At base, Front Matter consumed chapter slot 1 and APPENDIX surfaced as
    chapter 25 in the BookView — read-only matter must stay unnumbered.
    """
    service = FileService()
    filler = " ".join(["narrative body words"] * 120)
    structure = {
        "has_sections": True,
        "structure_type": "book",
        "sections": [
            {
                "title": "Front Matter",
                "type": "special",
                "content_type": "front_matter",
                "content": filler,
                "chapters": [],
            },
            {
                "title": "PART ONE",
                "type": "part",
                "number": "1",
                "chapters": [
                    {"title": "Chapter 1", "number": "1", "content": filler, "content_type": "chapter"},
                    {"title": "Chapter 2", "number": "2", "content": filler, "content_type": "chapter"},
                ],
            },
            {
                "title": "APPENDIX.",
                "type": "special",
                "content_type": "back_matter",
                "content": filler,
                "chapters": [],
            },
        ],
    }

    with contextlib.redirect_stdout(io.StringIO()):
        chapters = await service._extract_hierarchical_chapters(
            structure, book_type="entertainment", book_content=filler
        )

    assert [c["content_type"] for c in chapters] == [
        "front_matter",
        "chapter",
        "chapter",
        "back_matter",
    ]
    assert chapters[0]["chapter_number"] is None
    assert chapters[-1]["chapter_number"] is None
    assert [c["chapter_number"] for c in chapters[1:3]] == [2, 3]


def test_kan440_bare_numbered_heading_caps_prose_subtitle():
    """A bare numbered heading must not absorb the next prose line as subtitle.

    Real short titles on the next line (Last-President shape) are still
    appended; running narrative prose (orwell shape: 52-char sentence that
    passes the semantic filter) is never appended.
    """
    service = FileService()

    def prose(label: str, lines: int = 14) -> str:
        return "\n".join(
            f"{label} narrative line {idx} carries enough body text for detection."
            for idx in range(lines)
        )

    content = "\n\n".join(
        [
            "PART ONE",
            "Chapter 1",
            "It was a bright cold day in April, and the clocks were striking thirteen.",
            prose("chapter 1"),
            "Chapter 2",
            "Winston looked round the shabby little room above Mr Charrington",
            prose("chapter 2"),
            "PART TWO",
            "Chapter 3",
            "The Reign of Confusion",
            prose("chapter 3"),
        ]
    )

    result = _detect_quietly(service, content)
    titles = [
        chapter["title"]
        for section in (result["sections"] or [])
        for chapter in section.get("chapters") or []
    ]

    assert "Chapter 1" in titles
    assert "Chapter 2" in titles
    assert "Chapter 3: The Reign of Confusion" in titles
    assert not any("bright cold day" in title for title in titles)
    assert not any("shabby little room" in title for title in titles)
