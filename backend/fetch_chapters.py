import asyncio
from sqlalchemy import text
from app.core.database import async_session

async def main():
    async with async_session() as s:
        r = await s.exec(text("SELECT id, title, content_type, chapter_number, order_index FROM chapters WHERE book_id='4d0d78e0-74d2-40d1-adb5-1b5b8e9bf66e' ORDER BY order_index"))
        for row in r.all():
            d = dict(row._mapping)
            print(d)

asyncio.run(main())
