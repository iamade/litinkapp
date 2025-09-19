from pydantic import BaseModel
from typing import Any, Dict, Optional, List
from datetime import datetime


# Add these after the existing schemas, before the end of the file

class SectionBase(BaseModel):
    title: str
    section_type: str  # "part", "tablet", "book", "section"
    section_number: str  # "1", "I", "III", etc.
    order_index: int
    description: Optional[str] = None


class SectionCreate(SectionBase):
    book_id: str


class Section(SectionBase):
    id: str
    book_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChapterInput(BaseModel):
    title: str
    content: str = ""
    chapter_number: Optional[int] = None
    summary: Optional[str] = ""
    order_index: Optional[int] = None
    
    # Section-related fields for hierarchical books
    section_title: Optional[str] = None
    section_type: Optional[str] = None  # "part", "tablet", "book", "section"
    section_number: Optional[str] = None  # "1", "I", "III", etc.
    section_id: Optional[str] = None  # Foreign key reference


class SectionInput(BaseModel):
    title: str
    section_type: str  # "part", "tablet", "book", "section"
    section_number: str  # "1", "I", "III", etc.
    order_index: int
    description: Optional[str] = None
    

class BookStructureInput(BaseModel):
    structure_type: Optional[str] = "flat"
    has_sections: Optional[bool] = False
    sections: Optional[List[Dict[str, Any]]] = []
    chapters: Optional[List[Dict[str, Any]]] = []
    structure_metadata: Optional[Dict[str, Any]] = {}  # Add this
    
    class Config:
        schema_extra = {
            "example": {
                "structure_type": "tablet",
                "has_sections": True,
                "structure_metadata": {
                    "display_name": "Tablet Structure",
                    "icon": "🏺",
                    "section_label": "Tablet",
                    "chapter_label": "Section"
                },
                "sections": [
                    {
                        "title": "Tablet I: The Wild Man",
                        "section_type": "tablet",
                        "section_number": "I",
                        "order_index": 1
                    }
                ]
            }
        }


# class BookStructureInput(BaseModel):
#     structure_type: Optional[str] = "flat"  # "flat", "hierarchical"
#     has_sections: Optional[bool] = False
#     sections: Optional[List[Dict[str, Any]]] = []
#     chapters: Optional[List[Dict[str, Any]]] = []
    
#     # Add this method if it's missing
#     def get(self, key: str, default=None):
#         """Add dict-like get method for backward compatibility"""
#         return getattr(self, key, default)
    
#     class Config:
#         schema_extra = {
#             "example": {
#                 "structure_type": "hierarchical",
#                 "has_sections": True,
#                 "sections": [
#                     {
#                         "title": "Part I: Introduction",
#                         "section_type": "part",
#                         "section_number": "I",
#                         "order_index": 1
#                     }
#                 ],
#                 "chapters": [
#                     {
#                         "title": "Chapter 1: Getting Started",
#                         "content": "Chapter content here...",
#                         "chapter_number": 1,
#                         "section_title": "Part I: Introduction",
#                         "section_type": "part",
#                         "section_number": "I"
#                     }
#                 ]
#             }
#         }
        

class ChapterBase(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    duration: Optional[int] = None


class Chapter(ChapterBase):
    id: str
    book_id: str
    chapter_number: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



# Enhanced Chapter with section relationship
class ChapterWithSection(Chapter):
    section_id: Optional[str] = None
    section: Optional[Section] = None


class BookBase(BaseModel):
    title: str
    author_name: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    book_type: str
    difficulty: Optional[str] = "medium"
    tags: Optional[List[str]] = None
    language: Optional[str] = "en"



class Book(BookBase):
    id: str
    user_id: Optional[str] = None
    status: str
    total_chapters: int
    estimated_duration: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    chapters: Optional[List[Chapter]] = None
    
    class Config:
        from_attributes = True

# ✅ ADD: New preview schema that extends Book
class BookPreview(Book):
    """Book with preview chapters (not saved to database yet)"""
    preview_chapters: Optional[List[dict]] = None
    total_preview_chapters: Optional[int] = None
    author_name: Optional[str] = None  # From extraction
    cover_image_url: Optional[str] = None  # From extraction


# Enhanced Book with sections
class BookWithSections(Book):
    has_sections: Optional[bool] = False
    structure_type: Optional[str] = "flat"
    sections: Optional[List[Section]] = []
    chapters: Optional[List[ChapterWithSection]] = []




class ChapterCreate(ChapterBase):
    chapter_number: int
    book_id: str


class BookCreate(BookBase):
    user_id: str
    status: str
    book_type: str
    original_file_storage_path: Optional[str] = None


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author_name: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    book_type: Optional[str] = None
    difficulty: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    language: Optional[str] = None
    estimated_duration: Optional[int] = None
    original_file_storage_path: Optional[str] = None


class ChapterDraft(BaseModel):
    title: str
    content: str


class BookWithChapters(Book):
    chapters: List[Chapter] = []


class BookWithDraftChapters(Book):
    id: str
    user_id: Optional[str] = None
    status: str
    total_chapters: int
    estimated_duration: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    chapters: Optional[List[ChapterDraft]] = None

    class Config:
        from_attributes = True