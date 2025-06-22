from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, get_current_author
from app.core.database import get_db
from app.models.user import User
from app.models.book import Book, Chapter, BookType, BookStatus
from app.schemas.book import Book as BookSchema, BookCreate, BookUpdate, Chapter as ChapterSchema, ChapterCreate
from app.services.ai_service import AIService
from app.services.file_service import FileService

router = APIRouter()


@router.get("/", response_model=List[BookSchema])
async def get_books(
    book_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get published books"""
    book_type_enum = BookType(book_type) if book_type else None
    books = await Book.get_published_books(db, book_type_enum)
    return books


@router.get("/my-books", response_model=List[BookSchema])
async def get_my_books(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_author)
):
    """Get books by current author"""
    books = await Book.get_by_author(db, str(current_user.id))
    return books


@router.get("/{book_id}", response_model=BookSchema)
async def get_book(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get book by ID"""
    book = await Book.get_by_id(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    # Check if user can access this book
    if book.status != BookStatus.PUBLISHED and book.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return book


@router.post("/", response_model=BookSchema)
async def create_book(
    book_data: BookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_author)
):
    """Create a new book"""
    book = await Book.create(
        db,
        **book_data.dict(),
        author_id=current_user.id
    )
    return book


@router.put("/{book_id}", response_model=BookSchema)
async def update_book(
    book_id: str,
    book_data: BookUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_author)
):
    """Update book"""
    book = await Book.get_by_id(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    if book.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Update book fields
    update_data = book_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(book, field, value)
    
    await db.commit()
    await db.refresh(book)
    return book


@router.post("/{book_id}/chapters", response_model=ChapterSchema)
async def create_chapter(
    book_id: str,
    chapter_data: ChapterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_author)
):
    """Create a new chapter"""
    book = await Book.get_by_id(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    if book.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Generate AI content for the chapter
    ai_service = AIService()
    ai_content = await ai_service.generate_chapter_content(
        chapter_data.content,
        book.book_type,
        book.difficulty
    )
    
    chapter = await Chapter.create(
        db,
        book_id=book_id,
        **chapter_data.dict(),
        ai_generated_content=ai_content
    )
    
    # Update book chapter count
    book.total_chapters = len(await Chapter.get_by_book(db, book_id))
    await db.commit()
    
    return chapter


@router.get("/{book_id}/chapters", response_model=List[ChapterSchema])
async def get_chapters(
    book_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chapters for a book"""
    book = await Book.get_by_id(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    # Check access permissions
    if book.status != BookStatus.PUBLISHED and book.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    chapters = await Chapter.get_by_book(db, book_id)
    return chapters


@router.post("/upload", response_model=BookSchema)
async def upload_book(
    file: UploadFile = File(...),
    title: str = "",
    book_type: str = "learning",
    difficulty: str = "medium",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_author)
):
    """Upload and process a book file"""
    file_service = FileService()
    ai_service = AIService()
    
    # Process uploaded file
    content = await file_service.process_book_file(file)
    
    # Create book
    book = await Book.create(
        db,
        title=title or file.filename,
        author_name=current_user.display_name or current_user.email,
        author_id=current_user.id,
        book_type=book_type,
        difficulty=difficulty
    )
    
    # Generate chapters using AI
    chapters = await ai_service.generate_chapters_from_content(content, book.book_type)
    
    for i, chapter_content in enumerate(chapters, 1):
        await Chapter.create(
            db,
            book_id=book.id,
            chapter_number=i,
            title=chapter_content["title"],
            content=chapter_content["content"],
            summary=chapter_content.get("summary"),
            ai_generated_content=chapter_content.get("ai_content")
        )
    
    # Update book
    book.total_chapters = len(chapters)
    book.estimated_duration = sum(ch.get("duration", 15) for ch in chapters)
    await db.commit()
    
    return book