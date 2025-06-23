from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client

from app.core.auth import get_current_user, get_current_author, get_current_active_user
from app.core.database import get_supabase
from app.schemas import Book, BookCreate, BookUpdate, User
from app.schemas.book import Book as BookSchema, Chapter as ChapterSchema, ChapterCreate
from app.services.ai_service import AIService
from app.services.file_service import FileService

router = APIRouter()


@router.get("/", response_model=List[BookSchema])
async def get_books(
    book_type: Optional[str] = None,
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    """Get published books"""
    book_type_enum = BookType(book_type) if book_type else None
    response = supabase_client.table('books').select('*').eq('status', 'PUBLISHED').eq('book_type', book_type_enum).execute()
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    return response.data


@router.get("/my-books", response_model=List[BookSchema])
async def get_my_books(
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_author)
):
    """Get books by current author"""
    response = supabase_client.table('books').select('*').eq('author_id', current_user.id).execute()
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    return response.data


@router.get("/{book_id}", response_model=BookSchema)
async def get_book(
    book_id: int,
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    """Get book by ID"""
    response = supabase_client.table('books').select('*').eq('id', book_id).single().execute()
    if response.error:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book = response.data
    
    # Check if user can access this book
    if book['status'] != BookStatus.PUBLISHED and book['author_id'] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return book


@router.post(
    "/",
    response_model=BookSchema,
    tags=["Authors"]
)
async def create_book(
    title: str = Form(...),
    description: str = Form(...),
    file: UploadFile = File(...),
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new book"""
    file_service = FileService()
    content = await file_service.process_book_file(file)
    
    book_data = {
        "title": title,
        "description": description,
        "content": content,
        "author_id": current_user['id']
    }
    
    response = supabase_client.table('books').insert(book_data).execute()
    
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    
    return response.data[0]


@router.put("/{book_id}", response_model=BookSchema)
async def update_book(
    book_id: int,
    book_update: BookUpdate,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Update book"""
    # Verify the user is the author
    response = supabase_client.table('books').select('author_id').eq('id', book_id).single().execute()
    if response.error or not response.data or response.data['author_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized to update this book")
        
    update_data = book_update.dict(exclude_unset=True)
    response = supabase_client.table('books').update(update_data).eq('id', book_id).execute()

    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    
    return response.data[0]


@router.post("/{book_id}/chapters", response_model=ChapterSchema)
async def create_chapter(
    book_id: int,
    chapter_data: ChapterCreate,
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_author)
):
    """Create a new chapter"""
    response = supabase_client.table('books').select('*').eq('id', book_id).single().execute()
    if response.error:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book = response.data
    
    if book['author_id'] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Generate AI content for the chapter
    ai_service = AIService()
    ai_content = await ai_service.generate_chapter_content(
        chapter_data.content,
        book['book_type'],
        book['difficulty']
    )
    
    chapter = await Chapter.create(
        supabase_client,
        book_id=book_id,
        **chapter_data.dict(),
        ai_generated_content=ai_content
    )
    
    # Update book chapter count
    response = supabase_client.table('books').update({'total_chapters': len(await Chapter.get_by_book(supabase_client, book_id))}).eq('id', book_id).execute()
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    
    return chapter


@router.get("/{book_id}/chapters", response_model=List[ChapterSchema])
async def get_chapters(
    book_id: int,
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    """Get chapters for a book"""
    response = supabase_client.table('books').select('*').eq('id', book_id).single().execute()
    if response.error:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book = response.data
    
    # Check access permissions
    if book['status'] != BookStatus.PUBLISHED and book['author_id'] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    chapters = await Chapter.get_by_book(supabase_client, book_id)
    return chapters


@router.post("/upload", response_model=BookSchema)
async def upload_book(
    file: UploadFile = File(None),
    text_content: str = Form(None),
    title: str = "",
    book_type: str = "learning",
    difficulty: str = "medium",
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Upload and process a book file or raw text (supports .pdf, .docx, .txt, .epub)"""
    file_service = FileService()
    ai_service = AIService()

    if file:
        # Process uploaded file (including .epub)
        content = await file_service.process_book_file(file)
        book_title = title or file.filename
    elif text_content:
        content = text_content
        book_title = title or "Untitled Book"
    else:
        raise HTTPException(status_code=400, detail="No file or text content provided.")

    # Insert book into Supabase
    book_data = {
        "title": book_title,
        "author_name": current_user.get('display_name') or current_user.get('email'),
        "author_id": current_user['id'],
        "book_type": book_type,
        "difficulty": difficulty
    }
    response = supabase_client.table('books').insert(book_data).execute()
    if response.error or not response.data:
        raise HTTPException(status_code=400, detail=response.error.message if response.error else "Book creation failed.")
    book = response.data[0]

    # Generate chapters using AI
    chapters = await ai_service.generate_chapters_from_content(content, book["book_type"])

    for i, chapter_content in enumerate(chapters, 1):
        chapter_data = {
            "book_id": book["id"],
            "chapter_number": i,
            "title": chapter_content["title"],
            "content": chapter_content["content"],
            "summary": chapter_content.get("summary"),
            "ai_generated_content": chapter_content.get("ai_content"),
        }
        response = supabase_client.table('chapters').insert(chapter_data).execute()
        if response.error:
            raise HTTPException(status_code=400, detail=response.error.message)

    # Update book
    book["total_chapters"] = len(chapters)
    book["estimated_duration"] = sum(ch.get("duration", 15) for ch in chapters)
    supabase_client.table('books').update({
        'total_chapters': book["total_chapters"],
        'estimated_duration': book["estimated_duration"]
    }).eq('id', book["id"]).execute()

    return book


@router.delete("/{book_id}", response_model=BookSchema)
async def delete_book(
    book_id: int,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a book"""
    # Verify the user is the author
    response = supabase_client.table('books').select('author_id').eq('id', book_id).single().execute()
    if response.error or not response.data or response.data['author_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized to delete this book")

    response = supabase_client.table('books').delete().eq('id', book_id).execute()
    
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
        
    return response.data[0]


@router.post("/search", response_model=List[BookSchema])
async def search_books(
    query: str,
    supabase_client: Client = Depends(get_supabase)
):
    """Search for books by title or description"""
    response = supabase_client.table('books').select('*').text_search('fts', query).execute()
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    return response.data


@router.get("/recommendations/{user_id}", response_model=List[BookSchema])
async def get_book_recommendations(
    user_id: int,
    supabase_client: Client = Depends(get_supabase)
):
    """Get book recommendations for a user (dummy implementation)"""
    # This is a placeholder for a real recommendation engine
    response = supabase_client.table('books').select('*').limit(5).execute()
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    return response.data