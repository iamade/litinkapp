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
from supabase import create_client, Client
from app.services.ai_service import AIService
from app.schemas.book import BookCreate, ChapterCreate, BookUpdate
import tempfile
import math
import hashlib
import json
import time
from app.services.text_utils import TextSanitizer
import itertools
import traceback



class BookStructureDetector:
    def __init__(self):
        # Enhanced patterns for different book structures
        self.STRUCTURE_PATTERNS = {
            'tablet': {
                'patterns': [
                    r'(?i)^tablet\s+([ivx]+|\d+)[\s\-:]*(.{10,})$',
                    r'(?i)^clay\s+tablet\s+([ivx]+|\d+)[\s\-:]*(.{10,})$',
                ],
                'indicators': ['tablet', 'clay', 'cuneiform', 'mesopotamian', 'sumerian', 'babylonian'],
                'typical_count': (1, 12)
            },
            'book': {
                'patterns': [
                    r'(?i)^book\s+(\d+|[ivx]+|one|two|three|four|five|six|seven|eight|nine|ten)[\s\-:]*(.{10,})$',
                    r'(?i)^volume\s+(\d+|[ivx]+)[\s\-:]*(.{10,})$',
                ],
                'indicators': ['book', 'volume', 'tome', 'part'],
                'typical_count': (2, 10)
            },
            'part': {
                'patterns': [
                    r'(?i)^part\s+(\d+|[ivx]+|one|two|three|four|five|six|seven|eight|nine|ten)[\s\-:]*(.{10,})$',
                    r'(?i)^section\s+(\d+|[ivx]+)[\s\-:]*(.{10,})$',
                ],
                'indicators': ['part', 'section', 'division'],
                'typical_count': (2, 8)
            },
            'act': {
                'patterns': [
                    r'(?i)^act\s+([ivx]+|\d+)[\s\-:]*(.{10,})$',
                    r'(?i)^scene\s+([ivx]+|\d+)[\s\-:]*(.{10,})$',
                ],
                'indicators': ['act', 'scene', 'drama', 'play', 'theatre', 'theater'],
                'typical_count': (3, 7)
            },
            'movement': {
                'patterns': [
                    r'(?i)^movement\s+([ivx]+|\d+)[\s\-:]*(.{10,})$',
                    r'(?i)^symphony\s+([ivx]+|\d+)[\s\-:]*(.{10,})$',
                ],
                'indicators': ['movement', 'symphony', 'concerto', 'sonata', 'musical'],
                'typical_count': (3, 6)
            },
            'canto': {
                'patterns': [
                    r'(?i)^canto\s+([ivx]+|\d+)[\s\-:]*(.{10,})$',
                    r'(?i)^song\s+([ivx]+|\d+)[\s\-:]*(.{10,})$',
                ],
                'indicators': ['canto', 'song', 'verse', 'epic', 'poem'],
                'typical_count': (10, 100)
            }
        }
        
           # COMPREHENSIVE CHAPTER PATTERNS - handles multiple book formats
        self.CHAPTER_PATTERNS = [
            # Standalone numbers and Roman numerals (for books like yours)
            r'^(\d+)$',  # Just "1", "2", "3"
            r'^([IVX]+)$',  # Just "I", "II", "III"
            
            # Traditional chapter headers
            r'^CHAPTER\s+(\d+)[\.\s]*(.*)$',  # CHAPTER 1, CHAPTER 1. Title
            r'^CHAPTER\s+([IVX]+)[\.\s]*(.*)$',  # CHAPTER I, CHAPTER I. Title  
            r'^Chapter\s+(\d+)[\.\s]*(.*)$',   # Chapter 1, Chapter 1. Title
            r'^Chapter\s+([IVX]+)[\.\s]*(.*)$', # Chapter I, Chapter I. Title
            
            # More flexible variations
            r'^CHAPTER\s+(\d+)[\s\-:]*(.*)$',  # CHAPTER 1: Title, CHAPTER 1 - Title
            r'^CHAPTER\s+([IVX]+)[\s\-:]*(.*)$', # CHAPTER I: Title
            r'^Chapter\s+(\d+)[\s\-:]*(.*)$',   # Chapter 1: Title
            r'^Chapter\s+([IVX]+)[\s\-:]*(.*)$', # Chapter I: Title
            
            # Alternative formats
            r'^(\d+)\.\s*(.*)$',  # "1. Chapter Title"
            r'^([IVX]+)\.\s*(.*)$', # "I. Chapter Title"
            
            # Word-based chapters
            r'^CHAPTER\s+([A-Z][a-z]+)\s*(.*)$', # CHAPTER One, CHAPTER Two
            r'^Chapter\s+([A-Z][a-z]+)\s*(.*)$', # Chapter One, Chapter Two
        ]
        
        # FLEXIBLE TITLE PATTERNS - matches various title formats
        self.TITLE_PATTERNS = [
            r'^([A-Z][A-Za-z\s]+(?:to|of|and|the|in|with|for|on|at|by)\s+[A-Z][A-Za-z\s]+)$', # Complex titles
            r'^([A-Z][A-Za-z\s]{5,})$',  # Titles with at least 5 characters
            r'^([A-Z][a-zA-Z\s\-\:]+)$', # Titles with dashes and colons
            r'^([A-Z\s]+)$',  # All caps titles
        ]
        
        # Keep your existing section and special patterns as they are flexible
        self.SECTION_PATTERNS = [
            r'^PART\s+([A-Z]+|[IVX]+|\d+)[\s\-:]*(.{10,})$',
            r'^Part\s+([A-Z]+|[IVX]+|\d+)[\s\-:]*(.{10,})$',
            r'(?i)^tablet\s+([ivx]+|\d+)[\s\-:]*(.{10,})$',
            r'(?i)^book\s+(\d+|[ivx]+)[\s\-:]*(.{10,})$',
            r'(?i)^section\s+(\d+|[ivx]+)[\s\-:]*(.{10,})$',
        ]
        
        # Add TOC detection patterns to skip
        self.TOC_PATTERNS = [
            r'(?i)^contents?$',
            r'(?i)^table\s+of\s+contents?$',
            r'(?i)^index$',
            r'^\s*\d+\s*$',  # Lines with just numbers (page numbers)
            r'^.{1,50}\s+\d+\s*$',  # Short text followed by numbers (typical TOC entry)
        ]
        
        # Special sections that should be treated as standalone
        self.SPECIAL_SECTIONS = [
            r'(?i)^preface[\s\-:]*(.*)$',
            r'(?i)^introduction[\s\-:]*(.*)$',
            r'(?i)^foreword[\s\-:]*(.*)$',
            r'(?i)^prologue[\s\-:]*(.*)$',
            r'(?i)^epilogue[\s\-:]*(.*)$',
            r'(?i)^conclusion[\s\-:]*(.*)$',
            r'(?i)^appendix[\s\-:]*(.*)$',
        ]
        
        
    
        
        # """Enhanced structure detection that skips TOC sections"""
        # lines = content.split('\n')
        
        # # Try the improved chapter detection first for books with number + title format
        # chapter_headers = self._find_chapter_number_and_title(lines)
        
        # if len(chapter_headers) >= 8:  # Expect at least 8-9 chapters
        #     print(f"[STRUCTURE DETECTION] Using direct chapter detection: {len(chapter_headers)} chapters")
        #     flat_chapters = []
            
        #     for header in chapter_headers:
        #         content_text = self._extract_chapter_content(content, header, lines)
        #         flat_chapters.append({
        #             'title': header['title'],
        #             'number': header['number'],
        #             'content': content_text
        #         })
            
        #     return {
        #         "has_sections": False,
        #         "sections": None,
        #         "chapters": flat_chapters,
        #         "structure_type": "flat"
        #     }
            
        # # Fallback to comprehensive pattern matching
        # print("[STRUCTURE DETECTION] Using comprehensive pattern matching")
    
    
        # sections = []
        # current_section = None
        # flat_chapters = []
        # in_toc_section = False
        
        # for line_num, line in enumerate(lines):
        #     line = line.strip()
        #     if not line:
        #         continue
            
        #     # Skip if we're in a TOC section
        #     if self._is_toc_section(line):
        #         in_toc_section = True
        #         continue
            
        #     # Check if we've moved past TOC (substantial content indicates real chapters)
        #     if in_toc_section and len(line) > 100:  # Substantial content indicates we're past TOC
        #         in_toc_section = False
            
        #     if in_toc_section:
        #         continue
            
        #     # Skip obvious TOC entries
        #     if self._is_toc_entry(line):
        #         continue
                
        #     # Check if line matches any section pattern
        #     section_match = self._match_section_patterns(line)
        #     if section_match:
        #         # Verify this isn't a TOC entry by checking following content
        #         if self._has_substantial_following_content(lines, line_num):
        #             # Save previous section if exists
        #             if current_section:
        #                 sections.append(current_section)
                    
        #             # Start new section
        #             current_section = {
        #                 "title": line,
        #                 "number": section_match["number"],
        #                 "type": section_match["type"],
        #                 "chapters": [],
        #                 "content": self._extract_section_content(content, line, lines, line_num)
        #             }
        #         continue
            
        #     # Check for special sections (preface, introduction, etc.)
        #     special_match = self._match_special_sections(line)
        #     if special_match and self._has_substantial_following_content(lines, line_num):
        #         # Save previous section if exists
        #         if current_section:
        #             sections.append(current_section)
                
        #         # Create special section
        #         current_section = {
        #             "title": line,
        #             "number": special_match["number"],
        #             "type": "special",
        #             "chapters": [],
        #             "content": self._extract_section_content(content, line, lines, line_num)
        #         }
        #         continue
            
        #     # Check if line matches chapter pattern (only if we're in a section)
        #     if current_section:
        #         chapter_match = self._match_chapter_patterns(line)
        #         if chapter_match and self._has_substantial_following_content(lines, line_num):
        #             chapter_content = self._extract_chapter_content(content, line, lines, line_num)
        #             # Only add if content is substantial
        #             if len(chapter_content.strip()) > 500:  # Minimum content length
        #                 chapter_data = {
        #                     "title": line,
        #                     "number": chapter_match["number"],
        #                     "content": self._extract_chapter_content(content, line, lines, line_num)
        #                 }
        #                 current_section["chapters"].append(chapter_data)
        
        # # Add last section
        # if current_section:
        #     sections.append(current_section)
            
        # # Remove duplicate chapters based on normalized numbers
        # sections = self._remove_duplicate_chapters(sections)
        
        # # If no sections found, try to extract flat chapters
        # if not sections:
        #     flat_chapters = self._extract_flat_chapters(content)
            
        
        # # Determine structure type
        # has_sections = len(sections) > 0
        
        #     # Add deduplication logic
        # seen_titles = set()
        # unique_sections = []
        
        # for section in sections:  # 'sections' should already exist from your current code
        #     title_key = f"{section['title'].lower().strip()}"
        #     if title_key not in seen_titles:
        #         seen_titles.add(title_key)
        #         unique_sections.append(section)
        
        # # Also add minimum content length validation
        # filtered_sections = []
        # for section in unique_sections:
        #     if len(section.get('content', '').strip()) > 100:  # Minimum content threshold
        #         filtered_sections.append(section)
        
        # # Update the sections variable to use filtered_sections
        # sections = filtered_sections
            
        # return {
        #     "has_sections": has_sections,
        #     "sections": sections if has_sections else None,
        #     "chapters": flat_chapters if not has_sections else [],
        #     "structure_type": self._determine_structure_type(sections) if has_sections else "flat"
        # }
        
    
    
    
    def detect_structure(self, content: str) -> Dict[str, Any]:
        """Enhanced structure detection that skips TOC sections"""
        lines = content.split('\n')
        
        # Try the improved chapter detection first for books with number + title format
        chapter_headers = self._find_chapter_number_and_title(lines)
        
        if len(chapter_headers) >= 8:  # Expect at least 8-9 chapters
            print(f"[STRUCTURE DETECTION] Using direct chapter detection: {len(chapter_headers)} chapters")
            flat_chapters = []
            
            for header in chapter_headers:
                content_text = self._extract_chapter_content(content, header, lines)
                flat_chapters.append({
                    'title': header['title'],
                    'number': header['number'],
                    'content': content_text
                })
            
            return {
                "has_sections": False,
                "sections": None,
                "chapters": flat_chapters,
                "structure_type": "flat"
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
            if in_toc_section and len(line) > 100:  # Substantial content indicates we're past TOC
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
                        "content": self._extract_section_content(content, line, lines, line_num)
                    }
                continue
            
            # Check for special sections (preface, introduction, etc.)
            special_match = self._match_special_sections(line)
            if special_match and self._has_substantial_following_content(lines, line_num):
                # Save previous section if exists
                if current_section:
                    sections.append(current_section)
                
                # Create special section
                current_section = {
                    "title": line,
                    "number": special_match["number"],
                    "type": "special",
                    "chapters": [],
                    "content": self._extract_section_content(content, line, lines, line_num)
                }
                continue
            
            # Check if line matches chapter pattern (only if we're in a section)
            if current_section:
                chapter_match = self._match_chapter_patterns(line)
                if chapter_match and self._has_substantial_following_content(lines, line_num):
                    chapter_content = self._extract_chapter_content(content, line, lines, line_num)
                    # Only add if content is substantial
                    if len(chapter_content.strip()) > 500:  # Minimum content length
                        chapter_data = {
                            "title": line,
                            "number": chapter_match["number"],
                            "content": self._extract_chapter_content(content, line, lines, line_num)
                        }
                        current_section["chapters"].append(chapter_data)
        
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
            if len(section.get('content', '').strip()) > 100:  # Minimum content threshold
                filtered_sections.append(section)
        
        # Update the sections variable to use filtered_sections
        sections = filtered_sections
            
        return {
            "has_sections": has_sections,
            "sections": sections if has_sections else None,
            "chapters": flat_chapters if not has_sections else [],
            "structure_type": self._determine_structure_type(sections) if has_sections else "flat"
        }
    

    
    def _is_toc_section(self, line: str) -> bool:
        """Check if we're entering a TOC section"""
        toc_indicators = [
            r'(?i)^contents?$',
            r'(?i)^table\s+of\s+contents?$',
            r'(?i)^contents\s+page$'
        ]
        return any(re.match(pattern, line) for pattern in toc_indicators)
    
    def _is_toc_entry(self, line: str) -> bool:
        """Check if a line is a TOC entry"""
        for pattern in self.TOC_PATTERNS:
            if re.match(pattern, line):
                return True
        return False
    
    def _has_substantial_following_content(self, lines: List[str], start_line: int, min_lines: int = 10) -> bool:
        """Check if there's substantial content following this line"""
        content_lines = 0
        total_content = ""
        
        for i in range(start_line + 1, min(len(lines), start_line + 20)):  # Check next 20 lines
            line = lines[i].strip()
            if line and not re.match(r'^\d+$', line):  # Skip page numbers
                content_lines += 1
                total_content += line + " "
                
        # Must have multiple lines and substantial text
        return content_lines >= min_lines and len(total_content.strip()) > 200
    
    def _normalize_chapter_number(self, number: str) -> str:
        """Normalize chapter numbers (convert Roman to Arabic)"""
        number = number.strip().upper()
        
        # If it's already Arabic, return as is
        if number.isdigit():
            return number
            
        # Convert Roman numerals to Arabic
        roman_to_int = {
            'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
            'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
            'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15
        }
        return str(roman_to_int.get(number, number))
    
    def _remove_duplicate_chapters(self, sections: List[Dict]) -> List[Dict]:
        """Remove duplicate chapters based on normalized numbers"""
        for section in sections:
            if 'chapters' in section:
                seen_numbers = set()
                unique_chapters = []
                
                for chapter in section['chapters']:
                    normalized_number = self._normalize_chapter_number(chapter.get('number', ''))
                    if normalized_number not in seen_numbers:
                        seen_numbers.add(normalized_number)
                        unique_chapters.append(chapter)
                    else:
                        print(f"[DUPLICATE REMOVAL] Skipping duplicate chapter {normalized_number}: {chapter['title']}")
                
                section['chapters'] = unique_chapters
        
        return sections
    
    
    
    def _extract_chapter_content(self, full_content: str, chapter_info: Dict, lines: List[str]) -> str:
        """Extract content starting after the chapter title"""
        content_lines = []
        
        # Start extraction from after the title line
        start_line = chapter_info['title_line_num'] + 1
        
        print(f"[CONTENT EXTRACTION] Extracting content for: {chapter_info['title']}")
        print(f"[CONTENT EXTRACTION] Starting from line {start_line}")
        
        for i in range(start_line, len(lines)):
            line = lines[i].strip()
            
            # Skip empty lines at the beginning
            if not content_lines and not line:
                continue
                
            # Stop if we hit another chapter number
            if re.match(r'^(\d+)$', line) and i < len(lines) - 5:
                # Check if next few lines contain a title pattern
                has_title_after = False
                for j in range(i + 1, min(i + 10, len(lines))):
                    next_line = lines[j].strip()
                    if (next_line and len(next_line) > 10 and 
                        next_line[0].isupper() and len(next_line.split()) > 2):
                        has_title_after = True
                        break
                
                if has_title_after:
                    print(f"[CONTENT EXTRACTION] Stopped at next chapter: {line}")
                    break
            
            # Skip page numbers, headers, footers
            if re.match(r'^\d+$', line) or len(line) < 3:
                continue
                
            # Stop at bibliography sections
            if line.upper() in ['NOTES', 'BIBLIOGRAPHY', 'REFERENCES', 'FOOTNOTES']:
                print(f"[CONTENT EXTRACTION] Stopped at bibliography: {line}")
                break
            
            # Add content line
            content_lines.append(line)
            
            # Mark substantial content found
            if len(line) > 30 and not re.match(r'^\d+\.', line):
                print(f"[CONTENT EXTRACTION] Found substantial content: {line[:50]}...")
        
        content = '\n'.join(content_lines).strip()
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
            number_match = re.match(r'^(\d+)$', line)
            if number_match and line_num < len(lines) - 5:  # Must have content after
                chapter_number = int(number_match.group(1))
                
                # FIX: Be more restrictive about chapter numbers
                if chapter_number > 100:  # Skip obviously wrong numbers
                    continue
                    
                # Look for title in the next few lines
                chapter_title = None
                title_line_num = None
                
                for next_line_num in range(line_num + 1, min(line_num + 10, len(lines))):
                    next_line = lines[next_line_num].strip()
                    
                    # Skip empty lines and very short lines
                    if not next_line or len(next_line) < 5:
                        continue
                        
                    # Skip page numbers or single words
                    if re.match(r'^\d+$', next_line) or len(next_line.split()) < 2:
                        continue
                    
                    # FIX: More restrictive title validation
                    if (next_line[0].isupper() and 
                        len(next_line) > 10 and 
                        len(next_line) < 100 and  # Not too long
                        not re.match(r'^\d+\.', next_line) and  # Not a footnote
                        not re.search(r'\d{4}', next_line) and  # No years (likely copyright)
                        'copyright' not in next_line.lower() and
                        'isbn' not in next_line.lower() and
                        'published' not in next_line.lower()):
                        
                        chapter_title = next_line
                        title_line_num = next_line_num
                        break
                
                # FIX: More restrictive content validation
                if (chapter_title and title_line_num and 
                    self._has_substantial_following_content(lines, title_line_num, min_lines=8) and
                    chapter_number <= 50):  # Reasonable chapter count limit
                    
                    full_title = f"Chapter {chapter_number}: {chapter_title}"
                    chapter_headers.append({
                        'line_num': line_num,
                        'title_line_num': title_line_num,
                        'title': full_title,
                        'number': chapter_number,
                        'raw_title': chapter_title
                    })
                    print(f"[CHAPTER DETECTION] Found: {full_title}")
        
        # FIX: Additional validation - check for reasonable sequence
        if len(chapter_headers) >= 3:
            numbers = [h['number'] for h in chapter_headers]
            # Should start from 1 or close to 1, and be somewhat sequential
            if min(numbers) <= 3 and max(numbers) - min(numbers) < len(numbers) * 2:
                print(f"[CHAPTER DETECTION] Validated sequence: {min(numbers)} to {max(numbers)}")
                return chapter_headers
            else:
                print(f"[CHAPTER DETECTION] Invalid sequence: {min(numbers)} to {max(numbers)}, rejecting")
                return []
        
        return chapter_headers
    
    def _is_running_header_or_footer(self, text: str) -> bool:
        """Check if text is a running header or footer"""
        text_lower = text.lower()
        
        # Common running header/footer patterns
        running_patterns = [
            r'^page \d+',  # "Page 123"
            r'^\d+ - ',    # "123 - Book Title"
            r' - \d+$',    # "Book Title - 123"
            r'^chapter \d+ - ',  # "Chapter 1 - Title"
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
                    if self._has_substantial_following_content(lines, line_num, min_lines=5):
                        chapter_headers.append({
                            'line_num': line_num,
                            'title': line,
                            'number': match.group(1),
                            'pattern': pattern
                        })
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
                    "type": self._get_section_type(pattern)
                }
        return None
    
    def _match_special_sections(self, line: str) -> Optional[Dict]:
        """Match line against special section patterns"""
        # Add tracking for already processed special sections
        if not hasattr(self, '_processed_specials'):
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
                    "title": match.group(1).strip() if len(match.groups()) > 0 else match.group(0).strip(),
                    "type": "special"
                }
        return None



    def _match_chapter_patterns(self, line: str) -> Optional[Dict]:
        """Match line against chapter patterns"""
        for pattern in self.CHAPTER_PATTERNS:
            match = re.match(pattern, line)
            if match:
                return {
                    "number": match.group(1),
                    "title": match.group(2).strip() if len(match.groups()) > 1 else ""
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

    def _extract_section_content(self, full_content: str, section_title: str, lines: List[str], start_line: int) -> str:
        """Extract content for a specific section"""
        content_lines = []
        
        # Start from the line after the section title
        for i in range(start_line + 1, len(lines)):
            line = lines[i].strip()
            
            # Stop if we hit another section
            if (self._match_section_patterns(line) or 
                self._match_special_sections(line)):
                break
                
            content_lines.append(line)
        
        return '\n'.join(content_lines).strip()

    


    def _extract_flat_chapters(self, content: str) -> List[Dict]:
        """Extract chapters when no hierarchical structure is detected"""
        lines = content.split('\n')
        chapters = []
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            chapter_match = self._match_chapter_patterns(line)
            if chapter_match:
                 # FIX: Create chapter_info dict for the new method
                chapter_info = {
                    'title': line,
                    'title_line_num': line_num,
                    'line_num': line_num,
                    'number': chapter_match['number'],
                    'raw_title': line
                }
                extracted_content = self._extract_chapter_content(content, chapter_info, lines)
                
                # Add content validation before adding chapters
                if len(extracted_content.strip()) > 200:  # Only add chapters with substantial content
                    chapter_data = {
                        "title": line,
                        "number": chapter_match["number"],
                        "content": extracted_content
                    }
                    chapters.append(chapter_data)
                    print(f"DEBUG: Added flat chapter with {len(extracted_content)} characters: {line}")
                else:
                    print(f"DEBUG: Skipped short chapter ({len(extracted_content)} chars): {line}")
        
        
        return chapters
    
    def _analyze_content_for_structure(self, sections: List[Dict], structure_type: str) -> int:
        """Analyze section content with null safety"""
        score = 0
        content_indicators = {
            'tablet': ['gilgamesh', 'enkidu', 'uruk', 'flood', 'immortality', 'mesopotamia'],
            'book': ['chapter', 'prologue', 'epilogue', 'narrative', 'story'],
            'part': ['introduction', 'conclusion', 'overview', 'summary'],
            'act': ['dialogue', 'stage', 'enter', 'exit', 'scene'],
            'movement': ['tempo', 'allegro', 'adagio', 'musical', 'notes'],
            'canto': ['verse', 'stanza', 'rhyme', 'meter', 'epic']
        }
        
        if structure_type not in content_indicators:
            return 0
        
        indicators = content_indicators[structure_type]
        
        for section in sections:
            if not isinstance(section, dict):
                continue
            
            # FIX: Add null safety for content and title
            content_str = ""
            section_content = section.get('content')
            section_title = section.get('title')
            
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
        
    
     
    async def _extract_content_for_chapters_by_pages(self, validated_chapters: List[Dict], doc) -> List[Dict[str, Any]]:
        """Extract chapter content based on page numbers from TOC - with section awareness"""
        print("[PAGE EXTRACTION] Extracting content using page numbers from TOC...")
        
        final_chapters = []
        
        # Group chapters by section for better processing
        sections_map = {}
        for chapter in validated_chapters:
            section_title = chapter.get('section_title', 'No Section')
            if section_title not in sections_map:
                sections_map[section_title] = []
            sections_map[section_title].append(chapter)
        
        print(f"[PAGE EXTRACTION] Found {len(sections_map)} sections")
        
        # Process each section separately
        for section_title, section_chapters in sections_map.items():
            print(f"[PAGE EXTRACTION] Processing section: {section_title} ({len(section_chapters)} chapters)")
            
            # Sort chapters in this section by page number
            sorted_chapters = sorted(section_chapters, key=lambda x: x.get('page_hint', 999999))
            
            for i, chapter in enumerate(sorted_chapters):
                chapter_title = chapter['title']
                start_page = chapter.get('page_hint', 1)
                
                if start_page is None or start_page < 1:
                    print(f"[PAGE EXTRACTION] Invalid page number for: {chapter_title}")
                    continue
                
                # Convert to 0-based index
                start_page_idx = start_page - 1
                
                # Determine end page - look for next chapter in SAME section
                end_page_idx = len(doc) - 1  # Default to end of document
                
                if i + 1 < len(sorted_chapters):
                    next_chapter = sorted_chapters[i + 1]
                    next_start_page = next_chapter.get('page_hint')
                    if next_start_page and next_start_page > start_page:
                        end_page_idx = next_start_page - 2
                    else:
                        end_page_idx = min(start_page_idx + 20, len(doc) - 1)
                else:
                    # Last chapter in section - look for next section's first chapter
                    next_section_start = self._find_next_section_start_page(
                        section_title, sections_map, sorted_chapters[-1].get('page_hint', start_page)
                    )
                    if next_section_start:
                        end_page_idx = next_section_start - 2
                    else:
                        end_page_idx = min(start_page_idx + 30, len(doc) - 1)
                
                # Validate page range
                if start_page_idx >= end_page_idx:
                    print(f"[PAGE EXTRACTION] Invalid page range for {chapter_title}: {start_page} to {end_page_idx + 1}")
                    end_page_idx = min(start_page_idx + 10, len(doc) - 1)
                
                print(f"[PAGE EXTRACTION] {chapter_title}: pages {start_page} to {end_page_idx + 1}")
                
                # Extract content from page range
                chapter_content = ""
                actual_start = max(0, start_page_idx)
                actual_end = min(len(doc) - 1, end_page_idx)
                
                for page_idx in range(actual_start, actual_end + 1):
                    try:
                        page = doc[page_idx]
                        page_text = page.get_text()
                        chapter_content += page_text + "\n"
                    except Exception as e:
                        print(f"[PAGE EXTRACTION] Error reading page {page_idx}: {e}")
                        continue
                
                # Clean and validate content
                cleaned_content = self._clean_extracted_content(chapter_content, chapter_title)
                
                if len(cleaned_content.strip()) > 500:
                    final_chapters.append({
                        'title': chapter_title,
                        'content': cleaned_content,
                        'summary': f"Content for {chapter_title}",
                        'chapter_number': chapter.get('number', i + 1),
                        'page_range': f"{start_page}-{end_page_idx + 1}",
                        'extraction_method': 'page_based',
                        # Keep section information
                        'section_title': chapter.get('section_title'),
                        'section_type': chapter.get('section_type'),
                        'section_number': chapter.get('section_number'),
                    })
                    print(f"[PAGE EXTRACTION] ✅ Extracted {len(cleaned_content)} chars from pages {start_page}-{end_page_idx + 1}")
                else:
                    print(f"[PAGE EXTRACTION] ❌ Insufficient content from pages {start_page}-{end_page_idx + 1}")
        
        return final_chapters
    
    def _find_next_section_start_page(self, current_section: str, sections_map: dict, current_page: int) -> Optional[int]:
        """Find the starting page of the next section"""
        section_names = list(sections_map.keys())
        try:
            current_idx = section_names.index(current_section)
            if current_idx + 1 < len(section_names):
                next_section = section_names[current_idx + 1]
                next_section_chapters = sections_map[next_section]
                if next_section_chapters:
                    return min(ch.get('page_hint', 999999) for ch in next_section_chapters if ch.get('page_hint'))
        except (ValueError, IndexError):
            pass
        return None
    

    
    
    def _clean_extracted_content(self, content: str, chapter_title: str) -> str:
        """Clean content extracted from page ranges"""
        if not content:
            return ""
        
        lines = content.split('\n')
        cleaned_lines = []
        
        # Remove the chapter title from the beginning if it appears
        clean_title = chapter_title.split(':', 1)[-1].strip() if ':' in chapter_title else chapter_title
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip empty lines at the beginning
            if not cleaned_lines and not line_stripped:
                continue
            
            # Skip the chapter title line if it appears at the start
            if not cleaned_lines and clean_title.lower() in line_stripped.lower():
                continue
            
            # Skip page numbers and headers/footers
            if (re.match(r'^\d+$', line_stripped) or  # Just page numbers
                re.match(r'^[ivxlcdm]+$', line_stripped.lower()) or  # Roman numerals
                len(line_stripped) < 3 or  # Very short lines
                self._is_running_header_or_footer(line_stripped)):
                continue
            
            cleaned_lines.append(line)
        
        # Join and clean up excessive whitespace
        result = '\n'.join(cleaned_lines)
        result = re.sub(r'\n{3,}', '\n\n', result)  # Max 2 consecutive newlines
        
        return result.strip()
    
   
    

    def convert_roman_to_int(self, roman: str) -> int:
        """Convert Roman numerals to integers"""
        roman_values = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50, 
            'C': 100, 'D': 500, 'M': 1000
        }
        
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
            section_type = s.get('section_type')
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
                section_title = section.get('title')
                if section_title and isinstance(section_title, str):
                    section_title_lower = section_title.lower()
                    for indicator in config['indicators']:
                        if indicator in section_title_lower:
                            score += 3
            
            # 3. Count-based scoring
            min_count, max_count = config['typical_count']
            if min_count <= section_count <= max_count:
                score += 5
            elif section_count < min_count:
                score += 2
            
            # 4. Content analysis scoring with null safety
            try:
                content_score = self._analyze_content_for_structure(sections, structure_name)
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
                print(f"[STRUCTURE DETECTION] Detected structure: {best_structure[0]} (score: {best_structure[1]})")
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
            'flat': {
                'display_name': 'Simple Chapters',
                'icon': '📖',
                'description': 'Traditional chapter-based structure',
                'section_label': None,
                'chapter_label': 'Chapter'
            },
            'hierarchical': {
                'display_name': 'Multi-Level Structure',
                'icon': '🏗️',
                'description': 'Book with sections and subsections',
                'section_label': 'Section',
                'chapter_label': 'Chapter'
            },
            'tablet': {
                'display_name': 'Tablet Structure',
                'icon': '🏺',
                'description': 'Ancient text organized in tablets',
                'section_label': 'Tablet',
                'chapter_label': 'Section'
            },
            'book': {
                'display_name': 'Book Structure',
                'icon': '📚',
                'description': 'Multiple books within a larger work',
                'section_label': 'Book',
                'chapter_label': 'Chapter'
            },
            'part': {
                'display_name': 'Part Structure',
                'icon': '📋',
                'description': 'Organized into distinct parts',
                'section_label': 'Part',
                'chapter_label': 'Chapter'
            },
            'act': {
                'display_name': 'Theatrical Structure',
                'icon': '🎭',
                'description': 'Drama organized in acts and scenes',
                'section_label': 'Act',
                'chapter_label': 'Scene'
            },
            'movement': {
                'display_name': 'Musical Structure',
                'icon': '🎵',
                'description': 'Musical work with movements',
                'section_label': 'Movement',
                'chapter_label': 'Section'
            },
            'canto': {
                'display_name': 'Epic Structure',
                'icon': '📜',
                'description': 'Epic poem organized in cantos',
                'section_label': 'Canto',
                'chapter_label': 'Verse'
            }
        }
        
        return metadata.get(structure_type, metadata['hierarchical'])



class FileService:
    """File processing service for book uploads"""
    MAX_CHAPTERS = 50
    ROMAN_RE = r'[IVXLCDM]+'
    ROMAN_RE_LOWER = r'[ivxlcdm]+'  
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        # Initialize a new Supabase client with the service role key for backend operations
        self.db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        self.ai_service = AIService()
        self.structure_detector = BookStructureDetector()
        os.makedirs(self.upload_dir, exist_ok=True)
    
    # async def process_uploaded_book(
    #     self,
    #     storage_path: Optional[str],
    #     original_filename: Optional[str],
    #     text_content: Optional[str],
    #     book_type: str,
    #     user_id: str,
    #     book_id_to_update: str,
    # ) -> None:
    #     """Process uploaded book and create chapters with embeddings"""
    #     try:
    #         # Extract text content
    #         if text_content:
    #             content = text_content
    #         elif storage_path:
    #             # Download file from Supabase Storage to a temporary location
    #             with tempfile.NamedTemporaryFile(delete=False, suffix=original_filename) as temp_file:
    #                 file_content = self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).download(path=storage_path)
    #                 temp_file.write(file_content)
    #                 temp_file_path = temp_file.name

    #             extracted_data = self.process_book_file(temp_file_path, original_filename, user_id)
    #             content = extracted_data.get("text", "")
    #             author_name = extracted_data.get("author")
    #             cover_image_url = extracted_data.get("cover_image_url")

    #             # Clean up temporary file
    #             os.unlink(temp_file_path)
    #         else:
    #             raise ValueError("No content provided")

    #         # Update book with extracted content
    #         # Clean the content to handle Unicode escape sequences
    #         cleaned_content = self._clean_text_content(content)
            
    #         self.db.table("books").update({
    #             "content": cleaned_content,
    #             "status": "PROCESSING",
    #             "cover_image_url": cover_image_url
    #         }).eq("id", book_id_to_update).execute()

    #         # NEW FLOW: Extract chapters following the specified order
    #         chapters = await self.extract_chapters_with_new_flow(content, book_type, original_filename, storage_path)
            
    #         # Create sections and chapters in database
    #         # section_id_map = {}  # Map section titles to section IDs
    #         section_id_map: Dict[str, str] = {}  # section key -> section id

            
    #         for i, chapter_data in enumerate(chapters):
    #             section_id = None
                
    #             # If chapter has section data, create or get section
    #             if "section_title" in chapter_data:
    #                 # section_key = f"{chapter_data['section_title']}_{chapter_data.get('section_type', '')}"
    #                 section_key = f"{chapter_data.get('section_title','')}|{chapter_data.get('section_type','')}|{chapter_data.get('section_number','')}"
            
                    
    #                 # if section_key not in section_id_map:
    #                 #     # Create new section
    #                 #     section_insert_data = {
    #                 #         "book_id": book_id_to_update,
    #                 #         "title": chapter_data["section_title"],
    #                 #         "section_type": chapter_data.get("section_type", ""),
    #                 #         "section_number": chapter_data.get("section_number", ""),
    #                 #         "order_index": chapter_data.get("section_order", i + 1)
    #                 #     }
                        
    #                 #     section_response = self.db.table("book_sections").insert(section_insert_data).execute()
    #                 #     section_id = section_response.data[0]["id"]
    #                 #     section_id_map[section_key] = section_id
    #                 # else:
    #                 #     section_id = section_id_map[section_key]
                    
                    
    #                 if section_key not in section_id_map:
    #                         section_insert = {
    #                             "book_id": book_id_to_update,
    #                             "title": chapter_data.get("section_title", ""),
    #                             "section_type": chapter_data.get("section_type", "part"),   # book|part|section
    #                             "section_number": chapter_data.get("section_number", ""),
    #                             "order_index": len(section_id_map) + 1,
    #                         }
    #                         resp = self.db.table("book_sections").insert(section_insert).execute()
    #                         section_id_map[section_key] = resp.data[0]["id"]
    #                 section_id = section_id_map[section_key]
                    
    #             # Build chapter data
    #             chapter_insert_data = {
    #                 "book_id": book_id_to_update,
    #                 "chapter_number": chapter_data.get("chapter_number", chapter_data.get("number") or i + 1),
    #                 "title": chapter_data["title"],
    #                 "content": self._clean_text_content(chapter_data.get("content", "")),
    #                 "summary": self._clean_text_content(chapter_data.get("summary", "")),
    #                 "order_index": chapter_data.get("chapter_number", chapter_data.get("number") or i + 1),
    #             }
    #             if section_id:
    #                 chapter_insert_data["section_id"] = section_id

    #             # Insert chapter
    #             chapter_response = self.db.table("chapters").insert(chapter_insert_data).execute()
    #             chapter_id = chapter_response.data[0]["id"]

    #             # Create embeddings for the chapter (best-effort)
    #             try:
    #                 from app.services.embeddings_service import EmbeddingsService
    #                 embeddings_service = EmbeddingsService(self.db)
    #                 await embeddings_service.create_chapter_embeddings(chapter_id, chapter_insert_data["content"])
    #             except Exception as e:
    #                 print(f"Failed to create embeddings for chapter {chapter_id}: {e}")

    #         # Mark book as hierarchical if sections were created
    #         self.db.table("books").update({
    #             "has_sections": bool(section_id_map),
    #             "structure_type": "hierarchical" if section_id_map else "flat",
    #             "status": "READY",
    #             "total_chapters": len(chapters)
    #         }).eq("id", book_id_to_update).execute()

                
    #             # # Create chapter
    #             # chapter_insert_data = {
    #             #     "book_id": book_id_to_update,
    #             #     "chapter_number": chapter_data.get("chapter_number", i + 1),
    #             #     "title": chapter_data["title"],
    #             #     "content": self._clean_text_content(chapter_data["content"]),
    #             #     "summary": self._clean_text_content(chapter_data.get("summary", "")),
    #             #     "order_index": chapter_data.get("chapter_number", i + 1)
    #             # }
                
    #             # # Add section_id if chapter belongs to a section
    #             # if section_id:
    #             #     chapter_insert_data["section_id"] = section_id
                
    #             # # Insert chapter
    #             # chapter_response = self.db.table("chapters").insert(chapter_insert_data).execute()
    #             # chapter_id = chapter_response.data[0]["id"]
                
    #             # # Create embeddings for the chapter
    #             # try:
    #             #     from app.services.embeddings_service import EmbeddingsService
    #             #     embeddings_service = EmbeddingsService(self.db)
    #             #     await embeddings_service.create_chapter_embeddings(
    #             #         chapter_id=chapter_id,
    #             #         content=chapter_data["content"]
    #             #     )
    #             # except Exception as e:
    #             #     print(f"Failed to create embeddings for chapter {chapter_id}: {e}")

    #         # Create book-level embeddings
    #         try:
    #             from app.services.embeddings_service import EmbeddingsService
    #             embeddings_service = EmbeddingsService(self.db)
                
    #             # Get book data for embeddings
    #             book_response = self.db.table("books").select("*").eq("id", book_id_to_update).single().execute()
    #             book_data = book_response.data
                
    #             await embeddings_service.create_book_embeddings(
    #                 book_id=book_id_to_update,
    #                 title=book_data["title"],
    #                 description=book_data.get("description"),
    #                 content=content
    #             )
    #         except Exception as e:
    #             print(f"Failed to create book embeddings: {e}")

    #         # Update book status to completed
    #         self.db.table("books").update({
    #             "status": "READY",
    #             "total_chapters": len(chapters)
    #         }).eq("id", book_id_to_update).execute()

    #     except Exception as e:
    #         # Update book status to failed
    #         self.db.table("books").update({
    #             "status": "FAILED"
    #         }).eq("id", book_id_to_update).execute()
    #         raise e
    
    
        
    def _extract_chapter_content(self, full_content: str, chapter_title: str, lines: List[str], start_line: int) -> str:
        """Wrapper method to call BookStructureDetector's _extract_chapter_content"""
        # Create a chapter_info dict for the new method
        chapter_info = {
            'title': chapter_title,
            'title_line_num': start_line,  # Use start_line as title line
            'line_num': start_line - 1 if start_line > 0 else 0,
            'number': '1',  # Default number
            'raw_title': chapter_title
        }
        
        # Call the new method in BookStructureDetector
        return self.structure_detector._extract_chapter_content(full_content, chapter_info, lines)
        
        # return self.structure_detector._extract_chapter_content(full_content, chapter_title, lines, start_line)

    def process_book_file(self, file_path: str, filename: str, user_id: str = None) -> Dict[str, Any]:
        """Process different file types and extract content"""
        try:
            if filename.lower().endswith('.pdf'):
                return self.process_pdf(file_path, user_id)
            elif filename.lower().endswith('.docx'):
                return self.process_docx(file_path, user_id)
            elif filename.lower().endswith('.txt'):
                return self.process_txt(file_path, user_id)
            else:
                raise ValueError(f"Unsupported file type: {filename}")
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            raise

    def process_pdf(self, file_path: str, user_id: str = None) -> Dict[str, Any]:
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
            if metadata and metadata.get('author'):
                author = metadata['author']
            
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
                        storage_path = f"users/{user_id}/covers/cover_{int(time.time())}.png"
                        self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                            path=storage_path,
                            file=img_buffer.getvalue(),
                            file_options={"content-type": "image/png"}
                        )
                        
                        # Get the public URL
                        cover_image_url = self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(storage_path)
                        print(f"[COVER EXTRACTION] Cover image uploaded: {cover_image_url}")
                        
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
                            storage_path = f"users/{user_id}/covers/cover_{int(time.time())}.png"
                            self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                                path=storage_path,
                                file=img_buffer.getvalue(),
                                file_options={"content-type": "image/png"}
                            )
                            
                            cover_image_url = self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(storage_path)
                            print(f"[COVER EXTRACTION] Fallback cover image uploaded: {cover_image_url}")
                            
                        except Exception as fallback_error:
                            print(f"[COVER EXTRACTION] Fallback method also failed: {fallback_error}")
                            cover_image_url = None
                    
                    else:
                        print("[COVER EXTRACTION] No images found on first page")
                except Exception as e:
                    print(f"[COVER EXTRACTION] Error extracting cover: {e}")
            
            doc.close()
            
            return {
                "text": text,
                "author": author,
                "cover_image_url": cover_image_url
            }
        except Exception as e:
            print(f"Error processing PDF: {e}")
            raise

    def process_docx(self, file_path: str, user_id: str = None) -> Dict[str, Any]:
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
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        image_files = [f for f in zip_ref.namelist() if f.startswith('word/media/') and f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
                        
                        if image_files:
                            # Get the first image
                            first_image = image_files[0]
                            with zip_ref.open(first_image) as image_file:
                                img_data = image_file.read()
                                
                                # Upload to Supabase Storage under user folder
                                storage_path = f"users/{user_id}/covers/cover_{int(time.time())}.png"
                                self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                                    path=storage_path,
                                    file=img_data,
                                    file_options={"content-type": "image/png"}
                                )
                                
                                # Get the public URL
                                cover_image_url = self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(storage_path)
                                print(f"[COVER EXTRACTION] Cover image uploaded: {cover_image_url}")
                except Exception as e:
                    print(f"[COVER EXTRACTION] Error extracting cover from DOCX: {e}")
            
            return {
                "text": text,
                "author": None,
                "cover_image_url": cover_image_url
            }
        except Exception as e:
            print(f"Error processing DOCX: {e}")
            raise

    def process_txt(self, file_path: str, user_id: str = None) -> Dict[str, Any]:
        """Extract text from TXT (no cover image)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            
            return {
                "text": text,
                "author": None,
                "cover_image_url": None
            }
        except Exception as e:
            print(f"Error processing TXT: {e}")
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
            content = content.replace('\\n', '\n')
            content = content.replace('\\t', '\t')
            content = content.replace('\\r', '\r')
            content = content.replace('\\"', '"')
            content = content.replace("\\'", "'")
            
            # Remove any remaining backslash escapes
            import re
            content = re.sub(r'\\(.)', r'\1', content)
            
            return content.strip()

    def _is_duplicate_chapter(self, new_chapter: Dict[str, Any], existing_chapters: List[Dict[str, Any]], similarity_threshold: float = 0.8) -> bool:
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
                shorter_content = new_content if len(new_content) < len(existing_content) else existing_content
                longer_content = existing_content if len(new_content) < len(existing_content) else new_content
                
                # If shorter content is mostly contained in longer content, it's likely a duplicate
                if len(shorter_content) / len(longer_content) > similarity_threshold:
                    # Check if there's significant overlap
                    overlap_ratio = len(set(shorter_content.split()) & set(longer_content.split())) / len(set(shorter_content.split()))
                    if overlap_ratio > similarity_threshold:
                        return True
        
        return False

    def extract_learning_chapters(self, content: str) -> List[Dict[str, Any]]:
        """Extract chapters for learning content (max 50) with duplicate filtering"""
        patterns = [
            r'CHAPTER\s+\d+\.?\s*([^\n]+)',
            r'Chapter\s+\d+\.?\s*([^\n]+)',
            r'CHAPTER\s+\w+\s*([^\n]*)',
            r'Chapter\s+\w+\s*([^\n]*)',
            r'CHAPTER\s+\d+[:\s]*([^\n]+)',
            r'Chapter\s+\d+[:\s]*([^\n]+)',
            r'CHAPTER\s+\w+[:\s]*([^\n]+)',
            r'Chapter\s+\w+[:\s]*([^\n]+)',
            r'Lesson\s+\d+[:\s]*([^\n]+)',
            r'Unit\s+\d+[:\s]*([^\n]+)',
            r'Section\s+\d+[:\s]*([^\n]+)',
            r'Part\s+\d+[:\s]*([^\n]+)',
            r'CHAPTER\s+([A-Z]+)\b',
            r'Chapter\s+([A-Z][a-z]+)\b',
        ]
        chapters = []
        lines = content.split('\n')
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
                    title = match.group(1).strip() if match.lastindex and match.group(1).strip() else ""
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
                        chapter_start_line = i - current_chapter["content"].count('\n')
                        chapter_content = self._extract_chapter_content(
                            content, 
                            current_chapter["title"], 
                            lines, 
                            chapter_start_line
                        )
                        current_chapter["content"] = chapter_content
                        
                        # Only add chapter if it has meaningful content
                        if len(chapter_content.strip()) > 50:  # Minimum content length
                            if not self._is_duplicate_chapter(current_chapter, chapters):
                                chapters.append(current_chapter)
                                print(f"DEBUG: Added learning chapter: {current_chapter['title']}")
                                print(f"DEBUG: Chapter content length: {len(current_chapter.get('content', ''))}")
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
                        "summary": ""
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
            chapter_start_line = len(lines) - current_chapter["content"].count('\n')
            chapter_content = self._extract_chapter_content(
                content, 
                current_chapter["title"], 
                lines, 
                chapter_start_line
            )
            current_chapter["content"] = chapter_content
            
            # Only add final chapter if it has meaningful content
            if len(chapter_content.strip()) > 50:  # Minimum content length
                if not self._is_duplicate_chapter(current_chapter, chapters):
                    chapters.append(current_chapter)
                    print(f"DEBUG: Added final learning chapter: {current_chapter['title']}")

        if not chapters:
            chapters = [{
                "title": "Complete Content",
                "content": content,
                "summary": ""
            }]
        print(f"DEBUG: Total chapters extracted: {len(chapters)}")
        return chapters[:self.MAX_CHAPTERS]

    def extract_entertainment_chapters(self, content: str) -> List[Dict[str, Any]]:
        """Extract chapters for entertainment content (max 50) with duplicate filtering"""
        patterns = [
            r'CHAPTER\s+\d+\.?\s*([^\n]+)',
            r'Chapter\s+\d+\.?\s*([^\n]+)',
            r'CHAPTER\s+\w+\s*([^\n]*)',
            r'Chapter\s+\w+\s*([^\n]*)',
            r'CHAPTER\s+\d+[:\s]*([^\n]+)',
            r'Chapter\s+\d+[:\s]*([^\n]+)',
            r'CHAPTER\s+\w+[:\s]*([^\n]+)',
            r'Chapter\s+\w+[:\s]*([^\n]+)',
            r'Scene\s+\d+[:\s]*([^\n]+)',
            r'Act\s+\d+[:\s]*([^\n]+)',
            r'Part\s+\d+[:\s]*([^\n]+)',
            r'Book\s+\d+[:\s]*([^\n]+)',
            r'CHAPTER\s+([A-Z]+)\b',
            r'Chapter\s+([A-Z][a-z]+)\b',
        ]
        chapters = []
        lines = content.split('\n')
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
                    title = match.group(1).strip() if match.lastindex and match.group(1).strip() else ""
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
                        chapter_start_line = i - current_chapter["content"].count('\n')
                        chapter_content = self._extract_chapter_content(
                            content, 
                            current_chapter["title"], 
                            lines, 
                            chapter_start_line
                        )
                        current_chapter["content"] = chapter_content
                        
                        # Only add chapter if it has meaningful content
                        if len(chapter_content.strip()) > 50:  # Minimum content length
                            if not self._is_duplicate_chapter(current_chapter, chapters):
                                chapters.append(current_chapter)
                                print(f"DEBUG: Added entertainment chapter: {current_chapter['title']}")
                                print(f"DEBUG: Chapter content length: {len(current_chapter.get('content', ''))}")
                                if len(chapters) >= self.MAX_CHAPTERS:
                                    break

                    current_chapter = {
                        "title": title,
                        "content": line + "\n",
                        "summary": ""
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
            chapter_start_line = len(lines) - current_chapter["content"].count('\n')
            chapter_content = self._extract_chapter_content(
                content, 
                current_chapter["title"], 
                lines, 
                chapter_start_line
            )
            current_chapter["content"] = chapter_content
            
            # Only add final chapter if it has meaningful content
            if len(chapter_content.strip()) > 50:  # Minimum content length
                if not self._is_duplicate_chapter(current_chapter, chapters):
                    chapters.append(current_chapter)
                    print(f"DEBUG: Added final entertainment chapter: {current_chapter['title']}")

        if not chapters:
            chapters = [{
                "title": "Complete Story",
                "content": content,
                "summary": ""
            }]
        print(f"DEBUG: Total chapters extracted: {len(chapters)}")
        return chapters[:self.MAX_CHAPTERS]

    
    async def extract_chapters_from_pdf_with_toc(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        """Enhanced TOC extraction that looks for actual table of contents in text"""
        try:
            doc = fitz.open(file_path)
            
            # Method 1: Try PDF bookmarks first
            toc = doc.get_toc()
            if toc:
                print(f"[TOC EXTRACTION] Found PDF bookmarks: {len(toc)} entries")
                chapters = self._process_pdf_bookmarks(doc, toc)
                if chapters:
                    doc.close()
                    return chapters
            
            # Method 2: Search for TOC in document text
            print("[TOC EXTRACTION] Searching for TOC in document text...")
            chapters = await self._extract_toc_from_text(doc)
            if chapters:
                doc.close()
                return chapters
                
            doc.close()
            return []
            
        except Exception as e:
            print(f"[TOC EXTRACTION] Error: {e}")
            return []
        
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
                chapters.append({
                    "title": title.strip(),
                    "content": chapter_text.strip(),
                    "summary": "",
                    "chapter_number": i + 1
                })
        
        print(f"[TOC EXTRACTION] Processed {len(chapters)} chapters from bookmarks")
        return chapters
    
    async def _parse_toc_with_ai(self, toc_text: str, doc) -> List[Dict[str, Any]]:
        """Step 2: Use AI to extract chapter titles from TOC text"""
        print("[TOC PARSING] Using AI to extract chapter titles from TOC...")
        
        try:
            prompt = f"""
            Extract ONLY the main chapter titles from this table of contents. Look for entries that follow the pattern:
            "CHAPTER X. Title Name PageNumber"
            
            IGNORE:
            - List of Illustrations
            - List of Figures  
            - Preface
            - Bibliography
            - Index
            - Page headers
            
            TOC Text:
            {toc_text[:3000]}
            
            Return JSON with ONLY main chapters:
            {{
                "chapters": [
                    {{"title": "Chapter 1: Introduction to Angel Magic", "estimated_page": 1}},
                    {{"title": "Chapter 2: The Source of Angel Magic", "estimated_page": 23}}
                ]
            }}
            """
            
            response = await self.ai_service.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            
            if 'chapters' in result:
                print(f"[TOC PARSING] AI extracted {len(result['chapters'])} chapter titles")
                # Print what AI found
                for ch in result['chapters']:
                    print(f"[TOC PARSING] AI found: {ch['title']}")
                
                return await self._validate_chapters_exist_in_book(result['chapters'], doc)
            
        except Exception as e:
            print(f"[TOC PARSING] AI extraction failed: {e}")
        
        return []
    
    
    async def _validate_chapters_exist_in_book(self, chapter_titles: List[Dict], doc) -> List[Dict[str, Any]]:
        """Step 3: FIXED - More thorough validation that checks more of the book content"""
        print("[CHAPTER VALIDATION] Validating chapters exist in book...")
        
        # Get MORE book text for validation (not just first 5000 chars)
        full_text = ""
        sample_pages = min(50, len(doc))  # Check first 50 pages instead of just 5000 chars
        for i in range(sample_pages):
            full_text += doc[i].get_text()
        
        try:
            # Prepare chapter list for validation
            titles_to_validate = [ch['title'] for ch in chapter_titles]
            
            prompt = f"""
            I extracted these {len(chapter_titles)} chapter titles from a table of contents. Please check if these chapters actually exist in the book content.
            
            IMPORTANT: Look for chapter headings, not just keywords. A chapter exists if you find text like "CHAPTER X" or "Chapter X:" in the content.
            
            Extracted Chapters:
            {json.dumps(titles_to_validate)}
            
            Book Content (first 10000 chars from 50 pages):
            {full_text[:10000]}
            
            Return JSON with chapters that actually exist in the book. BE GENEROUS - if you find any evidence of a chapter, include it:
            {{
                "validated_chapters": [
                    {{"title": "Chapter 1: Introduction", "confidence": 0.95}},
                    {{"title": "Chapter 2: History", "confidence": 0.87}}
                ],
                "reasoning": "Found Chapter 1 and 2 headings in the text"
            }}
            """
            
            response = await self.ai_service.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,  # Increased token limit
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            
            if 'validated_chapters' in result:
                validated_count = len(result['validated_chapters'])
                print(f"[CHAPTER VALIDATION] AI validated {validated_count} chapters out of {len(chapter_titles)}")
                print(f"[CHAPTER VALIDATION] Reasoning: {result.get('reasoning', '')}")
                
                # If AI validates at least 50% of chapters, proceed with content extraction
                if validated_count >= len(chapter_titles) * 0.5:
                    return await self._extract_content_for_chapters(result['validated_chapters'], full_text)
                else:
                    print(f"[CHAPTER VALIDATION] Too few chapters validated ({validated_count}/{len(chapter_titles)}), using all TOC chapters")
                    # Use all TOC chapters if AI validation is too restrictive
                    return await self._extract_content_for_chapters(chapter_titles, full_text)
            
        except Exception as e:
            print(f"[CHAPTER VALIDATION] Validation failed: {e}")
        
        return []
    
    async def _extract_content_for_chapters(self, validated_chapters: List[Dict], full_text: str) -> List[Dict[str, Any]]:
        """Step 4: Extract content by searching for chapter titles in the text"""
        print("[CONTENT EXTRACTION] Extracting content by searching chapter titles...")
        
        final_chapters = []
        
        for i, chapter in enumerate(validated_chapters):
            chapter_title = chapter['title']
            print(f"[CONTENT EXTRACTION] Extracting content for: {chapter_title}")
            
            # Search for chapter title in text (flexible matching)
            chapter_patterns = [
                re.escape(chapter_title),  # Exact match
                re.escape(chapter_title.replace('Chapter ', '').replace(':', '')),  # Without "Chapter" prefix
                re.escape(chapter_title.split(':')[-1].strip()) if ':' in chapter_title else None,  # Just the title part
            ]
            
            content_start = None
            for pattern in chapter_patterns:
                if pattern:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        content_start = match.end()
                        print(f"[CONTENT EXTRACTION] Found chapter start at position {content_start}")
                        break
            
            if content_start is None:
                print(f"[CONTENT EXTRACTION] Could not find chapter: {chapter_title}")
                continue
            
            # Find content end (start of next chapter or end of book)
            content_end = len(full_text)
            if i + 1 < len(validated_chapters):
                next_chapter = validated_chapters[i + 1]['title']
                next_match = re.search(re.escape(next_chapter), full_text[content_start:], re.IGNORECASE)
                if next_match:
                    content_end = content_start + next_match.start()
            
            # Extract content
            content = full_text[content_start:content_end].strip()
            
            if len(content) > 200:
                # Validate first 200 characters with AI
                is_valid = await self._validate_content_match(chapter_title, content[:200])
                if is_valid:
                    final_chapters.append({
                        'title': chapter_title,
                        'content': content,
                        'summary': f"Content for {chapter_title}",
                        'chapter_number': i + 1
                    })
                    print(f"[CONTENT EXTRACTION] Successfully extracted {len(content)} chars for: {chapter_title}")
                else:
                    print(f"[CONTENT EXTRACTION] Content validation failed for: {chapter_title}")
            else:
                print(f"[CONTENT EXTRACTION] Insufficient content for: {chapter_title}")
        
        return final_chapters

    async def _validate_content_match(self, chapter_title: str, content_preview: str) -> bool:
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
            
            response = await self.ai_service.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            matches = result.get('matches', False)
            confidence = result.get('confidence', 0.0)
            
            print(f"[CONTENT VALIDATION] Match: {matches}, Confidence: {confidence}")
            return matches and confidence > 0.7
            
        except Exception as e:
            print(f"[CONTENT VALIDATION] Validation failed: {e}")
            return True  # Default to accepting if validation fails
        
    

    
    
    # async def _extract_toc_from_text(self, doc) -> List[Dict[str, Any]]:
    #     """Step 1: Extract TOC by finding ALL  chapter entries across multiple pages"""
    #     print("[TOC EXTRACTION] Searching for table of contents...")
        
    #     all_chapters = []
        
    #     # Search first 25 pages for ANY chapter entries
    #     for page_num in range(min(25, len(doc))):
    #         page = doc[page_num]
    #         text = page.get_text()
            
    #         print(f"[TOC EXTRACTION] Checking page {page_num + 1}...")
            
    #         # Look for chapter entries REGARDLESS of "Contents" header
    #         chapter_patterns = [
    #             r'CHAPTER\s+(\d+)\.\s+(.+?)\s+(\d+)',  # "CHAPTER 1. Title 123"
    #             r'Chapter\s+(\d+)[\.\s]+(.+?)\s+(\d+)', # "Chapter 1. Title 123"
    #         ]
            
    #         page_chapters = []
    #         for pattern in chapter_patterns:
    #             matches = re.findall(pattern, text, re.MULTILINE)
    #             for match in matches:
    #                 chapter_num, title, page_str = match
                    
    #                 # Clean title - remove dots and page numbers
    #                 clean_title = re.sub(r'\.+\s*\d*$', '', title.strip())  # Remove trailing dots and numbers
    #                 clean_title = re.sub(r'\.{3,}', '', clean_title)        # Remove multiple dots
                    
    #                 # Skip if title is too short or looks like page number
    #                 if len(clean_title.strip()) < 5 or clean_title.strip().isdigit():
    #                     continue
                    
    #                 try:
    #                     page_chapters.append({
    #                         'number': int(chapter_num),
    #                         'title': f"Chapter {chapter_num}: {clean_title}",
    #                         'page': int(page_str),
    #                         'raw_title': clean_title
    #                     })
    #                     print(f"[TOC EXTRACTION] Found Chapter {chapter_num}: {clean_title}")
    #                 except ValueError:
    #                     continue
            
    #         all_chapters.extend(page_chapters)
        
    #     # Remove duplicates and sort by chapter number
    #     unique_chapters = {}
    #     for ch in all_chapters:
    #         if ch['number'] not in unique_chapters:
    #             unique_chapters[ch['number']] = ch
        
    #     sorted_chapters = sorted(unique_chapters.values(), key=lambda x: x['number'])
        
    #     print(f"[TOC EXTRACTION] Found {len(sorted_chapters)} total unique chapters")
    #     for ch in sorted_chapters:
    #         print(f"[TOC EXTRACTION] Final: {ch['title']}")
        
    #     if len(sorted_chapters) >= 3:
    #         return await self._parse_toc_with_ai_improved(sorted_chapters, doc)
        
    #     return []
    
    @staticmethod
    def _roman_to_int(roman: str) -> int:
        values = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
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
        """Step 1: Extract TOC including BOOK/PART sections and roman-numeral chapters"""
        print("[TOC EXTRACTION] Searching for table of contents...")
    
        # Heuristic: scan up to 75 pages or full doc, whichever is smaller
        max_scan = min(75, len(doc))
        all_entries: List[Dict[str, Any]] = []
        current_section: Optional[Dict[str, Any]] = None
        
        # Track if we found a real TOC section
        found_contents_page = False
        toc_page_start = None
    
        # Patterns - compiled regex patterns
        section_patterns = [
            re.compile(r'^\s*(BOOK|PART|SECTION)\s+THE\s+([A-Z][A-Z\s]+)(?::|\.)?\s*(.*)$', re.MULTILINE),
            re.compile(r'^\s*(BOOK|PART|SECTION|VOLUME)\s+(FIRST|SECOND|THIRD|FOURTH|FIFTH|ONE|TWO|THREE|FOUR|FIVE|[IVX]+|\d+)[\s\-:]*(.*)$', re.MULTILINE),
        ]
       
        chapter_patterns = [
            # Roman numeral chapters with dots leading to page numbers
            re.compile(rf'^\s*([IVX]+)\.\s+(.+?)\s+\.{{2,}}\s*(\d+)\s*$', re.MULTILINE),
            re.compile(rf'^\s*([IVX]+)\.\s+(.+?)\s+(\d+)\s*$', re.MULTILINE),
            # Arabic numeral chapters
            re.compile(r'^\s*Chapter\s+(\d+)[\.\s]+(.+?)\s+(\d+)\s*$', re.IGNORECASE | re.MULTILINE),
            re.compile(r'^\s*(\d+)\.\s+(.+?)\s+\.{2,}\s*(\d+)\s*$', re.MULTILINE),
        ]
    
        found_any = False
        for page_num in range(max_scan):
            page = doc[page_num]
            text = page.get_text()
            if not text:
                continue
            
            print(f"[TOC EXTRACTION] Checking page {page_num + 1}...")
            
            # Check for "CONTENTS" or "TABLE OF CONTENTS" header
            if re.search(r'\b(CONTENTS|TABLE OF CONTENTS)\b', text, re.IGNORECASE):
                print(f"[TOC EXTRACTION] Found Contents header on page {page_num + 1}")
                found_contents_page = True
                if toc_page_start is None:
                    toc_page_start = page_num
    
            # FIX: More restrictive section patterns - only match if we're in TOC area
            if found_contents_page and toc_page_start is not None:
                for pattern in section_patterns:
                    for match in pattern.finditer(text):
                        sec_type = match.group(1).upper()
                        ordinal_word = match.group(2).upper()
                        sec_title_tail = (match.group(3) or "").strip()
                        
                        # FIX: Better validation of section matches
                        if (len(ordinal_word) > 15 or  # Reject very long matches
                            any(char.isdigit() for char in ordinal_word if char not in 'IVX') or  # Mixed letters/numbers
                            ordinal_word in ['CONTENTS', 'CHAPTER']):  # Skip these false matches
                            continue
                        
                        section_title = f"{sec_type.title()} the {ordinal_word.title()}"
                        if sec_title_tail and len(sec_title_tail) < 100:  # Reasonable length
                            section_title += f": {sec_title_tail}"
                        
                        current_section = {
                            "section_type": sec_type.lower(),
                            "section_number": ordinal_word.title(),
                            "title": section_title,
                        }
                        print(f"[TOC EXTRACTION] Found section: {section_title}")
    
            page_chapters = []
            for pat_idx, pattern in enumerate(chapter_patterns):
                matches = pattern.findall(text)
                print(f"[TOC EXTRACTION] Pattern {pat_idx} found {len(matches)} matches on page {page_num + 1}")
            
                for match in matches:
                    num, title, page_str = match
                    print(f"[TOC EXTRACTION] Raw match: num='{num}', title='{title}', page='{page_str}'")
                
                    # FIX: Better validation of matches
                    if (len(title.strip()) < 3 or  # Too short
                        len(title.strip()) > 100 or  # Too long
                        title.strip().isdigit() or  # Just numbers
                        'BOOK THE' in title.upper()):  # Section headers, not chapters
                        print(f"[TOC EXTRACTION] Skipping invalid title: '{title}'")
                        continue
                    
                    # Normalize number (roman -> int when needed)
                    try:
                        if re.fullmatch(r'[IVX]+', num.upper()):
                            chap_num = self._roman_to_int(num)
                            print(f"[TOC EXTRACTION] Converted roman '{num}' to {chap_num}")
                        else:
                            chap_num = int(num)
                            print(f"[TOC EXTRACTION] Using arabic number {chap_num}")
                    except Exception as e:
                        print(f"[TOC EXTRACTION] Failed to parse chapter number '{num}': {e}")
                        continue
    
                    # Normalize page
                    try:
                        page_num_val = int(page_str)
                        # FIX: Validate page number is reasonable
                        if page_num_val < 1 or page_num_val > len(doc):
                            print(f"[TOC EXTRACTION] Invalid page number: {page_num_val}")
                            continue
                        print(f"[TOC EXTRACTION] Page number: {page_num_val}")
                    except Exception as e:
                        print(f"[TOC EXTRACTION] Failed to parse page '{page_str}': {e}")
                        continue
    
                    clean_title = re.sub(r'\s*\.{2,}\s*$', '', title).strip()
                    clean_title = re.sub(r'\s+', ' ', clean_title)
                    
                    entry = {
                        "number": chap_num,
                        "title": f"Chapter {chap_num}: {clean_title}",
                        "raw_title": clean_title,
                        "page_hint": page_num_val,
                    }
                    
                    # Attach current section context if any
                    if current_section:
                        entry.update({
                            "section_title": current_section["title"],
                            "section_type": current_section["section_type"],
                            "section_number": current_section["section_number"],
                        })
    
                    page_chapters.append(entry)
                    found_any = True
                    print(f"[TOC EXTRACTION] Found chapter: {entry['title']} (sec={entry.get('section_title')})")
    
            all_entries.extend(page_chapters)
    
            # FIX: Early exit after processing TOC area
            if found_contents_page and toc_page_start is not None:
                # If we've processed several pages after finding TOC and have good results, stop
                pages_after_toc = page_num - toc_page_start
                if pages_after_toc >= 3 and len(all_entries) >= 8:  # Found substantial TOC
                    print(f"[TOC EXTRACTION] Early exit: processed {pages_after_toc} pages after TOC, found {len(all_entries)} entries")
                    break
                # If we've gone too far past TOC without finding more, stop
                elif pages_after_toc >= 10:
                    print(f"[TOC EXTRACTION] Stopping: {pages_after_toc} pages past TOC")
                    break
    
            # Original early exit condition as fallback
            if found_any and len(all_entries) >= 15:
                print(f"[TOC EXTRACTION] Early exit with {len(all_entries)} entries")
                break
    
        # Rest of the method remains the same...
        if not all_entries:
            print("[TOC EXTRACTION] Found 0 total unique chapters")
            return []
    
        # Deduplicate by chapter number+title
        dedup = {}
        for item in all_entries:
            if not isinstance(item, dict):
                continue
                
            # Ensure all required fields are safe strings
            section_title = item.get('section_title')
            chapter_num = item.get('number', 0)
            raw_title = item.get('raw_title')
            
            # FIX: Convert None to safe defaults
            section_key = str(section_title) if section_title is not None else 'no_section'
            title_key = str(raw_title).lower() if raw_title is not None else 'untitled'
            
            # Use section + chapter number + title as unique key
            key = (section_key, chapter_num, title_key)
            
            if key not in dedup:
                # FIX: Ensure the item has safe values before adding
                safe_item = {
                    'number': item.get('number', 1),
                    'title': str(item.get('title', 'Untitled Chapter')),
                    'raw_title': str(item.get('raw_title', 'Untitled')),
                    'page_hint': item.get('page_hint', 1),
                }
                
                # Add section info with null safety
                if section_title is not None:
                    safe_item.update({
                        'section_title': str(section_title),
                        'section_type': str(item.get('section_type', 'section')),
                        'section_number': str(item.get('section_number', '')),
                    })
                
                dedup[key] = safe_item
                print(f"[TOC EXTRACTION] Added unique: {safe_item['title']} | section={section_key}")
            else:
                print(f"[TOC EXTRACTION] Skipped duplicate: {item.get('title', 'Unknown')} | section={section_key}")

        chapters = list(dedup.values())
        
        # Sort with null safety
        chapters.sort(key=lambda x: (
            str(x.get('section_title', 'zzz_no_section')),
            x.get("number", 10_000)
        ))

        print(f"[TOC EXTRACTION] Found {len(chapters)} total unique chapters after improved dedupe")
        for ch in chapters:
            section_info = ch.get('section_title') if ch.get('section_title') else None
            print(f"[TOC EXTRACTION] Final: {ch['title']} | section={section_info}")

        # ... rest of existing logic with null safety ...
        if chapters:
            try:
                structure_type = self.structure_detector.detect_structure_type(chapters)
                print(f"[TOC EXTRACTION] Detected structure type: {structure_type}")
            except Exception as e:
                print(f"[TOC EXTRACTION] Structure detection error: {e}")
                structure_type = "flat"
            
            for chapter in chapters:
                chapter['detected_structure'] = structure_type
                if not chapter.get('section_type') and structure_type != 'flat':
                    chapter['section_type'] = structure_type

        if len(chapters) >= 3:
            return await self._parse_toc_with_ai_improved(chapters, doc)
        
        return []

    
    
    
    
    async def _parse_toc_with_ai_improved(self, chapters: List[Dict], doc) -> List[Dict[str, Any]]:
        """Use page-based extraction instead of AI parsing"""
        print(f"[TOC PARSING] Using page-based extraction for {len(chapters)} chapters")
        
        # Filter chapters that have valid page numbers
        chapters_with_pages = []
        for chapter in chapters:
            if chapter.get('page_hint') and isinstance(chapter['page_hint'], int) and chapter['page_hint'] > 0:
                chapters_with_pages.append(chapter)
                print(f"[TOC PARSING] Chapter '{chapter['title']}' starts at page {chapter['page_hint']}")
            else:
                print(f"[TOC PARSING] Skipping chapter without valid page: '{chapter['title']}'")
        
        if len(chapters_with_pages) >= 3:
            # Use page-based extraction
            return await self.structure_detector._extract_content_for_chapters_by_pages(chapters_with_pages, doc)
        else:
            print("[TOC PARSING] Not enough chapters with page numbers for page-based extraction")
            return []
    
    async def _validate_chapters_exist_in_book_improved(self, chapter_titles: List[Dict], original_chapters: List[Dict], doc) -> List[Dict[str, Any]]:
        """Skip AI validation - TOC extraction is reliable enough"""
        print(f"[CHAPTER VALIDATION] TOC found {len(chapter_titles)} chapters - proceeding directly to content extraction")
        
        # Get full book text
        full_text = ""
        for i in range(min(100, len(doc))):  
            full_text += doc[i].get_text()
        
        # Go directly to content extraction without AI validation
        return await self._extract_content_for_chapters_improved(chapter_titles, full_text)
    
    # async def _validate_chapters_exist_in_book_improved(self, chapter_titles: List[Dict], original_chapters: List[Dict], doc) -> List[Dict[str, Any]]:
    #     """Step 3: More lenient validation that doesn't reject valid chapters"""
    #     print("[CHAPTER VALIDATION] Validating chapters exist in book...")
        
    #     # Get book content for validation
    #     full_text = ""
    #     for i in range(min(100, len(doc))):  # Check more pages
    #         full_text += doc[i].get_text()
        
    #     try:
    #         titles_list = [ch['title'] for ch in chapter_titles]
            
    #         prompt = f"""
    #         These chapters were extracted from a table of contents. Check if they exist in the book.
            
    #         IMPORTANT: Be GENEROUS in validation. If you find ANY evidence of a chapter (even partial), mark it as valid.
            
    #         Chapters to validate:
    #         {json.dumps(titles_list)}
            
    #         Book content sample:
    #         {full_text[:8000]}
            
    #         Return JSON - include ALL chapters that have ANY evidence:
    #         {{
    #             "validated_chapters": [
    #                 {{"title": "Chapter 1: Introduction", "confidence": 0.8}},
    #                 {{"title": "Chapter 2: History", "confidence": 0.7}}
    #             ]
    #         }}
    #         """
            
    #         response = await self.ai_service.client.chat.completions.create(
    #             model="gpt-3.5-turbo",
    #             messages=[{"role": "user", "content": prompt}],
    #             max_tokens=1000,
    #             temperature=0.1
    #         )
            
    #         result = json.loads(response.choices[0].message.content)
            
    #         validated_count = len(result.get('validated_chapters', []))
    #         print(f"[CHAPTER VALIDATION] AI validated {validated_count} out of {len(chapter_titles)}")
            
    #         # If AI rejects more than 50% of chapters, ignore AI and use all chapters
    #         if validated_count < len(chapter_titles) * 0.5:
    #             print("[CHAPTER VALIDATION] AI too aggressive, using all TOC chapters")
    #             validated_chapters = chapter_titles
    #         else:
    #             validated_chapters = result['validated_chapters']
            
    #         # FIX: Remove original_chapters parameter from method call
    #         return self._extract_content_for_chapters_improved(validated_chapters, full_text)

    #     except Exception as e:
    #         print(f"[CHAPTER VALIDATION] Validation failed, using all chapters: {e}")
    #         # FIX: Remove original_chapters parameter from method call here too
    #         return self._extract_content_for_chapters_improved(chapter_titles, full_text)
        
    def _identify_toc_boundaries(self, full_text: str) -> Dict[str, int]:
        """Better TOC boundary detection"""
        toc_patterns = [
            r'\bContents\b',
            r'\bTable of Contents\b',
            r'CHAPTER\s+1\.\s+.*?\d+\s*\n.*?CHAPTER\s+2\.',  # Multiple chapter listings
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
        chapter_start_pattern = r'\n\s*1\s*\n[A-Z][^\.]*\n[A-Z][^\.]*'
        match = re.search(chapter_start_pattern, full_text[start_pos:])
        if match:
            end_pos = start_pos + match.start()
        
        return {'start': start_pos, 'end': end_pos}

    # def _extract_content_for_chapters_improved(self, validated_chapters: List[Dict], full_text: str) -> List[Dict[str, Any]]:
    #     """Step 4: Extract actual chapter content, avoiding TOC sections"""
    #     """Extract chapter content with better boundary handling"""
    #     print("[CONTENT EXTRACTION] Extracting actual chapter content...")
        
    #     toc_boundaries = self._identify_toc_boundaries(full_text)
    #     print(f"[CONTENT EXTRACTION] TOC boundaries: {toc_boundaries}")
        
    #     final_chapters = []
        
    #     for i, chapter in enumerate(validated_chapters):
    #         chapter_title = chapter['title']
    #         print(f"[CONTENT EXTRACTION] Processing: {chapter_title}")
            
    #         # chapter_num_match = re.search(r'Chapter (\d+)', chapter_title)
    #         # if not chapter_num_match:
    #         #     continue
    #         # chapter_num = int(chapter_num_match.group(1))
            
    #         # all_occurrences = self._find_all_chapter_occurrences(full_text, chapter_num, chapter_title)
    #         # Use title-based search instead of chapter number extraction
    #         all_occurrences = self._find_title_occurrences(full_text, chapter_title)

    #         content_start = None
            
    #         # For last chapter, be more lenient with TOC boundaries
    #         is_last_chapter = (i == len(validated_chapters) - 1)
            
    #         for occurrence in all_occurrences:
    #             # For last chapter, only skip if clearly in TOC start area
    #             if is_last_chapter:
    #                 if occurrence < toc_boundaries['start'] + 1000:  # Only skip if very early in doc
    #                     print(f"[CONTENT EXTRACTION] Skipping early occurrence at position {occurrence}")
    #                     continue
    #             else:
    #                 # For other chapters, use normal TOC boundary check
    #                 if self._is_in_toc_boundaries(occurrence, toc_boundaries):
    #                     print(f"[CONTENT EXTRACTION] Skipping TOC occurrence at position {occurrence}")
    #                     continue
                
    #             # Validate this is actual chapter content
    #             preview = full_text[occurrence:occurrence + 500]
    #             # if self._is_actual_chapter_content(preview, chapter_num):
    #             if self._is_actual_chapter_content_by_title(preview, chapter_title):
    #                 content_start = occurrence
    #                 print(f"[CONTENT EXTRACTION] Found chapter {chapter_title} start at position {content_start}")
    #                 break
    #             else:
    #                 print(f"[CONTENT EXTRACTION] Position {occurrence} appears to be another TOC/index reference")
            
    #         if content_start is not None:
    #             # content_end = self._find_chapter_content_end(full_text, chapter_num, content_start)
    #             content_end = self._find_chapter_content_end_by_title(full_text, validated_chapters, i, content_start)
    #             # Extract and clean content
    #             raw_content = full_text[content_start:content_end]
    #             extracted_content = self._clean_chapter_content(raw_content, chapter_title)
                
    #             if len(extracted_content) > 200:
    #                 final_chapters.append({
    #                     'title': chapter_title,
    #                     'content': extracted_content,
    #                     'summary': f"Content for {chapter_title}",
    #                     # 'chapter_number': chapter_num,
    #                     'toc_validated': True,
    #                     'extraction_method': 'content_search'
    #                 })
    #                 print(f"[CONTENT EXTRACTION] ✅ Successfully extracted {len(extracted_content)} chars for: {chapter_title}")
    #             else:
    #                 print(f"[CONTENT EXTRACTION] ❌ Content too short for: {chapter_title}")
    #         else:
    #             print(f"[CONTENT EXTRACTION] ❌ No valid content found for: {chapter_title}")
        
    #     return final_chapters
    
    async def _extract_content_for_chapters_improved(self, validated_chapters: List[Dict], full_text: str) -> List[Dict[str, Any]]:
        """Improved extraction using AI instead of pattern matching"""
        
        print(f"[CONTENT EXTRACTION] Using AI-powered extraction for {len(validated_chapters)} chapters")
        
        # Get chapter titles
        chapter_titles = [ch['title'] for ch in validated_chapters]
        
        # Use AI to extract content instead of pattern matching
        extracted_chapters = await self._extract_content_with_ai(full_text, chapter_titles)
        
        print(f"[CONTENT EXTRACTION] AI extracted {len(extracted_chapters)} chapters successfully")
        
        return extracted_chapters
    
    async def _extract_content_with_ai(self, full_text: str, chapter_titles: List[str]) -> List[Dict]:
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
                context={"book_title": self.extracted_title, "total_chapters": len(chapter_titles)}
            )
            
            if chapter_content and len(chapter_content) > 200:
                extracted_chapters.append({
                    'title': chapter_title,
                    'content': chapter_content,
                    'summary': f"Content for {chapter_title}",
                    'extraction_method': 'ai'
                })
                print(f"[AI EXTRACTION] ✅ Extracted {len(chapter_content)} chars")
            else:
                print(f"[AI EXTRACTION] ❌ No content found")
        
        return extracted_chapters
    
    def _split_text_for_ai(self, text: str, max_chunk_size: int = 15000) -> List[str]:
        """Split text into manageable chunks for AI processing"""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed the limit
            if len(current_chunk) + len(paragraph) > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Single paragraph is too large, split by sentences
                    sentences = paragraph.split('. ')
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

    def _find_relevant_chunks(self, text_chunks: List[str], chapter_title: str) -> List[str]:
        """Find chunks that likely contain the chapter content"""
        relevant_chunks = []
        
        # Extract key words from chapter title for searching
        title_words = chapter_title.lower().split()
        search_words = [word for word in title_words if len(word) > 3 and word not in ['chapter', 'the', 'and', 'of', 'to', 'in', 'for']]
        
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
            chapter_num_match = re.search(r'chapter (\d+)', chapter_title.lower())
            if chapter_num_match:
                chapter_num = chapter_num_match.group(1)
                if f"chapter {chapter_num}" in chunk_lower or f"\n{chapter_num}\n" in chunk_lower:
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
        
        print(f"[CHUNK SELECTION] Selected {len(relevant_chunks)} chunks for chapter: {chapter_title}")
        return relevant_chunks

    @property
    def extracted_title(self) -> Optional[str]:
        """Get the extracted book title"""
        return getattr(self, '_extracted_title', None)

    @extracted_title.setter
    def extracted_title(self, value: str):
        """Set the extracted book title"""
        self._extracted_title = value

    def _extract_book_title_from_content(self, content: str) -> str:
        """Extract book title from content"""
        lines = content.split('\n')[:20]  # Check first 20 lines
        
        # Look for title patterns
        for line in lines:
            line = line.strip()
            if len(line) > 10 and len(line) < 100:
                # Check if line looks like a title (starts with capital, has multiple words)
                if (line[0].isupper() and 
                    len(line.split()) > 2 and 
                    not re.match(r'^\d+', line) and
                    'chapter' not in line.lower()):
                    return line
        
        return "Untitled Book"

    async def _ai_extract_chapter_content(self, chunks: List[str], chapter_title: str, context: Dict) -> str:
        """Use AI to extract specific chapter content from text chunks"""
        
        # Combine relevant chunks
        search_text = "\n\n".join(chunks)
        
        # Use the property correctly
        book_title = self.extracted_title or context.get('book_title', 'Unknown Book')
        
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
            response = await self.ai_service.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting specific chapter content from books. Return only the requested chapter content, nothing else."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.1
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

    def _validate_ai_extracted_content(self, content: str, chapter_title: str) -> bool:
        """Validate that AI extracted relevant content"""
        if len(content) < 100:
            return False
        
        # Check if content seems related to the chapter title
        title_words = chapter_title.lower().split()
        content_lower = content.lower()
        
        # At least one significant word from title should appear in content
        significant_words = [w for w in title_words if len(w) > 3 and w not in ['chapter', 'the', 'and', 'of']]
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
        title_parts = chapter_title.split(':', 1)
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
        print(f"[CONTENT EXTRACTION] Found {len(occurrences)} title occurrences for: {clean_title}")
        
        return occurrences
    
    def _is_actual_chapter_content_by_title(self, content: str, chapter_title: str) -> bool:
        """Validate that this is actual chapter content, not TOC or page number"""
        
        # Extract clean title
        title_parts = chapter_title.split(':', 1)
        clean_title = title_parts[1].strip() if len(title_parts) > 1 else chapter_title
        
        # Check if the title appears at the beginning of the content
        content_start = content[:200].strip()
        if clean_title.lower() in content_start.lower():
            print(f"[CONTENT VALIDATION] Found title '{clean_title}' at content start")
            
            # Additional validation: check for substantial content following
            lines = content.split('\n')
            substantial_lines = [line for line in lines if len(line.strip()) > 20]
            
            if len(substantial_lines) >= 3:  # At least 3 substantial lines
                print(f"[CONTENT VALIDATION] Found {len(substantial_lines)} substantial lines")
                return True
        
        # Reject if it looks like TOC
        toc_indicators = [
            r'\.{3,}',  # Dots leading to page numbers
            r'\d+\s*$',  # Ends with just a number (page number)
            r'chapter.*?\d+.*?chapter',  # Multiple chapter references
        ]
        
        for pattern in toc_indicators:
            if re.search(pattern, content[:300], re.IGNORECASE):
                print(f"[CONTENT VALIDATION] TOC indicator found: {pattern}")
                return False
        
        # Basic content quality check
        word_count = len(content.split())
        has_sentences = bool(re.search(r'[.!?]', content[:500]))
        
        print(f"[CONTENT VALIDATION] Words: {word_count}, Has sentences: {has_sentences}")
        return word_count > 50 and has_sentences
    
    
    
    def _find_chapter_content_end_by_title(self, full_text: str, validated_chapters: List[Dict], current_index: int, content_start: int) -> int:
        """Find where current chapter ends by looking for the next chapter title"""
        
        # If this is the last chapter, return end of document
        if current_index >= len(validated_chapters) - 1:
            return len(full_text)
        
        # Get the next chapter title
        next_chapter = validated_chapters[current_index + 1]
        next_title_parts = next_chapter['title'].split(':', 1)
        next_clean_title = next_title_parts[1].strip() if len(next_title_parts) > 1 else next_chapter['title']
        
        # Search for the next chapter title after current content start
        search_text = full_text[content_start + 1000:]  # Skip first 1000 chars to avoid false matches
        
        # Try different variations of the next title
        title_variations = [next_clean_title, next_clean_title.upper(), next_clean_title.lower()]
        
        for title_var in title_variations:
            pos = search_text.find(title_var)
            if pos != -1:
                # Validate this is actually a chapter start, not just a reference
                potential_end = content_start + 1000 + pos
                preview = full_text[potential_end-100:potential_end+100]
                
                # Make sure it's not in a TOC (no dots leading to page numbers)
                if not re.search(r'\.{3,}', preview):
                    print(f"[CONTENT EXTRACTION] Found next chapter '{next_clean_title}' at position {potential_end}")
                    return potential_end
        
        # Fallback: return a reasonable chunk size
        return min(content_start + 10000, len(full_text))
        
    def _clean_chapter_content(self, content: str, chapter_title: int) -> str:
        """Remove headers, footers, page numbers, and other artifacts from chapter content"""
        lines = content.split('\n')
        cleaned_lines = []
        
        # Patterns for lines to skip
        skip_patterns = [
            r'^\s*\d+\s*$',  # Just page numbers
            r'^\s*[ivxlcdm]+\s*$',  # Roman numeral page numbers
            r'^.{0,50}•.{0,50}$',  # Short lines with bullets (often headers)
            r'^\s*\[?\s*\d+\s*\]?\s*$',  # Page numbers in brackets
            # Book title/author in header (usually short repeated lines)
            r'^.{5,40}$',  # Very short lines that might be headers
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
        result = '\n'.join(cleaned_lines)
        result = re.sub(r'\n{4,}', '\n\n\n', result)  # Max 3 newlines
        
        return result.strip()


    
    
    def _find_all_chapter_occurrences(self, full_text: str, chapter_num: int, chapter_title: str) -> List[int]:
        """Dynamically find chapter occurrences for any format"""
        occurrences = []
        
        # Extract clean title without "Chapter N:" prefix
        title_parts = chapter_title.split(':', 1)
        clean_title = title_parts[1].strip() if len(title_parts) > 1 else chapter_title
        
        # Build dynamic patterns based on common formats
        patterns = []
        
        # Add patterns for different chapter formats
        # Full format: "Chapter N: Title"
        patterns.append(rf'Chapter\s+{chapter_num}\s*[:.\-]?\s*{re.escape(clean_title)}')
        
        # Number with title
        patterns.append(rf'{chapter_num}\s*[:.\-]\s*{re.escape(clean_title)}')
        
        # Number on separate line from title
        patterns.append(rf'^\s*{chapter_num}\s*\n+\s*{re.escape(clean_title.split()[0])}')
        
        # Just the chapter number (various formats)
        patterns.extend([
            rf'^\s*Chapter\s+{chapter_num}\b',
            rf'^\s*{chapter_num}\s*$',  # Just number on line
            rf'^\s*{chapter_num}[:.\-]\s',  # Number with punctuation
        ])
        
        # Roman numerals for early chapters
        roman_map = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X'}
        if chapter_num in roman_map:
            patterns.append(rf'^\s*(?:Chapter\s+)?{roman_map[chapter_num]}\b')
        
        # Search with each pattern
        for pattern in patterns:
            try:
                for match in re.finditer(pattern, full_text, re.IGNORECASE | re.MULTILINE):
                    occurrences.append(match.start())
            except re.error:
                continue
        
        # Remove duplicates and sort
        occurrences = sorted(list(set(occurrences)))
        print(f"[CONTENT EXTRACTION] Found {len(occurrences)} occurrences for chapter {chapter_num}")
        
        return occurrences

    
    # def _find_all_chapter_occurrences(self, full_text: str, chapter_num: int, chapter_title: str) -> List[int]:
    #     """Find ALL occurrences of a chapter in the text"""
    #     occurrences = []
        
    #     # Extract just the title part (without "Chapter X:")
    #     title_match = re.search(r'Chapter \d+:\s*(.+)', chapter_title)
    #     clean_title = title_match.group(1) if title_match else chapter_title
        
    #     # Multiple search patterns
    #     patterns = [
    #         # Pattern 0: Chapter number and title
    #         rf'Chapter\s+{chapter_num}\s*[:\-.]?\s*{re.escape(clean_title)}',
    #         # Pattern 1: Just chapter number
    #         rf'Chapter\s+{chapter_num}\b',
    #         # Pattern 2: Number on its own line followed by title (YOUR BOOK FORMAT)
    #         rf'^\s*{chapter_num}\s*\n+\s*{re.escape(clean_title.split()[0])}',
    #         # Pattern 3: Just the number at start of line
    #         rf'^\s*{chapter_num}\s*$',
    #         # Pattern 4: Just the title
    #         rf'\b{re.escape(clean_title)}\b'
    #     ]
        
    #     for pattern_idx, pattern in enumerate(patterns):
    #         try:
    #             flags = re.IGNORECASE | re.MULTILINE
    #             for match in re.finditer(pattern, full_text, flags):
    #                 position = match.start()
    #                 occurrences.append(position)
    #                 print(f"[CONTENT EXTRACTION] Found pattern {pattern_idx} match at position {position}")
    #         except re.error:
    #             continue
            
    #     # Remove duplicates and sort
    #     occurrences = sorted(list(set(occurrences)))
    #     print(f"[CONTENT EXTRACTION] Found {len(occurrences)} total occurrences for chapter {chapter_num}")
        
    #     return occurrences
    
    # def _is_in_toc_boundaries(self, position: int, toc_boundaries: Dict[str, int]) -> bool:
    #     """Check if a position is within TOC boundaries"""
    #     return toc_boundaries['start'] <= position <= toc_boundaries['end']
    
    def _is_in_toc_boundaries(self, position: int, toc_boundaries: Dict[str, int]) -> bool:
        """Check if position is within TOC boundaries"""
        # Add some buffer to the boundaries
        start = max(0, toc_boundaries['start'] - 100)
        end = toc_boundaries['end'] + 100
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
            clean_title = chapter_title.split(': ', 1)[-1].strip() if ': ' in chapter_title else chapter_title

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
                        line_text = "".join(span["text"] for span in line["spans"]).strip()
                        
                        # Check if this line contains our chapter title
                        if clean_title.lower() in line_text.lower():
                            # Analyze formatting properties
                            line_font_sizes = [span["size"] for span in line["spans"] if span["text"].strip()]
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
                            is_centered = abs(line_center - page_center) < page_width * 0.25
                            
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
                                title_pos_in_page = page_text.lower().find(clean_title.lower())
                                if title_pos_in_page != -1:
                                    global_pos += title_pos_in_page
                                    title_occurrences.append(global_pos)
                                    print(f"[TEXT ANALYSIS] Found formatted title '{clean_title}' at global position {global_pos} (page {page_num + 1})")
                                    print(f"[TEXT ANALYSIS] Properties: large_font={is_large_font}, centered={is_centered}, near_top={is_near_top}")

            doc.close()
        except Exception as e:
            print(f"[TEXT ANALYSIS] Error analyzing PDF properties: {e}")

        return sorted(list(set(title_occurrences)))

    
    
    def _find_chapter_content_start(self, full_text: str, chapter_num: int, toc_boundaries: Dict) -> Optional[int]:
        """Find the actual start of chapter content using multiple strategies"""
        
        # Strategy 1: Look for chapter number with title formatting (like "1\nIntroduction\nto Angel Magic")
        chapter_start_patterns = [
            rf'\n\s*{chapter_num}\s*\n.*?(?:introduction|angel|magic|source|survival|making|keys|result|fairy|golden|today)',
            rf'CHAPTER\s+{chapter_num}[^\n]*\n(?!\s*\.)',  # CHAPTER X not followed by dots (not TOC)
            rf'Chapter\s+{chapter_num}[^\n]*\n(?!\s*\.)',   # Chapter X not followed by dots
            rf'\n\s*{chapter_num}\s*\n[A-Z][^\.]*\n',       # Number, then title without dots
        ]
        
        # Search AFTER TOC boundaries to avoid TOC content
        search_start = toc_boundaries.get('end', 0)
        search_text = full_text[search_start:]
        
        for i, pattern in enumerate(chapter_start_patterns):
            matches = list(re.finditer(pattern, search_text, re.IGNORECASE | re.MULTILINE))
            
            for match in matches:
                potential_start = search_start + match.start()
                
                # Validate this is not in TOC area
                if potential_start > toc_boundaries.get('end', 0):
                    print(f"[CONTENT EXTRACTION] Found chapter {chapter_num} start using pattern {i} at position {potential_start}")
                    
                    # Move to actual content start (after chapter heading)
                    content_start = search_start + match.end()
                    return content_start
        
        # Strategy 2: If specific patterns fail, look for any substantial content after chapter mentions
        fallback_patterns = [
            rf'\b{chapter_num}\b.*?\n.*?\n',  # Any occurrence of chapter number followed by content
        ]
        
        for pattern in fallback_patterns:
            matches = list(re.finditer(pattern, search_text, re.IGNORECASE))
            for match in matches:
                potential_start = search_start + match.end()
                # Check if this looks like actual content (not TOC)
                preview = full_text[potential_start:potential_start + 200]
                if not re.search(r'\.{3,}|\d+\s*$', preview):  # No TOC dots or ending with page numbers
                    print(f"[CONTENT EXTRACTION] Found chapter {chapter_num} using fallback at position {potential_start}")
                    return potential_start
        
        return None
        
    def _find_chapter_content_end(self, full_text: str, chapter_num: int, content_start: int) -> int:
        """Find where current chapter ends"""
        next_chapter_num = chapter_num + 1
        
        # Look for next chapter start
        next_chapter_patterns = [
            rf'\n\s*{next_chapter_num}\s*\n',
            rf'^\s*{next_chapter_num}\s*$',   # Just number at end of line
            rf'CHAPTER\s+{next_chapter_num}',
            rf'Chapter\s+{next_chapter_num}',
        ]
        
        search_text = full_text[content_start:]
        
        for pattern in next_chapter_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE | re.MULTILINE)
            if match:
                # Make sure this isn't in a TOC or reference
                potential_end = content_start + match.start()
                preview = full_text[potential_end-50:potential_end+50]
                if not re.search(r'\.{3,}', preview):  # No TOC dots nearby
                    return potential_end
        
     
        
     
    def _is_actual_chapter_content(self, content: str, chapter_num: int) -> bool:
        """MUCH LESS STRICT validation - the current one is rejecting everything"""
        
        # If we see the chapter number at the start, it's probably the real chapter
        if re.search(rf'^\s*{chapter_num}\s*[\n\r]', content[:50], re.MULTILINE):
            print(f"[CONTENT VALIDATION] Found chapter {chapter_num} number at start")
            return True
        
        # Only reject if it's CLEARLY a TOC
        lines = content[:300].split('\n')[:5]  # First 5 lines only
        
        # Strong TOC indicators - must have MULTIPLE of these
        strong_toc_indicators = 0
        for line in lines:
            # Page numbers with dots
            if re.search(r'\.{5,}\s*\d+\s*$', line):
                strong_toc_indicators += 1
            # Multiple chapter listings in one line
            elif re.search(r'chapter.*?chapter', line, re.IGNORECASE):
                strong_toc_indicators += 1
        
        # Only reject if MULTIPLE strong indicators
        if strong_toc_indicators >= 2:
            print(f"[CONTENT VALIDATION] Strong TOC indicators found: {strong_toc_indicators}")
            return False
        
        # Very basic content check - just need SOME text
        word_count = len(content.split())
        has_sentences = bool(re.search(r'[.!?]', content[:500]))
        
        print(f"[CONTENT VALIDATION] Words: {word_count}, Has sentences: {has_sentences}")
        
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
    ) -> Dict[str, Any]:
        """Process upload and return a PREVIEW with null safety throughout"""
        # FIX: Add comprehensive null safety at the start
        safe_filename = original_filename or "untitled_book"
        if not isinstance(safe_filename, str):
            safe_filename = str(safe_filename) if safe_filename else "untitled_book"
        
        safe_book_type = book_type or "learning"
        if not isinstance(safe_book_type, str):
            safe_book_type = str(safe_book_type) if safe_book_type else "learning"
        
        # 1) Extract content (pdf/docx/txt or provided text)
        if text_content:
            content = text_content
            cover_image_url = None
            author_name = None
        elif storage_path and safe_filename:
            with tempfile.NamedTemporaryFile(delete=False, suffix=safe_filename) as temp_file:
                temp_file.write(self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).download(storage_path))
                temp_file_path = temp_file.name
            extracted = self.process_book_file(temp_file_path, safe_filename, user_id)
            os.unlink(temp_file_path)
            content = extracted.get("text", "")
            cover_image_url = extracted.get("cover_image_url")
            author_name = extracted.get("author")
        else:
            raise ValueError("No content provided")
    
        # 2) Extract chapters with null safety
        chapters = await self.extract_chapters_with_new_flow(content, safe_book_type, safe_filename, storage_path)
        
        print(f"[PREVIEW] ✅ Extracted {len(chapters)} chapters for preview")
    
        # 3) Build structure with comprehensive null safety
        has_sections = False
        
        # FIX: More careful section detection with null safety
        for ch in chapters:
            section_title = ch.get("section_title")
            if section_title and isinstance(section_title, str) and section_title.strip():
                has_sections = True
                break
        
        if has_sections:
            sections_grouped = {}
            
            for ch in chapters:
                # FIX: Ensure all section values are safe strings
                section_title = ch.get("section_title") or "Default Section"
                section_type = ch.get("section_type") or "section"
                section_number = ch.get("section_number") or ""
                
                # Ensure all are strings
                if not isinstance(section_title, str):
                    section_title = str(section_title) if section_title else "Default Section"
                if not isinstance(section_type, str):
                    section_type = str(section_type) if section_type else "section"
                if not isinstance(section_number, str):
                    section_number = str(section_number) if section_number else ""
                
                section_key = (section_title, section_type, section_number)
                
                if section_key not in sections_grouped:
                    sections_grouped[section_key] = {
                        'title': section_title,
                        'section_type': section_type,
                        'section_number': section_number,
                        'chapters': []
                    }
                sections_grouped[section_key]['chapters'].append(ch)
            
            section_list = list(sections_grouped.values())
            
            # FIX: Add null safety for structure detection
            try:
                detected_structure = self.structure_detector.detect_structure_type(section_list)
            except Exception as e:
                print(f"[STRUCTURE DETECTION] Error: {e}, using default")
                detected_structure = "hierarchical"
            
            structure = {
                "id": book_id_to_update,
                "title": safe_filename,
                "structure_type": detected_structure,
                "has_sections": True,
                "sections": section_list,
                "chapters": [],
                "structure_metadata": self.structure_detector.get_structure_metadata(detected_structure)
            }
        else:
            structure = {
                "id": book_id_to_update,
                "title": safe_filename,
                "structure_type": "flat",
                "has_sections": False,
                "sections": [],
                "chapters": chapters,
                "structure_metadata": self.structure_detector.get_structure_metadata("flat")
            }
    
        # 4) Update book record with null safety
        try:
            self.db.table("books").update({
                "content": self._clean_text_content(content) if content else "",
                "title": safe_filename,
                "cover_image_url": cover_image_url,
                "author_name": author_name,
                "status": "READY",
                "structure_type": structure["structure_type"],
                "has_sections": structure["has_sections"],
                "total_chapters": sum(len(s["chapters"]) for s in structure["sections"]) if structure["has_sections"] else len(structure["chapters"]),
            }).eq("id", book_id_to_update).execute()
        except Exception as e:
            print(f"[DATABASE UPDATE] Error updating book: {e}")
            raise e
    
        # Return data for the frontend preview
        if structure["has_sections"]:
            flat_preview = list(itertools.chain.from_iterable([s["chapters"] for s in structure["sections"]]))
        else:
            flat_preview = structure["chapters"]
    
        return {
            "chapters": flat_preview[: self.MAX_CHAPTERS],
            "total_chapters": len(flat_preview),
            "author_name": author_name,
            "cover_image_url": cover_image_url,
            "structure_data": structure,
        }
    
   
     
    # async def process_uploaded_book_preview(
    #     self,
    #     storage_path: Optional[str],
    #     original_filename: Optional[str],
    #     text_content: Optional[str],
    #     book_type: str,
    #     user_id: str,
    #     book_id_to_update: str,
    # ) -> Dict[str, Any]:
    #     """Process upload and return a PREVIEW (no DB chapter writes except book metadata)."""
    #     # FIX: Add null safety for original_filename at the very beginning
    #     safe_filename = original_filename or "untitled_book"
    #     if not isinstance(safe_filename, str):
    #         safe_filename = str(safe_filename) if safe_filename else "untitled_book"
        
    #     # 1) Extract content (pdf/docx/txt or provided text)
    #     if text_content:
    #         content = text_content
    #         cover_image_url = None
    #         author_name = None
    #     elif storage_path and safe_filename:  # Use safe_filename here
    #         with tempfile.NamedTemporaryFile(delete=False, suffix=safe_filename) as temp_file:
    #             temp_file.write(self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).download(storage_path))
    #             temp_file_path = temp_file.name
    #         extracted = self.process_book_file(temp_file_path, safe_filename, user_id)  # Use safe_filename here
    #         os.unlink(temp_file_path)
    #         content = extracted.get("text", "")
    #         cover_image_url = extracted.get("cover_image_url")
    #         author_name = extracted.get("author")
    #     else:
    #         raise ValueError("No content provided")
    
    #     # 2) ✅ Use safe_filename in extract_chapters_with_new_flow
    #     chapters = await self.extract_chapters_with_new_flow(content, book_type, safe_filename, storage_path)
        
    #     print(f"[PREVIEW] ✅ Extracted {len(chapters)} chapters for preview")
    
    #     # 3) Build structure for preview - FIX: Use safe_filename in structure
    #     has_sections = any("section_title" in ch for ch in chapters)
        
    #     if has_sections:
    #         sections_grouped = {}
            
    #         for ch in chapters:
    #             section_key = (ch.get("section_title"), ch.get("section_type"), ch.get("section_number"))
    #             if section_key not in sections_grouped:
    #                 sections_grouped[section_key] = {
    #                     'title': ch.get("section_title", ""),
    #                     'section_type': ch.get("section_type", ""),
    #                     'section_number': ch.get("section_number", ""),
    #                     'chapters': []
    #                 }
    #             sections_grouped[section_key]['chapters'].append(ch)
            
    #         section_list = list(sections_grouped.values())
    #         detected_structure = self.structure_detector.detect_structure_type(section_list)
            
    #         structure = {
    #             "id": book_id_to_update,
    #             "title": safe_filename,  # FIX: Use safe_filename instead of original_filename
    #             "structure_type": detected_structure,
    #             "has_sections": True,
    #             "sections": section_list,
    #             "chapters": [],
    #             "structure_metadata": self.structure_detector.get_structure_metadata(detected_structure)
    #         }
    #     else:
    #         structure = {
    #             "id": book_id_to_update,
    #             "title": safe_filename,  # FIX: Use safe_filename instead of original_filename
    #             "structure_type": "flat",
    #             "has_sections": False,
    #             "sections": [],
    #             "chapters": chapters,
    #             "structure_metadata": self.structure_detector.get_structure_metadata("flat")
    #         }
    
    #     # 4) Update book record for preview - FIX: Use safe_filename
    #     self.db.table("books").update({
    #         "content": self._clean_text_content(content),
    #         "title": safe_filename,  # FIX: Use safe_filename instead of original_filename
    #         "cover_image_url": cover_image_url,
    #         "author_name": author_name,
    #         "status": "READY",
    #         "structure_type": structure["structure_type"],
    #         "has_sections": structure["has_sections"],
    #         "total_chapters": sum(len(s["chapters"]) for s in structure["sections"]) if structure["has_sections"] else len(structure["chapters"]),
    #     }).eq("id", book_id_to_update).execute()
    
    #     # Return data for the frontend preview
    #     if structure["has_sections"]:
    #         flat_preview = list(itertools.chain.from_iterable([s["chapters"] for s in structure["sections"]]))
    #     else:
    #         flat_preview = structure["chapters"]
    
    #     return {
    #         "chapters": flat_preview[: self.MAX_CHAPTERS],
    #         "total_chapters": len(flat_preview),
    #         "author_name": author_name,
    #         "cover_image_url": cover_image_url,
    #         "structure_data": structure,
    #     }
    

    
    async def confirm_book_structure(
        self,
        book_id: str,
        confirmed_chapters: List[Dict[str, Any]],
        user_id: str
    ) -> None:
        """Persist user-confirmed structure and create embeddings."""
        # Clean old data
        self.db.table("chapter_embeddings").delete().eq("book_id", book_id).execute()
        self.db.table("chapters").delete().eq("book_id", book_id).execute()
        self.db.table("book_sections").delete().eq("book_id", book_id).execute()
    
        # Build sections (if present)
        section_id_map: Dict[str, str] = {}
        order = 0
        for ch in confirmed_chapters:
            order += 1
            section_id = None
            if ch.get("section_title"):
                key = f"{ch.get('section_title')}|{ch.get('section_type')}|{ch.get('section_number')}"
                if key not in section_id_map:
                    sec_resp = self.db.table("book_sections").insert({
                        "book_id": book_id,
                        "title": ch.get("section_title"),
                        "section_type": ch.get("section_type", "part"),
                        "section_number": ch.get("section_number", ""),
                        "order_index": len(section_id_map) + 1,
                    }).execute()
                    section_id_map[key] = sec_resp.data[0]["id"]
                section_id = section_id_map[key]
    
            chap_resp = self.db.table("chapters").insert({
                "book_id": book_id,
                "section_id": section_id,
                "chapter_number": ch.get("chapter_number", order),
                "title": ch.get("title", f"Chapter {order}"),
                "content": self._clean_text_content(ch.get("content", "")),
                "summary": self._clean_text_content(ch.get("summary", "")),
                "order_index": order,
            }).execute()
            chapter_id = chap_resp.data[0]["id"]
    
            # best-effort embeddings
            try:
                from app.services.embeddings_service import EmbeddingsService
                es = EmbeddingsService(self.db)
                await es.create_chapter_embeddings(chapter_id, ch.get("content",""))
            except Exception as e:
                print(f"[EMBEDDINGS] Failed for chapter {chapter_id}: {e}")
    
        # Update book meta
        self.db.table("books").update({
            "has_sections": bool(section_id_map),
            "structure_type": "hierarchical" if section_id_map else "flat",
            "total_chapters": order,
            "status": "READY",
            "progress": 100,
            "progress_message": "Book structure saved successfully"
        }).eq("id", book_id).execute()
    
    
    
    async def _compare_with_toc_chapter(self, chapter_title: str, extracted_content: str, toc_reference: Dict) -> Dict:
        """Compare extracted content with TOC chapter for validation"""
        
        if not toc_reference:
            return {'is_valid': True, 'confidence': 0.7, 'reason': 'No TOC reference available'}
        
        try:
            # Get first 500 characters of both contents for comparison
            extracted_preview = extracted_content[:500]
            toc_preview = toc_reference.get('content', '')[:500]
            
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
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"[TOC COMPARISON] Comparison failed: {e}")
            return {'is_valid': True, 'confidence': 0.5, 'reason': 'Comparison failed, defaulting to valid'}
        

    def _parse_toc_text(self, toc_text: str, doc) -> List[Dict[str, Any]]:
        """Parse TOC text to extract chapter information"""
        chapters = []
        lines = toc_text.split('\n')
        
        # More specific patterns that match your book's ACTUAL TOC format
        toc_patterns = [
            r'^CHAPTER\s+(\d+)\.\s+(.+?)\s+(\d+)$',  # "CHAPTER 1. Introduction to Angel Magic 1"
            r'^Chapter\s+(\d+)[\.\s]+(.+?)\s+(\d+)$', # "Chapter 1. Title 1"
            r'^(\d+)\.\s+(.+?)\s+(\d+)$',            # "1. Title 1"
        ]
        
        print(f"[TOC PARSING] Analyzing {len(lines)} TOC lines...")
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            
            # Skip obvious non-chapter lines
            if (len(line) < 15 or 
                line.startswith('Page') or 
                line.lower().startswith('list of') or
                line.lower().startswith('preface') or
                'illustrations' in line.lower() or
                'figures' in line.lower()):
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
                        if ('illustration' in title.lower() or 
                            'figure' in title.lower() or
                            'by gustav' in title.lower() or
                            'by singleton' in title.lower()):
                            print(f"[TOC PARSING] Skipping illustration entry: {title}")
                            continue
                        
                        try:
                            page_num = int(page_str)
                            if 1 <= page_num <= len(doc):  # Valid page range
                                chapters.append({
                                    'number': chapter_num,
                                    'title': f"Chapter {chapter_num}: {title.strip()}",
                                    'page': page_num,
                                    'raw_title': title.strip()
                                })
                                print(f"[TOC PARSING] Added chapter: {chapter_num} - {title.strip()} (page {page_num})")
                        except ValueError:
                            print(f"[TOC PARSING] Invalid page number: {page_str}")
                            continue
                    break
        
        # Only proceed if we found chapters with reasonable numbering
        if chapters and len(chapters) >= 3:
            # Validate chapter sequence
            chapter_numbers = [int(ch['number']) for ch in chapters]
            if min(chapter_numbers) == 1 and max(chapter_numbers) <= 20:  # Reasonable chapter range
                print(f"[TOC PARSING] Found {len(chapters)} valid chapters in TOC")
                return self._extract_chapter_content_from_toc(chapters, doc)
            else:
                print(f"[TOC PARSING] Invalid chapter numbering: {chapter_numbers}")
        
        print("[TOC PARSING] No valid chapter structure found")
        return []
    
    def _extract_chapter_content_from_toc(self, chapters: List[Dict], doc) -> List[Dict[str, Any]]:
        """Extract content for TOC chapters with better validation"""
        final_chapters = []
        
        for i, chapter in enumerate(chapters):
            start_page = chapter['page'] - 1  # Convert to 0-based index
            end_page = len(doc) - 1
            
            # Find end page (start of next chapter)
            if i + 1 < len(chapters):
                end_page = chapters[i + 1]['page'] - 2  # Stop before next chapter
            
            print(f"[CONTENT EXTRACTION] Chapter {chapter['number']}: pages {start_page + 1} to {end_page + 1}")
            
            # Extract content from the actual chapter pages
            content = ""
            
            for page_idx in range(start_page, min(end_page + 1, len(doc))):
                page_text = doc[page_idx].get_text()
                content += page_text + "\n"
            
            # Clean content and validate
            content = content.strip()
            
            # Only add chapters with substantial content
            if len(content) > 1000:  # Minimum content threshold
                final_chapters.append({
                    'title': chapter['title'],
                    'content': content,
                    'summary': f"Chapter {chapter['number']}: {chapter['raw_title']}",
                    'chapter_number': int(chapter['number'])
                })
                print(f"[CONTENT EXTRACTION] Successfully extracted {len(content)} characters for: {chapter['title']}")
            else:
                print(f"[CONTENT EXTRACTION] Skipped chapter with insufficient content: {chapter['title']} ({len(content)} chars)")
        
        print(f"[TOC EXTRACTION] Final result: {len(final_chapters)} chapters with content")
        return final_chapters
     

    def parse_book_structure(self, content: str) -> Dict[str, Any]:
        """Parse book structure and separate front matter from chapters"""
        lines = content.split('\n')
        
        # Define patterns for different book sections
        front_matter_patterns = [
            r'^Contents$',
            r'^Table of Contents$',
            r'^Preface$',
            r'^Acknowledgments?$',
            r'^Introduction$',
            r'^Foreword$',
            r'^Copyright',
            r'^Library of Congress',
            r'^ISBN',
            r'^First Edition',
            r'^Cover Design',
            r'^Book Design',
            r'^List of Illustrations',
            r'^List of Figures'
        ]
        
        chapter_patterns = [
            r'^CHAPTER\s+\d+\.?\s*',
            r'^Chapter\s+\d+\.?\s*'
        ]
        
        sections = {
            'front_matter': [],
            'chapters': [],
            'back_matter': []
        }
        
        current_section = 'front_matter'
        current_content = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if this is a chapter header
            is_chapter = any(re.match(pattern, line_stripped, re.IGNORECASE) for pattern in chapter_patterns)
            
            # Check if this is front matter
            is_front_matter = any(re.match(pattern, line_stripped, re.IGNORECASE) for pattern in front_matter_patterns)
            
            if is_chapter:
                # Save current content and switch to chapters
                if current_content:
                    sections[current_section].append('\n'.join(current_content))
                current_section = 'chapters'
                current_content = [line]
            elif is_front_matter and current_section == 'front_matter':
                # Continue in front matter
                current_content.append(line)
            else:
                current_content.append(line)
        
        # Save the last section
        if current_content:
            sections[current_section].append('\n'.join(current_content))
        
        return sections

    def extract_chapters_with_structure(self, content: str, book_type: str) -> List[Dict[str, Any]]:
        """Extract chapters with proper book structure handling"""
        # First parse the book structure
        structure = self.parse_book_structure(content)
        
        # Extract chapters from the chapters section
        if structure['chapters']:
            chapter_content = '\n'.join(structure['chapters'])
            return self.extract_chapters(chapter_content, book_type)
        else:
            # Fallback to original method if no structure found
            return self.extract_chapters(content, book_type)

    async def validate_chapters_with_ai(self, chapters: List[Dict[str, Any]], book_content: str, book_type: str) -> List[Dict[str, Any]]:
        """Validate chapters using AI, but limit prompt size to avoid context_length_exceeded errors."""
        # Reduce chapter content for prompt
        reduced_chapters = [
            {
                "title": ch.get("title", ""),
                "content_preview": (ch.get("content", "")[:500] + ("..." if len(ch.get("content", "")) > 500 else ""))
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
                    {"role": "system", "content": "You are an expert book editor and content validator."},
                    {"role": "user", "content": f"{validation_prompt}\n\nPlease respond in JSON format."}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            if 'validated_chapters' in result and result['validated_chapters']:
                print(f"AI validation found {len(result.get('issues', []))} issues")
                return result['validated_chapters']
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
            cleaned = content.replace('\x00', '')
            
            # Remove excessive whitespace while preserving paragraph breaks
            lines = cleaned.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Strip whitespace from each line
                stripped_line = line.strip()
                if stripped_line:  # Keep non-empty lines
                    cleaned_lines.append(stripped_line)
                elif cleaned_lines and cleaned_lines[-1]:  # Add single empty line for paragraph breaks
                    cleaned_lines.append('')
            
            # Join lines back together
            result = '\n'.join(cleaned_lines)
            
            # Remove excessive consecutive newlines (more than 2)
            import re
            result = re.sub(r'\n{3,}', '\n\n', result)
            
            # Ensure the content doesn't exceed reasonable limits
            if len(result) > 50000:  # Limit to ~50k characters per chapter
                result = result[:50000] + "... [Content truncated]"
            
            return result.strip()
            
        except Exception as e:
            print(f"Error cleaning text content: {e}")
            # Return original content if cleaning fails
            return str(content) if content else ""


      
    async def extract_chapters_with_new_flow(self, content: str, book_type: str, original_filename: str, storage_path: str) -> List[Dict[str, Any]]:
        """Enhanced chapter extraction: TOC first, then fallback"""
        safe_filename = original_filename or "unknown_file.txt"
        if not isinstance(safe_filename, str):
            safe_filename = str(safe_filename) if safe_filename else "unknown_file.txt"
            
        print(f"[CHAPTER EXTRACTION] Starting extraction for {safe_filename}")
        print(f"[CHAPTER EXTRACTION] Storage path: {storage_path}")
        
        # Step 1: Try TOC extraction first (most reliable for PDFs)
        if safe_filename.lower().endswith('.pdf') and storage_path:
            print("[TOC EXTRACTION] Attempting PDF TOC extraction...")
            try:
                import tempfile
                import os
                import traceback
                
                # Download the file from storage to a temporary location
                print(f"[TOC EXTRACTION] Downloading from bucket path: {storage_path}")
                file_content = self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).download(path=storage_path)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name
                
                print(f"[TOC EXTRACTION] Created temporary file: {temp_file_path}")
                
                # FIX: Pass the temporary file path, not the original filename
                toc_chapters = await self.extract_chapters_from_pdf_with_toc(temp_file_path)
                
                # Clean up the temporary file
                try:
                    os.unlink(temp_file_path)
                    print(f"[TOC EXTRACTION] Cleaned up temporary file: {temp_file_path}")
                except Exception as cleanup_error:
                    print(f"[TOC EXTRACTION] Warning: Failed to cleanup temp file: {cleanup_error}")
                
                if not isinstance(toc_chapters, list):
                    toc_chapters = []
                    
                # If TOC found ANY chapters, use them
                if len(toc_chapters) >= 2:
                    print(f"[TOC EXTRACTION] SUCCESS: Using {len(toc_chapters)} TOC chapters")
                    return toc_chapters
                else:
                    print(f"[TOC EXTRACTION] Found {len(toc_chapters)} chapters, insufficient for TOC method")
                    
            except Exception as e:
                print(f"[TOC EXTRACTION] Failed: {e}")
                print(f"[TOC EXTRACTION] Full error: {traceback.format_exc()}")
                # Clean up temp file even if there's an error
                if 'temp_file_path' in locals():
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
        # If TOC extraction succeeded, organize chapters by sections
        if toc_chapters:
            print(f"[TOC EXTRACTION] SUCCESS: Using {len(toc_chapters)} TOC chapters")
            
            # Check if we have sectioned content
            has_sections = any(ch.get('section_title') for ch in toc_chapters)
            
            if has_sections:
                # Organize into hierarchical structure
                return self._organize_chapters_into_sections(toc_chapters)
            else:
                # Return as flat structure
                return toc_chapters
    
        # Step 2: Fallback to structure detection
        print("[STRUCTURE DETECTION] TOC failed, using structure detection...")
        structure_result = self.structure_detector.detect_structure(content)
        
        # Convert the detect_structure result to the format expected by the rest of the method
        if structure_result["has_sections"]:
            # Convert sections to the format expected by _extract_hierarchical_chapters
            converted_structure = {
                "has_sections": True,
                "sections": structure_result["sections"],
                "structure_type": structure_result["structure_type"]
            }
            extracted_chapters = await self._extract_hierarchical_chapters(converted_structure, book_type, content)
        else:
            # Use the flat chapters from detect_structure
            extracted_chapters = []
            for i, chapter in enumerate(structure_result["chapters"]):
                chapter_data = {
                    "title": chapter["title"],
                    "content": chapter["content"],
                    "summary": chapter.get("summary", ""),
                    "chapter_number": chapter.get("number", i + 1)
                }
                extracted_chapters.append(chapter_data)
        
        # Step 3: Filter if too many chapters found
        if len(extracted_chapters) > 20:
            final_chapters = await self._ai_filter_real_chapters(extracted_chapters, book_type, content)
        else:
            final_chapters = extracted_chapters
        
        print(f"[CHAPTER EXTRACTION] FINAL: {len(final_chapters)} chapters extracted")
        return final_chapters
    
    def _organize_chapters_into_sections(self, chapters: List[Dict]) -> List[Dict[str, Any]]:
        """Organize chapters into sectioned structure"""
        print("[SECTION ORGANIZATION] Organizing chapters into sections...")
        
        # Group chapters by section
        sections_map = {}
        for chapter in chapters:
            section_title = chapter.get('section_title', 'Default Section')
            section_type = chapter.get('section_type', 'section')
            section_number = chapter.get('section_number', '')
            
            section_key = f"{section_title}|{section_type}|{section_number}"
            
            if section_key not in sections_map:
                sections_map[section_key] = {
                    'title': section_title,
                    'section_type': section_type,
                    'section_number': section_number,
                    'chapters': []
                }
            
            # Add chapter to section
            sections_map[section_key]['chapters'].append(chapter)
        
        print(f"[SECTION ORGANIZATION] Created {len(sections_map)} sections")
        
        # Convert to final format with section metadata
        final_chapters = []
        
        for section_key, section_data in sections_map.items():
            section_title = section_data['title']
            section_chapters = section_data['chapters']
            
            print(f"[SECTION ORGANIZATION] Section '{section_title}': {len(section_chapters)} chapters")
            
            # Sort chapters within section by chapter number
            section_chapters.sort(key=lambda x: x.get('number', 0))
            
            # Add each chapter with full section context
            for chapter in section_chapters:
                final_chapter = {
                    'title': chapter['title'],
                    'content': chapter['content'],
                    'summary': chapter.get('summary', ''),
                    'chapter_number': chapter.get('number', 1),
                    'section_title': section_data['title'],
                    'section_type': section_data['section_type'],
                    'section_number': section_data['section_number'],
                    'extraction_method': chapter.get('extraction_method', 'toc'),
                    'has_sections': True
                }
                final_chapters.append(final_chapter)
        
        return final_chapters

    
   
    
    # async def extract_chapters_with_new_flow(self, content: str, book_type: str, original_filename: str, storage_path: str) -> List[Dict[str, Any]]:
    #     """Enhanced chapter extraction: TOC first, then fallback"""
    #     print(f"[CHAPTER EXTRACTION] Starting extraction for {original_filename}")
        
    #      # Store the content for later use
    #     book_content = content
    
        
    #     # Step 1: Try TOC extraction first (most reliable for PDFs)
    #     if original_filename and original_filename.lower().endswith('.pdf') and storage_path:
    #         print("[TOC EXTRACTION] Attempting PDF TOC extraction...")
    #         try:
    #             with tempfile.NamedTemporaryFile(delete=False, suffix=original_filename) as temp_file:
    #                 file_content = self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).download(path=storage_path)
    #                 temp_file.write(file_content)
    #                 temp_file_path = temp_file.name
                
    #             toc_chapters = await self.extract_chapters_from_pdf_with_toc(temp_file_path)
    #             if not isinstance(toc_chapters, list):
    #                 toc_chapters = []
    #             os.unlink(temp_file_path)
                
    #             # If TOC found ANY chapters, use them (don't require high threshold)
    #             # if toc_chapters and len(toc_chapters) >= 2:  # Just need at least 2 chapters
    #             if len(toc_chapters) >= 2:  # Just need at least 2 chapters
    #                 print(f"[TOC EXTRACTION] SUCCESS: Using {len(toc_chapters)} TOC chapters")
    #                 return toc_chapters  # Don't fall back to structure detection
                    
    #         except Exception as e:
    #             print(f"[TOC EXTRACTION] Failed: {e}")
    #             if 'temp_file_path' in locals():
    #                 try:
    #                     os.unlink(temp_file_path)
    #                 except:
    #                     pass
            
    #     # Step 2: Fallback to structure detection only if TOC failed
    #     print("[STRUCTURE DETECTION] TOC failed, using structure detection...")
    #     structure = self.structure_detector.detect_structure(content)
        
    #     if structure['has_sections']:
    #         extracted_chapters = await self._extract_hierarchical_chapters(structure, book_type, book_content)
    #     else:
    #         extracted_chapters = await self._extract_flat_chapters(structure['chapters'], book_type, book_content)
        
    #     # Step 3: Filter if too many chapters found
    #     if len(extracted_chapters) > 20:
    #         final_chapters = await self._ai_filter_real_chapters(extracted_chapters, book_type, book_content)
    #     else:
    #         final_chapters = extracted_chapters
        
    #     print(f"[CHAPTER EXTRACTION] FINAL: {len(final_chapters)} chapters extracted")
    #     return final_chapters
    
    def _validate_chapters_against_toc(self, extracted_chapters: List[Dict], toc_chapters: List[Dict]) -> List[Dict]:
        """
        Validate extracted chapters against TOC and remove duplicates
        """
        print("[TOC VALIDATION] Starting chapter validation against TOC...")
        
        # Create a set of normalized TOC chapter titles
        toc_titles = set()
        for toc_chapter in toc_chapters:
            normalized_title = self._normalize_chapter_title(toc_chapter['title'])
            toc_titles.add(normalized_title)
            print(f"[TOC VALIDATION] TOC chapter: {normalized_title}")
        
        # Filter extracted chapters to only include those that match TOC
        validated_chapters = []
        seen_titles = set()
        
        for chapter in extracted_chapters:
            normalized_title = self._normalize_chapter_title(chapter['title'])
            
            # Skip if we've already seen this title (removes duplicates)
            if normalized_title in seen_titles:
                print(f"[TOC VALIDATION] Skipping duplicate: {normalized_title}")
                continue
            
            # Check if this chapter exists in TOC
            if normalized_title in toc_titles:
                # Find the corresponding TOC chapter for additional info
                toc_match = None
                for toc_chapter in toc_chapters:
                    if self._normalize_chapter_title(toc_chapter['title']) == normalized_title:
                        toc_match = toc_chapter
                        break
                
                # Use TOC content if extracted content is too short
                if toc_match and len(chapter['content'].strip()) < 500:
                    chapter['content'] = toc_match['content']
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
        title = re.sub(r'^CHAPTER\s+', '', title)
        
        # Normalize Roman numerals to Arabic
        roman_pattern = r'^([IVX]+)[\.\s]*'
        match = re.match(roman_pattern, title)
        if match:
            roman = match.group(1)
            arabic = self._roman_to_arabic(roman)
            title = re.sub(roman_pattern, f'{arabic}. ', title)
        
        # Remove extra whitespace and punctuation
        title = re.sub(r'[\.\s]+', ' ', title).strip()
        
        return title

    def _roman_to_arabic(self, roman: str) -> int:
        """Convert Roman numerals to Arabic numbers"""
        roman_values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
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

    async def _extract_hierarchical_chapters(self, structure: Dict[str, Any], book_type: str, book_content: str) -> List[Dict[str, Any]]:
        """Extract chapters from hierarchical structure"""
        all_chapters = []
        chapter_counter = 1
        
        # Add null check for structure
        if not structure or not structure.get('sections'):
            print("[HIERARCHICAL EXTRACTION] No sections found in structure")
            return []
        
        for section_index, section in enumerate(structure['sections']):
            section_type = section.get('type', 'section')  # Add fallback
            section_title = section.get('title', f'Section {section_index + 1}')  # Add fallback
            
            print(f"[HIERARCHICAL EXTRACTION] Processing {section_type}: {section_title}")
            
            # If section has chapters within it, extract them
            if section.get('chapters'):
                for chapter in section['chapters']:
                    chapter_data = {
                        "title": chapter.get('title', f'Chapter {chapter_counter}'),  # Add fallback
                        "content": chapter.get('content', ''),
                        "summary": chapter.get('summary', f"Chapter from {section_title}"),  # Use existing or create
                        "section_title": section_title,
                        "section_type": section_type,
                        "section_number": section.get('number', str(section_index + 1)),  # Add fallback
                        "chapter_number": chapter_counter
                    }
                    all_chapters.append(chapter_data)
                    chapter_counter += 1
            else:
                # Treat the entire section as a chapter (like tablets)
                chapter_data = {
                    "title": section_title,
                    "content": section.get('content', ''),
                    "summary": f"{section_type.title()} content",
                    "section_title": section_title,
                    "section_type": section_type,
                    "section_number": section.get('number', str(section_index + 1)),
                    "chapter_number": chapter_counter
                }
                all_chapters.append(chapter_data)
                chapter_counter += 1
        
        print(f"[HIERARCHICAL EXTRACTION] Extracted {len(all_chapters)} total chapters")
        
        # Skip AI validation if we have reasonable number of chapters
        if 3 <= len(all_chapters) <= 20:  # Reasonable chapter count
            print("[AI VALIDATION] Skipping AI validation - chapter count looks reasonable")
            return all_chapters
        
        # Apply AI validation if needed
        if len(all_chapters) > 20:
            validated_chapters = await self._ai_filter_real_chapters(all_chapters, book_type, book_content)
            return validated_chapters
        
        return all_chapters
    
    # In _extract_flat_chapters method  
    async def _extract_flat_chapters(self, chapters: List[Dict], book_type: str, book_content: str) -> List[Dict[str, Any]]:
        """Extract chapters from flat structure"""
        print(f"[FLAT EXTRACTION] Processing {len(chapters)} flat chapters")
        
        chapter_list = []
        for index, chapter in enumerate(chapters):
            chapter_data = {
                "title": chapter['title'],
                "content": chapter['content'],
                "summary": f"Chapter {index + 1}",
                "chapter_number": index + 1
            }
            chapter_list.append(chapter_data)
        
        # Skip AI validation if we have reasonable number of chapters
        if 3 <= len(chapter_list) <= 20:  # Reasonable chapter count
            print("[AI VALIDATION] Skipping AI validation - chapter count looks reasonable")
            return chapter_list
        
        # Apply AI validation if needed
        if len(chapter_list) > 20:
            validated_chapters = await self._ai_filter_real_chapters(chapter_list, book_type, book_content)
            return validated_chapters
        
        return chapter_list

    
    async def _ai_filter_real_chapters(self, chapters: List[Dict[str, Any]], book_type: str, book_content: str) -> List[Dict[str, Any]]:
        """Use AI to filter and identify real chapters from a list - MORE CONSERVATIVE"""
        print(f"[AI FILTERING] Filtering {len(chapters)} chapters to find real chapters...")
        
        # FIX: Don't use AI filtering unless we have an excessive number of chapters
        if len(chapters) <= 30:
            print(f"[AI FILTERING] Chapter count reasonable ({len(chapters)}), skipping AI filtering")
            return chapters[:25]  # Just cap at 25 if needed
        
        # Add input validation
        if not chapters:
            print("[AI FILTERING] No chapters to filter")
            return []
        
        # Prepare a sample of the book content for AI context
        content_sample = book_content[:8000] if len(book_content) > 8000 else book_content
        
        # Limit chapters sent to AI to avoid token limits
        chapters_to_analyze = chapters[:30]  # Analyze first 30 only
        
        # FIX: Much more conservative prompt
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
            response = await self.ai_service.extract_real_chapters_from_list(prompt)
            
            if not response or 'chapters' not in response:
                print(f"[AI FILTERING] No valid response from AI, keeping all chapters")
                return chapters_to_analyze
            
            valid_indices = response.get('chapters', [])
            filtered_chapters = []
            
            for idx in valid_indices:
                if 1 <= idx <= len(chapters_to_analyze):
                    filtered_chapters.append(chapters_to_analyze[idx - 1])
            
            # FIX: Much more lenient threshold - keep most chapters
            if len(filtered_chapters) < len(chapters_to_analyze) * 0.7:  # Less than 70% kept
                print(f"[AI FILTERING] AI too aggressive ({len(filtered_chapters)}/{len(chapters_to_analyze)}), keeping most chapters")
                filtered_chapters = chapters_to_analyze[:20]  # Keep first 20
            
            estimated_total = response.get('total_chapters', len(filtered_chapters))
            reason = response.get('reasoning', 'AI analysis')
            
            print(f"[AI FILTERING] AI kept {len(filtered_chapters)} chapters out of {len(chapters_to_analyze)}")
            print(f"[AI FILTERING] Estimated total chapters: {estimated_total}")
            print(f"[AI FILTERING] Reasoning: {reason}")
            
            return filtered_chapters
            
        except Exception as e:
            print(f"[AI FILTERING] Error: {e}")
            print(f"[AI FILTERING] Falling back to keeping first 20 chapters")
            return chapters[:20]  # Conservative fallback


    def _pattern_based_chapter_filtering(self, chapters: List[Dict]) -> List[Dict[str, Any]]:
        """Fallback method to filter chapters using patterns"""
        print("[PATTERN FILTERING] Using pattern-based chapter filtering...")
        
        real_chapters = []
        seen_numbers = set()
        
        for chapter in chapters:
            title = chapter.get('title', '').strip()
            
            # Skip obvious non-chapters
            skip_patterns = [
                r'^\d{4}$',  # Just years
                r'^Page \d+',  # Page numbers
                r'^Figure \d+',  # Figure captions
                r'^Table \d+',  # Table captions
                r'^List of',  # List of figures, etc.
                r'^Bibliography',
                r'^Index$',
                r'^\d+$',  # Just numbers
            ]
            
            if any(re.match(pattern, title, re.IGNORECASE) for pattern in skip_patterns):
                continue
            
            # Look for proper chapter patterns
            chapter_patterns = [
                r'^Chapter\s+(\d+)[:\.\s]*(.+)$',
                r'^(\d+)[:\.\s]+([A-Z].{10,})$',  # Number followed by substantial title
            ]
            
            for pattern in chapter_patterns:
                match = re.match(pattern, title, re.IGNORECASE)
                if match:
                    chapter_num = int(match.group(1))
                    if chapter_num not in seen_numbers and len(chapter.get('content', '')) > 1000:
                        seen_numbers.add(chapter_num)
                        real_chapters.append(chapter)
                    break
        
        # Sort by chapter number
        real_chapters.sort(key=lambda x: int(re.search(r'(\d+)', x['title']).group(1)) if re.search(r'(\d+)', x['title']) else 0)
        
        print(f"[PATTERN FILTERING] Filtered to {len(real_chapters)} chapters")
        return real_chapters
        

    # async def _validate_chapters_with_ai(self, chapters: List[Dict], book_type: str) -> List[Dict[str, Any]]:
    #     """Validate and enhance chapters with AI using chunking to avoid token limits"""
    #     print(f"[AI VALIDATION] Validating {len(chapters)} chapters with AI...")
        
    #     # If we have too many chapters, ask AI to identify the real ones
    #     if len(chapters) > 50:
    #         return await self._ai_filter_real_chapters(chapters, book_type)
            
    #     CHUNK_SIZE = 10  # Process 10 chapters at a time instead of all 492
    #     validated_chapters = []
        
    #     try:
    #         if not self.ai_service.client:
    #             print("[AI VALIDATION] AI service not available, skipping validation")
    #             return chapters
            
    #         # Process chapters in chunks
    #         for i in range(0, len(chapters), CHUNK_SIZE):
    #             chunk = chapters[i:i + CHUNK_SIZE]
    #             chunk_num = i//CHUNK_SIZE + 1
    #             total_chunks = (len(chapters) + CHUNK_SIZE - 1) // CHUNK_SIZE
                
    #             print(f"[AI VALIDATION] Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} chapters)")
                
    #             # Prepare chapters for AI validation (reduced content)
    #             chapters_for_validation = []
    #             for chapter in chunk:
    #                 chapters_for_validation.append({
    #                     "title": chapter.get("title", ""),
    #                     "content": chapter.get("content", "")[:500],  # Limit content to 500 chars
    #                     "summary": chapter.get("summary", "")
    #                 })
                
    #             # Create shorter prompt for each chunk
    #             validation_prompt = f"""
    #             Please validate and enhance these {len(chunk)} {book_type} book chapters (chunk {chunk_num}/{total_chunks}). IMPORTANT: Return ONLY valid JSON with no additional text or formatting.
                
    #             For each chapter, ensure:
    #             1. Title is clear and descriptive
    #             2. Content is meaningful and substantial
    #             3. Summary is accurate (if provided)
                
    #             Return in this JSON format:
    #             {{
    #                 "validated_chapters": [
    #                     {{
    #                         "title": "Enhanced title",
    #                         "content": "Enhanced content preview...",
    #                         "summary": "Enhanced summary"
    #                     }}
    #                 ]
    #             }}
                
    #             Chapters to validate: {json.dumps(chapters_for_validation)}
    #             """
                
    #             try:
    #                 response = await self.ai_service.client.chat.completions.create(
    #                     model="gpt-3.5-turbo",
    #                     messages=[{"role": "user", "content": validation_prompt}],
    #                     max_tokens=2000,  # Reduced token limit
    #                     temperature=0.3
    #                 )
                    
    #                 result = json.loads(response.choices[0].message.content)
                    
    #                 if 'validated_chapters' in result and result['validated_chapters']:
    #                     print(f"[AI VALIDATION] Chunk {chunk_num} enhanced {len(result['validated_chapters'])} chapters")
                        
    #                     # Merge AI enhancements with original chapter data
    #                     for j, original_chapter in enumerate(chunk):
    #                         if j < len(result['validated_chapters']):
    #                             ai_chapter = result['validated_chapters'][j]
    #                             enhanced_chapter = {
    #                                 **original_chapter,  # Keep original data
    #                                 "title": ai_chapter.get("title", original_chapter.get("title", "")),
    #                                 "summary": ai_chapter.get("summary", original_chapter.get("summary", ""))
    #                                 # Keep original content, don't replace with truncated version
    #                             }
    #                             validated_chapters.append(enhanced_chapter)
    #                         else:
    #                             validated_chapters.append(original_chapter)
    #                 else:
    #                     print(f"[AI VALIDATION] Chunk {chunk_num} returned no enhancements, using original chapters")
    #                     validated_chapters.extend(chunk)
                        
    #             except Exception as chunk_error:
    #                 print(f"[AI VALIDATION] Chunk {chunk_num} failed: {chunk_error}")
    #                 # Add chapters without AI validation as fallback
    #                 validated_chapters.extend(chunk)
            
    #         print(f"[AI VALIDATION] Completed processing {len(validated_chapters)} chapters")
    #         return validated_chapters
            
    #     except Exception as e:
    #         print(f"[AI VALIDATION] Overall AI validation failed: {e}")
    #         return chapters


    def _get_fallback_chapters(self, content: str, book_type: str) -> List[Dict[str, Any]]:
            """Fallback method when all other extraction methods fail"""
            if book_type == "learning":
                return [{
                    "title": "Complete Learning Content",
                    "content": content,
                    "summary": "Complete learning material"
                }]
            else:
                return [{
                    "title": "Complete Story",
                    "content": content,
                    "summary": "Complete story content"
                }]

    def _clean_text_content(self, content: str) -> str:
            """Clean text content to handle Unicode escape sequences and problematic characters"""
            return TextSanitizer.sanitize_text(content)
        
    
    async def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        """Upload file to Supabase storage"""
        
        try:
            # Read file
            async with aiofiles.open(local_path, 'rb') as f:
                file_data = await f.read()
            
            # Upload to Supabase storage
            bucket_name = "video-files"  # Make sure this bucket exists
            
            result = self.supabase.storage.from_(bucket_name).upload(
                remote_path, 
                file_data,
                file_options={"content-type": "video/mp4"}
            )
            
            if result.error:
                print(f"[FILE UPLOAD ERROR] {result.error}")
                return None
            
            # Get public URL
            public_url_result = self.supabase.storage.from_(bucket_name).get_public_url(remote_path)
            
            if public_url_result:
                print(f"[FILE UPLOAD SUCCESS] {remote_path} -> {public_url_result}")
                return public_url_result
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
                        async with aiofiles.open(local_path, 'wb') as f:
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