from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional, List
from fastapi import HTTPException, status
from enum import Enum
import uuid

class SecurityQuestionsSchema(str, Enum):
    MOTHER_MAIDEN_NAME = "mother_maiden_name"
    CHILDHOOD_FRIEND = "childhood_friend"
    FAVORITE_COLOUR = "favorite_color"
    BIRTH_CITY = "birth_city"
    
    @classmethod
    def get_description(cls, value: "SecurityQuestionsSchema") -> str:
        descriptions = {
            cls.MOTHER_MAIDEN_NAME: "What is the name of your mother?",
            cls.CHILDHOOD_FRIEND: "What is the name of your childhood friend?",
            cls.FAVORITE_COLOUR: "What is your favorite color?",
            cls.BIRTH_CITY: "What is the name of the city you were born in"
        }
        return descriptions.get(value, "Unknown security question")
    

class AccountStatusSchema(str, Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    LOCKED = 'locked'
    PENDING = 'pending'
    

class RoleChoicesSchema(str, Enum):
    EXPLORER = "explorer"
    # AUTHOR = "author"
    CREATOR = "creator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    
class UserBaseSchema(BaseModel):
    email: EmailStr
    display_name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    first_name: str = Field(max_length=30)
    middle_name: str | None = Field(max_length=30, default=None)
    last_name: str = Field(max_length=30)
    roles: List[RoleChoicesSchema] = Field(default=[RoleChoicesSchema.EXPLORER])
    is_active: bool = False
    is_superuser: bool = False
    security_question: SecurityQuestionsSchema = Field(max_length=30)
    security_answer: str = Field(max_length=30)
    account_status: AccountStatusSchema = Field(default=AccountStatusSchema.INACTIVE)
    
class UserCreateSchema(UserBaseSchema):
    password: str = Field(min_length=8, max_length=40)
    confirm_password: str = Field(min_length=8, max_length=40)
    
    @field_validator("confirm_password")
    def validate_confirm_password(cls,v,values):
        if "password" in values.data and v!= values.data["password"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status":"error",
                    "message": "Passwords do not match",
                    "action": "Please ensure that the passwords you entered match",
                    
                }
            )
        return v
    
class UserReadSchema(UserBaseSchema):
    id: uuid.UUID
    full_name: str
    
class EmailVerificationRequestSchema(BaseModel):
    email: EmailStr
    
class UserLoginRequestSchema(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=40,
    )
    
class OTPVerifyRequestSchema(BaseModel):
    email: EmailStr
    otp: str = Field(
        min_length=6,
        max_length=6,
    )
    
class UserUpdateSchema(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


# class UserSchema(UserBaseSchema):
#     id: str
#     is_active: bool
#     is_verified: bool
#     email_verified: bool
#     email_verified_at: Optional[datetime] = None
#     created_at: datetime
#     updated_at: datetime
    
#     class Config:
#         from_attributes = True

class AddRoleRequestSchema(BaseModel):
    role: str = Field(..., description="Role to add: 'creator' or 'explorer'")


class RemoveRoleRequestSchema(BaseModel):
    role: str = Field(..., description="Role to remove: 'creator' or 'explorer'")

    

class TokenSchema(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str


class TokenDataSchema(BaseModel):
    user_id: Optional[str] = None

# class UserRegisterSchema(BaseModel):
#     email: EmailStr
#     password: str
#     display_name: Optional[str] = None
#     role: str = "explorer"
    
class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordResetConfirmSchema(BaseModel):
    email: EmailStr
    token: str
    new_password: str = Field(min_length=8, max_length=40)


