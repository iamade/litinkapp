"""
Alert Service
Monitors system metrics and creates alerts when thresholds are exceeded
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from supabase import Client
from app.core.services.metrics import MetricsService
from app.core.services.cost_tracker import CostTrackerService
import asyncio


class AlertService:
    """Service for monitoring and alerting on system metrics"""

    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.metrics_service = MetricsService(supabase)
        self.cost_tracker_service = CostTrackerService(supabase)

    async def get_alert_settings(self) -> Dict[str, Any]:
        """Get current alert threshold settings"""
        query = (
            self.supabase.table("admin_settings")
            .select("*")
            .eq("setting_key", "alert_thresholds")
            .maybeSingle()
        )

        response = query.execute()

        if response.data:
            return response.data["setting_value"]

        # Return defaults if not found
        return {
            "high_fallback_rate": 30,
            "cost_spike_percentage": 50,
            "circuit_breaker_enabled": True,
            "low_success_rate": 80,
        }

    async def check_all_alerts(self) -> List[Dict[str, Any]]:
        """Check all alert conditions and create alerts if needed"""
        settings = await self.get_alert_settings()
        alerts = []

        # Check fallback rates
        fallback_alerts = await self.check_high_fallback_rates(
            settings["high_fallback_rate"]
        )
        alerts.extend(fallback_alerts)

        # Check cost spikes
        cost_alerts = await self.check_cost_spikes(settings["cost_spike_percentage"])
        alerts.extend(cost_alerts)

        # Check model success rates
        success_alerts = await self.check_low_success_rates(
            settings["low_success_rate"]
        )
        alerts.extend(success_alerts)

        # Create alert records in database
        for alert in alerts:
            await self.create_alert(alert)

        return alerts

    async def check_high_fallback_rates(
        self, threshold: float = 30.0
    ) -> List[Dict[str, Any]]:
        """Check if any service has high fallback rates"""
        alerts = []

        # Get fallback rates for last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        fallback_data = await self.metrics_service.get_fallback_rates(
            start_date=one_hour_ago
        )

        # Check each service
        services = [
            "script_generation",
            "image_generation",
            "video_generation",
            "audio_generation",
        ]

        for service in services:
            service_data = fallback_data.get(service, {})
            fallback_rate = service_data.get("fallback_rate", 0)

            if fallback_rate > threshold:
                severity = "critical" if fallback_rate > 50 else "warning"

                alerts.append(
                    {
                        "alert_type": "high_fallback_rate",
                        "severity": severity,
                        "message": f"{service.replace('_', ' ').title()} has high fallback rate: {fallback_rate}%",
                        "metric_value": fallback_rate,
                        "threshold_value": threshold,
                        "metadata": {
                            "service": service,
                            "total_operations": service_data.get("total_operations", 0),
                            "fallback_count": service_data.get("fallback_count", 0),
                            "period": "last_hour",
                        },
                    }
                )

        # Check overall rate
        overall_rate = fallback_data["overall_summary"]["overall_fallback_rate"]
        if overall_rate > threshold:
            severity = "critical" if overall_rate > 50 else "warning"

            alerts.append(
                {
                    "alert_type": "high_fallback_rate",
                    "severity": severity,
                    "message": f"Overall system fallback rate is high: {overall_rate}%",
                    "metric_value": overall_rate,
                    "threshold_value": threshold,
                    "metadata": {
                        "service": "all",
                        "total_operations": fallback_data["overall_summary"][
                            "total_operations"
                        ],
                        "total_fallbacks": fallback_data["overall_summary"][
                            "total_fallbacks"
                        ],
                        "period": "last_hour",
                    },
                }
            )

        return alerts

    async def check_cost_spikes(
        self, spike_percentage: float = 50.0
    ) -> List[Dict[str, Any]]:
        """Check for unusual cost spikes"""
        alerts = []

        # Compare today's costs to yesterday's
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)

        today_summary = await self.cost_tracker_service.get_cost_summary(
            start_date=today, end_date=datetime.now()
        )

        yesterday_summary = await self.cost_tracker_service.get_cost_summary(
            start_date=yesterday, end_date=today
        )

        today_cost = today_summary["total_cost"]
        yesterday_cost = yesterday_summary["total_cost"]

        if yesterday_cost > 0:
            cost_change = ((today_cost - yesterday_cost) / yesterday_cost) * 100

            if cost_change > spike_percentage:
                alerts.append(
                    {
                        "alert_type": "cost_spike",
                        "severity": "warning",
                        "message": f"Cost spike detected: {cost_change:.1f}% increase from yesterday",
                        "metric_value": cost_change,
                        "threshold_value": spike_percentage,
                        "metadata": {
                            "today_cost": today_cost,
                            "yesterday_cost": yesterday_cost,
                            "absolute_increase": today_cost - yesterday_cost,
                            "cost_by_service": today_summary["cost_by_service"],
                        },
                    }
                )

        return alerts

    async def check_low_success_rates(
        self, min_success_rate: float = 80.0
    ) -> List[Dict[str, Any]]:
        """Check for models with low success rates"""
        alerts = []

        # Get model performance for last 6 hours
        six_hours_ago = datetime.now() - timedelta(hours=6)
        model_performance = await self.metrics_service.get_model_performance(
            start_date=six_hours_ago
        )

        for model_data in model_performance:
            success_rate = model_data["success_rate"]
            total_attempts = model_data["total_attempts"]

            # Only alert if there are enough attempts to be significant
            if total_attempts >= 10 and success_rate < min_success_rate:
                severity = "critical" if success_rate < 50 else "warning"

                alerts.append(
                    {
                        "alert_type": "model_failure",
                        "severity": severity,
                        "message": f"Model {model_data['model']} has low success rate: {success_rate}%",
                        "metric_value": success_rate,
                        "threshold_value": min_success_rate,
                        "metadata": {
                            "model": model_data["model"],
                            "total_attempts": total_attempts,
                            "successful": model_data["successful"],
                            "failed": model_data["failed"],
                            "period": "last_6_hours",
                        },
                    }
                )

        return alerts

    async def create_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new alert in the database"""
        # Check if similar alert already exists and is unacknowledged
        existing_query = (
            self.supabase.table("admin_alerts")
            .select("*")
            .eq("alert_type", alert_data["alert_type"])
            .is_("acknowledged_at", "null")
            .gte("created_at", (datetime.now() - timedelta(hours=1)).isoformat())
        )

        existing_response = existing_query.execute()

        # If similar unacknowledged alert exists from last hour, don't create duplicate
        if existing_response.data:
            for existing in existing_response.data:
                if existing.get("metadata", {}).get("service") == alert_data.get(
                    "metadata", {}
                ).get("service"):
                    return existing

        # Create new alert
        insert_response = (
            self.supabase.table("admin_alerts")
            .insert(
                {
                    "alert_type": alert_data["alert_type"],
                    "severity": alert_data["severity"],
                    "message": alert_data["message"],
                    "metric_value": alert_data.get("metric_value"),
                    "threshold_value": alert_data.get("threshold_value"),
                    "metadata": alert_data.get("metadata", {}),
                }
            )
            .execute()
        )

        return insert_response.data[0] if insert_response.data else {}

    async def get_recent_alerts(
        self, hours: int = 24, acknowledged: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        cutoff = datetime.now() - timedelta(hours=hours)

        query = (
            self.supabase.table("admin_alerts")
            .select("*")
            .gte("created_at", cutoff.isoformat())
            .order("created_at", desc=True)
        )

        if acknowledged is not None:
            if acknowledged:
                query = query.not_.is_("acknowledged_at", "null")
            else:
                query = query.is_("acknowledged_at", "null")

        response = query.execute()
        return response.data

    async def acknowledge_alert(self, alert_id: str, user_id: str) -> Dict[str, Any]:
        """Acknowledge an alert"""
        update_response = (
            self.supabase.table("admin_alerts")
            .update(
                {
                    "acknowledged_at": datetime.now().isoformat(),
                    "acknowledged_by": user_id,
                }
            )
            .eq("id", alert_id)
            .execute()
        )

        return update_response.data[0] if update_response.data else {}

    async def get_alert_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get alert statistics for the specified period"""
        cutoff = datetime.now() - timedelta(days=days)

        query = (
            self.supabase.table("admin_alerts")
            .select("*")
            .gte("created_at", cutoff.isoformat())
        )

        response = query.execute()

        total_alerts = len(response.data)
        by_severity = {"info": 0, "warning": 0, "critical": 0}
        by_type = {}
        acknowledged_count = 0

        for alert in response.data:
            by_severity[alert["severity"]] += 1

            alert_type = alert["alert_type"]
            by_type[alert_type] = by_type.get(alert_type, 0) + 1

            if alert["acknowledged_at"]:
                acknowledged_count += 1

        return {
            "total_alerts": total_alerts,
            "by_severity": by_severity,
            "by_type": by_type,
            "acknowledged": acknowledged_count,
            "unacknowledged": total_alerts - acknowledged_count,
            "period_days": days,
        }

    async def update_alert_settings(
        self, settings: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """Update alert threshold settings"""
        # Update or insert settings
        upsert_response = (
            self.supabase.table("admin_settings")
            .upsert(
                {
                    "setting_key": "alert_thresholds",
                    "setting_value": settings,
                    "description": "Threshold values for triggering alerts",
                    "updated_at": datetime.now().isoformat(),
                    "updated_by": user_id,
                }
            )
            .execute()
        )

        return upsert_response.data[0] if upsert_response.data else {}
