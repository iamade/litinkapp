from pydantic import field_validator
from pydantic.functional_validators import AfterValidator
from sqlmodel import SQLModel, Field
from typing import Optional, List, Annotated
from fastapi import HTTPException, status
from enum import Enum
import uuid
import re
from sqlalchemy import Column, JSON


def validate_email_flexible(v: str) -> str:
    """Custom email validator that allows .local domains for development/testing."""
    if not v:
        raise ValueError("Email is required")

    # Basic email format validation
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, v):
        raise ValueError("Invalid email format")

    return v.lower()


# Custom email type that allows .local domains
FlexibleEmailStr = Annotated[str, AfterValidator(validate_email_flexible)]


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
            cls.BIRTH_CITY: "What is the name of the city you were born in",
        }
        return descriptions.get(value, "Unknown security question")


class AccountStatusSchema(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    PENDING = "pending"


class RoleChoicesSchema(str, Enum):
    EXPLORER = "explorer"
    # AUTHOR = "author"
    CREATOR = "creator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserBaseSchema(SQLModel):
    email: FlexibleEmailStr = Field(unique=True, index=True, max_length=255)
    display_name: str | None = Field(
        default=None, max_length=100, unique=True, nullable=True
    )
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    first_name: str | None = Field(default=None, max_length=30, nullable=True)
    middle_name: str | None = Field(max_length=30, default=None)
    last_name: str | None = Field(default=None, max_length=30, nullable=True)
    roles: List[RoleChoicesSchema] = Field(
        default=[RoleChoicesSchema.EXPLORER], sa_column=Column(JSON)
    )
    is_active: bool = False
    is_superuser: bool = False
    security_question: SecurityQuestionsSchema | None = Field(
        default=None, max_length=30, nullable=True
    )
    security_answer: str | None = Field(default=None, max_length=30, nullable=True)
    account_status: AccountStatusSchema = Field(default=AccountStatusSchema.INACTIVE)
    preferred_mode: str = Field(default="explorer")
    onboarding_completed: bool = Field(default=False)


class UserCreateSchema(UserBaseSchema):
    password: str = Field(min_length=8, max_length=40)
    confirm_password: str = Field(min_length=8, max_length=40)

    @field_validator("confirm_password")
    def validate_confirm_password(cls, v, values):
        if "password" in values.data and v != values.data["password"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Passwords do not match",
                    "action": "Please ensure that the passwords you entered match",
                },
            )
        return v


class UserReadSchema(UserBaseSchema):
    id: uuid.UUID
    full_name: str


class UserUpdateSchema(SQLModel):
    preferred_mode: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class EmailVerificationRequestSchema(SQLModel):
    email: FlexibleEmailStr


class UserLoginRequestSchema(SQLModel):
    email: FlexibleEmailStr
    password: str = Field(
        min_length=8,
        max_length=40,
    )


class AddRoleRequestSchema(SQLModel):
    role: str = Field(..., description="Role to add: 'creator' or 'explorer'")


class RemoveRoleRequestSchema(SQLModel):
    role: str = Field(..., description="Role to remove: 'creator' or 'explorer'")


class TokenDataSchema(SQLModel):
    user_id: Optional[str] = None


class PasswordResetRequestSchema(SQLModel):
    email: FlexibleEmailStr


class PasswordResetConfirmSchema(SQLModel):
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=40,
    )

    confirm_password: str = Field(..., min_length=8, max_length=40)

    @field_validator("confirm_password")
    def validate_password_match(cls, v, values):
        if "new_password" in values.data and v != values.data["new_password"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Passwords do not match",
                    "action": "Please ensure that the passwords you entered match",
                },
            )

        return v
