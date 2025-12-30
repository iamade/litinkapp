from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.auth import get_current_user
from app.auth.models import User
from app.user_profile.models import Profile
from app.user_profile.schema import OnboardingData
from sqlmodel import select

router = APIRouter(prefix="/users/me", tags=["user_profile"])


@router.post("/onboarding")
async def save_onboarding_data(
    data: OnboardingData,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    try:
        # Update User fields if provided
        if data.firstName:
            user.first_name = data.firstName
        if data.lastName:
            user.last_name = data.lastName
        if data.username:
            user.display_name = data.username
        if data.securityQuestion:
            user.security_question = data.securityQuestion
        if data.securityAnswer:
            user.security_answer = data.securityAnswer

        user.onboarding_completed = True

        session.add(user)

        # Get or create Profile
        result = await session.exec(select(Profile).where(Profile.user_id == user.id))
        profile = result.first()

        if not profile:
            profile = Profile(user_id=user.id)

        # Update Profile preferences
        preferences = profile.preferences or {}
        preferences.update(
            {
                "primaryRole": data.primaryRole,
                "professionalRole": data.professionalRole,
                "teamSize": data.teamSize,
                "discoverySource": data.discoverySource,
                "interests": data.interests,
            }
        )
        profile.preferences = preferences

        session.add(profile)
        await session.commit()
        await session.refresh(user)

        return {"message": "Onboarding completed successfully"}

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save onboarding data: {str(e)}",
        )
