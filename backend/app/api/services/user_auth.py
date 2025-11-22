import asyncio
from typing import Optional, Tuple
import jwt
import uuid
from fastapi import HTTPException, status
from supabase import Client


from app.auth.models import User
from app.auth.schema import AccountStatusSchema, UserCreateSchema
from app.auth.utils import (
    generate_password_hash, generate_display_name, verify_password, create_activation_token, generate_otp
)
from datetime import datetime, timedelta, timezone
# from app.core.services.account_lockout import send_account_lockout_email
from app.core.services.activation_email import send_activation_email
from app.core.config import settings
from app.core.logging import get_logger
from app.core.services.login_otp import send_login_otp_email
from app.core.database import get_supabase

logger = get_logger()

class UserAuthService:
    """
    Supabase-backed auth service. Works with 'profiles' table and optional supporting tables.
    """

    def __init__(self, supabase: Optional[Client] = None) -> None:
        self.supabase: Client = supabase or get_supabase()
        self.table = "profiles"
        
    # ---------------------------
    # Query helpers
    # ---------------------------
    async def get_user_by_email(
        self, email: str, include_inactive: bool = False
    ) -> Optional[dict]:
        try:
            query = self.supabase.table(self.table).select("*").eq("email", email)
            if not include_inactive:
                query = query.eq("is_active", True)
            resp = query.single().execute()
            return resp.data if resp.data else None
        except Exception as e:
            # Suppress PGRST116 (0 rows) as it just means user not found
            if hasattr(e, 'code') and e.code == 'PGRST116':
                return None
            logger.error(f"get_user_by_email failed for {email}: {e}")
            return None
        
    
    async def get_user_by_id(
        self, user_id: uuid.UUID | str, include_inactive: bool = False
    ) -> Optional[dict]:
        try:
            uid = str(user_id)
            query = self.supabase.table(self.table).select("*").eq("id", uid)
            if not include_inactive:
                query = query.eq("is_active", True)
            resp = query.single().execute()
            return resp.data if resp.data else None
        except Exception as e:
            logger.error(f"get_user_by_id failed for {user_id}: {e}")
            return None
        
    async def check_user_email_exists(self, email: str) -> bool:
        return bool(await self.get_user_by_email(email, include_inactive=True))

    # ---------------------------
    # Password verification
    # ---------------------------
    async def verify_user_password(self, plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)
    
    # ---------------------------
    # User state management
    # ---------------------------
    async def _update_user(self, user_id: str, updates: dict) -> dict:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        resp = self.supabase.table(self.table).update(updates).eq("id", user_id).execute()
        if resp.error or not resp.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": "error", "message": f"Update failed: {getattr(resp.error,'message', 'unknown')}"},
            )
        return resp.data[0]
    
    async def reset_user_state(
        self,
        user_id: str,
        *,
        clear_otp: bool = True,
        log_action: bool = True,
    ) -> dict:
        # Fetch current to compute transition logs
        user = await self.get_user_by_id(user_id, include_inactive=True)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"status": "error", "message": "User not found"},
            )

        previous_status = user.get("account_status")
        updates = {
            "failed_login_attempts": 0,
            "last_failed_login": None,
        }
        if clear_otp:
            updates["otp"] = ""
            updates["otp_expiry_time"] = None
        if user.get("account_status") == AccountStatusSchema.LOCKED:
            updates["account_status"] = AccountStatusSchema.ACTIVE

        updated = await self._update_user(user["id"], updates)

        if log_action and previous_status != updated.get("account_status"):
            logger.info(
                f"User {updated.get('email')} state reset: {previous_status} -> {updated.get('account_status')}"
            )
        return updated

    async def validate_user_status(self, user: dict) -> None:
        if not user.get("is_active", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Your account is not activated",
                    "action": "Please activate your account first",
                },
            )

        status_val = user.get("account_status")
        if status_val == AccountStatusSchema.LOCKED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Your account is locked",
                    "action": "Please contact support",
                },
            )
        if status_val == AccountStatusSchema.INACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Your account is inactive",
                    "action": "Please contact support",
                },
            )

    # ---------------------------
    # OTP
    # ---------------------------
    async def generate_and_save_otp(self, user_id: str, email: str) -> Tuple[bool, str]:
        try:
            otp = generate_otp()
            expiry = (datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRATION_MINUTES)).isoformat()

            await self._update_user(user_id, {"otp": otp, "otp_expiry_time": expiry})

            # Retry send up to 3 times with backoff
            for attempt in range(3):
                try:
                    await send_login_otp_email(email, otp)
                    logger.info(f"OTP sent to {email} successfully")
                    return True, otp
                except Exception as e:
                    logger.error(f"Failed to send OTP email (attempt {attempt + 1}): {e}")
                    if attempt == 2:
                        # Clear OTP if email fails after retries
                        await self._update_user(user_id, {"otp": "", "otp_expiry_time": None})
                        return False, ""
                    await asyncio.sleep(2**attempt)

            return False, ""
        except Exception as e:
            logger.error(f"Failed to generate and save OTP: {e}")
            try:
                await self._update_user(user_id, {"otp": "", "otp_expiry_time": None})
            except Exception:
                pass
            return False, ""

    async def verify_login_otp(self, email: str, otp: str) -> dict:
        try:
            user = await self.get_user_by_email(email, include_inactive=True)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"status": "error", "message": "Invalid credentials"},
                )

            await self.validate_user_status(user)
            await self.check_user_lockout(user)

            if not user.get("otp") or user.get("otp") != otp:
                await self.increment_failed_login_attempts(user["id"], user_email=user.get("email"))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "error",
                        "message": "Invalid OTP",
                        "action": "Please check your OTP and try again",
                    },
                )

            expiry = user.get("otp_expiry_time")
            if not expiry or datetime.fromisoformat(expiry) < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "error",
                        "message": "OTP has expired",
                        "action": "Please request a new OTP",
                    },
                )

            updated = await self.reset_user_state(user["id"], clear_otp=False)
            return updated
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during OTP verification: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"status": "error", "message": "Failed to verify OTP", "action": "Please try again later"},
            )

    # ---------------------------
    # Lockout
    # ---------------------------
    async def check_user_lockout(self, user: dict) -> None:
        if user.get("account_status") != AccountStatusSchema.LOCKED:
            return

        last_failed = user.get("last_failed_login")
        if not last_failed:
            return

        lockout_time = datetime.fromisoformat(last_failed) + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
        now = datetime.now(timezone.utc)

        if now >= lockout_time:
            await self.reset_user_state(user["id"], clear_otp=False)
            logger.info(f"Lockout period ended for user {user.get('email')}")
            return

        remaining_minutes = int((lockout_time - now).total_seconds() / 60)
        logger.warning(f"Attempted login to locked account: {user.get('email')}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": "Your account is temporarily locked",
                "action": f"Please try again after {remaining_minutes} minutes",
                "lockout_remaining_minutes": remaining_minutes,
            },
        )

    async def increment_failed_login_attempts(self, user_id: str, user_email: Optional[str] = None) -> dict:
        user = await self.get_user_by_id(user_id, include_inactive=True)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        attempts = int(user.get("failed_login_attempts", 0)) + 1
        updates = {
            "failed_login_attempts": attempts,
            "last_failed_login": datetime.now(timezone.utc).isoformat(),
        }

        if attempts >= settings.LOGIN_ATTEMPTS:
            updates["account_status"] = AccountStatusSchema.LOCKED

        updated = await self._update_user(user_id, updates)

        if updates.get("account_status") == AccountStatusSchema.LOCKED and user_email:
            try:
                await self._send_account_lockout_email(user_email, updated.get("last_failed_login"))
                logger.info(f"Account lockout notification email sent to {user_email}")
            except Exception as e:
                logger.error(f"Failed to send account lockout email to {user_email}: {e}")

            logger.warning(
                f"User {user_email} has been locked out due to too many failed login attempts"
            )

        return updated

    # ---------------------------
    # Registration and activation
    # ---------------------------
    async def create_user(self, user_data: UserCreateSchema) -> dict:
        # data = user_data.model_dump(
        #     exclude={"confirm_password", "display_name", "is_active", "account_status"}
        # )
        # password = data.pop("password")
        
        password = user_data.password
        
        # Step 1: Create user via admin API (no email sent by Supabase)
        try:
            auth_response = self.supabase.auth.admin.create_user({
                "email": user_data.email,
                "password": password,  # Plain password - Supabase hashes it
                "email_confirm": False,  # Disable Supabase email verification
                "user_metadata": {
                    "first_name": user_data.first_name,
                    "last_name": user_data.last_name
                }
            })
        except Exception as e:
            logger.error(f"Supabase admin create_user failed: {type(e).__name__}: {e}")
            if hasattr(e, 'code'):
                logger.error(f"Error code: {e.code}")
            if hasattr(e, 'details'):
                logger.error(f"Error details: {e.details}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": "error", "message": "Registration failed"}
            )
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": "error", "message": "Could not create user"}
            )
        
        user_id = auth_response.user.id  # UUID from auth.users


        profile = {
            "id": user_id,
            "email": user_data.email,
            "first_name": user_data.first_name,
            "middle_name": user_data.middle_name,
            "last_name": user_data.last_name,
            "display_name": generate_display_name(),
            "is_active": False,
            "account_status": AccountStatusSchema.PENDING,
            "security_question": user_data.security_question.value,
            "security_answer": generate_password_hash(user_data.security_answer.lower().strip()),
            "roles": [r.value if hasattr(r, "value") else r for r in user_data.roles],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
    
        }

        resp = self.supabase.table(self.table).upsert(profile).execute()
        if not resp.data:
            # Cleanup: delete auth user if profile creation fails
            try:
                self.supabase.auth.admin.delete_user(user_id)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": "error", "message": f"Registration failed: {getattr(resp.error,'message','unknown')}"},
            )

        new_user = resp.data[0]
        activation_token = create_activation_token(uuid.UUID(new_user["id"]))

        try:
            await send_activation_email(new_user["email"], activation_token)
            logger.info(f"Activation email sent to {new_user['email']}")
        except Exception as e:
            logger.error(f"Failed to send activation email to {new_user['email']}: {e}")
            # You may choose to delete the inserted user here if email is mandatory.
            raise

        return new_user

    async def activate_user_account(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") != "activation":
                raise ValueError("Invalid token type")

            user_id = str(uuid.UUID(payload["id"]))
            user = await self.get_user_by_id(user_id, include_inactive=True)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"status": "error", "message": "User not found"},
                )
            if user.get("is_active", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"status": "error", "message": "User already activated"},
                )
                
            # IMPORTANT: Update Supabase Auth user (mark email as verified)
            try:
                self.supabase.auth.admin.update_user_by_id(
                    user_id,
                    {"email_confirm": True}
                )
                logger.info(f"Email verified in Supabase Auth for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to verify email in Supabase Auth: {e}")
                # Continue with profile activation even if auth update fails
        

            updated = await self.reset_user_state(user_id, clear_otp=True, log_action=True)
            updated = await self._update_user(
                user_id,
                {"is_active": True, "account_status": AccountStatusSchema.ACTIVE},
            )
            logger.info(f"User {updated.get('email')} activated successfully")
            return updated

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": "error", "message": "Activation token expired"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": "error", "message": "Invalid activation token"},
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to activate user account: {e}")
            raise

    # ---------------------------
    # Password reset
    # ---------------------------
    async def reset_password(self, token: str, new_password: str) -> None:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") != "password_reset":
                raise ValueError("Invalid reset token")

            user_id = str(uuid.UUID(payload["id"]))
            user = await self.get_user_by_id(user_id, include_inactive=True)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"status": "error", "message": "User not found"},
                )

            # IMPORTANT: Update password in Supabase Auth (not profiles!)
            try:
                self.supabase.auth.admin.update_user_by_id(
                    user_id,
                    {"password": new_password}  # Supabase hashes it securely
                )
                logger.info(f"Password updated in Supabase Auth for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to update password in Supabase Auth: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"status": "error", "message": "Failed to reset password"}
                )

            # Reset custom lockout state
            await self.reset_user_state(user_id, clear_otp=True, log_action=True)
            logger.info(f"Password reset successful for user {user.get('email')}")

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": "error", "message": "Password reset token expired"}
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": "error", "message": "Invalid password reset token"}
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to reset password: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"status": "error", "message": "Failed to reset password"}
            )

    

    async def _send_account_lockout_email(self, email: str, locked_at_iso: Optional[str]) -> None:
        """
        Placeholder. Replace with a concrete email template/service.
        """
        logger.warning(f"[DEV] Account lockout email to {email} at {locked_at_iso}")

user_auth_service = UserAuthService()