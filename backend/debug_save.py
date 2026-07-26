import asyncio, json, traceback
from sqlalchemy import text
from app.core.database import async_session

async def main():
    async with async_session() as session:
        try:
            # Simulate inserting the first preview chapter manually
            from app.books.models import Chapter
            import uuid
            ch = Chapter(
                book_id=uuid.UUID("bd2e79b9-f94f-41d6-8bdb-b195e0edb522"),
                section_id=None,
                chapter_number="1",  # mimic preview payload type
                title="Test",
                content="hello",
                summary="",
                content_type="chapter",
                order_index=1,
            )
            session.add(ch)
            await session.flush()
            print("inserted")
        except Exception as e:
            print("ERROR", e)
            traceback.print_exc()

asyncio.run(main())
