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


class FileService:
    """File processing service for book uploads"""
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        # Initialize a new Supabase client with the service role key for backend operations
        self.db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        self.ai_service = AIService()
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def process_uploaded_book(
        self,
        storage_path: Optional[str],
        original_filename: Optional[str],
        text_content: Optional[str],
        book_type: str,
        user_id: str,
        book_id_to_update: str,
    ) -> None:
        """Orchestrates the entire book processing flow for a given book ID."""
        
        book_id = book_id_to_update

        try:
            # Update status to PROCESSING
            update_data = {
                "status": "PROCESSING",
                "progress": 1,
                "total_steps": 4,
                "progress_message": "Extracting content...",
            }
            self.db.table("books").update(update_data).eq("id", book_id).execute()

            # 2. Extract content from file or use provided text
            if storage_path and original_filename:
                # Download file from Supabase Storage to a temporary location
                with tempfile.NamedTemporaryFile(delete=False, suffix=original_filename) as temp_file:
                    file_content = self.db.storage.from_(settings.SUPABASE_BUCKET_NAME).download(path=storage_path)
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name

                extracted_data = self.process_book_file(temp_file_path, original_filename)
                
                # Clean up the temporary file
                os.unlink(temp_file_path)

                content = extracted_data.get("text", "")
                author_name = extracted_data.get("author")
                cover_path = extracted_data.get("cover_image_path")
            else:
                content = text_content
                author_name = None
                cover_path = None

            if not content or content.isspace():
                raise ValueError("Extracted content is empty.")

            # Update book with extracted info and progress
            update_data = {
                "author_name": author_name,
                "cover_image_path": cover_path.replace(self.upload_dir, "/uploads") if cover_path else None,
                "status": "GENERATING",
                "progress": 2,
                "progress_message": "Generating chapters with AI...",
            }
            self.db.table("books").update(update_data).eq("id", book_id).execute()

            # 3. Generate chapters using AI
            chapters_data = self.ai_service.generate_chapters_from_content_sync(
                content, book_type
            )
            if not chapters_data:
                raise ValueError("AI failed to generate chapters.")

            # Update book progress
            update_data = {
                "progress": 3,
                "progress_message": "Saving chapters...",
            }
            self.db.table("books").update(update_data).eq("id", book_id).execute()

            # 4. Save chapters to the database, with strict error checking
            for i, chap_data in enumerate(chapters_data):
                # First, validate the chapter data from the AI service
                validated_chapter = ChapterCreate(
                    chapter_number=i + 1,
                    title=chap_data.get("title", f"Chapter {i+1}"),
                    content=chap_data.get("content", "No content available."),
                )

                # Then, create the full payload for the database insert
                insert_payload = validated_chapter.dict()
                insert_payload['book_id'] = book_id

                response = self.db.table("chapters").insert(insert_payload).execute()

                # CRITICAL: If the insert call succeeds but returns no data, it's a silent failure.
                # Raise an exception to force the book status to FAILED.
                if not response.data:
                    error_detail = getattr(response, 'error', 'No error details provided.')
                    raise Exception(f"Failed to insert chapter {i+1}. The database returned no data. Details: {error_detail}")

            # 5. Finalize book processing
            final_update = {
                "total_chapters": len(chapters_data),
                "status": "READY",
                "progress": 4,
                "progress_message": "Book is ready!",
            }
            db_response = (
                self.db.table("books")
                .update(final_update)
                .eq("id", book_id)
                .execute()
            )
            
            # Fetch the final book object with its chapters
            final_book = self.db.table("books").select("*, chapters(*)").eq("id", book_id).single().execute()
            return final_book.data

        except Exception as e:
            print(f"Error processing book {book_id}: {e}")
            error_update = {
                "status": "FAILED",
                "progress_message": "An error occurred during processing.",
                "error_message": str(e),
            }
            self.db.table("books").update(error_update).eq("id", book_id).execute()
            # Do not re-raise, as this is a background task
    
    def process_book_file(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Process book file from its path and extract text, author, cover, chapters"""
        if filename.endswith('.pdf'):
            return self._extract_pdf_info(file_path)
        elif filename.endswith('.docx'):
            text = self._extract_docx_text(file_path)
            return {"text": text, "author": None, "cover_image_path": None, "chapters": []}
        elif filename.endswith('.txt'):
            text = self._extract_txt_text(file_path)
            return {"text": text, "author": None, "cover_image_path": None, "chapters": []}
        else:
            raise ValueError("Unsupported file format")
    
    def _extract_pdf_info(self, file_path: str) -> Dict[str, Any]:
        """Extract text, author, cover image from PDF file"""
        author = None
        cover_image_path = None
        text = ""
        
        # Extract author and text using PyPDF2
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                # Extract author from metadata
                if pdf_reader.metadata and pdf_reader.metadata.author:
                    author = pdf_reader.metadata.author
        except Exception as e:
            print(f"PDF extraction error: {e}")
        
        # If author not found in metadata, try to extract from bold/large text in first 2 pages
        if not author:
            try:
                doc = fitz.open(file_path)
                for page_num in range(min(2, len(doc))):
                    page = doc[page_num]
                    blocks = page.get_text("dict")['blocks']
                    for block in blocks:
                        if 'lines' in block:
                            for line in block['lines']:
                                for span in line['spans']:
                                    text_span = span['text'].strip()
                                    is_bold = 'bold' in span['font'].lower() or span['flags'] & 2**4 != 0
                                    is_large = span['size'] > 14  # Adjust threshold as needed
                                    # Heuristic: bold or large text, not too long, not all caps
                                    if text_span and (is_bold or is_large) and 3 < len(text_span) < 50 and not text_span.isupper():
                                        # Prefer lines starting with 'by '
                                        if text_span.lower().startswith('by '):
                                            author = text_span[3:].strip()
                                            break
                                        # Or just take the first bold/large line as author
                                        if not author:
                                            author = text_span
                                if author:
                                    break
                        if author:
                            break
                    if author:
                        break
            except Exception as e:
                print(f"Author extraction from text failed: {e}")
        
        # Extract cover image using PyMuPDF
        try:
            doc = fitz.open(file_path)
            # Extract cover image from first 4 pages
            for page_num in range(min(4, len(doc))):
                page = doc[page_num]
                images = page.get_images(full=True)
                if images:
                    xref = images[0][0]
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n < 5:  # this is GRAY or RGB
                        cover_image_path = os.path.join(self.upload_dir, f"cover_{os.path.basename(file_path)}.png")
                        pix.save(cover_image_path)
                        break
                    else:  # CMYK: convert to RGB first
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                        cover_image_path = os.path.join(self.upload_dir, f"cover_{os.path.basename(file_path)}.png")
                        pix.save(cover_image_path)
                        break
        except Exception as e:
            print(f"PyMuPDF extraction error: {e}")

        return {
            "text": text,
            "author": author,
            "cover_image_path": cover_image_path
        }
    
    def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            print(f"DOCX extraction error: {e}")
            return "Error extracting DOCX content"
    
    def _extract_txt_text(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"TXT extraction error: {e}")
            return "Error extracting TXT content"
    
    def save_audio_file(self, audio_data: bytes, filename: str) -> str:
        """Save audio file and return URL"""
        audio_path = os.path.join(self.upload_dir, "audio", filename)
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        
        with open(audio_path, 'wb') as f:
            f.write(audio_data)
        
        audio_url = f"/uploads/audio/{filename}"
        return audio_url
    
    def save_video_file(self, video_data: bytes, filename: str) -> str:
        """Save video file and return URL"""
        video_path = os.path.join(self.upload_dir, "video", filename)
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        
        with open(video_path, 'wb') as f:
            f.write(video_data)
        
        video_url = f"/uploads/video/{filename}"
        return video_url