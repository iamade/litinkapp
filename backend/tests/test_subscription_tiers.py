import pytest

class TestSubscriptionTierConfig:
    def test_all_tiers_have_required_keys(self):
        """Every tier must define all required limit keys"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        required_keys = ['videos_per_month', 'images_per_month', 'audio_per_month', 'scripts_per_month', 'plots_per_month', 'price_monthly', 'display_name', 'watermark', 'priority', 'support']
        for tier in SubscriptionTier:
            if tier == SubscriptionTier.ENTERPRISE:
                continue
            for key in required_keys:
                assert key in SubscriptionManager.TIER_LIMITS[tier], f'{tier.value} missing {key}'

    def test_tier_prices_ascending(self):
        """Higher tiers should cost more"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        tiers_ordered = [SubscriptionTier.FREE, SubscriptionTier.BASIC, SubscriptionTier.PRO, SubscriptionTier.PREMIUM, SubscriptionTier.PROFESSIONAL]
        prices = [SubscriptionManager.TIER_LIMITS[t]['price_monthly'] for t in tiers_ordered]
        assert prices == sorted(prices), f'Prices not ascending: {prices}'

    def test_tier_display_names_correct(self):
        """Verify display names match expected values"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        expected = {
            SubscriptionTier.FREE: 'Free',
            SubscriptionTier.BASIC: 'Basic',
            SubscriptionTier.PRO: 'Standard',  # PRO enum displays as Standard
            SubscriptionTier.PREMIUM: 'Premium',
            SubscriptionTier.PROFESSIONAL: 'Professional',
        }
        for tier, name in expected.items():
            assert SubscriptionManager.TIER_LIMITS[tier]['display_name'] == name, f'{tier.value} display_name should be {name}'

    def test_voice_cloning_gating(self):
        """Voice cloning should only be available from Pro tier onwards"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        assert SubscriptionManager.TIER_LIMITS[SubscriptionTier.FREE]['voice_cloning'] is False
        assert SubscriptionManager.TIER_LIMITS[SubscriptionTier.BASIC]['voice_cloning'] is False
        assert SubscriptionManager.TIER_LIMITS[SubscriptionTier.PRO]['voice_cloning'] is True
        assert SubscriptionManager.TIER_LIMITS[SubscriptionTier.PREMIUM]['voice_cloning'] is True

    def test_model_selection_gating(self):
        """Model selection should only be available from Pro tier onwards"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        assert SubscriptionManager.TIER_LIMITS[SubscriptionTier.FREE]['model_selection'] is False
        assert SubscriptionManager.TIER_LIMITS[SubscriptionTier.BASIC]['model_selection'] is False
        assert SubscriptionManager.TIER_LIMITS[SubscriptionTier.PRO]['model_selection'] is True

    def test_api_access_gating(self):
        """API access should only be available from Premium tier onwards"""
        from app.api.services.subscription import SubscriptionManager
        from app.subscriptions.models import SubscriptionTier
        assert SubscriptionManager.TIER_LIMITS[SubscriptionTier.FREE]['api_access'] is False
        assert SubscriptionManager.TIER_LIMITS[SubscriptionTier.BASIC]['api_access'] is False
        assert SubscriptionManager.TIER_LIMITS[SubscriptionTier.PRO]['api_access'] is False
        assert SubscriptionManager.TIER_LIMITS[SubscriptionTier.PREMIUM]['api_access'] is True
