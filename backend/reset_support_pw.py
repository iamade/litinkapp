import asyncio
from sqlalchemy import text
from app.core.database import async_session

async def main():
    async with async_session() as s:
        r = await s.exec(text("UPDATE \"user\" SET hashed_password='$argon2id$v=19$m=65536,t=3,p=4$a62VUgph7N37v/e+V4oRAg$7fGDS8XIhBYoWRl7+d5gIWDrTG4NSOGwpUnquPGc2Fc' WHERE email='support@litinkai.com'"))
        await s.commit()
        print('updated', r.rowcount)

asyncio.run(main())
