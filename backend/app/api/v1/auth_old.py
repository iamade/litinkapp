# from datetime import timedelta, datetime, timezone
# from fastapi import APIRouter, Depends, HTTPException, status, Body
# from app.auth.schema import PasswordResetRequestSchema
# from supabase import Client
# from gotrue.errors import AuthApiError
# from postgrest.exceptions import APIError
# from pydantic import BaseModel

# from app.core.auth import (
#     verify_password,
#     get_password_hash,
#     create_access_token,
#     get_current_user
# )
# from app.core.config import settings
# from app.core.database import get_supabase
# from app.schemas.auth import Token, UserLogin, UserRegister
# from app.schemas.user import User as UserSchema, UserCreate

# router = APIRouter()





# @router.post("/register", response_model=UserSchema, status_code=201)
# async def register(
#     user_data: UserCreate,
#     supabase_client: Client = Depends(get_supabase)
# ):
#     """Register a new user with email verification required"""
#     try:
#         # Sign up user with Supabase Auth (will send verification email automatically)
#         response = supabase_client.auth.sign_up({
#             "email": user_data.email,
#             "password": user_data.password,
#             "options": {
#                 "data": {
#                     "display_name": user_data.display_name
#                 },
#                 "email_redirect_to": f"{settings.FRONTEND_URL}/auth/verify-email"
#             }
#         })
#     except AuthApiError as e:
#         error_message = str(e)
#         if "already registered" in error_message.lower():
#             raise HTTPException(status_code=400, detail="Email already registered")
#         raise HTTPException(status_code=400, detail=error_message)

#     if response.user is None:
#         raise HTTPException(status_code=400, detail="Could not create user")

#     # Manually create the user profile after successful auth sign-up
#     profile_data = {
#         "id": response.user.id,
#         "email": user_data.email,
#         "display_name": user_data.display_name or user_data.email.split('@')[0],
#         "roles": user_data.roles,
#         "email_verified": False,
#         "verification_token_sent_at": datetime.now(timezone.utc).isoformat()
#     }

#     try:
#         profile_response = supabase_client.table('profiles').insert(profile_data).execute()

#         # Add missing fields to align with the User response model
#         new_profile = profile_response.data[0]
#         new_profile['is_active'] = True
#         new_profile['is_verified'] = False

#         return new_profile
#     except APIError as e:
#         import traceback
#         import logging
#         logger = logging.getLogger(__name__)

#         logger.error(f"Profile creation failed: {e}")
#         logger.error(f"Profile data attempted: {profile_data}")
#         logger.error(f"Traceback: {traceback.format_exc()}")

#         # Try to delete the auth user if profile creation fails
#         try:
#             supabase_client.auth.admin.delete_user(response.user.id)
#         except Exception as cleanup_error:
#             logger.error(f"Failed to cleanup auth user: {cleanup_error}")

#         raise HTTPException(status_code=400, detail="Database error saving new user. Please try again.")
#     except Exception as e:
#         import traceback
#         import logging
#         logger = logging.getLogger(__name__)

#         logger.error(f"Unexpected error during profile creation: {e}")
#         logger.error(f"Profile data attempted: {profile_data}")
#         logger.error(f"Traceback: {traceback.format_exc()}")

#         # Try to delete the auth user if profile creation fails
#         try:
#             supabase_client.auth.admin.delete_user(response.user.id)
#         except Exception as cleanup_error:
#             logger.error(f"Failed to cleanup auth user: {cleanup_error}")

#         raise HTTPException(status_code=400, detail="Registration failed. Please try again.")


# @router.post("/login", response_model=Token)
# async def login(
#     user_data: UserLogin,
#     supabase: Client = Depends(get_supabase)
# ):
#     """Login user and return access token (requires verified email)"""
#     try:
#         # Authenticate with Supabase
#         auth_response = supabase.auth.sign_in_with_password({
#             "email": user_data.email,
#             "password": user_data.password
#         })

#         if not auth_response.user:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Incorrect email or password",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )

#         # Check if email is verified
#         profile_response = supabase.table('profiles').select('email_verified').eq('id', auth_response.user.id).maybeSingle().execute()

#         if profile_response.data and not profile_response.data.get('email_verified', False):
#             # Sign out the user since they're not verified
#             supabase.auth.sign_out()
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Email not verified. Please check your email for the verification link.",
#             )

#         # Create access token
#         access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
#         access_token = create_access_token(
#             data={"sub": auth_response.user.id}, expires_delta=access_token_expires
#         )

#         return {
#             "access_token": access_token,
#             "token_type": "bearer",
#             "refresh_token": auth_response.session.refresh_token,
#         }

#     except Exception as e:
#         if isinstance(e, HTTPException):
#             raise e
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Authentication failed",
#             headers={"WWW-Authenticate": "Bearer"},
#         )


# @router.post("/request-password-reset")
# async def request_password_reset(
#     request: PasswordResetRequestSchema,
#     supabase: Client = Depends(get_supabase)
# ):
#     """Request a password reset email"""
#     try:
#         response = supabase.auth.reset_password_email(request.email)
#         return {"message": "Password reset email sent successfully"}
#     except AuthApiError as e:
#         # Don't reveal if email exists or not for security
#         return {"message": "If the email exists, a password reset link has been sent"}


# @router.post("/confirm-password-reset")
# async def confirm_password_reset(
#     request: PasswordResetConfirm,
#     supabase: Client = Depends(get_supabase)
# ):
#     """Confirm password reset with token"""
#     try:
#         response = supabase.auth.verify_otp({
#             "email": request.email,
#             "token": request.token,
#             "type": "recovery"
#         })
        
#         # Update password
#         supabase.auth.update_user({
#             "password": request.new_password
#         })
        
#         return {"message": "Password reset successfully"}
#     except AuthApiError as e:
#         raise HTTPException(status_code=400, detail=f"Password reset failed: {e}")


# @router.post("/resend-verification")
# async def resend_verification_email(
#     request: EmailVerificationRequest,
#     supabase: Client = Depends(get_supabase)
# ):
#     """Resend email verification with rate limiting"""
#     try:
#         # Check if user exists
#         user_response = supabase.table('profiles').select('id, email_verified, verification_token_sent_at').eq('email', request.email).maybeSingle().execute()

#         if not user_response.data:
#             # Don't reveal if email exists or not for security
#             return {"message": "If the email exists and is unverified, a verification email has been sent"}

#         user = user_response.data

#         # Check if already verified
#         if user.get('email_verified'):
#             return {"message": "Email is already verified"}

#         # Check rate limiting using database function
#         can_send_response = supabase.rpc('can_request_verification_email', {'user_id': user['id']}).execute()

#         if not can_send_response.data:
#             raise HTTPException(status_code=429, detail="Please wait 5 minutes before requesting another verification email")

#         # Resend verification email via Supabase Auth
#         response = supabase.auth.resend(
#             type='signup',
#             email=request.email,
#             options={
#                 'email_redirect_to': f"{settings.FRONTEND_URL}/auth/verify-email"
#             }
#         )

#         # Update the verification token sent timestamp
#         supabase.rpc('update_verification_token_sent', {'user_id': user['id']}).execute()

#         return {"message": "Verification email sent successfully"}
#     except AuthApiError as e:
#         # Don't reveal if email exists or not for security
#         return {"message": "If the email exists and is unverified, a verification email has been sent"}
#     except HTTPException:
#         raise
#     except Exception as e:
#         import logging
#         logger = logging.getLogger(__name__)
#         logger.error(f"Error resending verification email: {e}")
#         raise HTTPException(status_code=500, detail="Failed to resend verification email")


# @router.post("/verify-email")
# async def verify_email(
#     token_hash: str = Body(..., embed=True),
#     supabase: Client = Depends(get_supabase)
# ):
#     """Verify email using token from email link"""
#     try:
#         # Verify the token with Supabase Auth
#         response = supabase.auth.verify_otp({
#             'token_hash': token_hash,
#             'type': 'signup'
#         })

#         if not response.user:
#             raise HTTPException(status_code=400, detail="Invalid or expired verification token")

#         # Update profile to mark email as verified
#         supabase.table('profiles').update({
#             'email_verified': True
#         }).eq('id', response.user.id).execute()

#         return {
#             "message": "Email verified successfully",
#             "user_id": response.user.id
#         }

#     except AuthApiError as e:
#         raise HTTPException(status_code=400, detail=f"Email verification failed: {str(e)}")
#     except Exception as e:
#         import logging
#         logger = logging.getLogger(__name__)
#         logger.error(f"Email verification error: {e}")
#         raise HTTPException(status_code=500, detail="Email verification failed")


# @router.get("/verification-status")
# async def check_verification_status(
#     current_user: dict = Depends(get_current_user)
# ):
#     """Check if current user's email is verified"""
#     return {
#         "email": current_user.get('email'),
#         "email_verified": current_user.get('email_verified', False),
#         "email_verified_at": current_user.get('email_verified_at')
#     }


# @router.get("/me", response_model=UserSchema)
# async def get_current_user_info(
#     current_user: dict = Depends(get_current_user)
# ):
#     """Get current user information"""
#     return current_user


# @router.post("/refresh", response_model=Token)
# async def refresh_token(
#     refresh_token: str = Body(..., embed=True),
#     supabase: Client = Depends(get_supabase)
# ):
#     """Refresh access token using a refresh token"""
#     try:
#         response = supabase.auth.refresh_session(refresh_token)
#         if not response.session:
#             raise HTTPException(status_code=401, detail="Invalid refresh token")

#         access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
#         access_token = create_access_token(
#             data={"sub": response.user.id}, expires_delta=access_token_expires
#         )
        
#         return {
#             "access_token": access_token,
#             "token_type": "bearer",
#             "refresh_token": response.session.refresh_token,
#         }
#     except AuthApiError as e:
#         raise HTTPException(status_code=401, detail=f"Could not refresh token: {e}")