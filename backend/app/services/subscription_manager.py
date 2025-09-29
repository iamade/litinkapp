from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import stripe
from app.core.database import get_supabase
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class SubscriptionTier(Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class SubscriptionManager:
    """
    Manages user subscriptions and tier-based access
    """

    TIER_LIMITS = {
        SubscriptionTier.FREE: {
            "videos_per_month": 2,
            "max_video_duration": 60,  # seconds
            "max_resolution": "720p",
            "watermark": True,
            "priority": 0,
            "support": "community",
            "api_access": False,
            "price_monthly": 0
        },
        SubscriptionTier.BASIC: {
            "videos_per_month": 10,
            "max_video_duration": 180,
            "max_resolution": "720p",
            "watermark": False,
            "priority": 1,
            "support": "email",
            "api_access": False,
            "price_monthly": 19
        },
        SubscriptionTier.PRO: {
            "videos_per_month": 30,
            "max_video_duration": 300,
            "max_resolution": "1080p",
            "watermark": False,
            "priority": 2,
            "support": "priority_email",
            "api_access": False,
            "voice_cloning": True,
            "price_monthly": 49
        },
        SubscriptionTier.PREMIUM: {
            "videos_per_month": 100,
            "max_video_duration": 600,
            "max_resolution": "4K",
            "watermark": False,
            "priority": 3,
            "support": "chat",
            "api_access": True,
            "voice_cloning": True,
            "custom_voices": 5,
            "price_monthly": 99
        },
        SubscriptionTier.PROFESSIONAL: {
            "videos_per_month": 500,  # Soft limit
            "max_video_duration": 1800,
            "max_resolution": "4K",
            "watermark": False,
            "priority": 4,
            "support": "phone",
            "api_access": True,
            "voice_cloning": True,
            "custom_voices": "unlimited",
            "custom_models": True,
            "price_monthly": 299
        },
        SubscriptionTier.ENTERPRISE: {
            "videos_per_month": "unlimited",
            "max_video_duration": "unlimited",
            "max_resolution": "8K",
            "watermark": False,
            "priority": 5,
            "support": "dedicated",
            "api_access": True,
            "white_label": True,
            "custom_deployment": True,
            "sla": "99.9%",
            "price_monthly": "custom"
        }
    }

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or get_supabase()
        stripe.api_key = settings.STRIPE_SECRET_KEY

    async def get_user_tier(self, user_id: str) -> SubscriptionTier:
        """
        Get user's current subscription tier
        """
        try:
            logger.info(f"Getting user tier for user_id: {user_id}")

            # Check if user has any subscriptions (active or not)
            all_subs = self.supabase.table('user_subscriptions').select('*').eq('user_id', user_id).execute()
            logger.info(f"User {user_id} has {len(all_subs.data or [])} total subscriptions")

            # Check database for active user subscription - don't use .single() as it may return 0 rows
            result = self.supabase.table('user_subscriptions').select('*').eq(
                'user_id', user_id
            ).eq('status', 'active').execute()

            if result.data and len(result.data) > 0:
                tier = SubscriptionTier(result.data[0]['tier'])
                logger.info(f"User {user_id} has active {tier.value} subscription")
                return tier
            else:
                # Default to free tier
                logger.info(f"User {user_id} has no active subscription, defaulting to FREE tier")
                return SubscriptionTier.FREE

        except Exception as e:
            logger.error(f"Error getting user tier for user {user_id}: {str(e)}")
            return SubscriptionTier.FREE

    async def check_usage_limits(
        self,
        user_id: str,
        resource_type: str = "video"
    ) -> Dict[str, Any]:
        """
        Check if user has exceeded their usage limits
        """
        tier = await self.get_user_tier(user_id)
        limits = self.TIER_LIMITS[tier]

        # Get current month's usage
        current_period_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)

        usage_result = self.supabase.table('usage_logs').select('*').eq(
            'user_id', user_id
        ).gte('created_at', current_period_start.isoformat()).execute()

        video_count = len([u for u in usage_result.data if u['resource_type'] == 'video'])

        return {
            "tier": tier.value,
            "limits": limits,
            "current_usage": {
                "videos": video_count,
                "period_start": current_period_start.isoformat(),
                "period_end": (current_period_start + timedelta(days=30)).isoformat()
            },
            "can_generate": video_count < limits["videos_per_month"] if isinstance(limits["videos_per_month"], int) else True,
            "videos_remaining": max(0, limits["videos_per_month"] - video_count) if isinstance(limits["videos_per_month"], int) else "unlimited"
        }

    async def create_checkout_session(
        self,
        user_id: str,
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """
        Create Stripe checkout session for subscription
        """
        try:
            # Get price ID for tier (you need to create these in Stripe Dashboard)
            price_ids = {
                SubscriptionTier.BASIC: settings.STRIPE_BASIC_PRICE_ID,
                SubscriptionTier.PRO: settings.STRIPE_PRO_PRICE_ID,
                SubscriptionTier.PREMIUM: settings.STRIPE_PREMIUM_PRICE_ID,
                SubscriptionTier.PROFESSIONAL: settings.STRIPE_PROFESSIONAL_PRICE_ID
            }

            price_id = price_ids.get(tier)
            if not price_id:
                raise ValueError(f"No price ID configured for tier: {tier.value}")

            # Create Stripe checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': user_id,
                    'tier': tier.value
                }
            )

            return {
                "checkout_url": session.url,
                "session_id": session.id
            }

        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            raise

    async def handle_subscription_webhook(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ):
        """
        Handle Stripe webhook events for subscriptions
        """
        if event_type == 'checkout.session.completed':
            session = event_data['object']
            user_id = session['metadata']['user_id']
            tier = session['metadata']['tier']

            # Update user subscription in database
            self.supabase.table('user_subscriptions').upsert({
                'user_id': user_id,
                'tier': tier,
                'status': 'active',
                'stripe_customer_id': session['customer'],
                'stripe_subscription_id': session['subscription'],
                'current_period_start': datetime.now().isoformat(),
                'current_period_end': (datetime.now() + timedelta(days=30)).isoformat(),
                'video_count_limit': self.TIER_LIMITS[SubscriptionTier(tier)]['videos_per_month'],
                'video_count_used': 0
            }).execute()

            logger.info(f"Subscription activated for user {user_id}: {tier}")

        elif event_type == 'customer.subscription.deleted':
            subscription = event_data['object']

            # Downgrade to free tier
            result = self.supabase.table('user_subscriptions').update({
                'status': 'cancelled',
                'tier': 'free'
            }).eq('stripe_subscription_id', subscription['id']).execute()

            logger.info(f"Subscription cancelled: {subscription['id']}")

    async def record_usage(
        self,
        user_id: str,
        resource_type: str,
        cost_usd: float = 0.0,
        metadata: Dict[str, Any] = None
    ):
        """
        Record usage for billing and limits tracking
        """
        try:
            usage_data = {
                'user_id': user_id,
                'resource_type': resource_type,
                'cost_usd': cost_usd,
                'metadata': metadata or {},
                'created_at': datetime.now().isoformat()
            }

            self.supabase.table('usage_logs').insert(usage_data).execute()

            # Update subscription usage count if it's a video
            if resource_type == 'video':
                tier = await self.get_user_tier(user_id)
                if tier != SubscriptionTier.FREE:
                    # Increment video count for paid users
                    self.supabase.table('user_subscriptions').update({
                        'video_count_used': self.supabase.table('user_subscriptions').select('video_count_used').eq('user_id', user_id).single().execute().data['video_count_used'] + 1
                    }).eq('user_id', user_id).execute()

            logger.info(f"Usage recorded for user {user_id}: {resource_type}, cost: ${cost_usd}")

        except Exception as e:
            logger.error(f"Error recording usage: {str(e)}")

    async def can_user_generate_video(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user can generate a video based on their subscription limits
        """
        usage_check = await self.check_usage_limits(user_id, "video")

        return {
            "can_generate": usage_check["can_generate"],
            "tier": usage_check["tier"],
            "videos_used": usage_check["current_usage"]["videos"],
            "videos_limit": usage_check["limits"]["videos_per_month"],
            "videos_remaining": usage_check["videos_remaining"]
        }