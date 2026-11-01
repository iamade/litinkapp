import pytest

class TestDownloadRestrictions:
    def test_free_tier_config(self):
        """Free tier should have download restrictions in its config"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        limits = SubscriptionManager.TIER_LIMITS[SubscriptionTier.FREE]
        assert limits['watermark'] is True  # Download should be watermarked
        # When implemented: assert limits.get('download_individual_assets', False) is False

    def test_premium_tier_unrestricted(self):
        """Premium+ may download without a watermark (KAN-140, updated policy 2026-04-02).

        The tier default is watermark ON for every tier; Premium can toggle it OFF at the
        point of download via can_remove_watermark. The earlier watermark-False expectation
        was superseded by KAN-140.
        """
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        limits = SubscriptionManager.TIER_LIMITS[SubscriptionTier.PREMIUM]
        assert limits['watermark'] is True
        assert limits['can_remove_watermark'] is True
