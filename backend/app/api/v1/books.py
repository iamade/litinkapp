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
from app.schemas import Book, BookCreate, BookUpdate, User, BookStructureInput, ChapterInput, SectionInput, BookWithSections
from app.schemas.book import Book as BookSchema, BookPreview, Chapter as ChapterSchema, ChapterCreate, BookWithDraftChapters, BookWithChapters
from app.services.ai_service import AIService
from app.services.file_service import FileService
from app.core.config import settings


class BookStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class UserBookStatus(str, Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"  # New status for payment required
    PROCESSING = "PROCESSING"      # Initial upload, file processing
    GENERATING = "GENERATING"      # AI generating chapters/content
    READY = "READY"               # AI processing complete
    FAILED = "FAILED"             # Processing failed


router = APIRouter()


@router.get("/superadmin-learning-books", response_model=List[BookWithChapters])
async def get_superadmin_learning_books(
    supabase_client: Client = Depends(get_supabase)
):
    """Get all published learning books authored by the superadmin (for Explore Learning Materials)"""
    try:
        # Get superadmin user_id
        profile_resp = supabase_client.table('profiles').select('id').eq('email', 'support@litinkai.com').execute()
        if not profile_resp.data or len(profile_resp.data) == 0:
            # No superadmin profile found, return empty list
            return []
        superadmin_id = profile_resp.data[0]['id']
        # Get published learning books by superadmin
        books_resp = supabase_client.table('books').select('*, chapters(*)').eq('user_id', superadmin_id).eq('book_type', 'learning').eq('status', 'READY').order('created_at', desc=True).execute()
        return books_resp.data or []
    except Exception as e:
        print(f"Error in /superadmin-learning-books: {e}")
        return []


@router.get("/superadmin-entertainment-books", response_model=List[BookWithChapters])
async def get_superadmin_entertainment_books(
    supabase_client: Client = Depends(get_supabase)
):
    """Get all published entertainment books authored by the superadmin (for Interactive Stories)"""
    try:
        # Get superadmin user_id
        profile_resp = supabase_client.table('profiles').select('id').eq('email', 'support@litinkai.com').execute()
        if not profile_resp.data or len(profile_resp.data) == 0:
            # No superadmin profile found, return empty list
            return []
        superadmin_id = profile_resp.data[0]['id']
        # Get published entertainment books by superadmin
        books_resp = supabase_client.table('books').select('*, chapters(*)').eq('user_id', superadmin_id).eq('book_type', 'entertainment').eq('status', 'READY').order('created_at', desc=True).execute()
        return books_resp.data or []
    except Exception as e:
        print(f"Error in /superadmin-entertainment-books: {e}")
        return []


@router.get("/learning-progress")
async def get_learning_books_with_progress(
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    try:
        books_response = supabase_client.table('books').select('*, chapters(*)').eq('user_id', current_user["id"]).eq('book_type', 'learning').execute()
        books = books_response.data or []
        result = []
        for book in books:
            chapters = book.get('chapters') or []
            if not isinstance(chapters, list) or len(chapters) == 0:
                result.append({
                    'id': book.get('id', ''),
                    'title': book.get('title', ''),
                    'author_name': book.get('author_name', ''),
                    'cover_image_url': book.get('cover_image_url', ''),
                    'description': book.get('description', ''),
                    'progress': 0,
                    'total_chapters': 0,
                    'book_type': book.get('book_type', ''),
                    'status': book.get('status', ''),
                })
                continue
            chapter_ids = [c.get('id') for c in chapters if c.get('id')]
            total_chapters = len(chapter_ids)
            progress = 0
            if total_chapters > 0:
                content_response = supabase_client.table('learning_content').select('chapter_id, content_type, status').in_('chapter_id', chapter_ids).eq('user_id', current_user["id"]).eq('status', 'ready').execute()
                content = content_response.data or []
                chapters_with_content = set([c.get('chapter_id') for c in content if c.get('content_type') in ['audio_narration', 'realistic_video']])
                progress = round((len(chapters_with_content) / total_chapters) * 100)
            result.append({
                'id': book.get('id', ''),
                'title': book.get('title', ''),
                'author_name': book.get('author_name', ''),
                'cover_image_url': book.get('cover_image_url', ''),
                'description': book.get('description', ''),
                'progress': progress,
                'total_chapters': total_chapters,
                'book_type': book.get('book_type', ''),
                'status': book.get('status', ''),
            })
        return result
    except Exception as e:
        print(f"Error in /learning-progress: {e}")
        return []


@router.get("/", response_model=List[BookSchema])
async def get_books(
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_user)
):
    """Get books uploaded by the current user"""
    try:
        response = supabase_client.table('books').select('*').eq('user_id', current_user["id"]).execute()
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

@router.post("/upload", response_model=BookPreview, status_code=status.HTTP_202_ACCEPTED)
async def upload_book(
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    book_type: str = Form(...),
    supabase_client: Client = Depends(get_supabase),  # FIX: Add missing dependency
    current_user: User = Depends(get_current_user)
):
    """Upload book file - PREVIEW MODE (doesn't save chapters yet)"""
    if not file and not text_content:
        raise HTTPException(status_code=400, detail="Either file or text content is required")

    try:
        # Create initial book record
        book_data = {
            "title": title,
            "description": description,
            "book_type": book_type,
            "user_id": str(current_user["id"]),
            "status": "PROCESSING",  # Initial status
        }
        
        book_response = supabase_client.table("books").insert(book_data).execute()
        book = book_response.data[0]
        
        storage_path = None
        original_filename = None
        
        if file:
            # Upload file to storage
            file_content = await file.read()
            original_filename = file.filename
            storage_path = f"users/{current_user['id']}/{original_filename}"
            
            supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": file.content_type}
            )
            
            
            
            # Update book with storage info
            supabase_client.table("books").update({
                "original_file_storage_path": storage_path, 
            }).eq("id", book["id"]).execute()

        # Process book for PREVIEW only (don't save chapters)
        file_service = FileService()
        preview_result = await file_service.process_uploaded_book_preview(
            storage_path=storage_path,
            original_filename=original_filename,
            text_content=text_content,
            book_type=book_type,
            user_id=str(current_user["id"]),
            book_id_to_update=book["id"]
        )
        
        # ✅ FIX: Return book with preview data WITHOUT conflicting status
        # Remove status from preview_result to avoid conflict
        preview_data = {k: v for k, v in preview_result.items() if k != 'status'}
        
        # Return updated book from database (includes the status update from file_service)
        updated_book_response = supabase_client.table("books").select("*").eq("id", book["id"]).single().execute()
        updated_book = updated_book_response.data
        
        # Merge book data with preview chapters (but don't save chapters to DB yet)
        final_response = {
            **updated_book,
            "preview_chapters": preview_data.get("chapters", []),  # ✅ Preview only
            "total_preview_chapters": preview_data.get("total_chapters", 0),
            "author_name": preview_data.get("author_name"),
            "cover_image_url": preview_data.get("cover_image_url"),
        }
        # Merge the results
        return BookPreview(**final_response)
        # return BookSchema(**book, **preview_result)

    except Exception as e:
        # Clean up on failure
        if 'book' in locals():
            supabase_client.table("books").delete().eq("id", book["id"]).execute()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# @router.post("/upload", response_model=BookSchema, status_code=status.HTTP_202_ACCEPTED)
# async def upload_book(
#     background_tasks: BackgroundTasks,
#     book_type: str = Form(...),
#     file: Optional[UploadFile] = File(None),
#     text_content: Optional[str] = Form(None),
#     supabase_client: Client = Depends(get_supabase),
#     current_user: dict = Depends(get_current_active_user),
# ):
#     """
#     Upload and process a book from a file or raw text.
#     This endpoint now includes payment logic for 2nd+ books.
#     """
#     if not file and not text_content:
#         raise HTTPException(
#             status_code=400,
#             detail="Either a file or text content must be provided.",
#         )

#     # Check how many books the user has already uploaded (excluding FAILED ones)
#     # books_response = supabase_client.table('books').select('id', count='exact').eq('user_id', current_user['id']).neq('status', 'FAILED').execute()
#     # book_count = books_response.count or 0
    
#     # # Determine if payment is required (2nd book and beyond, unless superadmin)
#     # requires_payment = (book_count >= 1) and (current_user.get('role') != 'superadmin')
#     # initial_status = "PENDING_PAYMENT" if requires_payment else "QUEUED"

#     # Payment bypass - always set to QUEUED
#     requires_payment = False
#     initial_status = "QUEUED"
    
#     file_service = FileService()
    
#     storage_path = None
#     original_filename = None

#     if file:
#         original_filename = file.filename
#         # Define a unique path in Supabase Storage
#         storage_path = f"users/{current_user['id']}/{original_filename}"
        
#         try:
#             # Read file content and upload to Supabase Storage
#             content = await file.read()
#             # Try to upload, if duplicate exists, use upsert to overwrite
#             supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
#                 path=storage_path,
#                 file=content,
#                 file_options={"content-type": file.content_type},
#             )
#         except Exception as upload_error:
#             #if it's a duplicate error, use update with upsert to overwrite
#             if "Duplicate" in str(upload_error) or "already exists" in str(upload_error):
#                 try:
#                     # Reset file pointer to beginning
#                     await file.seek(0)
#                     content = await file.read()
                    
#                     #Use update with upsert to overwrite existing file
#                     supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).update(
#                         path=storage_path,
#                         file=content,
#                         file_options={
#                             "content-type": file.content_type,
#                             "upsert": "true" # This allows overwriting existing files
#                         })
#                 except Exception as update_error:
#                     raise Exception(f"Failed to overwrite existing file: {update_error}")
#             else:
#                 raise upload_error
                
#             # raise HTTPException(status_code=500, detail=f"Failed to upload file to storage: {e}")

#     # Create an initial book record
#     initial_book_data = BookCreate(
#         title=original_filename if file else "Untitled Text",
#         user_id=current_user["id"],
#         book_type=book_type,
#         status=initial_status,
#         original_file_storage_path=storage_path
#     )
    
#     try:
#         response = supabase_client.table("books").insert(initial_book_data.dict(exclude_none=True)).execute()
#         book_record = response.data[0]
        
#             # Add the processing task to the background for free first book
#         background_tasks.add_task(
#                 file_service.process_uploaded_book,
#                 storage_path=storage_path,
#                 original_filename=original_filename,
#                 text_content=text_content,
#                 book_type=book_type,
#                 user_id=current_user["id"],
#                 book_id_to_update=book_record["id"],
#             )
            
#         return {
#                 **book_record,
#                 "payment_required": False,
#                 "message": "Book processing started"
#             }
        
#         # if requires_payment:
#         #     # Return book record with payment_required flag
#         #     # Frontend will handle creating checkout session
#         #     return {
#         #         **book_record,
#         #         "payment_required": True,
#         #         "message": "Payment required for additional book uploads"
#         #     }
#         # else:
#         #     # Add the processing task to the background for free first book
#         #     background_tasks.add_task(
#         #         file_service.process_uploaded_book,
#         #         storage_path=storage_path,
#         #         original_filename=original_filename,
#         #         text_content=text_content,
#         #         book_type=book_type,
#         #         user_id=current_user["id"],
#         #         book_id_to_update=book_record["id"],
#         #     )
            
#         #     return {
#         #         **book_record,
#         #         "payment_required": False,
#         #         "message": "Book processing started"
#         #     }

#     except Exception as e:
#         # This will catch errors during initial book creation
#         raise HTTPException(status_code=500, detail=f"Failed to queue book processing: {e}")


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
        sections_data = []
        chapters_data = book.get("chapters", [])

        if book.get("has_sections") and book.get("structure_type") != "flat":
            # Fetch sections data from book_sections table
            try:
                sections_response = supabase_client.table("book_sections").select("*").eq("book_id", book_id).order("order_index").execute()
                sections_data = sections_response.data or []
            except Exception as e:
                print(f"Error fetching sections: {e}")
                sections_data = []

        # Create enhanced book response with structure data
        book_response = {
            **book,
            "structure_data": {
                "id": book["id"],
                "title": book.get("title", ""),
                "structure_type": book.get("structure_type", "flat"),
                "has_sections": book.get("has_sections", False),
                "sections": sections_data,
                "chapters": chapters_data
            }
        }

        return book_response
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

        # # Delete the original book file
        # try:
        #     original_file_storage_path = book.get("original_file_storage_path")
        #     if original_file_storage_path:
        #         supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).remove([original_file_storage_path])
        #         print(f"Deleted book file: {original_file_storage_path}")
        #     else:
        #         print(f"Warning: No original_file_storage_path found for book {book_id}")
        # except Exception as e:
        #     print(f"Warning: Could not delete book file: {e}")
            
                # Delete the specific book file from users folder
        try:
            original_file_storage_path = book.get("original_file_storage_path")
            if original_file_storage_path:
                supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).remove([original_file_storage_path])
                print(f"Deleted book file: {original_file_storage_path}")
            else:
                # If no original_file_storage_path, try to find files in the user's folder
                try:
                    # List all files in the user's root folder
                    user_files = supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).list(path=f"users/{user_id}")
                    if user_files:
                        # Filter out folders (covers, audio, videos)
                        book_files = [f for f in user_files if f['name'] not in ['covers', 'audio', 'videos'] and 'metadata' in f]
                        if book_files:
                            file_paths = [f"users/{user_id}/{file['name']}" for file in book_files]
                            supabase_client.storage.from_(settings.SUPABASE_BUCKET_NAME).remove(file_paths)
                            print(f"Deleted {len(file_paths)} book files for user {user_id}")
                except Exception as e:
                    print(f"Warning: Could not list/delete book files: {e}")
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


@router.post("/{book_id}/save-structure", status_code=status.HTTP_200_OK)
async def save_book_structure(
    book_id: str,
    structure_data: dict,  # Contains confirmed_chapters array
    supabase_client: Client = Depends(get_supabase), 
    current_user: User = Depends(get_current_user)
):
    """Save confirmed book structure to database"""
    try:
        # Verify book ownership
        book_response = supabase_client.table("books").select("*").eq("id", book_id).eq("user_id", str(current_user["id"])).single().execute()
        if not book_response.data:
            raise HTTPException(status_code=404, detail="Book not found")
            
        # Extract confirmed chapters from structure_data
        confirmed_chapters = structure_data.get("chapters", [])
        if not confirmed_chapters:
            raise HTTPException(status_code=400, detail="No chapters provided")
        
        # Save confirmed structure
        file_service = FileService()
        await file_service.confirm_book_structure(
            book_id=book_id,
            confirmed_chapters=confirmed_chapters,
            user_id=str(current_user["id"])
        )
        
        # Return updated book
        updated_book = supabase_client.table("books").select("*").eq("id", book_id).single().execute()
        return {"message": "Book structure saved successfully", "book": updated_book.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save structure: {str(e)}")


# @router.post("/{book_id}/save-chapters")
# async def save_user_chapters(
#     book_id: str,
#     chapters: List[ChapterInput],
#     supabase_client: Client = Depends(get_supabase),
#     current_user: dict = Depends(get_current_active_user)
# ):
#     # Check book ownership
#     response = supabase_client.table("books").select("user_id").eq("id", book_id).single().execute()
#     if not response.data or response.data["user_id"] != current_user["id"]:
#         raise HTTPException(status_code=403, detail="Not authorized to modify this book")
    
#      # Delete existing chapter embeddings for this book
#     supabase_client.table('chapter_embeddings').delete().eq('book_id', book_id).execute()
    
#     # Delete existing draft chapters for this book
#     supabase_client.table('chapters').delete().eq('book_id', book_id).execute()
#     # Insert new chapters and create embeddings
#     embeddings_service = EmbeddingsService(supabase_client)
#     for idx, chapter in enumerate(chapters, 1):
#         chapter_data = {
#             "book_id": book_id,
#             "title": chapter.title,
#             "content": chapter.content,
#             "chapter_number": idx
#         }
#         insert_response = supabase_client.table('chapters').insert(chapter_data).execute()
#         chapter_id = insert_response.data[0]['id']
#         # Create embeddings for the new chapter
#         await embeddings_service.create_chapter_embeddings(chapter_id, chapter.content)

#     # Update total_chapters in books table
#     supabase_client.table('books').update({"total_chapters": len(chapters)}).eq('id', book_id).execute()
#     return {"message": "Chapters saved", "total_chapters": len(chapters)}


# @router.post("/{book_id}/save-structure")
# async def save_book_structure(
#     book_id: str,
#     structure_data: BookStructureInput,
#     supabase_client: Client = Depends(get_supabase),
#     current_user: dict = Depends(get_current_active_user)
# ):
#     """Save the book structure (sections and chapters) after user review"""
#     try:
#         # Convert to dict if needed
#         if hasattr(structure_data, 'dict'):
#             structure_dict = structure_data.dict()
#         else:
#             structure_dict = {
#                 'sections': getattr(structure_data, 'sections', []),
#                 'chapters': getattr(structure_data, 'chapters', [])
#             }
#         # Verify book ownership
#         book_response = supabase_client.table('books').select('*').eq('id', book_id).eq('user_id', current_user['id']).execute()
#         if not book_response.data:
#             raise HTTPException(status_code=404, detail="Book not found or not authorized")
        
#         book = book_response.data[0]
        
#         # Extract chapters from structure_data
#         chapters = structure_dict.get("chapters", [])
#         sections = structure_dict.get("sections", [])
        
#         if not chapters:
#             raise HTTPException(status_code=400, detail="No chapters provided in structure data")
        
#         # Delete existing chapter embeddings for this book
#         supabase_client.table('chapter_embeddings').delete().eq('book_id', book_id).execute()
#         print(f"Deleted existing chapter embeddings for book {book_id}")
        
#         # Delete existing chapters for this book
#         supabase_client.table('chapters').delete().eq('book_id', book_id).execute()
#         print(f"Deleted existing chapters for book {book_id}")
        
#         # Delete existing book sections for this book
#         supabase_client.table('book_sections').delete().eq('book_id', book_id).execute()
#         print(f"Deleted existing book sections for book {book_id}")
        
#         # Create section_id mapping if there are sections
#         section_id_map = {}
#         if sections:
#             for section in sections:
#                 section_data = {
#                     "book_id": book_id,
#                     "title": section.get("title", ""),
#                     "section_type": section.get("section_type", ""),
#                     "section_number": section.get("section_number", ""),
#                     "order_index": section.get("order_index", 0)
#                 }
#                 section_response = supabase_client.table('book_sections').insert(section_data).execute()
#                 section_id = section_response.data[0]['id']
#                 section_key = f"{section.get('title', '')}_{section.get('section_type', '')}"
#                 section_id_map[section_key] = section_id
        
#         # Insert new chapters and create embeddings
#         embeddings_service = EmbeddingsService(supabase_client)
        
#         for idx, chapter in enumerate(chapters, 1):
#             # Prepare chapter data
#             chapter_data = {
#                 "book_id": book_id,
#                 "title": chapter.get("title", f"Chapter {idx}"),
#                 "content": chapter.get("content", ""),
#                 "chapter_number": chapter.get("chapter_number", idx),
#                 "summary": chapter.get("summary", ""),
#                 "order_index": chapter.get("order_index", idx)
#             }
            
#             # Add section_id if chapter belongs to a section
#             if chapter.get("section_title") and sections:
#                 section_key = f"{chapter.get('section_title')}_{chapter.get('section_type', '')}"
#                 if section_key in section_id_map:
#                     chapter_data["section_id"] = section_id_map[section_key]
            
#             # Insert chapter
#             insert_response = supabase_client.table('chapters').insert(chapter_data).execute()
#             chapter_id = insert_response.data[0]['id']
#             print(f"Inserted chapter {idx}: {chapter_data['title']}")
            
#             # Create embeddings for the new chapter
#             if chapter_data["content"].strip():  # Only create embeddings if there's content
#                 try:
#                     await embeddings_service.create_chapter_embeddings(chapter_id, chapter_data["content"])
#                     print(f"Created embeddings for chapter {chapter_id}")
#                 except Exception as e:
#                     print(f"Warning: Failed to create embeddings for chapter {chapter_id}: {e}")
        
#         # Update book with structure information and final status
#         book_update = {
#             "has_sections": structure_dict.get("has_sections", False),
#             "structure_type": structure_dict.get("structure_type", "flat"),
#             "total_chapters": len(chapters),
#             "status": "READY",
#             "progress": 100,
#             "progress_message": "Book structure saved successfully"
#         }
        
#         supabase_client.table('books').update(book_update).eq('id', book_id).execute()
#         print(f"Updated book {book_id} with final status")
        
#         return {
#             "success": True, 
#             "message": "Book structure saved successfully",
#             "chapters_created": len(chapters),
#             "sections_created": len(sections)
#         }
        
#     except Exception as e:
#         print(f"Error saving book structure: {e}")
#         raise HTTPException(status_code=500, detail=f"Failed to save book structure: {str(e)}")
