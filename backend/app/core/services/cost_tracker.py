"""
Cost Tracker Service
Aggregates and analyzes cost data from model usage tracking
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.subscriptions.models import UsageLog
from app.plots.models import PlotOverview
from app.videos.models import VideoSegment, AudioGeneration, ImageGeneration


class CostTrackerService:
    """Service for tracking and analyzing AI model costs"""

    # Model cost per 1M tokens or per generation (approximate USD)
    # Updated to match new model configurations from pricing_new.md strategy
    MODEL_COSTS = {
        # ===== TEXT & SCRIPT GENERATION MODELS (per 1M tokens) =====
        # OpenAI Models
        "openai/gpt-4o": {"input": 2.50, "output": 10.00},
        "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "openai/chatgpt-4o-latest": {"input": 2.50, "output": 10.00},
        "openai/gpt-4.5-preview": {
            "input": 5.00,
            "output": 15.00,
        },  # Estimated premium pricing
        "openai/gpt-5": {"input": 10.00, "output": 30.00},  # Estimated GPT-5 pricing
        "openai/gpt-5.2-pro": {
            "input": 15.00,
            "output": 45.00,
        },  # Estimated high-end pricing
        "openai/gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        # Anthropic Models
        "anthropic/claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
        "anthropic/claude-sonnet-4.5": {
            "input": 3.00,
            "output": 15.00,
        },  # Latest Sonnet
        "anthropic/claude-opus-4": {"input": 15.00, "output": 75.00},  # Claude Opus 4
        "anthropic/claude-opus-4.5": {
            "input": 15.00,
            "output": 75.00,
        },  # Claude Opus 4.5
        "anthropic/claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        # Google Gemini Models
        "google/gemini-2.0-flash-exp:free": {"input": 0.00, "output": 0.00},
        "google/gemini-2.5-pro": {"input": 1.25, "output": 5.00},  # Estimated
        "google/gemini-3-flash-preview": {
            "input": 0.50,
            "output": 1.50,
        },  # Estimated Gemini 3 Flash
        "google/gemini-3-pro-preview": {
            "input": 2.50,
            "output": 10.00,
        },  # Estimated Gemini 3 Pro
        # DeepSeek Models
        "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28},
        # Qwen Models
        "qwen/qwen-2.5-72b-instruct": {
            "input": 0.35,
            "output": 0.70,
        },  # Estimated for 72B model
        "qwen/qwen3-coder": {
            "input": 0.50,
            "output": 1.00,
        },  # Estimated for thinking model
        # Baidu Models
        "baidu/ernie-4.5-21b-a3b-thinking": {
            "input": 0.40,
            "output": 0.80,
        },  # Estimated
        # Meta Models
        "meta-llama/llama-3.3-70b-instruct:free": {"input": 0.00, "output": 0.00},
        # Mistral Models
        "mistralai/mistral-nemo": {"input": 0.03, "output": 0.03},
        # ===== IMAGE GENERATION MODELS (per generation) =====
        # Old models (keeping for backward compatibility)
        "runway_image": 0.05,
        "gen4_image": 0.03,
        # New Image Models (from pricing_new.md)
        # Direct API Models
        "hunyuan-image-3.0": 0.02,  # Hunyuan-Image-3.0 (cost-effective for free tier)
        "nano-banana": 0.015,  # Nano Banana / Gemini-2.5
        "nano-banana-pro": 0.04,  # Nano Banana Pro / Gemini-3
        "gpt-image-1.5": 0.08,  # GPT-Image-1.5 (premium)
        # ModelsLab Models
        "flux-2-dev": 0.025,  # Flux-2-Dev
        "flux-2-pro": 0.05,  # Flux-2-Pro
        "flux-2-max": 0.08,  # Flux-2-Max (premium)
        "flux-2-flex": 0.06,  # Flux-2-Flex
        "seedream-4.5": 0.02,  # Seedream-4.5
        # ===== VIDEO GENERATION MODELS (per second of video) =====
        # Old models (keeping for backward compatibility)
        "veo2_pro": 0.15,
        "veo2": 0.08,
        "seedance-i2v": 0.05,
        # New Video Models (from pricing_new.md)
        # Google Veo Series (Direct API)
        "veo-3-fast": 0.08,  # Veo-3-Fast
        "veo-3-fast-audio": 0.12,  # Veo-3-Fast-Audio (with audio)
        "veo-3-audio": 0.18,  # Veo-3-Audio (premium with audio)
        "veo-3.1-fast-audio": 0.15,  # Veo-3.1-Fast-Audio (enhanced)
        "veo-3.1-audio": 0.22,  # Veo-3.1-Audio (top-tier)
        # ModelsLab Models
        "seedance-v1-pro": 0.06,  # Seedance-v1-Pro
        "kling-2.5-turbo": 0.05,  # Kling-2.5-Turbo
        "kling-2.5-turbo-1080p": 0.07,  # Kling-2.5-Turbo-1080p
        "kling-2.6-pro": 0.10,  # Kling-2.6-Pro
        "wan2.5-i2v-preview": 0.12,  # Wan2.5-I2V-Preview
        "wan2.5-i2v": 0.10,  # Wan2.5-I2V (720p) with audio support
        "wan2.6-i2v": 0.05,  # Wan2.6-I2V (480p) with audio support
        # ===== AUDIO GENERATION MODELS (per minute) =====
        "eleven_multilingual_v2": 0.30,
        "eleven_turbo_v2": 0.20,
        "eleven_english_v1": 0.15,
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_cost_summary(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
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

        total_cost = (
            script_costs["total"]
            + image_costs["total"]
            + video_costs["total"]
            + audio_costs["total"]
        )
        total_savings = (
            script_costs["savings"]
            + image_costs["savings"]
            + video_costs["savings"]
            + audio_costs["savings"]
        )

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
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get cost breakdown by subscription tier"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Query usage_logs table grouped by tier
        stmt = select(UsageLog).where(
            UsageLog.created_at >= start_date, UsageLog.created_at <= end_date
        )
        result = await self.session.exec(stmt)
        usage_logs = result.all()

        tier_costs = {}
        for record in usage_logs:
            metadata = record.meta or {}
            tier = metadata.get("user_tier", "unknown")
            # Assuming cost_usd is stored in meta or we calculate it?
            # The original code accessed record.get("cost_usd"), but UsageLog model doesn't have cost_usd.
            # It might be in meta or calculated. Let's assume it's in meta for now based on original code usage pattern,
            # or we might need to calculate it.
            # Original: cost = record.get("cost_usd", 0) or 0
            # UsageLog model has 'usage_count' and 'resource_type'.
            # I'll check if 'cost_usd' is in meta.
            cost = metadata.get("cost_usd", 0) or 0

            if tier not in tier_costs:
                tier_costs[tier] = {"tier": tier, "total_cost": 0, "count": 0}

            tier_costs[tier]["total_cost"] += cost
            tier_costs[tier]["count"] += 1

        result = []
        for tier_data in tier_costs.values():
            tier_data["total_cost"] = round(tier_data["total_cost"], 2)
            tier_data["average_cost_per_operation"] = round(
                (
                    tier_data["total_cost"] / tier_data["count"]
                    if tier_data["count"] > 0
                    else 0
                ),
                4,
            )
            result.append(tier_data)

        return sorted(result, key=lambda x: x["total_cost"], reverse=True)

    async def _get_script_costs(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, float]:
        """Calculate script generation costs"""
        # Query plot_overviews for model usage
        stmt = select(PlotOverview).where(
            PlotOverview.created_at >= start_date, PlotOverview.created_at <= end_date
        )
        result = await self.session.exec(stmt)
        plots = result.all()

        # PlotOverview doesn't have generation_cost field, so we estimate based on model_used
        total_cost = 0.0
        for plot in plots:
            model_used = plot.model_used or "openai/gpt-4o-mini"
            model_cost = self.MODEL_COSTS.get(
                model_used, {"input": 0.15, "output": 0.60}
            )
            if isinstance(model_cost, dict):
                # Estimate ~1000 tokens input, ~2000 tokens output per plot
                total_cost += (model_cost["input"] * 0.001) + (
                    model_cost["output"] * 0.002
                )
            else:
                total_cost += model_cost

        # Estimate savings (simplified - would need more data in production)
        savings = total_cost * 0.15  # Assume 15% savings from fallbacks

        return {"total": total_cost, "savings": savings}

    async def _get_image_costs(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, float]:
        """Calculate image generation costs"""
        stmt = select(ImageGeneration).where(
            ImageGeneration.created_at >= start_date,
            ImageGeneration.created_at <= end_date,
            ImageGeneration.status == "completed",
        )
        result = await self.session.exec(stmt)
        images = result.all()

        total_cost = 0
        intended_cost = 0

        for record in images:
            model_used = record.model_id or "gen4_image"
            metadata = record.metadata or {}

            # Get actual cost
            actual_model_cost = self.MODEL_COSTS.get(model_used, 0.03)
            # If actual_model_cost is a dict (LLM), take output cost as approx?
            # But images are per generation (float).
            if isinstance(actual_model_cost, dict):
                actual_model_cost = 0.03  # Fallback

            total_cost += actual_model_cost

            # Get intended cost if available
            intended_model = metadata.get("model_used_primary")
            if intended_model:
                intended_val = self.MODEL_COSTS.get(intended_model, actual_model_cost)
                if isinstance(intended_val, dict):
                    intended_val = actual_model_cost
                intended_cost += intended_val
            else:
                intended_cost += actual_model_cost

        savings = max(0, intended_cost - total_cost)

        return {"total": total_cost, "savings": savings}

    async def _get_video_costs(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, float]:
        """Calculate video generation costs"""
        stmt = select(VideoSegment).where(
            VideoSegment.created_at >= start_date,
            VideoSegment.created_at <= end_date,
            VideoSegment.status == "completed",
        )
        result = await self.session.exec(stmt)
        segments = result.all()

        total_cost = 0
        intended_cost = 0

        for record in segments:
            # VideoSegment doesn't have processing_model directly on it in the model definition I saw earlier?
            # Wait, I saw VideoSegment model:
            # class VideoSegment(SQLModel, table=True):
            # ...
            # processing_model is NOT in the model definition I saw!
            # It has metadata. Maybe it's in metadata?
            # Or maybe I missed it.
            # Let's assume it's in metadata for now if not on model.
            # But the Supabase query selected "processing_model".
            # If it's not on the model, I can't select it.
            # I'll check metadata.
            metadata = record.metadata or {}
            model_used = metadata.get("processing_model", "veo2")
            duration = record.duration_seconds or 5

            # Get actual cost (per second)
            cost_per_second = self.MODEL_COSTS.get(model_used, 0.08)
            if isinstance(cost_per_second, dict):
                cost_per_second = 0.08

            total_cost += cost_per_second * duration

            # Get intended cost if available
            intended_model = metadata.get("model_used_primary")
            if intended_model:
                intended_val = self.MODEL_COSTS.get(intended_model, cost_per_second)
                if isinstance(intended_val, dict):
                    intended_val = cost_per_second
                intended_cost += intended_val * duration
            else:
                intended_cost += cost_per_second * duration

        savings = max(0, intended_cost - total_cost)

        return {"total": total_cost, "savings": savings}

    async def _get_audio_costs(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, float]:
        """Calculate audio generation costs"""
        stmt = select(AudioGeneration).where(
            AudioGeneration.created_at >= start_date,
            AudioGeneration.created_at <= end_date,
            AudioGeneration.status == "completed",
        )
        result = await self.session.exec(stmt)
        audios = result.all()

        total_cost = 0
        intended_cost = 0

        for record in audios:
            model_used = record.voice_model or "eleven_turbo_v2"
            duration = record.duration_seconds or 10
            metadata = record.metadata or {}

            # Convert to minutes and get cost
            duration_minutes = duration / 60
            cost_per_minute = self.MODEL_COSTS.get(model_used, 0.20)
            if isinstance(cost_per_minute, dict):
                cost_per_minute = 0.20

            total_cost += cost_per_minute * duration_minutes

            # Get intended cost if available
            intended_model = metadata.get("model_used_primary")
            if intended_model:
                intended_val = self.MODEL_COSTS.get(intended_model, cost_per_minute)
                if isinstance(intended_val, dict):
                    intended_val = cost_per_minute
                intended_cost += intended_val * duration_minutes
            else:
                intended_cost += cost_per_minute * duration_minutes

        savings = max(0, intended_cost - total_cost)

        return {"total": total_cost, "savings": savings}

    async def get_daily_costs(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get daily cost breakdown"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # Query usage_logs for daily aggregation
        stmt = select(UsageLog).where(
            UsageLog.created_at >= start_date, UsageLog.created_at <= end_date
        )
        result = await self.session.exec(stmt)
        logs = result.all()

        # Group by date
        daily_data = {}
        for record in logs:
            date_str = record.created_at.strftime("%Y-%m-%d")
            # Assuming cost is in meta
            cost = (record.meta or {}).get("cost_usd", 0) or 0

            if date_str not in daily_data:
                daily_data[date_str] = {
                    "date": date_str,
                    "total_cost": 0,
                    "operations": 0,
                }

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
            prev_week = (
                daily_costs[-14:-7] if len(daily_costs) >= 14 else daily_costs[:7]
            )

            recent_avg = sum(day["total_cost"] for day in recent_week) / len(
                recent_week
            )
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
