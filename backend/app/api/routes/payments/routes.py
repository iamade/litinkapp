from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
import stripe
import os
from typing import Dict, Any
import logging

from app.core.database import get_session
from app.core.auth import get_current_active_user
from app.core.config import settings

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/create-book-upload-checkout-session")
async def create_book_upload_checkout_session(
    book_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user)
):
    """Create a Stripe Checkout Session for book upload payment"""
    try:
        # Prevent superadmin from creating a payment session
        user_roles = current_user.get('roles', [])
        if 'superadmin' in user_roles:
            raise HTTPException(status_code=400, detail="Superadmin does not require payment for book uploads.")
        # Verify the book exists and belongs to the user
        book_response = supabase_client.table('books').select('*').eq('id', book_id).eq('user_id', current_user['id']).single().execute()
        
        if not book_response.data:
            raise HTTPException(status_code=404, detail="Book not found or not authorized")
        
        book = book_response.data
        
        # Verify the book is in PENDING_PAYMENT status
        if book['status'] != 'PENDING_PAYMENT':
            raise HTTPException(status_code=400, detail="Book is not pending payment")
        
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': settings.STRIPE_PRICE_ID,  # You'll need to create this in Stripe Dashboard
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{settings.FRONTEND_URL}/dashboard?payment=success&book_id={book_id}",
            cancel_url=f"{settings.FRONTEND_URL}/dashboard?payment=cancelled&book_id={book_id}",
            metadata={
                'book_id': book_id,
                'user_id': current_user['id'],
                'type': 'book_upload'
            },
            customer_email=current_user['email']
        )
        
        # Store the checkout session ID in the book record for reference
        supabase_client.table('books').update({
            'stripe_checkout_session_id': checkout_session.id
        }).eq('id', book_id).execute()
        
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
    session: AsyncSession = Depends(get_session)
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
        book_id = session['metadata'].get('book_id')
        user_id = session['metadata'].get('user_id')
        payment_type = session['metadata'].get('type')
        
        if payment_type == 'book_upload' and book_id:
            try:
                # Update book status from PENDING_PAYMENT to QUEUED
                update_response = supabase_client.table('books').update({
                    'status': 'QUEUED',
                    'stripe_payment_intent_id': session.get('payment_intent'),
                    'stripe_customer_id': session.get('customer'),
                    'payment_status': 'paid'
                }).eq('id', book_id).execute()
                
                if update_response.data:
                    logger.info(f"Successfully updated book {book_id} status to QUEUED after payment")
                    
                    # Trigger background processing
                    # Note: You might want to trigger your existing background processing here
                    # For now, the book will be picked up by any existing polling mechanisms
                    
                else:
                    logger.error(f"Failed to update book {book_id} after payment")
                    
            except Exception as e:
                logger.error(f"Error processing payment completion for book {book_id}: {e}")
    
    elif event['type'] == 'payment_intent.payment_failed':
        session = event['data']['object']
        logger.warning(f"Payment failed for session: {session.get('id')}")
        
    else:
        logger.info(f"Unhandled event type: {event['type']}")
    
    return JSONResponse(content={"status": "success"})

@router.get("/check-payment-status/{book_id}")
async def check_payment_status(
    book_id: str,
    session: AsyncSession = Depends(get_session),
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
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user)
):
    """Get the count of books uploaded by the current user"""
    try:
        # Count books that are not in FAILED status
        books_response = supabase_client.table('books').select('id', count='exact').eq('user_id', current_user['id']).neq('status', 'FAILED').execute()
        
        book_count = books_response.count or 0
        
        return {
            "user_id": current_user['id'],
            "book_count": book_count,
            "next_book_requires_payment": book_count >= 1
        }
        
    except Exception as e:
        logger.error(f"Error getting user book count: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")