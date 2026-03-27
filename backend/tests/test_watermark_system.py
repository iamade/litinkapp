import pytest

class TestWatermarkSystem:
    def test_free_tier_has_watermark(self):
        """Free tier should have watermark=True in TIER_LIMITS"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        limits = SubscriptionManager.TIER_LIMITS[SubscriptionTier.FREE]
        assert limits['watermark'] is True

    def test_basic_tier_no_watermark(self):
        """Basic tier and above should have watermark=False"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        for tier in [SubscriptionTier.BASIC, SubscriptionTier.PRO, SubscriptionTier.PREMIUM, SubscriptionTier.PROFESSIONAL]:
            assert SubscriptionManager.TIER_LIMITS[tier]['watermark'] is False, f'{tier} should not have watermark'

    def test_all_tiers_have_watermark_key(self):
        """Every tier should define watermark setting"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        for tier in SubscriptionTier:
            if tier == SubscriptionTier.ENTERPRISE:
                continue
            assert 'watermark' in SubscriptionManager.TIER_LIMITS[tier], f'{tier} missing watermark key'
