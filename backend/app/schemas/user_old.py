from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    display_name: str
    roles: List[str] = Field(default=["explorer"])
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


class User(UserBase):
    id: str
    is_active: bool
    is_verified: bool
    email_verified: bool
    email_verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AddRoleRequest(BaseModel):
    role: str = Field(..., description="Role to add: 'author' or 'explorer'")


class RemoveRoleRequest(BaseModel):
    role: str = Field(..., description="Role to remove: 'author' or 'explorer'")