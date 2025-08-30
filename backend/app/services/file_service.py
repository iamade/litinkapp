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



class BookStructureDetector:
    def __init__(self):
        # # Enhanced patterns to detect various hierarchical structures
        # self.SECTION_PATTERNS = [
        #     r'^PART\s+([A-Z]+|[IVX]+|\d+)[\s\-:]*(.*)$',  # PART THREE, PART I, PART 1
        #     r'^Part\s+([A-Z]+|[IVX]+|\d+)[\s\-:]*(.*)$',  # Part Three, Part I, Part 1
        #     # Tablets: "TABLET I", "TABLET II", "TABLET III" (most specific first)
        #     r'(?i)^tablet\s+([ivx]+|\d+)[\s\-:]*(.*)$',
        #     # Parts: "Part 1", "Part I", "Part One"
        #     r'(?i)^part\s+(\d+|[ivx]+|one|two|three|four|five|six|seven|eight|nine|ten)[\s\-:]*(.*)$',
        #     # Books: "Book 1", "Book I"
        #     r'(?i)^book\s+(\d+|[ivx]+)[\s\-:]*(.*)$',
        #     # Sections: "Section 1", "Section I"
        #     r'(?i)^section\s+(\d+|[ivx]+)[\s\-:]*(.*)$',
        #     # Chapters as main sections: "Chapter 1", "Chapter I"
        #     r'(?i)^chapter\s+(\d+|[ivx]+)[\s\-:]*(.*)$',
        # ]
        
        # self.CHAPTER_PATTERNS = [
        #     r'^CHAPTER\s+\d+\.\s+(.+)$',  # More specific - must start line
        #     r'^CHAPTER\s+[IVX]+\.\s+(.+)$',  # Roman numerals
        #     r'^Chapter\s+\d+\.\s+(.+)$',  # Capitalized version
        #     r'^Chapter\s+[IVX]+\.\s+(.+)$',  # Capitalized Roman numerals
        # ]
        
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

    def detect_structure(self, content: str) -> Dict[str, Any]:
        # """
        # Detect if book has hierarchical structure and extract it
        # """
        # lines = content.split('\n')
        # sections = []
        # current_section = None
        # flat_chapters = []
        
        # for line_num, line in enumerate(lines):
        #     line = line.strip()
        #     if not line:
        #         continue
                
        #     # Check if line matches any section pattern
        #     section_match = self._match_section_patterns(line)
        #     if section_match:
        #         # Save previous section if exists
        #         if current_section:
        #             sections.append(current_section)
                
        #         # Start new section
        #         current_section = {
        #             "title": line,
        #             "number": section_match["number"],
        #             "type": section_match["type"],
        #             "chapters": [],
        #             "content": self._extract_section_content(content, line, lines, line_num)
        #         }
        #         continue
        
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
        
        for section in sections:  # 'sections' should already exist from your current code
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
    
    
    # def _extract_chapter_content(self, full_content: str, chapter_title: str, lines: List[str], start_line: int) -> str:
    #     """Enhanced chapter content extraction that gets actual chapter content"""
    #     content_lines = []
    #     found_substantial_content = False
    #     skip_lines = 0
        
    #     # Start from the line after the chapter title
    #     for i in range(start_line + 1, len(lines)):
    #         if i >= len(lines):
    #             break
                
    #         line = lines[i].strip()
            
    #         # Skip empty lines at the beginning
    #         if not line and not found_substantial_content:
    #             continue
            
    #          # Skip footnote references at the beginning (numbers followed by periods)
    #         if not found_substantial_content and re.match(r'^\d+\.\s', line):
    #             skip_lines += 1
    #             if skip_lines > 10:  # Don't skip too many lines
    #                 found_substantial_content = True
    #             continue
            
    #         # Stop if we hit another chapter or section header
    #         if (self._match_chapter_patterns(line) or 
    #             self._match_section_patterns(line) or
    #             self._match_special_sections(line)):
    #             break
            
    #         # Skip obvious page numbers and headers/footers
    #         if re.match(r'^\d+$', line) or len(line) < 3:
    #             continue
            
    #          # Skip lines that look like footnotes or references
    #         if re.match(r'^\d+\.\s', line) and not found_substantial_content:
    #             continue
                
    #         # Skip "NOTES" sections
    #         if line.upper() in ['NOTES', 'BIBLIOGRAPHY', 'REFERENCES']:
    #             break
            
    #         # Add the line to content
    #         content_lines.append(line)
            
    #         # Mark that we found substantial content (paragraph text, not just references)
    #         if len(line) > 50 and not re.match(r'^\d+\.', line):
    #             found_substantial_content = True
        
    #     content = '\n'.join(content_lines).strip()
        
    #     # Clean up content - remove footnote sections at the end
    #     content_lines = content.split('\n')
    #     cleaned_lines = []
        
    #     for line in content_lines:
    #         # Stop at "NOTES" or when we hit a series of numbered references
    #         if (line.strip().upper() in ['NOTES', 'BIBLIOGRAPHY', 'REFERENCES'] or
    #             (re.match(r'^\d+\.\s', line.strip()) and len([l for l in content_lines[content_lines.index(line):content_lines.index(line)+3] if re.match(r'^\d+\.\s', l.strip())]) >= 2)):
    #             break
    #         cleaned_lines.append(line)
        
    #     content = '\n'.join(cleaned_lines).strip()
            
    #     # Ensure we have substantial content
    #     if len(content) < 200:
    #         print(f"[WARNING] Chapter '{chapter_title}' has only {len(content)} characters of content")
        
    #     return content if content else "Content not available"
    
    
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
        """Find chapters by looking for number + title pattern"""
        chapter_headers = []
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Look for just a number on its own line
            number_match = re.match(r'^(\d+)$', line)
            if number_match and line_num < len(lines) - 5:  # Must have content after
                chapter_number = number_match.group(1)
                
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
                    
                    # Check if this looks like a chapter title
                    if (next_line[0].isupper() and 
                        len(next_line) > 10 and 
                        not re.match(r'^\d+\.', next_line)):  # Not a footnote
                        
                        chapter_title = next_line
                        title_line_num = next_line_num
                        break
                
                # Verify substantial content follows
                if (chapter_title and title_line_num and 
                    self._has_substantial_following_content(lines, title_line_num, min_lines=5)):
                    
                    full_title = f"Chapter {chapter_number}: {chapter_title}"
                    chapter_headers.append({
                        'line_num': line_num,
                        'title_line_num': title_line_num,
                        'title': full_title,
                        'number': chapter_number,
                        'raw_title': chapter_title
                    })
                    print(f"[CHAPTER DETECTION] Found: {full_title}")
        
        return chapter_headers
        
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


class FileService:
    """File processing service for book uploads"""
    MAX_CHAPTERS = 50
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        # Initialize a new Supabase client with the service role key for backend operations
        self.db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        self.ai_service = AIService()
        self.structure_detector = BookStructureDetector()
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def process_uploaded_book(
        self,
        storage_path: Optional[str],
        original_filename: Optional[str],
        text_content: Optional[str],
        book_type: str,
        user_id: str,
        book_id_to_update: str,
    ) -> None:
        """Process uploaded book and create chapters with embeddings"""
        try:
            # Extract text content
            if text_content:
                content = text_content
            elif storage_path:
                # Download file from Supabase Storage to a temporary location
                with tempfile.NamedTemporaryFile(delete=False, suffix=original_filename) as temp_file:
                    file_content = self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).download(path=storage_path)
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name

                extracted_data = self.process_book_file(temp_file_path, original_filename, user_id)
                content = extracted_data.get("text", "")
                author_name = extracted_data.get("author")
                cover_image_url = extracted_data.get("cover_image_url")

                # Clean up temporary file
                os.unlink(temp_file_path)
            else:
                raise ValueError("No content provided")

            # Update book with extracted content
            # Clean the content to handle Unicode escape sequences
            cleaned_content = self._clean_text_content(content)
            
            self.db.table("books").update({
                "content": cleaned_content,
                "status": "PROCESSING",
                "cover_image_url": cover_image_url
            }).eq("id", book_id_to_update).execute()

            # NEW FLOW: Extract chapters following the specified order
            chapters = await self.extract_chapters_with_new_flow(content, book_type, original_filename, storage_path)
            
            # Create sections and chapters in database
            section_id_map = {}  # Map section titles to section IDs
            
            for i, chapter_data in enumerate(chapters):
                section_id = None
                
                # If chapter has section data, create or get section
                if "section_title" in chapter_data:
                    section_key = f"{chapter_data['section_title']}_{chapter_data.get('section_type', '')}"
                    
                    if section_key not in section_id_map:
                        # Create new section
                        section_insert_data = {
                            "book_id": book_id_to_update,
                            "title": chapter_data["section_title"],
                            "section_type": chapter_data.get("section_type", ""),
                            "section_number": chapter_data.get("section_number", ""),
                            "order_index": chapter_data.get("section_order", i + 1)
                        }
                        
                        section_response = self.db.table("book_sections").insert(section_insert_data).execute()
                        section_id = section_response.data[0]["id"]
                        section_id_map[section_key] = section_id
                    else:
                        section_id = section_id_map[section_key]
                
                # Create chapter
                chapter_insert_data = {
                    "book_id": book_id_to_update,
                    "chapter_number": chapter_data.get("chapter_number", i + 1),
                    "title": chapter_data["title"],
                    "content": self._clean_text_content(chapter_data["content"]),
                    "summary": self._clean_text_content(chapter_data.get("summary", "")),
                    "order_index": chapter_data.get("chapter_number", i + 1)
                }
                
                # Add section_id if chapter belongs to a section
                if section_id:
                    chapter_insert_data["section_id"] = section_id
                
                # Insert chapter
                chapter_response = self.db.table("chapters").insert(chapter_insert_data).execute()
                chapter_id = chapter_response.data[0]["id"]
                
                # Create embeddings for the chapter
                try:
                    from app.services.embeddings_service import EmbeddingsService
                    embeddings_service = EmbeddingsService(self.db)
                    await embeddings_service.create_chapter_embeddings(
                        chapter_id=chapter_id,
                        content=chapter_data["content"]
                    )
                except Exception as e:
                    print(f"Failed to create embeddings for chapter {chapter_id}: {e}")

            # Create book-level embeddings
            try:
                from app.services.embeddings_service import EmbeddingsService
                embeddings_service = EmbeddingsService(self.db)
                
                # Get book data for embeddings
                book_response = self.db.table("books").select("*").eq("id", book_id_to_update).single().execute()
                book_data = book_response.data
                
                await embeddings_service.create_book_embeddings(
                    book_id=book_id_to_update,
                    title=book_data["title"],
                    description=book_data.get("description"),
                    content=content
                )
            except Exception as e:
                print(f"Failed to create book embeddings: {e}")

            # Update book status to completed
            self.db.table("books").update({
                "status": "READY",
                "total_chapters": len(chapters)
            }).eq("id", book_id_to_update).execute()

        except Exception as e:
            # Update book status to failed
            self.db.table("books").update({
                "status": "FAILED"
            }).eq("id", book_id_to_update).execute()
            raise e
        
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

    
    
    async def _extract_toc_from_text(self, doc) -> List[Dict[str, Any]]:
        """Step 1: Extract TOC by finding ALL chapter entries across multiple pages"""
        print("[TOC EXTRACTION] Searching for table of contents...")
        
        all_chapters = []
        
        # Search first 15 pages for ANY chapter entries
        for page_num in range(min(15, len(doc))):
            page = doc[page_num]
            text = page.get_text()
            
            print(f"[TOC EXTRACTION] Checking page {page_num + 1}...")
            
            # Look for chapter entries REGARDLESS of "Contents" header
            chapter_patterns = [
                r'CHAPTER\s+(\d+)\.\s+(.+?)\s+(\d+)',  # "CHAPTER 1. Title 123"
                r'Chapter\s+(\d+)[\.\s]+(.+?)\s+(\d+)', # "Chapter 1. Title 123"
            ]
            
            page_chapters = []
            for pattern in chapter_patterns:
                matches = re.findall(pattern, text, re.MULTILINE)
                for match in matches:
                    chapter_num, title, page_str = match
                    
                    # Clean title - remove dots and page numbers
                    clean_title = re.sub(r'\.+\s*\d*$', '', title.strip())  # Remove trailing dots and numbers
                    clean_title = re.sub(r'\.{3,}', '', clean_title)        # Remove multiple dots
                    
                    # Skip if title is too short or looks like page number
                    if len(clean_title.strip()) < 5 or clean_title.strip().isdigit():
                        continue
                    
                    try:
                        page_chapters.append({
                            'number': int(chapter_num),
                            'title': f"Chapter {chapter_num}: {clean_title}",
                            'page': int(page_str),
                            'raw_title': clean_title
                        })
                        print(f"[TOC EXTRACTION] Found Chapter {chapter_num}: {clean_title}")
                    except ValueError:
                        continue
            
            all_chapters.extend(page_chapters)
        
        # Remove duplicates and sort by chapter number
        unique_chapters = {}
        for ch in all_chapters:
            if ch['number'] not in unique_chapters:
                unique_chapters[ch['number']] = ch
        
        sorted_chapters = sorted(unique_chapters.values(), key=lambda x: x['number'])
        
        print(f"[TOC EXTRACTION] Found {len(sorted_chapters)} total unique chapters")
        for ch in sorted_chapters:
            print(f"[TOC EXTRACTION] Final: {ch['title']}")
        
        if len(sorted_chapters) >= 3:
            return await self._parse_toc_with_ai_improved(sorted_chapters, doc)
        
        return []


    
    async def _parse_toc_with_ai_improved(self, chapters: List[Dict], doc) -> List[Dict[str, Any]]:
        """Step 2: Skip AI parsing since we already have clean chapter data"""
        print(f"[TOC PARSING] Using {len(chapters)} directly extracted chapters")
        
        # Convert to the format expected by validation
        chapter_titles = [{'title': ch['title']} for ch in chapters]
        
        return await self._validate_chapters_exist_in_book_improved(chapter_titles, chapters, doc)
     
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
        """Process uploaded book for PREVIEW only - don't save chapters yet"""
        try:
            # Extract text content (same as your existing logic)
            if text_content:
                content = text_content
                self.extracted_title = self._extract_book_title_from_content(content)
            elif storage_path:
                with tempfile.NamedTemporaryFile(delete=False, suffix=original_filename) as temp_file:
                    file_content = self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).download(path=storage_path)
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name
                    

                extracted_data = self.process_book_file(temp_file_path, original_filename, user_id)
                content = extracted_data.get("text", "")
                author_name = extracted_data.get("author")
                cover_image_url = extracted_data.get("cover_image_url")
                
                # Extract title from content
                self.extracted_title = self._extract_book_title_from_content(content)
                
                # Set defaults for variables that might not be defined
                author_name = locals().get('author_name')
                cover_image_url = locals().get('cover_image_url')
            

                os.unlink(temp_file_path)
            else:
                raise ValueError("No content provided")

            # Update book with extracted content but keep status as PENDING_CONFIRMATION
            cleaned_content = self._clean_text_content(content)
            
            update_data = {
            "content": cleaned_content,
            "status": "READY",  # ✅ Changed from "PENDING_CONFIRMATION" to "READY"
            }
            
            # Add optional fields if they exist
            if cover_image_url:
                update_data["cover_image_url"] = cover_image_url
                
            if author_name:
                update_data["author_name"] = author_name
                
            update_response = self.db.table("books").update(update_data).eq("id", book_id_to_update).execute()
            
             # Check if the update was successful
            if not update_response.data:
                raise Exception(f"Failed to update book {book_id_to_update} in database")
            
            # Get the updated book data
            updated_book = update_response.data[0]
            print(f"[BOOK UPDATE] Successfully updated book: {updated_book.get('title', 'Unknown')}")


            # update_response = self.db.table("books").update({
            #     "content": cleaned_content,
            #     "status": "PENDING_CONFIRMATION",  # Key change: don't set to READY
            #     "cover_image_url": cover_image_url
            # }).eq("id", book_id_to_update).execute()

            # Extract chapters but DON'T save them to database yet
            chapters = await self.extract_chapters_with_new_flow(
                content, book_type, original_filename, storage_path
                )
            
            extracted_title = original_filename  # Implement this
            
            # Return chapters for preview instead of saving them
            return {
                "status": "READY",
                "title": extracted_title or "Untitled Book", 
                "chapters": chapters,
                "total_chapters": len(chapters),
                "book_id": book_id_to_update,
                "author_name": author_name,
                "cover_image_url": cover_image_url,
                "updated_book": updated_book
            }

        except Exception as e:
            self.db.table("books").update({
                "status": "FAILED",
                "error_message": str(e)
            }).eq("id", book_id_to_update).execute()
            raise e
        
        
    async def confirm_book_structure(
    self,
    book_id: str,
    confirmed_chapters: List[Dict[str, Any]],
    user_id: str
) -> None:
        """Save confirmed chapters to database after user approval"""
        try:
            print(f"[CONFIRM STRUCTURE] Starting confirmation for book {book_id}")
            
            # Update book status to processing
            self.db.table("books").update({
                "status": "PROCESSING"
            }).eq("id", book_id).execute()

            # Delete any existing chapters/sections/embeddings for this book
            try:
                # Delete embeddings first
                existing_chapters = self.db.table("chapters").select("id").eq("book_id", book_id).execute()
                if existing_chapters.data:
                    chapter_ids = [ch["id"] for ch in existing_chapters.data]
                    for chapter_id in chapter_ids:
                        self.db.table("chapter_embeddings").delete().eq("chapter_id", chapter_id).execute()
                    print(f"Deleted existing chapter embeddings for book {book_id}")

                # Delete chapters
                self.db.table("chapters").delete().eq("book_id", book_id).execute()
                print(f"Deleted existing chapters for book {book_id}")
                
                # Delete sections
                self.db.table("book_sections").delete().eq("book_id", book_id).execute()
                print(f"Deleted existing book sections for book {book_id}")
                
            except Exception as cleanup_error:
                print(f"Error during cleanup: {cleanup_error}")

            # Create sections and chapters in database (your existing logic)
            section_id_map = {}
            
            for i, chapter_data in enumerate(confirmed_chapters):
                section_id = None
                
                # If chapter has section data, create or get section
                if "section_title" in chapter_data:
                    section_key = f"{chapter_data['section_title']}_{chapter_data.get('section_type', '')}"
                    
                    if section_key not in section_id_map:
                        section_insert_data = {
                            "book_id": book_id,
                            "title": chapter_data["section_title"],
                            "section_type": chapter_data.get("section_type", ""),
                            "section_number": chapter_data.get("section_number", ""),
                            "order_index": chapter_data.get("section_order", i + 1)
                        }
                        
                        section_response = self.db.table("book_sections").insert(section_insert_data).execute()
                        section_id = section_response.data[0]["id"]
                        section_id_map[section_key] = section_id
                    else:
                        section_id = section_id_map[section_key]
                
                # Create chapter
                chapter_insert_data = {
                    "book_id": book_id,
                    "chapter_number": chapter_data.get("chapter_number", i + 1),
                    "title": chapter_data["title"],
                    "content": self._clean_text_content(chapter_data["content"]),
                    "summary": self._clean_text_content(chapter_data.get("summary", "")),
                    "order_index": chapter_data.get("chapter_number", i + 1)
                }
                
                if section_id:
                    chapter_insert_data["section_id"] = section_id
                
                # Insert chapter
                chapter_response = self.db.table("chapters").insert(chapter_insert_data).execute()
                chapter_id = chapter_response.data[0]["id"]
                
                print(f"Inserted chapter {i + 1}: {chapter_data['title']}")
                
                # Create embeddings for the chapter
                try:
                    from app.services.embeddings_service import EmbeddingsService
                    embeddings_service = EmbeddingsService(self.db)
                    await embeddings_service.create_chapter_embeddings(
                        chapter_id=chapter_id,
                        content=chapter_data["content"]
                    )
                    print(f"Created embeddings for chapter {chapter_id}")
                except Exception as e:
                    print(f"Failed to create embeddings for chapter {chapter_id}: {e}")

            # Create book-level embeddings
            try:
                from app.services.embeddings_service import EmbeddingsService
                embeddings_service = EmbeddingsService(self.db)
                
                book_response = self.db.table("books").select("*").eq("id", book_id).single().execute()
                book_data = book_response.data
                
                await embeddings_service.create_book_embeddings(
                    book_id=book_id,
                    title=book_data["title"],
                    description=book_data.get("description"),
                    content=book_data.get("content", "")
                )
            except Exception as e:
                print(f"Failed to create book embeddings: {e}")

            # Update book status to completed
            update_data = {
            "status": "READY",
            "total_chapters": len(confirmed_chapters),
            "has_sections": any(ch.get("section_title") for ch in confirmed_chapters),  # Check if any chapters have sections
            "structure_type": "hierarchical" if any(ch.get("section_title") for ch in confirmed_chapters) else "flat"
             }
            
            self.db.table("books").update(update_data).eq("id", book_id).execute()

            print(f"[CONFIRM STRUCTURE] Successfully confirmed {len(confirmed_chapters)} chapters")

        except Exception as e:
            self.db.table("books").update({
                "status": "FAILED"
            }).eq("id", book_id).execute()
            print(f"Error confirming book structure: {e}")
            raise e

    
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
        print(f"[CHAPTER EXTRACTION] Starting extraction for {original_filename}")
        
         # Store the content for later use
        book_content = content
    
        
        # Step 1: Try TOC extraction first (most reliable for PDFs)
        if original_filename and original_filename.lower().endswith('.pdf') and storage_path:
            print("[TOC EXTRACTION] Attempting PDF TOC extraction...")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=original_filename) as temp_file:
                    file_content = self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).download(path=storage_path)
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name
                
                toc_chapters = await self.extract_chapters_from_pdf_with_toc(temp_file_path)
                if not isinstance(toc_chapters, list):
                    toc_chapters = []
                os.unlink(temp_file_path)
                
                # If TOC found ANY chapters, use them (don't require high threshold)
                # if toc_chapters and len(toc_chapters) >= 2:  # Just need at least 2 chapters
                if len(toc_chapters) >= 2:  # Just need at least 2 chapters
                    print(f"[TOC EXTRACTION] SUCCESS: Using {len(toc_chapters)} TOC chapters")
                    return toc_chapters  # Don't fall back to structure detection
                    
            except Exception as e:
                print(f"[TOC EXTRACTION] Failed: {e}")
                if 'temp_file_path' in locals():
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
            
        # Step 2: Fallback to structure detection only if TOC failed
        print("[STRUCTURE DETECTION] TOC failed, using structure detection...")
        structure = self.structure_detector.detect_structure(content)
        
        if structure['has_sections']:
            extracted_chapters = await self._extract_hierarchical_chapters(structure, book_type, book_content)
        else:
            extracted_chapters = await self._extract_flat_chapters(structure['chapters'], book_type, book_content)
        
        # Step 3: Filter if too many chapters found
        if len(extracted_chapters) > 20:
            final_chapters = await self._ai_filter_real_chapters(extracted_chapters, book_type, book_content)
        else:
            final_chapters = extracted_chapters
        
        print(f"[CHAPTER EXTRACTION] FINAL: {len(final_chapters)} chapters extracted")
        return final_chapters
    
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
        
        for section_index, section in enumerate(structure['sections']):
            print(f"[HIERARCHICAL EXTRACTION] Processing {section['type']}: {section['title']}")
            
            # If section has chapters within it, extract them
            if section['chapters']:
                for chapter in section['chapters']:
                    chapter_data = {
                        "title": chapter['title'],
                        "content": chapter['content'],
                        "summary": f"Chapter from {section['title']}",
                        "section_title": section['title'],
                        "section_type": section['type'],
                        "section_number": section['number'],
                        "chapter_number": chapter_counter
                    }
                    all_chapters.append(chapter_data)
                    chapter_counter += 1
            else:
                # Treat the entire section as a chapter (like tablets)
                chapter_data = {
                    "title": section['title'],
                    "content": section['content'],
                    "summary": f"{section['type'].title()} content",
                    "section_title": section['title'],
                    "section_type": section['type'],
                    "section_number": section['number'],
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
    

    # async def _extract_flat_chapters(self, chapters: List[Dict], book_type: str) -> List[Dict[str, Any]]:
    #     """Extract chapters from flat structure"""
    #     print(f"[FLAT EXTRACTION] Processing {len(chapters)} flat chapters")
        
    #     chapter_list = []
    #     for index, chapter in enumerate(chapters):
    #         chapter_data = {
    #             "title": chapter['title'],
    #             "content": chapter['content'],
    #             "summary": f"Chapter {index + 1}",
    #             "chapter_number": index + 1
    #         }
    #         chapter_list.append(chapter_data)
        
    #     # Apply AI validation if available
    #     if len(chapter_list) > 0:
    #         validated_chapters = await self._validate_chapters_with_ai(chapter_list, book_type)
    #         return validated_chapters
        
    #     return chapter_list
    
   
    
    async def _ai_filter_real_chapters(self, chapters: List[Dict[str, Any]], book_type: str, book_content: str) -> List[Dict[str, Any]]:
        """Use AI to filter and identify real chapters from a list"""
        print(f"[AI FILTERING] Filtering {len(chapters)} chapters to find real chapters...")
        
        # Prepare a sample of the book content for AI context
        content_sample = book_content[:10000] if len(book_content) > 10000 else book_content
        
        # Build the prompt with actual book content
        prompt = f"""You are analyzing a {book_type} book. Here's a sample of the book content:

    ---
    {content_sample}
    ---

    I have extracted the following potential chapters:
    {json.dumps([{'number': i+1, 'title': ch['title']} for i, ch in enumerate(chapters[:30])], indent=2)}

    Based on the book content above, identify which entries are actual chapters (not preface, contents, acknowledgments, etc).
    Return only the chapter numbers that are real chapters.

    Format your response as:
    CHAPTERS: [list of chapter numbers]
    TOTAL: estimated total chapters
    REASON: brief explanation"""

        try:
            # Use the prompt in the AI call
            response = await self.ai_service.extract_real_chapters_from_list(prompt)
            
            if not response or 'chapters' not in response:
                print(f"[AI FILTERING] No valid response from AI")
                return chapters[:20]  # Fallback
            
            valid_indices = response['chapters']
            filtered_chapters = []
            
            for idx in valid_indices:
                if 1 <= idx <= len(chapters):
                    filtered_chapters.append(chapters[idx - 1])
            
            estimated_total = response.get('total_chapters', len(filtered_chapters))
            reason = response.get('reasoning', 'AI analysis')
            
            print(f"[AI FILTERING] AI identified {len(filtered_chapters)} real chapters out of {len(chapters)}")
            print(f"[AI FILTERING] Estimated total chapters: {estimated_total}")
            print(f"[AI FILTERING] Reasoning: {reason}")
            
            return filtered_chapters
            
        except Exception as e:
            print(f"[AI FILTERING] Error: {e}")
            return chapters[:20]  # Fallback to first 20
        
    
    



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