import asyncio
import asyncpg
import os


async def check_db(password):
    try:
        conn = await asyncpg.connect(
            user="postgres",
            password=password,
            database="litinkai",
            host="localhost",
            port=5432,
        )
        print(f"✅ Success with password: {password}")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Failed with password: {password} - Error: {e}")
        return False


async def main():
    passwords = ["1234", "litink123", "postgres", "password"]
    for p in passwords:
        if await check_db(p):
            break


if __name__ == "__main__":
    asyncio.run(main())
