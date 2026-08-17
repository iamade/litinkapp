import asyncio
from sqlalchemy import text
from app.core.database import async_session

async def main():
    async with async_session() as s:
        # Update MinIO credentials to match local.yml defaults
        r = await s.exec(text("UPDATE admin_settings SET value='minioadmin' WHERE key='MINIO_ACCESS_KEY'"))
        await s.commit()
        print('access_key updated', r.rowcount)
        r = await s.exec(text("UPDATE admin_settings SET value='minioadmin' WHERE key='MINIO_SECRET_KEY'"))
        await s.commit()
        print('secret_key updated', r.rowcount)

asyncio.run(main())
