import stripe
from typing import Dict, Any, Optional, List
import json
from datetime import datetime
from app.core.config import settings


class StripeService:
    """Stripe service for handling subscription payments"""

    def __init__(self):
        """Initialize Stripe with test keys"""
        if not settings.STRIPE_SECRET_KEY:
            raise ValueError("STRIPE_SECRET_KEY is required")

        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET

        # Product and price IDs for tiers
        self.products = {
            'free': {
                'name': 'Free',
                'price_id': getattr(settings, 'STRIPE_FREE_PRICE_ID', None)
            },
            'basic': {
                'name': 'Basic',
                'price_id': getattr(settings, 'STRIPE_BASIC_PRICE_ID', None)
            },
            'pro': {
                'name': 'Pro',
                'price_id': getattr(settings, 'STRIPE_PRO_PRICE_ID', None)
            }
        }

    async def create_or_get_customer(self, user_id: str, email: str, name: Optional[str] = None) -> str:
        """Create or retrieve Stripe customer"""
        try:
            # Check if customer already exists
            customers = stripe.Customer.list(email=email, limit=1)
            if customers.data:
                return customers.data[0].id

            # Create new customer
            customer_data = {
                'email': email,
                'metadata': {'user_id': user_id}
            }
            if name:
                customer_data['name'] = name

            customer = stripe.Customer.create(**customer_data)
            print(f"[StripeService] Created customer {customer.id} for user {user_id}")
            return customer.id

        except Exception as e:
            print(f"[StripeService] Error creating customer: {e}")
            raise

    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Create Stripe checkout session"""
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={'user_id': user_id},
                allow_promotion_codes=True
            )

            print(f"[StripeService] Created checkout session {session.id} for user {user_id}")
            return {
                'session_id': session.id,
                'url': session.url
            }

        except Exception as e:
            print(f"[StripeService] Error creating checkout session: {e}")
            raise

    async def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a subscription"""
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )

            print(f"[StripeService] Cancelled subscription {subscription_id}")
            return {
                'subscription_id': subscription.id,
                'status': subscription.status,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'current_period_end': subscription.current_period_end
            }

        except Exception as e:
            print(f"[StripeService] Error cancelling subscription: {e}")
            raise

    async def reactivate_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Reactivate a cancelled subscription"""
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=False
            )

            print(f"[StripeService] Reactivated subscription {subscription_id}")
            return {
                'subscription_id': subscription.id,
                'status': subscription.status,
                'cancel_at_period_end': subscription.cancel_at_period_end
            }

        except Exception as e:
            print(f"[StripeService] Error reactivating subscription: {e}")
            raise

    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription details"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'price_id': subscription.items.data[0].price.id if subscription.items.data else None
            }

        except Exception as e:
            print(f"[StripeService] Error getting subscription: {e}")
            raise

    async def create_price(self, product_id: str, amount: int, currency: str = 'usd', interval: str = 'month') -> str:
        """Create a price object for a product"""
        try:
            price = stripe.Price.create(
                product=product_id,
                unit_amount=amount,  # Amount in cents
                currency=currency,
                recurring={'interval': interval}
            )

            print(f"[StripeService] Created price {price.id} for product {product_id}")
            return price.id

        except Exception as e:
            print(f"[StripeService] Error creating price: {e}")
            raise

    async def create_product(self, name: str, description: Optional[str] = None) -> str:
        """Create a product"""
        try:
            product_data = {'name': name}
            if description:
                product_data['description'] = description

            product = stripe.Product.create(**product_data)

            print(f"[StripeService] Created product {product.id}: {name}")
            return product.id

        except Exception as e:
            print(f"[StripeService] Error creating product: {e}")
            raise

    async def handle_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        try:
            if not self.webhook_secret:
                raise ValueError("STRIPE_WEBHOOK_SECRET is required for webhook handling")

            event = stripe.Webhook.construct_event(payload, signature, self.webhook_secret)

            print(f"[StripeService] Received webhook event: {event.type}")

            # Handle different event types
            if event.type == 'customer.subscription.created':
                return await self._handle_subscription_created(event.data.object)
            elif event.type == 'customer.subscription.updated':
                return await self._handle_subscription_updated(event.data.object)
            elif event.type == 'customer.subscription.deleted':
                return await self._handle_subscription_deleted(event.data.object)
            elif event.type == 'invoice.payment_succeeded':
                return await self._handle_payment_succeeded(event.data.object)
            elif event.type == 'invoice.payment_failed':
                return await self._handle_payment_failed(event.data.object)
            else:
                print(f"[StripeService] Unhandled event type: {event.type}")
                return {'event_type': event.type, 'handled': False}

        except Exception as e:
            print(f"[StripeService] Error handling webhook: {e}")
            raise

    async def _handle_subscription_created(self, subscription: Any) -> Dict[str, Any]:
        """Handle subscription created event"""
        return {
            'event_type': 'subscription.created',
            'subscription_id': subscription.id,
            'customer_id': subscription.customer,
            'status': subscription.status,
            'price_id': subscription.items.data[0].price.id if subscription.items.data else None,
            'current_period_start': subscription.current_period_start,
            'current_period_end': subscription.current_period_end
        }

    async def _handle_subscription_updated(self, subscription: Any) -> Dict[str, Any]:
        """Handle subscription updated event"""
        return {
            'event_type': 'subscription.updated',
            'subscription_id': subscription.id,
            'customer_id': subscription.customer,
            'status': subscription.status,
            'price_id': subscription.items.data[0].price.id if subscription.items.data else None,
            'current_period_start': subscription.current_period_start,
            'current_period_end': subscription.current_period_end,
            'cancel_at_period_end': subscription.cancel_at_period_end
        }

    async def _handle_subscription_deleted(self, subscription: Any) -> Dict[str, Any]:
        """Handle subscription deleted event"""
        return {
            'event_type': 'subscription.deleted',
            'subscription_id': subscription.id,
            'customer_id': subscription.customer,
            'status': subscription.status
        }

    async def _handle_payment_succeeded(self, invoice: Any) -> Dict[str, Any]:
        """Handle successful payment"""
        return {
            'event_type': 'payment.succeeded',
            'invoice_id': invoice.id,
            'subscription_id': invoice.subscription,
            'customer_id': invoice.customer,
            'amount_paid': invoice.amount_paid,
            'currency': invoice.currency
        }

    async def _handle_payment_failed(self, invoice: Any) -> Dict[str, Any]:
        """Handle failed payment"""
        return {
            'event_type': 'payment.failed',
            'invoice_id': invoice.id,
            'subscription_id': invoice.subscription,
            'customer_id': invoice.customer,
            'amount_due': invoice.amount_due,
            'currency': invoice.currency
        }

    async def get_customer_payment_methods(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get customer's payment methods"""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type='card'
            )

            return [{
                'id': pm.id,
                'type': pm.type,
                'card': {
                    'brand': pm.card.brand,
                    'last4': pm.card.last4,
                    'exp_month': pm.card.exp_month,
                    'exp_year': pm.card.exp_year
                } if pm.card else None
            } for pm in payment_methods.data]

        except Exception as e:
            print(f"[StripeService] Error getting payment methods: {e}")
            raise

    async def update_subscription_price(self, subscription_id: str, new_price_id: str) -> Dict[str, Any]:
        """Update subscription to a new price"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            current_item = subscription.items.data[0]

            updated_subscription = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': current_item.id,
                    'price': new_price_id,
                }],
                proration_behavior='create_prorations'
            )

            print(f"[StripeService] Updated subscription {subscription_id} to price {new_price_id}")
            return {
                'subscription_id': updated_subscription.id,
                'status': updated_subscription.status,
                'price_id': updated_subscription.items.data[0].price.id
            }

        except Exception as e:
            print(f"[StripeService] Error updating subscription price: {e}")
            raise

    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer details from Stripe"""
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return {
                'id': customer.id,
                'email': customer.email,
                'name': customer.name,
                'metadata': customer.metadata
            }
        except Exception as e:
            print(f"[StripeService] Error getting customer: {e}")
            raise


# Global instance
stripe_service = StripeService()