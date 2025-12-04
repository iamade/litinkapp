from fastapi import APIRouter, Depends
from app.auth.schema import UserReadSchema, UserUpdateSchema
from app.auth.models import User
from app.core.auth import get_current_active_user
from app.core.database import get_session
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter()


@router.get("/me", response_model=UserReadSchema)
async def read_user_me(
    current_user: User = Depends(get_current_active_user),
):
    return current_user


@router.put("/me", response_model=UserReadSchema)
async def update_user_me(
    user_in: UserUpdateSchema,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update own user.
    """
    user_data = user_in.model_dump(exclude_unset=True)

    for field, value in user_data.items():
        setattr(current_user, field, value)

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return current_user
