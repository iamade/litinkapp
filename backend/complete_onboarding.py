import asyncio
from sqlalchemy import text
from app.core.database import async_session

async def main():
    async with async_session() as s:
        r = await s.exec(text("UPDATE \"user\" SET onboarding_completed=true WHERE email='support@litinkai.com'"))
        await s.commit()
        print('updated', r.rowcount)

asyncio.run(main())
