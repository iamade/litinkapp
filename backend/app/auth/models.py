from typing import Optional
import uuid
from datetime import datetime, timezone
from pydantic import computed_field, Field
from app.auth.schema import UserBaseSchema, RoleChoicesSchema

class User(UserBaseSchema, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    hashed_password: str
    failed_login_attempts: int = Field(default=0)
    last_failed_login: Optional[datetime] = None
    otp: str = Field(max_length=6, default="")
    otp_expiry_time: Optional[datetime] = None 
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    @computed_field
    @property
    def full_name(self) -> str:
        full_name = f"{self.first_name} {self.middle_name + ' ' if self.middle_name else ''}{self.last_name}"
        return full_name.title().strip()
    
    def has_role(self, role: RoleChoicesSchema) -> bool:
        return role in self.roles 