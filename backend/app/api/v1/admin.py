"""
Admin API Endpoints
Superadmin-only endpoints for cost tracking, metrics, and system monitoring
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client
from pydantic import BaseModel

from app.core.auth import get_current_superadmin
from app.core.database import get_supabase
from app.services.cost_tracker_service import CostTrackerService
from app.services.metrics_service import MetricsService
from app.services.alert_service import AlertService


router = APIRouter(prefix="/admin", tags=["admin"])


# Pydantic models for request/response
class AlertSettingsUpdate(BaseModel):
    high_fallback_rate: Optional[float] = None
    cost_spike_percentage: Optional[float] = None
    circuit_breaker_enabled: Optional[bool] = None
    low_success_rate: Optional[float] = None


class AcknowledgeAlertRequest(BaseModel):
    alert_id: str


# Cost Tracking Endpoints
@router.get("/cost-tracking/summary")
async def get_cost_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase)
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
    supabase: Client = Depends(get_supabase)
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
    supabase: Client = Depends(get_supabase)
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
    supabase: Client = Depends(get_supabase)
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
    supabase: Client = Depends(get_supabase)
):
    """Get fallback rates by tier and service"""
    metrics_service = MetricsService(supabase)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    fallback_rates = await metrics_service.get_fallback_rates(start_date=start, end_date=end)
    return fallback_rates


@router.get("/metrics/model-performance")
async def get_model_performance(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase)
):
    """Get performance metrics for all models"""
    metrics_service = MetricsService(supabase)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    performance = await metrics_service.get_model_performance(start_date=start, end_date=end)
    return {"models": performance}


@router.get("/metrics/circuit-breaker-status")
async def get_circuit_breaker_status(
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase)
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
    supabase: Client = Depends(get_supabase)
):
    """Get model usage distribution by service"""
    metrics_service = MetricsService(supabase)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    distribution = await metrics_service.get_model_usage_distribution(start_date=start, end_date=end)
    return distribution


@router.get("/metrics/generation-times")
async def get_generation_times(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase)
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
    supabase: Client = Depends(get_supabase)
):
    """Get system health check with model availability"""
    metrics_service = MetricsService(supabase)
    health = await metrics_service.get_health_check()
    return health


# Alert Endpoints
@router.get("/alerts/recent")
async def get_recent_alerts(
    hours: int = Query(24, description="Number of hours to look back"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase)
):
    """Get recent alerts"""
    alert_service = AlertService(supabase)
    alerts = await alert_service.get_recent_alerts(hours=hours, acknowledged=acknowledged)
    return {"alerts": alerts}


@router.get("/alerts/statistics")
async def get_alert_statistics(
    days: int = Query(7, description="Number of days for statistics"),
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase)
):
    """Get alert statistics"""
    alert_service = AlertService(supabase)
    stats = await alert_service.get_alert_statistics(days=days)
    return stats


@router.post("/alerts/acknowledge")
async def acknowledge_alert(
    request: AcknowledgeAlertRequest,
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase)
):
    """Acknowledge an alert"""
    alert_service = AlertService(supabase)
    result = await alert_service.acknowledge_alert(
        alert_id=request.alert_id,
        user_id=current_user["id"]
    )
    return {"success": True, "alert": result}


@router.post("/alerts/check")
async def run_alert_check(
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase)
):
    """Manually trigger alert check (usually runs on schedule)"""
    alert_service = AlertService(supabase)
    alerts = await alert_service.check_all_alerts()
    return {"alerts_created": len(alerts), "alerts": alerts}


@router.get("/alerts/settings")
async def get_alert_settings(
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase)
):
    """Get current alert threshold settings"""
    alert_service = AlertService(supabase)
    settings = await alert_service.get_alert_settings()
    return {"settings": settings}


@router.put("/alerts/settings")
async def update_alert_settings(
    settings: AlertSettingsUpdate,
    current_user: dict = Depends(get_current_superadmin),
    supabase: Client = Depends(get_supabase)
):
    """Update alert threshold settings"""
    alert_service = AlertService(supabase)

    # Get current settings and merge with updates
    current_settings = await alert_service.get_alert_settings()

    update_dict = settings.dict(exclude_unset=True)
    merged_settings = {**current_settings, **update_dict}

    result = await alert_service.update_alert_settings(
        settings=merged_settings,
        user_id=current_user["id"]
    )

    return {"success": True, "settings": result}
