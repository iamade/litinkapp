import aiofiles
from fastapi import UploadFile
from typing import Dict, Any, Optional, List
import os
import PyPDF2
import docx
import fitz  # PyMuPDF
from app.core.config import settings
import re


class FileService:
    """File processing service for book uploads"""
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def process_book_file(self, file: UploadFile) -> Dict[str, Any]:
        """Process uploaded book file and extract text, author, cover, chapters"""
        file_path = os.path.join(self.upload_dir, file.filename)
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        if file.filename.endswith('.pdf'):
            return await self._extract_pdf_info(file_path)
        elif file.filename.endswith('.docx'):
            text = await self._extract_docx_text(file_path)
            return {"text": text, "author": None, "cover_image_path": None, "chapters": []}
        elif file.filename.endswith('.txt'):
            text = await self._extract_txt_text(file_path)
            return {"text": text, "author": None, "cover_image_path": None, "chapters": []}
        else:
            raise ValueError("Unsupported file format")
    
    async def _extract_pdf_info(self, file_path: str) -> Dict[str, Any]:
        """Extract text, author, cover image, and chapters from PDF file"""
        author = None
        cover_image_path = None
        chapters: List[Dict[str, str]] = []
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
            
        # Extract cover image and chapters using PyMuPDF
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

            # Try multiple methods to extract chapters
            # 1. First try TOC
            toc = doc.get_toc()
            if toc:
                chapters = [{"title": entry[1], "content": ""} for entry in toc if entry[1]]
            else:
                # 2. If no TOC, analyze text formatting
                potential_chapters = []
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    blocks = page.get_text("dict")["blocks"]
                    
                    for block in blocks:
                        if "lines" in block:
                            for line in block["lines"]:
                                for span in line["spans"]:
                                    text = span["text"].strip()
                                    # Check if this might be a chapter title:
                                    # 1. Text is bold or larger than normal
                                    # 2. Starts with common chapter indicators
                                    # 3. Not too long (chapter titles are usually brief)
                                    is_bold = "bold" in span["font"].lower() or span["flags"] & 2**4 != 0
                                    is_large = span["size"] > 12  # Adjust threshold as needed
                                    starts_with_chapter = any(text.lower().startswith(x) for x in ["chapter", "section", "part"])
                                    has_number_prefix = bool(re.match(r"^\d+\.?\s+", text))
                                    
                                    if text and len(text) < 100 and (
                                        (is_bold or is_large) and (starts_with_chapter or has_number_prefix)
                                    ):
                                        potential_chapters.append({"title": text, "content": ""})

                if potential_chapters:
                    chapters = potential_chapters
                else:
                    # 3. Fallback: look for chapter patterns in text
                    chapter_patterns = [
                        r"Chapter\s+\d+[:\s\-]+[A-Za-z0-9 ,.'\-]+",
                        r"\d+\.\s+[A-Z][A-Za-z0-9 ,.'\-]+",
                        r"CHAPTER\s+[A-Z0-9]+[:\s\-]+[A-Za-z0-9 ,.'\-]+"
                    ]
                    for pattern in chapter_patterns:
                        found_chapters = re.findall(pattern, text)
                        if found_chapters:
                            chapters = [{"title": title.strip(), "content": ""} for title in found_chapters]
                            break

        except Exception as e:
            print(f"PyMuPDF extraction error: {e}")

        return {
            "text": text,
            "author": author,
            "cover_image_path": cover_image_path,
            "chapters": chapters
        }
    
    async def _extract_docx_text(self, file_path: str) -> str:
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
    
    async def _extract_txt_text(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                return await file.read()
        except Exception as e:
            print(f"TXT extraction error: {e}")
            return "Error extracting TXT content"
    
    async def save_audio_file(self, audio_data: bytes, filename: str) -> str:
        """Save audio file and return URL"""
        audio_path = os.path.join(self.upload_dir, "audio", filename)
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        
        async with aiofiles.open(audio_path, 'wb') as f:
            await f.write(audio_data)
        
        return f"/uploads/audio/{filename}"
    
    async def save_video_file(self, video_data: bytes, filename: str) -> str:
        """Save video file and return URL"""
        video_path = os.path.join(self.upload_dir, "video", filename)
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        
        async with aiofiles.open(video_path, 'wb') as f:
            await f.write(video_data)
        
        return f"/uploads/video/{filename}"