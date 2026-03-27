from app.tasks.celery_app import celery_app
from app.core.database import async_session
from app.core.services.storage import get_storage_service, S3StorageService
from sqlalchemy import text
import asyncio
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, time_limit=3600, soft_time_limit=3500)
def backfill_media_to_s3(self, batch_size=20, dry_run=False):
    """Backfill existing ModelsLab CDN URLs to our own S3 storage."""
    return asyncio.run(async_backfill_media_to_s3(batch_size, dry_run))


async def async_backfill_media_to_s3(batch_size=20, dry_run=False):
    """
    Async backfill: find all image_generations with ModelsLab CDN URLs,
    download them, upload to S3, update the record.
    """
    stats = {
        "total_found": 0,
        "migrated": 0,
        "already_expired": 0,
        "failed": 0,
        "skipped": 0,
    }

    async with async_session() as session:
        # Find all records with ModelsLab CDN URLs
        query = text(
            """
            SELECT id, image_url, user_id, meta
            FROM image_generations
            WHERE status = 'completed'
              AND image_url IS NOT NULL
              AND (
                image_url LIKE '%%pub-%%'
                OR image_url LIKE '%%modelslab%%'
                OR image_url LIKE '%%stablediffusionapi%%'
              )
            ORDER BY created_at DESC
        """
        )

        result = await session.execute(query)
        records = result.mappings().all()
        stats["total_found"] = len(records)
        logger.info(f"[Backfill] Found {len(records)} records to migrate (dry_run={dry_run})")

        if not records:
            return stats

        storage = get_storage_service()

        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            logger.info(
                f"[Backfill] Processing batch {i // batch_size + 1} ({len(batch)} records)"
            )

            for record in batch:
                record_id = str(record["id"])
                old_url = record["image_url"]
                user_id = str(record["user_id"]) if record["user_id"] else "system"
                existing_meta = record["meta"] or {}

                if dry_run:
                    logger.info(
                        f"[Backfill DRY RUN] Would migrate {record_id}: {old_url[:60]}..."
                    )
                    stats["migrated"] += 1
                    continue

                try:
                    s3_path = S3StorageService.build_media_path(
                        user_id=user_id,
                        media_type="images",
                        record_id=record_id,
                        extension="png",
                    )
                    new_url = await storage.persist_from_url(
                        old_url, s3_path, content_type="image/png"
                    )

                    # Update record with permanent S3 URL
                    updated_meta = {
                        **existing_meta,
                        "original_cdn_url": old_url,
                        "backfill_migrated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    update_query = text(
                        """
                        UPDATE image_generations
                        SET image_url = :new_url, meta = :meta, updated_at = NOW()
                        WHERE id = :id
                    """
                    )
                    await session.execute(
                        update_query,
                        {
                            "new_url": new_url,
                            "meta": json.dumps(updated_meta),
                            "id": record_id,
                        },
                    )
                    await session.commit()
                    stats["migrated"] += 1
                    logger.info(f"[Backfill] Migrated {record_id}")

                except Exception as e:
                    error_msg = str(e)
                    if "404" in error_msg:
                        # CDN already expired
                        updated_meta = {
                            **existing_meta,
                            "cdn_expired": True,
                            "original_cdn_url": old_url,
                            "backfill_failed_at": datetime.now(timezone.utc).isoformat(),
                        }
                        expire_query = text(
                            """
                            UPDATE image_generations
                            SET image_url = NULL, meta = :meta, updated_at = NOW()
                            WHERE id = :id
                        """
                        )
                        await session.execute(
                            expire_query,
                            {"meta": json.dumps(updated_meta), "id": record_id},
                        )
                        await session.commit()
                        stats["already_expired"] += 1
                        logger.warning(f"[Backfill] CDN expired for {record_id}")
                    else:
                        stats["failed"] += 1
                        logger.error(f"[Backfill] Failed {record_id}: {e}")

            # Pause between batches
            await asyncio.sleep(2)

    logger.info(f"[Backfill] Complete: {stats}")
    return stats
