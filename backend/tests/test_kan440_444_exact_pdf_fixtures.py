import contextlib
import hashlib
import io
from pathlib import Path

import fitz

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
