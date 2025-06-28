from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.embeddings_service import EmbeddingsService
from supabase import Client
from postgrest.exceptions import APIError
from enum import Enum
import shutil
import fitz
import os
import aiofiles
from pydantic import BaseModel
from fastapi.responses import Response
import io

from app.core.auth import get_current_user, get_current_author, get_current_active_user
from app.core.database import get_supabase
from app.schemas import Book, BookCreate, BookUpdate, User
from app.schemas.book import Book as BookSchema, Chapter as ChapterSchema, ChapterCreate, BookWithDraftChapters, BookWithChapters
from app.services.ai_service import AIService
from app.services.file_service import FileService
from app.core.config import settings


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
    """Get books by current user"""
    try:
        response = supabase_client.table('books').select('*').eq('user_id', current_user.id).execute()
        return response.data
    except APIError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/{book_id}", response_model=BookWithChapters)
async def get_book(
    book_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    """Get book by ID with its chapters"""
    try:
        response = supabase_client.table('books').select('*, chapters(*)').eq('id', book_id).single().execute()
        book = response.data
    except APIError as e:
        raise HTTPException(status_code=404, detail="Book not found")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Check if user can access this book
    if book['status'] != BookStatus.PUBLISHED and book['user_id'] != current_user['id']:
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
        "user_id": current_user['id']
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
        response = supabase_client.table('books').select('user_id').eq('id', book_id).single().execute()
        if not response.data or response.data['user_id'] != current_user['id']:
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
    
    if book['user_id'] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Generate AI content for the chapter
    ai_service = AIService()
    ai_content = await ai_service.generate_chapter_ai_elements(
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
    if book['status'] != BookStatus.PUBLISHED and book['user_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    chapters_response = supabase_client.table('chapters').select('*').eq('book_id', book_id).execute()
    chapters = chapters_response.data
    return chapters


@router.post("/upload", response_model=BookSchema, status_code=status.HTTP_202_ACCEPTED)
async def upload_book(
    background_tasks: BackgroundTasks,
    book_type: str = Form(...),
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Upload and process a book from a file or raw text.
    This endpoint now runs the processing in the background.
    """
    if not file and not text_content:
        raise HTTPException(
            status_code=400,
            detail="Either a file or text content must be provided.",
        )

    file_service = FileService()
    
    storage_path = None
    original_filename = None

    if file:
        original_filename = file.filename
        # Define a unique path in Supabase Storage
        storage_path = f"{current_user['id']}/{original_filename}"
        
        try:
            # Read file content and upload to Supabase Storage
            content = await file.read()
            supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                path=storage_path,
                file=content,
                file_options={"content-type": file.content_type}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload file to storage: {e}")

    # Create an initial book record so we can return an ID immediately
    initial_book_data = BookCreate(
        title=original_filename if file else "Untitled Text",
        user_id=current_user["id"],
        book_type=book_type,
        status="QUEUED",
    )
    
    try:
        response = supabase_client.table("books").insert(initial_book_data.dict(exclude_none=True)).execute()
        book_record = response.data[0]
        
        # Add the processing task to the background
        background_tasks.add_task(
            file_service.process_uploaded_book,
            storage_path=storage_path,
            original_filename=original_filename,
            text_content=text_content,
            book_type=book_type,
            user_id=current_user["id"],
            book_id_to_update=book_record["id"], # Pass ID to update
        )
        
        return book_record

    except Exception as e:
        # This will catch errors during initial book creation
        raise HTTPException(status_code=500, detail=f"Failed to queue book processing: {e}")


@router.get("/{book_id}/status", response_model=BookWithChapters)
async def get_book_status(
    book_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
):
    """Get the processing status of a book by its ID, and output time from QUEUED to READY."""
    try:
        response = (
            supabase_client.table("books")
            .select("*, chapters(*)")
            .eq("id", book_id)
            .single()
            .execute()
        )
        book = response.data
        if not book:
            raise HTTPException(
                status_code=404, detail="Book not found or you don't have access."
            )
        import datetime
        from datetime import timezone
        import time
        # Track QUEUED timestamp
        now_utc = datetime.datetime.now(timezone.utc)
        updated = False
        if book["status"] == "QUEUED":
            if not book.get("queued_at"):
                # Store the current time as queued_at
                supabase_client.table("books").update({"queued_at": now_utc.isoformat()}).eq("id", book_id).execute()
                book["queued_at"] = now_utc.isoformat()
                updated = True
        # If book is READY and has queued_at, calculate processing time
        processing_time_seconds = None
        if book["status"] == "READY" and book.get("queued_at"):
            try:
                queued_at = datetime.datetime.fromisoformat(book["queued_at"])
                ready_at = book.get("ready_at")
                if not ready_at:
                    # Store the current time as ready_at
                    supabase_client.table("books").update({"ready_at": now_utc.isoformat()}).eq("id", book_id).execute()
                    ready_at = now_utc.isoformat()
                    book["ready_at"] = ready_at
                    updated = True
                else:
                    ready_at = book["ready_at"]
                ready_at_dt = datetime.datetime.fromisoformat(ready_at)
                processing_time_seconds = int((ready_at_dt - queued_at).total_seconds())
            except Exception:
                processing_time_seconds = None
        # Return book with processing_time_seconds if available
        if processing_time_seconds is not None:
            book["processing_time_seconds"] = processing_time_seconds
        return book
    except APIError:
        raise HTTPException(status_code=404, detail="Book not found.")


@router.post("/{book_id}/regenerate-chapters", response_model=BookWithDraftChapters)
async def regenerate_chapters(
    book_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
    ai_service: AIService = Depends(AIService)
):
    """Regenerates chapters for a book and returns them for review."""
    # 1. Fetch the book and verify ownership
    response = supabase_client.table('books').select('*').eq('id', book_id).single().execute()
    if not response.data or response.data.get('user_id') != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized or book not found")
    
    book = response.data
    content = book.get('content')
    book_type = book.get('book_type')

    if not content:
        raise HTTPException(status_code=400, detail="Book content not found, cannot regenerate chapters.")

    # 2. Update status to GENERATING
    supabase_client.table('books').update({
        "status": UserBookStatus.GENERATING.value,
        "progress": 3,
        "progress_message": "Regenerating AI chapters..."
    }).eq('id', book["id"]).execute()

    # 3. Regenerate chapters
    ai_chapters = await ai_service.generate_chapters_from_content(content, book_type)
    chapters = [{"title": ch.get("title", ""), "content": ch.get("content", "")} for ch in ai_chapters]

    # 4. Return book with draft chapters for review
    return {
        **book,
        "chapters": chapters
    }


@router.post("/{book_id}/retry", response_model=BookSchema)
async def retry_book_processing(
    book_id: str,
    background_tasks: BackgroundTasks,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Retry processing a failed book"""
    try:
        # Check if book exists and belongs to user
        response = supabase_client.table('books').select('*').eq('id', book_id).eq('user_id', current_user['id']).execute()
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
        
        # Restart the processing
        file_service = FileService()
        
        # Get the book content and type
        content = book.get('content', '')
        book_type = book.get('book_type', 'learning')
        
        if not content:
            raise HTTPException(status_code=400, detail="Book content not found, cannot retry processing")
        
        # Add the processing task to the background
        background_tasks.add_task(
            file_service.process_uploaded_book,
            storage_path=None,  # Content is already extracted
            original_filename=None,
            text_content=content,
            book_type=book_type,
            user_id=current_user["id"],
            book_id_to_update=book_id,
        )
        
        # Return the updated book
        updated_response = supabase_client.table('books').select('*').eq('id', book_id).single().execute()
        return updated_response.data
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{book_id}")
async def delete_book(
    book_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    # 1. Get the book record to find the storage path and verify ownership
    book_response = supabase_client.table("books").select("*").eq("id", book_id).single().execute()
    if not book_response.data:
        raise HTTPException(status_code=404, detail="Book not found")
    book = book_response.data

    # 2. Only allow the owner to delete
    if book["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this book")

    user_id = current_user["id"]

    # 3. Delete all user files from Supabase Storage
    try:
        # Delete covers
        try:
            covers = supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).list(path=f"users/{user_id}/covers")
            if covers:
                cover_paths = [f"users/{user_id}/covers/{item['name']}" for item in covers]
                supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).remove(cover_paths)
                print(f"Deleted {len(cover_paths)} cover files for user {user_id}")
        except Exception as e:
            print(f"Warning: Could not delete cover files: {e}")

        # Delete audio files
        try:
            audio_files = supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).list(path=f"users/{user_id}/audio")
            if audio_files:
                audio_paths = [f"users/{user_id}/audio/{item['name']}" for item in audio_files]
                supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).remove(audio_paths)
                print(f"Deleted {len(audio_paths)} audio files for user {user_id}")
        except Exception as e:
            print(f"Warning: Could not delete audio files: {e}")

        # Delete video files
        try:
            video_files = supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).list(path=f"users/{user_id}/videos")
            if video_files:
                video_paths = [f"users/{user_id}/videos/{item['name']}" for item in video_files]
                supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).remove(video_paths)
                print(f"Deleted {len(video_paths)} video files for user {user_id}")
        except Exception as e:
            print(f"Warning: Could not delete video files: {e}")

        # Delete the original book file
        try:
            storage_path = f"{user_id}/{book['title']}"
            supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).remove([storage_path])
            print(f"Deleted book file: {storage_path}")
        except Exception as e:
            print(f"Warning: Could not delete book file: {e}")

    except Exception as e:
        # Log the error but continue, as the book record should still be deleted
        print(f"Warning: Could not delete files from storage: {e}")

    # 4. Delete related records from database
    try:
        # Delete video records
        supabase_client.table("videos").delete().eq("book_id", book_id).execute()
        print(f"Deleted video records for book {book_id}")
        
        # Delete chapter embeddings
        supabase_client.table("chapter_embeddings").delete().eq("book_id", book_id).execute()
        print(f"Deleted chapter embeddings for book {book_id}")
        
        # Delete chapters (this will cascade to other related records)
        supabase_client.table("chapters").delete().eq("book_id", book_id).execute()
        print(f"Deleted chapters for book {book_id}")
        
        # Delete book embeddings
        supabase_client.table("book_embeddings").delete().eq("book_id", book_id).execute()
        print(f"Deleted book embeddings for book {book_id}")
        
        # Finally, delete the book record
        supabase_client.table("books").delete().eq("id", book_id).execute()
        print(f"Deleted book record {book_id}")
        
    except APIError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e.message}")

    return {"message": "Book and all associated data deleted successfully"}


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


@router.post("/{book_id}/extract-cover")
async def extract_cover_from_page(
    book_id: str,
    page: int,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    # Get book record
    response = supabase_client.table("books").select("user_id, title").eq("id", book_id).single().execute()
    if not response.data or response.data["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to modify this book")
    book = response.data
    file_path = os.path.join(settings.UPLOAD_DIR, book['title'])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Book file not found on server")
    try:
        doc = fitz.open(file_path)
        if page < 1 or page > len(doc):
            raise HTTPException(status_code=400, detail="Invalid page number")
        page_obj = doc[page - 1]
        images = page_obj.get_images(full=True)
        if not images:
            raise HTTPException(status_code=404, detail="No image found on that page")
        xref = images[0][0]
        pix = fitz.Pixmap(doc, xref)
        # Save to in-memory buffer
        img_buffer = io.BytesIO()
        pix.save(img_buffer, format="png")
        img_buffer.seek(0)
        # Upload to Supabase Storage under user folder
        user_id = current_user["id"]
        storage_path = f"users/{user_id}/covers/cover_{book_id}.png"
        supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
            path=storage_path,
            file=img_buffer.getvalue(),
            file_options={"content-type": "image/png"}
        )
        # Get the correct public URL from Supabase
        cover_url = supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(storage_path)
        supabase_client.table('books').update({"cover_image_url": cover_url}).eq('id', book_id).execute()
        return {"cover_image_url": cover_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract cover: {e}")


@router.post("/{book_id}/upload-cover")
async def upload_cover_image(
    book_id: str,
    cover_image: UploadFile = File(...),
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    # Get book record
    response = supabase_client.table("books").select("user_id").eq("id", book_id).single().execute()
    if not response.data or response.data["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to modify this book")
    # Read file into memory
    img_bytes = await cover_image.read()
    user_id = current_user["id"]
    storage_path = f"users/{user_id}/covers/cover_{book_id}_upload.png"
    supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
        path=storage_path,
        file=img_bytes,
        file_options={"content-type": "image/png"}
    )
    # Get the correct public URL from Supabase
    cover_url = supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(storage_path)
    supabase_client.table('books').update({"cover_image_url": cover_url}).eq('id', book_id).execute()
    return {"cover_image_url": cover_url}


# Schema for chapter input
class ChapterInput(BaseModel):
    title: str
    content: str = ""


@router.post("/{book_id}/save-chapters")
async def save_user_chapters(
    book_id: str,
    chapters: List[ChapterInput],
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    # Check book ownership
    response = supabase_client.table("books").select("user_id").eq("id", book_id).single().execute()
    if not response.data or response.data["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to modify this book")
    
     # Delete existing chapter embeddings for this book
    supabase_client.table('chapter_embeddings').delete().eq('book_id', book_id).execute()
    
    # Delete existing draft chapters for this book
    supabase_client.table('chapters').delete().eq('book_id', book_id).execute()
    # Insert new chapters and create embeddings
    embeddings_service = EmbeddingsService(supabase_client)
    for idx, chapter in enumerate(chapters, 1):
        chapter_data = {
            "book_id": book_id,
            "title": chapter.title,
            "content": chapter.content,
            "chapter_number": idx
        }
        insert_response = supabase_client.table('chapters').insert(chapter_data).execute()
        chapter_id = insert_response.data[0]['id']
        # Create embeddings for the new chapter
        await embeddings_service.create_chapter_embeddings(chapter_id, chapter.content)

    # Update total_chapters in books table
    supabase_client.table('books').update({"total_chapters": len(chapters)}).eq('id', book_id).execute()
    return {"message": "Chapters saved", "total_chapters": len(chapters)}