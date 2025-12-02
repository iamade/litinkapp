"""
Admin API Endpoints
Superadmin-only endpoints for cost tracking, metrics, system monitoring, and user management
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client
from pydantic import BaseModel, Field
import logging

from app.core.auth import get_current_superadmin
from app.core.database import get_supabase
from app.core.services.cost_tracker import CostTrackerService
from app.core.services.metrics import MetricsService
from app.core.services.alert import AlertService
from app.core.config import settings

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


# Cost Tracking Endpoints
@router.get("/cost-tracking/summary")
async def get_cost_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get overall cost summary for the specified period"""
    cost_tracker = CostTrackerService(supabase)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    summary = await cost_tracker.get_cost_summary(start_date=start, end_date=end)
    return summary


@router.get("/cost-tracking/by-tier")
async def get_cost_by_tier(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get cost breakdown by subscription tier"""
    cost_tracker = CostTrackerService(supabase)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    tier_costs = await cost_tracker.get_cost_by_tier(start_date=start, end_date=end)
    return {"tiers": tier_costs}


@router.get("/cost-tracking/daily")
async def get_daily_costs(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get daily cost breakdown"""
    cost_tracker = CostTrackerService(supabase)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    daily_costs = await cost_tracker.get_daily_costs(start_date=start, end_date=end)
    return {"daily_costs": daily_costs}


@router.get("/cost-tracking/predictions")
async def get_cost_predictions(
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get cost predictions based on usage patterns"""
    cost_tracker = CostTrackerService(supabase)
    predictions = await cost_tracker.get_cost_predictions()
    return predictions


# Metrics Endpoints
@router.get("/metrics/fallback-rates")
async def get_fallback_rates(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get fallback rates by tier and service"""
    metrics_service = MetricsService(supabase)

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
    supabase: Client = Depends(get_supabase),
):
    """Get performance metrics for all models"""
    metrics_service = MetricsService(supabase)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    performance = await metrics_service.get_model_performance(
        start_date=start, end_date=end
    )
    return {"models": performance}


@router.get("/metrics/circuit-breaker-status")
async def get_circuit_breaker_status(
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get current circuit breaker status for all models"""
    metrics_service = MetricsService(supabase)
    status = await metrics_service.get_circuit_breaker_status()
    return {"circuit_breakers": status}


@router.get("/metrics/model-usage-distribution")
async def get_model_usage_distribution(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get model usage distribution by service"""
    metrics_service = MetricsService(supabase)

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
    supabase: Client = Depends(get_supabase),
):
    """Get average generation times by service and model"""
    metrics_service = MetricsService(supabase)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    times = await metrics_service.get_generation_times(start_date=start, end_date=end)
    return times


@router.get("/health-check")
async def get_health_check(
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get system health check with model availability"""
    metrics_service = MetricsService(supabase)
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
    supabase: Client = Depends(get_supabase),
):
    """Get recent alerts"""
    alert_service = AlertService(supabase)
    alerts = await alert_service.get_recent_alerts(
        hours=hours, acknowledged=acknowledged
    )
    return {"alerts": alerts}


@router.get("/alerts/statistics")
async def get_alert_statistics(
    days: int = Query(7, description="Number of days for statistics"),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get alert statistics"""
    alert_service = AlertService(supabase)
    stats = await alert_service.get_alert_statistics(days=days)
    return stats


@router.post("/alerts/acknowledge")
async def acknowledge_alert(
    request: AcknowledgeAlertRequest,
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Acknowledge an alert"""
    alert_service = AlertService(supabase)
    result = await alert_service.acknowledge_alert(
        alert_id=request.alert_id, user_id=current_user["id"]
    )
    return {"success": True, "alert": result}


@router.post("/alerts/check")
async def run_alert_check(
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Manually trigger alert check (usually runs on schedule)"""
    alert_service = AlertService(supabase)
    alerts = await alert_service.check_all_alerts()
    return {"alerts_created": len(alerts), "alerts": alerts}


@router.get("/alerts/settings")
async def get_alert_settings(
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get current alert threshold settings"""
    alert_service = AlertService(supabase)
    settings = await alert_service.get_alert_settings()
    return {"settings": settings}


@router.put("/alerts/settings")
async def update_alert_settings(
    settings: AlertSettingsUpdate,
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Update alert threshold settings"""
    alert_service = AlertService(supabase)

    # Get current settings and merge with updates
    current_settings = await alert_service.get_alert_settings()

    update_dict = settings.dict(exclude_unset=True)
    merged_settings = {**current_settings, **update_dict}

    result = await alert_service.update_alert_settings(
        settings=merged_settings, user_id=current_user["id"]
    )

    return {"success": True, "settings": result}


# User Verification Management Endpoints
class ManualVerifyRequest(BaseModel):
    user_id: str


class BulkSendVerificationRequest(BaseModel):
    limit: Optional[int] = 100


@router.get("/users/unverified")
async def get_unverified_users(
    limit: int = Query(100, description="Maximum number of users to return"),
    offset: int = Query(0, description="Pagination offset"),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get list of unverified users"""
    try:
        response = (
            supabase.table("profiles")
            .select("id, email, display_name, created_at, verification_token_sent_at")
            .eq("email_verified", False)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        # Get total count
        count_response = (
            supabase.table("profiles")
            .select("id", count="exact")
            .eq("email_verified", False)
            .execute()
        )

        return {
            "users": response.data,
            "total": count_response.count,
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
    supabase: Client = Depends(get_supabase),
):
    """Manually verify a user's email (bypass email verification)"""
    try:
        # Update profile to mark as verified
        response = (
            supabase.table("profiles")
            .update({"email_verified": True})
            .eq("id", request.user_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")

        logger.info(
            f"Admin {current_user['email']} manually verified user {request.user_id}"
        )

        return {
            "success": True,
            "message": "User email verified successfully",
            "user": response.data[0],
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
    supabase: Client = Depends(get_supabase),
):
    """Send verification emails to all unverified users (batch operation)"""
    try:
        # Get unverified users
        response = (
            supabase.table("profiles")
            .select("id, email")
            .eq("email_verified", False)
            .limit(request.limit)
            .execute()
        )

        if not response.data:
            return {
                "success": True,
                "message": "No unverified users found",
                "sent": 0,
                "failed": 0,
            }

        sent_count = 0
        failed_count = 0
        failed_users = []

        for user in response.data:
            try:
                # Resend verification email via Supabase Auth
                supabase.auth.resend(
                    type="signup",
                    email=user["email"],
                    options={
                        "email_redirect_to": f"{settings.FRONTEND_URL}/auth/verify-email"
                    },
                )

                # Update timestamp
                supabase.rpc(
                    "update_verification_token_sent", {"user_id": user["id"]}
                ).execute()

                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send verification to {user['email']}: {e}")
                failed_count += 1
                failed_users.append({"email": user["email"], "error": str(e)})

        logger.info(
            f"Admin {current_user['email']} sent bulk verification emails: {sent_count} sent, {failed_count} failed"
        )

        return {
            "success": True,
            "sent": sent_count,
            "failed": failed_count,
            "failed_users": failed_users if failed_users else None,
        }
    except Exception as e:
        logger.error(f"Error sending bulk verification emails: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to send verification emails"
        )


@router.get("/users/verification-stats")
async def get_verification_statistics(
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get statistics about email verification"""
    try:
        # Total users
        total_response = (
            supabase.table("profiles").select("id", count="exact").execute()
        )
        total_users = total_response.count

        # Verified users
        verified_response = (
            supabase.table("profiles")
            .select("id", count="exact")
            .eq("email_verified", True)
            .execute()
        )
        verified_users = verified_response.count

        # Unverified users
        unverified_users = total_users - verified_users

        # Users who verified within 24 hours
        quick_verify_response = supabase.rpc(
            "count",
            {
                "table_name": "profiles",
                "where_clause": "email_verified = true AND (email_verified_at - created_at) < interval '24 hours'",
            },
        ).execute()

        verification_rate = (
            (verified_users / total_users * 100) if total_users > 0 else 0
        )

        return {
            "total_users": total_users,
            "verified_users": verified_users,
            "unverified_users": unverified_users,
            "verification_rate": round(verification_rate, 2),
            "verified_within_24h": (
                quick_verify_response.data
                if hasattr(quick_verify_response, "data")
                else 0
            ),
        }
    except Exception as e:
        logger.error(f"Error fetching verification statistics: {e}")
        # Return basic stats if advanced query fails
        total_response = (
            supabase.table("profiles").select("id", count="exact").execute()
        )
        verified_response = (
            supabase.table("profiles")
            .select("id", count="exact")
            .eq("email_verified", True)
            .execute()
        )

        total_users = total_response.count
        verified_users = verified_response.count
        verification_rate = (
            (verified_users / total_users * 100) if total_users > 0 else 0
        )

        return {
            "total_users": total_users,
            "verified_users": verified_users,
            "unverified_users": total_users - verified_users,
            "verification_rate": round(verification_rate, 2),
        }


# User Role Management Endpoints
class AddRoleToUserRequest(BaseModel):
    user_id: str
    role: str = Field(..., pattern="^(explorer|creator|admin|superadmin)$")


class RemoveRoleFromUserRequest(BaseModel):
    user_id: str
    role: str = Field(..., pattern="^(explorer|creator|admin|superadmin)$")


@router.get("/users/list")
async def list_all_users(
    limit: int = Query(50, description="Maximum number of users to return"),
    offset: int = Query(0, description="Pagination offset"),
    search: Optional[str] = Query(None, description="Search by email or display name"),
    role_filter: Optional[str] = Query(None, description="Filter by role"),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get list of all users with their roles"""
    try:
        query = supabase.table("profiles").select(
            "id, email, display_name, roles, email_verified, created_at, updated_at"
        )

        # Apply search filter if provided
        if search:
            query = query.or_(f"email.ilike.%{search}%,display_name.ilike.%{search}%")

        # Apply role filter if provided
        if role_filter:
            query = query.contains("roles", [role_filter])

        # Apply pagination
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

        response = query.execute()

        # Get total count
        count_query = supabase.table("profiles").select("id", count="exact")
        if search:
            count_query = count_query.or_(
                f"email.ilike.%{search}%,display_name.ilike.%{search}%"
            )
        if role_filter:
            count_query = count_query.contains("roles", [role_filter])

        count_response = count_query.execute()

        return {
            "users": response.data,
            "total": count_response.count,
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
    supabase: Client = Depends(get_supabase),
):
    """Get detailed information about a specific user"""
    try:
        response = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .maybeSingle()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")

        return {"user": response.data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user details")


@router.get("/users/{user_id}/roles")
async def get_user_roles(
    user_id: str,
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get roles for a specific user"""
    try:
        response = (
            supabase.table("profiles")
            .select("id, email, display_name, roles")
            .eq("id", user_id)
            .maybeSingle()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "user_id": response.data["id"],
            "email": response.data["email"],
            "display_name": response.data["display_name"],
            "roles": response.data["roles"],
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
    supabase: Client = Depends(get_supabase),
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
        user_response = (
            supabase.table("profiles")
            .select("id, email, display_name, roles")
            .eq("id", request.user_id)
            .maybeSingle()
            .execute()
        )

        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if user already has the role
        if request.role in user_response.data["roles"]:
            return {
                "success": True,
                "message": f"User already has the {request.role} role",
                "user": user_response.data,
            }

        # Use the database function to add role
        supabase.rpc(
            "add_role_to_user", {"user_id": request.user_id, "new_role": request.role}
        ).execute()

        # Fetch updated user data
        updated_user = (
            supabase.table("profiles")
            .select("id, email, display_name, roles")
            .eq("id", request.user_id)
            .maybeSingle()
            .execute()
        )

        logger.info(
            f"Admin {current_user['email']} added role '{request.role}' to user {user_response.data['email']}"
        )

        return {
            "success": True,
            "message": f"Successfully added {request.role} role to user",
            "user": updated_user.data,
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
    supabase: Client = Depends(get_supabase),
):
    """Remove a role from a user"""
    try:
        # Prevent removing superadmin role from primary superadmin
        user_response = (
            supabase.table("profiles")
            .select("id, email, display_name, roles")
            .eq("id", request.user_id)
            .maybeSingle()
            .execute()
        )

        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")

        if (
            request.role == "superadmin"
            and user_response.data["email"] == "support@litinkai.com"
        ):
            raise HTTPException(
                status_code=403,
                detail="Cannot remove superadmin role from primary superadmin account",
            )

        # Check if user has the role
        if request.role not in user_response.data["roles"]:
            return {
                "success": True,
                "message": f"User does not have the {request.role} role",
                "user": user_response.data,
            }

        # Use the database function to remove role
        try:
            supabase.rpc(
                "remove_role_from_user",
                {"user_id": request.user_id, "role_to_remove": request.role},
            ).execute()
        except Exception as e:
            if "Cannot remove last role" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail="Cannot remove last role from user. User must have at least one role.",
                )
            raise

        # Fetch updated user data
        updated_user = (
            supabase.table("profiles")
            .select("id, email, display_name, roles")
            .eq("id", request.user_id)
            .maybeSingle()
            .execute()
        )

        logger.info(
            f"Admin {current_user['email']} removed role '{request.role}' from user {user_response.data['email']}"
        )

        return {
            "success": True,
            "message": f"Successfully removed {request.role} role from user",
            "user": updated_user.data,
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
                "description": "Can moderate content and manage users (except superadmin)",
            },
            {
                "value": "superadmin",
                "label": "Superadmin",
                "description": "Full system access including user role management",
            },
        ]
    }


# User Deletion Endpoints
@router.get("/users/{user_id}/deletion-preview")
async def get_user_deletion_preview(
    user_id: str,
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Get preview of what will be deleted if user is removed"""
    try:
        # Call the database function to get deletion preview
        response = supabase.rpc(
            "get_user_deletion_preview", {"target_user_id": user_id}
        ).execute()

        if not response.data:
            raise HTTPException(
                status_code=404, detail="User not found or preview unavailable"
            )

        return response.data
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting deletion preview for user {user_id}: {error_msg}")

        # Handle specific errors
        if "User not found" in error_msg:
            raise HTTPException(status_code=404, detail="User not found")
        if "Cannot delete primary superadmin" in error_msg:
            raise HTTPException(
                status_code=403, detail="Cannot delete primary superadmin account"
            )

        raise HTTPException(
            status_code=500, detail=f"Failed to get deletion preview: {error_msg}"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase),
):
    """Permanently delete a user and all their content"""
    try:
        # Call the database function to delete user
        response = supabase.rpc(
            "delete_user_completely",
            {
                "target_user_id": user_id,
                "deleting_admin_id": current_user["id"],
                "deletion_reason": reason,
            },
        ).execute()

        if not response.data:
            raise HTTPException(
                status_code=500, detail="Deletion failed: No response from database"
            )

        result = response.data

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
    supabase: Client = Depends(get_supabase),
):
    """Delete multiple users at once"""
    if not request.user_ids:
        raise HTTPException(status_code=400, detail="No user IDs provided")

    results = {"total": len(request.user_ids), "successful": [], "failed": []}

    for user_id in request.user_ids:
        try:
            # Call the database function to delete user
            response = supabase.rpc(
                "delete_user_completely",
                {
                    "target_user_id": user_id,
                    "deleting_admin_id": current_user["id"],
                    "deletion_reason": request.reason or "Batch deletion",
                },
            ).execute()

            if response.data and response.data.get("success"):
                results["successful"].append(
                    {
                        "user_id": user_id,
                        "email": response.data.get("deleted_email"),
                        "audit_id": response.data.get("audit_id"),
                    }
                )
                logger.info(
                    f"Batch deletion: User {response.data.get('deleted_email')} deleted"
                )
            else:
                error_msg = (
                    response.data.get("error", "Unknown error")
                    if response.data
                    else "No response"
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
    supabase: Client = Depends(get_supabase),
):
    """Get audit log of deleted users"""
    try:
        query = (
            supabase.table("deleted_users_audit")
            .select(
                "id, original_user_id, email, display_name, roles, user_created_at, deleted_at, deletion_reason, content_summary, deleted_by"
            )
            .order("deleted_at", desc=True)
            .range(offset, offset + limit - 1)
        )

        response = query.execute()

        # Get total count
        count_response = (
            supabase.table("deleted_users_audit").select("id", count="exact").execute()
        )

        return {
            "audit_logs": response.data,
            "total": count_response.count,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Error fetching deletion audit log: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch deletion audit log"
        )
