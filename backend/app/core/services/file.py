import uuid
import aiofiles
from fastapi import UploadFile
from typing import Dict, Any, Optional, List
import os
import PyPDF2
import docx
import fitz  # PyMuPDF
from app.core.config import settings
import re
from app.core.services.ai import AIService
from sqlmodel.ext.asyncio.session import AsyncSession
from app.books.schemas import BookCreate, ChapterCreate, BookUpdate
import tempfile
import math
import hashlib
import json
import time
from app.core.services.text_utils import TextSanitizer
import itertools
import traceback
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


class BookStructureDetector:
    def __init__(self):
        # Enhanced patterns for different book structures
        self.STRUCTURE_PATTERNS = {
            "tablet": {
                "patterns": [
                    r"(?i)^tablet\s+([ivx]+|\d+)[\s\-:]*(.{10,})$",
                    r"(?i)^clay\s+tablet\s+([ivx]+|\d+)[\s\-:]*(.{10,})$",
                ],
                "indicators": [
                    "tablet",
                    "clay",
                    "cuneiform",
                    "mesopotamian",
                    "sumerian",
                    "babylonian",
                ],
                "typical_count": (1, 12),
            },
            "book": {
                "patterns": [
                    r"(?i)^book\s+(\d+|[ivx]+|one|two|three|four|five|six|seven|eight|nine|ten)[\s\-:]*(.{10,})$",
                    r"(?i)^volume\s+(\d+|[ivx]+)[\s\-:]*(.{10,})$",
                ],
                "indicators": ["book", "volume", "tome", "part"],
                "typical_count": (2, 10),
            },
            "part": {
                "patterns": [
                    r"(?i)^part\s+(\d+|[ivx]+|one|two|three|four|five|six|seven|eight|nine|ten)[\s\-:]*(.{10,})$",
                    r"(?i)^section\s+(\d+|[ivx]+)[\s\-:]*(.{10,})$",
                ],
                "indicators": ["part", "section", "division"],
                "typical_count": (2, 8),
            },
            "act": {
                "patterns": [
                    r"(?i)^act\s+([ivx]+|\d+)[\s\-:]*(.{10,})$",
                    r"(?i)^scene\s+([ivx]+|\d+)[\s\-:]*(.{10,})$",
                ],
                "indicators": ["act", "scene", "drama", "play", "theatre", "theater"],
                "typical_count": (3, 7),
            },
            "movement": {
                "patterns": [
                    r"(?i)^movement\s+([ivx]+|\d+)[\s\-:]*(.{10,})$",
                    r"(?i)^symphony\s+([ivx]+|\d+)[\s\-:]*(.{10,})$",
                ],
                "indicators": ["movement", "symphony", "concerto", "sonata", "musical"],
                "typical_count": (3, 6),
            },
            "canto": {
                "patterns": [
                    r"(?i)^canto\s+([ivx]+|\d+)[\s\-:]*(.{10,})$",
                    r"(?i)^song\s+([ivx]+|\d+)[\s\-:]*(.{10,})$",
                ],
                "indicators": ["canto", "song", "verse", "epic", "poem"],
                "typical_count": (10, 100),
            },
        }

        # COMPREHENSIVE CHAPTER PATTERNS - handles multiple book formats
        # Ordered by specificity (most specific first)
        self.WORD_TO_NUMBER = {
            "ONE": 1,
            "TWO": 2,
            "THREE": 3,
            "FOUR": 4,
            "FIVE": 5,
            "SIX": 6,
            "SEVEN": 7,
            "EIGHT": 8,
            "NINE": 9,
            "TEN": 10,
            "ELEVEN": 11,
            "TWELVE": 12,
            "THIRTEEN": 13,
            "FOURTEEN": 14,
            "FIFTEEN": 15,
            "SIXTEEN": 16,
            "SEVENTEEN": 17,
            "EIGHTEEN": 18,
            "NINETEEN": 19,
            "TWENTY": 20,
            "THIRTY": 30,
            "FORTY": 40,
            "FIFTY": 50,
            "SIXTY": 60,
            "SEVENTY": 70,
            "EIGHTY": 80,
            "NINETY": 90,
            "HUNDRED": 100,
        }

        # Build regex for spelled out numbers
        number_words = "|".join(self.WORD_TO_NUMBER.keys())
        # Regex for compound numbers like "TWENTY-ONE" or "THIRTY TWO"
        self.SPELLED_NUMBER_RE = (
            f"((?:{number_words})(?:[\\\\s\\\\-]*(?:{number_words}))?)"
        )

        self.CHAPTER_PATTERNS = [
            # Roman numerals with CHAPTER keyword (like "CHAPTER XIX.")
            r"^\s*CHAPTER\s+([IVXLCDM]+)\.?\s*$",  # CHAPTER XIX. or CHAPTER XIX
            r"^\s*CHAPTER\s+([IVXLCDM]+)[\.\s]*(.+)$",  # CHAPTER I. Title or CHAPTER I Title
            r"^\s*Chapter\s+([IVXLCDM]+)\.?\s*$",  # Chapter XIX. or Chapter XIX
            r"^\s*Chapter\s+([IVXLCDM]+)[\.\s]*(.+)$",  # Chapter I. Title
            # Numeric chapters with CHAPTER keyword
            r"^\s*CHAPTER\s+(\d+)\.?\s*$",  # CHAPTER 19. or CHAPTER 19
            r"^\s*CHAPTER\s+(\d+)[\.\s]*(.+)$",  # CHAPTER 1. Title or CHAPTER 1 Title
            r"^\s*Chapter\s+(\d+)\.?\s*$",  # Chapter 19. or Chapter 19
            r"^\s*Chapter\s+(\d+)[\.\s]*(.+)$",  # Chapter 1. Title
            # Standalone Roman numerals or numbers (for minimalist books)
            r"^\s*([IVXLCDM]+)\.?\s*$",  # Just "XIX." or "I."
            r"^\s*(\d+)\.?\s*$",  # Just "19." or "1."
            # Spelled out standalone numbers (e.g. "ONE", "TWENTY-ONE")
            rf"^\s*{self.SPELLED_NUMBER_RE}\.?\s*$",
            # With separators (colon, dash)
            r"^\s*CHAPTER\s+(\d+)[\s\-:]+(.+)$",  # CHAPTER 1: Title, CHAPTER 1 - Title
            r"^\s*CHAPTER\s+([IVXLCDM]+)[\s\-:]+(.+)$",  # CHAPTER I: Title
            r"^\s*Chapter\s+(\d+)[\s\-:]+(.+)$",  # Chapter 1: Title
            r"^\s*Chapter\s+([IVXLCDM]+)[\s\-:]+(.+)$",  # Chapter I: Title
            # Number/Roman with period and title
            r"^\s*(\d+)\.\s+(.+)$",  # "1. Chapter Title"
            r"^\s*([IVXLCDM]+)\.\s+(.+)$",  # "I. Chapter Title"
            # Word-based chapters
            r"^\s*CHAPTER\s+([A-Z][a-z]+)\s*(.*)$",  # CHAPTER One, CHAPTER Two
            r"^\s*Chapter\s+([A-Z][a-z]+)\s*(.*)$",  # Chapter One, Chapter Two
        ]

        # FLEXIBLE TITLE PATTERNS - matches various title formats
        self.TITLE_PATTERNS = [
            r"^([A-Z][A-Za-z\s]+(?:to|of|and|the|in|with|for|on|at|by)\s+[A-Z][A-Za-z\s]+)$",  # Complex titles
            r"^([A-Z][A-Za-z\s]{5,})$",  # Titles with at least 5 characters
            r"^([A-Z][a-zA-Z\s\-\:]+)$",  # Titles with dashes and colons
            r"^([A-Z\s]+)$",  # All caps titles
        ]

        # Keep your existing section and special patterns as they are flexible
        self.SECTION_PATTERNS = [
            r"^PART\s+([A-Z]+|[IVX]+|\d+)[\s\-:]*(.{10,})$",
            r"^Part\s+([A-Z]+|[IVX]+|\d+)[\s\-:]*(.{10,})$",
            r"(?i)^tablet\s+([ivx]+|\d+)[\s\-:]*(.{10,})$",
            r"(?i)^book\s+(\d+|[ivx]+)[\s\-:]*(.{10,})$",
            r"(?i)^section\s+(\d+|[ivx]+)[\s\-:]*(.{10,})$",
        ]

        # Add TOC detection patterns to skip
        self.TOC_PATTERNS = [
            r"(?i)^contents?$",
            r"(?i)^table\s+of\s+contents?$",
            r"(?i)^index$",
            r"^\s*\d+\s*$",  # Lines with just numbers (page numbers)
            r"^.{1,50}\s+\d+\s*$",  # Short text followed by numbers (typical TOC entry)
        ]

        # Special sections that should be treated as standalone
        self.SPECIAL_SECTIONS = [
            r"(?i)^preface[\s\-:]*(.*)$",
            r"(?i)^introduction[\s\-:]*(.*)$",
            r"(?i)^foreword[\s\-:]*(.*)$",
            r"(?i)^prologue[\s\-:]*(.*)$",
            r"(?i)^epilogue[\s\-:]*(.*)$",
            r"(?i)^conclusion[\s\-:]*(.*)$",
            r"(?i)^appendix[\s\-:]*(.*)$",
        ]

        # Special sections that should be treated as standalone or excluded
        self.SPECIAL_SECTIONS = [
            r"(?i)^preface[\s\-:]*(.*)$",
            r"(?i)^introduction[\s\-:]*(.*)$",
            r"(?i)^foreword[\s\-:]*(.*)$",
            r"(?i)^prologue[\s\-:]*(.*)$",
            r"(?i)^epilogue[\s\-:]*(.*)$",
            r"(?i)^conclusion[\s\-:]*(.*)$",
            r"(?i)^appendix[\s\-:]*(.*)$",
            r"(?i)^notes[\s\-:]*(.*)$",
            r"(?i)^suggested\s+reading[\s\-:]*(.*)$",
            r"(?i)^bibliography[\s\-:]*(.*)$",
            r"(?i)^index[\s\-:]*(.*)$",
            r"(?i)^references[\s\-:]*(.*)$",
            r"(?i)^glossary[\s\-:]*(.*)$",
        ]

    def detect_structure(self, content: str) -> Dict[str, Any]:
        """Enhanced structure detection that skips TOC sections"""
        lines = content.split("\n")

        # Try the improved chapter detection first for books with number + title format
        chapter_headers = self._find_chapter_number_and_title(lines)

        if len(chapter_headers) >= 8:  # Expect at least 8-9 chapters
            print(
                f"[STRUCTURE DETECTION] Using direct chapter detection: {len(chapter_headers)} chapters"
            )
            flat_chapters = []

            for header in chapter_headers:
                content_text = self._extract_chapter_content(content, header, lines)
                flat_chapters.append(
                    {
                        "title": header["title"],
                        "number": header["number"],
                        "content": content_text,
                    }
                )

            return {
                "has_sections": False,
                "sections": None,
                "chapters": flat_chapters,
                "structure_type": "flat",
            }

        # Fallback to comprehensive pattern matching
        print("[STRUCTURE DETECTION] Using comprehensive pattern matching")

        sections = []
        current_section = None
        flat_chapters = []
        in_toc_section = False

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Skip if we're in a TOC section
            if self._is_toc_section(line):
                in_toc_section = True
                continue

            # Check if we've moved past TOC (substantial content indicates real chapters)
            if (
                in_toc_section and len(line) > 100
            ):  # Substantial content indicates we're past TOC
                in_toc_section = False

            if in_toc_section:
                continue

            # Skip obvious TOC entries
            if self._is_toc_entry(line):
                continue

            # Check if line matches any section pattern
            section_match = self._match_section_patterns(line)
            if section_match:
                # Verify this isn't a TOC entry by checking following content
                if self._has_substantial_following_content(lines, line_num):
                    # Save previous section if exists
                    if current_section:
                        sections.append(current_section)

                    # Start new section
                    current_section = {
                        "title": line,
                        "number": section_match["number"],
                        "type": section_match["type"],
                        "chapters": [],
                        "content": self._extract_section_content(
                            content, line, lines, line_num
                        ),
                    }
                continue

            # Check for special sections (preface, introduction, etc.)
            special_match = self._match_special_sections(line)
            if special_match and self._has_substantial_following_content(
                lines, line_num
            ):
                # Save previous section if exists
                if current_section:
                    sections.append(current_section)

                # Create special section
                current_section = {
                    "title": line,
                    "number": special_match["number"],
                    "type": "special",
                    "chapters": [],
                    "content": self._extract_section_content(
                        content, line, lines, line_num
                    ),
                }
                continue

            # Check if line matches chapter pattern (only if we're in a section)
            if current_section:
                chapter_match = self._match_chapter_patterns(line)
                if chapter_match and self._has_substantial_following_content(
                    lines, line_num
                ):
                    # Build a proper title
                    chapter_number = chapter_match["number"]
                    chapter_subtitle = chapter_match.get("title", "").strip()

                    # Create a readable title
                    if chapter_subtitle:
                        chapter_title = f"Chapter {chapter_number}: {chapter_subtitle}"
                    else:
                        # No subtitle, look for title in next few lines
                        title_found = None
                        for i in range(line_num + 1, min(line_num + 5, len(lines))):
                            next_line = lines[i].strip()
                            if not next_line:
                                continue
                            if 10 < len(next_line) < 100:
                                if not self._match_chapter_patterns(next_line):
                                    title_found = next_line
                                    break

                        if title_found:
                            chapter_title = f"Chapter {chapter_number}: {title_found}"
                        else:
                            chapter_title = f"Chapter {chapter_number}"

                    # Create chapter_info for extraction
                    chapter_info = {
                        "title": chapter_title,
                        "title_line_num": line_num,
                        "line_num": line_num,
                        "number": chapter_number,
                        "raw_title": line,
                    }
                    chapter_content = self._extract_chapter_content(
                        content, chapter_info, lines
                    )

                    # Only add if content is substantial
                    if len(chapter_content.strip()) > 500:  # Minimum content length
                        chapter_data = {
                            "title": chapter_title,
                            "number": chapter_number,
                            "content": chapter_content,
                        }
                        current_section["chapters"].append(chapter_data)
                        print(
                            f"[HIERARCHICAL] Added chapter {chapter_number} to section '{current_section['title']}'"
                        )

        # Add last section
        if current_section:
            sections.append(current_section)

        # Remove duplicate chapters based on normalized numbers
        sections = self._remove_duplicate_chapters(sections)

        # If no sections found, try to extract flat chapters
        if not sections:
            flat_chapters = self._extract_flat_chapters(content)

        # Determine structure type
        has_sections = len(sections) > 0

        # Add deduplication logic
        seen_titles = set()
        unique_sections = []

        for section in sections:
            title_key = f"{section['title'].lower().strip()}"
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_sections.append(section)

        # Also add minimum content length validation
        filtered_sections = []
        for section in unique_sections:
            if (
                len(section.get("content", "").strip()) > 100
            ):  # Minimum content threshold
                filtered_sections.append(section)

        # Update the sections variable to use filtered_sections
        sections = filtered_sections

        return {
            "has_sections": has_sections,
            "sections": sections if has_sections else None,
            "chapters": flat_chapters if not has_sections else [],
            "structure_type": (
                self._determine_structure_type(sections) if has_sections else "flat"
            ),
        }

    def _is_toc_section(self, line: str) -> bool:
        """Check if we're entering a TOC section"""
        toc_indicators = [
            r"(?i)^contents?$",
            r"(?i)^table\s+of\s+contents?$",
            r"(?i)^contents\s+page$",
        ]
        return any(re.match(pattern, line) for pattern in toc_indicators)

    def _is_toc_entry(self, line: str) -> bool:
        """Check if a line is a TOC entry"""
        for pattern in self.TOC_PATTERNS:
            if re.match(pattern, line):
                return True
        return False

    def _has_substantial_following_content(
        self, lines: List[str], start_line: int, min_lines: int = 10
    ) -> bool:
        """Check if there's substantial content following this line"""
        content_lines = 0
        total_content = ""

        for i in range(
            start_line + 1, min(len(lines), start_line + 20)
        ):  # Check next 20 lines
            line = lines[i].strip()
            if line and not re.match(r"^\d+$", line):  # Skip page numbers
                content_lines += 1
                total_content += line + " "

        # Must have multiple lines and substantial text
        return content_lines >= min_lines and len(total_content.strip()) > 200

    def _normalize_chapter_number(self, number: str) -> str:
        """Normalize chapter numbers (convert Roman to Arabic)"""
        number = number.strip().upper()
        # Remove trailing dot if present
        if number.endswith("."):
            number = number[:-1]

        # If it's already Arabic, return as is
        if number.isdigit():
            return number

        # Convert Roman numerals to Arabic
        roman_to_int = {
            "I": 1,
            "II": 2,
            "III": 3,
            "IV": 4,
            "V": 5,
            "VI": 6,
            "VII": 7,
            "VIII": 8,
            "IX": 9,
            "X": 10,
            "XI": 11,
            "XII": 12,
            "XIII": 13,
            "XIV": 14,
            "XV": 15,
            "XVI": 16,
            "XVII": 17,
            "XVIII": 18,
            "XIX": 19,
            "XX": 20,
            "XXI": 21,
            "XXII": 22,
            "XXIII": 23,
            "XXIV": 24,
            "XXV": 25,
            "XXX": 30,
            "XL": 40,
            "L": 50,
        }
        return str(roman_to_int.get(number, number))

    def _remove_duplicate_chapters(self, sections: List[Dict]) -> List[Dict]:
        """Remove duplicate chapters based on normalized numbers"""
        for section in sections:
            if "chapters" in section:
                seen_numbers = set()
                unique_chapters = []

                for chapter in section["chapters"]:
                    normalized_number = self._normalize_chapter_number(
                        chapter.get("number", "")
                    )
                    if normalized_number not in seen_numbers:
                        seen_numbers.add(normalized_number)
                        unique_chapters.append(chapter)
                    else:
                        print(
                            f"[DUPLICATE REMOVAL] Skipping duplicate chapter {normalized_number}: {chapter['title']}"
                        )

                section["chapters"] = unique_chapters

        return sections

    def _extract_chapter_content(
        self,
        full_content: str,
        chapter_info_or_title,
        lines: List[str],
        line_num: int = None,
    ) -> str:
        """Extract content starting after the chapter title

        Args:
            full_content: The full text content
            chapter_info_or_title: Either a dict with 'title_line_num' or a string chapter title
            lines: List of lines in the content
            line_num: Optional line number when chapter_info_or_title is a string
        """
        content_lines = []

        # Handle both dict and individual argument formats for backward compatibility
        if isinstance(chapter_info_or_title, dict):
            chapter_title = chapter_info_or_title.get("title", "Unknown")
            start_line = chapter_info_or_title["title_line_num"] + 1
        else:
            # chapter_info_or_title is a string (chapter_title), line_num is provided
            if line_num is None:
                raise ValueError(
                    "line_num must be provided when chapter_info_or_title is a string"
                )
            chapter_title = chapter_info_or_title
            start_line = line_num + 1

        print(f"[CONTENT EXTRACTION] Extracting content for: {chapter_title}")
        print(f"[CONTENT EXTRACTION] Starting from line {start_line}")

        for i in range(start_line, len(lines)):
            line = lines[i].strip()

            # Skip empty lines at the beginning
            if not content_lines and not line:
                continue

            # Stop if we hit another chapter number - RELAXED CHECK
            if re.match(r"^(\d+)$", line) and i < len(lines) - 5:
                # Only break if the next line actually looks like a chapter title or continuation
                # Many books have page numbers in the middle of text flow on raw extraction
                is_real_chapter_break = False

                # Check previous line (if it ends with sentence terminator, break is more likely)
                # prev_line = lines[i-1].strip() if i > 0 else ""

                # Check next few lines for title pattern
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if not next_line:
                        continue

                    # If next line looks like a title (uppercase, shortish) or matches chapter pattern
                    if (
                        10 < len(next_line) < 100 and next_line[0].isupper()
                    ) or self._match_chapter_patterns(next_line):
                        is_real_chapter_break = True
                        break

                if is_real_chapter_break:
                    print(
                        f"[CONTENT EXTRACTION] Stopped at next chapter number break: {line}"
                    )
                    break
                else:
                    # Probably a page number, ignore it
                    continue
                # Check if next few lines contain a title pattern
                has_title_after = False
                for j in range(i + 1, min(i + 10, len(lines))):
                    next_line = lines[j].strip()
                    if (
                        next_line
                        and len(next_line) > 10
                        and next_line[0].isupper()
                        and len(next_line.split()) > 2
                    ):
                        has_title_after = True
                        break

                if has_title_after:
                    print(f"[CONTENT EXTRACTION] Stopped at next chapter: {line}")
                    break

            # Skip page numbers, headers, footers
            if re.match(r"^\d+$", line) or len(line) < 3:
                continue

            # Stop at bibliography sections
            if line.upper() in ["NOTES", "BIBLIOGRAPHY", "REFERENCES", "FOOTNOTES"]:
                print(f"[CONTENT EXTRACTION] Stopped at bibliography: {line}")
                break

            # Add content line
            content_lines.append(line)

            # Mark substantial content found
            if len(line) > 30 and not re.match(r"^\d+\.", line):
                print(f"[CONTENT EXTRACTION] Found substantial content: {line[:50]}...")

        content = "\n".join(content_lines).strip()
        print(f"[CONTENT EXTRACTION] Extracted {len(content)} characters")

        return content if len(content) > 100 else "Content not available"

    def _find_chapter_number_and_title(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Find chapters by looking for number + title pattern - MORE RESTRICTIVE"""
        chapter_headers = []

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Look for just a number on its own line
            number_match = re.match(r"^(\d+)$", line)
            if number_match and line_num < len(lines) - 5:  # Must have content after
                chapter_number = int(number_match.group(1))

                # FIX: Be more restrictive about chapter numbers
                if chapter_number > 100:  # Skip obviously wrong numbers
                    continue

                # Look for title in the next few lines
                chapter_title = None
                title_line_num = None

                for next_line_num in range(
                    line_num + 1, min(line_num + 10, len(lines))
                ):
                    next_line = lines[next_line_num].strip()

                    # Skip empty lines and very short lines
                    if not next_line or len(next_line) < 5:
                        continue

                    # Skip page numbers or single words
                    if re.match(r"^\d+$", next_line) or len(next_line.split()) < 2:
                        continue

                    # FIX: More restrictive title validation
                    if (
                        next_line[0].isupper()
                        and len(next_line) > 10
                        and len(next_line) < 100  # Not too long
                        and not re.match(r"^\d+\.", next_line)  # Not a footnote
                        and not re.search(
                            r"\d{4}", next_line
                        )  # No years (likely copyright)
                        and "copyright" not in next_line.lower()
                        and "isbn" not in next_line.lower()
                        and "published" not in next_line.lower()
                    ):

                        chapter_title = next_line
                        title_line_num = next_line_num
                        break

                # FIX: More restrictive content validation
                if (
                    chapter_title
                    and title_line_num
                    and self._has_substantial_following_content(
                        lines, title_line_num, min_lines=8
                    )
                    and chapter_number <= 50
                ):  # Reasonable chapter count limit

                    full_title = f"Chapter {chapter_number}: {chapter_title}"
                    chapter_headers.append(
                        {
                            "line_num": line_num,
                            "title_line_num": title_line_num,
                            "title": full_title,
                            "number": chapter_number,
                            "raw_title": chapter_title,
                        }
                    )
                    print(f"[CHAPTER DETECTION] Found: {full_title}")

        # FIX: Additional validation - check for reasonable sequence
        # Relaxed: If we found at least 3 chapters, even if sequence has gaps, it's better than nothing
        if len(chapter_headers) >= 3:
            numbers = [h["number"] for h in chapter_headers]
            # More lenient sequence check
            if min(numbers) <= 10:  # Allow starting a bit later
                print(
                    f"[CHAPTER DETECTION] Validated sequence: {min(numbers)} to {max(numbers)}"
                )
                return chapter_headers
            else:
                print(
                    f"[CHAPTER DETECTION] Suspicious sequence start: {min(numbers)}, keeping for now"
                )
                return chapter_headers

        return chapter_headers

    def _is_running_header_or_footer(self, text: str) -> bool:
        """Check if text is a running header or footer"""
        text_lower = text.lower()

        # Common running header/footer patterns
        running_patterns = [
            r"^page \d+",  # "Page 123"
            r"^\d+ - ",  # "123 - Book Title"
            r" - \d+$",  # "Book Title - 123"
            r"^chapter \d+ - ",  # "Chapter 1 - Title"
        ]

        # Check if it's too short (likely page number or header)
        if len(text.split()) <= 2:
            return True

        # Check patterns
        for pattern in running_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _find_all_chapter_headers(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Find all potential chapter headers in the content"""
        chapter_headers = []

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Look for chapter patterns
            for pattern in self.CHAPTER_PATTERNS:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Verify this has substantial following content
                    if self._has_substantial_following_content(
                        lines, line_num, min_lines=5
                    ):
                        chapter_headers.append(
                            {
                                "line_num": line_num,
                                "title": line,
                                "number": match.group(1),
                                "pattern": pattern,
                            }
                        )
                        break

        print(f"[CHAPTER DETECTION] Found {len(chapter_headers)} potential chapters")
        for header in chapter_headers:
            print(f"[CHAPTER DETECTION] Line {header['line_num']}: {header['title']}")

        return chapter_headers

    def _match_section_patterns(self, line: str) -> Optional[Dict]:
        """Match line against section patterns"""
        for pattern in self.SECTION_PATTERNS:
            match = re.match(pattern, line)
            if match:
                return {
                    "number": match.group(1),
                    "title": match.group(2).strip() if len(match.groups()) > 1 else "",
                    "type": self._get_section_type(pattern),
                }
        return None

    def _match_special_sections(self, line: str) -> Optional[Dict]:
        """Match line against special section patterns"""
        # Add tracking for already processed special sections
        if not hasattr(self, "_processed_specials"):
            self._processed_specials = set()

        for pattern in self.SPECIAL_SECTIONS:
            match = re.match(pattern, line)
            if match:
                # Create unique key for this special section
                section_key = f"{pattern}_{match.group(0)}"

                # Skip if we've already processed this special section
                if section_key in self._processed_specials:
                    return None  # Skip duplicates

                # Mark as processed
                self._processed_specials.add(section_key)

                return {
                    "number": "0",  # Special sections don't have numbers
                    "title": (
                        match.group(1).strip()
                        if len(match.groups()) > 0
                        else match.group(0).strip()
                    ),
                    "type": "special",
                }
        return None

    def _roman_to_int(self, roman: str) -> int:
        """Convert Roman numeral to integer"""
        roman_values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        total = 0
        prev_value = 0

        for char in reversed(roman.upper()):
            value = roman_values.get(char, 0)
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value

        return total

    def _normalize_chapter_number(self, number_str: str) -> str:
        """Normalize chapter number to a consistent format"""
        # Clean up the input
        number_str = number_str.strip().upper()
        if number_str.endswith("."):
            number_str = number_str[:-1]

        # Check if it's a Roman numeral
        if re.match(r"^[IVXLCDM]+$", number_str):
            # Convert to integer
            decimal = self._roman_to_int(number_str)
            return str(decimal)

        # Check if it's a spelled out number (e.g. ONE or TWENTY-ONE)
        if re.match(r"^[A-Z\- \t]+$", number_str) and not number_str.isdigit():
            # Handle compound numbers like TWENTY-ONE
            parts = re.split(r"[\s\-]+", number_str)
            total = 0
            valid_word = False

            current_val = 0
            for part in parts:
                if part in self.WORD_TO_NUMBER:
                    val = self.WORD_TO_NUMBER[part]
                    if val == 100:  # Handle HUNDRED multiplier if simple
                        current_val = (current_val or 1) * 100
                    else:
                        current_val += val
                    valid_word = True

            if valid_word and current_val > 0:
                print(f"[CHAPTER NORMALIZE] Converted '{number_str}' to {current_val}")
                return str(current_val)

        return number_str

    def _match_chapter_patterns(self, line: str) -> Optional[Dict]:
        """Match line against chapter patterns"""
        for pattern in self.CHAPTER_PATTERNS:
            match = re.match(pattern, line)
            if match:
                raw_number = match.group(1)
                normalized_number = self._normalize_chapter_number(raw_number)
                return {
                    "number": normalized_number,
                    "raw_number": raw_number,
                    "title": match.group(2).strip() if len(match.groups()) > 1 else "",
                }
        return None

    def _get_section_type(self, pattern: str) -> str:
        """Determine section type from pattern"""
        pattern_lower = pattern.lower()
        if "tablet" in pattern_lower:
            return "tablet"
        elif "part" in pattern_lower:
            return "part"
        elif "book" in pattern_lower:
            return "book"
        elif "section" in pattern_lower:
            return "section"
        elif "chapter" in pattern_lower:
            return "chapter"
        else:
            return "section"

    def _determine_structure_type(self, sections: List[Dict]) -> str:
        """Determine the overall structure type"""
        if not sections:
            return "flat"

        section_types = [section.get("type", "unknown") for section in sections]
        most_common_type = max(set(section_types), key=section_types.count)
        return most_common_type

    def _extract_section_content(
        self, full_content: str, section_title: str, lines: List[str], start_line: int
    ) -> str:
        """Extract content for a specific section"""
        content_lines = []

        # Start from the line after the section title
        for i in range(start_line + 1, len(lines)):
            line = lines[i].strip()

            # Stop if we hit another section
            if self._match_section_patterns(line) or self._match_special_sections(line):
                break

            content_lines.append(line)

        return "\n".join(content_lines).strip()

    def _extract_flat_chapters(self, content: str) -> List[Dict]:
        """Extract chapters when no hierarchical structure is detected"""
        lines = content.split("\n")
        chapters = []

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            chapter_match = self._match_chapter_patterns(line)
            if chapter_match:
                # Build a proper title
                chapter_number = chapter_match["number"]
                chapter_subtitle = chapter_match.get("title", "").strip()

                # Create a readable title
                if chapter_subtitle:
                    # Has a subtitle: "Chapter 19: The Adventure"
                    chapter_title = f"Chapter {chapter_number}: {chapter_subtitle}"
                else:
                    # No subtitle, look for title in next few lines
                    title_found = None
                    for i in range(line_num + 1, min(line_num + 5, len(lines))):
                        next_line = lines[i].strip()
                        # Skip empty lines
                        if not next_line:
                            continue
                        # Check if this looks like a title (short, not all caps unless reasonable length)
                        if 10 < len(next_line) < 100:
                            # Not another chapter marker
                            if not self._match_chapter_patterns(next_line):
                                title_found = next_line
                                break

                    if title_found:
                        chapter_title = f"Chapter {chapter_number}: {title_found}"
                    else:
                        chapter_title = f"Chapter {chapter_number}"

                # FIX: Create chapter_info dict for the new method
                chapter_info = {
                    "title": chapter_title,
                    "title_line_num": line_num,
                    "line_num": line_num,
                    "number": chapter_number,
                    "raw_title": line,
                }
                extracted_content = self._extract_chapter_content(
                    content, chapter_info, lines
                )

                # Add content validation before adding chapters
                if (
                    len(extracted_content.strip()) > 200
                ):  # Only add chapters with substantial content
                    chapter_data = {
                        "title": chapter_title,
                        "number": chapter_number,
                        "content": extracted_content,
                    }
                    chapters.append(chapter_data)
                    print(
                        f"[FLAT CHAPTERS] Added chapter {chapter_number} ({len(extracted_content)} chars): {chapter_title}"
                    )
                else:
                    print(
                        f"[FLAT CHAPTERS] Skipped short content ({len(extracted_content)} chars) for: {chapter_title}"
                    )

        return chapters

    def _analyze_content_for_structure(
        self, sections: List[Dict], structure_type: str
    ) -> int:
        """Analyze section content with null safety"""
        score = 0
        content_indicators = {
            "tablet": [
                "gilgamesh",
                "enkidu",
                "uruk",
                "flood",
                "immortality",
                "mesopotamia",
            ],
            "book": ["chapter", "prologue", "epilogue", "narrative", "story"],
            "part": ["introduction", "conclusion", "overview", "summary"],
            "act": ["dialogue", "stage", "enter", "exit", "scene"],
            "movement": ["tempo", "allegro", "adagio", "musical", "notes"],
            "canto": ["verse", "stanza", "rhyme", "meter", "epic"],
        }

        if structure_type not in content_indicators:
            return 0

        indicators = content_indicators[structure_type]

        for section in sections:
            if not isinstance(section, dict):
                continue

            # FIX: Add null safety for content and title
            content_str = ""
            section_content = section.get("content")
            section_title = section.get("title")

            if section_content and isinstance(section_content, str):
                content_str += section_content + " "
            if section_title and isinstance(section_title, str):
                content_str += section_title + " "

            if content_str:
                content_lower = content_str.lower()
                for indicator in indicators:
                    if indicator in content_lower:
                        score += 1

        return min(score, 5)  # Cap at 5 points

    def _find_page_by_title_scan(
        self, doc, chapter_title: str, start_page: int, end_page: int
    ) -> Optional[int]:
        """Fallback: Scan pages for the chapter title if page number finding fails - with OCR"""
        print(
            f"[PAGE FINDER] Scanning pages {start_page+1}-{end_page+1} for title: {chapter_title}"
        )

        try:
            # Clean title for matching
            clean_title = chapter_title
            if ":" in chapter_title:
                clean_title = chapter_title.split(":", 1)[1].strip()

            clean_title_upper = clean_title.upper()

            for i in range(start_page, min(len(doc), end_page)):
                try:
                    page = doc[i]
                    text = page.get_text()

                    # OCR fallback for scanned PDFs
                    if not text.strip():
                        try:
                            tp = page.get_textpage_ocr(
                                flags=0, language="eng", dpi=150, full=True
                            )
                            text = page.get_text(textpage=tp)
                        except Exception:
                            pass

                    # Check for title in the first 1000 chars (usually top of page)
                    page_head = text[:1000].upper()

                    # Loose matching - check if title exists in header area
                    if clean_title_upper in page_head:
                        print(
                            f"[PAGE FINDER] Found title '{clean_title}' on page {i+1}"
                        )
                        return i
                except Exception:
                    continue

        except Exception as e:
            print(f"[PAGE FINDER] Error scanning for title: {e}")

        return None

    async def _extract_content_for_chapters_by_pages(
        self, validated_chapters: List[Dict], doc
    ) -> List[Dict[str, Any]]:
        """Extract chapter content using actual page number detection"""
        print(f"[PAGE EXTRACTION] Extracting content using page numbers from TOC...")

        # Group chapters by section
        sections_map = {}
        for chapter in validated_chapters:
            section_key = chapter.get("section_title", "Main")
            if section_key not in sections_map:
                sections_map[section_key] = []
            sections_map[section_key].append(chapter)

        print(f"[PAGE EXTRACTION] Found {len(sections_map)} sections")

        final_chapters = []

        for section_name, chapters in sections_map.items():
            print(
                f"[PAGE EXTRACTION] Processing section: {section_name} ({len(chapters)} chapters)"
            )

            # Sort chapters by page number within section
            chapters.sort(key=lambda x: x.get("page_hint", 0))

            for i, chapter in enumerate(chapters):
                chapter_title = chapter["title"]
                toc_page_num = chapter.get("page_hint", 1)

                # Find the actual page where this page number appears
                actual_start_page = self._find_actual_page_by_number(doc, toc_page_num)

                if actual_start_page is None:
                    print(
                        f"[PAGE EXTRACTION] Could not find actual page {toc_page_num} for {chapter_title}"
                    )
                    # Fallback: Scan for title
                    scan_start = (
                        0
                        if i == 0
                        else (
                            final_chapters[-1]["actual_end_page"]
                            if final_chapters
                            else 0
                        )
                    )
                    scan_end = min(len(doc), scan_start + 50)

                    found_page = self._find_page_by_title_scan(
                        doc, chapter_title, scan_start, scan_end
                    )
                    if found_page is not None:
                        print(
                            f"[PAGE EXTRACTION] Recovered start page using title scan: {found_page + 1}"
                        )
                        actual_start_page = found_page
                    else:
                        print(
                            f"[PAGE EXTRACTION] Title scan failed. Defaulting to TOC page {toc_page_num}"
                        )
                        actual_start_page = toc_page_num  # Fallback to TOC page number
                else:
                    print(
                        f"[PAGE EXTRACTION] Found page number {toc_page_num} on actual page {actual_start_page + 1}"
                    )

                # Determine end page
                if i < len(chapters) - 1:
                    next_chapter = chapters[i + 1]
                    next_toc_page = next_chapter.get("page_hint", toc_page_num + 10)
                    actual_end_page = self._find_actual_page_by_number(
                        doc, next_toc_page
                    )

                    if actual_end_page is not None:
                        end_page = actual_end_page - 1
                    else:
                        end_page = actual_start_page + min(
                            20, next_toc_page - toc_page_num - 1
                        )
                else:
                    # Last chapter in section - check if there's another section
                    next_section_start = self._find_next_section_start_page(
                        section_name, sections_map, actual_start_page
                    )
                    if next_section_start:
                        end_page = next_section_start - 1
                    else:
                        end_page = min(len(doc) - 1, actual_start_page + 30)

                # Ensure valid page range
                if actual_start_page >= end_page:
                    print(
                        f"[PAGE EXTRACTION] Invalid page range for {chapter_title}: {actual_start_page} to {end_page}"
                    )
                    end_page = min(len(doc) - 1, actual_start_page + 10)

                print(
                    f"[PAGE EXTRACTION] {chapter_title}: pages {actual_start_page + 1} to {end_page + 1}"
                )

                # Extract content from the actual page range
                content = self._extract_pages_content(doc, actual_start_page, end_page)

                # Clean the content
                cleaned_content = self._clean_extracted_content(content, chapter_title)

                if len(cleaned_content) > 100:
                    final_chapters.append(
                        {
                            "title": chapter_title,
                            "content": cleaned_content,
                            "summary": f"Content from {chapter_title}",
                            "number": chapter.get("number", i + 1),
                            "section_title": chapter.get("section_title"),
                            "section_type": chapter.get("section_type"),
                            "section_number": chapter.get("section_number"),
                            "extraction_method": "page_based",
                            "actual_start_page": actual_start_page + 1,
                            "actual_end_page": end_page + 1,
                        }
                    )
                    print(
                        f"[PAGE EXTRACTION] ✅ Extracted {len(cleaned_content)} chars from pages {actual_start_page + 1}-{end_page + 1}"
                    )
                else:
                    print(f"[PAGE EXTRACTION] ❌ Content too short for {chapter_title}")

        return final_chapters

    # def _find_actual_page_by_number(self, doc, target_page_num: int) -> Optional[int]:
    #     """Find the actual PDF page where a specific page number is printed"""
    #     print(f"[PAGE FINDER] Looking for printed page number {target_page_num}")

    #     # Common page number patterns
    #     page_patterns = [
    #         rf'\b{target_page_num}\b',  # Just the number
    #         rf'^{target_page_num}$',    # Number alone on line
    #         rf'^\s*{target_page_num}\s*$',  # Number with whitespace
    #     ]

    #     # Search in a reasonable range around the expected position
    #     search_start = max(0, target_page_num - 10)
    #     search_end = min(len(doc), target_page_num + 20)

    #     for page_idx in range(search_start, search_end):
    #         page = doc[page_idx]
    #         text = page.get_text()

    #         # Look for the page number in various positions
    #         lines = text.split('\n')

    #         # Check first few lines (headers)
    #         for line_idx in range(min(5, len(lines))):
    #             line = lines[line_idx].strip()
    #             for pattern in page_patterns:
    #                 if re.search(pattern, line):
    #                     print(f"[PAGE FINDER] Found page {target_page_num} on PDF page {page_idx + 1} (header)")
    #                     return page_idx

    #         # Check last few lines (footers)
    #         for line_idx in range(max(0, len(lines) - 5), len(lines)):
    #             line = lines[line_idx].strip()
    #             for pattern in page_patterns:
    #                 if re.search(pattern, line):
    #                     print(f"[PAGE FINDER] Found page {target_page_num} on PDF page {page_idx + 1} (footer)")
    #                     return page_idx

    #     print(f"[PAGE FINDER] Could not find printed page number {target_page_num}")
    #     return None

    def _find_actual_page_by_number(self, doc, target_page_num: int) -> Optional[int]:
        """Find the actual PDF page where a specific page number is printed - IMPROVED with numbering system detection"""
        print(f"[PAGE FINDER] Looking for printed page number {target_page_num}")

        # First, analyze the TOC to determine the numbering system used
        numbering_system = self._detect_numbering_system(doc, target_page_num)
        print(f"[PAGE FINDER] Detected numbering system: {numbering_system}")

        # Convert target page to expected formats
        if numbering_system == "roman":
            target_roman = self._arabic_to_roman(target_page_num)
            search_patterns = [
                rf"\b{target_roman}\b",
                rf"^\s*{target_roman}\s*$",
                rf"^\s*{target_page_num}\s*$",  # Fallback to Arabic
            ]
        elif numbering_system == "arabic":
            search_patterns = [
                rf"\b{target_page_num}\b",
                rf"^\s*{target_page_num}\s*$",
            ]
        else:  # mixed or unknown
            target_roman = (
                self._arabic_to_roman(target_page_num)
                if target_page_num <= 50
                else None
            )
            search_patterns = [
                rf"\b{target_page_num}\b",
                rf"^\s*{target_page_num}\s*$",
            ]
            if target_roman:
                search_patterns.extend(
                    [
                        rf"\b{target_roman}\b",
                        rf"^\s*{target_roman}\s*$",
                    ]
                )

        print(f"[PAGE FINDER] Search patterns: {search_patterns}")

        # Calculate search range - be more intelligent about where to look
        if target_page_num <= 20:
            # Early pages might use Roman numerals, search from beginning
            search_start = 0
            search_end = min(len(doc), 50)
        else:
            # Later pages likely use Arabic, search around expected position
            search_start = max(0, target_page_num - 10)
            search_end = min(len(doc), target_page_num + 30)

        print(f"[PAGE FINDER] Searching PDF pages {search_start + 1} to {search_end}")

        for page_idx in range(search_start, search_end):
            page = doc[page_idx]
            text = page.get_text()

            # OCR fallback for scanned PDFs
            if not text.strip():
                try:
                    tp = page.get_textpage_ocr(
                        flags=0, language="eng", dpi=150, full=True
                    )
                    text = page.get_text(textpage=tp)
                except Exception:
                    pass

            # Get lines for better analysis
            lines = text.split("\n")

            # Check headers (first 5 lines)
            for line_idx in range(min(5, len(lines))):
                line = lines[line_idx].strip()
                if self._matches_page_number(line, search_patterns, page_idx):
                    # Additional validation - make sure this isn't a figure/list reference
                    if not self._is_false_page_match(text, line, target_page_num):
                        print(
                            f"[PAGE FINDER] Found page {target_page_num} on PDF page {page_idx + 1} (header)"
                        )
                        return page_idx

            # Check footers (last 5 lines)
            for line_idx in range(max(0, len(lines) - 5), len(lines)):
                line = lines[line_idx].strip()
                if self._matches_page_number(line, search_patterns, page_idx):
                    # Additional validation
                    if not self._is_false_page_match(text, line, target_page_num):
                        print(
                            f"[PAGE FINDER] Found page {target_page_num} on PDF page {page_idx + 1} (footer)"
                        )
                        return page_idx

        print(f"[PAGE FINDER] Could not find printed page number {target_page_num}")
        return None

    def _detect_numbering_system(self, doc, target_page_num: int) -> str:
        """Detect whether the book uses Roman numerals, Arabic numbers, or mixed - with OCR"""

        # Look at the first few pages to see what numbering system is used
        roman_indicators = 0
        arabic_indicators = 0

        for page_idx in range(min(20, len(doc))):
            page = doc[page_idx]
            text = page.get_text()

            # OCR fallback for scanned PDFs
            if not text.strip():
                try:
                    tp = page.get_textpage_ocr(
                        flags=0, language="eng", dpi=150, full=True
                    )
                    text = page.get_text(textpage=tp)
                except Exception:
                    pass

            lines = text.split("\n")

            # Check headers and footers for numbering patterns
            check_lines = lines[:3] + lines[-3:]  # First 3 and last 3 lines

            for line in check_lines:
                line = line.strip()
                if len(line) < 10:  # Short lines are more likely to be page numbers
                    # Check for Roman numerals
                    if re.match(r"^[ivxlcdm]+$", line.lower()):
                        roman_indicators += 1
                    # Check for Arabic numbers (but not years or other large numbers)
                    elif re.match(r"^\d{1,3}$", line) and int(line) < 200:
                        arabic_indicators += 1

        print(
            f"[NUMBERING DETECTION] Roman indicators: {roman_indicators}, Arabic indicators: {arabic_indicators}"
        )

        if roman_indicators > arabic_indicators * 2:
            return "roman"
        elif arabic_indicators > roman_indicators * 2:
            return "arabic"
        else:
            return "mixed"

    def _arabic_to_roman(self, num: int) -> str:
        """Convert Arabic number to Roman numeral"""
        if num > 50:  # Don't convert large numbers
            return str(num)

        roman_numerals = [
            (50, "L"),
            (40, "XL"),
            (10, "X"),
            (9, "IX"),
            (5, "V"),
            (4, "IV"),
            (1, "I"),
        ]

        result = ""
        for value, numeral in roman_numerals:
            count = num // value
            result += numeral * count
            num -= value * count

        return result

    def _matches_page_number(
        self, line: str, patterns: List[str], page_idx: int
    ) -> bool:
        """Check if a line matches any of the page number patterns"""
        for pattern in patterns:
            if re.search(pattern, line):
                return True
        return False

    def _is_false_page_match(
        self, page_text: str, matched_line: str, target_page_num: int
    ) -> bool:
        """Check if this is a false positive (like figure numbers, list items, etc.)"""

        # Check if we're in a "List of Figures" or similar section
        page_text_lower = page_text.lower()
        if any(
            indicator in page_text_lower
            for indicator in [
                "list of illustrations",
                "list of figures",
                "table of contents",
                "contents",
                "bibliography",
                "index",
            ]
        ):
            print(
                f"[PAGE FINDER] Rejecting match in list/index section: {matched_line}"
            )
            return True

        # Check if the matched line contains other text that suggests it's not a page number
        if len(matched_line.split()) > 2:  # Page numbers are usually standalone
            print(f"[PAGE FINDER] Rejecting match with extra text: {matched_line}")
            return True

        # Check for figure/illustration patterns around the match
        lines_around = page_text.split("\n")
        for i, line in enumerate(lines_around):
            if matched_line in line:
                # Check surrounding lines for figure/illustration keywords
                start_idx = max(0, i - 2)
                end_idx = min(len(lines_around), i + 3)
                context = " ".join(lines_around[start_idx:end_idx]).lower()

                if any(
                    keyword in context
                    for keyword in [
                        "figure",
                        "illustration",
                        "plate",
                        "diagram",
                        "chart",
                        "table",
                        "by gustav",
                        "by singleton",
                    ]
                ):
                    print(
                        f"[PAGE FINDER] Rejecting match near figure/illustration: {context[:100]}"
                    )
                    return True
                break

        return False

    def _extract_pages_content(self, doc, start_page: int, end_page: int) -> str:
        """Extract text content from a range of pages - with OCR fallback for scanned PDFs"""
        content_parts = []

        for page_num in range(start_page, end_page + 1):
            if page_num < len(doc):
                page = doc[page_num]
                text = page.get_text()

                # OCR fallback for scanned/image-based PDFs
                if not text.strip():
                    try:
                        tp = page.get_textpage_ocr(
                            flags=0, language="eng", dpi=150, full=True
                        )
                        text = page.get_text(textpage=tp)
                        if text.strip():
                            print(
                                f"[PAGE EXTRACTION] OCR extracted text from page {page_num + 1}"
                            )
                    except Exception as e:
                        print(
                            f"[PAGE EXTRACTION] OCR failed for page {page_num + 1}: {e}"
                        )

                if text.strip():
                    content_parts.append(text)

        return "\n\n".join(content_parts)

    def _find_next_section_start_page(
        self, current_section: str, sections_map: dict, current_page: int
    ) -> Optional[int]:
        """Find the starting page of the next section"""
        section_names = list(sections_map.keys())
        try:
            current_idx = section_names.index(current_section)
            if current_idx + 1 < len(section_names):
                next_section = section_names[current_idx + 1]
                next_section_chapters = sections_map[next_section]
                if next_section_chapters:
                    return min(
                        ch.get("page_hint", 999999)
                        for ch in next_section_chapters
                        if ch.get("page_hint")
                    )
        except (ValueError, IndexError):
            pass
        return None

    def _clean_extracted_content(self, content: str, chapter_title: str) -> str:
        """Clean content extracted from page ranges"""
        if not content:
            return ""

        lines = content.split("\n")
        cleaned_lines = []

        # Remove the chapter title from the beginning if it appears
        clean_title = (
            chapter_title.split(":", 1)[-1].strip()
            if ":" in chapter_title
            else chapter_title
        )

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Skip empty lines at the beginning
            if not cleaned_lines and not line_stripped:
                continue

            # Skip the chapter title line if it appears at the start
            if not cleaned_lines and clean_title.lower() in line_stripped.lower():
                continue

            # Skip page numbers and headers/footers
            if (
                re.match(r"^\d+$", line_stripped)  # Just page numbers
                or re.match(r"^[ivxlcdm]+$", line_stripped.lower())  # Roman numerals
                or len(line_stripped) < 3  # Very short lines
                or self._is_running_header_or_footer(line_stripped)
            ):
                continue

            cleaned_lines.append(line)

        # Join and clean up excessive whitespace
        result = "\n".join(cleaned_lines)
        result = re.sub(r"\n{3,}", "\n\n", result)  # Max 2 consecutive newlines

        return result.strip()

    def convert_roman_to_int(self, roman: str) -> int:
        """Convert Roman numerals to integers"""
        roman_values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

        roman = roman.upper()
        total = 0
        prev_value = 0

        for char in reversed(roman):
            value = roman_values.get(char, 0)
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value

        return total

    def detect_structure_type(self, sections: List[Dict]) -> str:
        """Enhanced structure type detection with null safety"""
        if not sections:
            return "flat"

        # FIX: Add null safety for section processing
        section_types = []
        section_count = len(sections)

        for s in sections:
            if not isinstance(s, dict):
                continue
            section_type = s.get("section_type")
            if section_type and isinstance(section_type, str):
                section_types.append(section_type.lower())

        # Calculate confidence scores for each structure type
        structure_scores = {}

        for structure_name, config in self.STRUCTURE_PATTERNS.items():
            score = 0

            # 1. Direct type match
            direct_matches = sum(1 for t in section_types if t == structure_name)
            score += direct_matches * 10

            # 2. Pattern-based scoring with null safety
            for section in sections:
                if not isinstance(section, dict):
                    continue
                section_title = section.get("title")
                if section_title and isinstance(section_title, str):
                    section_title_lower = section_title.lower()
                    for indicator in config["indicators"]:
                        if indicator in section_title_lower:
                            score += 3

            # 3. Count-based scoring
            min_count, max_count = config["typical_count"]
            if min_count <= section_count <= max_count:
                score += 5
            elif section_count < min_count:
                score += 2

            # 4. Content analysis scoring with null safety
            try:
                content_score = self._analyze_content_for_structure(
                    sections, structure_name
                )
                score += content_score
            except Exception as e:
                print(f"[STRUCTURE DETECTION] Content analysis error: {e}")
                score += 0

            structure_scores[structure_name] = score

        # Find the best match
        if structure_scores:
            best_structure = max(structure_scores.items(), key=lambda x: x[1])

            # Only return specific structure if confidence is high enough
            if best_structure[1] >= 8:
                print(
                    f"[STRUCTURE DETECTION] Detected structure: {best_structure[0]} (score: {best_structure[1]})"
                )
                return best_structure[0]

        # Check for generic hierarchical vs flat
        if section_types:
            print(f"[STRUCTURE DETECTION] Generic hierarchical structure detected")
            return "hierarchical"
        else:
            return "flat"

    def get_structure_metadata(self, structure_type: str) -> Dict[str, Any]:
        """Get metadata for a specific structure type"""
        metadata = {
            "flat": {
                "display_name": "Simple Chapters",
                "icon": "📖",
                "description": "Traditional chapter-based structure",
                "section_label": None,
                "chapter_label": "Chapter",
            },
            "hierarchical": {
                "display_name": "Multi-Level Structure",
                "icon": "🏗️",
                "description": "Book with sections and subsections",
                "section_label": "Section",
                "chapter_label": "Chapter",
            },
            "tablet": {
                "display_name": "Tablet Structure",
                "icon": "🏺",
                "description": "Ancient text organized in tablets",
                "section_label": "Tablet",
                "chapter_label": "Section",
            },
            "book": {
                "display_name": "Book Structure",
                "icon": "📚",
                "description": "Multiple books within a larger work",
                "section_label": "Book",
                "chapter_label": "Chapter",
            },
            "part": {
                "display_name": "Part Structure",
                "icon": "📋",
                "description": "Organized into distinct parts",
                "section_label": "Part",
                "chapter_label": "Chapter",
            },
            "act": {
                "display_name": "Theatrical Structure",
                "icon": "🎭",
                "description": "Drama organized in acts and scenes",
                "section_label": "Act",
                "chapter_label": "Scene",
            },
            "movement": {
                "display_name": "Musical Structure",
                "icon": "🎵",
                "description": "Musical work with movements",
                "section_label": "Movement",
                "chapter_label": "Section",
            },
            "canto": {
                "display_name": "Epic Structure",
                "icon": "📜",
                "description": "Epic poem organized in cantos",
                "section_label": "Canto",
                "chapter_label": "Verse",
            },
        }

        return metadata.get(structure_type, metadata["hierarchical"])


class FileService:
    """File processing service for book uploads"""

    MAX_CHAPTERS = 50
    ROMAN_RE = r"[IVXLCDM]+"
    ROMAN_RE_LOWER = r"[ivxlcdm]+"

    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.ai_service = AIService()
        self.structure_detector = BookStructureDetector()
        os.makedirs(self.upload_dir, exist_ok=True)

    def _extract_chapter_content(
        self, full_content: str, chapter_title: str, lines: List[str], start_line: int
    ) -> str:
        """Wrapper method to call BookStructureDetector's _extract_chapter_content"""
        # Create a chapter_info dict for the new method
        chapter_info = {
            "title": chapter_title,
            "title_line_num": start_line,  # Use start_line as title line
            "line_num": start_line - 1 if start_line > 0 else 0,
            "number": "1",  # Default number
            "raw_title": chapter_title,
        }

        # Call the new method in BookStructureDetector
        return self.structure_detector._extract_chapter_content(
            full_content, chapter_info, lines
        )

        # return self.structure_detector._extract_chapter_content(full_content, chapter_title, lines, start_line)

    async def process_book_file(
        self, file_path: str, filename: str, user_id: str = None
    ) -> Dict[str, Any]:
        """Process different file types and extract content"""
        try:
            if filename.lower().endswith(".pdf"):
                return await self.process_pdf(file_path, user_id)
            elif filename.lower().endswith(".docx"):
                return await self.process_docx(file_path, user_id)
            elif filename.lower().endswith(".txt"):
                return await self.process_txt(file_path, user_id)
            elif filename.lower().endswith(".epub"):
                return await self.process_epub(file_path, user_id)
            else:
                raise ValueError(f"Unsupported file type: {filename}")
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            raise

    async def process_pdf(self, file_path: str, user_id: str = None) -> Dict[str, Any]:
        """Extract text, metadata, and cover image from PDF"""
        try:
            doc = fitz.open(file_path)
            text = ""
            author = None
            cover_image_url = None

            # Extract text from all pages
            for page in doc:
                text += page.get_text()

            # Try to extract author from metadata
            metadata = doc.metadata
            if metadata and metadata.get("author"):
                author = metadata["author"]

            # Extract cover image from first page
            if user_id and len(doc) > 0:
                try:
                    first_page = doc[0]
                    # Get images from the first page
                    images = first_page.get_images(full=True)

                    if images:
                        # Extract the first image as cover
                        xref = images[0][0]
                        pix = fitz.Pixmap(doc, xref)

                        # Save to in-memory buffer
                        import io

                        img_buffer = io.BytesIO()
                    try:
                        img_buffer.write(pix.tobytes("png"))
                        img_buffer.seek(0)

                        # Upload to Supabase Storage under user folder
                        storage_path = (
                            f"users/{user_id}/covers/cover_{int(time.time())}.png"
                        )

                        # Get the public URL
                        # Get the public URL
                        from app.core.services.storage import storage_service

                        cover_image_url = await storage_service.upload(
                            img_buffer.getvalue(), storage_path, "image/png"
                        )
                        print(
                            f"[COVER EXTRACTION] Cover image uploaded: {cover_image_url}"
                        )

                        # Clean up
                        pix = None
                        img_buffer.close()

                    except Exception as e:
                        print(f"[COVER EXTRACTION] Error with pixmap conversion: {e}")
                        # Fallback to different method

                        try:
                            page = doc[0]  # Get first page
                            pix_fallback = page.get_pixmap()
                            img_data = pix_fallback.pil_tobytes(format="PNG")

                            img_buffer = io.BytesIO()
                            img_buffer.write(img_data)
                            img_buffer.seek(0)

                            # Upload fallback image
                            storage_path = (
                                f"users/{user_id}/covers/cover_{int(time.time())}.png"
                            )
                            from app.core.services.storage import storage_service

                            cover_image_url = await storage_service.upload(
                                img_buffer.getvalue(), storage_path, "image/png"
                            )
                            print(
                                f"[COVER EXTRACTION] Fallback cover image uploaded: {cover_image_url}"
                            )

                        except Exception as fallback_error:
                            print(
                                f"[COVER EXTRACTION] Fallback method also failed: {fallback_error}"
                            )
                            cover_image_url = None

                    else:
                        print("[COVER EXTRACTION] No images found on first page")
                except Exception as e:
                    print(f"[COVER EXTRACTION] Error extracting cover: {e}")

            doc.close()

            return {"text": text, "author": author, "cover_image_url": cover_image_url}
        except Exception as e:
            print(f"Error processing PDF: {e}")
            raise

    async def process_docx(self, file_path: str, user_id: str = None) -> Dict[str, Any]:
        """Extract text and cover image from DOCX"""
        try:
            doc = docx.Document(file_path)
            text = ""
            cover_image_url = None

            # Extract text from paragraphs
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"

            # Extract cover image from DOCX (first image found)
            if user_id:
                try:
                    # DOCX files store images in the document's media folder
                    # This is a simplified approach - in practice, you might need more complex extraction
                    import zipfile
                    import tempfile
                    import os

                    # Extract images from DOCX (DOCX is a ZIP file)
                    with zipfile.ZipFile(file_path, "r") as zip_ref:
                        image_files = [
                            f
                            for f in zip_ref.namelist()
                            if f.startswith("word/media/")
                            and f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
                        ]

                        if image_files:
                            # Get the first image
                            first_image = image_files[0]
                            with zip_ref.open(first_image) as image_file:
                                img_data = image_file.read()

                                # Upload to Supabase Storage under user folder
                                # Upload to Local Storage under user folder
                                storage_path = f"users/{user_id}/covers/cover_{int(time.time())}.png"
                                from app.core.services.storage import storage_service

                                cover_image_url = await storage_service.upload(
                                    img_data, storage_path, "image/png"
                                )
                                print(
                                    f"[COVER EXTRACTION] Cover image uploaded: {cover_image_url}"
                                )
                except Exception as e:
                    print(f"[COVER EXTRACTION] Error extracting cover from DOCX: {e}")

            return {"text": text, "author": None, "cover_image_url": cover_image_url}
        except Exception as e:
            print(f"Error processing DOCX: {e}")
            raise

    async def process_txt(self, file_path: str, user_id: str = None) -> Dict[str, Any]:
        """Extract text from TXT (no cover image)"""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                text = file.read()

            return {"text": text, "author": None, "cover_image_url": None}
        except Exception as e:
            print(f"Error processing TXT: {e}")
            raise

    def extract_epub_chapters(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract chapters from EPUB file using its built-in structure"""
        try:
            book = epub.read_epub(file_path)
            chapters = []

            # Get the spine (reading order)
            spine = book.spine
            print(f"[EPUB] Spine contains {len(spine)} items")

            chapter_number = 0
            skipped_count = 0

            for idx, (item_id, _) in enumerate(spine):
                item = book.get_item_with_id(item_id)

                if not item:
                    print(f"[EPUB] Item {idx}: Could not get item with id '{item_id}'")
                    continue

                item_type = item.get_type()
                print(f"[EPUB] Item {idx} (id: {item_id}): type = {item_type}")

                if item_type == ebooklib.ITEM_DOCUMENT:
                    # Parse HTML content
                    soup = BeautifulSoup(item.get_content(), "html.parser")

                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()

                    # Get text content
                    text = soup.get_text()

                    # Clean the text
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (
                        phrase.strip() for line in lines for phrase in line.split("  ")
                    )
                    clean_text = "\n".join(chunk for chunk in chunks if chunk)

                    content_length = len(clean_text.strip())
                    print(f"[EPUB] Item {idx}: content length = {content_length}")

                    # Skip if content is too short (likely not a real chapter)
                    # Lowered threshold from 200 to 100 to catch more chapters
                    if content_length < 100:
                        skipped_count += 1
                        print(
                            f"[EPUB] Skipping item {idx}: content too short ({content_length} chars)"
                        )
                        continue

                    # Try to find chapter title from first heading or first line
                    title = None
                    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
                        title_text = heading.get_text().strip()
                        if title_text:
                            title = title_text
                            print(f"[EPUB] Found heading title: {title}")
                            break

                    # If no heading found, use first line as title or try to detect chapter pattern
                    if not title:
                        first_lines = clean_text.split("\n")[:5]
                        for line in first_lines:
                            line_stripped = line.strip()
                            # Check if it matches chapter pattern
                            chapter_match = self._match_chapter_patterns(line_stripped)
                            if chapter_match:
                                # Use the chapter pattern as title
                                if chapter_match.get("title"):
                                    title = f"Chapter {chapter_match['number']}: {chapter_match['title']}"
                                else:
                                    title = f"Chapter {chapter_match['number']}"
                                print(f"[EPUB] Found chapter pattern: {title}")
                                break
                            # Otherwise check if it looks like a title
                            elif 5 < len(
                                line_stripped
                            ) < 100 and not line_stripped.endswith("."):
                                title = line_stripped
                                print(f"[EPUB] Using first line as title: {title}")
                                break

                    # Generate title if still none
                    if not title:
                        chapter_number += 1
                        title = f"Chapter {chapter_number}"
                    else:
                        chapter_number += 1

                    chapters.append(
                        {
                            "number": str(chapter_number),
                            "title": title,
                            "content": clean_text,
                            "type": "chapter",
                        }
                    )
                    print(f"[EPUB] ✓ Added chapter {chapter_number}: {title}")

            print(
                f"[EPUB] Extracted {len(chapters)} chapters from spine (skipped {skipped_count} short items)"
            )
            return chapters

        except Exception as e:
            print(f"[EPUB] Error extracting chapters: {e}")
            traceback.print_exc()
            return []

    async def process_epub(self, file_path: str, user_id: str = None) -> Dict[str, Any]:
        """Extract text from EPUB file"""
        try:
            book = epub.read_epub(file_path)

            # Extract metadata
            author = None
            try:
                author_metadata = book.get_metadata("DC", "creator")
                if (
                    author_metadata
                    and isinstance(author_metadata, list)
                    and len(author_metadata) > 0
                ):
                    # ebooklib returns tuples like: [('Author Name', {})]
                    if (
                        isinstance(author_metadata[0], tuple)
                        and len(author_metadata[0]) > 0
                    ):
                        author = author_metadata[0][0]
                    elif isinstance(author_metadata[0], str):
                        author = author_metadata[0]

                # Ensure author is a string or None, never a list
                if author and not isinstance(author, str):
                    author = str(author)

                # If still empty or invalid, set to None
                if not author or author.strip() == "":
                    author = None
            except Exception as e:
                print(f"[DEBUG] Error extracting author metadata: {e}")
                author = None

            # Extract text from all document items
            text_content = []

            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    # Parse HTML content
                    soup = BeautifulSoup(item.get_content(), "html.parser")

                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()

                    # Get text and clean it
                    text = soup.get_text()

                    # Break into lines and remove leading/trailing space on each
                    lines = (line.strip() for line in text.splitlines())

                    # Break multi-headlines into a line each
                    chunks = (
                        phrase.strip() for line in lines for phrase in line.split("  ")
                    )

                    # Drop blank lines
                    text = "\n".join(chunk for chunk in chunks if chunk)

                    if text:
                        text_content.append(text)

            # Combine all text
            full_text = "\n\n".join(text_content)

            # Try to extract cover image (optional)
            cover_image_url = None
            # Cover image extraction is complex and optional for now

            return {
                "text": full_text,
                "author": author,
                "cover_image_url": cover_image_url,
            }
        except Exception as e:
            print(f"Error processing EPUB: {e}")
            traceback.print_exc()
            raise

    def extract_chapters(self, content: str, book_type: str) -> List[Dict[str, Any]]:
        """Extract chapters from content based on book type"""
        if book_type == "learning":
            return self.extract_learning_chapters(content)
        else:
            return self.extract_entertainment_chapters(content)

    def _clean_text_content(self, content: str) -> str:
        """Clean text content by handling Unicode escape sequences and other formatting issues"""
        if not content:
            return ""

        try:
            # Use TextSanitizer if available
            sanitizer = TextSanitizer()
            return sanitizer.sanitize(content)
        except:
            # Fallback to basic cleaning
            # Handle common Unicode escape sequences
            content = content.replace("\\n", "\n")
            content = content.replace("\\t", "\t")
            content = content.replace("\\r", "\r")
            content = content.replace('\\"', '"')
            content = content.replace("\\'", "'")

            # Remove any remaining backslash escapes
            import re

            content = re.sub(r"\\(.)", r"\1", content)

            return content.strip()

    def _is_duplicate_chapter(
        self,
        new_chapter: Dict[str, Any],
        existing_chapters: List[Dict[str, Any]],
        similarity_threshold: float = 0.8,
    ) -> bool:
        """Check if a chapter is a duplicate based on title and content similarity"""
        new_title = new_chapter["title"].strip().lower()
        new_content = new_chapter["content"].strip()

        # Create a simple hash of the content for quick comparison
        new_content_hash = hashlib.md5(new_content.encode()).hexdigest()

        for existing_chapter in existing_chapters:
            existing_title = existing_chapter["title"].strip().lower()
            existing_content = existing_chapter["content"].strip()
            existing_content_hash = hashlib.md5(existing_content.encode()).hexdigest()

            # Check if titles are identical or very similar
            if new_title == existing_title:
                return True

            # Check if content is identical (same hash)
            if new_content_hash == existing_content_hash:
                return True

            # Check for very similar content (optional - more expensive)
            if len(new_content) > 50 and len(existing_content) > 50:
                # Simple similarity check based on content length and overlap
                shorter_content = (
                    new_content
                    if len(new_content) < len(existing_content)
                    else existing_content
                )
                longer_content = (
                    existing_content
                    if len(new_content) < len(existing_content)
                    else new_content
                )

                # If shorter content is mostly contained in longer content, it's likely a duplicate
                if len(shorter_content) / len(longer_content) > similarity_threshold:
                    # Check if there's significant overlap
                    overlap_ratio = len(
                        set(shorter_content.split()) & set(longer_content.split())
                    ) / len(set(shorter_content.split()))
                    if overlap_ratio > similarity_threshold:
                        return True

        return False

    def extract_learning_chapters(self, content: str) -> List[Dict[str, Any]]:
        """Extract chapters for learning content (max 50) with duplicate filtering"""
        patterns = [
            r"CHAPTER\s+\d+\.?\s*([^\n]+)",
            r"Chapter\s+\d+\.?\s*([^\n]+)",
            r"CHAPTER\s+\w+\s*([^\n]*)",
            r"Chapter\s+\w+\s*([^\n]*)",
            r"CHAPTER\s+\d+[:\s]*([^\n]+)",
            r"Chapter\s+\d+[:\s]*([^\n]+)",
            r"CHAPTER\s+\w+[:\s]*([^\n]+)",
            r"Chapter\s+\w+[:\s]*([^\n]+)",
            r"Lesson\s+\d+[:\s]*([^\n]+)",
            r"Unit\s+\d+[:\s]*([^\n]+)",
            r"Section\s+\d+[:\s]*([^\n]+)",
            r"Part\s+\d+[:\s]*([^\n]+)",
            r"CHAPTER\s+([A-Z]+)\b",
            r"Chapter\s+([A-Z][a-z]+)\b",
        ]
        chapters = []
        lines = content.split("\n")
        current_chapter = {"title": "Introduction", "content": "", "summary": ""}
        i = 0
        while i < len(lines):
            line = lines[i]
            if len(chapters) >= self.MAX_CHAPTERS:
                break
            is_chapter_header = False
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Look ahead for title if group(1) is empty
                    title = (
                        match.group(1).strip()
                        if match.lastindex and match.group(1).strip()
                        else ""
                    )
                    if not title:
                        # Look ahead for next non-empty line
                        j = i + 1
                        while j < len(lines) and not lines[j].strip():
                            j += 1
                        if j < len(lines):
                            title = lines[j].strip()
                            i = j  # Skip the title line in the next iteration
                    if current_chapter["content"].strip():
                        # Extract content for this chapter using the improved method
                        chapter_start_line = i - current_chapter["content"].count("\n")
                        chapter_content = self._extract_chapter_content(
                            content, current_chapter["title"], lines, chapter_start_line
                        )
                        current_chapter["content"] = chapter_content

                        # Only add chapter if it has meaningful content
                        if len(chapter_content.strip()) > 50:  # Minimum content length
                            if not self._is_duplicate_chapter(
                                current_chapter, chapters
                            ):
                                chapters.append(current_chapter)
                                print(
                                    f"DEBUG: Added learning chapter: {current_chapter['title']}"
                                )
                                print(
                                    f"DEBUG: Chapter content length: {len(current_chapter.get('content', ''))}"
                                )
                                if len(chapters) >= self.MAX_CHAPTERS:
                                    break

                    # if current_chapter["content"].strip():
                    #     if not self._is_duplicate_chapter(current_chapter, chapters):
                    #         chapters.append(current_chapter)
                    #         if len(chapters) >= self.MAX_CHAPTERS:
                    #             break

                    current_chapter = {
                        "title": title,
                        "content": line + "\n",
                        "summary": "",
                    }
                    is_chapter_header = True
                    break
            if not is_chapter_header:
                current_chapter["content"] += line + "\n"
            i += 1
        # if len(chapters) < self.MAX_CHAPTERS and current_chapter["content"].strip():
        #     if not self._is_duplicate_chapter(current_chapter, chapters):
        #         chapters.append(current_chapter)

        if len(chapters) < self.MAX_CHAPTERS and current_chapter["content"].strip():
            # Extract content for the final chapter
            chapter_start_line = len(lines) - current_chapter["content"].count("\n")
            chapter_content = self._extract_chapter_content(
                content, current_chapter["title"], lines, chapter_start_line
            )
            current_chapter["content"] = chapter_content

            # Only add final chapter if it has meaningful content
            if len(chapter_content.strip()) > 50:  # Minimum content length
                if not self._is_duplicate_chapter(current_chapter, chapters):
                    chapters.append(current_chapter)
                    print(
                        f"DEBUG: Added final learning chapter: {current_chapter['title']}"
                    )

        if not chapters:
            chapters = [
                {"title": "Complete Content", "content": content, "summary": ""}
            ]
        print(f"DEBUG: Total chapters extracted: {len(chapters)}")
        return chapters[: self.MAX_CHAPTERS]

    def extract_entertainment_chapters(self, content: str) -> List[Dict[str, Any]]:
        """Extract chapters for entertainment content (max 50) with duplicate filtering"""
        patterns = [
            r"CHAPTER\s+\d+\.?\s*([^\n]+)",
            r"Chapter\s+\d+\.?\s*([^\n]+)",
            r"CHAPTER\s+\w+\s*([^\n]*)",
            r"Chapter\s+\w+\s*([^\n]*)",
            r"CHAPTER\s+\d+[:\s]*([^\n]+)",
            r"Chapter\s+\d+[:\s]*([^\n]+)",
            r"CHAPTER\s+\w+[:\s]*([^\n]+)",
            r"Chapter\s+\w+[:\s]*([^\n]+)",
            r"Scene\s+\d+[:\s]*([^\n]+)",
            r"Act\s+\d+[:\s]*([^\n]+)",
            r"Part\s+\d+[:\s]*([^\n]+)",
            r"Book\s+\d+[:\s]*([^\n]+)",
            r"CHAPTER\s+([A-Z]+)\b",
            r"Chapter\s+([A-Z][a-z]+)\b",
        ]
        chapters = []
        lines = content.split("\n")
        current_chapter = {"title": "Prologue", "content": "", "summary": ""}
        i = 0
        while i < len(lines):
            line = lines[i]
            if len(chapters) >= self.MAX_CHAPTERS:
                break
            is_chapter_header = False
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    title = (
                        match.group(1).strip()
                        if match.lastindex and match.group(1).strip()
                        else ""
                    )
                    if not title:
                        j = i + 1
                        while j < len(lines) and not lines[j].strip():
                            j += 1
                        if j < len(lines):
                            title = lines[j].strip()
                            i = j
                    # if current_chapter["content"].strip():
                    #     if not self._is_duplicate_chapter(current_chapter, chapters):
                    #         chapters.append(current_chapter)
                    #         if len(chapters) >= self.MAX_CHAPTERS:
                    #             break
                    if current_chapter["content"].strip():
                        # Extract content for this chapter using the improved method
                        chapter_start_line = i - current_chapter["content"].count("\n")
                        chapter_content = self._extract_chapter_content(
                            content, current_chapter["title"], lines, chapter_start_line
                        )
                        current_chapter["content"] = chapter_content

                        # Only add chapter if it has meaningful content
                        if len(chapter_content.strip()) > 50:  # Minimum content length
                            if not self._is_duplicate_chapter(
                                current_chapter, chapters
                            ):
                                chapters.append(current_chapter)
                                print(
                                    f"DEBUG: Added entertainment chapter: {current_chapter['title']}"
                                )
                                print(
                                    f"DEBUG: Chapter content length: {len(current_chapter.get('content', ''))}"
                                )
                                if len(chapters) >= self.MAX_CHAPTERS:
                                    break

                    current_chapter = {
                        "title": title,
                        "content": line + "\n",
                        "summary": "",
                    }
                    is_chapter_header = True
                    break
            if not is_chapter_header:
                current_chapter["content"] += line + "\n"
            i += 1
        # if len(chapters) < self.MAX_CHAPTERS and current_chapter["content"].strip():
        #     if not self._is_duplicate_chapter(current_chapter, chapters):
        #         chapters.append(current_chapter)

        if len(chapters) < self.MAX_CHAPTERS and current_chapter["content"].strip():
            # Extract content for the final chapter
            chapter_start_line = len(lines) - current_chapter["content"].count("\n")
            chapter_content = self._extract_chapter_content(
                content, current_chapter["title"], lines, chapter_start_line
            )
            current_chapter["content"] = chapter_content

            # Only add final chapter if it has meaningful content
            if len(chapter_content.strip()) > 50:  # Minimum content length
                if not self._is_duplicate_chapter(current_chapter, chapters):
                    chapters.append(current_chapter)
                    print(
                        f"DEBUG: Added final entertainment chapter: {current_chapter['title']}"
                    )

        if not chapters:
            chapters = [{"title": "Complete Story", "content": content, "summary": ""}]
        print(f"DEBUG: Total chapters extracted: {len(chapters)}")
        return chapters[: self.MAX_CHAPTERS]

    async def extract_chapters_from_pdf_with_toc(
        self, file_path: str, progress_callback=None
    ) -> Optional[List[Dict[str, Any]]]:
        """Updated Multi-strategy TOC extraction with better complexity detection"""
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)

            print("[TOC EXTRACTION] Starting updated multi-strategy extraction...")
            if progress_callback:
                await progress_callback(
                    30,
                    f"Scanning {total_pages} pages for TOC...",
                    "toc",
                    total_pages=total_pages,
                )

            # Strategy 1: Try PDF bookmarks first (most reliable)
            toc = doc.get_toc()
            if toc and len(toc) >= 3:
                if progress_callback:
                    await progress_callback(
                        35, "Found PDF bookmarks, extracting...", "toc"
                    )
                bookmark_chapters = self._process_pdf_bookmarks(doc, toc)
                if len(bookmark_chapters) >= 3:
                    print(
                        f"[TOC EXTRACTION] SUCCESS: PDF bookmarks yielded {len(bookmark_chapters)} chapters"
                    )
                    if progress_callback:
                        await progress_callback(
                            90,
                            f"Extracted {len(bookmark_chapters)} chapters from bookmarks",
                            "complete",
                            completed_step=f"✅ Found {len(bookmark_chapters)} chapters from PDF bookmarks",
                            total_chapters=len(bookmark_chapters),
                        )
                    doc.close()
                    return bookmark_chapters

            # Strategy 2: Analyze TOC complexity to choose appropriate method
            if progress_callback:
                await progress_callback(
                    40, "Detecting Table of Contents pages...", "toc"
                )
            toc_pages = self._find_toc_pages(doc)
            if toc_pages:
                if progress_callback:
                    await progress_callback(
                        45,
                        f"Found TOC on page(s) {[p+1 for p in toc_pages]}",
                        "toc",
                        completed_step=f"✅ TOC detected on page {toc_pages[0]+1}",
                    )
                toc_complexity = self._analyze_toc_complexity(doc, toc_pages)
                print(f"[TOC EXTRACTION] TOC complexity assessment: {toc_complexity}")

                if toc_complexity == "simple":
                    # Strategy 2A: Simple pattern-based extraction for straightforward TOCs
                    if progress_callback:
                        await progress_callback(
                            50, "Extracting chapters from TOC patterns...", "extract"
                        )
                    simple_chapters = await self._extract_simple_toc_patterns(
                        doc, toc_pages
                    )
                    if len(simple_chapters) >= 3:
                        print(
                            f"[TOC EXTRACTION] SUCCESS: Simple pattern extraction yielded {len(simple_chapters)} chapters"
                        )
                        if progress_callback:
                            await progress_callback(
                                55,
                                f"Found {len(simple_chapters)} chapters, extracting content...",
                                "content",
                                completed_step=f"✅ Found {len(simple_chapters)} chapters in TOC",
                                total_chapters=len(simple_chapters),
                            )
                        doc.close()
                        return simple_chapters

                elif toc_complexity == "complex":
                    # Strategy 2B: AI-powered extraction for complex columnar TOCs
                    if progress_callback:
                        await progress_callback(
                            50, "Complex TOC detected, using AI analysis...", "ai"
                        )
                    ai_chapters = await self._extract_complex_toc_with_ai(
                        doc, toc_pages
                    )
                    if len(ai_chapters) >= 5:
                        print(
                            f"[TOC EXTRACTION] SUCCESS: AI complex extraction yielded {len(ai_chapters)} chapters"
                        )
                        if progress_callback:
                            await progress_callback(
                                55,
                                f"AI found {len(ai_chapters)} chapters, extracting content...",
                                "content",
                                completed_step=f"✅ AI extracted {len(ai_chapters)} chapters",
                                total_chapters=len(ai_chapters),
                            )
                        doc.close()
                        return ai_chapters

                # Strategy 3: Pattern-based fallback
                if progress_callback:
                    await progress_callback(
                        55, "Trying pattern-based extraction...", "extract"
                    )
                pattern_chapters = await self._extract_toc_with_patterns(
                    doc, True, toc_pages[0], min(75, len(doc))
                )
                print(
                    f"[DEBUG] Pattern extraction returned {len(pattern_chapters)} chapters"
                )
                if len(pattern_chapters) >= 3:
                    print(
                        f"[TOC EXTRACTION] SUCCESS: Pattern fallback yielded {len(pattern_chapters)} chapters"
                    )
                    if progress_callback:
                        await progress_callback(
                            60,
                            f"Found {len(pattern_chapters)} chapters, extracting content...",
                            "content",
                            completed_step=f"✅ Pattern matching found {len(pattern_chapters)} chapters",
                            total_chapters=len(pattern_chapters),
                        )
                    doc.close()
                    return pattern_chapters
                print(f"[DEBUG] Falling through to AI fallback check")

                # Strategy 3.5: AI Fallback if patterns failed but we have TOC pages
                # This catches the case where complexity is "moderate" (so we skipped explicit AI)
                # but patterns failed to parse the specific format
                print(
                    f"[TOC EXTRACTION] Pattern fallback failed ({len(pattern_chapters)} chapters). Attempting AI fallback on confirmed TOC pages..."
                )
                if progress_callback:
                    await progress_callback(
                        60, "Patterns insufficient, trying AI analysis...", "ai"
                    )
                ai_fallback_chapters = await self._extract_complex_toc_with_ai(
                    doc, toc_pages
                )
                if len(ai_fallback_chapters) >= 3:
                    print(
                        f"[TOC EXTRACTION] SUCCESS: AI fallback yielded {len(ai_fallback_chapters)} chapters"
                    )
                    if progress_callback:
                        await progress_callback(
                            65,
                            f"AI found {len(ai_fallback_chapters)} chapters, extracting content...",
                            "content",
                            completed_step=f"✅ AI analysis found {len(ai_fallback_chapters)} chapters",
                            total_chapters=len(ai_fallback_chapters),
                        )
                    doc.close()
                    return ai_fallback_chapters

            # Strategy 4: Layout analysis with coordinates (last resort for very complex TOCs)
            if toc_pages:
                layout_chapters = await self._analyze_toc_layout_with_coordinates(
                    doc, toc_pages
                )
                if len(layout_chapters) >= 3:
                    print(
                        f"[TOC EXTRACTION] SUCCESS: Layout analysis yielded {len(layout_chapters)} chapters"
                    )
                    doc.close()
                    return layout_chapters

            doc.close()
            print("[TOC EXTRACTION] All strategies failed")
            return []

        except Exception as e:
            print(f"[TOC EXTRACTION] Error: {e}")
            return []

    def _analyze_toc_complexity(self, doc, toc_pages: List[int]) -> str:
        """Analyze TOC complexity to determine extraction strategy"""

        complexity_indicators = {
            "simple_patterns": 0,
            "complex_patterns": 0,
            "section_indicators": 0,
            "columnar_layout": 0,
        }

        for page_num in toc_pages[:3]:  # Check first 3 TOC pages
            page = doc[page_num]
            text = page.get_text()

            # ✅ FIX: Better TOC header detection
            has_contents_header = bool(
                re.search(r"\b(contents|table\s+of\s+contents)\b", text, re.IGNORECASE)
            )

            # Check for simple chapter patterns
            simple_chapter_patterns = [
                r"CHAPTER\s+\d+[\.\s]+[A-Z]",  # "CHAPTER 1. Title"
                r"Chapter\s+\d+[\.\s]+[A-Z]",  # "Chapter 1. Title"
                r"^\s*\d+\.\s+[A-Z]",  # "1. Title"
                r"CHAPTER\s+\d+\s+[A-Z]",  # "CHAPTER 1 Title" (no dot)
                r"Chapter\s+\d+\s+[A-Z]",  # "Chapter 1 Title" (no dot)
            ]

            for pattern in simple_chapter_patterns:
                matches = len(re.findall(pattern, text, re.MULTILINE))
                complexity_indicators["simple_patterns"] += matches

            # Check for complex/hierarchical patterns
            complex_patterns = [
                r"BOOK\s+THE\s+(FIRST|SECOND|THIRD)",  # "BOOK THE FIRST"
                r"PART\s+[IVX]+",  # "PART I", "PART II"
                r"ACT\s+[IVX]+",  # "ACT I"
                r"SECTION\s+[IVX]+",  # "SECTION I"
            ]

            for pattern in complex_patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                complexity_indicators["section_indicators"] += matches

            # Check for columnar layout indicators
            lines = text.split("\n")
            for line in lines:
                # Look for multiple page numbers on one line (columnar format)
                page_numbers = re.findall(r"\b\d{2,3}\b", line)
                if len(page_numbers) >= 2:
                    complexity_indicators["columnar_layout"] += 1

        print(f"[TOC COMPLEXITY] Indicators: {complexity_indicators}")

        # Determine complexity
        # if complexity_indicators['section_indicators'] >= 2 or complexity_indicators['columnar_layout'] >= 3:
        #     return "complex"
        # elif complexity_indicators['simple_patterns'] >= 5:
        #     return "simple"
        # else:
        #     return "moderate"

        if complexity_indicators["section_indicators"] >= 2:
            return "complex"
        elif complexity_indicators["columnar_layout"] >= 3:
            return "complex"
        elif complexity_indicators["simple_patterns"] >= 3:  # Lowered threshold
            return "simple"
        else:
            return "moderate"  # This will still use pattern-based extraction

    async def _extract_simple_toc_patterns(
        self, doc, toc_pages: List[int]
    ) -> List[Dict[str, Any]]:
        """Extract chapters from simple, straightforward TOCs (like Angel Magic book)"""
        print("[SIMPLE TOC] Extracting from simple TOC structure...")

        all_chapters = []

        for page_num in toc_pages:
            page = doc[page_num]
            text = page.get_text()

            print(f"[SIMPLE TOC] Processing page {page_num + 1}")
            print(f"[SIMPLE TOC] First 500 chars: {text[:500]}")

            # Focus on clear chapter patterns only
            chapter_patterns = [
                # Standard patterns
                r"CHAPTER\s+(\d+)[\.\s]*(.+?)\s+(\d+)",  # "CHAPTER 1. Title 123"
                r"Chapter\s+(\d+)[\.\s]*(.+?)\s+(\d+)",  # "Chapter 1. Title 123"
                r"^(\d+)\.\s+(.+?)\s+(\d{1,3})$",  # "1. Title 123" - improved end anchor
                # ✅ NEW: Angel Magic specific patterns
                r"CHAPTER\s+(\d+)[\.\s]+([A-Z][^\.]+?)\s+(\d+)",  # "CHAPTER 1. Introduction to Angel Magic 1"
                r"Chapter\s+(\d+)[\.\s]+([A-Z][^\.]+?)\s+(\d+)",  # "Chapter 1. Introduction to Angel Magic 1"
                # Flexible dot patterns
                r"CHAPTER\s+(\d+)\s+([A-Z][^\n]+?)\s+(\d+)$",  # "CHAPTER 1 Title 123" (no dots)
                r"Chapter\s+(\d+)\s+([A-Z][^\n]+?)\s+(\d+)$",  # "Chapter 1 Title 123" (no dots)           # "1. Title 123"
            ]

            for pattern_idx, pattern in enumerate(chapter_patterns):
                matches = re.findall(pattern, text, re.MULTILINE)
                print(
                    f"[SIMPLE TOC] Pattern {pattern_idx} found {len(matches)} matches"
                )

                for match in matches:
                    chapter_num, title, page_str = match

                    clean_title = title.strip()
                    # Clean title - remove dots and extra whitespace
                    clean_title = re.sub(r"\.+$", "", title.strip())
                    clean_title = re.sub(r"\s+", " ", clean_title)

                    # Skip if title is too short, contains appendix materials, or looks like page number
                    if (
                        len(clean_title) < 3
                        or clean_title.isdigit()
                        or any(
                            word in clean_title.lower()
                            for word in [
                                "appendix",
                                "index",
                                "bibliography",
                                "notes",
                                "figures",
                                "illustrations",
                                "notes only",
                                "references only",
                            ]
                        )
                    ):
                        print(
                            f"[SIMPLE TOC] Skipping: '{clean_title}' (too short or appendix)"
                        )
                        continue

                    try:
                        all_chapters.append(
                            {
                                "number": int(chapter_num),
                                "title": f"Chapter {chapter_num}: {clean_title}",
                                "raw_title": clean_title,
                                "page_hint": int(page_str),
                                "is_main_chapter": True,
                            }
                        )
                        print(
                            f"[SIMPLE TOC] Found: Chapter {chapter_num}: {clean_title}"
                        )
                    except ValueError:
                        print(
                            f"[SIMPLE TOC] ❌ Error parsing chapter {chapter_num}: {e}"
                        )
                        continue

        # Remove duplicates and sort
        unique_chapters = {}
        for ch in all_chapters:
            if ch["number"] not in unique_chapters:
                unique_chapters[ch["number"]] = ch

        sorted_chapters = sorted(unique_chapters.values(), key=lambda x: x["number"])

        print(f"[SIMPLE TOC] Extracted {len(sorted_chapters)} simple chapters")
        for ch in sorted_chapters:
            print(f"[SIMPLE TOC] Final: {ch['title']}")

        if len(sorted_chapters) >= 3:
            return await self._parse_toc_with_ai_improved(sorted_chapters, doc)

        return []

    def _find_toc_pages(self, doc) -> List[int]:
        """Find pages that likely contain TOC - IMPROVED with better validation"""
        toc_pages = []
        confirmed_toc_start = None

        for page_num in range(min(30, len(doc))):
            page = doc[page_num]
            text = page.get_text()

            # OCR fallback for image-based/scanned PDFs
            if not text.strip() and page_num < 15:
                try:
                    # Try PyMuPDF's built-in OCR (requires Tesseract)
                    tp = page.get_textpage_ocr(
                        flags=0, language="eng", dpi=150, full=True
                    )
                    text = page.get_text(textpage=tp)
                    if text.strip():
                        print(
                            f"[OCR] Successfully extracted text from page {page_num + 1} via OCR"
                        )
                except Exception as e:
                    # OCR not available or failed
                    print(f"[OCR] OCR failed for page {page_num + 1}: {e}")

            text_upper = text.upper()

            # DEBUG: Print text from likely TOC pages to see actual format
            if 7 <= page_num <= 12:
                print(f"[DEBUG TOC] Page {page_num + 1} text (first 500 chars):")
                print(repr(text[:500]))
                print("---END DEBUG---")

            # ✅ FIX: First, look for explicit TOC headers
            explicit_toc_indicators = [r"\bCONTENTS\b", r"\bTABLE\s+OF\s+CONTENTS\b"]

            has_explicit_toc = any(
                re.search(pattern, text_upper) for pattern in explicit_toc_indicators
            )

            if has_explicit_toc:
                print(f"[TOC PAGES] Found explicit TOC header on page {page_num + 1}")
                toc_pages.append(page_num)
                if confirmed_toc_start is None:
                    confirmed_toc_start = page_num
                continue

            # ✅ FIX: Only look for chapter patterns if we're near a confirmed TOC start
            if confirmed_toc_start is not None:
                # Check if this page continues the TOC (must be within 10 pages of TOC start)
                if page_num <= confirmed_toc_start + 9:

                    spelled_num = (
                        self.structure_detector.SPELLED_NUMBER_RE
                        if hasattr(self, "structure_detector")
                        else r"(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTY|THIRTY-ONE|TWENTY|TWENTY-ONE)"
                    )

                    chapter_patterns = [
                        r"CHAPTER\s+\d+",  # "CHAPTER 1", "CHAPTER 2"
                        r"Chapter\s+\d+",  # "Chapter 1", "Chapter 2"
                        r"CHAPTER\s+[IVX]+",  # "CHAPTER I", "CHAPTER II"
                        r"Chapter\s+[IVX]+",  # "Chapter I", "Chapter II"
                        r"BOOK\s+THE\s+(FIRST|SECOND|THIRD)",  # "BOOK THE FIRST"
                        rf"{spelled_num}",  # Spelled out numbers like "THIRTY"
                    ]

                    chapter_matches = 0
                    for pattern in chapter_patterns:
                        chapter_matches += len(re.findall(pattern, text))

                    # ✅ FIX: Require substantial TOC-like formatting
                    # Relaxed dot matching (allow single dots with spaces)
                    page_number_patterns = len(
                        re.findall(r"(\.{2,}|\s\.\s)\s*\d+", text)
                    )  # Dots leading to page numbers

                    # Must have BOTH chapter patterns AND TOC formatting
                    # Relax logic: if we have MANY chapter matches, we need fewer dots
                    if (chapter_matches >= 3 and page_number_patterns >= 1) or (
                        chapter_matches >= 5
                    ):
                        print(
                            f"[TOC PAGES] Found TOC continuation on page {page_num + 1} ({chapter_matches} chapters, {page_number_patterns} page refs)"
                        )
                        toc_pages.append(page_num)
                    else:
                        print(
                            f"[TOC PAGES] Page {page_num + 1} doesn't meet TOC continuation criteria (chapters: {chapter_matches}, page refs: {page_number_patterns})"
                        )
                else:
                    print(
                        f"[TOC PAGES] Page {page_num + 1} too far from TOC start ({confirmed_toc_start + 1})"
                    )
            else:
                # ✅ FIX: Without confirmed TOC start, be much more strict
                # Only accept pages that have very strong TOC indicators
                strong_toc_score = 0

                spelled_num = (
                    self.structure_detector.SPELLED_NUMBER_RE
                    if hasattr(self, "structure_detector")
                    else r"(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|THIRTY)"
                )

                # Count chapter-like entries with page numbers
                chapter_with_pages = len(
                    re.findall(
                        r"(CHAPTER|Chapter)\s+[IVX\d]+.*?\d+\s*$", text, re.MULTILINE
                    )
                )

                # Also check for spelled out lines ending in numbers
                spelled_with_pages = len(
                    re.findall(
                        rf"{spelled_num}\s*\n.*?\.{{1,}}\s*\d+\s*$", text, re.MULTILINE
                    )
                )

                if chapter_with_pages >= 5 or spelled_with_pages >= 3:
                    strong_toc_score += 3

                # ✅ NEW: Count numbered entries with page numbers (e.g., "1. Title Name 11")
                # This handles TOC formats like: "1. Our Gang: The Electronics Kids 11"
                numbered_entries = len(
                    re.findall(
                        r"^\s*\d+\.\s+[A-Za-z][^\n]{3,}\s+\d{1,3}\s*$",
                        text,
                        re.MULTILINE,
                    )
                )
                if numbered_entries >= 5:
                    strong_toc_score += 3
                    print(
                        f"[TOC PAGES] Page {page_num + 1} has {numbered_entries} numbered entries"
                    )

                # Count dotted lines (TOC formatting)
                dotted_lines = len(re.findall(r"(\.{3,}|\s\.\s)\s*\d+", text))
                if dotted_lines >= 3:
                    strong_toc_score += 2

                # Count structural divisions
                structural_divisions = len(
                    re.findall(r"BOOK\s+THE\s+(FIRST|SECOND|THIRD)", text_upper)
                )
                if structural_divisions >= 1:
                    strong_toc_score += 2

                # Only add if we have strong evidence (lowered from 5 to 3 for numbered lists)
                if strong_toc_score >= 3:
                    print(
                        f"[TOC PAGES] Found strong TOC page at {page_num + 1} (score: {strong_toc_score})"
                    )
                    toc_pages.append(page_num)
                    if confirmed_toc_start is None:
                        confirmed_toc_start = page_num
                else:
                    print(
                        f"[TOC PAGES] Page {page_num + 1} insufficient TOC evidence (score: {strong_toc_score})"
                    )

        # ✅ FIX: Additional validation - remove isolated pages
        if len(toc_pages) > 1:
            validated_pages = []
            for page in toc_pages:
                # Keep page if it's the first TOC page or within 2 pages of another TOC page
                if page == confirmed_toc_start or any(
                    abs(page - other_page) <= 2
                    for other_page in toc_pages
                    if other_page != page
                ):
                    validated_pages.append(page)
                else:
                    print(f"[TOC PAGES] Removing isolated TOC page {page + 1}")

            toc_pages = validated_pages

        print(f"[TOC PAGES] Final TOC pages: {[p + 1 for p in toc_pages]}")
        return toc_pages

    def _process_pdf_bookmarks(self, doc, toc) -> List[Dict[str, Any]]:
        """Process PDF bookmarks into chapters"""
        chapters = []
        main_chapters = [item for item in toc if item[0] == 1]  # Level 1 items only

        for i, (level, title, page) in enumerate(main_chapters):
            start_page = page - 1
            end_page = len(doc) - 1

            # Find next chapter
            if i + 1 < len(main_chapters):
                end_page = main_chapters[i + 1][2] - 2

            # Extract content
            chapter_text = ""
            for p in range(start_page, min(end_page + 1, len(doc))):
                chapter_text += doc[p].get_text()

            if len(chapter_text.strip()) > 500:  # Minimum content threshold
                chapters.append(
                    {
                        "title": title.strip(),
                        "content": chapter_text.strip(),
                        "summary": "",
                        "chapter_number": i + 1,
                    }
                )

        print(f"[TOC EXTRACTION] Processed {len(chapters)} chapters from bookmarks")
        return chapters

    async def _extract_content_for_chapters(
        self, validated_chapters: List[Dict], full_text: str
    ) -> List[Dict[str, Any]]:
        """Step 4: Extract content by searching for chapter titles in the text"""
        print("[CONTENT EXTRACTION] Extracting content by searching chapter titles...")

        final_chapters = []

        for i, chapter in enumerate(validated_chapters):
            chapter_title = chapter["title"]
            print(f"[CONTENT EXTRACTION] Extracting content for: {chapter_title}")

            # Search for chapter title in text (flexible matching)
            chapter_patterns = [
                re.escape(chapter_title),  # Exact match
                re.escape(
                    chapter_title.replace("Chapter ", "").replace(":", "")
                ),  # Without "Chapter" prefix
                (
                    re.escape(chapter_title.split(":")[-1].strip())
                    if ":" in chapter_title
                    else None
                ),  # Just the title part
            ]

            content_start = None
            for pattern in chapter_patterns:
                if pattern:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        content_start = match.end()
                        print(
                            f"[CONTENT EXTRACTION] Found chapter start at position {content_start}"
                        )
                        break

            if content_start is None:
                print(f"[CONTENT EXTRACTION] Could not find chapter: {chapter_title}")
                continue

            # Find content end (start of next chapter or end of book)
            content_end = len(full_text)
            if i + 1 < len(validated_chapters):
                next_chapter = validated_chapters[i + 1]["title"]
                next_match = re.search(
                    re.escape(next_chapter), full_text[content_start:], re.IGNORECASE
                )
                if next_match:
                    content_end = content_start + next_match.start()

            # Extract content
            content = full_text[content_start:content_end].strip()

            if len(content) > 200:
                # Validate first 200 characters with AI
                is_valid = await self._validate_content_match(
                    chapter_title, content[:200]
                )
                if is_valid:
                    final_chapters.append(
                        {
                            "title": chapter_title,
                            "content": content,
                            "summary": f"Content for {chapter_title}",
                            "chapter_number": i + 1,
                        }
                    )
                    print(
                        f"[CONTENT EXTRACTION] Successfully extracted {len(content)} chars for: {chapter_title}"
                    )
                else:
                    print(
                        f"[CONTENT EXTRACTION] Content validation failed for: {chapter_title}"
                    )
            else:
                print(f"[CONTENT EXTRACTION] Insufficient content for: {chapter_title}")

        return final_chapters

    @staticmethod
    def _roman_to_int(roman: str) -> int:
        values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        total = 0
        prev = 0
        for ch in roman.upper():
            v = values.get(ch, 0)
            total += v
            if v > prev:
                total -= 2 * prev
            prev = v
        return total or 0

    async def _extract_toc_from_text(self, doc) -> List[Dict[str, Any]]:
        """Enhanced TOC extraction with AI as primary method"""
        print("[TOC EXTRACTION] Searching for table of contents...")

        max_scan = min(75, len(doc))
        toc_page_start = None

        # First pass: Find TOC pages and extract raw text
        toc_text_blocks = []

        for page_num in range(max_scan):
            page = doc[page_num]
            text = page.get_text()
            if not text:
                continue

            print(f"[TOC EXTRACTION] Checking page {page_num + 1}...")

            # Check for "CONTENTS" or "TABLE OF CONTENTS" header
            if re.search(r"\b(CONTENTS|TABLE OF CONTENTS)\b", text, re.IGNORECASE):
                print(f"[TOC EXTRACTION] Found Contents header on page {page_num + 1}")
                if toc_page_start is None:
                    toc_page_start = page_num

                # Store the raw text for AI analysis
                toc_text_blocks.append(
                    {"page_num": page_num + 1, "text": text, "lines": text.split("\n")}
                )

        # FIX: Always try AI extraction first if we found TOC pages
        if toc_text_blocks:
            print(
                f"[TOC EXTRACTION] Found {len(toc_text_blocks)} TOC pages, using AI extraction as primary method..."
            )
            ai_chapters = await self._extract_toc_with_ai(toc_text_blocks, doc)

            # FIX: Lower the threshold - if AI finds ANY reasonable number of chapters, use them
            if len(ai_chapters) >= 5:  # Reduced from 8 to 5
                print(
                    f"[TOC EXTRACTION] AI successfully extracted {len(ai_chapters)} chapters"
                )
                return await self._parse_toc_with_ai_improved(ai_chapters, doc)
            else:
                print(
                    f"[TOC EXTRACTION] AI found {len(ai_chapters)} chapters, trying pattern-based as backup..."
                )

        # Fallback to pattern-based extraction
        print("[TOC EXTRACTION] Using pattern-based extraction as fallback...")
        pattern_chapters = await self._extract_toc_with_patterns(
            doc, bool(toc_text_blocks), toc_page_start, max_scan
        )

        # FIX: If pattern-based finds very few chapters but AI found some, combine them
        if toc_text_blocks and len(pattern_chapters) <= 4 and len(ai_chapters) >= 3:
            print(
                f"[TOC EXTRACTION] Pattern-based found only {len(pattern_chapters)} chapters, combining with AI results..."
            )

            # Merge AI and pattern results, preferring AI
            combined_chapters = []
            seen_titles = set()

            # Add AI chapters first
            for ch in ai_chapters:
                title_key = ch.get("raw_title", "").lower().strip()
                if title_key and title_key not in seen_titles:
                    combined_chapters.append(ch)
                    seen_titles.add(title_key)

            # Add any unique pattern chapters
            for ch in pattern_chapters:
                title_key = ch.get("raw_title", "").lower().strip()
                if title_key and title_key not in seen_titles:
                    combined_chapters.append(ch)
                    seen_titles.add(title_key)

            if len(combined_chapters) > len(pattern_chapters):
                print(
                    f"[TOC EXTRACTION] Combined approach yielded {len(combined_chapters)} chapters"
                )
                return await self._parse_toc_with_ai_improved(combined_chapters, doc)

        return pattern_chapters

    def _extract_section_type(self, section_text: str) -> str:
        """Extract section type from section title"""
        section_lower = section_text.lower()
        if "book" in section_lower:
            return "book"
        elif "part" in section_lower:
            return "part"
        elif "section" in section_lower:
            return "section"
        elif "chapter" in section_lower:
            return "chapter"
        else:
            return "section"

    def _extract_section_number(self, section_text: str) -> str:
        """Extract section number from section title"""
        # Look for patterns like "FIRST", "SECOND", "THE FIRST", etc.
        section_words = ["FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH"]
        for word in section_words:
            if word in section_text.upper():
                return word.title()

        # Look for Roman numerals
        roman_match = re.search(r"\b([IVX]+)\b", section_text.upper())
        if roman_match:
            return roman_match.group(1)

        # Look for Arabic numbers
        num_match = re.search(r"\b(\d+)\b", section_text)
        if num_match:
            return num_match.group(1)

        return ""

    async def _extract_toc_with_patterns(
        self,
        doc,
        found_contents_page: bool,
        toc_page_start: Optional[int],
        max_scan: int,
    ) -> List[Dict[str, Any]]:
        """Enhanced pattern-based extraction to find ALL sections and chapters"""
        print("[PATTERN TOC EXTRACTION] Using pattern-based extraction...")

        all_entries: List[Dict[str, Any]] = []
        current_section: Optional[Dict[str, Any]] = None

        # ✅ FIX: Better section patterns to catch all book sections
        section_patterns = [
            re.compile(
                r"^\s*(BOOK|PART|SECTION)\s+(THE\s+)?(FIRST|SECOND|THIRD|FOURTH|FIFTH|ONE|TWO|THREE|FOUR|FIVE|[IVX]+|\d+)[\s\-:]*(.*)$",
                re.MULTILINE | re.IGNORECASE,
            ),
        ]

        # ✅ FIX: More comprehensive chapter patterns for different TOC layouts
        spelled_num = (
            self.structure_detector.SPELLED_NUMBER_RE
            if hasattr(self, "structure_detector")
            else ""
        )

        chapter_patterns = [
            # Pattern for "I. TITLE ... PAGE" format
            re.compile(
                rf"^\s*([IVX]+)\.\s+([A-Z][A-Z\s]+[A-Z])\s+\.{{2,}}\s*(\d+)\s*$",
                re.MULTILINE,
            ),
            # Pattern for "I. TITLE PAGE" format (without dots)
            re.compile(
                rf"^\s*([IVX]+)\.\s+([A-Z][A-Z\s]+[A-Z])\s+(\d+)\s*$", re.MULTILINE
            ),
            # Pattern for Roman numeral on separate line from title
            re.compile(
                r"^\s*([IVX]+)\s*$\s*([A-Z][A-Z\s]+[A-Z])\s+(\d+)$", re.MULTILINE
            ),
            # Pattern for spelled out number (THIRTY) on separate line from title
            re.compile(
                rf"^\s*{spelled_num}\s*\n\s*([A-Z][^\n]+?)\s+(\.{{1,}}|\s)\s*(\d+)\s*$",
                re.MULTILINE | re.IGNORECASE,
            ),
            # Pattern for titles that span multiple lines
            re.compile(r"^\s*([IVX]+)\s*\n\s*([A-Z][^\n]+?)\s+(\d+)\s*$", re.MULTILINE),
            # Pattern for complex multi-line titles
            re.compile(
                r"^\s*([IVX]+)\s*\n\s*([A-Z][^\n]+)\n\s*([A-Z][^\n]*)\s+(\d+)\s*$",
                re.MULTILINE,
            ),
        ]

        found_any = False

        # ✅ FIX: Scan more pages to find all TOC content
        scan_end = min(max_scan, len(doc))
        for page_num in range(scan_end):
            page = doc[page_num]
            text = page.get_text()

            print(f"[PATTERN TOC EXTRACTION] Checking page {page_num + 1}...")

            # Look for section headers first
            for section_pattern in section_patterns:
                for match in section_pattern.finditer(text):
                    section_type = match.group(1).lower()  # BOOK, PART, etc.
                    section_number_word = match.group(3)  # FIRST, SECOND, etc.
                    section_subtitle = match.group(4)  # The rest of the title

                    section_title = (
                        f"{match.group(1).title()} the {section_number_word.title()}"
                    )
                    if section_subtitle.strip():
                        section_title += f": {section_subtitle.strip()}"

                    current_section = {
                        "title": section_title,
                        "type": section_type,
                        "number": section_number_word.lower(),
                    }
                    print(f"[PATTERN TOC EXTRACTION] Found section: {section_title}")
                    found_any = True

            # Look for chapters in current section context
            for pattern_idx, chapter_pattern in enumerate(chapter_patterns):
                matches = list(chapter_pattern.finditer(text))
                print(
                    f"[PATTERN TOC EXTRACTION] Pattern {pattern_idx} found {len(matches)} matches on page {page_num + 1}"
                )

                for match in matches:
                    try:
                        if len(match.groups()) == 3:
                            num_str, title_str, page_str = match.groups()
                        elif len(match.groups()) == 4:  # Multi-line title
                            if (
                                pattern_idx == 3
                            ):  # Check if it's our spelled-out pattern
                                # Spelled num regex has nested groups, so match.groups is messier
                                # Wait, SPELLED_NUMBER_RE is ((?:...)) so has 1 capturing group.
                                # So (Number, Title, Separator, Page) -> 4 groups.
                                num_str, title_str, sep, page_str = match.groups()
                            else:
                                num_str, title_part1, title_part2, page_str = (
                                    match.groups()
                                )
                                title_str = f"{title_part1.strip()} {title_part2.strip()}".strip()
                        else:
                            continue

                        print(
                            f"[PATTERN TOC EXTRACTION] Raw match: num='{num_str}', title='{title_str}', page='{page_str}'"
                        )

                        # Convert Roman OR Spelled to Arabic
                        try:
                            # Try simple/roman conversion
                            if re.match(r"^[IVXLCDM]+$", num_str.strip().upper()):
                                chapter_number = self._roman_to_int(
                                    num_str.strip().upper()
                                )
                            else:
                                # Try normalizer for spelled out numbers
                                norm = (
                                    self.structure_detector._normalize_chapter_number(
                                        num_str
                                    )
                                )
                                if norm.isdigit():
                                    chapter_number = int(norm)
                                else:
                                    print(
                                        f"[PATTERN TOC EXTRACTION] Failed to normalize number: {num_str}"
                                    )
                                    continue

                            print(
                                f"[PATTERN TOC EXTRACTION] Converted '{num_str}' to {chapter_number}"
                            )
                        except:
                            continue

                        # Validate page number
                        try:
                            page_number = int(page_str.strip())
                            print(
                                f"[PATTERN TOC EXTRACTION] Page number: {page_number}"
                            )
                        except:
                            continue

                        # Clean title
                        clean_title = title_str.strip()
                        if len(clean_title) < 3:
                            continue

                        entry = {
                            "number": chapter_number,
                            "title": f"Chapter {chapter_number}: {clean_title}",
                            "raw_title": clean_title,
                            "page_hint": page_number,
                            "is_main_chapter": True,
                        }

                        # Add section info if we have a current section
                        if current_section:
                            entry.update(
                                {
                                    "section_title": current_section["title"],
                                    "section_type": current_section["type"],
                                    "section_number": current_section["number"],
                                }
                            )
                            print(
                                f"[PATTERN TOC EXTRACTION] Found chapter: {clean_title} (sec={current_section['title']})"
                            )
                        else:
                            print(
                                f"[PATTERN TOC EXTRACTION] Found chapter: {clean_title} (no section)"
                            )

                        all_entries.append(entry)
                        found_any = True

                    except Exception as e:
                        print(f"[PATTERN TOC EXTRACTION] Error processing match: {e}")
                        continue

            # ✅ FIX: Stop scanning after we've gone well past TOC pages
            if toc_page_start is not None and page_num > toc_page_start + 15:
                print(f"[PATTERN TOC EXTRACTION] Stopping: 15+ pages past TOC start")
                break

        # Process results
        if not all_entries:
            print("[PATTERN TOC EXTRACTION] No entries found")
            return []

        # ✅ FIX: Improved deduplication that preserves different sections
        dedup = {}
        for item in all_entries:
            # Create key that includes section info to avoid cross-section duplicates
            section_key = item.get("section_title", "no_section")
            chapter_key = (
                f"{section_key}_{item.get('number')}_{item.get('raw_title', '')}"
            )

            if chapter_key not in dedup:
                dedup[chapter_key] = item

        chapters = list(dedup.values())

        # Sort by section and then by chapter number
        chapters.sort(
            key=lambda x: (
                x.get("section_title", "zzz_no_section"),
                x.get("number", 10_000),
            )
        )

        print(
            f"[PATTERN TOC EXTRACTION] Found {len(chapters)} total unique chapters after improved dedupe"
        )
        for ch in chapters:
            section_info = (
                f" | section={ch.get('section_title', 'None')}"
                if ch.get("section_title")
                else ""
            )
            print(
                f"[PATTERN TOC EXTRACTION] Final: {ch.get('title', 'Unknown')}{section_info}"
            )

        # Add structure detection and return
        if chapters:
            structure_type = self._detect_structure_from_chapters(chapters)
            print(f"[PATTERN TOC EXTRACTION] Detected structure type: {structure_type}")

        if len(chapters) >= 3:
            return await self._parse_toc_with_ai_improved(chapters, doc)

        return []

    async def _analyze_toc_layout_with_coordinates(
        self, doc, toc_pages: List[int]
    ) -> List[Dict]:
        """Analyze TOC layout using text coordinates for complex layouts"""
        print("[LAYOUT ANALYSIS] Analyzing TOC text positioning...")

        chapters = []

        for page_num in toc_pages:
            page = doc[page_num]

            # Get text with coordinates
            text_dict = page.get_text("dict")

            # Group text blocks by vertical position
            text_blocks = []
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                text_blocks.append(
                                    {
                                        "text": text,
                                        "bbox": span["bbox"],
                                        "x": span["bbox"][0],
                                        "y": span["bbox"][1],
                                        "font_size": span["size"],
                                    }
                                )

            # Sort by vertical position
            text_blocks.sort(key=lambda x: x["y"])

            # Look for columnar patterns
            chapters.extend(
                self._extract_chapters_from_layout(text_blocks, page_num + 1)
            )

        return chapters

    def _extract_chapters_from_layout(
        self, text_blocks: List[Dict], page_num: int
    ) -> List[Dict]:
        """Extract chapters from positioned text blocks with deduplication"""
        chapters = []

        # Find potential chapter numbers (Roman numerals in specific positions)
        roman_numerals = []
        titles = []
        page_numbers = []

        for block in text_blocks:
            text = block["text"].strip()

            # Detect Roman numerals
            if re.match(r"^[IVX]+\.?$", text.upper()):
                roman_numerals.append(
                    {
                        "text": text.rstrip("."),
                        "position": block,
                        "number": self._roman_to_int(text.rstrip(".")),
                    }
                )

            # Detect titles (uppercase, reasonable length)
            elif (
                re.match(r"^[A-Z][A-Z\s]+[A-Z]$", text)
                and 5 <= len(text) <= 50
                and text not in ["CONTENTS", "CHAPTER", "PAGE"]
            ):
                titles.append({"text": text, "position": block})

            # Detect page numbers
            elif re.match(r"^\d+$", text) and 1 <= int(text) <= 1000:
                page_numbers.append({"text": int(text), "position": block})

        print(
            f"[LAYOUT ANALYSIS] Page {page_num}: Found {len(roman_numerals)} numerals, {len(titles)} titles, {len(page_numbers)} page nums"
        )

        # Track used components to avoid duplicates
        used_numerals = set()
        used_titles = set()
        used_pages = set()

        # Match numerals with titles and page numbers
        for numeral in roman_numerals:
            if numeral["number"] in used_numerals:
                continue

            # Find the closest title (vertically)
            closest_title = None
            min_distance = float("inf")

            for title in titles:
                if title["text"] in used_titles:
                    continue
                # Calculate vertical distance
                distance = abs(title["position"]["y"] - numeral["position"]["y"])
                if distance < min_distance:
                    min_distance = distance
                    closest_title = title

            if closest_title and min_distance < 50:  # Within 50 units vertically
                # Find associated page number
                associated_page = None
                for page_num_obj in page_numbers:
                    if page_num_obj["text"] in used_pages:
                        continue
                    # Find page numbers in the same horizontal area
                    if (
                        abs(
                            page_num_obj["position"]["x"]
                            - closest_title["position"]["x"]
                        )
                        < 200
                    ):
                        associated_page = page_num_obj
                        break

                if associated_page:
                    chapter = {
                        "number": numeral["number"],
                        "title": f"Chapter {numeral['number']}: {closest_title['text']}",
                        "raw_title": closest_title["text"],
                        "page_hint": associated_page["text"],
                    }
                    chapters.append(chapter)

                    # Mark as used
                    used_numerals.add(numeral["number"])
                    used_titles.add(closest_title["text"])
                    used_pages.add(associated_page["text"])

                    print(
                        f"[LAYOUT ANALYSIS] Matched: Chapter {numeral['number']}: {closest_title['text']} -> page {associated_page['text']}"
                    )

        return chapters

    async def _parse_toc_with_ai_improved(
        self, chapters: List[Dict], doc
    ) -> List[Dict[str, Any]]:
        """Use page-based extraction to get actual content - GENERIC approach"""
        print(f"[TOC PARSING] Using page-based extraction for {len(chapters)} chapters")

        # Filter chapters that have valid page numbers
        chapters_with_pages = []
        for chapter in chapters:
            page_hint = chapter.get("page_hint")
            if page_hint and isinstance(page_hint, int) and page_hint > 0:
                chapters_with_pages.append(chapter)
                print(
                    f"[TOC PARSING] Chapter '{chapter['title']}' starts at page {page_hint}"
                )
            else:
                print(
                    f"[TOC PARSING] Skipping chapter without valid page: '{chapter['title']}'"
                )

        if len(chapters_with_pages) >= 3:
            print(
                f"[TOC PARSING] Proceeding with content extraction for {len(chapters_with_pages)} chapters"
            )
            # Use page-based extraction
            extracted_chapters = (
                await self.structure_detector._extract_content_for_chapters_by_pages(
                    chapters_with_pages, doc
                )
            )

            # Ensure we have content
            chapters_with_content = []
            for chapter in extracted_chapters:
                if chapter.get("content") and len(chapter["content"].strip()) > 100:
                    chapters_with_content.append(chapter)
                    print(
                        f"[CONTENT CHECK] Chapter '{chapter['title']}' has {len(chapter['content'])} chars"
                    )
                else:
                    print(
                        f"[CONTENT CHECK] Chapter '{chapter['title']}' has insufficient content"
                    )

            return chapters_with_content
        else:
            print(
                "[TOC PARSING] Not enough chapters with page numbers for page-based extraction"
            )
            return []

    def _identify_toc_boundaries(self, full_text: str) -> Dict[str, int]:
        """Better TOC boundary detection"""
        toc_patterns = [
            r"\bContents\b",
            r"\bTable of Contents\b",
            r"CHAPTER\s+1\.\s+.*?\d+\s*\n.*?CHAPTER\s+2\.",  # Multiple chapter listings
        ]

        start_pos = 0
        end_pos = 5000  # Default to first 5000 chars

        # Find TOC start
        for pattern in toc_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                start_pos = match.start()
                break

        # Find TOC end by looking for actual chapter content start
        # Look for "1\nIntroduction\nto Angel Magic" pattern (your book's format)
        chapter_start_pattern = r"\n\s*1\s*\n[A-Z][^\.]*\n[A-Z][^\.]*"
        match = re.search(chapter_start_pattern, full_text[start_pos:])
        if match:
            end_pos = start_pos + match.start()

        return {"start": start_pos, "end": end_pos}

    async def _extract_content_for_chapters_improved(
        self, validated_chapters: List[Dict], full_text: str
    ) -> List[Dict[str, Any]]:
        """Improved extraction using AI instead of pattern matching"""

        print(
            f"[CONTENT EXTRACTION] Using AI-powered extraction for {len(validated_chapters)} chapters"
        )

        # Get chapter titles
        chapter_titles = [ch["title"] for ch in validated_chapters]

        # Use AI to extract content instead of pattern matching
        extracted_chapters = await self._extract_content_with_ai(
            full_text, chapter_titles
        )

        print(
            f"[CONTENT EXTRACTION] AI extracted {len(extracted_chapters)} chapters successfully"
        )

        return extracted_chapters

    async def _extract_content_with_ai(
        self, full_text: str, chapter_titles: List[str]
    ) -> List[Dict]:
        """Use AI to extract chapter content instead of pattern matching"""

        # Split text into manageable chunks for AI processing
        text_chunks = self._split_text_for_ai(full_text, max_chunk_size=15000)

        extracted_chapters = []

        for chapter_title in chapter_titles:
            print(f"[AI EXTRACTION] Processing: {chapter_title}")

            # Find relevant chunks that likely contain this chapter
            relevant_chunks = self._find_relevant_chunks(text_chunks, chapter_title)

            # Use AI to extract the specific chapter content
            chapter_content = await self._ai_extract_chapter_content(
                chunks=relevant_chunks,
                chapter_title=chapter_title,
                context={
                    "book_title": self.extracted_title,
                    "total_chapters": len(chapter_titles),
                },
            )

            if chapter_content and len(chapter_content) > 200:
                extracted_chapters.append(
                    {
                        "title": chapter_title,
                        "content": chapter_content,
                        "summary": f"Content for {chapter_title}",
                        "extraction_method": "ai",
                    }
                )
                print(f"[AI EXTRACTION] ✅ Extracted {len(chapter_content)} chars")
            else:
                print(f"[AI EXTRACTION] ❌ No content found")

        return extracted_chapters

    def _split_text_for_ai(self, text: str, max_chunk_size: int = 15000) -> List[str]:
        """Split text into manageable chunks for AI processing"""
        chunks = []

        # Split by paragraphs first
        paragraphs = text.split("\n\n")
        current_chunk = ""

        for paragraph in paragraphs:
            # If adding this paragraph would exceed the limit
            if len(current_chunk) + len(paragraph) > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Single paragraph is too large, split by sentences
                    sentences = paragraph.split(". ")
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) > max_chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = sentence
                            else:
                                # Single sentence too large, force split
                                chunks.append(sentence[:max_chunk_size])
                        else:
                            current_chunk += sentence + ". "
            else:
                current_chunk += paragraph + "\n\n"

        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        print(f"[AI CHUNKING] Split text into {len(chunks)} chunks")
        return chunks

    def _find_relevant_chunks(
        self, text_chunks: List[str], chapter_title: str
    ) -> List[str]:
        """Find chunks that likely contain the chapter content"""
        relevant_chunks = []

        # Extract key words from chapter title for searching
        title_words = chapter_title.lower().split()
        search_words = [
            word
            for word in title_words
            if len(word) > 3
            and word not in ["chapter", "the", "and", "of", "to", "in", "for"]
        ]

        # Score chunks based on relevance
        chunk_scores = []
        for i, chunk in enumerate(text_chunks):
            chunk_lower = chunk.lower()
            score = 0

            # Score based on title word matches
            for word in search_words:
                if word in chunk_lower:
                    score += chunk_lower.count(word)

            # Bonus for exact chapter title match
            if chapter_title.lower() in chunk_lower:
                score += 10

            # Bonus for chapter number patterns
            chapter_num_match = re.search(r"chapter (\d+)", chapter_title.lower())
            if chapter_num_match:
                chapter_num = chapter_num_match.group(1)
                if (
                    f"chapter {chapter_num}" in chunk_lower
                    or f"\n{chapter_num}\n" in chunk_lower
                ):
                    score += 15

            chunk_scores.append((i, score))

        # Sort by score and take top chunks
        chunk_scores.sort(key=lambda x: x[1], reverse=True)

        # Take top 3 chunks or chunks with score > 0
        for i, score in chunk_scores:
            if score > 0 and len(relevant_chunks) < 3:
                relevant_chunks.append(text_chunks[i])

        # If no relevant chunks found, take first few chunks as fallback
        if not relevant_chunks:
            relevant_chunks = text_chunks[:2]

        print(
            f"[CHUNK SELECTION] Selected {len(relevant_chunks)} chunks for chapter: {chapter_title}"
        )
        return relevant_chunks

    @property
    def extracted_title(self) -> Optional[str]:
        """Get the extracted book title"""
        return getattr(self, "_extracted_title", None)

    @extracted_title.setter
    def extracted_title(self, value: str):
        """Set the extracted book title"""
        self._extracted_title = value

    def _extract_book_title_from_content(self, content: str) -> str:
        """Extract book title from content"""
        lines = content.split("\n")[:20]  # Check first 20 lines

        # Look for title patterns
        for line in lines:
            line = line.strip()
            if len(line) > 10 and len(line) < 100:
                # Check if line looks like a title (starts with capital, has multiple words)
                if (
                    line[0].isupper()
                    and len(line.split()) > 2
                    and not re.match(r"^\d+", line)
                    and "chapter" not in line.lower()
                ):
                    return line

        return "Untitled Book"

    def _validate_ai_extracted_content(self, content: str, chapter_title: str) -> bool:
        """Validate that AI extracted relevant content"""
        if len(content) < 100:
            return False

        # Check if content seems related to the chapter title
        title_words = chapter_title.lower().split()
        content_lower = content.lower()

        # At least one significant word from title should appear in content
        significant_words = [
            w
            for w in title_words
            if len(w) > 3 and w not in ["chapter", "the", "and", "of"]
        ]
        if significant_words:
            word_matches = sum(1 for word in significant_words if word in content_lower)
            if word_matches == 0:
                print(f"[AI VALIDATION] No title words found in content")
                return False

        return True

    def _find_title_occurrences(self, full_text: str, chapter_title: str) -> List[int]:
        """Find all occurrences of the exact chapter title in the text"""
        occurrences = []

        # Clean the title - remove "Chapter N:" prefix if present
        title_parts = chapter_title.split(":", 1)
        clean_title = title_parts[1].strip() if len(title_parts) > 1 else chapter_title

        # Try multiple variations of the title
        title_variations = [
            clean_title,  # Exact title
            clean_title.upper(),  # All caps
            clean_title.lower(),  # All lowercase
            clean_title.title(),  # Title case
        ]

        for title_var in title_variations:
            # Find exact matches
            start = 0
            while True:
                pos = full_text.find(title_var, start)
                if pos == -1:
                    break
                occurrences.append(pos)
                start = pos + 1

        # Remove duplicates and sort
        occurrences = sorted(list(set(occurrences)))
        print(
            f"[CONTENT EXTRACTION] Found {len(occurrences)} title occurrences for: {clean_title}"
        )

        return occurrences

    def _is_actual_chapter_content_by_title(
        self, content: str, chapter_title: str
    ) -> bool:
        """Validate that this is actual chapter content, not TOC or page number"""

        # Extract clean title
        title_parts = chapter_title.split(":", 1)
        clean_title = title_parts[1].strip() if len(title_parts) > 1 else chapter_title

        # Check if the title appears at the beginning of the content
        content_start = content[:200].strip()
        if clean_title.lower() in content_start.lower():
            print(f"[CONTENT VALIDATION] Found title '{clean_title}' at content start")

            # Additional validation: check for substantial content following
            lines = content.split("\n")
            substantial_lines = [line for line in lines if len(line.strip()) > 20]

            if len(substantial_lines) >= 3:  # At least 3 substantial lines
                print(
                    f"[CONTENT VALIDATION] Found {len(substantial_lines)} substantial lines"
                )
                return True

        # Reject if it looks like TOC
        toc_indicators = [
            r"\.{3,}",  # Dots leading to page numbers
            r"\d+\s*$",  # Ends with just a number (page number)
            r"chapter.*?\d+.*?chapter",  # Multiple chapter references
        ]

        for pattern in toc_indicators:
            if re.search(pattern, content[:300], re.IGNORECASE):
                print(f"[CONTENT VALIDATION] TOC indicator found: {pattern}")
                return False

        # Basic content quality check
        word_count = len(content.split())
        has_sentences = bool(re.search(r"[.!?]", content[:500]))

        print(
            f"[CONTENT VALIDATION] Words: {word_count}, Has sentences: {has_sentences}"
        )
        return word_count > 50 and has_sentences

    def _find_chapter_content_end_by_title(
        self,
        full_text: str,
        validated_chapters: List[Dict],
        current_index: int,
        content_start: int,
    ) -> int:
        """Find where current chapter ends by looking for the next chapter title"""

        # If this is the last chapter, return end of document
        if current_index >= len(validated_chapters) - 1:
            return len(full_text)

        # Get the next chapter title
        next_chapter = validated_chapters[current_index + 1]
        next_title_parts = next_chapter["title"].split(":", 1)
        next_clean_title = (
            next_title_parts[1].strip()
            if len(next_title_parts) > 1
            else next_chapter["title"]
        )

        # Search for the next chapter title after current content start
        search_text = full_text[
            content_start + 1000 :
        ]  # Skip first 1000 chars to avoid false matches

        # Try different variations of the next title
        title_variations = [
            next_clean_title,
            next_clean_title.upper(),
            next_clean_title.lower(),
        ]

        for title_var in title_variations:
            pos = search_text.find(title_var)
            if pos != -1:
                # Validate this is actually a chapter start, not just a reference
                potential_end = content_start + 1000 + pos
                preview = full_text[potential_end - 100 : potential_end + 100]

                # Make sure it's not in a TOC (no dots leading to page numbers)
                if not re.search(r"\.{3,}", preview):
                    print(
                        f"[CONTENT EXTRACTION] Found next chapter '{next_clean_title}' at position {potential_end}"
                    )
                    return potential_end

        # Fallback: return a reasonable chunk size
        return min(content_start + 10000, len(full_text))

    def _clean_chapter_content(self, content: str, chapter_title: int) -> str:
        """Remove headers, footers, page numbers, and other artifacts from chapter content"""
        lines = content.split("\n")
        cleaned_lines = []

        # Patterns for lines to skip
        skip_patterns = [
            r"^\s*\d+\s*$",  # Just page numbers
            r"^\s*[ivxlcdm]+\s*$",  # Roman numeral page numbers
            r"^.{0,50}•.{0,50}$",  # Short lines with bullets (often headers)
            r"^\s*\[?\s*\d+\s*\]?\s*$",  # Page numbers in brackets
            # Book title/author in header (usually short repeated lines)
            r"^.{5,40}$",  # Very short lines that might be headers
        ]

        # Track repeated lines (often headers/footers)
        line_counts = {}
        for line in lines:
            stripped = line.strip()
            if stripped and len(stripped) < 60:  # Short lines only
                line_counts[stripped] = line_counts.get(stripped, 0) + 1

        # Lines that appear more than 3 times are likely headers/footers
        repeated_lines = {line for line, count in line_counts.items() if count > 3}

        for line in lines:
            stripped = line.strip()

            # Skip empty lines at the beginning
            if not cleaned_lines and not stripped:
                continue

            # Skip repeated header/footer lines
            if stripped in repeated_lines:
                continue

            # Skip lines matching skip patterns
            skip = False
            for pattern in skip_patterns:
                if re.match(pattern, stripped, re.IGNORECASE):
                    skip = True
                    break

            if not skip:
                cleaned_lines.append(line)

        # Remove excessive blank lines
        result = "\n".join(cleaned_lines)
        result = re.sub(r"\n{4,}", "\n\n\n", result)  # Max 3 newlines

        return result.strip()

    def _find_all_chapter_occurrences(
        self, full_text: str, chapter_num: int, chapter_title: str
    ) -> List[int]:
        """Dynamically find chapter occurrences for any format"""
        occurrences = []

        # Extract clean title without "Chapter N:" prefix
        title_parts = chapter_title.split(":", 1)
        clean_title = title_parts[1].strip() if len(title_parts) > 1 else chapter_title

        # Build dynamic patterns based on common formats
        patterns = []

        # Add patterns for different chapter formats
        # Full format: "Chapter N: Title"
        patterns.append(
            rf"Chapter\s+{chapter_num}\s*[:.\-]?\s*{re.escape(clean_title)}"
        )

        # Number with title
        patterns.append(rf"{chapter_num}\s*[:.\-]\s*{re.escape(clean_title)}")

        # Number on separate line from title
        patterns.append(
            rf"^\s*{chapter_num}\s*\n+\s*{re.escape(clean_title.split()[0])}"
        )

        # Just the chapter number (various formats)
        patterns.extend(
            [
                rf"^\s*Chapter\s+{chapter_num}\b",
                rf"^\s*{chapter_num}\s*$",  # Just number on line
                rf"^\s*{chapter_num}[:.\-]\s",  # Number with punctuation
            ]
        )

        # Roman numerals for early chapters
        roman_map = {
            1: "I",
            2: "II",
            3: "III",
            4: "IV",
            5: "V",
            6: "VI",
            7: "VII",
            8: "VIII",
            9: "IX",
            10: "X",
        }
        if chapter_num in roman_map:
            patterns.append(rf"^\s*(?:Chapter\s+)?{roman_map[chapter_num]}\b")

        # Search with each pattern
        for pattern in patterns:
            try:
                for match in re.finditer(
                    pattern, full_text, re.IGNORECASE | re.MULTILINE
                ):
                    occurrences.append(match.start())
            except re.error:
                continue

        # Remove duplicates and sort
        occurrences = sorted(list(set(occurrences)))
        print(
            f"[CONTENT EXTRACTION] Found {len(occurrences)} occurrences for chapter {chapter_num}"
        )

        return occurrences

    def _is_in_toc_boundaries(
        self, position: int, toc_boundaries: Dict[str, int]
    ) -> bool:
        """Check if position is within TOC boundaries"""
        # Add some buffer to the boundaries
        start = max(0, toc_boundaries["start"] - 100)
        end = toc_boundaries["end"] + 100
        return start <= position <= end

    def _analyze_text_properties(self, file_path: str, chapter_title: str) -> List[int]:
        """
        Analyzes the PDF to find occurrences of the chapter title that are formatted
        as titles (e.g., larger font, centered).
        """
        title_occurrences = []
        try:
            doc = fitz.open(file_path)
            # Extract just the title part (remove "Chapter X: " prefix)
            clean_title = (
                chapter_title.split(": ", 1)[-1].strip()
                if ": " in chapter_title
                else chapter_title
            )

            for page_num, page in enumerate(doc):
                # Get text blocks with formatting information
                if page_num < 5:  # Skip first 5 pages
                    continue
                blocks = page.get_text("dict", flags=11)["blocks"]
                if not blocks:
                    continue

                # Calculate average font size for this page
                font_sizes = []
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                if span["text"].strip():
                                    font_sizes.append(span["size"])

                if not font_sizes:
                    continue

                avg_font_size = sum(font_sizes) / len(font_sizes)
                max_font_size = max(font_sizes)

                # Look for the chapter title in formatted text
                for block in blocks:
                    if "lines" not in block:
                        continue

                    for line in block["lines"]:
                        line_text = "".join(
                            span["text"] for span in line["spans"]
                        ).strip()

                        # Check if this line contains our chapter title
                        if clean_title.lower() in line_text.lower():
                            # Analyze formatting properties
                            line_font_sizes = [
                                span["size"]
                                for span in line["spans"]
                                if span["text"].strip()
                            ]
                            if not line_font_sizes:
                                continue

                            avg_line_font = sum(line_font_sizes) / len(line_font_sizes)

                            # Check if font is significantly larger than average
                            is_large_font = avg_line_font > avg_font_size * 1.2

                            # Check if text is centered (within page margins)
                            line_bbox = fitz.Rect(line["bbox"])
                            page_width = page.rect.width
                            line_center = (line_bbox.x0 + line_bbox.x1) / 2
                            page_center = page_width / 2
                            is_centered = (
                                abs(line_center - page_center) < page_width * 0.25
                            )

                            # Check if it's near the top of the page (likely a chapter title)
                            is_near_top = line_bbox.y0 < page.rect.height * 0.4
                            # Title criteria: large font OR (centered AND near top)
                            if is_large_font or (is_centered and is_near_top):
                                # Calculate global position in the document
                                global_pos = 0
                                for p in range(page_num):
                                    global_pos += len(doc[p].get_text())

                                # Add approximate position within the current page
                                page_text = page.get_text()
                                title_pos_in_page = page_text.lower().find(
                                    clean_title.lower()
                                )
                                if title_pos_in_page != -1:
                                    global_pos += title_pos_in_page
                                    title_occurrences.append(global_pos)
                                    print(
                                        f"[TEXT ANALYSIS] Found formatted title '{clean_title}' at global position {global_pos} (page {page_num + 1})"
                                    )
                                    print(
                                        f"[TEXT ANALYSIS] Properties: large_font={is_large_font}, centered={is_centered}, near_top={is_near_top}"
                                    )

            doc.close()
        except Exception as e:
            print(f"[TEXT ANALYSIS] Error analyzing PDF properties: {e}")

        return sorted(list(set(title_occurrences)))

    def _find_chapter_content_start(
        self, full_text: str, chapter_num: int, toc_boundaries: Dict
    ) -> Optional[int]:
        """Find the actual start of chapter content using multiple strategies"""

        # Strategy 1: Look for chapter number with title formatting (like "1\nIntroduction\nto Angel Magic")
        chapter_start_patterns = [
            rf"\n\s*{chapter_num}\s*\n.*?(?:introduction|angel|magic|source|survival|making|keys|result|fairy|golden|today)",
            rf"CHAPTER\s+{chapter_num}[^\n]*\n(?!\s*\.)",  # CHAPTER X not followed by dots (not TOC)
            rf"Chapter\s+{chapter_num}[^\n]*\n(?!\s*\.)",  # Chapter X not followed by dots
            rf"\n\s*{chapter_num}\s*\n[A-Z][^\.]*\n",  # Number, then title without dots
        ]

        # Search AFTER TOC boundaries to avoid TOC content
        search_start = toc_boundaries.get("end", 0)
        search_text = full_text[search_start:]

        for i, pattern in enumerate(chapter_start_patterns):
            matches = list(
                re.finditer(pattern, search_text, re.IGNORECASE | re.MULTILINE)
            )

            for match in matches:
                potential_start = search_start + match.start()

                # Validate this is not in TOC area
                if potential_start > toc_boundaries.get("end", 0):
                    print(
                        f"[CONTENT EXTRACTION] Found chapter {chapter_num} start using pattern {i} at position {potential_start}"
                    )

                    # Move to actual content start (after chapter heading)
                    content_start = search_start + match.end()
                    return content_start

        # Strategy 2: If specific patterns fail, look for any substantial content after chapter mentions
        fallback_patterns = [
            rf"\b{chapter_num}\b.*?\n.*?\n",  # Any occurrence of chapter number followed by content
        ]

        for pattern in fallback_patterns:
            matches = list(re.finditer(pattern, search_text, re.IGNORECASE))
            for match in matches:
                potential_start = search_start + match.end()
                # Check if this looks like actual content (not TOC)
                preview = full_text[potential_start : potential_start + 200]
                if not re.search(
                    r"\.{3,}|\d+\s*$", preview
                ):  # No TOC dots or ending with page numbers
                    print(
                        f"[CONTENT EXTRACTION] Found chapter {chapter_num} using fallback at position {potential_start}"
                    )
                    return potential_start

        return None

    def _find_chapter_content_end(
        self, full_text: str, chapter_num: int, content_start: int
    ) -> int:
        """Find where current chapter ends"""
        next_chapter_num = chapter_num + 1

        # Look for next chapter start
        next_chapter_patterns = [
            rf"\n\s*{next_chapter_num}\s*\n",
            rf"^\s*{next_chapter_num}\s*$",  # Just number at end of line
            rf"CHAPTER\s+{next_chapter_num}",
            rf"Chapter\s+{next_chapter_num}",
        ]

        search_text = full_text[content_start:]

        for pattern in next_chapter_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE | re.MULTILINE)
            if match:
                # Make sure this isn't in a TOC or reference
                potential_end = content_start + match.start()
                preview = full_text[potential_end - 50 : potential_end + 50]
                if not re.search(r"\.{3,}", preview):  # No TOC dots nearby
                    return potential_end

    def _is_actual_chapter_content(self, content: str, chapter_num: int) -> bool:
        """MUCH LESS STRICT validation - the current one is rejecting everything"""

        # If we see the chapter number at the start, it's probably the real chapter
        if re.search(rf"^\s*{chapter_num}\s*[\n\r]", content[:50], re.MULTILINE):
            print(f"[CONTENT VALIDATION] Found chapter {chapter_num} number at start")
            return True

        # Only reject if it's CLEARLY a TOC
        lines = content[:300].split("\n")[:5]  # First 5 lines only

        # Strong TOC indicators - must have MULTIPLE of these
        strong_toc_indicators = 0
        for line in lines:
            # Page numbers with dots
            if re.search(r"\.{5,}\s*\d+\s*$", line):
                strong_toc_indicators += 1
            # Multiple chapter listings in one line
            elif re.search(r"chapter.*?chapter", line, re.IGNORECASE):
                strong_toc_indicators += 1

        # Only reject if MULTIPLE strong indicators
        if strong_toc_indicators >= 2:
            print(
                f"[CONTENT VALIDATION] Strong TOC indicators found: {strong_toc_indicators}"
            )
            return False

        # Very basic content check - just need SOME text
        word_count = len(content.split())
        has_sentences = bool(re.search(r"[.!?]", content[:500]))

        print(
            f"[CONTENT VALIDATION] Words: {word_count}, Has sentences: {has_sentences}"
        )

        # Accept if there's any reasonable content
        return word_count > 20 or has_sentences

    async def process_uploaded_book_preview(
        self,
        storage_path: Optional[str],
        original_filename: Optional[str],
        text_content: Optional[str],
        book_type: str,
        user_id: str,
        book_id_to_update: str,
        session: AsyncSession,
        progress_book_id: Optional[str] = None,  # For progress tracking
    ) -> Dict[str, Any]:
        """Process upload and return a PREVIEW with proper structure handling"""

        # Helper function to emit progress updates
        async def emit_progress(
            percent: int,
            message: str,
            stage: str = "",
            completed_step: str = None,
            details: str = "",
            total_pages: int = 0,
            current_page: int = 0,
            total_chapters: int = 0,
            current_chapter: int = 0,
        ):
            if progress_book_id:
                from app.core.services.progress import progress_store

                await progress_store.update(
                    progress_book_id,
                    percent=percent,
                    message=message,
                    stage=stage,
                    details=details,
                    completed_step=completed_step,
                    total_pages=total_pages,
                    current_page=current_page,
                    total_chapters=total_chapters,
                    current_chapter=current_chapter,
                )

        # Add comprehensive null safety at the start
        safe_filename = original_filename or "untitled_book"
        if not isinstance(safe_filename, str):
            safe_filename = str(safe_filename) if safe_filename else "untitled_book"

        safe_book_type = book_type or "learning"
        if not isinstance(safe_book_type, str):
            safe_book_type = str(safe_book_type) if safe_book_type else "learning"

        # 1) Extract content (pdf/docx/txt or provided text)
        await emit_progress(10, "Extracting content from file...", "extract")

        if text_content:
            content = text_content
            cover_image_url = None
            author_name = None
        elif storage_path and safe_filename:
            from app.core.services.storage import storage_service

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=safe_filename
            ) as temp_file:
                file_content = await storage_service.download(storage_path)
                if file_content is None:
                    raise ValueError(f"File not found in storage: {storage_path}")
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            extracted = await self.process_book_file(
                temp_file_path, safe_filename, user_id
            )
            os.unlink(temp_file_path)
            content = extracted.get("text", "")
            cover_image_url = extracted.get("cover_image_url")
            author_name = extracted.get("author")
        else:
            raise ValueError("No content provided")

        await emit_progress(
            15,
            "Scanning for Table of Contents...",
            "toc",
            completed_step="✅ File content extracted",
        )

        # 2) Extract chapters with null safety - pass progress callback
        extracted_data = await self.extract_chapters_with_new_flow(
            content,
            safe_book_type,
            safe_filename,
            storage_path,
            progress_callback=emit_progress if progress_book_id else None,
        )

        print(f"[PREVIEW] ✅ Extracted data type: {type(extracted_data)}")
        print(
            f"[PREVIEW] ✅ Extracted data length: {len(extracted_data) if extracted_data else 0}"
        )

        # ✅ FIX: Handle the two different return formats from extract_chapters_with_new_flow
        if (
            extracted_data
            and isinstance(extracted_data, list)
            and len(extracted_data) > 0
        ):
            # Check if first item is a section (has 'chapters' key) or a chapter (has 'content' key)
            first_item = extracted_data[0]

            if isinstance(first_item, dict) and "chapters" in first_item:
                # This is a list of sections, each containing chapters
                print(
                    f"[PREVIEW] Detected hierarchical structure with {len(extracted_data)} sections"
                )

                sections_list = extracted_data
                has_sections = True

                # Extract all individual chapters from all sections
                all_chapters = []
                for section in sections_list:
                    section_chapters = section.get("chapters", [])
                    all_chapters.extend(section_chapters)
                    print(
                        f"[PREVIEW] Section '{section.get('title')}' contributes {len(section_chapters)} chapters"
                    )

                print(
                    f"[PREVIEW] Total chapters across all sections: {len(all_chapters)}"
                )

            elif isinstance(first_item, dict) and "content" in first_item:
                # This is a list of individual chapters (flat structure)
                print(
                    f"[PREVIEW] Detected flat structure with {len(extracted_data)} chapters"
                )

                all_chapters = extracted_data
                sections_list = []
                has_sections = False

            else:
                print(
                    f"[PREVIEW] Unknown data structure: {first_item.keys() if isinstance(first_item, dict) else type(first_item)}"
                )
                raise ValueError("Unknown extracted data structure")
        else:
            print("[PREVIEW] No data extracted")
            all_chapters = []
            sections_list = []
            has_sections = False

        print(
            f"[PREVIEW] Final analysis: has_sections={has_sections}, chapters_count={len(all_chapters)}, sections_count={len(sections_list)}"
        )

        # 3) Build the complete structure based on detection
        if has_sections and sections_list:
            print(
                f"[PREVIEW] Building hierarchical structure from {len(sections_list)} sections"
            )

            # Detect structure type
            try:
                detected_structure = self.structure_detector.detect_structure_type(
                    sections_list
                )
            except Exception as e:
                print(f"[STRUCTURE DETECTION] Error: {e}, using hierarchical")
                detected_structure = "hierarchical"

            # Build complete structure object
            structure_data = {
                "id": book_id_to_update,
                "title": safe_filename,
                "structure_type": detected_structure,
                "has_sections": True,
                "sections": sections_list,
                "chapters": [],  # Empty for hierarchical
                "structure_metadata": self.structure_detector.get_structure_metadata(
                    detected_structure
                ),
            }

            total_chapters = len(all_chapters)
            print(
                f"[PREVIEW] ✅ Built hierarchical structure: {len(sections_list)} sections with {total_chapters} total chapters"
            )

            # ✅ FIX: Return sections for hierarchical books
            return_data = {
                "status": "READY",
                "chapters": sections_list,  # Return sections, each with their chapters
                "total_chapters": total_chapters,
                "author_name": author_name,
                "cover_image_url": cover_image_url,
                "structure_data": structure_data,
                "has_sections": True,  # ✅ CRITICAL FIX: Make sure this is set
                "structure_type": detected_structure,
            }

        else:
            print(
                f"[PREVIEW] Building flat structure from {len(all_chapters)} chapters"
            )

            # Format individual chapters for flat structure
            formatted_chapters = []
            for i, ch in enumerate(all_chapters):
                if not isinstance(ch, dict):
                    continue

                chapter_data = {
                    "id": f"chapter_{i + 1}",
                    "book_id": book_id_to_update,
                    "chapter_number": ch.get("chapter_number", ch.get("number", i + 1)),
                    "title": ch.get("title", f"Chapter {i + 1}"),
                    "content": ch.get("content", ""),
                    "summary": ch.get("summary", ""),
                    "order_index": i,
                }
                formatted_chapters.append(chapter_data)

            structure_data = {
                "id": book_id_to_update,
                "title": safe_filename,
                "structure_type": "flat",
                "has_sections": False,
                "sections": [],
                "chapters": formatted_chapters,
                "structure_metadata": self.structure_detector.get_structure_metadata(
                    "flat"
                ),
            }

            print(
                f"[PREVIEW] ✅ Built flat structure: {len(formatted_chapters)} chapters"
            )

            # For flat books, return chapters directly
            return_data = {
                "status": "READY",
                "chapters": formatted_chapters,
                "total_chapters": len(formatted_chapters),
                "author_name": author_name,
                "cover_image_url": cover_image_url,
                "structure_data": structure_data,
                "has_sections": False,
                "structure_type": "flat",
            }

        # 4) Update book record with complete structure information
        # 4) Update book record with complete structure information
        try:
            from app.books.models import Book
            from sqlmodel import select
            import uuid

            stmt = select(Book).where(Book.id == uuid.UUID(book_id_to_update))
            result = await session.exec(stmt)
            book = result.first()

            if book:
                book.content = self._clean_text_content(content)
                book.title = safe_filename
                if cover_image_url:
                    book.cover_image_url = cover_image_url
                if author_name:
                    book.author_name = author_name
                book.status = "READY"
                book.structure_type = structure_data["structure_type"]
                book.has_sections = structure_data["has_sections"]
                book.total_chapters = return_data["total_chapters"]

                session.add(book)
                await session.commit()
                await session.refresh(book)
                print(f"[PREVIEW] Successfully updated book record {book_id_to_update}")
            else:
                print(f"[PREVIEW] Book {book_id_to_update} not found for update")

        except Exception as e:
            print(f"[PREVIEW] Failed to update book record: {e}")

        print(f"[PREVIEW] Final return data:")
        print(f"[PREVIEW] - status: {return_data['status']}")
        print(f"[PREVIEW] - has_sections: {return_data['has_sections']}")
        print(f"[PREVIEW] - structure_type: {return_data['structure_type']}")
        print(f"[PREVIEW] - chapters type: {type(return_data['chapters'])}")
        print(f"[PREVIEW] - chapters count: {len(return_data['chapters'])}")
        print(
            f"[PREVIEW] - structure_data present: {bool(return_data.get('structure_data'))}"
        )

        return return_data

    async def confirm_book_structure(
        self,
        book_id: str,
        confirmed_chapters: List[Dict[str, Any]],
        user_id: str,
        session: AsyncSession,
    ):
        """Persist user-confirmed structure and create embeddings. Yields progress updates."""
        yield f"Starting to save structure for book {book_id}"
        yield f"Received {len(confirmed_chapters)} confirmed chapters"

        try:
            from app.books.models import (
                Book,
                Chapter,
                ChapterEmbedding,
                BookEmbedding,
                Section,
            )
            from sqlmodel import select, delete
            import uuid

            book_uuid = uuid.UUID(book_id)

            # ✅ FIX: Clean old data in the CORRECT order to avoid foreign key violations
            yield "Cleaning existing data..."

            # 1. Delete chapter embeddings first (they reference chapters)
            try:
                stmt = delete(ChapterEmbedding).where(
                    ChapterEmbedding.book_id == book_uuid
                )
                await session.exec(stmt)
                yield "Deleted chapter embeddings"
            except Exception as e:
                print(
                    f"[STRUCTURE SAVE] Warning: Failed to delete chapter embeddings: {e}"
                )

            # 2. Delete book embeddings (they reference the book)
            try:
                stmt = delete(BookEmbedding).where(BookEmbedding.book_id == book_uuid)
                await session.exec(stmt)
                yield "Deleted book embeddings"
            except Exception as e:
                print(
                    f"[STRUCTURE SAVE] Warning: Failed to delete book embeddings: {e}"
                )

            # 3. Delete chapters (they reference sections and book)
            try:
                stmt = delete(Chapter).where(Chapter.book_id == book_uuid)
                await session.exec(stmt)
                yield "Deleted chapters"
            except Exception as e:
                print(f"[STRUCTURE SAVE] Warning: Failed to delete chapters: {e}")

            # 4. Delete sections (they reference book)
            try:
                stmt = delete(Section).where(Section.book_id == book_uuid)
                await session.exec(stmt)
                yield "Deleted sections"
            except Exception as e:
                print(f"[STRUCTURE SAVE] Warning: Failed to delete sections: {e}")

            # Build sections (if present)
            section_id_map: Dict[str, uuid.UUID] = {}
            order = 0

            # We need to commit deletions before insertions?
            # SQLAlchemy handles transaction, so it should be fine within same transaction.

            for ch in confirmed_chapters:
                order += 1
                section_id = None
                if ch.get("section_title"):
                    section_key = f"{ch.get('section_title','')}|{ch.get('section_type','')}|{ch.get('section_number','')}"

                    if section_key not in section_id_map:
                        # Create new section
                        section = Section(
                            book_id=book_uuid,
                            title=ch["section_title"],
                            section_type=ch.get("section_type") or "",
                            section_number=ch.get("section_number") or "",
                            order_index=ch.get("section_order", order),
                        )
                        session.add(section)
                        await session.flush()  # Flush to get ID
                        await session.refresh(section)
                        section_id = section.id
                        section_id_map[section_key] = section_id
                    else:
                        section_id = section_id_map[section_key]

                # Create chapter
                chapter = Chapter(
                    book_id=book_uuid,
                    section_id=section_id,
                    chapter_number=order,
                    title=ch.get("title", f"Chapter {order}"),
                    content=self._clean_text_content(ch.get("content", "")),
                    summary=self._clean_text_content(ch.get("summary", "")),
                    order_index=order,
                )
                session.add(chapter)
                await session.flush()
                await session.refresh(chapter)
                yield f"Created chapter: {chapter.title}"

                # Create embeddings (best-effort)
                try:
                    from app.core.services.embeddings import EmbeddingsService

                    es = EmbeddingsService(session)
                    await es.create_chapter_embeddings(
                        chapter.id, ch.get("content", "")
                    )
                    yield f"Created embeddings for chapter {chapter.id}"
                except Exception as e:
                    print(f"[EMBEDDINGS] Failed for chapter {chapter.id}: {e}")

            # Update book metadata
            yield "Updating book metadata..."
            try:
                stmt = select(Book).where(Book.id == book_uuid)
                result = await session.exec(stmt)
                book = result.first()

                if book:
                    book.has_sections = bool(section_id_map)
                    book.structure_type = "hierarchical" if section_id_map else "flat"
                    book.total_chapters = order
                    book.status = "READY"
                    book.progress = 100
                    book.progress_message = "Book structure saved successfully"

                    session.add(book)
                    await session.commit()

                print(
                    f"[STRUCTURE SAVE] ✅ Successfully saved structure for book {book_id}"
                )
                yield "Structure saved successfully"
                yield f"- {len(section_id_map)} sections created"
                yield f"- {order} chapters created"
            except Exception as e:
                print(f"[STRUCTURE SAVE] Failed to update book metadata: {e}")

        except Exception as e:
            print(f"[STRUCTURE SAVE] ❌ Error saving structure: {e}")
            yield f"Error saving structure: {str(e)}"
            print(f"[STRUCTURE SAVE] Full error: {traceback.format_exc()}")
            raise e

    async def _compare_with_toc_chapter(
        self, chapter_title: str, extracted_content: str, toc_reference: Dict
    ) -> Dict:
        """Compare extracted content with TOC chapter for validation"""

        if not toc_reference:
            return {
                "is_valid": True,
                "confidence": 0.7,
                "reason": "No TOC reference available",
            }

        try:
            # Get first 500 characters of both contents for comparison
            extracted_preview = extracted_content[:500]
            toc_preview = toc_reference.get("content", "")[:500]

            prompt = f"""
            Compare these two versions of the same chapter to validate content extraction:
            
            Chapter Title: {chapter_title}
            
            Version 1 (Extracted from book content):
            {extracted_preview}
            
            Version 2 (From TOC/page extraction):
            {toc_preview}
            
            Return JSON:
            {{
                "is_valid": true/false,
                "confidence": 0.0-1.0,
                "reason": "explanation of comparison",
                "similarity": 0.0-1.0
            }}
            
            Validate if Version 1 looks like proper chapter content and is reasonably similar to Version 2.
            """

            response = await self.ai_service.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1,
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"[TOC COMPARISON] Comparison failed: {e}")
            return {
                "is_valid": True,
                "confidence": 0.5,
                "reason": "Comparison failed, defaulting to valid",
            }

    def _parse_toc_text(self, toc_text: str, doc) -> List[Dict[str, Any]]:
        """Parse TOC text to extract chapter information"""
        chapters = []
        lines = toc_text.split("\n")

        # More specific patterns that match your book's ACTUAL TOC format
        toc_patterns = [
            r"^CHAPTER\s+(\d+)\.\s+(.+?)\s+(\d+)$",  # "CHAPTER 1. Introduction to Angel Magic 1"
            r"^Chapter\s+(\d+)[\.\s]+(.+?)\s+(\d+)$",  # "Chapter 1. Title 1"
            r"^(\d+)\.\s+(.+?)\s+(\d+)$",  # "1. Title 1"
        ]

        print(f"[TOC PARSING] Analyzing {len(lines)} TOC lines...")

        for line_num, line in enumerate(lines):
            line = line.strip()

            # Skip obvious non-chapter lines
            if (
                len(line) < 15
                or line.startswith("Page")
                or line.lower().startswith("list of")
                or line.lower().startswith("preface")
                or "illustrations" in line.lower()
                or "figures" in line.lower()
            ):
                continue

            print(f"[TOC PARSING] Processing line: '{line}'")

            for pattern_idx, pattern in enumerate(toc_patterns):
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    print(f"[TOC PARSING] Pattern {pattern_idx} matched: {groups}")

                    if len(groups) == 3:  # Chapter number, title, page
                        chapter_num, title, page_str = groups

                        # Additional validation: make sure title doesn't contain illustration keywords
                        if (
                            "illustration" in title.lower()
                            or "figure" in title.lower()
                            or "by gustav" in title.lower()
                            or "by singleton" in title.lower()
                        ):
                            print(f"[TOC PARSING] Skipping illustration entry: {title}")
                            continue

                        try:
                            page_num = int(page_str)
                            if 1 <= page_num <= len(doc):  # Valid page range
                                chapters.append(
                                    {
                                        "number": chapter_num,
                                        "title": f"Chapter {chapter_num}: {title.strip()}",
                                        "page": page_num,
                                        "raw_title": title.strip(),
                                    }
                                )
                                print(
                                    f"[TOC PARSING] Added chapter: {chapter_num} - {title.strip()} (page {page_num})"
                                )
                        except ValueError:
                            print(f"[TOC PARSING] Invalid page number: {page_str}")
                            continue
                    break

        # Only proceed if we found chapters with reasonable numbering
        if chapters and len(chapters) >= 3:
            # Validate chapter sequence
            chapter_numbers = [int(ch["number"]) for ch in chapters]
            if (
                min(chapter_numbers) == 1 and max(chapter_numbers) <= 20
            ):  # Reasonable chapter range
                print(f"[TOC PARSING] Found {len(chapters)} valid chapters in TOC")
                return self._extract_chapter_content_from_toc(chapters, doc)
            else:
                print(f"[TOC PARSING] Invalid chapter numbering: {chapter_numbers}")

        print("[TOC PARSING] No valid chapter structure found")
        return []

    def _extract_chapter_content_from_toc(
        self, chapters: List[Dict], doc
    ) -> List[Dict[str, Any]]:
        """Extract content for TOC chapters with better validation"""
        final_chapters = []

        for i, chapter in enumerate(chapters):
            start_page = chapter["page"] - 1  # Convert to 0-based index
            end_page = len(doc) - 1

            # Find end page (start of next chapter)
            if i + 1 < len(chapters):
                end_page = chapters[i + 1]["page"] - 2  # Stop before next chapter

            print(
                f"[CONTENT EXTRACTION] Chapter {chapter['number']}: pages {start_page + 1} to {end_page + 1}"
            )

            # Extract content from the actual chapter pages
            content = ""

            for page_idx in range(start_page, min(end_page + 1, len(doc))):
                page_text = doc[page_idx].get_text()
                content += page_text + "\n"

            # Clean content and validate
            content = content.strip()

            # Only add chapters with substantial content
            if len(content) > 1000:  # Minimum content threshold
                final_chapters.append(
                    {
                        "title": chapter["title"],
                        "content": content,
                        "summary": f"Chapter {chapter['number']}: {chapter['raw_title']}",
                        "chapter_number": int(chapter["number"]),
                    }
                )
                print(
                    f"[CONTENT EXTRACTION] Successfully extracted {len(content)} characters for: {chapter['title']}"
                )
            else:
                print(
                    f"[CONTENT EXTRACTION] Skipped chapter with insufficient content: {chapter['title']} ({len(content)} chars)"
                )

        print(
            f"[TOC EXTRACTION] Final result: {len(final_chapters)} chapters with content"
        )
        return final_chapters

    def parse_book_structure(self, content: str) -> Dict[str, Any]:
        """Parse book structure and separate front matter from chapters"""
        lines = content.split("\n")

        # Define patterns for different book sections
        front_matter_patterns = [
            r"^Contents$",
            r"^Table of Contents$",
            r"^Preface$",
            r"^Acknowledgments?$",
            r"^Introduction$",
            r"^Foreword$",
            r"^Copyright",
            r"^Library of Congress",
            r"^ISBN",
            r"^First Edition",
            r"^Cover Design",
            r"^Book Design",
            r"^List of Illustrations",
            r"^List of Figures",
        ]

        chapter_patterns = [r"^CHAPTER\s+\d+\.?\s*", r"^Chapter\s+\d+\.?\s*"]

        sections = {"front_matter": [], "chapters": [], "back_matter": []}

        current_section = "front_matter"
        current_content = []

        for line in lines:
            line_stripped = line.strip()

            # Check if this is a chapter header
            is_chapter = any(
                re.match(pattern, line_stripped, re.IGNORECASE)
                for pattern in chapter_patterns
            )

            # Check if this is front matter
            is_front_matter = any(
                re.match(pattern, line_stripped, re.IGNORECASE)
                for pattern in front_matter_patterns
            )

            if is_chapter:
                # Save current content and switch to chapters
                if current_content:
                    sections[current_section].append("\n".join(current_content))
                current_section = "chapters"
                current_content = [line]
            elif is_front_matter and current_section == "front_matter":
                # Continue in front matter
                current_content.append(line)
            else:
                current_content.append(line)

        # Save the last section
        if current_content:
            sections[current_section].append("\n".join(current_content))

        return sections

    def extract_chapters_with_structure(
        self, content: str, book_type: str
    ) -> List[Dict[str, Any]]:
        """Extract chapters with proper book structure handling"""
        # First parse the book structure
        structure = self.parse_book_structure(content)

        # Extract chapters from the chapters section
        if structure["chapters"]:
            chapter_content = "\n".join(structure["chapters"])
            return self.extract_chapters(chapter_content, book_type)
        else:
            # Fallback to original method if no structure found
            return self.extract_chapters(content, book_type)

    async def validate_chapters_with_ai(
        self, chapters: List[Dict[str, Any]], book_content: str, book_type: str
    ) -> List[Dict[str, Any]]:
        """Validate chapters using AI, but limit prompt size to avoid context_length_exceeded errors."""
        # Reduce chapter content for prompt
        reduced_chapters = [
            {
                "title": ch.get("title", ""),
                "content_preview": (
                    ch.get("content", "")[:500]
                    + ("..." if len(ch.get("content", "")) > 500 else "")
                ),
            }
            for ch in chapters
        ]
        # Use reduced_chapters in the prompt
        validation_prompt = f"""
You are an expert book editor. Here are the extracted chapters for a {book_type} book. For each chapter, only a preview of the content is shown. Please check if the chapter titles and structure make sense. Suggest improvements if needed.

Chapters:
{reduced_chapters}
"""

        try:
            if not self.ai_service.client:
                print("AI service not available, skipping validation")
                return chapters

            response = await self.ai_service.client.chat.completions.create(
                model="gpt-3.5-turbo-1106",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert book editor and content validator.",
                    },
                    {
                        "role": "user",
                        "content": f"{validation_prompt}\n\nPlease respond in JSON format.",
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            result = json.loads(response.choices[0].message.content)

            if "validated_chapters" in result and result["validated_chapters"]:
                print(f"AI validation found {len(result.get('issues', []))} issues")
                return result["validated_chapters"]
            else:
                print("AI validation returned no corrections, using original chapters")
                return chapters

        except Exception as e:
            print(f"AI validation failed: {e}")
            return chapters

    def _clean_text_content(self, content: str) -> str:
        """Clean and sanitize text content"""
        if not content:
            return ""

        try:
            # Remove null bytes and other problematic characters
            cleaned = content.replace("\x00", "")

            # Remove excessive whitespace while preserving paragraph breaks
            lines = cleaned.split("\n")
            cleaned_lines = []

            for line in lines:
                # Strip whitespace from each line
                stripped_line = line.strip()
                if stripped_line:  # Keep non-empty lines
                    cleaned_lines.append(stripped_line)
                elif (
                    cleaned_lines and cleaned_lines[-1]
                ):  # Add single empty line for paragraph breaks
                    cleaned_lines.append("")

            # Join lines back together
            result = "\n".join(cleaned_lines)

            # Remove excessive consecutive newlines (more than 2)
            import re

            result = re.sub(r"\n{3,}", "\n\n", result)

            # Ensure the content doesn't exceed reasonable limits
            if len(result) > 50000:  # Limit to ~50k characters per chapter
                result = result[:50000] + "... [Content truncated]"

            return result.strip()

        except Exception as e:
            print(f"Error cleaning text content: {e}")
            # Return original content if cleaning fails
            return str(content) if content else ""

    async def extract_chapters_with_new_flow(
        self,
        content: str,
        book_type: str,
        original_filename: str,
        storage_path: str,
        progress_callback=None,  # Optional progress callback
    ) -> List[Dict[str, Any]]:
        """Enhanced chapter extraction: TOC first, then fallback with null safety"""
        # FIX: Add comprehensive null safety at the start
        safe_filename = original_filename or "unknown_file.txt"
        if not isinstance(safe_filename, str):
            safe_filename = str(safe_filename) if safe_filename else "unknown_file.txt"

        print(f"[CHAPTER EXTRACTION] Starting extraction for {safe_filename}")
        print(f"[CHAPTER EXTRACTION] Storage path: {storage_path or 'None'}")
        print(f"[CHAPTER EXTRACTION] Storage path type: {type(storage_path)}")

        # Step 1: Try EPUB-specific extraction for EPUB files
        if (
            safe_filename.lower().endswith(".epub")
            and storage_path
            and isinstance(storage_path, str)
        ):

            print("[EPUB EXTRACTION] Attempting EPUB chapter extraction...")
            if progress_callback:
                await progress_callback(20, "Processing EPUB file...", "epub")
            try:
                from app.core.services.storage import storage_service

                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".epub"
                ) as temp_file:
                    file_content = await storage_service.download(storage_path)
                    if file_content is None:
                        raise ValueError(f"File not found in storage: {storage_path}")
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name

                epub_chapters = self.extract_epub_chapters(temp_file_path)

                # FIX: Ensure epub_chapters is a valid list
                if not isinstance(epub_chapters, list):
                    epub_chapters = []

                os.unlink(temp_file_path)
                print(f"[EPUB EXTRACTION] Cleaned up temporary file: {temp_file_path}")

                if len(epub_chapters) > 0:
                    print(
                        f"[EPUB EXTRACTION] SUCCESS: Found {len(epub_chapters)} chapters from EPUB structure"
                    )
                    if progress_callback:
                        await progress_callback(
                            90,
                            f"Found {len(epub_chapters)} chapters",
                            "complete",
                            completed_step=f"✅ Extracted {len(epub_chapters)} chapters from EPUB",
                            total_chapters=len(epub_chapters),
                        )
                    return epub_chapters  # Return the chapters directly
                else:
                    print(
                        "[EPUB EXTRACTION] No chapters found in EPUB structure, falling back to text parsing"
                    )

            except Exception as e:
                print(f"[EPUB EXTRACTION] Failed: {e}")
                print(f"[EPUB EXTRACTION] Full error: {traceback.format_exc()}")
                # Clean up temp file even if there's an error
                if "temp_file_path" in locals():
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass

        # Step 2: Try TOC extraction for PDFs
        toc_chapters = []
        if (
            safe_filename.lower().endswith(".pdf")
            and storage_path
            and isinstance(storage_path, str)
        ):

            print("[TOC EXTRACTION] Attempting PDF TOC extraction...")
            if progress_callback:
                await progress_callback(20, "Downloading PDF for analysis...", "toc")
            try:
                from app.core.services.storage import storage_service

                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=safe_filename
                ) as temp_file:
                    file_content = await storage_service.download(storage_path)
                    if file_content is None:
                        raise ValueError(f"File not found in storage: {storage_path}")
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name

                if progress_callback:
                    await progress_callback(
                        25,
                        "Scanning PDF for Table of Contents...",
                        "toc",
                        completed_step="✅ PDF downloaded for analysis",
                    )

                toc_chapters = await self.extract_chapters_from_pdf_with_toc(
                    temp_file_path, progress_callback=progress_callback
                )

                # FIX: Ensure toc_chapters is a valid list
                if not isinstance(toc_chapters, list):
                    toc_chapters = []

                os.unlink(temp_file_path)
                print(f"[TOC EXTRACTION] Cleaned up temporary file: {temp_file_path}")

            except Exception as e:
                print(f"[TOC EXTRACTION] Failed: {e}")
                print(f"[TOC EXTRACTION] Full error: {traceback.format_exc()}")
                # Clean up temp file even if there's an error
                if "temp_file_path" in locals():
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass

        # FIX: Use TOC chapters if we found ANY reasonable number (lowered threshold)
        if len(toc_chapters) >= 3:  # Reduced from >= 2
            print(f"[TOC EXTRACTION] SUCCESS: Using {len(toc_chapters)} TOC chapters")

            # Check if we have sectioned content
            has_sections = any(ch.get("section_title") for ch in toc_chapters)

            if has_sections:
                # ✅ FIX: Return the organized sections structure
                print(
                    "[TOC EXTRACTION] Organizing chapters into sections for hierarchical structure"
                )
                organized_sections = self._organize_chapters_into_sections(toc_chapters)
                print(
                    f"[TOC EXTRACTION] Organized into {len(organized_sections)} sections"
                )
                return organized_sections  # Return sections list
            else:
                # Return as flat structure - list of chapters
                print("[TOC EXTRACTION] Returning as flat chapter structure")
                return toc_chapters  # Return chapters list
        else:
            print(
                f"[TOC EXTRACTION] Found {len(toc_chapters)} chapters, insufficient for TOC method"
            )

        # Step 2: Fallback to structure detection
        print("[STRUCTURE DETECTION] TOC failed, using structure detection...")
        structure_result = self.structure_detector.detect_structure(content)

        # Convert the detect_structure result to the format expected by the rest of the method
        if structure_result["has_sections"]:
            # Convert sections to the format expected by _extract_hierarchical_chapters
            converted_structure = {
                "has_sections": True,
                "sections": structure_result["sections"],
                "structure_type": structure_result["structure_type"],
            }
            extracted_chapters = await self._extract_hierarchical_chapters(
                converted_structure, book_type, content
            )
        else:
            # Use the flat chapters from detect_structure
            extracted_chapters = []
            for i, chapter in enumerate(structure_result["chapters"]):
                chapter_data = {
                    "title": chapter["title"],
                    "content": chapter["content"],
                    "summary": chapter.get("summary", ""),
                    "chapter_number": chapter.get("number", i + 1),
                }
                extracted_chapters.append(chapter_data)

        # Step 3: Filter if too many chapters found
        if len(extracted_chapters) > 20:
            final_chapters = await self._ai_filter_real_chapters(
                extracted_chapters, book_type, content
            )
        else:
            final_chapters = extracted_chapters

        print(f"[CHAPTER EXTRACTION] FINAL: {len(final_chapters)} chapters extracted")
        return final_chapters

    def _organize_chapters_into_sections(
        self, chapters: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Organize chapters with sections into a hierarchical structure"""
        print("[SECTION ORGANIZATION] Organizing chapters into sections...")

        sections_map = {}

        for chapter in chapters:
            section_title = chapter.get("section_title", "Main Content")
            section_type = chapter.get("section_type", "section")
            section_number = chapter.get("section_number", "")

            # Create a unique key for the section
            section_key = f"{section_title}|{section_type}|{section_number}"
            print(
                f"[SECTION ORGANIZATION] Created {section_title}|{section_type}|{section_number} section details"
            )

            if section_key not in sections_map:
                sections_map[section_key] = {
                    "id": f"section_{len(sections_map) + 1}",
                    "book_id": "",  # Will be set when saving
                    "section_number": section_number,
                    "section_type": section_type,
                    "title": section_title,
                    "order_index": len(sections_map),
                    "chapters": [],
                }

            # Add chapter to section
            chapter_data = {
                "id": f"chapter_{len(sections_map[section_key]['chapters']) + 1}",
                "book_id": "",
                "section_id": sections_map[section_key]["id"],
                "chapter_number": chapter.get("number", 1),
                "title": chapter["title"],
                "content": chapter.get("content", ""),
                "summary": chapter.get("summary", ""),
                "order_index": len(sections_map[section_key]["chapters"]),
            }

            sections_map[section_key]["chapters"].append(chapter_data)

        sections_list = list(sections_map.values())

        print(f"[SECTION ORGANIZATION] Created {len(sections_list)} sections")
        for section in sections_list:
            print(
                f"[SECTION ORGANIZATION] Section '{section['title']}': {len(section['chapters'])} chapters"
            )

        return sections_list

    def _validate_chapters_against_toc(
        self, extracted_chapters: List[Dict], toc_chapters: List[Dict]
    ) -> List[Dict]:
        """
        Validate extracted chapters against TOC and remove duplicates
        """
        print("[TOC VALIDATION] Starting chapter validation against TOC...")

        # Create a set of normalized TOC chapter titles
        toc_titles = set()
        for toc_chapter in toc_chapters:
            normalized_title = self._normalize_chapter_title(toc_chapter["title"])
            toc_titles.add(normalized_title)
            print(f"[TOC VALIDATION] TOC chapter: {normalized_title}")

        # Filter extracted chapters to only include those that match TOC
        validated_chapters = []
        seen_titles = set()

        for chapter in extracted_chapters:
            normalized_title = self._normalize_chapter_title(chapter["title"])

            # Skip if we've already seen this title (removes duplicates)
            if normalized_title in seen_titles:
                print(f"[TOC VALIDATION] Skipping duplicate: {normalized_title}")
                continue

            # Check if this chapter exists in TOC
            if normalized_title in toc_titles:
                # Find the corresponding TOC chapter for additional info
                toc_match = None
                for toc_chapter in toc_chapters:
                    if (
                        self._normalize_chapter_title(toc_chapter["title"])
                        == normalized_title
                    ):
                        toc_match = toc_chapter
                        break

                # Use TOC content if extracted content is too short
                if toc_match and len(chapter["content"].strip()) < 500:
                    chapter["content"] = toc_match["content"]
                    print(f"[TOC VALIDATION] Used TOC content for: {normalized_title}")

                validated_chapters.append(chapter)
                seen_titles.add(normalized_title)
                print(f"[TOC VALIDATION] Validated chapter: {normalized_title}")
            else:
                print(f"[TOC VALIDATION] Rejected (not in TOC): {normalized_title}")

        return validated_chapters

    def _normalize_chapter_title(self, title: str) -> str:
        """
        Normalize chapter titles for comparison
        """
        if not title:
            return ""

        # Clean the title
        title = title.strip().upper()

        # Remove common prefixes
        title = re.sub(r"^CHAPTER\s+", "", title)

        # Normalize Roman numerals to Arabic
        roman_pattern = r"^([IVX]+)[\.\s]*"
        match = re.match(roman_pattern, title)
        if match:
            roman = match.group(1)
            arabic = self._roman_to_arabic(roman)
            title = re.sub(roman_pattern, f"{arabic}. ", title)

        # Remove extra whitespace and punctuation
        title = re.sub(r"[\.\s]+", " ", title).strip()

        return title

    def _roman_to_arabic(self, roman: str) -> int:
        """Convert Roman numerals to Arabic numbers"""
        roman_values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        total = 0
        prev_value = 0

        for char in reversed(roman.upper()):
            value = roman_values.get(char, 0)
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value

        return total

    async def _extract_hierarchical_chapters(
        self, structure: Dict[str, Any], book_type: str, book_content: str
    ) -> List[Dict[str, Any]]:
        """Extract chapters from hierarchical structure"""
        all_chapters = []
        chapter_counter = 1

        # Add null check for structure
        if not structure or not structure.get("sections"):
            print("[HIERARCHICAL EXTRACTION] No sections found in structure")
            return []

        for section_index, section in enumerate(structure["sections"]):
            section_type = section.get("type", "section")  # Add fallback
            section_title = section.get(
                "title", f"Section {section_index + 1}"
            )  # Add fallback

            print(
                f"[HIERARCHICAL EXTRACTION] Processing {section_type}: {section_title}"
            )

            # If section has chapters within it, extract them
            if section.get("chapters"):
                for chapter in section["chapters"]:
                    chapter_data = {
                        "title": chapter.get(
                            "title", f"Chapter {chapter_counter}"
                        ),  # Add fallback
                        "content": chapter.get("content", ""),
                        "summary": chapter.get(
                            "summary", f"Chapter from {section_title}"
                        ),  # Use existing or create
                        "section_title": section_title,
                        "section_type": section_type,
                        "section_number": section.get(
                            "number", str(section_index + 1)
                        ),  # Add fallback
                        "chapter_number": chapter_counter,
                    }
                    all_chapters.append(chapter_data)
                    chapter_counter += 1
            else:
                # Treat the entire section as a chapter (like tablets)
                chapter_data = {
                    "title": section_title,
                    "content": section.get("content", ""),
                    "summary": f"{section_type.title()} content",
                    "section_title": section_title,
                    "section_type": section_type,
                    "section_number": section.get("number", str(section_index + 1)),
                    "chapter_number": chapter_counter,
                }
                all_chapters.append(chapter_data)
                chapter_counter += 1

        print(f"[HIERARCHICAL EXTRACTION] Extracted {len(all_chapters)} total chapters")

        # Skip AI validation if we have reasonable number of chapters
        if 3 <= len(all_chapters) <= 20:  # Reasonable chapter count
            print(
                "[AI VALIDATION] Skipping AI validation - chapter count looks reasonable"
            )
            return all_chapters

        # Apply AI validation if needed
        if len(all_chapters) > 20:
            validated_chapters = await self._ai_filter_real_chapters(
                all_chapters, book_type, book_content
            )
            return validated_chapters

        return all_chapters

    # In _extract_flat_chapters method
    async def _extract_flat_chapters(
        self, chapters: List[Dict], book_type: str, book_content: str
    ) -> List[Dict[str, Any]]:
        """Extract chapters from flat structure"""
        print(f"[FLAT EXTRACTION] Processing {len(chapters)} flat chapters")

        chapter_list = []
        for index, chapter in enumerate(chapters):
            chapter_data = {
                "title": chapter["title"],
                "content": chapter["content"],
                "summary": f"Chapter {index + 1}",
                "chapter_number": index + 1,
            }
            chapter_list.append(chapter_data)

        # Skip AI validation if we have reasonable number of chapters
        if 3 <= len(chapter_list) <= 20:  # Reasonable chapter count
            print(
                "[AI VALIDATION] Skipping AI validation - chapter count looks reasonable"
            )
            return chapter_list

        # Apply AI validation if needed
        if len(chapter_list) > 20:
            validated_chapters = await self._ai_filter_real_chapters(
                chapter_list, book_type, book_content
            )
            return validated_chapters

        return chapter_list

    def _get_fallback_chapters(
        self, content: str, book_type: str
    ) -> List[Dict[str, Any]]:
        """Fallback method when all other extraction methods fail"""
        if book_type == "learning":
            return [
                {
                    "title": "Complete Learning Content",
                    "content": content,
                    "summary": "Complete learning material",
                }
            ]
        else:
            return [
                {
                    "title": "Complete Story",
                    "content": content,
                    "summary": "Complete story content",
                }
            ]

    def _clean_text_content(self, content: str) -> str:
        """Clean text content to handle Unicode escape sequences and problematic characters"""
        return TextSanitizer.sanitize_text(content)

    async def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        """Upload file to Local storage"""
        try:
            from app.core.services.storage import storage_service

            # Read file
            async with aiofiles.open(local_path, "rb") as f:
                file_data = await f.read()

            # Upload to Local storage
            # Determine content type based on extension
            import mimetypes

            content_type, _ = mimetypes.guess_type(local_path)

            public_url = await storage_service.upload(
                file_data, remote_path, content_type
            )

            if public_url:
                print(f"[FILE UPLOAD SUCCESS] {remote_path} -> {public_url}")
                return public_url
            else:
                print(f"[FILE UPLOAD ERROR] Failed to get public URL for {remote_path}")
                return None

        except Exception as e:
            print(f"[FILE UPLOAD ERROR] {str(e)}")
            return None

    async def download_file(self, url: str, local_path: str) -> bool:
        """Download file from URL to local path"""

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        async with aiofiles.open(local_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        print(f"[FILE DOWNLOAD SUCCESS] {url} -> {local_path}")
                        return True
                    else:
                        print(f"[FILE DOWNLOAD ERROR] HTTP {response.status} for {url}")
                        return False

        except Exception as e:
            print(f"[FILE DOWNLOAD ERROR] {str(e)}")
            return False

    def get_temp_filename(self, prefix: str = "temp", extension: str = ".mp4") -> str:
        """Generate unique temporary filename"""
        return f"{prefix}_{uuid.uuid4().hex}{extension}"

    async def _extract_complex_toc_with_ai(
        self, doc, toc_pages: List[int]
    ) -> List[Dict[str, Any]]:
        """AI extraction for complex TOCs - COMPLETELY GENERIC"""
        print("[COMPLEX TOC AI] Using AI for complex TOC extraction...")

        # Get text from detected TOC pages
        toc_text_blocks = []
        for page_num in toc_pages:
            page = doc[page_num]
            text = page.get_text()

            # OCR fallback for scanned/image-based PDFs
            if not text.strip():
                try:
                    tp = page.get_textpage_ocr(
                        flags=0, language="eng", dpi=150, full=True
                    )
                    text = page.get_text(textpage=tp)
                    if text.strip():
                        print(
                            f"[COMPLEX TOC AI] OCR extracted text from page {page_num + 1}"
                        )
                except Exception as e:
                    print(f"[COMPLEX TOC AI] OCR failed for page {page_num + 1}: {e}")

            toc_text_blocks.append(
                {"page_num": page_num + 1, "text": text, "lines": text.split("\n")}
            )

        # Generic search for additional TOC pages (not hardcoded)
        last_toc_page = max(toc_pages) if toc_pages else 0
        print(
            f"[COMPLEX TOC AI] Searching up to 10 pages after last TOC page {last_toc_page + 1}"
        )

        for additional_page in range(
            last_toc_page + 1, min(last_toc_page + 11, len(doc))
        ):
            page = doc[additional_page]
            text = page.get_text()

            # OCR fallback for scanned PDFs
            if not text.strip():
                try:
                    tp = page.get_textpage_ocr(
                        flags=0, language="eng", dpi=150, full=True
                    )
                    text = page.get_text(textpage=tp)
                except Exception:
                    pass

            text_upper = text.upper()

            # Generic TOC continuation indicators
            continuation_score = 0

            # Check for structural divisions (works for any book type)
            structural_patterns = [
                r"BOOK\s+(THE\s+)?(FIRST|SECOND|THIRD|FOURTH|FIFTH|ONE|TWO|THREE|FOUR|FIVE|[IVX]+|\d+)",
                r"PART\s+(THE\s+)?(FIRST|SECOND|THIRD|FOURTH|FIFTH|ONE|TWO|THREE|FOUR|FIVE|[IVX]+|\d+)",
                r"SECTION\s+(THE\s+)?(FIRST|SECOND|THIRD|FOURTH|FIFTH|ONE|TWO|THREE|FOUR|FIVE|[IVX]+|\d+)",
                r"VOLUME\s+(THE\s+)?(FIRST|SECOND|THIRD|FOURTH|FIFTH|ONE|TWO|THREE|FOUR|FIVE|[IVX]+|\d+)",
                r"ACT\s+(THE\s+)?(FIRST|SECOND|THIRD|FOURTH|FIFTH|ONE|TWO|THREE|FOUR|FIVE|[IVX]+|\d+)",
            ]

            for pattern in structural_patterns:
                if re.search(pattern, text_upper):
                    continuation_score += 3
                    print(
                        f"[COMPLEX TOC AI] Found structural division on page {additional_page + 1}"
                    )

            # Check for chapter number patterns (generic)
            chapter_patterns = [
                r"[IVX]+\.\s+[A-Z]",  # Roman numerals with titles
                r"\d+\.\s+[A-Z]",  # Arabic numbers with titles
                r"CHAPTER\s+[IVX]+",  # "CHAPTER I", etc.
                r"Chapter\s+\d+",  # "Chapter 1", etc.
            ]

            total_chapter_entries = 0
            for pattern in chapter_patterns:
                matches = len(re.findall(pattern, text))
                total_chapter_entries += matches

            if total_chapter_entries >= 3:
                continuation_score += 2
                print(
                    f"[COMPLEX TOC AI] Found {total_chapter_entries} chapter entries on page {additional_page + 1}"
                )

            # Check for page number references (common in TOCs)
            page_refs = len(
                re.findall(r"\.{3,}\s*\d+|[A-Za-z]\s+\d+\s*$", text, re.MULTILINE)
            )
            if page_refs >= 5:
                continuation_score += 3  # Strong indicator
                print(
                    f"[COMPLEX TOC AI] Found high density of page refs ({page_refs}) on page {additional_page + 1}"
                )
            elif page_refs >= 2:
                continuation_score += 1

            # Only include if we have evidence (lowered threshold from 3 to 2)
            if continuation_score >= 2:
                print(
                    f"[COMPLEX TOC AI] ✅ Including page {additional_page + 1} (score: {continuation_score})"
                )
                toc_text_blocks.append(
                    {
                        "page_num": additional_page + 1,
                        "text": text,
                        "lines": text.split("\n"),
                    }
                )
            else:
                print(
                    f"[COMPLEX TOC AI] ❌ Skipping page {additional_page + 1} (score: {continuation_score})"
                )

        # GAP FILLING LOGIC: If we have a gap between pages, fill it
        # E.g. we have pages [8, 9, 10] and [15], we should likely include [11, 12, 13, 14]
        # Sort current blocks by page
        toc_text_blocks.sort(key=lambda x: x["page_num"])

        print(
            f"[COMPLEX TOC AI] Starting Gap Filling Check. Current pages: {[b['page_num'] for b in toc_text_blocks]}"
        )

        filled_blocks = []
        if toc_text_blocks:
            current_pages = {b["page_num"] for b in toc_text_blocks}
            min_page = toc_text_blocks[0]["page_num"]
            max_page = toc_text_blocks[-1]["page_num"]

            print(
                f"[COMPLEX TOC AI] Checking for gaps between page {min_page} and {max_page}"
            )

            for p in range(min_page, max_page + 1):
                if p not in current_pages:
                    # Found a gap page
                    print(f"[COMPLEX TOC AI] Filling gap: including page {p}")
                    try:
                        # Find the doc index for this page (p is 1-based, doc is 0-based)
                        page_idx = p - 1
                        if 0 <= page_idx < len(doc):
                            page_text = doc[page_idx].get_text()
                            filled_blocks.append(
                                {
                                    "page_num": p,
                                    "text": page_text,
                                    "lines": page_text.split("\n"),
                                }
                            )
                    except Exception as e:
                        print(f"[COMPLEX TOC AI] Error filling gap page {p}: {e}")

        # Add filled blocks and resort
        if filled_blocks:
            print(f"[COMPLEX TOC AI] Added {len(filled_blocks)} gap-filled pages")
            toc_text_blocks.extend(filled_blocks)
            toc_text_blocks.sort(key=lambda x: x["page_num"])
        else:
            print("[COMPLEX TOC AI] No gaps found to fill")

        combined_toc_text = "\n\n=== PAGE BREAK ===\n\n".join(
            [f"PAGE {block['page_num']}:\n{block['text']}" for block in toc_text_blocks]
        )

        print(f"[COMPLEX TOC AI] Processing {len(toc_text_blocks)} TOC pages")
        print(f"[COMPLEX TOC AI] Combined text length: {len(combined_toc_text)}")

        # COMPLETELY GENERIC PROMPT - works for any book
        prompt = f"""
        You are analyzing a Table of Contents that may have a hierarchical structure with multiple sections.

        CRITICAL: DISTINGUISH BETWEEN CHAPTERS AND SUB-SECTIONS
        - A CHAPTER is a top-level entry like: "1 Algorithms with numbers", "Chapter 9 Coping with NP-completeness", "0 Prologue"
        - A SUB-SECTION is an indented or numbered sub-entry like: "1.1 Basic arithmetic", "9.2 Approximation algorithms"
        - ONLY extract TOP-LEVEL CHAPTERS, NOT sub-sections!
        - If you see "1 Title" followed by "1.1 Subtitle", "1.2 Subtitle", the chapter is "1 Title" and the 1.x entries are sub-sections to IGNORE

        INSTRUCTIONS:
        1. Extract ONLY major structural divisions and their TOP-LEVEL chapters
        2. Look for hierarchical patterns such as:
           - Books: "BOOK I", "BOOK THE FIRST", "BOOK ONE"
           - Parts: "PART I", "PART ONE", "PART A"
           - Sections: "SECTION I", "SECTION ONE"
           - Acts: "ACT I", "ACT ONE" (for plays)
           - Volumes: "VOLUME I", "VOLUME ONE"
           - Any other major divisions
        3. Within each section, find ONLY TOP-LEVEL chapters:
           - Roman numerals: I, II, III, IV, V, etc.
           - Arabic numbers WITHOUT decimals: 0, 1, 2, 3, 4, 5, etc. (NOT 1.1, 2.3)
           - "Chapter N" entries
           - DO NOT include sub-sections like "1.1", "2.3", "10.5", etc.
        4. Scan ALL pages provided - content may continue across pages
        5. Find ALL structural divisions - don't assume a specific number
        6. IGNORE auxiliary content: preface, appendix, notes, bibliography, index, exercises

        EXAMPLE OF WHAT TO EXTRACT:
        From a TOC like:
        "0 Prologue ........... 11
           0.1 Books and algorithms ... 11
           0.2 Enter Fibonacci ... 12
         1 Algorithms with numbers ... 21
           1.1 Basic arithmetic ... 21
           1.2 Modular arithmetic ... 25"
        
        You should extract ONLY:
        - Chapter 0: "Prologue" (page 11)
        - Chapter 1: "Algorithms with numbers" (page 21)
        NOT the 0.1, 0.2, 1.1, 1.2 sub-sections!

        TOC Text (Multiple Pages):
        {combined_toc_text[:20000]}

        Return JSON with the complete structure found:
        {{
            "sections": [
                {{
                    "section_title": "Detected Section Name",
                    "section_type": "book|part|act|volume|section",
                    "section_number": "I|II|III|ONE|TWO|1|2|3",
                    "chapters": [
                        {{
                            "number": "0|1|2|I|II (TOP-LEVEL ONLY, no decimals)",
                            "title": "Chapter Title",
                            "page": page_number
                        }}
                    ]
                }}
            ]
        }}

        REQUIREMENTS:
        - Extract ONLY TOP-LEVEL chapters (no sub-sections like 1.1, 2.3)
        - Include ALL main chapters within each division
        - If no major divisions exist, create a single section with all chapters
        - Keep original number formats (Roman numerals as Roman, Arabic as Arabic)
        - Return ONLY the JSON object

        RETURN ONLY VALID JSON, NO OTHER TEXT.
        """

        try:
            response = await self.ai_service._make_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing Table of Contents from any type of book. Extract the complete hierarchical structure comprehensively. Return ONLY valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                provider="auto",
                max_tokens=8000,
                temperature=0.1,
            )

            content = response.choices[0].message.content.strip()

            # Clean JSON response
            print(f"[COMPLEX TOC AI] Raw AI response length: {len(content)}")
            print(f"[COMPLEX TOC AI] First 500 chars: {content[:500]}")

            # Remove markdown formatting if present
            if content.startswith("```"):
                lines = content.split("\n")
                start_idx = 1
                end_idx = len(lines) - 1
                for i, line in enumerate(lines[1:], 1):
                    if line.strip().startswith("{"):
                        start_idx = i
                        break
                for i in range(len(lines) - 1, 0, -1):
                    if lines[i].strip().endswith("}"):
                        end_idx = i
                        break
                content = "\n".join(lines[start_idx : end_idx + 1])

            # Find JSON boundaries
            first_brace = content.find("{")
            if first_brace != -1:
                brace_count = 0
                last_brace = -1
                for i, char in enumerate(content[first_brace:], first_brace):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            last_brace = i
                            break

                if last_brace != -1:
                    content = content[first_brace : last_brace + 1]

            print(f"[COMPLEX TOC AI] Cleaned content length: {len(content)}")

            result = json.loads(content)
            sections = result.get("sections", [])

            print(f"[COMPLEX TOC AI] AI found {len(sections)} sections")

            # Generic conversion to flat chapter list
            all_chapters = []
            chapter_counter = 1

            for section in sections:
                section_title = section.get(
                    "section_title", f"Section {len(all_chapters) + 1}"
                )
                section_type = section.get("section_type", "section")
                section_number = section.get(
                    "section_number", str(len(all_chapters) + 1)
                )

                print(f"[COMPLEX TOC AI] Processing section: {section_title}")

                for ch in section.get("chapters", []):
                    try:
                        # Handle different number formats generically
                        raw_number = ch.get("number", str(chapter_counter))
                        title = str(ch.get("title", "Unknown")).strip()
                        page_hint = ch.get("page", 1)

                        # Convert Roman numerals to integers for chapter numbering
                        if isinstance(raw_number, str) and re.match(
                            r"^[IVX]+$", raw_number.strip().upper()
                        ):
                            chapter_number = self._roman_to_int(
                                raw_number.strip().upper()
                            )
                        else:
                            try:
                                chapter_number = int(raw_number)
                            except (ValueError, TypeError):
                                chapter_number = chapter_counter

                        # Ensure page_hint is an integer
                        try:
                            page_hint = int(page_hint)
                        except (ValueError, TypeError):
                            page_hint = 1

                        if not title or len(title) < 2:
                            continue

                        formatted_chapter = {
                            "number": chapter_counter,
                            "title": f"Chapter {chapter_number}: {title}",
                            "raw_title": title,
                            "page_hint": page_hint,
                            "section_title": section_title,
                            "section_type": section_type,
                            "section_number": section_number,
                            "is_main_chapter": True,
                        }

                        all_chapters.append(formatted_chapter)
                        print(
                            f"[COMPLEX TOC AI] Added: {title} (Section: {section_title})"
                        )
                        chapter_counter += 1

                    except (ValueError, TypeError) as e:
                        print(f"[COMPLEX TOC AI] Error processing chapter {ch}: {e}")
                        continue

            print(f"[COMPLEX TOC AI] Total chapters extracted: {len(all_chapters)}")

            # Extract content using page-based extraction
            if len(all_chapters) >= 3:
                print(
                    "[COMPLEX TOC AI] Extracting content using page-based extraction..."
                )
                return await self._parse_toc_with_ai_improved(all_chapters, doc)

            return all_chapters

        except json.JSONDecodeError as e:
            print(f"[COMPLEX TOC AI] JSON decode failed: {e}")
            print(
                f"[COMPLEX TOC AI] Failed content: {content if 'content' in locals() else 'No content'}"
            )
            return []
        except Exception as e:
            print(f"[COMPLEX TOC AI] Failed: {e}")
            return []

    async def _extract_toc_with_ai(
        self, toc_text_blocks: List[Dict], doc
    ) -> List[Dict[str, Any]]:
        """Generic AI TOC parsing for any book - completely generic approach"""
        print("[AI TOC EXTRACTION] Using AI to parse TOC structure...")

        # Combine all TOC text with better separation
        combined_toc_text = "\n\n=== NEW PAGE ===\n\n".join(
            [f"PAGE {block['page_num']}:\n{block['text']}" for block in toc_text_blocks]
        )

        # Completely generic prompt
        prompt = f"""
            You are analyzing a Table of Contents from a book. Extract ALL chapters and sections from this TOC.
            
            INSTRUCTIONS:
            1. Extract EVERY chapter entry you can find across ALL pages
            2. Look for any numbering system: Roman numerals (I, II, III), Arabic numbers (1, 2, 3), or word numbers (One, Two)
            3. Identify any major sections/books/parts that group chapters together
            4. The TOC may span multiple pages - analyze ALL pages thoroughly
            5. Don't miss any chapters just because the layout is complex or they appear on later pages
            6. Include ALL sections mentioned (there could be 2, 3, 4, or more major divisions)
            7. Look for patterns like columnar layouts where numbers and titles may be separated
            8. Look for the PRIMARY content divisions (main chapters, books, parts, acts, etc.)
            9. IGNORE front/back matter: preface, acknowledgments, bibliography, index, appendix, notes
            10. IGNORE subsections and detailed breakdowns - focus on major divisions
            11. Look for numbered or titled main content sections
            12. Typically books have 3-25 main content divisions
            
            WHAT TO EXTRACT (examples):
            - Numbered chapters: "Chapter 1", "Chapter 2"
            - Named sections: "The Beginning", "The Journey" 
            - Books/Parts: "Book One", "Part I"
            - Acts/Movements: "Act 1", "First Movement"
            - Any major story/content divisions
            
            WHAT TO IGNORE:
            - Table of contents, list of figures, preface, acknowledgments
            - Bibliography, index, appendix, notes, references
            - Detailed subsections within main chapters
            - Publication information, copyright pages
        
            Common patterns to look for:
            - "CHAPTER 1. Title Name ... Page"
            - "I. Title Name ... Page" (Roman numerals)
            - "BOOK/PART/SECTION [Name]" followed by chapters
            - Multi-level hierarchies with sections containing chapters
            - Any numbered content that represents story/learning divisions
            
            TOC Text (spans multiple pages):
            {combined_toc_text[:12000]}
            
            Return JSON with ALL chapters found. If the book has sections/parts/books, include that information:
            {{
                "chapters": [
                    {{
                        "number": 1,
                        "title": "First Chapter Title",
                        "page": 1,
                        "section": "Section Name (if any, otherwise leave empty)"
                    }},
                    {{
                        "number": 2,
                        "title": "Second Chapter Title", 
                        "page": 15,
                        "section": "Section Name (if any, otherwise leave empty)"
                    }}
                ]
            }}
            
            CRITICAL:
            - Extract the COMPLETE structure - don't stop early
            - If chapters are grouped under sections/books/parts, include that section information
            - If no clear sections exist, leave section field empty
            - Look at ALL pages of the TOC provided
            - Return ONLY valid JSON, no other text
            """

        try:
            # ✅ FIX: Use new provider-based system
            response = await self.ai_service._make_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at parsing Table of Contents from any book. Extract ALL sections and chapters comprehensively from any book structure. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                provider="auto",
                max_tokens=5000,
                temperature=0.1,
            )

            # Clean the response
            content = response.choices[0].message.content.strip()

            # Remove markdown formatting if present
            if content.startswith("```"):
                lines = content.split("\n")
                # Find the actual JSON content between ```
                start_idx = 1
                end_idx = len(lines) - 1
                for i, line in enumerate(lines[1:], 1):
                    if line.strip().startswith("{"):
                        start_idx = i
                        break
                for i in range(len(lines) - 1, 0, -1):
                    if lines[i].strip().endswith("}"):
                        end_idx = i
                        break
                content = "\n".join(lines[start_idx : end_idx + 1])

            # Additional cleaning
            content = content.strip()
            if content.startswith("json\n"):
                content = content[5:]

            print(f"[AI TOC EXTRACTION] AI response length: {len(content)}")
            print(f"[AI TOC EXTRACTION] First 200 chars: {content[:200]}")

            result = json.loads(content)
            chapters = result.get("chapters", [])

            print(f"[AI TOC EXTRACTION] AI extracted {len(chapters)} chapters")

            # Add: Count chapters per section to verify we got all sections
            section_counts = {}
            for ch in chapters:
                section = ch.get("section", "No Section")
                if section and section.strip():  # Only count non-empty sections
                    section_counts[section] = section_counts.get(section, 0) + 1

            print(f"[AI TOC EXTRACTION] Chapters per section: {section_counts}")

            # Convert to our format with better validation
            formatted_chapters = []
            chapter_counter = 1

            for ch in chapters:
                if not ch.get("title") or not ch.get("page"):
                    print(
                        f"[AI TOC EXTRACTION] Skipping chapter with missing title or page: {ch}"
                    )
                    continue

                try:
                    chapter_number = int(ch.get("number", chapter_counter))
                    page_hint = int(ch.get("page", 1))
                    title = str(ch.get("title", "Unknown")).strip()

                    # Clean the title
                    title = re.sub(r"\.{3,}.*$", "", title)
                    title = re.sub(r"\s+\d+\s*$", "", title)
                    title = title.strip()

                    if not title or len(title) < 2:
                        continue

                    formatted_chapter = {
                        "number": chapter_number,
                        "title": f"Chapter {chapter_number}: {title}",
                        "raw_title": title,
                        "page_hint": page_hint,
                    }

                    # Add section info if present
                    section_info = ch.get("section", "")
                    if (
                        section_info
                        and isinstance(section_info, str)
                        and section_info.strip()
                    ):
                        formatted_chapter.update(
                            {
                                "section_title": section_info.strip(),
                                "section_type": self._extract_section_type(
                                    section_info
                                ),
                                "section_number": self._extract_section_number(
                                    section_info
                                ),
                            }
                        )

                        print(
                            f"[AI TOC EXTRACTION] Formatted: Chapter {chapter_number}: {title} (Section: {section_info})"
                        )
                    else:
                        print(
                            f"[AI TOC EXTRACTION] Formatted: Chapter {chapter_number}: {title} (No section)"
                        )

                    formatted_chapters.append(formatted_chapter)
                    chapter_counter += 1

                except (ValueError, TypeError) as e:
                    print(f"[AI TOC EXTRACTION] Error processing chapter {ch}: {e}")
                    continue

            # Final verification: Check section distribution
            final_section_counts = {}
            for ch in formatted_chapters:
                section = ch.get("section_title", "No Section")
                final_section_counts[section] = final_section_counts.get(section, 0) + 1

            print(
                f"[AI TOC EXTRACTION] Final chapters per section: {final_section_counts}"
            )
            print(
                f"[AI TOC EXTRACTION] Total formatted chapters: {len(formatted_chapters)}"
            )

            return formatted_chapters

        except json.JSONDecodeError as e:
            print(f"[AI TOC EXTRACTION] JSON decode failed: {e}")
            print(
                f"[AI TOC EXTRACTION] Raw response: {response.choices[0].message.content if 'response' in locals() else 'No response'}"
            )
            return []
        except Exception as e:
            print(f"[AI TOC EXTRACTION] Failed: {e}")
            print(f"[AI TOC EXTRACTION] Full error: {traceback.format_exc()}")
            return []

    async def _enhance_partial_toc_with_ai(
        self, doc, partial_chapters: List[Dict]
    ) -> List[Dict]:
        """Use AI to find missing chapters when partial TOC is detected"""
        print(
            f"[TOC ENHANCEMENT] Enhancing {len(partial_chapters)} partial chapters with AI..."
        )

        # Get more text from the document
        full_toc_text = ""
        for page_num in range(min(40, len(doc))):
            page_text = doc[page_num].get_text()
            if any(
                keyword in page_text.upper()
                for keyword in ["CONTENTS", "CHAPTER", "BOOK THE"]
            ):
                full_toc_text += f"\n--- PAGE {page_num + 1} ---\n{page_text}"

        try:
            prompt = f"""
            I found {len(partial_chapters)} chapters in a Table of Contents, but I suspect there are more. 
            
            Currently found chapters:
            {json.dumps([{'title': ch['title'], 'page': ch.get('page_hint')} for ch in partial_chapters], indent=2)}
            
            Here's the full TOC text to analyze:
            {full_toc_text[:10000]}
            
            Please find ALL chapters in this TOC, including any I missed. Look for:
            - Roman numerals (I, II, III, etc.)
            - Chapter titles in various formats
            - Page numbers
            - Section divisions (Book the First, etc.)
            
            Return complete list as JSON:
            {{
                "chapters": [
                    {{
                        "number": 1,
                        "title": "THE PERIOD",
                        "page": 1,
                        "section": "BOOK THE FIRST"
                    }}
                ]
            }}
            """

            # ✅ FIX: Use new provider-based system
            response = await self.ai_service._make_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing Table of Contents. Find ALL chapters, don't miss any.",
                    },
                    {"role": "user", "content": prompt},
                ],
                provider="auto",
                max_tokens=4000,
                temperature=0.1,
            )

            result = json.loads(response.choices[0].message.content)
            enhanced_chapters = []

            for ch in result.get("chapters", []):
                formatted_chapter = {
                    "number": ch.get("number", 1),
                    "title": f"Chapter {ch.get('number', 1)}: {ch.get('title', 'Unknown')}",
                    "raw_title": ch.get("title", "Unknown"),
                    "page_hint": ch.get("page", 1),
                }

                if ch.get("section"):
                    formatted_chapter.update(
                        {
                            "section_title": ch["section"],
                            "section_type": (
                                "book" if "BOOK" in ch["section"].upper() else "section"
                            ),
                        }
                    )

                enhanced_chapters.append(formatted_chapter)

            print(
                f"[TOC ENHANCEMENT] AI enhanced to {len(enhanced_chapters)} total chapters"
            )
            return enhanced_chapters

        except Exception as e:
            print(f"[TOC ENHANCEMENT] Failed: {e}")
            return partial_chapters

    async def _validate_content_match(
        self, chapter_title: str, content_preview: str
    ) -> bool:
        """Step 5: Validate that extracted content actually matches the chapter"""
        print(f"[CONTENT VALIDATION] Validating content for: {chapter_title}")

        try:
            prompt = f"""
            Does this content preview match what you'd expect for a chapter titled "{chapter_title}"?
            
            Content Preview:
            {content_preview}
            
            Return JSON:
            {{
                "matches": true/false,
                "confidence": 0.0-1.0,
                "reason": "explanation"
            }}
            """

            # ✅ FIX: Use new provider-based system
            response = await self.ai_service._make_completion(
                messages=[{"role": "user", "content": prompt}],
                provider="auto",
                max_tokens=300,
                temperature=0.1,
            )

            result = json.loads(response.choices[0].message.content)
            matches = result.get("matches", False)
            confidence = result.get("confidence", 0.0)

            print(f"[CONTENT VALIDATION] Match: {matches}, Confidence: {confidence}")
            return matches and confidence > 0.7

        except Exception as e:
            print(f"[CONTENT VALIDATION] Validation failed: {e}")
            return True  # Default to accepting if validation fails

    async def _ai_extract_chapter_content(
        self, chunks: List[str], chapter_title: str, context: Dict
    ) -> str:
        """Use AI to extract specific chapter content from text chunks"""

        # Combine relevant chunks
        search_text = "\n\n".join(chunks)

        # Use the property correctly
        book_title = self.extracted_title or context.get("book_title", "Unknown Book")

        print(f"[AI EXTRACTION] Processing: {chapter_title}")
        print(f"[AI EXTRACTION] Search text length: {len(search_text)}")
        print(f"[AI EXTRACTION] First 200 chars: {search_text[:200]}...")

        prompt = f"""
        Extract the full content for the chapter titled "{chapter_title}" from the following text.
        
        Book context: {book_title} - Total chapters: {context.get('total_chapters', 'unknown')}
        
        Instructions:
        1. Find the chapter that matches the title "{chapter_title}"
        2. Extract the complete content from chapter start to chapter end
        3. Include all paragraphs, sections, and subsections within this chapter
        4. Stop before the next chapter begins
        5. Remove any table of contents references
        6. Return only the main chapter content, not headers or page numbers
        
        Text to search:
        {search_text[:10000]}...
        
        Chapter content:
        """

        try:
            # ✅ FIX: Use new provider-based system
            response = await self.ai_service._make_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting specific chapter content from books. Return only the requested chapter content, nothing else.",
                    },
                    {"role": "user", "content": prompt},
                ],
                provider="auto",
                max_tokens=4000,
                temperature=0.1,
            )
            content = response.choices[0].message.content.strip()
            print(f"[AI EXTRACTION] AI returned {len(content)} characters")
            print(f"[AI EXTRACTION] First 200 chars of AI response: {content[:200]}...")

            # Validate the extracted content
            is_valid = self._validate_ai_extracted_content(content, chapter_title)
            print(f"[AI EXTRACTION] Content validation: {is_valid}")

            # Validate the extracted content
            if is_valid:
                return content
            else:
                print(f"[AI EXTRACTION] Content failed validation")
                return ""

        except Exception as e:
            print(f"[AI EXTRACTION] Error: {e}")
            import traceback

            print(f"[AI EXTRACTION] Full error: {traceback.format_exc()}")
            return ""

    async def _ai_filter_real_chapters(
        self, chapters: List[Dict[str, Any]], book_type: str, book_content: str
    ) -> List[Dict[str, Any]]:
        """Use AI to filter and identify real chapters from a list - MORE CONSERVATIVE"""
        print(
            f"[AI FILTERING] Filtering {len(chapters)} chapters to find real chapters..."
        )

        # Don't use AI filtering unless we have an excessive number of chapters
        if len(chapters) <= 30:
            print(
                f"[AI FILTERING] Chapter count reasonable ({len(chapters)}), skipping AI filtering"
            )
            return chapters[:25]  # Just cap at 25 if needed

        # Add input validation
        if not chapters:
            print("[AI FILTERING] No chapters to filter")
            return []

        # Prepare a sample of the book content for AI context
        content_sample = (
            book_content[:8000] if len(book_content) > 8000 else book_content
        )

        # Limit chapters sent to AI to avoid token limits
        chapters_to_analyze = chapters[:30]  # Analyze first 30 only

        # Much more conservative prompt
        prompt = f"""You are analyzing a {book_type} book. Here's a sample of the book content:
    
        ---
        {content_sample}
        ---
    
        I have extracted {len(chapters_to_analyze)} potential chapters. Many are likely valid chapters.
    
        Chapter titles:
        {json.dumps([{'number': i+1, 'title': ch.get('title', 'Untitled')[:100]} for i, ch in enumerate(chapters_to_analyze)], indent=2)}
    
        IMPORTANT: Be VERY CONSERVATIVE. Only exclude chapters if they are clearly:
        - Table of contents entries
        - Copyright pages
        - Index entries
        - Bibliography entries
        - Obviously not story/content chapters
    
        Most chapters should be KEPT, not removed.
    
        Return JSON with chapter numbers to KEEP (be generous):
        {{
            "chapters": [1, 2, 3, 4, ...],
            "total_chapters": {len(chapters_to_analyze)},
            "reasoning": "Kept most chapters as they appear to be valid story content"
        }}"""

        try:
            # ✅ FIX: Use new provider-based system
            response = await self.ai_service._make_completion(
                messages=[{"role": "user", "content": prompt}],
                provider="auto",
                max_tokens=2000,
                temperature=0.1,
            )

            result = json.loads(response.choices[0].message.content)

            if not result or "chapters" not in result:
                print(f"[AI FILTERING] No valid response from AI, keeping all chapters")
                return chapters_to_analyze

            valid_indices = result.get("chapters", [])
            filtered_chapters = []

            for idx in valid_indices:
                if 1 <= idx <= len(chapters_to_analyze):
                    filtered_chapters.append(chapters_to_analyze[idx - 1])

            # Much more lenient threshold - keep most chapters
            if (
                len(filtered_chapters) < len(chapters_to_analyze) * 0.7
            ):  # Less than 70% kept
                print(
                    f"[AI FILTERING] AI too aggressive ({len(filtered_chapters)}/{len(chapters_to_analyze)}), keeping most chapters"
                )
                filtered_chapters = chapters_to_analyze[:20]  # Keep first 20

            estimated_total = result.get("total_chapters", len(filtered_chapters))
            reason = result.get("reasoning", "AI analysis")

            print(
                f"[AI FILTERING] AI kept {len(filtered_chapters)} chapters out of {len(chapters_to_analyze)}"
            )
            print(f"[AI FILTERING] Estimated total chapters: {estimated_total}")
            print(f"[AI FILTERING] Reasoning: {reason}")

            return filtered_chapters

        except Exception as e:
            print(f"[AI FILTERING] Error: {e}")
            print(f"[AI FILTERING] Falling back to keeping first 20 chapters")
            return chapters[:20]  # Conservative fallback

    # Add the missing _detect_structure_from_chapters method
    def _detect_structure_from_chapters(self, chapters: List[Dict]) -> str:
        """Detect the structure type from chapter data"""
        sections = set()
        for chapter in chapters:
            if chapter.get("section_title"):
                sections.add(chapter["section_title"])

        if len(sections) > 1:
            return "hierarchical"
        return "flat"
