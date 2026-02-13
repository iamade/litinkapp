import asyncio
import uuid
from sqlmodel import select
from app.core.database import get_session
from app.plots.models import Character


async def list_characters():
    async for session in get_session():
        stmt = select(Character.id, Character.name, Character.user_id)
        result = await session.exec(stmt)
        characters = result.all()
        print(f"Found {len(characters)} characters:")
        for char in characters:
            print(f"ID: {char.id}, Name: {char.name}, User: {char.user_id}")

        # Check specific ID
        target_id = "fdad9eed-6d90-4b04-9a0b-8daf62780997"
        try:
            target_uuid = uuid.UUID(target_id)
            found = any(c.id == target_uuid for c in characters)
            print(f"\nTarget ID {target_id} found: {found}")
        except ValueError:
            print(f"\nTarget ID {target_id} is not a valid UUID")


if __name__ == "__main__":
    asyncio.run(list_characters())
