import aiofiles
from fastapi import UploadFile
from typing import Dict, Any
import os
import PyPDF2
import docx
from app.core.config import settings


class FileService:
    """File processing service for book uploads"""
    
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def process_book_file(self, file: UploadFile) -> str:
        """Process uploaded book file and extract text content"""
        # Save uploaded file
        file_path = os.path.join(self.upload_dir, file.filename)
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Extract text based on file type
        if file.filename.endswith('.pdf'):
            return await self._extract_pdf_text(file_path)
        elif file.filename.endswith('.docx'):
            return await self._extract_docx_text(file_path)
        elif file.filename.endswith('.txt'):
            return await self._extract_txt_text(file_path)
        else:
            raise ValueError("Unsupported file format")
    
    async def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            print(f"PDF extraction error: {e}")
            return "Error extracting PDF content"
    
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