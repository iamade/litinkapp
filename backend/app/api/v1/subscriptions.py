from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from supabase import Client
from datetime import datetime
import json

from app.schemas.subscription import (
    UserSubscription,
    SubscriptionTierInfo,
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    SubscriptionUsageStats,
    SubscriptionCancelRequest,
    SubscriptionCancelResponse,
    WebhookEvent
)
from app.core.database import get_supabase
from app.core.auth import get_current_active_user
from app.services.stripe_service import stripe_service

router = APIRouter()


@router.get("/current", response_model=UserSubscription)
async def get_current_subscription(
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get the current user's subscription"""
    try:
        response = supabase_client.table('user_subscriptions').select('*').eq('user_id', current_user['id']).execute()

        if not response.data:
            # Return free tier if no subscription exists
            free_tier = supabase_client.table('subscription_tiers').select('*').eq('tier', 'free').single().execute()
            if not free_tier.data:
                raise HTTPException(status_code=500, detail="Free tier configuration not found")

            return {
                'id': f"free-{current_user['id']}",
                'user_id': current_user['id'],
                'tier': 'free',
                'status': 'active',
                'monthly_video_limit': free_tier.data['monthly_video_limit'],
                'video_quality': free_tier.data['video_quality'],
                'has_watermark': free_tier.data['has_watermark'],
                'videos_generated_this_period': 0,
                'created_at': current_user.get('created_at'),
                'updated_at': current_user.get('updated_at')
            }

        return response.data[0]

    except Exception as e:
        print(f"[SubscriptionsAPI] Error getting current subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscription")


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    checkout_data: CheckoutSessionCreate,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Create a Stripe checkout session for subscription"""
    try:
        # Get tier information
        tier_response = supabase_client.table('subscription_tiers').select('*').eq('tier', checkout_data.tier.value).single().execute()
        if not tier_response.data:
            raise HTTPException(status_code=404, detail="Subscription tier not found")

        tier_info = tier_response.data
        if not tier_info.get('stripe_price_id'):
            raise HTTPException(status_code=400, detail="Tier not available for purchase")

        # Disable backend integration for pro tier
        if tier_info['tier'] == 'pro':
            raise HTTPException(status_code=400, detail="Pro tier is coming soon")

        # Create or get Stripe customer
        customer_id = await stripe_service.create_or_get_customer(
            user_id=current_user['id'],
            email=current_user.get('email'),
            name=current_user.get('display_name')
        )

        # Create checkout session
        session_data = await stripe_service.create_checkout_session(
            customer_id=customer_id,
            price_id=tier_info['stripe_price_id'],
            success_url=checkout_data.success_url,
            cancel_url=checkout_data.cancel_url,
            user_id=current_user['id']
        )

        return session_data

    except Exception as e:
        print(f"[SubscriptionsAPI] Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/webhook")
async def handle_stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    from supabase import create_client
    from app.core.config import settings

    try:
        payload = await request.body()
        signature = request.headers.get('stripe-signature')

        if not signature:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")

        # Handle webhook
        event_data = await stripe_service.handle_webhook(payload, signature)

        # Create service role supabase client for webhook processing
        supabase_client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY
        )

        # Process the event based on type
        if event_data['event_type'] == 'subscription.created':
            await _handle_subscription_created(event_data, supabase_client)
        elif event_data['event_type'] == 'subscription.updated':
            await _handle_subscription_updated(event_data, supabase_client)
        elif event_data['event_type'] == 'subscription.deleted':
            await _handle_subscription_deleted(event_data, supabase_client)
        elif event_data['event_type'] == 'payment.succeeded':
            await _handle_payment_succeeded(event_data, supabase_client)
        elif event_data['event_type'] == 'payment.failed':
            await _handle_payment_failed(event_data, supabase_client)

        return {"status": "success"}

    except Exception as e:
        print(f"[SubscriptionsAPI] Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/usage", response_model=SubscriptionUsageStats)
async def get_usage_stats(
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get current usage statistics"""
    try:
        # Get user's subscription
        sub_response = supabase_client.table('user_subscriptions').select('*').eq('user_id', current_user['id']).execute()

        if not sub_response.data:
            # Use free tier defaults
            free_tier = supabase_client.table('subscription_tiers').select('*').eq('tier', 'free').single().execute()
            if not free_tier.data:
                raise HTTPException(status_code=500, detail="Free tier configuration not found")

            return {
                'current_period_videos': 0,
                'period_limit': free_tier.data['monthly_video_limit'],
                'remaining_videos': free_tier.data['monthly_video_limit'],
                'can_generate_video': True
            }

        subscription = sub_response.data[0]
        current_videos = subscription.get('videos_generated_this_period', 0)
        limit = subscription.get('monthly_video_limit', 0)

        return {
            'current_period_videos': current_videos,
            'period_limit': limit,
            'remaining_videos': max(0, limit - current_videos),
            'period_start': subscription.get('current_period_start'),
            'period_end': subscription.get('current_period_end'),
            'can_generate_video': current_videos < limit
        }

    except Exception as e:
        print(f"[SubscriptionsAPI] Error getting usage stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage statistics")


@router.get("/tiers", response_model=List[SubscriptionTierInfo])
async def get_subscription_tiers(
    supabase_client: Client = Depends(get_supabase)
):
    """Get available subscription tiers"""
    try:
        print(f"[SubscriptionsAPI] Starting get_subscription_tiers, supabase_client: {supabase_client}")
        response = supabase_client.table('subscription_tiers').select('*').eq('is_active', True).order('display_order').execute()
        print(f"[SubscriptionsAPI] Query executed, data length: {len(response.data) if response.data else 0}")

        if not response.data:
            print(f"[SubscriptionsAPI] No active subscription tiers found")

        return response.data

    except Exception as e:
        print(f"[SubscriptionsAPI] Error getting subscription tiers: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscription tiers")


@router.post("/cancel", response_model=SubscriptionCancelResponse)
async def cancel_subscription(
    cancel_data: SubscriptionCancelRequest = SubscriptionCancelRequest(),
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Cancel the current user's subscription"""
    try:
        # Get user's subscription
        sub_response = supabase_client.table('user_subscriptions').select('*').eq('user_id', current_user['id']).execute()

        if not sub_response.data:
            raise HTTPException(status_code=404, detail="No active subscription found")

        subscription = sub_response.data[0]
        if not subscription.get('stripe_subscription_id'):
            raise HTTPException(status_code=400, detail="No Stripe subscription to cancel")

        # Cancel via Stripe
        cancel_result = await stripe_service.cancel_subscription(subscription['stripe_subscription_id'])

        # Update local database
        update_data = {
            'cancel_at_period_end': cancel_result['cancel_at_period_end'],
            'updated_at': 'now()'
        }
        if cancel_data.cancel_at_period_end:
            update_data['cancelled_at'] = 'now()'

        supabase_client.table('user_subscriptions').update(update_data).eq('id', subscription['id']).execute()

        # Log the cancellation
        supabase_client.table('subscription_history').insert({
            'user_id': current_user['id'],
            'subscription_id': subscription['id'],
            'event_type': 'cancelled',
            'from_status': subscription['status'],
            'to_status': 'cancelled' if not cancel_data.cancel_at_period_end else subscription['status'],
            'reason': 'User requested cancellation'
        }).execute()

        return {
            'subscription_id': subscription['id'],
            'status': cancel_result['status'],
            'cancel_at_period_end': cancel_result['cancel_at_period_end'],
            'current_period_end': cancel_result.get('current_period_end')
        }

    except Exception as e:
        print(f"[SubscriptionsAPI] Error cancelling subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.post("/reactivate")
async def reactivate_subscription(
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Reactivate a cancelled subscription"""
    try:
        # Get user's subscription
        sub_response = supabase_client.table('user_subscriptions').select('*').eq('user_id', current_user['id']).execute()

        if not sub_response.data:
            raise HTTPException(status_code=404, detail="No subscription found")

        subscription = sub_response.data[0]
        if not subscription.get('stripe_subscription_id'):
            raise HTTPException(status_code=400, detail="No Stripe subscription to reactivate")

        # Reactivate via Stripe
        reactivate_result = await stripe_service.reactivate_subscription(subscription['stripe_subscription_id'])

        # Update local database
        supabase_client.table('user_subscriptions').update({
            'cancel_at_period_end': False,
            'cancelled_at': None,
            'updated_at': 'now()'
        }).eq('id', subscription['id']).execute()

        # Log the reactivation
        supabase_client.table('subscription_history').insert({
            'user_id': current_user['id'],
            'subscription_id': subscription['id'],
            'event_type': 'reactivated',
            'from_status': subscription['status'],
            'to_status': reactivate_result['status'],
            'reason': 'User reactivated subscription'
        }).execute()

        return {"message": "Subscription reactivated successfully"}

    except Exception as e:
        print(f"[SubscriptionsAPI] Error reactivating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to reactivate subscription")


# Helper functions for webhook processing
async def _handle_subscription_created(event_data: dict, supabase_client: Client):
    """Handle subscription created webhook"""
    try:
        # Get tier info from price_id
        tier_response = supabase_client.table('subscription_tiers').select('*').eq('stripe_price_id', event_data['price_id']).single().execute()
        if not tier_response.data:
            print(f"[Webhook] Tier not found for price_id: {event_data['price_id']}")
            return

        tier_info = tier_response.data

        # Get user_id from customer metadata
        customer = await stripe_service.get_customer(event_data['customer_id'])
        user_id = customer.get('metadata', {}).get('user_id')

        if not user_id:
            print(f"[Webhook] No user_id found for customer: {event_data['customer_id']}")
            return

        # Create or update subscription
        subscription_data = {
            'user_id': user_id,
            'tier': tier_info['tier'],
            'status': event_data['status'],
            'stripe_customer_id': event_data['customer_id'],
            'stripe_subscription_id': event_data['subscription_id'],
            'stripe_price_id': event_data['price_id'],
            'monthly_video_limit': tier_info['monthly_video_limit'],
            'video_quality': tier_info['video_quality'],
            'has_watermark': tier_info['has_watermark'],
            'current_period_start': datetime.fromtimestamp(event_data['current_period_start']),
            'current_period_end': datetime.fromtimestamp(event_data['current_period_end']),
            'videos_generated_this_period': 0
        }

        supabase_client.table('user_subscriptions').upsert(subscription_data, on_conflict='user_id').execute()

        # Log the event
        supabase_client.table('subscription_history').insert({
            'user_id': user_id,
            'event_type': 'created',
            'to_tier': tier_info['tier'],
            'to_status': event_data['status'],
            'stripe_event_id': event_data.get('stripe_event_id')
        }).execute()

        print(f"[Webhook] Subscription created for user {user_id}")

    except Exception as e:
        print(f"[Webhook] Error handling subscription created: {e}")


async def _handle_subscription_updated(event_data: dict, supabase_client: Client):
    """Handle subscription updated webhook"""
    try:
        # Update subscription in database
        update_data = {
            'status': event_data['status'],
            'current_period_start': datetime.fromtimestamp(event_data['current_period_start']),
            'current_period_end': datetime.fromtimestamp(event_data['current_period_end']),
            'cancel_at_period_end': event_data.get('cancel_at_period_end', False),
            'updated_at': 'now()'
        }

        supabase_client.table('user_subscriptions').update(update_data).eq('stripe_subscription_id', event_data['subscription_id']).execute()

        print(f"[Webhook] Subscription updated: {event_data['subscription_id']}")

    except Exception as e:
        print(f"[Webhook] Error handling subscription updated: {e}")


async def _handle_subscription_deleted(event_data: dict, supabase_client: Client):
    """Handle subscription deleted webhook"""
    try:
        # Update subscription status
        supabase_client.table('user_subscriptions').update({
            'status': 'cancelled',
            'updated_at': 'now()'
        }).eq('stripe_subscription_id', event_data['subscription_id']).execute()

        print(f"[Webhook] Subscription deleted: {event_data['subscription_id']}")

    except Exception as e:
        print(f"[Webhook] Error handling subscription deleted: {e}")


async def _handle_payment_succeeded(event_data: dict, supabase_client: Client):
    """Handle successful payment webhook"""
    try:
        # Log payment success
        supabase_client.table('subscription_history').insert({
            'user_id': None,  # Will be filled from subscription lookup
            'event_type': 'payment_succeeded',
            'stripe_invoice_id': event_data['invoice_id'],
            'amount_paid': event_data['amount_paid'] / 100,  # Convert from cents
            'currency': event_data['currency']
        }).execute()

        print(f"[Webhook] Payment succeeded: {event_data['invoice_id']}")

    except Exception as e:
        print(f"[Webhook] Error handling payment succeeded: {e}")


async def _handle_payment_failed(event_data: dict, supabase_client: Client):
    """Handle failed payment webhook"""
    try:
        # Update subscription status to past_due
        supabase_client.table('user_subscriptions').update({
            'status': 'past_due',
            'updated_at': 'now()'
        }).eq('stripe_customer_id', event_data['customer_id']).execute()

        # Log payment failure
        supabase_client.table('subscription_history').insert({
            'user_id': None,  # Will be filled from subscription lookup
            'event_type': 'payment_failed',
            'stripe_invoice_id': event_data['invoice_id'],
            'amount_paid': 0,
            'currency': event_data['currency']
        }).execute()

        print(f"[Webhook] Payment failed: {event_data['invoice_id']}")

    except Exception as e:
        print(f"[Webhook] Error handling payment failed: {e}")

