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

# class BookStructureDetector:
#     def __init__(self):
#         # Enhanced patterns to detect various hierarchical structures
#         self.SECTION_PATTERNS = [
#             # Parts: "Part 1", "Part I", "Part One"
#             r'(?i)^part\s+(\d+|[ivx]+|one|two|three|four|five|six|seven|eight|nine|ten)[\s\-:]*(.*)$',
#             # Books: "Book 1", "Book I"
#             r'(?i)^book\s+(\d+|[ivx]+)[\s\-:]*(.*)$',
#             # Tablets: "TABLET I", "TABLET II", "TABLET III"
#             r'(?i)^tablet\s+([ivx]+|\d+)[\s\-:]*(.*)$',
#             # Sections: "Section 1", "Section I"
#             r'(?i)^section\s+(\d+|[ivx]+)[\s\-:]*(.*)$',
#             # Chapters as main sections: "Chapter 1", "Chapter I"
#             r'(?i)^chapter\s+(\d+|[ivx]+)[\s\-:]*(.*)$',
#         ]
        
#         self.CHAPTER_PATTERNS = [
#             # Standard chapters within sections
#             r'(?i)^chapter\s+(\d+|[ivx]+)[\s\-:]*(.*)$',
#             # Numbered items: "1.", "1.1", "2.3"
#             r'^(\d+(?:\.\d+)*)[\.\s]+(.*)$',
#             # Lettered items: "A.", "B.", "a.", "b."
#             r'^([a-zA-Z])[\.\s]+(.*)$',
#         ]

#     def detect_structure(self, content: str) -> Dict[str, Any]:
#         """
#         Detect if book has hierarchical structure and extract it
#         """
#         lines = content.split('\n')
#         sections = []
#         current_section = None
#         flat_chapters = []
        
#         for line in lines:
#             line = line.strip()
#             if not line:
#                 continue
                
#             # Check if line matches any section pattern
#             section_match = self._match_section_patterns(line)
#             if section_match:
#                 # Save previous section if exists
#                 if current_section:
#                     sections.append(current_section)
                
#                 # Start new section
#                 current_section = {
#                     "title": line,
#                     "number": section_match["number"],
#                     "type": section_match["type"],
#                     "chapters": []
#                 }
#                 continue
            
#             # Check if line matches chapter pattern
#             chapter_match = self._match_chapter_patterns(line)
#             if chapter_match:
#                 chapter_data = {
#                     "title": line,
#                     "number": chapter_match["number"],
#                     "content": self._extract_chapter_content(content, line)
#                 }
                
#                 if current_section:
#                     current_section["chapters"].append(chapter_data)
#                 else:
#                     flat_chapters.append(chapter_data)
        
#         # Add last section
#         if current_section:
#             sections.append(current_section)
        
#         # Determine structure type
#         has_sections = len(sections) > 0
        
#         return {
#             "has_sections": has_sections,
#             "sections": sections if has_sections else None,
#             "chapters": flat_chapters if not has_sections else [],
#             "structure_type": self._determine_structure_type(sections) if has_sections else "flat"
#         }

#     def _match_section_patterns(self, line: str) -> Optional[Dict]:
#         """Match line against section patterns"""
#         for pattern in self.SECTION_PATTERNS:
#             match = re.match(pattern, line)
#             if match:
#                 return {
#                     "number": match.group(1),
#                     "title": match.group(2).strip() if len(match.groups()) > 1 else "",
#                     "type": self._get_section_type(pattern)
#                 }
#         return None

#     def _match_chapter_patterns(self, line: str) -> Optional[Dict]:
#         """Match line against chapter patterns"""
#         for pattern in self.CHAPTER_PATTERNS:
#             match = re.match(pattern, line)
#             if match:
#                 return {
#                     "number": match.group(1),
#                     "title": match.group(2).strip() if len(match.groups()) > 1 else ""
#                 }
#         return None

#     def _get_section_type(self, pattern: str) -> str:
#         """Determine section type from pattern"""
#         if "part" in pattern.lower():
#             return "part"
#         elif "tablet" in pattern.lower():
#             return "tablet"
#         elif "book" in pattern.lower():
#             return "book"
#         elif "section" in pattern.lower():
#             return "section"
#         else:
#             return "chapter"

#     def _determine_structure_type(self, sections: List[Dict]) -> str:
#         """Determine the overall structure type"""
#         if not sections:
#             return "flat"
        
#         section_types = [section.get("type", "unknown") for section in sections]
#         most_common_type = max(set(section_types), key=section_types.count)
#         return most_common_type

#     def _extract_chapter_content(self, full_content: str, chapter_title: str) -> str:
#         """Extract content for a specific chapter"""
#         # This is a simplified implementation
#         # You'll need to implement more sophisticated content extraction
#         lines = full_content.split('\n')
#         start_index = -1
        
#         for i, line in enumerate(lines):
#             if chapter_title.strip() in line.strip():
#                 start_index = i
#                 break
        
#         if start_index == -1:
#             return ""
        
#         # Extract content until next chapter/section
#         content_lines = []
#         for i in range(start_index + 1, len(lines)):
#             line = lines[i].strip()
            
#             # Stop if we hit another chapter/section
#             if (self._match_section_patterns(line) or 
#                 self._match_chapter_patterns(line)):
#                 break
                
#             content_lines.append(line)
        
#         return '\n'.join(content_lines).strip()


class BookStructureDetector:
    def __init__(self):
        # Enhanced patterns to detect various hierarchical structures
        self.SECTION_PATTERNS = [
            r'^PART\s+([A-Z]+|[IVX]+|\d+)[\s\-:]*(.*)$',  # PART THREE, PART I, PART 1
            r'^Part\s+([A-Z]+|[IVX]+|\d+)[\s\-:]*(.*)$',  # Part Three, Part I, Part 1
            # Tablets: "TABLET I", "TABLET II", "TABLET III" (most specific first)
            r'(?i)^tablet\s+([ivx]+|\d+)[\s\-:]*(.*)$',
            # Parts: "Part 1", "Part I", "Part One"
            r'(?i)^part\s+(\d+|[ivx]+|one|two|three|four|five|six|seven|eight|nine|ten)[\s\-:]*(.*)$',
            # Books: "Book 1", "Book I"
            r'(?i)^book\s+(\d+|[ivx]+)[\s\-:]*(.*)$',
            # Sections: "Section 1", "Section I"
            r'(?i)^section\s+(\d+|[ivx]+)[\s\-:]*(.*)$',
            # Chapters as main sections: "Chapter 1", "Chapter I"
            r'(?i)^chapter\s+(\d+|[ivx]+)[\s\-:]*(.*)$',
        ]
        
        self.CHAPTER_PATTERNS = [
            r'^CHAPTER\s+\d+\.\s+(.+)$',  # More specific - must start line
            r'^CHAPTER\s+[IVX]+\.\s+(.+)$',  # Roman numerals
            r'^Chapter\s+\d+\.\s+(.+)$',  # Capitalized version
            r'^Chapter\s+[IVX]+\.\s+(.+)$',  # Capitalized Roman numerals
        ]
        # self.CHAPTER_PATTERNS = [
        #     # Standard chapters within sections
        #     r'(?i)^chapter\s+(\d+|[ivx]+)[\s\-:]*(.*)$',
        #     # Numbered items: "1.", "1.1", "2.3"
        #     r'^(\d+(?:\.\d+)*)[\.\s]+(.*)$',
        #     # Lettered items: "A.", "B.", "a.", "b."
        #     r'^([a-zA-Z])[\.\s]+(.*)$',
        # ]
        
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
        """
        Detect if book has hierarchical structure and extract it
        """
        lines = content.split('\n')
        sections = []
        current_section = None
        flat_chapters = []
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Check if line matches any section pattern
            section_match = self._match_section_patterns(line)
            if section_match:
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
            if special_match:
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
                if chapter_match:
                    chapter_data = {
                        "title": line,
                        "number": chapter_match["number"],
                        "content": self._extract_chapter_content(content, line, lines, line_num)
                    }
                    current_section["chapters"].append(chapter_data)
        
        # Add last section
        if current_section:
            sections.append(current_section)
        
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


    # def _match_special_sections(self, line: str) -> Optional[Dict]:
    #     """Match line against special section patterns"""
    #     for pattern in self.SPECIAL_SECTIONS:
    #         match = re.match(pattern, line)
    #         if match:
    #             return {
    #                 "number": "0",  # Special sections don't have numbers
    #                 "title": match.group(1).strip() if len(match.groups()) > 0 else "",
    #                 "type": "special"
    #             }
    #     return None

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

    
    def _extract_chapter_content(self, full_content: str, chapter_title: str, lines: List[str], start_line: int) -> str:
        """Extract content for a specific chapter"""
        content_lines = []
        
        # Start from the line after the chapter title
        for i in range(start_line + 1, len(lines)):
            if i >= len(lines):
                break
                
            line = lines[i].strip()
            
            # Stop if we hit another chapter or section header
            if (self._match_chapter_patterns(line.strip()) or 
                self._match_section_patterns(line.strip()) or
                self._match_special_sections(line.strip())):
                break
            
            # Skip table of contents entries and page numbers
            if re.match(r'^\d+$', line) or 'Contents' in line:
                continue
                
            # Add the line to content (keep original formatting)
            content_lines.append(line)
        
        content = '\n'.join(content_lines).strip()
        
        # If content is too short, try to get more context
        if len(content) < 100 and start_line + 1 < len(lines):
            # Look ahead more lines if content seems too short
            for i in range(len(content_lines) + start_line + 1, min(len(lines), start_line + 50)):
                line = lines[i]
                if (re.match(r'^CHAPTER\s+\d+\.|^CHAPTER\s+[IVX]+\.', line) or
                    self._match_section_patterns(line.strip()) or
                    self._match_section_patterns(line.strip())):
                    break
                content_lines.append(line)
            content = '\n'.join(content_lines).strip()
    
        return content if content else "Content not available"

    # def _extract_chapter_content(self, full_content: str, chapter_title: str, lines: List[str], start_line: int) -> str:
        # """Extract content for a specific chapter"""
        # content_lines = []
        
        # # Start from the line after the chapter title
        # for i in range(start_line + 1, len(lines)):
        #     line = lines[i].strip()
            
        #     # Stop if we hit another chapter or section
        #     if (self._match_chapter_patterns(line) or 
        #         self._match_section_patterns(line) or
        #         self._match_special_sections(line)):
        #         break
                
        #     content_lines.append(line)
        
        # return '\n'.join(content_lines).strip()

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
                extracted_content = self._extract_chapter_content(content, line, lines, line_num)
                
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
        
            # if chapter_match:
            #     chapter_data = {
            #         "title": line,
            #         "number": chapter_match["number"],
            #         "content": self._extract_chapter_content(content, line, lines, line_num)
            #     }
            #     chapters.append(chapter_data)
        
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

    def extract_chapters_from_pdf_with_toc(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        """Extract chapters using PDF table of contents"""
        try:
            doc = fitz.open(file_path)
            
            # Try to extract TOC
            toc = doc.get_toc()
            
            if toc:
                chapters = []
                for i, (level, title, page) in enumerate(toc):
                    if level == 1:  # Main chapters
                        # Get text from this page to next chapter or end
                        start_page = page - 1  # Convert to 0-based index
                        end_page = len(doc) - 1
                        
                        # Find next chapter
                        for j in range(i + 1, len(toc)):
                            if toc[j][0] == 1:  # Next main chapter
                                end_page = toc[j][2] - 2  # Convert to 0-based index
                                break
                        
                        # Extract text for this chapter
                        chapter_text = ""
                        for p in range(start_page, min(end_page + 1, len(doc))):
                            chapter_text += doc[p].get_text()
                        
                        chapters.append({
                            "title": title,
                            "content": chapter_text,
                            "summary": "",
                            "page_start": page,
                            "page_end": end_page + 1
                        })
                
                doc.close()
                return chapters
            
            doc.close()
            return None
            
        except Exception as e:
            print(f"Error extracting TOC from PDF: {e}")
            return None

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


    # async def extract_chapters_with_new_flow(
    #     self, 
    #     content: str, 
    #     book_type: str, 
    #     original_filename: Optional[str] = None,
    #     storage_path: Optional[str] = None
    # ) -> List[Dict[str, Any]]:
    #     """Extract chapters following the new flow order"""
        
    #     # Step 1: Try regex patterns for structured content
    #     print("[CHAPTER EXTRACTION] Step 1: Attempting regex pattern matching...")
    #     chapters = self.extract_chapters_with_structure(content, book_type)
        
    #     if chapters and len(chapters) > 1:
    #         print(f"[CHAPTER EXTRACTION] Step 1 SUCCESS: Found {len(chapters)} chapters using regex patterns")
    #     else:
    #         print("[CHAPTER EXTRACTION] Step 1 FAILED: No structured chapters found, proceeding to AI generation")
            
    #         # Step 2: Use AI generation for unstructured content
    #         print("[CHAPTER EXTRACTION] Step 2: Using AI generation for unstructured content...")
    #         try:
    #             ai_chapters = await self.ai_service.generate_chapters_from_content(content, book_type)
    #             if ai_chapters and len(ai_chapters) > 0:
    #                 chapters = ai_chapters
    #                 print(f"[CHAPTER EXTRACTION] Step 2 SUCCESS: AI generated {len(chapters)} chapters")
    #             else:
    #                 print("[CHAPTER EXTRACTION] Step 2 FAILED: AI generation failed, using fallback")
    #                 chapters = self._get_fallback_chapters(content, book_type)
    #         except Exception as e:
    #             print(f"[CHAPTER EXTRACTION] Step 2 ERROR: {e}, using fallback")
    #             chapters = self._get_fallback_chapters(content, book_type)
        
    #     # Step 3: Use PDF TOC extraction for quality check (if available)
    #     if original_filename and original_filename.lower().endswith('.pdf') and storage_path:
    #         print("[CHAPTER EXTRACTION] Step 3: Attempting PDF TOC extraction for quality check...")
    #         try:
    #             # Download file temporarily for TOC extraction
    #             with tempfile.NamedTemporaryFile(delete=False, suffix=original_filename) as temp_file:
    #                 file_content = self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).download(path=storage_path)
    #                 temp_file.write(file_content)
    #                 temp_file_path = temp_file.name
                
    #             toc_chapters = self.extract_chapters_from_pdf_with_toc(temp_file_path)
    #             os.unlink(temp_file_path)
                
    #             if toc_chapters and len(toc_chapters) > 0:
    #                 print(f"[CHAPTER EXTRACTION] Step 3 SUCCESS: TOC found {len(toc_chapters)} chapters")
    #                 # Use TOC chapters if they provide better structure
    #                 if len(toc_chapters) >= len(chapters):
    #                     chapters = toc_chapters
    #                     print("[CHAPTER EXTRACTION] Step 3: Using TOC chapters (better structure)")
    #                 else:
    #                     print("[CHAPTER EXTRACTION] Step 3: Keeping previous chapters (TOC has fewer chapters)")
    #             else:
    #                 print("[CHAPTER EXTRACTION] Step 3: No TOC found, keeping previous chapters")
    #         except Exception as e:
    #             print(f"[CHAPTER EXTRACTION] Step 3 ERROR: {e}, keeping previous chapters")
        
    #     # Step 4: Validate with AI for quality
    #     print("[CHAPTER EXTRACTION] Step 4: Validating chapters with AI...")
    #     try:
    #         validated_chapters = await self.validate_chapters_with_ai(chapters, content, book_type)
    #         if validated_chapters and len(validated_chapters) > 0:
    #             chapters = validated_chapters
    #             print(f"[CHAPTER EXTRACTION] Step 4 SUCCESS: AI validated {len(chapters)} chapters")
    #         else:
    #             print("[CHAPTER EXTRACTION] Step 4: AI validation returned no changes, keeping original chapters")
    #     except Exception as e:
    #         print(f"[CHAPTER EXTRACTION] Step 4 ERROR: {e}, keeping original chapters")
        
    #     print(f"[CHAPTER EXTRACTION] FINAL RESULT: {len(chapters)} chapters extracted")
    #     return chapters

    async def extract_chapters_with_new_flow(self, content: str, book_type: str, original_filename: str, storage_path: str) -> List[Dict[str, Any]]:
        """
        Enhanced chapter extraction with hierarchical structure detection
        """
        print(f"[STRUCTURE DETECTION] Starting structure detection for {original_filename}")
        
        # Step 1: Detect book structure
        structure = self.structure_detector.detect_structure(content)
        print(f"[STRUCTURE DETECTION] Detected structure type: {structure['structure_type']}")
        print(f"[STRUCTURE DETECTION] Has sections: {structure['has_sections']}")
        
        if structure['has_sections']:
            print(f"[STRUCTURE DETECTION] Found {len(structure['sections'])} sections")
            return await self._extract_hierarchical_chapters(structure, book_type)
        else:
            print(f"[STRUCTURE DETECTION] Found {len(structure['chapters'])} flat chapters")
            return await self._extract_flat_chapters(structure['chapters'], book_type)

    async def _extract_hierarchical_chapters(self, structure: Dict[str, Any], book_type: str) -> List[Dict[str, Any]]:
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
        
        # Apply AI validation if available
        if len(all_chapters) > 0:
            validated_chapters = await self._validate_chapters_with_ai(all_chapters, book_type)
            return validated_chapters
        
        return all_chapters

    async def _extract_flat_chapters(self, chapters: List[Dict], book_type: str) -> List[Dict[str, Any]]:
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
        
        # Apply AI validation if available
        if len(chapter_list) > 0:
            validated_chapters = await self._validate_chapters_with_ai(chapter_list, book_type)
            return validated_chapters
        
        return chapter_list

    # async def _validate_chapters_with_ai(self, chapters: List[Dict], book_type: str) -> List[Dict[str, Any]]:
    #     """Validate and enhance chapters with AI"""
    #     print(f"[AI VALIDATION] Validating {len(chapters)} chapters with AI...")
        
    #     try:
    #         if not self.ai_service.client:
    #             print("[AI VALIDATION] AI service not available, skipping validation")
    #             return chapters
            
    #         # Prepare chapters for AI validation
    #         chapters_for_validation = []
    #         for chapter in chapters:
    #             chapters_for_validation.append({
    #                 "title": chapter["title"],
    #                 "content": chapter["content"][:1000],  # Limit content for validation
    #                 "summary": chapter.get("summary", "")
    #             })
            
    #         validation_prompt = f"""
    #         Please validate and enhance these {book_type} book chapters. Return the response in JSON format.
            
    #         For each chapter, ensure:
    #         1. Title is clear and descriptive
    #         2. Content is properly formatted
    #         3. Summary is accurate and concise
            
    #         Chapters to validate:
    #         {json.dumps(chapters_for_validation, indent=2)}
            
    #         Return in this JSON format:
    #         {{
    #             "validated_chapters": [
    #                 {{
    #                     "title": "Enhanced title",
    #                     "content": "Original content (don't modify)",
    #                     "summary": "Enhanced summary"
    #                 }}
    #             ],
    #             "issues": ["Any issues found"]
    #         }}
    #         """
            
    #         response = await self.ai_service.client.chat.completions.create(
    #             model="gpt-3.5-turbo-1106",
    #             messages=[
    #                 {"role": "system", "content": "You are an expert book editor and content validator. Please respond with valid JSON format."},
    #                 {"role": "user", "content": validation_prompt}
    #             ],
    #             response_format={"type": "json_object"},
    #             temperature=0.3
    #         )
            
    #         result = json.loads(response.choices[0].message.content)
            
    #         if 'validated_chapters' in result and result['validated_chapters']:
    #             print(f"[AI VALIDATION] AI enhanced {len(result['validated_chapters'])} chapters")
                
    #             # Merge AI enhancements with original chapter data
    #             enhanced_chapters = []
    #             for i, original_chapter in enumerate(chapters):
    #                 if i < len(result['validated_chapters']):
    #                     ai_chapter = result['validated_chapters'][i]
    #                     enhanced_chapter = {
    #                         **original_chapter,  # Keep original data
    #                         "title": ai_chapter.get("title", original_chapter["title"]),
    #                         "summary": ai_chapter.get("summary", original_chapter.get("summary", ""))
    #                     }
    #                     enhanced_chapters.append(enhanced_chapter)
    #                 else:
    #                     enhanced_chapters.append(original_chapter)
                
    #             return enhanced_chapters
    #         else:
    #             print("[AI VALIDATION] AI returned no enhancements, using original chapters")
    #             return chapters
                
    #     except Exception as e:
    #         print(f"[AI VALIDATION] AI validation failed: {e}")
    #         return chapters

    async def _validate_chapters_with_ai(self, chapters: List[Dict], book_type: str) -> List[Dict[str, Any]]:
        """Validate and enhance chapters with AI using chunking to avoid token limits"""
        print(f"[AI VALIDATION] Validating {len(chapters)} chapters with AI...")
        
        CHUNK_SIZE = 10  # Process 10 chapters at a time instead of all 492
        validated_chapters = []
        
        try:
            if not self.ai_service.client:
                print("[AI VALIDATION] AI service not available, skipping validation")
                return chapters
            
            # Process chapters in chunks
            for i in range(0, len(chapters), CHUNK_SIZE):
                chunk = chapters[i:i + CHUNK_SIZE]
                chunk_num = i//CHUNK_SIZE + 1
                total_chunks = (len(chapters) + CHUNK_SIZE - 1) // CHUNK_SIZE
                
                print(f"[AI VALIDATION] Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} chapters)")
                
                # Prepare chapters for AI validation (reduced content)
                chapters_for_validation = []
                for chapter in chunk:
                    chapters_for_validation.append({
                        "title": chapter.get("title", ""),
                        "content": chapter.get("content", "")[:500],  # Limit content to 500 chars
                        "summary": chapter.get("summary", "")
                    })
                
                # Create shorter prompt for each chunk
                validation_prompt = f"""
                Please validate and enhance these {len(chunk)} {book_type} book chapters (chunk {chunk_num}/{total_chunks}). IMPORTANT: Return ONLY valid JSON with no additional text or formatting.
                
                For each chapter, ensure:
                1. Title is clear and descriptive
                2. Content is meaningful and substantial
                3. Summary is accurate (if provided)
                
                Return in this JSON format:
                {{
                    "validated_chapters": [
                        {{
                            "title": "Enhanced title",
                            "content": "Enhanced content preview...",
                            "summary": "Enhanced summary"
                        }}
                    ]
                }}
                
                Chapters to validate: {json.dumps(chapters_for_validation)}
                """
                
                try:
                    response = await self.ai_service.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": validation_prompt}],
                        max_tokens=2000,  # Reduced token limit
                        temperature=0.3
                    )
                    
                    result = json.loads(response.choices[0].message.content)
                    
                    if 'validated_chapters' in result and result['validated_chapters']:
                        print(f"[AI VALIDATION] Chunk {chunk_num} enhanced {len(result['validated_chapters'])} chapters")
                        
                        # Merge AI enhancements with original chapter data
                        for j, original_chapter in enumerate(chunk):
                            if j < len(result['validated_chapters']):
                                ai_chapter = result['validated_chapters'][j]
                                enhanced_chapter = {
                                    **original_chapter,  # Keep original data
                                    "title": ai_chapter.get("title", original_chapter.get("title", "")),
                                    "summary": ai_chapter.get("summary", original_chapter.get("summary", ""))
                                    # Keep original content, don't replace with truncated version
                                }
                                validated_chapters.append(enhanced_chapter)
                            else:
                                validated_chapters.append(original_chapter)
                    else:
                        print(f"[AI VALIDATION] Chunk {chunk_num} returned no enhancements, using original chapters")
                        validated_chapters.extend(chunk)
                        
                except Exception as chunk_error:
                    print(f"[AI VALIDATION] Chunk {chunk_num} failed: {chunk_error}")
                    # Add chapters without AI validation as fallback
                    validated_chapters.extend(chunk)
            
            print(f"[AI VALIDATION] Completed processing {len(validated_chapters)} chapters")
            return validated_chapters
            
        except Exception as e:
            print(f"[AI VALIDATION] Overall AI validation failed: {e}")
            return chapters


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