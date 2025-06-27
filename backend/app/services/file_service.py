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


class FileService:
    """File processing service for book uploads"""
    MAX_CHAPTERS = 50
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        # Initialize a new Supabase client with the service role key for backend operations
        self.db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        self.ai_service = AIService()
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

                extracted_data = self.process_book_file(temp_file_path, original_filename)
                content = extracted_data.get("text", "")
                author_name = extracted_data.get("author")
                cover_path = extracted_data.get("cover_image_path")

                # --- TOC-based chapter extraction for PDF using real page numbers ---
                chapters_data = None
                if original_filename.lower().endswith('.pdf'):
                    chapters_data = self.extract_chapters_from_pdf_with_toc(temp_file_path)

                # Clean up temporary file
                os.unlink(temp_file_path)
            else:
                raise ValueError("No content provided")

            # Update book with extracted content
            self.db.table("books").update({
                "content": content,
                "status": "PROCESSING"
            }).eq("id", book_id_to_update).execute()

            # Extract chapters
            chapters = await self.extract_chapters_with_ai_validation(content, book_type)
            
            # Create chapters in database
            for i, chapter_data in enumerate(chapters):
                # Manually construct the insert data to ensure book_id is included
                insert_data = {
                    "book_id": book_id_to_update,
                    "chapter_number": i + 1,
                    "title": chapter_data["title"],
                    "content": chapter_data["content"],
                    "summary": chapter_data.get("summary", "")
                }
                
                # Insert chapter
                chapter_response = self.db.table("chapters").insert(insert_data).execute()
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

    def process_book_file(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Process different file types and extract content"""
        try:
            if filename.lower().endswith('.pdf'):
                return self.process_pdf(file_path)
            elif filename.lower().endswith('.docx'):
                return self.process_docx(file_path)
            elif filename.lower().endswith('.txt'):
                return self.process_txt(file_path)
            else:
                raise ValueError(f"Unsupported file type: {filename}")
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            raise

    def process_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extract text and metadata from PDF"""
        try:
            doc = fitz.open(file_path)
            text = ""
            author = None
            
            for page in doc:
                text += page.get_text()
            
            # Try to extract author from metadata
            metadata = doc.metadata
            if metadata and metadata.get('author'):
                author = metadata['author']
            
            doc.close()
            
            return {
                "text": text,
                "author": author,
                "cover_image_path": None
            }
        except Exception as e:
            print(f"Error processing PDF: {e}")
            raise

    def process_docx(self, file_path: str) -> Dict[str, Any]:
        """Extract text from DOCX"""
        try:
            doc = docx.Document(file_path)
            text = ""
            
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return {
                "text": text,
                "author": None,
                "cover_image_path": None
            }
        except Exception as e:
            print(f"Error processing DOCX: {e}")
            raise

    def process_txt(self, file_path: str) -> Dict[str, Any]:
        """Extract text from TXT"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            
            return {
                "text": text,
                "author": None,
                "cover_image_path": None
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
                        if not self._is_duplicate_chapter(current_chapter, chapters):
                            chapters.append(current_chapter)
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
        if len(chapters) < self.MAX_CHAPTERS and current_chapter["content"].strip():
            if not self._is_duplicate_chapter(current_chapter, chapters):
                chapters.append(current_chapter)
        if not chapters:
            chapters = [{
                "title": "Complete Content",
                "content": content,
                "summary": ""
            }]
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
                    if current_chapter["content"].strip():
                        if not self._is_duplicate_chapter(current_chapter, chapters):
                            chapters.append(current_chapter)
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
        if len(chapters) < self.MAX_CHAPTERS and current_chapter["content"].strip():
            if not self._is_duplicate_chapter(current_chapter, chapters):
                chapters.append(current_chapter)
        if not chapters:
            chapters = [{
                "title": "Complete Story",
                "content": content,
                "summary": ""
            }]
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
        """Use AI to validate and improve chapter extraction"""
        try:
            if not self.ai_service.client:
                print("AI service not available, skipping validation")
                return chapters
            
            # Create a validation prompt
            validation_prompt = f"""
You are an expert book editor. Review the extracted chapters and validate their correctness.

Book Type: {book_type}
Total Book Content Length: {len(book_content)} characters

EXTRACTED CHAPTERS:
{json.dumps(chapters, indent=2)}

VALIDATION TASKS:
1. Check if chapters are properly separated (no overlap)
2. Verify chapter titles match their content
3. Ensure front matter (cover, TOC, preface) is not included in chapters
4. Confirm each chapter has substantial, relevant content
5. Identify any missing chapters or content

If issues are found, provide corrected chapter structure.
Return JSON with 'validated_chapters' array and 'issues' array.
"""
            
            response = await self.ai_service.client.chat.completions.create(
                model="gpt-3.5-turbo-1106",
                messages=[
                    {"role": "system", "content": "You are an expert book editor and content validator."},
                    {"role": "user", "content": validation_prompt}
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

    async def extract_chapters_with_ai_validation(self, content: str, book_type: str) -> List[Dict[str, Any]]:
        """Extract chapters and validate with AI"""
        # First extract chapters using regex
        chapters = self.extract_chapters_with_structure(content, book_type)
        
        # Then validate with AI
        validated_chapters = await self.validate_chapters_with_ai(chapters, content, book_type)
        
        return validated_chapters