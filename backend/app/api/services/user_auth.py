import asyncio
from typing import Optional, Tuple
import jwt
import uuid
from fastapi import HTTPException, status

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
# from app.core.services.login_otp import send_login_otp_email
from app.core.database import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

logger = get_logger()

class UserAuthService:
    
    # def __init__(self, supabase: Optional[Client] = None) -> None:
    #     self.supabase: Client = supabase or get_supabase()
    #     self.table = "profiles"
        
    # ---------------------------
    # Query helpers
    # ---------------------------
    async def get_user_by_email(
        self, email: str, session: AsyncSession, include_inactive: bool = False
    ) -> User | None:
        statement = select(User).where(User.email == email)
        
        if not include_inactive:
            statement = statement.where(User.is_active)
        result = await session.exec(statement)
        user = result.first()
        return user
        
    
    async def get_user_by_id(
        self, id: uuid.UUID, session: AsyncSession, include_inactive: bool = False
    ) -> User | None:
        statement = select(User).where(User.id == id)
        
        if not include_inactive:
             statement = statement.where(User.is_active)
        result = await session.exec(statement)
        user = result.first()
        return user
        
    async def check_user_email_exists(self, email: str, session: AsyncSession) -> bool:
        user = await self.get_user_by_email(email, session)
        return bool(user)
    # ---------------------------
    # Password verification
    # ---------------------------
    async def verify_user_password(self, plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)
    
    # ---------------------------
    # User state management
    # ---------------------------
    # async def _update_user(self, user_id: str, updates: dict) -> dict:
    #     updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    #     resp = self.supabase.table(self.table).update(updates).eq("id", user_id).execute()
    #     if resp.error or not resp.data:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail={"status": "error", "message": f"Update failed: {getattr(resp.error,'message', 'unknown')}"},
    #         )
    #     return resp.data[0]
    
    # async def reset_user_state(
    #     self,
    #     user: User, 
    #     session: AsyncSession,
    #     *,
    #     # clear_otp: bool = True,
    #     log_action: bool = True,
    # ) -> None:
    #     # Fetch current to compute transition logs
    #     user = await self.get_user_by_id(user_id, include_inactive=True)
    #     if not user:
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail={"status": "error", "message": "User not found"},
    #         )

    #     previous_status = user.get("account_status")
    #     updates = {
    #         "failed_login_attempts": 0,
    #         "last_failed_login": None,
    #     }
    #     if clear_otp:
    #         updates["otp"] = ""
    #         updates["otp_expiry_time"] = None
    #     if user.get("account_status") == AccountStatusSchema.LOCKED:
    #         updates["account_status"] = AccountStatusSchema.ACTIVE

    #     updated = await self._update_user(user["id"], updates)

    #     if log_action and previous_status != updated.get("account_status"):
    #         logger.info(
    #             f"User {updated.get('email')} state reset: {previous_status} -> {updated.get('account_status')}"
    #         )
    #     return updated
    
    async def reset_user_state(
        self, user: User, session: AsyncSession, *, log_action: bool = True, #clear_otp: bool = True,
    ) -> None:
        previous_status = user.account_status
        
        user.failed_login_attempts = 0
        user.last_failed_login = None
        
        # if clear_otp:
        #     user.otp = ""
        #     user.otp_expiry_time = None
            
        if user.account_status == AccountStatusSchema.LOCKED:
            user.account_status = AccountStatusSchema.ACTIVE
            
        
        await session.commit()
        
        await session.refresh(user)
        
        if log_action and previous_status != user.account_status:
            logger.info(
                f"User {user.email} state reset: {previous_status} -> {user.account_status}"
            )
            
    async def validate_user_status(self, user: User)-> None:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Your account is not activated",
                    "action":"Please activate your account first"
                }
            )
        
        if user.account_status == AccountStatusSchema.LOCKED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Your account is locked",
                    "action":"Please contact support",
                }
            )
            
        if user.account_status == AccountStatusSchema.INACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Your account is inactive",
                    "action":"Please contact your account",
                }
            )
            
   

    # ---------------------------
    # OTP
    # ---------------------------
    # async def generate_and_save_otp(self, user: User, session: AsyncSession,) -> Tuple[bool, str]:
        # try:
        #     otp = generate_otp()
        #     user.otp = otp
            
        #     user.otp_expiry_time = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRATION_MINUTES)
            
        #     await session.commit()
        #     await session.refresh(user)
            
        #     for attempt in range(3):
        #         try:
        #             await send_login_otp_email(user.email, otp)
        #             logger.info(f"OTP sent to {user.email} successfully")
        #             return True, otp
        #         except Exception as e:
        #             logger.error(
        #                 f"Failed to send OTP email (attempt {attempt + 1}): {e}"
        #             )
        #             if attempt == 2:
        #                 user.otp = ""
        #                 user.otp_expiry_time = None
        #                 await session.commit()
        #                 await session.refresh(user)
        #                 return False, ""
        #             await asyncio.sleep(2**attempt)
        #     return False, ""
                    
            
        # except Exception as e:
        #     logger.error(f"Failed to generate and save OTP: {e}")
            
        #     user.otp = ""
        #     user.otp_expiry_time = None
        #     await session.commit()
        #     await session.refresh(user)
        #     return False, ""
        
    
    

    # ---------------------------
    # Lockout
    # ---------------------------
    async def check_user_lockout(self, user: User, session: AsyncSession,) -> None:
        if user.account_status != AccountStatusSchema.LOCKED:
            return
        
        if user.last_failed_login is None:
            return
        
        lockout_time = user.last_failed_login + timedelta(
            minutes=settings.LOCKOUT_DURATION_MINUTES
        )
        
        current_time = datetime.now(timezone.utc)
        
        if current_time >= lockout_time:
            await self.reset_user_state(user, session)
            logger.info(f"Lockout period ended for user {user.email}")
            return
        
        remaining_minutes = int((lockout_time - current_time).total_seconds() / 60)
        
        logger.warning(f"Attempted login to locked account: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": "Your account is temporarily locked",
                "action": f"Please try again after {remaining_minutes} minutes",
                "lockout_remaining_minutes": remaining_minutes,
            },
        )

#   async def increment_failed_login_attempts(
#         self,
#         user: User,
#         session: AsyncSession,
#     ) -> None:
#         user.failed_login_attempts += 1

#         current_time = datetime.now(timezone.utc)
#         user.last_failed_login = current_time

#         if user.failed_login_attempts >= settings.LOGIN_ATTEMPTS:
#             user.account_status = AccountStatusSchema.LOCKED

#             try:
#                 await send_account_lockout_email(user.email, current_time)
#                 logger.info(f"Account lockout notification email sent to {user.email}")

#             except Exception as e:
#                 logger.error(
#                     f"Failed to send account lockout email to {user.email}: {e}"
#                 )
#             logger.warning(
#                 f"User {user.email} has been locked out due to too many failed login attempts"
#             )
#         await session.commit()

#         await session.refresh(user)

    # ---------------------------
    # Registration and activation
    # ---------------------------
    async def create_user(
        self,
        user_data: UserCreateSchema,
        session: AsyncSession,
    )-> User:
        user_data_dict = user_data.model_dump(
            exclude={
                "confirm_password",
                "username",
                "is_active",
                "account_status"
            }
        )
        
        password = user_data_dict.pop("password")
        new_user = User(
            display_name=generate_display_name(),
            hashed_password=generate_password_hash(password),
            is_active=False,
            account_status=AccountStatusSchema.PENDING,
            **user_data_dict,
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        activation_token = create_activation_token(new_user.id)
        try:
            await send_activation_email(new_user.email, activation_token)
            logger.info(f"Activation email sent to {new_user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send activation email to {new_user.email}: {e} ")
            raise
        return new_user
    
    
    async def activate_user_account(
        self, token: str, session: AsyncSession,
    )-> User:
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )

            if payload.get("type") != "activation":
                raise ValueError("Invalid token type")
            
            user_id = uuid.UUID(payload["id"])
            
            user = await self.get_user_by_id(user_id, session, include_inactive=True)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "status":"error",
                        "message":"User not found",
                    }
                )
            if user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status":"error",
                        "message":"User already activated",
                    }
                )
                
            await self.reset_user_state(user, session, log_action=True)
            
            user.is_active = True
            user.account_status = AccountStatusSchema.ACTIVE
            
            await session.commit()
            await session.refresh(user)
            
            return user
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status":"error",
                    "message":"Activation token expired",
                },
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status":"error",
                    "message":"Invalid activation token",
                },
            )
        except HTTPException as http_ex:
            raise http_ex
        except Exception as e:
            logger.error(f"Failed to activate user account: {e}")
            raise
    

    # ---------------------------
    # Password reset
    # ---------------------------
    async def reset_password(
        self,
        token: str,
        new_password: str,
        session: AsyncSession,
    )-> None:
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            
            if payload.get("type") != "password_reset":
                raise ValueError("Invalid reset token")
            
            user_id = uuid.UUID(payload["id"])
            
            user = await self.get_user_by_id(user_id, session, include_inactive=True)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "status": "error", "message": "User not found"
                    },
                )
                
            user.hashed_password = generate_password_hash(new_password)
            
            await self.reset_user_state(user, session, log_action=True)
            
            await session.commit()
            await session.refresh(user)
            
            logger.info(f"Password reset successful for user {user.email}")
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Password reset token expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid password reset token")
        except Exception as e:
            logger.error(f"Failed to reset password: {e}")
            raise


user_auth_service = UserAuthService()