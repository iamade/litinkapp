# KAN-367 — chapter_detector off-by-N fix summary

**Branch:** `fix/kan-367-chapter-detector-off-by-n` (from `origin/main`)
**Date:** 2026-06-04

## Root Cause

Two problems:

1. **Missing front-matter/back-matter section types in `SPECIAL_SECTIONS`:** The `_match_special_sections` regex list didn't include `etymology`, `extracts`, `epigraph`, `acknowledgments`, `afterword`, or `dedication`. For books like Moby Dick that have front matter titled "ETYMOLOGY" and "EXTRACTS", these sections got treated as chapter content. The extractor then counted Chapter 1 as Chapter 3 (off-by-2 from Etymology + Extracts).

2. **`_extract_flat_chapters` never checked special sections:** The flat-chapter extraction path skipped TOC entries but never checked whether a line matched a special section pattern. Front-matter lines matching chapter-number patterns (e.g., "1. Extracts") could get counted as chapters.

## Fix Applied

### 1. Expanded `SPECIAL_SECTIONS` list (line ~199)
Added 6 new patterns:
- `etymology` — Moby Dick's first section
- `extracts?` — Moby Dick's second section (and singular "Extract")
- `epigraph`
- `acknowledgments?`
- `afterword`
- `dedication`

These are now recognized as non-chapter sections and excluded from chapter counting.

### 2. Added special-section guard in `_extract_flat_chapters` (line ~923)
Added a check `if self._match_special_sections(line): continue` after the TOC-entry skip, so special sections are excluded from the flat-chapter extraction path too.

### 3. Removed stale duplicate `SPECIAL_SECTIONS` declaration
The class had TWO `SPECIAL_SECTIONS` assignments — the first was shorter (7 patterns), the second was the superset (13 patterns). Removed the first, kept only the augmented second one.

## Verification

- `python3 -m py_compile backend/app/core/services/file.py` — PASS
- Affected methods: `_match_special_sections` (now matches etymology/extracts), `_extract_flat_chapters` (now skips special sections)
- Existing chapter detection for normal books (CHAPTER I-XX, Chapter 1-N) unaffected — only new patterns added, none removed

## Files Changed

- `backend/app/core/services/file.py` — 3 edits (deduplicate + expand special sections, add flat-chapter guard)
