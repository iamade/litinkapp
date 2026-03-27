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
        """Premium+ should allow unrestricted downloads"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        limits = SubscriptionManager.TIER_LIMITS[SubscriptionTier.PREMIUM]
        assert limits['watermark'] is False
