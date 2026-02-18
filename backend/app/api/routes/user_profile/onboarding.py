from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.auth import get_current_user
from app.auth.models import User
from app.user_profile.models import Profile
from app.user_profile.schema import OnboardingData
from app.subscriptions.models import UserSubscription
from sqlmodel import select

router = APIRouter(prefix="/users/me", tags=["user_profile"])


@router.get("")
async def get_current_user_profile(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get current user profile including subscription tier.
    """
    # Look up user's subscription tier
    subscription_tier = "free"  # Default to free
    try:
        result = await session.exec(
            select(UserSubscription).where(UserSubscription.user_id == user.id)
        )
        subscription = result.first()
        if subscription and subscription.tier:
            subscription_tier = (
                subscription.tier.value
                if hasattr(subscription.tier, "value")
                else str(subscription.tier)
            )
    except Exception:
        # If lookup fails, default to free
        pass

    # Build response with all user fields + subscription_tier
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "roles": [
            role.value if hasattr(role, "value") else str(role)
            for role in (user.roles or [])
        ],
        "preferred_mode": user.preferred_mode,
        "onboarding_completed": user.onboarding_completed,
        "subscription_tier": subscription_tier,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
    }


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
