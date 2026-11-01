import pytest

class TestWatermarkSystem:
    def test_free_tier_has_watermark(self):
        """Free tier should have watermark=True in TIER_LIMITS"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        limits = SubscriptionManager.TIER_LIMITS[SubscriptionTier.FREE]
        assert limits['watermark'] is True

    def test_basic_tier_no_watermark(self):
        """KAN-140 (updated policy 2026-04-02): watermark is ON by default for ALL tiers.

        Paid tiers (Basic and above) can toggle it OFF at the point of download via
        can_remove_watermark; the tier default itself stays True. The name is kept so
        the id is stable; the earlier False expectation was superseded by KAN-140.
        """
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        for tier in [SubscriptionTier.BASIC, SubscriptionTier.PRO, SubscriptionTier.PREMIUM, SubscriptionTier.PROFESSIONAL]:
            limits = SubscriptionManager.TIER_LIMITS[tier]
            assert limits['watermark'] is True, f'{tier} should default to watermark ON'
            assert limits['can_remove_watermark'] is True, f'{tier} should be able to remove the watermark at download'

    def test_free_tier_cannot_remove_watermark(self):
        """Free tier is watermarked and cannot toggle it off at download (KAN-140)"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        limits = SubscriptionManager.TIER_LIMITS[SubscriptionTier.FREE]
        assert limits['watermark'] is True
        assert limits['can_remove_watermark'] is False

    def test_all_tiers_have_watermark_key(self):
        """Every tier should define watermark setting"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        for tier in SubscriptionTier:
            if tier == SubscriptionTier.ENTERPRISE:
                continue
            assert 'watermark' in SubscriptionManager.TIER_LIMITS[tier], f'{tier} missing watermark key'
