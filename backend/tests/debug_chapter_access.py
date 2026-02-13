import asyncio
import uuid
import sys
import os

# Add backend directory to path
sys.path.append(
    "/Users/adesegunkoiki/My_app_projects/People-Protocol-apps/litinkapp/backend"
)

from app.core.database import get_session
from app.books.models import Chapter, Book
from sqlmodel import select


async def check_chapter_access():
    target_chapter_id = "126ccf25-df67-4d95-8c18-d78ba47f4ff4"

    async for session in get_session():
        try:
            print(f"Checking access for chapter: {target_chapter_id}")

            # 1. Fetch Chapter
            stmt = select(Chapter).where(Chapter.id == target_chapter_id)
            result = await session.exec(stmt)
            chapter = result.first()

            if not chapter:
                print("❌ Chapter NOT FOUND")
                return

            print(f"✅ Chapter Found: {chapter.title} (ID: {chapter.id})")
            print(f"   Book ID: {chapter.book_id}")

            # 2. Fetch Book
            stmt = select(Book).where(Book.id == chapter.book_id)
            result = await session.exec(stmt)
            book = result.first()

            if not book:
                print("❌ Book NOT FOUND for this chapter")
                return

            print(f"✅ Book Found: {book.title} (ID: {book.id})")
            print(f"   Status: {book.status}")
            print(f"   User ID: {book.user_id} (Type: {type(book.user_id)})")

            # 3. Simulate Logic
            # Note: We don't have the current_user ID from the failed request effectively,
            # but we can see what the book's owner is.

        except Exception as e:
            print(f"Error: {e}")
        finally:
            break


if __name__ == "__main__":
    asyncio.run(check_chapter_access())
