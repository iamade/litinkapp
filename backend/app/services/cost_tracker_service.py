"""
Cost Tracker Service
Aggregates and analyzes cost data from model usage tracking
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from supabase import Client
from app.core.database import get_supabase


class CostTrackerService:
    """Service for tracking and analyzing AI model costs"""

    # Model cost per 1M tokens or per generation (approximate USD)
    MODEL_COSTS = {
        # LLM Models (per 1M tokens)
        "openai/gpt-4o": {"input": 2.50, "output": 10.00},
        "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "anthropic/claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
        "anthropic/claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        "openai/gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "deepseek-chat-v3-0324:free": {"input": 0.00, "output": 0.00},
        "arliai/qwq-32b-arliai-rpr-v1:free": {"input": 0.00, "output": 0.00},
        "meta-llama/llama-3.2-3b-instruct": {"input": 0.06, "output": 0.06},
        "mistralai/mistral-7b-instruct": {"input": 0.07, "output": 0.07},

        # Image Models (per generation)
        "runway_image": 0.05,
        "gen4_image": 0.03,
        "nano-banana": 0.01,

        # Video Models (per second of video)
        "veo2_pro": 0.15,
        "veo2": 0.08,
        "seedance-i2v": 0.05,

        # Audio Models (per minute)
        "eleven_multilingual_v2": 0.30,
        "eleven_turbo_v2": 0.20,
        "eleven_english_v1": 0.15,
    }

    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def get_cost_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get overall cost summary"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Get usage from multiple tables
        script_costs = await self._get_script_costs(start_date, end_date)
        image_costs = await self._get_image_costs(start_date, end_date)
        video_costs = await self._get_video_costs(start_date, end_date)
        audio_costs = await self._get_audio_costs(start_date, end_date)

        total_cost = script_costs["total"] + image_costs["total"] + video_costs["total"] + audio_costs["total"]
        total_savings = script_costs["savings"] + image_costs["savings"] + video_costs["savings"] + audio_costs["savings"]

        return {
            "total_cost": round(total_cost, 2),
            "total_savings": round(total_savings, 2),
            "cost_by_service": {
                "script_generation": round(script_costs["total"], 2),
                "image_generation": round(image_costs["total"], 2),
                "video_generation": round(video_costs["total"], 2),
                "audio_generation": round(audio_costs["total"], 2),
            },
            "savings_by_service": {
                "script_generation": round(script_costs["savings"], 2),
                "image_generation": round(image_costs["savings"], 2),
                "video_generation": round(video_costs["savings"], 2),
                "audio_generation": round(audio_costs["savings"], 2),
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

    async def get_cost_by_tier(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get cost breakdown by subscription tier"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Query usage_logs table grouped by tier
        query = self.supabase.table("usage_logs").select(
            "user_id, metadata, cost_usd, created_at"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())

        response = query.execute()

        tier_costs = {}
        for record in response.data:
            metadata = record.get("metadata", {})
            tier = metadata.get("user_tier", "unknown")
            cost = record.get("cost_usd", 0) or 0

            if tier not in tier_costs:
                tier_costs[tier] = {"tier": tier, "total_cost": 0, "count": 0}

            tier_costs[tier]["total_cost"] += cost
            tier_costs[tier]["count"] += 1

        result = []
        for tier_data in tier_costs.values():
            tier_data["total_cost"] = round(tier_data["total_cost"], 2)
            tier_data["average_cost_per_operation"] = round(
                tier_data["total_cost"] / tier_data["count"] if tier_data["count"] > 0 else 0, 4
            )
            result.append(tier_data)

        return sorted(result, key=lambda x: x["total_cost"], reverse=True)

    async def _get_script_costs(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Calculate script generation costs"""
        # Query plot_overviews for model usage
        query = self.supabase.table("plot_overviews").select(
            "model_used, generation_cost, created_at"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())

        response = query.execute()

        total_cost = sum(record.get("generation_cost", 0) or 0 for record in response.data)

        # Estimate savings (simplified - would need more data in production)
        savings = total_cost * 0.15  # Assume 15% savings from fallbacks

        return {"total": total_cost, "savings": savings}

    async def _get_image_costs(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Calculate image generation costs"""
        query = self.supabase.table("image_generations").select(
            "model_id, metadata, created_at"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat()).eq("status", "completed")

        response = query.execute()

        total_cost = 0
        intended_cost = 0

        for record in response.data:
            model_used = record.get("model_id", "gen4_image")
            metadata = record.get("metadata", {})

            # Get actual cost
            actual_model_cost = self.MODEL_COSTS.get(model_used, 0.03)
            total_cost += actual_model_cost

            # Get intended cost if available
            intended_model = metadata.get("model_used_primary")
            if intended_model:
                intended_cost += self.MODEL_COSTS.get(intended_model, actual_model_cost)
            else:
                intended_cost += actual_model_cost

        savings = max(0, intended_cost - total_cost)

        return {"total": total_cost, "savings": savings}

    async def _get_video_costs(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Calculate video generation costs"""
        query = self.supabase.table("video_segments").select(
            "processing_model, duration_seconds, metadata, created_at"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat()).eq("status", "completed")

        response = query.execute()

        total_cost = 0
        intended_cost = 0

        for record in response.data:
            model_used = record.get("processing_model", "veo2")
            duration = record.get("duration_seconds", 5)
            metadata = record.get("metadata", {})

            # Get actual cost (per second)
            cost_per_second = self.MODEL_COSTS.get(model_used, 0.08)
            total_cost += cost_per_second * duration

            # Get intended cost if available
            intended_model = metadata.get("model_used_primary")
            if intended_model:
                intended_cost += self.MODEL_COSTS.get(intended_model, cost_per_second) * duration
            else:
                intended_cost += cost_per_second * duration

        savings = max(0, intended_cost - total_cost)

        return {"total": total_cost, "savings": savings}

    async def _get_audio_costs(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Calculate audio generation costs"""
        query = self.supabase.table("audio_generations").select(
            "voice_model, duration_seconds, metadata, created_at"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat()).eq("status", "completed")

        response = query.execute()

        total_cost = 0
        intended_cost = 0

        for record in response.data:
            model_used = record.get("voice_model", "eleven_turbo_v2")
            duration = record.get("duration_seconds", 10)
            metadata = record.get("metadata", {})

            # Convert to minutes and get cost
            duration_minutes = duration / 60
            cost_per_minute = self.MODEL_COSTS.get(model_used, 0.20)
            total_cost += cost_per_minute * duration_minutes

            # Get intended cost if available
            intended_model = metadata.get("model_used_primary")
            if intended_model:
                intended_cost += self.MODEL_COSTS.get(intended_model, cost_per_minute) * duration_minutes
            else:
                intended_cost += cost_per_minute * duration_minutes

        savings = max(0, intended_cost - total_cost)

        return {"total": total_cost, "savings": savings}

    async def get_daily_costs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get daily cost breakdown"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Query usage_logs for daily aggregation
        query = self.supabase.table("usage_logs").select(
            "created_at, cost_usd, resource_type"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())

        response = query.execute()

        # Group by date
        daily_data = {}
        for record in response.data:
            date_str = record["created_at"][:10]  # YYYY-MM-DD
            cost = record.get("cost_usd", 0) or 0

            if date_str not in daily_data:
                daily_data[date_str] = {"date": date_str, "total_cost": 0, "operations": 0}

            daily_data[date_str]["total_cost"] += cost
            daily_data[date_str]["operations"] += 1

        result = []
        for data in daily_data.values():
            data["total_cost"] = round(data["total_cost"], 2)
            result.append(data)

        return sorted(result, key=lambda x: x["date"])

    async def get_cost_predictions(self) -> Dict[str, Any]:
        """Predict future costs based on usage patterns"""
        # Get last 30 days of data
        thirty_days_ago = datetime.now() - timedelta(days=30)
        daily_costs = await self.get_daily_costs(start_date=thirty_days_ago)

        if not daily_costs:
            return {
                "predicted_monthly_cost": 0,
                "confidence": "low",
                "trend": "insufficient_data",
            }

        # Calculate average daily cost
        total_cost = sum(day["total_cost"] for day in daily_costs)
        avg_daily_cost = total_cost / len(daily_costs)

        # Project to monthly
        predicted_monthly = avg_daily_cost * 30

        # Calculate trend
        if len(daily_costs) >= 7:
            recent_week = daily_costs[-7:]
            prev_week = daily_costs[-14:-7] if len(daily_costs) >= 14 else daily_costs[:7]

            recent_avg = sum(day["total_cost"] for day in recent_week) / len(recent_week)
            prev_avg = sum(day["total_cost"] for day in prev_week) / len(prev_week)

            if recent_avg > prev_avg * 1.2:
                trend = "increasing"
            elif recent_avg < prev_avg * 0.8:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "unknown"

        return {
            "predicted_monthly_cost": round(predicted_monthly, 2),
            "average_daily_cost": round(avg_daily_cost, 2),
            "trend": trend,
            "confidence": "high" if len(daily_costs) >= 20 else "medium",
            "data_points": len(daily_costs),
        }
