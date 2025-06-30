from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from supabase import Client
import stripe
import os
from typing import Dict, Any
import logging

from app.core.database import get_supabase
from app.core.auth import get_current_active_user
from app.core.config import settings

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/create-book-upload-checkout-session")
async def create_book_upload_checkout_session(
    book_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Create a Stripe Checkout Session for book upload payment"""
    try:
        # Verify the user needs to pay (not superadmin, and has uploaded 1+ books)
        if current_user.get('role') == 'superadmin':
            raise HTTPException(status_code=400, detail="Superadmin users don't need to pay")
        
        # Check how many books the user has already uploaded (excluding FAILED ones)
        books_response = supabase_client.table('books').select('id', count='exact').eq('user_id', current_user['id']).neq('status', 'FAILED').execute()
        book_count = books_response.count or 0
        
        if book_count == 0:
            raise HTTPException(status_code=400, detail="First book is free")
        
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': settings.STRIPE_PRICE_ID,  # You'll need to create this in Stripe Dashboard
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{settings.FRONTEND_URL}/upload?payment=success",
            cancel_url=f"{settings.FRONTEND_URL}/upload?payment=cancelled",
            metadata={
                'user_id': current_user['id'],
                'type': 'book_upload',
                'book_count': str(book_count + 1)  # This will be their nth book
            },
            customer_email=current_user['email']
        )
        
        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(status_code=400, detail=f"Payment processing error: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    supabase_client: Client = Depends(get_supabase)
):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Extract metadata
        user_id = session['metadata'].get('user_id')
        payment_type = session['metadata'].get('type')
        
        if payment_type == 'book_upload' and user_id:
            try:
                # Mark user as having completed payment for additional uploads
                # We could store this in a user_payments table or just rely on the fact
                # that they can now upload (since the frontend will handle the flow)
                logger.info(f"Payment completed for user {user_id} for book upload")
                
                # You could store payment record here if needed
                # payment_record = {
                #     'user_id': user_id,
                #     'stripe_session_id': session['id'],
                #     'stripe_payment_intent_id': session.get('payment_intent'),
                #     'amount': session['amount_total'],
                #     'currency': session['currency'],
                #     'status': 'completed',
                #     'type': 'book_upload'
                # }
                # supabase_client.table('payments').insert(payment_record).execute()
                    
            except Exception as e:
                logger.error(f"Error processing payment completion for user {user_id}: {e}")
    
    elif event['type'] == 'payment_intent.payment_failed':
        session = event['data']['object']
        logger.warning(f"Payment failed for session: {session.get('id')}")
        
    else:
        logger.info(f"Unhandled event type: {event['type']}")
    
    return JSONResponse(content={"status": "success"})

@router.get("/check-payment-status/{book_id}")
async def check_payment_status(
    book_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Check the payment status of a book"""
    try:
        # Get book details
        book_response = supabase_client.table('books').select('*').eq('id', book_id).eq('user_id', current_user['id']).single().execute()
        
        if not book_response.data:
            raise HTTPException(status_code=404, detail="Book not found")
        
        book = book_response.data
        
        return {
            "book_id": book_id,
            "status": book['status'],
            "payment_status": book.get('payment_status', 'unpaid'),
            "requires_payment": book['status'] == 'PENDING_PAYMENT'
        }
        
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/user-book-count")
async def get_user_book_count(
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get the count of books uploaded by the current user"""
    try:
        # Count books that are not in FAILED status
        books_response = supabase_client.table('books').select('id', count='exact').eq('user_id', current_user['id']).neq('status', 'FAILED').execute()
        
        book_count = books_response.count or 0
        
        # Superadmin never needs to pay
        if current_user.get('role') == 'superadmin':
            next_book_requires_payment = False
        else:
            next_book_requires_payment = book_count >= 1
        
        return {
            "user_id": current_user['id'],
            "book_count": book_count,
            "next_book_requires_payment": next_book_requires_payment,
            "is_superadmin": current_user.get('role') == 'superadmin'
        }
        
    except Exception as e:
        logger.error(f"Error getting user book count: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")