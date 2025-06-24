from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ChapterBase(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    duration: Optional[int] = None


class ChapterCreate(ChapterBase):
    chapter_number: int


class Chapter(ChapterBase):
    id: str
    book_id: str
    chapter_number: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BookBase(BaseModel):
    title: str
    author_name: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    book_type: str
    difficulty: Optional[str] = "medium"
    tags: Optional[List[str]] = None
    language: Optional[str] = "en"


class BookCreate(BookBase):
    user_id: str
    status: str
    book_type: str


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


class ChapterDraft(BaseModel):
    title: str
    content: str


class BookWithDraftChapters(BookBase):
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