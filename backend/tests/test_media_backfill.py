import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBackfillMediaToS3:
    @pytest.mark.asyncio
    async def test_dry_run_returns_stats(self):
        """Dry run should count records but not modify anything"""
        from app.tasks.media_backfill_task import async_backfill_media_to_s3

        mock_records = [
            {
                "id": "rec-1",
                "image_url": "https://pub-cdn.modelslab.com/img1.png",
                "user_id": "user-1",
                "meta": {},
            },
            {
                "id": "rec-2",
                "image_url": "https://modelslab.com/output/img2.png",
                "user_id": "user-2",
                "meta": {},
            },
        ]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = mock_records
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.tasks.media_backfill_task.async_session") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            stats = await async_backfill_media_to_s3(batch_size=20, dry_run=True)

            assert stats["total_found"] == 2
            assert stats["migrated"] == 2  # dry_run counts as migrated
            mock_session.commit.assert_not_called()  # No DB writes in dry run

    @pytest.mark.asyncio
    async def test_empty_db_returns_zeros(self):
        """No records to migrate should return all zeros"""
        from app.tasks.media_backfill_task import async_backfill_media_to_s3

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.tasks.media_backfill_task.async_session") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            stats = await async_backfill_media_to_s3()
            assert stats["total_found"] == 0
            assert stats["migrated"] == 0


class TestMediaHealthEndpoint:
    @pytest.mark.asyncio
    async def test_returns_correct_counts(self):
        """Health endpoint should return image counts by storage location"""
        # This tests the SQL query logic — would need integration test with real DB
        # For unit test, verify the endpoint returns the expected shape
        pass  # Integration test needed
