from fastapi import APIRouter, Depends, HTTPException
from app.auth.schema import (
    UserReadSchema,
    UserUpdateSchema,
    RoleChoicesSchema,
    AddRoleRequestSchema,
    RemoveRoleRequestSchema,
)
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


@router.post("/me/roles", response_model=UserReadSchema)
async def add_role_to_me(
    role_data: AddRoleRequestSchema,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Self-service role addition. Users can add 'creator' role to themselves.
    Admin/super_admin roles cannot be self-assigned.
    """
    try:
        role = RoleChoicesSchema(role_data.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role: {role_data.role}. Valid roles: explorer, creator",
        )

    # Prevent self-assignment of admin roles
    if role in [RoleChoicesSchema.ADMIN, RoleChoicesSchema.SUPER_ADMIN]:
        raise HTTPException(
            status_code=403, detail="Admin roles cannot be self-assigned"
        )

    # Check if user already has this role
    if role in current_user.roles:
        raise HTTPException(
            status_code=400, detail=f"User already has role: {role.value}"
        )

    # Add the role
    current_user.roles = list(current_user.roles) + [role]
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return current_user


@router.delete("/me/roles", response_model=UserReadSchema)
async def remove_role_from_me(
    role_data: RemoveRoleRequestSchema,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Self-service role removal. Users can remove 'creator' role from themselves.
    Cannot remove the last remaining role (must keep at least 'explorer').
    """
    try:
        role = RoleChoicesSchema(role_data.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role: {role_data.role}. Valid roles: explorer, creator",
        )

    # Check if user has this role
    if role not in current_user.roles:
        raise HTTPException(
            status_code=400, detail=f"User does not have role: {role.value}"
        )

    # Ensure user keeps at least one role (explorer)
    if len(current_user.roles) <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove last role. Users must have at least one role.",
        )

    # Remove the role
    new_roles = [r for r in current_user.roles if r != role]
    current_user.roles = new_roles
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return current_user
