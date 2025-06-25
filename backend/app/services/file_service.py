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

            # 3. Generate chapters using AI with chunking
            target_chapters = self._determine_target_chapters(content)
            chapters_data = self.generate_chapters_with_chunking(content, book_type, target_chapters=target_chapters, book_id=book_id)
            if not chapters_data or len(chapters_data) == 0:
                raise ValueError("AI failed to generate chapters after chunking.")

            # Update book progress
            update_data = {
                "progress": 3,
                "progress_message": f"Saving {len(chapters_data)} chapters...",
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

    def _extract_table_of_contents(self, content: str) -> list:
        """Extract table of contents from book content."""
        toc_patterns = [
            # Pattern for "Chapter X: Title" or "Part X: Title" (cleaner version)
            r'(?:Chapter|Part|Section)\s+(\d+)[:.\s]+([^\n\r.]+?)(?:\s*\.+\s*\d+)?$',
            # Pattern for numbered chapters "1. Title" or "I. Title" (cleaner version)
            r'^(\d+|[IVX]+)[:.\s]+([^\n\r.]+?)(?:\s*\.+\s*\d+)?$',
            # Pattern for "Contents" section with better extraction
            r'(?:Contents?|Table of Contents?)[\s\S]*?((?:Chapter|Part|Section)\s+\d+[:.\s]+[^\n\r.]+?(?:\s*\.+\s*\d+)?(?:\n(?:Chapter|Part|Section)\s+\d+[:.\s]+[^\n\r.]+?(?:\s*\.+\s*\d+)?)*)',
        ]
        
        toc_entries = []
        for pattern in toc_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    number = match.group(1)
                    title = match.group(2).strip()
                    
                    # Clean up the title
                    title = self._clean_chapter_title(title)
                    
                    # Skip if title is too short or contains obvious artifacts
                    if len(title) < 3 or self._is_title_artifact(title):
                        continue
                    
                    toc_entries.append({
                        'number': number,
                        'title': title,
                        'start_pos': match.start()
                    })
        
        # Sort by position in document
        toc_entries.sort(key=lambda x: x['start_pos'])
        
        # Remove duplicates based on title similarity
        unique_entries = []
        for entry in toc_entries:
            if not any(self._titles_similar(entry['title'], existing['title']) for existing in unique_entries):
                unique_entries.append(entry)
        
        return unique_entries

    def _clean_chapter_title(self, title: str) -> str:
        """Clean up chapter title by removing artifacts and formatting."""
        # Remove page numbers and dots at the end
        title = re.sub(r'\s*\.+\s*\d+\s*$', '', title)
        
        # Remove extra whitespace and dots
        title = re.sub(r'\s+', ' ', title)
        title = re.sub(r'\.+', '.', title)
        
        # Remove common PDF artifacts
        title = re.sub(r'[^\w\s\-:().]', '', title)
        
        # Clean up extra spaces
        title = title.strip()
        
        return title

    def _is_title_artifact(self, title: str) -> bool:
        """Check if a title is likely a PDF artifact."""
        # Check for common PDF artifacts
        artifact_patterns = [
            r'^\d+$',  # Just numbers
            r'^[IVX]+$',  # Just roman numerals
            r'^\s*\.+\s*$',  # Just dots
            r'^\s*[^\w\s]+\s*$',  # Just punctuation
            r'\.{3,}',  # Too many dots
        ]
        
        for pattern in artifact_patterns:
            if re.match(pattern, title):
                return True
        
        return False

    def _titles_similar(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar (to avoid duplicates)."""
        # Normalize titles for comparison
        norm1 = re.sub(r'\s+', ' ', title1.lower().strip())
        norm2 = re.sub(r'\s+', ' ', title2.lower().strip())
        
        # Check if one is contained in the other
        if norm1 in norm2 or norm2 in norm1:
            return True
        
        # Check for high similarity (simple approach)
        if len(norm1) > 10 and len(norm2) > 10:
            # Count common words
            words1 = set(norm1.split())
            words2 = set(norm2.split())
            common_words = words1.intersection(words2)
            
            if len(common_words) >= min(len(words1), len(words2)) * 0.7:
                return True
        
        return False

    def _split_content_by_toc(self, content: str, toc_entries: list) -> list:
        """Split content by table of contents entries."""
        if not toc_entries:
            return [content]  # Fallback to single chunk
        
        chunks = []
        for i, entry in enumerate(toc_entries):
            start_pos = entry['start_pos']
            end_pos = toc_entries[i + 1]['start_pos'] if i + 1 < len(toc_entries) else len(content)
            
            chunk_content = content[start_pos:end_pos].strip()
            if chunk_content:
                chunks.append({
                    'title': entry['title'],
                    'number': entry['number'],
                    'content': chunk_content
                })
        
        return chunks

    def _split_content_into_chunks(self, content: str, num_chunks: int) -> list:
        """Smart content splitting that respects book structure."""
        # First, try to extract table of contents
        toc_entries = self._extract_table_of_contents(content)
        
        if toc_entries and len(toc_entries) >= 3:  # If we found a reasonable TOC
            print(f"[Smart Chunking] Found {len(toc_entries)} TOC entries: {[e['title'] for e in toc_entries[:5]]}")
            chunks = self._split_content_by_toc(content, toc_entries)
            return chunks
        else:
            # Fallback to paragraph-based chunking with size limits
            print(f"[Smart Chunking] No TOC found, using paragraph-based chunking")
            paragraphs = content.split('\n\n')
            
            # Filter out empty paragraphs and very short ones
            paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 50]
            
            # Calculate target chunk size (aim for 5000-15000 characters per chunk)
            total_content_length = sum(len(p) for p in paragraphs)
            target_chunk_size = max(settings.MIN_CHUNK_SIZE, min(settings.MAX_CHUNK_SIZE, total_content_length // num_chunks))
            
            chunks = []
            current_chunk = []
            current_length = 0
            
            for paragraph in paragraphs:
                paragraph_length = len(paragraph)
                
                # If adding this paragraph would exceed target size and we have content, start new chunk
                if current_chunk and (current_length + paragraph_length > target_chunk_size):
                    chunk_content = '\n\n'.join(current_chunk)
                    if len(chunk_content) >= settings.MIN_CHUNK_SIZE:  # Minimum chunk size
                        chunks.append({
                            'title': f"Section {len(chunks) + 1}",
                            'number': str(len(chunks) + 1),
                            'content': chunk_content
                        })
                    current_chunk = [paragraph]
                    current_length = paragraph_length
                else:
                    current_chunk.append(paragraph)
                    current_length += paragraph_length
            
            # Add the last chunk if it has content
            if current_chunk:
                chunk_content = '\n\n'.join(current_chunk)
                if len(chunk_content) >= settings.MIN_CHUNK_SIZE:  # Minimum chunk size
                    chunks.append({
                        'title': f"Section {len(chunks) + 1}",
                        'number': str(len(chunks) + 1),
                        'content': chunk_content
                    })
            
            # If we still have too many chunks, merge them
            if len(chunks) > num_chunks * 2:
                print(f"[Smart Chunking] Too many chunks ({len(chunks)}), merging...")
                chunks = self._merge_small_chunks(chunks, num_chunks)
            
            # Limit the total number of chunks
            if len(chunks) > settings.MAX_CHUNKS_PER_BOOK:
                print(f"[Smart Chunking] Limiting chunks to {settings.MAX_CHUNKS_PER_BOOK} (from {len(chunks)})")
                chunks = chunks[:settings.MAX_CHUNKS_PER_BOOK]
            
            print(f"[Smart Chunking] Created {len(chunks)} chunks with average size {sum(len(c['content']) for c in chunks) // len(chunks) if chunks else 0} chars")
            return chunks

    def _merge_small_chunks(self, chunks: list, target_count: int) -> list:
        """Merge small chunks to reduce total count."""
        if len(chunks) <= target_count:
            return chunks
        
        merged_chunks = []
        current_chunk = chunks[0]['content']
        current_title = chunks[0]['title']
        
        for i in range(1, len(chunks)):
            # If merging would create a chunk under 15000 chars and we're under target, merge
            if (len(current_chunk) + len(chunks[i]['content']) < 15000 and 
                len(merged_chunks) + 1 < target_count):
                current_chunk += '\n\n' + chunks[i]['content']
                current_title = f"{current_title} & {chunks[i]['title']}"
            else:
                # Save current chunk and start new one
                merged_chunks.append({
                    'title': current_title,
                    'number': str(len(merged_chunks) + 1),
                    'content': current_chunk
                })
                current_chunk = chunks[i]['content']
                current_title = chunks[i]['title']
        
        # Add the last chunk
        if current_chunk:
            merged_chunks.append({
                'title': current_title,
                'number': str(len(merged_chunks) + 1),
                'content': current_chunk
            })
        
        return merged_chunks

    def _is_valid_chapter_list(self, chapters):
        """Basic validation for AI chapter output."""
        return (
            isinstance(chapters, list) and
            all(isinstance(ch, dict) and 'title' in ch and 'content' in ch for ch in chapters)
        )

    def _update_book_progress(self, book_id: str, progress: int, message: str):
        """Update book progress in database."""
        try:
            update_data = {
                "progress": progress,
                "progress_message": message,
            }
            self.db.table("books").update(update_data).eq("id", book_id).execute()
        except Exception as e:
            print(f"Error updating progress: {e}")

    def generate_chapters_with_chunking(self, content: str, book_type: str, target_chapters: int = 12, max_retries: int = 2, book_id: str = None) -> list:
        """
        Smart chunking that respects book structure and generates chapters.
        """
        print(f"[Smart Chunking] Starting chapter generation for {book_type} book")
        
        # Get smart chunks based on book structure
        chunks = self._split_content_into_chunks(content, target_chapters)
        print(f"[Smart Chunking] Split into {len(chunks)} chunks based on book structure")
        
        # Limit the number of chunks to process to prevent excessive processing
        max_chunks = min(len(chunks), target_chapters * 2)  # Max 2x target chapters
        if len(chunks) > max_chunks:
            print(f"[Smart Chunking] Limiting processing to {max_chunks} chunks (from {len(chunks)})")
            chunks = chunks[:max_chunks]
        
        all_chapters = []
        total_chunks = len(chunks)
        
        for idx, chunk_data in enumerate(chunks):
            chunk_title = chunk_data['title']
            chunk_content = chunk_data['content']
            chunk_number = chunk_data['number']
            
            # Update progress if book_id is provided
            if book_id:
                progress_percent = int((idx / total_chunks) * 100)
                self._update_book_progress(book_id, 2, f"Processing chunk {idx+1}/{total_chunks} ({progress_percent}%)")
            
            # Skip chunks that are too small
            if len(chunk_content) < settings.MIN_CHUNK_SIZE:
                print(f"[Smart Chunking] Skipping chunk {idx+1}/{total_chunks}: too small ({len(chunk_content)} chars)")
                continue
            
            print(f"[Smart Chunking] Processing chunk {idx+1}/{total_chunks}: '{chunk_title}' (length: {len(chunk_content)} chars)")
            
            try:
                # Create a more specific prompt for this chunk
                prompt_context = f"""
                This is {chunk_title} (Section {chunk_number}) from a {book_type} book.
                Generate 1-3 chapters from this section, maintaining the original structure and content.
                Focus on the key concepts and learning objectives for this section.
                """
                
                # For now, use the existing AI service but with better context
                chapters = self.ai_service.generate_chapters_from_content_sync(chunk_content, book_type)
                
                if not self._is_valid_chapter_list(chapters):
                    print(f"[Smart Chunking] Invalid chapter list for chunk {idx+1}, got: {chapters}")
                    # Create a fallback chapter from the chunk
                    chapters = [{
                        'title': chunk_title,
                        'content': chunk_content[:2000] + "..." if len(chunk_content) > 2000 else chunk_content
                    }]
                
                # Add chunk context to chapter titles
                for chapter in chapters:
                    if not chapter['title'].startswith(chunk_title):
                        chapter['title'] = f"{chunk_title}: {chapter['title']}"
                
                # Ensure unique chapter titles
                used_titles = set()
                for chapter in chapters:
                    original_title = chapter['title']
                    counter = 1
                    while chapter['title'] in used_titles:
                        chapter['title'] = f"{original_title} (Part {counter})"
                        counter += 1
                    used_titles.add(chapter['title'])
                
                all_chapters.extend(chapters)
                print(f"[Smart Chunking] Generated {len(chapters)} chapters from chunk {idx+1}")
                
                # Stop early if we have enough chapters
                if len(all_chapters) >= target_chapters:
                    print(f"[Smart Chunking] Reached target chapter count ({len(all_chapters)}), stopping early")
                    break
                
            except Exception as e:
                print(f"[Smart Chunking] Error processing chunk {idx+1}: {e}")
                # Create a fallback chapter
                fallback_chapter = {
                    'title': chunk_title,
                    'content': chunk_content[:2000] + "..." if len(chunk_content) > 2000 else chunk_content
                }
                all_chapters.append(fallback_chapter)
        
        print(f"[Smart Chunking] Total chapters generated: {len(all_chapters)}")
        
        # Final cleanup: ensure proper chapter numbering and clean titles
        all_chapters = self._finalize_chapters(all_chapters, target_chapters)
        
        # If we have too many chapters, try to consolidate
        if len(all_chapters) > target_chapters * 1.5:
            print(f"[Smart Chunking] Too many chapters ({len(all_chapters)}), consolidating...")
            all_chapters = self._consolidate_chapters(all_chapters, target_chapters)
        
        return all_chapters if all_chapters else self.ai_service._get_mock_chapters(book_type)

    def _finalize_chapters(self, chapters: list, target_count: int) -> list:
        """Final cleanup of chapters to ensure proper numbering and clean titles."""
        if not chapters:
            return chapters
        
        # Limit to target count or maximum allowed chapters
        max_chapters = min(target_count, settings.MAX_CHAPTERS_PER_BOOK)
        if len(chapters) > max_chapters:
            print(f"[Smart Chunking] Limiting to {max_chapters} chapters (from {len(chapters)})")
            chapters = chapters[:max_chapters]
        
        # Clean up titles and ensure proper numbering
        for i, chapter in enumerate(chapters):
            # Clean the title
            chapter['title'] = self._clean_chapter_title(chapter['title'])
            
            # Ensure title is not empty
            if not chapter['title'].strip():
                chapter['title'] = f"Chapter {i+1}"
            
            # Remove any remaining page numbers or artifacts
            chapter['title'] = re.sub(r'\s*\.+\s*\d+\s*$', '', chapter['title'])
            chapter['title'] = re.sub(r'\s+', ' ', chapter['title']).strip()
            
            # Ensure proper chapter numbering
            if not chapter['title'].startswith(f"Chapter {i+1}"):
                chapter['title'] = f"Chapter {i+1}: {chapter['title']}"
        
        return chapters

    def _consolidate_chapters(self, chapters: list, target_count: int) -> list:
        """Consolidate chapters to reach target count."""
        if len(chapters) <= target_count:
            return chapters
        
        # Simple consolidation: merge adjacent chapters
        consolidated = []
        merge_ratio = len(chapters) // target_count
        
        for i in range(0, len(chapters), merge_ratio):
            group = chapters[i:i+merge_ratio]
            if group:
                merged_chapter = {
                    'title': f"Chapter {len(consolidated) + 1}: {group[0]['title']}",
                    'content': '\n\n'.join([ch['content'] for ch in group])
                }
                consolidated.append(merged_chapter)
        
        return consolidated[:target_count]

    def _determine_target_chapters(self, content: str) -> int:
        """
        Dynamically determine the target number of chapters from book content.
        Uses a hybrid approach: TOC extraction -> content analysis -> AI fallback.
        """
        print("[Chapter Detection] Analyzing book content to determine target chapters...")
        
        # Method 1: Extract from Table of Contents
        toc_chapters = self._extract_table_of_contents(content)
        if toc_chapters and len(toc_chapters) > 0:
            target_count = len(toc_chapters)
            print(f"[Chapter Detection] Found {target_count} chapters from Table of Contents")
            return min(target_count, settings.MAX_CHAPTERS_PER_BOOK)
        
        # Method 2: Content analysis - look for chapter patterns
        chapter_patterns = self._find_chapter_patterns(content)
        if chapter_patterns and len(chapter_patterns) > 0:
            target_count = len(chapter_patterns)
            print(f"[Chapter Detection] Found {target_count} chapters from content analysis")
            return min(target_count, settings.MAX_CHAPTERS_PER_BOOK)
        
        # Method 3: Estimate based on content length and book type
        estimated_chapters = self._estimate_chapters_by_length(content)
        print(f"[Chapter Detection] Estimated {estimated_chapters} chapters based on content length")
        return min(estimated_chapters, settings.MAX_CHAPTERS_PER_BOOK)
    
    def _find_chapter_patterns(self, content: str) -> list:
        """
        Find chapter patterns in content using regex and text analysis.
        """
        chapter_patterns = []
        
        # Common chapter patterns
        patterns = [
            r'^Chapter\s+\d+[:\s]*(.+?)$',  # Chapter 1: Title
            r'^CHAPTER\s+\d+[:\s]*(.+?)$',  # CHAPTER 1: Title
            r'^\d+\.\s+(.+?)$',             # 1. Title
            r'^Part\s+\d+[:\s]*(.+?)$',     # Part 1: Title
            r'^Section\s+\d+[:\s]*(.+?)$',  # Section 1: Title
            r'^Unit\s+\d+[:\s]*(.+?)$',     # Unit 1: Title
        ]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) < 10 or len(line) > 200:  # Skip very short or very long lines
                continue
                
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    title = match.group(1).strip() if len(match.groups()) > 0 else line
                    # Clean the title
                    title = re.sub(r'^\d+\.\s*', '', title)  # Remove leading numbers
                    title = re.sub(r'\s+', ' ', title).strip()  # Clean whitespace
                    
                    if title and len(title) > 3 and not self._is_title_artifact(title):
                        chapter_patterns.append({
                            'title': title,
                            'line': line
                        })
                    break
        
        # Remove duplicates and sort by appearance in text
        unique_chapters = []
        seen_titles = set()
        for chapter in chapter_patterns:
            normalized_title = self._normalize_title(chapter['title'])
            if normalized_title not in seen_titles:
                seen_titles.add(normalized_title)
                unique_chapters.append(chapter)
        
        return unique_chapters
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for duplicate detection."""
        # Remove common prefixes and normalize
        normalized = re.sub(r'^(Chapter|CHAPTER|Part|Section|Unit)\s+\d+[:\s]*', '', title, flags=re.IGNORECASE)
        normalized = re.sub(r'^\d+\.\s*', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip().lower()
        return normalized
    
    def _estimate_chapters_by_length(self, content: str) -> int:
        """
        Estimate number of chapters based on content length and typical chapter sizes.
        """
        content_length = len(content)
        
        # Typical chapter sizes (in characters) for different book types
        # These are rough estimates based on common book structures
        typical_chapter_sizes = {
            'technical': 15000,    # Technical books often have longer chapters
            'educational': 12000,  # Educational books
            'fiction': 8000,       # Fiction books
            'non-fiction': 10000,  # General non-fiction
            'academic': 18000,     # Academic books
        }
        
        # Default to educational if unknown
        avg_chapter_size = typical_chapter_sizes.get('educational', 12000)
        
        # Calculate estimated chapters
        estimated = max(1, content_length // avg_chapter_size)
        
        # Apply reasonable bounds
        estimated = max(3, estimated)  # Minimum 3 chapters
        estimated = min(estimated, settings.MAX_CHAPTERS_PER_BOOK)  # Maximum from config
        
        return estimated