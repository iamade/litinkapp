from fastapi import APIRouter, Depends
from app.core.auth import get_current_active_user
from app.auth.schema import UserReadSchema
from app.auth.models import User

router = APIRouter()


@router.get("/me", response_model=UserReadSchema)
def read_user_me(current_user: User = Depends(get_current_active_user)):
    return current_user
