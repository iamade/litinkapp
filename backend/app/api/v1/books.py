from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client
from postgrest.exceptions import APIError
from enum import Enum

from app.core.auth import get_current_user, get_current_author, get_current_active_user
from app.core.database import get_supabase
from app.schemas import Book, BookCreate, BookUpdate, User
from app.schemas.book import Book as BookSchema, Chapter as ChapterSchema, ChapterCreate
from app.services.ai_service import AIService
from app.services.file_service import FileService


class BookStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class UserBookStatus(str, Enum):
    PROCESSING = "PROCESSING"      # Initial upload, file processing
    GENERATING = "GENERATING"      # AI generating chapters/content
    READY = "READY"               # AI processing complete
    FAILED = "FAILED"             # Processing failed


router = APIRouter()


@router.get("/", response_model=List[BookSchema])
async def get_books(
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    """Get all books"""
    try:
        response = supabase_client.table('books').select('*').execute()
        return response.data
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/my-books", response_model=List[BookSchema], tags=["Authors"])
async def get_my_books(
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_author)
):
    """Get books by current author"""
    try:
        response = supabase_client.table('books').select('*').eq('author_id', current_user.id).execute()
        return response.data
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/{book_id}", response_model=BookSchema)
async def get_book(
    book_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    """Get book by ID"""
    try:
        response = supabase_client.table('books').select('*').eq('id', book_id).single().execute()
        book = response.data
    except APIError as e:
        raise HTTPException(status_code=404, detail="Book not found")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
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
    
    try:
        response = supabase_client.table('books').insert(book_data).execute()
        if not response.data:
            raise HTTPException(status_code=400, detail="Book creation failed.")
        return response.data[0]
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.put("/{book_id}", response_model=BookSchema)
async def update_book(
    book_id: str,
    book_update: BookUpdate,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Update book"""
    try:
        response = supabase_client.table('books').select('author_id').eq('id', book_id).single().execute()
        if not response.data or response.data['author_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to update this book")
    except APIError as e:
        raise HTTPException(status_code=403, detail="Not authorized to update this book")
        
    update_data = book_update.dict(exclude_unset=True)
    try:
        response = supabase_client.table('books').update(update_data).eq('id', book_id).execute()
        return response.data[0]
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/{book_id}/chapters", response_model=ChapterSchema)
async def create_chapter(
    book_id: str,
    chapter_data: ChapterCreate,
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_author)
):
    """Create a new chapter"""
    try:
        response = supabase_client.table('books').select('*').eq('id', book_id).single().execute()
        book = response.data
    except APIError as e:
        raise HTTPException(status_code=404, detail="Book not found")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
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
    
    # Insert chapter
    chapter_insert = chapter_data.dict()
    chapter_insert['book_id'] = book_id
    chapter_insert['ai_generated_content'] = ai_content
    try:
        response = supabase_client.table('chapters').insert(chapter_insert).execute()
        chapter = response.data[0]
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)
    
    # Update book chapter count
    try:
        response = supabase_client.table('books').update({'total_chapters': len(await Chapter.get_by_book(supabase_client, book_id))}).eq('id', book_id).execute()
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)
    
    return chapter


@router.get("/{book_id}/chapters", response_model=List[ChapterSchema])
async def get_chapters(
    book_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    """Get chapters for a book"""
    try:
        response = supabase_client.table('books').select('*').eq('id', book_id).single().execute()
        book = response.data
    except APIError as e:
        raise HTTPException(status_code=404, detail="Book not found")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
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
    """Upload and process a book file or raw text"""
    try:
        file_service = FileService()
        ai_service = AIService()
        
        # Initial book data with PROCESSING status
        book_data = {
            "title": title or (file.filename if file else "Untitled Book"),
            "author_id": current_user['id'],
            "book_type": book_type,
            "difficulty": difficulty,
            "status": UserBookStatus.PROCESSING.value,
            "error_message": None,
            "progress": 0,
            "total_steps": 4  # File processing, Text extraction, AI generation, Chapter creation
        }
        
        # Create book record
        response = supabase_client.table('books').insert(book_data).execute()
        if not response.data:
            raise Exception("Book creation failed")
        book = response.data[0]
        
        try:
            # Step 1: Process file
            supabase_client.table('books').update({
                "progress": 1,
                "progress_message": "Processing uploaded file..."
            }).eq('id', book["id"]).execute()
            
            extracted = None
            content = None
            if file:
                extracted = await file_service.process_book_file(file)
                content = extracted["text"]
                # Update book with extracted metadata
                update_data = {}
                if extracted.get("author"):
                    update_data["author_name"] = extracted["author"]
                if extracted.get("cover_image_path"):
                    update_data["cover_image_path"] = extracted["cover_image_path"]
                if update_data:
                    supabase_client.table('books').update(update_data).eq('id', book["id"]).execute()
            elif text_content:
                content = text_content
            else:
                raise Exception("No file or text content provided")
            
            # Step 2: Extract text and metadata
            supabase_client.table('books').update({
                "progress": 2,
                "progress_message": "Extracting text and metadata..."
            }).eq('id', book["id"]).execute()
            
            # Update to GENERATING status before AI processing
            supabase_client.table('books').update({
                "status": UserBookStatus.GENERATING.value,
                "progress": 3,
                "progress_message": "Generating AI content..."
            }).eq('id', book["id"]).execute()
            
            # Step 3: Generate chapters
            chapters = []
            if extracted and extracted.get("chapters"):
                chapters = extracted["chapters"]
            else:
                # Generate chapters using AI
                ai_chapters = await ai_service.generate_chapters_from_content(content, book_type)
                chapters = [{"title": ch["title"], "content": ch["content"]} for ch in ai_chapters]
            
            # Step 4: Create chapters
            supabase_client.table('books').update({
                "progress": 4,
                "progress_message": "Creating chapters..."
            }).eq('id', book["id"]).execute()
            
            for idx, chapter in enumerate(chapters, 1):
                chapter_data = {
                    "book_id": book["id"],
                    "title": chapter["title"],
                    "content": chapter.get("content", ""),
                    "chapter_number": idx
                }
                supabase_client.table('chapters').insert(chapter_data).execute()
            
            # Update book with success status
            supabase_client.table('books').update({
                "status": UserBookStatus.READY.value,
                "progress": 4,
                "progress_message": "Book processing complete!",
                "total_chapters": len(chapters)
            }).eq('id', book["id"]).execute()
            
            return book
            
        except Exception as e:
            # Update book with error status
            error_message = str(e)
            supabase_client.table('books').update({
                "status": UserBookStatus.FAILED.value,
                "error_message": error_message,
                "progress_message": "Processing failed. Click retry to try again."
            }).eq('id', book["id"]).execute()
            raise Exception(error_message)
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{book_id}/retry", response_model=BookSchema)
async def retry_book_processing(
    book_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Retry processing a failed book"""
    try:
        # Check if book exists and belongs to user
        response = supabase_client.table('books').select('*').eq('id', book_id).eq('author_id', current_user['id']).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Book not found")
        book = response.data[0]
        
        # Only allow retry for failed books
        if book['status'] != UserBookStatus.FAILED.value:
            raise HTTPException(status_code=400, detail="Can only retry failed books")
        
        # Reset book status and progress
        supabase_client.table('books').update({
            "status": UserBookStatus.PROCESSING.value,
            "error_message": None,
            "progress": 0,
            "progress_message": "Restarting book processing..."
        }).eq('id', book_id).execute()
        
        # TODO: Implement actual retry logic here
        # For now, just return the updated book
        return book
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{book_id}", response_model=BookSchema)
async def delete_book(
    book_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a book"""
    try:
        response = supabase_client.table('books').select('author_id').eq('id', book_id).single().execute()
        if not response.data or response.data['author_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to delete this book")
    except APIError as e:
        raise HTTPException(status_code=403, detail="Not authorized to delete this book")

    try:
        response = supabase_client.table('books').delete().eq('id', book_id).execute()
        return response.data[0]
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/search", response_model=List[BookSchema])
async def search_books(
    query: str,
    supabase_client: Client = Depends(get_supabase)
):
    """Search for books by title or description"""
    try:
        response = supabase_client.table('books').select('*').text_search('fts', query).execute()
        return response.data
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/recommendations/{user_id}", response_model=List[BookSchema])
async def get_book_recommendations(
    user_id: int,
    supabase_client: Client = Depends(get_supabase)
):
    """Get book recommendations for a user (dummy implementation)"""
    # This is a placeholder for a real recommendation engine
    try:
        response = supabase_client.table('books').select('*').limit(5).execute()
        return response.data
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)