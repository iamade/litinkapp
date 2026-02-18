import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import async_session
from app.videos.models import ImageGeneration
from sqlmodel import select, delete
from sqlalchemy import func


async def cleanup_stale_images():
    print("Starting cleanup of stale 'pending' image records...")

    cutoff_time = datetime.utcnow() - timedelta(minutes=5)
    print(f"Deleting records older than: {cutoff_time.isoformat()}")

    async with async_session() as session:
        try:
            # Count query for both pending and in_progress
            count_query = select(func.count()).where(
                (ImageGeneration.status == "pending")
                | (ImageGeneration.status == "in_progress"),
                ImageGeneration.created_at < cutoff_time,
            )
            result = await session.execute(count_query)
            count = result.scalar()

            if count == 0:
                print("No stale 'pending' or 'in_progress' records found.")
                return

            print(f"Found {count} stale records. Marking as 'failed'...")

            # Update query - set status to failed instead of deleting
            from sqlalchemy import update

            update_query = (
                update(ImageGeneration)
                .where(
                    (ImageGeneration.status == "pending")
                    | (ImageGeneration.status == "in_progress"),
                    ImageGeneration.created_at < cutoff_time,
                )
                .values(
                    status="failed",
                    error_message="Task timed out or failed without reporting (Stale Record Cleanup)",
                    updated_at=datetime.utcnow(),
                )
            )

            await session.execute(update_query)
            await session.commit()

            print(f"Successfully updated {count} stale image records to 'failed'.")

        except Exception as e:
            print(f"Error during cleanup: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(cleanup_stale_images())
