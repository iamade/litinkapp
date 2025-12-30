"""
Admin API Endpoints
Superadmin-only endpoints for cost tracking, metrics, system monitoring, and user management
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, func, col, desc, or_, text
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel, Field
import logging
import uuid

from app.core.auth import get_current_superadmin
from app.core.database import get_session
from app.core.services.cost_tracker import CostTrackerService
from app.core.services.metrics import MetricsService
from app.core.services.alert import AlertService
from app.core.config import settings
from app.user_profile.models import Profile
from app.auth.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# Pydantic models for request/response
class AlertSettingsUpdate(BaseModel):
    high_fallback_rate: Optional[float] = None
    cost_spike_percentage: Optional[float] = None
    circuit_breaker_enabled: Optional[bool] = None
    low_success_rate: Optional[float] = None


class AcknowledgeAlertRequest(BaseModel):
    alert_id: str


# User Deletion Models
class DeleteUserRequest(BaseModel):
    user_id: str
    reason: Optional[str] = None


class BatchDeleteUsersRequest(BaseModel):
    user_ids: List[str]
    reason: Optional[str] = None


# User Verification Management Endpoints
class ManualVerifyRequest(BaseModel):
    user_id: str


class BulkSendVerificationRequest(BaseModel):
    limit: Optional[int] = 100


# User Role Management Endpoints
class AddRoleToUserRequest(BaseModel):
    user_id: str
    role: str = Field(..., pattern="^(explorer|creator|admin|superadmin)$")


class RemoveRoleFromUserRequest(BaseModel):
    user_id: str
    role: str = Field(..., pattern="^(explorer|creator|admin|superadmin)$")


# Cost Tracking Endpoints
@router.get("/cost-tracking/summary")
async def get_cost_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get overall cost summary for the specified period"""
    cost_tracker = CostTrackerService(session)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    summary = await cost_tracker.get_cost_summary(start_date=start, end_date=end)
    return summary


@router.get("/cost-tracking/by-tier")
async def get_cost_by_tier(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get cost breakdown by subscription tier"""
    cost_tracker = CostTrackerService(session)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    tier_costs = await cost_tracker.get_cost_by_tier(start_date=start, end_date=end)
    return {"tiers": tier_costs}


@router.get("/cost-tracking/daily")
async def get_daily_costs(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get daily cost breakdown"""
    cost_tracker = CostTrackerService(session)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    daily_costs = await cost_tracker.get_daily_costs(start_date=start, end_date=end)
    return {"daily_costs": daily_costs}


@router.get("/cost-tracking/predictions")
async def get_cost_predictions(
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get cost predictions based on usage patterns"""
    cost_tracker = CostTrackerService(session)
    predictions = await cost_tracker.get_cost_predictions()
    return predictions


# Metrics Endpoints
@router.get("/metrics/fallback-rates")
async def get_fallback_rates(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get fallback rates by tier and service"""
    metrics_service = MetricsService(session)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    fallback_rates = await metrics_service.get_fallback_rates(
        start_date=start, end_date=end
    )
    return fallback_rates


@router.get("/metrics/model-performance")
async def get_model_performance(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get performance metrics for all models"""
    metrics_service = MetricsService(session)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    performance = await metrics_service.get_model_performance(
        start_date=start, end_date=end
    )
    return {"models": performance}


@router.get("/metrics/circuit-breaker-status")
async def get_circuit_breaker_status(
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get current circuit breaker status for all models"""
    metrics_service = MetricsService(session)
    status = await metrics_service.get_circuit_breaker_status()
    return {"circuit_breakers": status}


@router.get("/metrics/model-usage-distribution")
async def get_model_usage_distribution(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get model usage distribution by service"""
    metrics_service = MetricsService(session)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    distribution = await metrics_service.get_model_usage_distribution(
        start_date=start, end_date=end
    )
    return distribution


@router.get("/metrics/generation-times")
async def get_generation_times(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get average generation times by service and model"""
    metrics_service = MetricsService(session)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    times = await metrics_service.get_generation_times(start_date=start, end_date=end)
    return times


@router.get("/health-check")
async def get_health_check(
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get system health check with model availability"""
    metrics_service = MetricsService(session)
    health = await metrics_service.get_health_check()
    return health


# Alert Endpoints
@router.get("/alerts/recent")
async def get_recent_alerts(
    hours: int = Query(24, description="Number of hours to look back"),
    acknowledged: Optional[bool] = Query(
        None, description="Filter by acknowledged status"
    ),
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get recent alerts"""
    alert_service = AlertService(session)
    alerts = await alert_service.get_recent_alerts(
        hours=hours, acknowledged=acknowledged
    )
    return {"alerts": alerts}


@router.get("/alerts/statistics")
async def get_alert_statistics(
    days: int = Query(7, description="Number of days for statistics"),
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get alert statistics"""
    alert_service = AlertService(session)
    stats = await alert_service.get_alert_statistics(days=days)
    return stats


@router.post("/alerts/acknowledge")
async def acknowledge_alert(
    request: AcknowledgeAlertRequest,
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Acknowledge an alert"""
    alert_service = AlertService(session)
    result = await alert_service.acknowledge_alert(
        alert_id=request.alert_id, user_id=current_user["id"]
    )
    return {"success": True, "alert": result}


@router.post("/alerts/check")
async def run_alert_check(
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Manually trigger alert check (usually runs on schedule)"""
    alert_service = AlertService(session)
    alerts = await alert_service.check_all_alerts()
    return {"alerts_created": len(alerts), "alerts": alerts}


@router.get("/alerts/settings")
async def get_alert_settings(
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get current alert threshold settings"""
    alert_service = AlertService(session)
    settings = await alert_service.get_alert_settings()
    return {"settings": settings}


@router.put("/alerts/settings")
async def update_alert_settings(
    settings: AlertSettingsUpdate,
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Update alert threshold settings"""
    alert_service = AlertService(session)

    # Get current settings and merge with updates
    current_settings = await alert_service.get_alert_settings()

    update_dict = settings.dict(exclude_unset=True)
    merged_settings = {**current_settings, **update_dict}

    result = await alert_service.update_alert_settings(
        settings=merged_settings, user_id=current_user["id"]
    )

    return {"success": True, "settings": result}


# User Verification Management Endpoints
@router.get("/users/unverified")
async def get_unverified_users(
    limit: int = Query(100, description="Maximum number of users to return"),
    offset: int = Query(0, description="Pagination offset"),
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get list of unverified users"""
    try:
        stmt = select(Profile).where(Profile.email_verified == False)
        stmt = stmt.order_by(desc(Profile.created_at))
        stmt = stmt.offset(offset).limit(limit)

        result = await session.exec(stmt)
        users = result.all()

        # Get total count
        count_stmt = select(func.count()).where(Profile.email_verified == False)
        count_result = await session.exec(count_stmt)
        total = count_result.one()

        return {
            "users": users,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Error fetching unverified users: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch unverified users")


@router.post("/users/verify-manually")
async def manually_verify_user(
    request: ManualVerifyRequest,
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Manually verify a user's email (bypass email verification)"""
    try:
        # Update profile to mark as verified
        stmt = select(Profile).where(Profile.id == request.user_id)
        result = await session.exec(stmt)
        user = result.first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.email_verified = True
        session.add(user)
        await session.commit()
        await session.refresh(user)

        logger.info(
            f"Admin {current_user['email']} manually verified user {request.user_id}"
        )

        return {
            "success": True,
            "message": "User email verified successfully",
            "user": user,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error manually verifying user: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify user")


@router.post("/users/send-verification-bulk")
async def send_verification_emails_bulk(
    request: BulkSendVerificationRequest,
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Send verification emails to all unverified users (batch operation)"""
    # TODO: Implement this using a proper Auth service or email service.
    # Supabase client removal means we cannot use supabase.auth.resend directly here.
    # This functionality is temporarily disabled during refactoring.

    return {
        "success": False,
        "message": "Bulk verification email sending is temporarily disabled during system upgrade.",
        "sent": 0,
        "failed": 0,
    }


@router.get("/users/verification-stats")
async def get_verification_statistics(
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get statistics about user activation (verified users)"""
    try:
        # Total users (using User model, not Profile)
        total_stmt = select(func.count()).select_from(User)
        total_result = await session.exec(total_stmt)
        total_users = total_result.one()

        # Active/Verified users (is_active = true means verified)
        verified_stmt = (
            select(func.count()).select_from(User).where(User.is_active == True)
        )
        verified_result = await session.exec(verified_stmt)
        verified_users = verified_result.one()

        # Inactive/Unverified users
        unverified_users = total_users - verified_users

        # Users who verified within 24 hours - simplified (not tracked precisely)
        verified_within_24h = 0

        verification_rate = (
            (verified_users / total_users * 100) if total_users > 0 else 0
        )

        return {
            "total_users": total_users,
            "verified_users": verified_users,
            "unverified_users": unverified_users,
            "verification_rate": round(verification_rate, 2),
            "verified_within_24h": verified_within_24h,
        }
    except Exception as e:
        logger.error(f"Error fetching verification statistics: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch verification statistics"
        )


# User Role Management Endpoints
@router.get("/users/list")
async def list_all_users(
    limit: int = Query(50, description="Maximum number of users to return"),
    offset: int = Query(0, description="Pagination offset"),
    search: Optional[str] = Query(None, description="Search by email or display name"),
    role_filter: Optional[str] = Query(None, description="Filter by role"),
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get list of all users with their roles"""
    try:
        stmt = select(User)

        # Apply search filter if provided
        if search:
            stmt = stmt.where(
                or_(
                    col(User.email).ilike(f"%{search}%"),
                    col(User.display_name).ilike(f"%{search}%"),
                )
            )

        # Apply role filter if provided - use text() for JSON array containment
        if role_filter:
            # For JSON column, we need to cast to text and check if role is in the array
            stmt = stmt.where(text(f"roles::text LIKE '%\"{role_filter}\"%'"))

        # Apply pagination
        stmt = stmt.order_by(desc(User.created_at)).offset(offset).limit(limit)

        result = await session.exec(stmt)
        users = result.all()

        # Get total count
        count_stmt = select(func.count()).select_from(User)
        if search:
            count_stmt = count_stmt.where(
                or_(
                    col(User.email).ilike(f"%{search}%"),
                    col(User.display_name).ilike(f"%{search}%"),
                )
            )
        if role_filter:
            count_stmt = count_stmt.where(
                text(f"roles::text LIKE '%\"{role_filter}\"%'")
            )

        count_result = await session.exec(count_stmt)
        total = count_result.one()

        return {
            "users": users,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get detailed information about a specific user"""
    try:
        stmt = select(Profile).where(Profile.id == user_id)
        result = await session.exec(stmt)
        user = result.first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {"user": user}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user details")


@router.get("/users/{user_id}/roles")
async def get_user_roles(
    user_id: str,
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get roles for a specific user"""
    try:
        stmt = select(Profile).where(Profile.id == user_id)
        result = await session.exec(stmt)
        user = result.first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "roles": user.roles,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user roles: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user roles")


@router.post("/users/roles/add")
async def add_role_to_user(
    request: AddRoleToUserRequest,
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Add a role to a user"""
    try:
        # Prevent adding superadmin role unless current user is superadmin
        if (
            request.role == "superadmin"
            and current_user["email"] != "support@litinkai.com"
        ):
            raise HTTPException(
                status_code=403,
                detail="Only the primary superadmin can grant superadmin role",
            )

        # Check if user exists
        stmt = select(Profile).where(Profile.id == request.user_id)
        result = await session.exec(stmt)
        user = result.first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if user already has the role
        current_roles = user.roles or []
        if request.role in current_roles:
            return {
                "success": True,
                "message": f"User already has the {request.role} role",
                "user": user,
            }

        # Add role
        # We can update the Profile directly, but if there's an RPC 'add_role_to_user'
        # that does more (like syncs with Auth), we should try to call it.
        # However, for pure DB refactor, we update the Profile.
        # If the RPC is critical, we can call it via SQL.
        # Let's try to call the RPC via SQL for consistency with previous logic,
        # assuming the RPC exists in Postgres.
        try:
            await session.exec(
                text("SELECT add_role_to_user(:user_id, :new_role)"),
                params={"user_id": request.user_id, "new_role": request.role},
            )
            await session.commit()
            await session.refresh(user)
        except Exception as rpc_error:
            # Fallback to direct update if RPC fails or doesn't exist
            logger.warning(
                f"RPC add_role_to_user failed, falling back to direct update: {rpc_error}"
            )
            if request.role not in current_roles:
                user.roles = current_roles + [request.role]
                session.add(user)
                await session.commit()
                await session.refresh(user)

        logger.info(
            f"Admin {current_user['email']} added role '{request.role}' to user {user.email}"
        )

        return {
            "success": True,
            "message": f"Successfully added {request.role} role to user",
            "user": user,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding role to user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add role: {str(e)}")


@router.post("/users/roles/remove")
async def remove_role_from_user(
    request: RemoveRoleFromUserRequest,
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Remove a role from a user"""
    try:
        # Prevent removing superadmin role from primary superadmin
        stmt = select(Profile).where(Profile.id == request.user_id)
        result = await session.exec(stmt)
        user = result.first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if request.role == "superadmin" and user.email == "support@litinkai.com":
            raise HTTPException(
                status_code=403,
                detail="Cannot remove superadmin role from primary superadmin account",
            )

        # Check if user has the role
        current_roles = user.roles or []
        if request.role not in current_roles:
            return {
                "success": True,
                "message": f"User does not have the {request.role} role",
                "user": user,
            }

        # Remove role
        try:
            await session.exec(
                text("SELECT remove_role_from_user(:user_id, :role_to_remove)"),
                params={"user_id": request.user_id, "role_to_remove": request.role},
            )
            await session.commit()
            await session.refresh(user)
        except Exception as e:
            if "Cannot remove last role" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail="Cannot remove last role from user. User must have at least one role.",
                )
            # Fallback to direct update
            logger.warning(
                f"RPC remove_role_from_user failed, falling back to direct update: {e}"
            )
            if request.role in current_roles:
                if len(current_roles) <= 1:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot remove last role from user. User must have at least one role.",
                    )
                new_roles = [r for r in current_roles if r != request.role]
                user.roles = new_roles
                session.add(user)
                await session.commit()
                await session.refresh(user)

        logger.info(
            f"Admin {current_user['email']} removed role '{request.role}' from user {user.email}"
        )

        return {
            "success": True,
            "message": f"Successfully removed {request.role} role from user",
            "user": user,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing role from user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove role: {str(e)}")


@router.get("/roles/available")
async def get_available_roles(
    current_user: dict = Depends(get_current_superadmin),
):
    """Get list of available roles in the system"""
    return {
        "roles": [
            {
                "value": "explorer",
                "label": "Explorer",
                "description": "Basic user who can explore and consume content",
            },
            {
                "value": "creator",
                "label": "Creator",
                "description": "Can create and publish their own content",
            },
            {
                "value": "admin",
                "label": "Admin",
                "description": "Can manage content and users",
            },
            {
                "value": "superadmin",
                "label": "Super Admin",
                "description": "Full system access",
            },
        ]
    }


# User Deletion Endpoints
@router.get("/users/{user_id}/deletion-preview")
async def get_user_deletion_preview(
    user_id: str,
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get preview of what will be deleted if user is removed"""
    try:
        # Convert string user_id to UUID
        import uuid as uuid_module

        try:
            user_uuid = uuid_module.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        # Get the user first
        user_stmt = select(User).where(User.id == user_uuid)
        user_result = await session.exec(user_stmt)
        user = user_result.first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if trying to delete primary superadmin
        if user.email == "support@litinkai.com":
            raise HTTPException(
                status_code=403, detail="Cannot delete primary superadmin account"
            )

        # Count related content - import models as needed
        from app.books.models import Book, Chapter
        from app.plots.models import PlotOverview, Character, ChapterScript
        from app.videos.models import ImageGeneration, AudioGeneration, VideoSegment
        from app.subscriptions.models import UserSubscription, UsageLog

        # Get counts for each type of content (use user_uuid for all queries)
        books_count = (
            await session.exec(
                select(func.count()).select_from(Book).where(Book.user_id == user_uuid)
            )
        ).one()

        chapters_count = (
            await session.exec(
                select(func.count())
                .select_from(Chapter)
                .join(Book, Chapter.book_id == Book.id)
                .where(Book.user_id == user_uuid)
            )
        ).one()

        characters_count = (
            await session.exec(
                select(func.count())
                .select_from(Character)
                .where(Character.user_id == user_uuid)
            )
        ).one()

        plot_overviews_count = (
            await session.exec(
                select(func.count())
                .select_from(PlotOverview)
                .where(PlotOverview.user_id == user_uuid)
            )
        ).one()

        chapter_scripts_count = (
            await session.exec(
                select(func.count())
                .select_from(ChapterScript)
                .where(ChapterScript.user_id == user_uuid)
            )
        ).one()

        image_generations_count = (
            await session.exec(
                select(func.count())
                .select_from(ImageGeneration)
                .where(ImageGeneration.user_id == user_uuid)
            )
        ).one()

        audio_generations_count = (
            await session.exec(
                select(func.count())
                .select_from(AudioGeneration)
                .where(AudioGeneration.user_id == user_uuid)
            )
        ).one()

        video_generations_count = (
            await session.exec(
                select(func.count())
                .select_from(VideoSegment)
                .where(VideoSegment.user_id == user_uuid)
            )
        ).one()

        subscriptions_count = (
            await session.exec(
                select(func.count())
                .select_from(UserSubscription)
                .where(UserSubscription.user_id == user_uuid)
            )
        ).one()

        usage_logs_count = (
            await session.exec(
                select(func.count())
                .select_from(UsageLog)
                .where(UsageLog.user_id == user_uuid)
            )
        ).one()

        # Build the preview response
        content_counts = {
            "books": books_count,
            "chapters": chapters_count,
            "characters": characters_count,
            "scripts": chapter_scripts_count,
            "plot_overviews": plot_overviews_count,
            "image_generations": image_generations_count,
            "audio_generations": audio_generations_count,
            "video_generations": video_generations_count,
            "subscriptions": subscriptions_count,
            "usage_logs": usage_logs_count,
        }

        # Generate warnings
        warnings = []
        total_content = sum(content_counts.values())
        if total_content > 100:
            warnings.append(
                f"This user has {total_content} total items that will be deleted"
            )
        if subscriptions_count > 0:
            warnings.append("User has active subscription(s)")

        return {
            "user_id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "roles": [
                r.value if hasattr(r, "value") else r for r in (user.roles or [])
            ],
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "email_verified": user.is_active,
            "content_counts": content_counts,
            "can_delete": True,
            "warnings": warnings,
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting deletion preview for user {user_id}: {error_msg}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get deletion preview: {error_msg}"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Permanently delete a user and all their content"""
    try:
        # Call the database function to delete user
        from sqlalchemy import text

        query = text(
            """
            SELECT * FROM delete_user_completely(
                :target_user_id, 
                :deleting_admin_id, 
                :deletion_reason
            )
        """
        )
        result_proxy = await session.execute(
            query,
            {
                "target_user_id": user_id,
                "deleting_admin_id": current_user["id"],
                "deletion_reason": reason,
            },
        )
        result = result_proxy.mappings().first()

        # Check if deletion was successful
        if not result.get("success"):
            error_message = result.get("error", "Unknown error")
            logger.error(f"User deletion failed for {user_id}: {error_message}")

            # Handle specific errors
            if "User not found" in error_message:
                raise HTTPException(status_code=404, detail="User not found")
            if "Cannot delete primary superadmin" in error_message:
                raise HTTPException(
                    status_code=403, detail="Cannot delete primary superadmin account"
                )
            if "Cannot delete your own account" in error_message:
                raise HTTPException(
                    status_code=403, detail="Cannot delete your own account"
                )

            raise HTTPException(
                status_code=500, detail=f"Deletion failed: {error_message}"
            )

        logger.info(
            f"User {result.get('deleted_email')} deleted by admin {current_user['email']}"
        )

        return {
            "success": True,
            "message": f"User {result.get('deleted_email')} has been permanently deleted",
            "deleted_user_id": result.get("deleted_user_id"),
            "deleted_email": result.get("deleted_email"),
            "audit_id": result.get("audit_id"),
            "deleted_at": result.get("deleted_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


@router.post("/users/batch-delete")
async def batch_delete_users(
    request: BatchDeleteUsersRequest,
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Delete multiple users at once"""
    if not request.user_ids:
        raise HTTPException(status_code=400, detail="No user IDs provided")

    results = {"total": len(request.user_ids), "successful": [], "failed": []}

    for user_id in request.user_ids:
        try:
            # Call the database function to delete user
            from sqlalchemy import text

            query = text(
                """
                SELECT * FROM delete_user_completely(
                    :target_user_id, 
                    :deleting_admin_id, 
                    :deletion_reason
                )
            """
            )
            result_proxy = await session.execute(
                query,
                {
                    "target_user_id": user_id,
                    "deleting_admin_id": current_user["id"],
                    "deletion_reason": request.reason or "Batch deletion",
                },
            )
            result = result_proxy.mappings().first()

            if result and result.get("success"):
                results["successful"].append(
                    {
                        "user_id": user_id,
                        "email": result.get("deleted_email"),
                        "audit_id": result.get("audit_id"),
                    }
                )
                logger.info(
                    f"Batch deletion: User {result.get('deleted_email')} deleted"
                )
            else:
                error_msg = (
                    result.get("error", "Unknown error") if result else "No response"
                )
                results["failed"].append({"user_id": user_id, "error": error_msg})
                logger.error(f"Batch deletion failed for user {user_id}: {error_msg}")
        except Exception as e:
            results["failed"].append({"user_id": user_id, "error": str(e)})
            logger.error(f"Exception during batch deletion for user {user_id}: {e}")

    logger.info(
        f"Batch deletion completed by {current_user['email']}: {len(results['successful'])} successful, {len(results['failed'])} failed"
    )

    return {
        "success": len(results["failed"]) == 0,
        "message": f"Deleted {len(results['successful'])} of {results['total']} users",
        "results": results,
    }


@router.get("/users/deletion-audit")
async def get_deletion_audit_log(
    limit: int = Query(50, description="Maximum number of audit records to return"),
    offset: int = Query(0, description="Pagination offset"),
    current_user: dict = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    """Get audit log of deleted users"""
    try:
        from sqlalchemy import text

        # Get audit logs with pagination
        query = text(
            """
            SELECT id, original_user_id, email, display_name, roles, user_created_at, 
                   deleted_at, deletion_reason, content_summary, deleted_by
            FROM deleted_users_audit
            ORDER BY deleted_at DESC
            LIMIT :limit OFFSET :offset
        """
        )
        result = await session.execute(query, {"limit": limit, "offset": offset})
        audit_logs = [dict(row) for row in result.mappings()]

        # Get total count
        count_query = text("SELECT COUNT(*) as count FROM deleted_users_audit")
        count_result = await session.execute(count_query)
        total_count = count_result.scalar()

        return {
            "audit_logs": audit_logs,
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Failed to fetch deletion audit log: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch audit log: {str(e)}"
        )
