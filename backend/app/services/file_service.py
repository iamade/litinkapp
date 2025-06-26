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


class FileService:
    """File processing service for book uploads"""
    
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
            chapters = self.extract_chapters(content, book_type)
            
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

    def extract_learning_chapters(self, content: str) -> List[Dict[str, Any]]:
        """Extract chapters for learning content"""
        # Split by common learning content patterns
        patterns = [
            r'Chapter\s+\d+[:\s]*([^\n]+)',
            r'Lesson\s+\d+[:\s]*([^\n]+)',
            r'Unit\s+\d+[:\s]*([^\n]+)',
            r'Section\s+\d+[:\s]*([^\n]+)',
            r'Part\s+\d+[:\s]*([^\n]+)'
        ]
        
        chapters = []
        lines = content.split('\n')
        current_chapter = {"title": "Introduction", "content": "", "summary": ""}
        
        for line in lines:
            # Check if line matches any chapter pattern
            is_chapter_header = False
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Save previous chapter if it has content
                    if current_chapter["content"].strip():
                        chapters.append(current_chapter)
                    
                    # Start new chapter
                    current_chapter = {
                        "title": match.group(1).strip(),
                        "content": line + "\n",
                        "summary": ""
                    }
                    is_chapter_header = True
                    break
            
            if not is_chapter_header:
                current_chapter["content"] += line + "\n"
        
        # Add the last chapter
        if current_chapter["content"].strip():
            chapters.append(current_chapter)
        
        # If no chapters found, create a single chapter
        if not chapters:
            chapters = [{
                "title": "Complete Content",
                "content": content,
                "summary": ""
            }]
        
        return chapters

    def extract_entertainment_chapters(self, content: str) -> List[Dict[str, Any]]:
        """Extract chapters for entertainment content"""
        # Split by common story patterns
        patterns = [
            r'Chapter\s+\d+[:\s]*([^\n]+)',
            r'Scene\s+\d+[:\s]*([^\n]+)',
            r'Act\s+\d+[:\s]*([^\n]+)',
            r'Part\s+\d+[:\s]*([^\n]+)',
            r'Book\s+\d+[:\s]*([^\n]+)'
        ]
        
        chapters = []
        lines = content.split('\n')
        current_chapter = {"title": "Prologue", "content": "", "summary": ""}
        
        for line in lines:
            # Check if line matches any chapter pattern
            is_chapter_header = False
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Save previous chapter if it has content
                    if current_chapter["content"].strip():
                        chapters.append(current_chapter)
                    
                    # Start new chapter
                    current_chapter = {
                        "title": match.group(1).strip(),
                        "content": line + "\n",
                        "summary": ""
                    }
                    is_chapter_header = True
                    break
            
            if not is_chapter_header:
                current_chapter["content"] += line + "\n"
        
        # Add the last chapter
        if current_chapter["content"].strip():
            chapters.append(current_chapter)
        
        # If no chapters found, create a single chapter
        if not chapters:
            chapters = [{
                "title": "Complete Story",
                "content": content,
                "summary": ""
            }]
        
        return chapters

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