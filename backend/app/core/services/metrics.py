"""
Metrics Service
Aggregates and analyzes model performance metrics, fallback rates, and system health
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from supabase import Client
from collections import defaultdict


class MetricsService:
    """Service for tracking and analyzing model performance metrics"""

    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def get_fallback_rates(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get fallback rates by tier and service"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()

        fallback_data = {
            "script_generation": await self._get_script_fallback_rates(start_date, end_date),
            "image_generation": await self._get_image_fallback_rates(start_date, end_date),
            "video_generation": await self._get_video_fallback_rates(start_date, end_date),
            "audio_generation": await self._get_audio_fallback_rates(start_date, end_date),
            "overall_summary": {},
        }

        # Calculate overall metrics
        total_operations = 0
        total_fallbacks = 0

        for service_data in [fallback_data["script_generation"], fallback_data["image_generation"],
                             fallback_data["video_generation"], fallback_data["audio_generation"]]:
            total_operations += service_data["total_operations"]
            total_fallbacks += service_data["fallback_count"]

        fallback_data["overall_summary"] = {
            "total_operations": total_operations,
            "total_fallbacks": total_fallbacks,
            "overall_fallback_rate": round(
                (total_fallbacks / total_operations * 100) if total_operations > 0 else 0, 2
            ),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

        return fallback_data

    async def _get_script_fallback_rates(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get script generation fallback rates"""
        query = self.supabase.table("plot_overviews").select(
            "model_used, generation_method, created_at"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())

        response = query.execute()

        total = len(response.data)
        fallback_count = sum(
            1 for record in response.data
            if record.get("generation_method") in ["fallback", "fallback2"]
        )

        return {
            "service": "script_generation",
            "total_operations": total,
            "fallback_count": fallback_count,
            "fallback_rate": round((fallback_count / total * 100) if total > 0 else 0, 2),
        }

    async def _get_image_fallback_rates(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get image generation fallback rates"""
        query = self.supabase.table("image_generations").select(
            "model_id, metadata, created_at"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())

        response = query.execute()

        total = len(response.data)
        fallback_count = sum(
            1 for record in response.data
            if record.get("metadata", {}).get("model_tier_used") in ["fallback", "fallback2"]
        )

        return {
            "service": "image_generation",
            "total_operations": total,
            "fallback_count": fallback_count,
            "fallback_rate": round((fallback_count / total * 100) if total > 0 else 0, 2),
        }

    async def _get_video_fallback_rates(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get video generation fallback rates"""
        query = self.supabase.table("video_segments").select(
            "processing_model, metadata, created_at"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())

        response = query.execute()

        total = len(response.data)
        fallback_count = sum(
            1 for record in response.data
            if record.get("metadata", {}).get("model_tier_used") in ["fallback", "fallback2"]
        )

        return {
            "service": "video_generation",
            "total_operations": total,
            "fallback_count": fallback_count,
            "fallback_rate": round((fallback_count / total * 100) if total > 0 else 0, 2),
        }

    async def _get_audio_fallback_rates(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get audio generation fallback rates"""
        query = self.supabase.table("audio_generations").select(
            "voice_model, metadata, created_at"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())

        response = query.execute()

        total = len(response.data)
        fallback_count = sum(
            1 for record in response.data
            if record.get("metadata", {}).get("model_tier_used") in ["fallback", "fallback2"]
        )

        return {
            "service": "audio_generation",
            "total_operations": total,
            "fallback_count": fallback_count,
            "fallback_rate": round((fallback_count / total * 100) if total > 0 else 0, 2),
        }

    async def get_model_performance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get performance metrics for all models"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()

        # Query model_performance_metrics table if it exists
        # For now, aggregate from generation tables
        model_stats = defaultdict(lambda: {
            "total_attempts": 0,
            "successful": 0,
            "failed": 0,
            "total_time": 0,
        })

        # Aggregate from image_generations
        img_query = self.supabase.table("image_generations").select(
            "model_id, status, generation_time_seconds, created_at"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())

        img_response = img_query.execute()

        for record in img_response.data:
            model = record.get("model_id", "unknown")
            status = record.get("status", "failed")
            gen_time = record.get("generation_time_seconds", 0) or 0

            model_stats[model]["total_attempts"] += 1
            if status == "completed":
                model_stats[model]["successful"] += 1
            else:
                model_stats[model]["failed"] += 1
            model_stats[model]["total_time"] += gen_time

        # Aggregate from audio_generations
        audio_query = self.supabase.table("audio_generations").select(
            "voice_model, status, generation_time_seconds, created_at"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())

        audio_response = audio_query.execute()

        for record in audio_response.data:
            model = record.get("voice_model", "unknown")
            status = record.get("status", "completed")
            gen_time = record.get("generation_time_seconds", 0) or 0

            model_stats[model]["total_attempts"] += 1
            if status == "completed":
                model_stats[model]["successful"] += 1
            else:
                model_stats[model]["failed"] += 1
            model_stats[model]["total_time"] += gen_time

        # Convert to list with calculated metrics
        result = []
        for model, stats in model_stats.items():
            success_rate = (
                round((stats["successful"] / stats["total_attempts"] * 100), 2)
                if stats["total_attempts"] > 0 else 0
            )
            avg_time = (
                round(stats["total_time"] / stats["total_attempts"], 2)
                if stats["total_attempts"] > 0 else 0
            )

            result.append({
                "model": model,
                "total_attempts": stats["total_attempts"],
                "successful": stats["successful"],
                "failed": stats["failed"],
                "success_rate": success_rate,
                "average_generation_time": avg_time,
            })

        return sorted(result, key=lambda x: x["total_attempts"], reverse=True)

    async def get_circuit_breaker_status(self) -> List[Dict[str, Any]]:
        """Get current circuit breaker status for all models"""
        # This would typically query Redis or a cache layer
        # For now, return mock data structure
        # In production, this would integrate with ModelFallbackManager's circuit breaker state

        return [
            {
                "model": "Model information not available in current implementation",
                "status": "active",
                "failure_count": 0,
                "last_failure": None,
                "blocked_until": None,
                "note": "Circuit breaker state is managed in-memory by ModelFallbackManager. "
                        "Implement Redis integration for persistent state tracking."
            }
        ]

    async def get_model_usage_distribution(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get model usage distribution by service"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()

        distribution = {
            "image_models": await self._get_image_model_distribution(start_date, end_date),
            "audio_models": await self._get_audio_model_distribution(start_date, end_date),
            "video_models": await self._get_video_model_distribution(start_date, end_date),
        }

        return distribution

    async def _get_image_model_distribution(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get image model usage distribution"""
        query = self.supabase.table("image_generations").select(
            "model_id"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())

        response = query.execute()

        model_counts = defaultdict(int)
        for record in response.data:
            model = record.get("model_id", "unknown")
            model_counts[model] += 1

        total = sum(model_counts.values())

        result = []
        for model, count in model_counts.items():
            result.append({
                "model": model,
                "count": count,
                "percentage": round((count / total * 100) if total > 0 else 0, 2),
            })

        return sorted(result, key=lambda x: x["count"], reverse=True)

    async def _get_audio_model_distribution(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get audio model usage distribution"""
        query = self.supabase.table("audio_generations").select(
            "voice_model"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())

        response = query.execute()

        model_counts = defaultdict(int)
        for record in response.data:
            model = record.get("voice_model", "unknown")
            model_counts[model] += 1

        total = sum(model_counts.values())

        result = []
        for model, count in model_counts.items():
            result.append({
                "model": model,
                "count": count,
                "percentage": round((count / total * 100) if total > 0 else 0, 2),
            })

        return sorted(result, key=lambda x: x["count"], reverse=True)

    async def _get_video_model_distribution(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get video model usage distribution"""
        query = self.supabase.table("video_segments").select(
            "processing_model"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())

        response = query.execute()

        model_counts = defaultdict(int)
        for record in response.data:
            model = record.get("processing_model", "unknown")
            model_counts[model] += 1

        total = sum(model_counts.values())

        result = []
        for model, count in model_counts.items():
            result.append({
                "model": model,
                "count": count,
                "percentage": round((count / total * 100) if total > 0 else 0, 2),
            })

        return sorted(result, key=lambda x: x["count"], reverse=True)

    async def get_generation_times(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get average generation times by service and model"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()

        return {
            "image_generation": await self._get_image_generation_times(start_date, end_date),
            "audio_generation": await self._get_audio_generation_times(start_date, end_date),
            "video_generation": await self._get_video_generation_times(start_date, end_date),
        }

    async def _get_image_generation_times(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get image generation time statistics"""
        query = self.supabase.table("image_generations").select(
            "model_id, generation_time_seconds"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat()).eq("status", "completed")

        response = query.execute()

        times = [record.get("generation_time_seconds", 0) for record in response.data if record.get("generation_time_seconds")]

        if not times:
            return {"average": 0, "min": 0, "max": 0, "count": 0}

        return {
            "average": round(sum(times) / len(times), 2),
            "min": round(min(times), 2),
            "max": round(max(times), 2),
            "count": len(times),
        }

    async def _get_audio_generation_times(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get audio generation time statistics"""
        query = self.supabase.table("audio_generations").select(
            "voice_model, generation_time_seconds"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat()).eq("status", "completed")

        response = query.execute()

        times = [record.get("generation_time_seconds", 0) for record in response.data if record.get("generation_time_seconds")]

        if not times:
            return {"average": 0, "min": 0, "max": 0, "count": 0}

        return {
            "average": round(sum(times) / len(times), 2),
            "min": round(min(times), 2),
            "max": round(max(times), 2),
            "count": len(times),
        }

    async def _get_video_generation_times(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get video generation time statistics"""
        query = self.supabase.table("video_segments").select(
            "processing_model, generation_time_seconds"
        ).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat()).eq("status", "completed")

        response = query.execute()

        times = [record.get("generation_time_seconds", 0) for record in response.data if record.get("generation_time_seconds")]

        if not times:
            return {"average": 0, "min": 0, "max": 0, "count": 0}

        return {
            "average": round(sum(times) / len(times), 2),
            "min": round(min(times), 2),
            "max": round(max(times), 2),
            "count": len(times),
        }

    async def get_health_check(self) -> Dict[str, Any]:
        """Get system health check with model availability by tier"""
        # Check recent generation success rates
        one_hour_ago = datetime.now() - timedelta(hours=1)

        fallback_rates = await self.get_fallback_rates(start_date=one_hour_ago)
        model_performance = await self.get_model_performance(start_date=one_hour_ago)

        # Determine overall health
        overall_fallback_rate = fallback_rates["overall_summary"]["overall_fallback_rate"]

        if overall_fallback_rate > 50:
            health_status = "critical"
        elif overall_fallback_rate > 30:
            health_status = "warning"
        else:
            health_status = "healthy"

        return {
            "status": health_status,
            "timestamp": datetime.now().isoformat(),
            "fallback_rate_last_hour": overall_fallback_rate,
            "services": {
                "script_generation": fallback_rates["script_generation"],
                "image_generation": fallback_rates["image_generation"],
                "video_generation": fallback_rates["video_generation"],
                "audio_generation": fallback_rates["audio_generation"],
            },
            "top_performing_models": model_performance[:5] if model_performance else [],
        }
