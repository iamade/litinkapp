from app.core.database import async_session
from sqlalchemy import text
import asyncio

async def main():
    async with async_session() as s:
        r = await s.exec(text("SELECT id, email FROM users WHERE email LIKE 'psq%' LIMIT 5"))
        print([dict(row._mapping) for row in r.all()])

asyncio.run(main())
