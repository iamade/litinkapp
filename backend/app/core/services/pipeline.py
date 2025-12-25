from typing import Dict, List, Optional, Any
from enum import Enum
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime


class PipelineStep(Enum):
    AUDIO_GENERATION = "audio_generation"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    AUDIO_VIDEO_MERGE = "audio_video_merge"
    LIP_SYNC = "lip_sync"


class PipelineStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineManager:
    def __init__(self):
        # Workflow: video generation first, then lip sync, merge is manual
        self.step_order = {PipelineStep.VIDEO_GENERATION: 1, PipelineStep.LIP_SYNC: 2}

    async def initialize_pipeline(
        self, video_generation_id: str, session: AsyncSession
    ) -> bool:
        """Initialize pipeline steps for a video generation"""
        try:
            # Create all pipeline steps
            for step, order in self.step_order.items():
                insert_query = text(
                    """
                    INSERT INTO pipeline_steps (
                        video_generation_id, step_name, step_order, status
                    ) VALUES (
                        :video_generation_id, :step_name, :step_order, :status
                    )
                """
                )
                await session.execute(
                    insert_query,
                    {
                        "video_generation_id": video_generation_id,
                        "step_name": step.value,
                        "step_order": order,
                        "status": PipelineStatus.PENDING.value,
                    },
                )

            # Update video generation
            pipeline_state = {
                "initialized": True,
                "current_step": PipelineStep.VIDEO_GENERATION.value,
                "steps_completed": 0,
                "total_steps": len(self.step_order),
            }

            update_query = text(
                """
                UPDATE video_generations 
                SET pipeline_state = :pipeline_state, 
                    can_resume = true 
                WHERE id = :id
            """
            )
            await session.execute(
                update_query,
                {
                    "pipeline_state": json.dumps(pipeline_state),
                    "id": video_generation_id,
                },
            )
            await session.commit()

            return True

        except Exception as e:
            print(f"[PIPELINE] Failed to initialize: {str(e)}")
            return False

    async def get_pipeline_status(
        self, video_generation_id: str, session: AsyncSession
    ) -> Dict[str, Any]:
        """Get current pipeline status"""
        try:
            # Get video generation data
            video_query = text("SELECT * FROM video_generations WHERE id = :id")
            video_result = await session.execute(
                video_query, {"id": video_generation_id}
            )
            video_data = video_result.mappings().first()

            # Get pipeline steps
            steps_query = text(
                """
                SELECT * FROM pipeline_steps 
                WHERE video_generation_id = :id 
                ORDER BY step_order
            """
            )
            steps_result = await session.execute(
                steps_query, {"id": video_generation_id}
            )
            steps_data = [dict(row) for row in steps_result.mappings()]

            # Calculate progress
            completed_steps = len([s for s in steps_data if s["status"] == "completed"])
            failed_steps = len([s for s in steps_data if s["status"] == "failed"])
            total_steps = len(steps_data)

            progress_percentage = (
                (completed_steps / total_steps * 100) if total_steps > 0 else 0
            )

            # Find current step
            current_step = None
            next_step = None

            for step in steps_data:
                if step["status"] in ["processing"]:
                    current_step = step["step_name"]
                    break
                elif step["status"] == "pending":
                    next_step = step["step_name"]
                    break

            return {
                "video_generation_id": video_generation_id,
                "overall_status": (
                    video_data.get("generation_status") if video_data else None
                ),
                "can_resume": (
                    video_data.get("can_resume", False) if video_data else False
                ),
                "failed_at_step": (
                    video_data.get("failed_at_step") if video_data else None
                ),
                "retry_count": video_data.get("retry_count", 0) if video_data else 0,
                "progress": {
                    "completed_steps": completed_steps,
                    "failed_steps": failed_steps,
                    "total_steps": total_steps,
                    "percentage": round(progress_percentage, 1),
                    "current_step": current_step,
                    "next_step": next_step,
                },
                "steps": steps_data,
                "pipeline_state": (
                    json.loads(video_data.get("pipeline_state", "{}"))
                    if video_data and video_data.get("pipeline_state")
                    else {}
                ),
            }

        except Exception as e:
            print(f"[PIPELINE] Failed to get status: {str(e)}")
            return {}

    async def mark_step_started(
        self, video_generation_id: str, step: PipelineStep, session: AsyncSession
    ) -> bool:
        """Mark a step as started"""
        try:
            print(
                f"[PIPELINE DEBUG] Marking step {step.value} as started for video {video_generation_id}"
            )

            update_step_query = text(
                """
                UPDATE pipeline_steps 
                SET status = :status, 
                    started_at = :started_at 
                WHERE video_generation_id = :video_id 
                  AND step_name = :step_name
            """
            )
            await session.execute(
                update_step_query,
                {
                    "status": PipelineStatus.PROCESSING.value,
                    "started_at": datetime.now().isoformat(),
                    "video_id": video_generation_id,
                    "step_name": step.value,
                },
            )

            # Update video generation current step
            pipeline_state = await self.get_pipeline_state(video_generation_id, session)
            pipeline_state["current_step"] = step.value

            update_video_query = text(
                """
                UPDATE video_generations 
                SET pipeline_state = :pipeline_state 
                WHERE id = :id
            """
            )
            await session.execute(
                update_video_query,
                {
                    "pipeline_state": json.dumps(pipeline_state),
                    "id": video_generation_id,
                },
            )
            await session.commit()

            return True

        except Exception as e:
            print(f"[PIPELINE] Failed to mark step started: {str(e)}")
            return False

    async def mark_step_completed(
        self,
        video_generation_id: str,
        step: PipelineStep,
        session: AsyncSession,
        step_data: Dict = None,
    ) -> bool:
        """Mark a step as completed"""
        try:
            if step_data:
                update_query = text(
                    """
                    UPDATE pipeline_steps 
                    SET status = :status, 
                        completed_at = :completed_at,
                        step_data = :step_data
                    WHERE video_generation_id = :video_id 
                      AND step_name = :step_name
                """
                )
                await session.execute(
                    update_query,
                    {
                        "status": PipelineStatus.COMPLETED.value,
                        "completed_at": datetime.now().isoformat(),
                        "step_data": json.dumps(step_data),
                        "video_id": video_generation_id,
                        "step_name": step.value,
                    },
                )
            else:
                update_query = text(
                    """
                    UPDATE pipeline_steps 
                    SET status = :status, 
                        completed_at = :completed_at
                    WHERE video_generation_id = :video_id 
                      AND step_name = :step_name
                """
                )
                await session.execute(
                    update_query,
                    {
                        "status": PipelineStatus.COMPLETED.value,
                        "completed_at": datetime.now().isoformat(),
                        "video_id": video_generation_id,
                        "step_name": step.value,
                    },
                )

            # Update video generation progress
            pipeline_state = await self.get_pipeline_state(video_generation_id, session)
            pipeline_state["steps_completed"] = (
                pipeline_state.get("steps_completed", 0) + 1
            )

            update_video_query = text(
                """
                UPDATE video_generations 
                SET pipeline_state = :pipeline_state 
                WHERE id = :id
            """
            )
            await session.execute(
                update_video_query,
                {
                    "pipeline_state": json.dumps(pipeline_state),
                    "id": video_generation_id,
                },
            )
            await session.commit()

            return True

        except Exception as e:
            print(f"[PIPELINE] Failed to mark step completed: {str(e)}")
            return False

    async def mark_step_failed(
        self,
        video_generation_id: str,
        step: PipelineStep,
        error_message: str,
        session: AsyncSession,
    ) -> bool:
        """Mark a step as failed"""
        try:
            # Get current retry count
            retry_query = text(
                """
                SELECT retry_count FROM pipeline_steps 
                WHERE video_generation_id = :video_id 
                  AND step_name = :step_name
            """
            )
            retry_result = await session.execute(
                retry_query, {"video_id": video_generation_id, "step_name": step.value}
            )
            current_retry = retry_result.scalar() or 0

            # Update step status
            update_step_query = text(
                """
                UPDATE pipeline_steps 
                SET status = :status, 
                    error_message = :error_message,
                    retry_count = :retry_count
                WHERE video_generation_id = :video_id 
                  AND step_name = :step_name
            """
            )
            await session.execute(
                update_step_query,
                {
                    "status": PipelineStatus.FAILED.value,
                    "error_message": error_message,
                    "retry_count": current_retry + 1,
                    "video_id": video_generation_id,
                    "step_name": step.value,
                },
            )

            # Get current video retry count
            video_retry_query = text(
                """
                SELECT retry_count FROM video_generations 
                WHERE id = :id
            """
            )
            video_retry_result = await session.execute(
                video_retry_query, {"id": video_generation_id}
            )
            current_video_retry = video_retry_result.scalar() or 0

            # Update video generation
            update_video_query = text(
                """
                UPDATE video_generations 
                SET generation_status = 'failed',
                    failed_at_step = :failed_step,
                    can_resume = true,
                    retry_count = :retry_count
                WHERE id = :id
            """
            )
            await session.execute(
                update_video_query,
                {
                    "failed_step": step.value,
                    "retry_count": current_video_retry + 1,
                    "id": video_generation_id,
                },
            )
            await session.commit()

            return True

        except Exception as e:
            print(f"[PIPELINE] Failed to mark step failed: {str(e)}")
            return False

    async def get_next_step_to_run(
        self, video_generation_id: str, session: AsyncSession
    ) -> Optional[PipelineStep]:
        """Get the next step that should be run"""
        try:
            steps_query = text(
                """
                SELECT * FROM pipeline_steps 
                WHERE video_generation_id = :id 
                ORDER BY step_order
            """
            )
            steps_result = await session.execute(
                steps_query, {"id": video_generation_id}
            )
            steps = [dict(row) for row in steps_result.mappings()]

            for step in steps:
                if step["status"] in ["pending", "failed"]:
                    return PipelineStep(step["step_name"])

            return None

        except Exception as e:
            print(f"[PIPELINE] Failed to get next step: {str(e)}")
            return None

    async def can_resume_from_step(
        self, video_generation_id: str, step: PipelineStep, session: AsyncSession
    ) -> bool:
        """Check if pipeline can resume from a specific step"""
        try:
            # Get the step data
            step_query = text(
                """
                SELECT * FROM pipeline_steps 
                WHERE video_generation_id = :video_id 
                  AND step_name = :step_name
            """
            )
            step_result = await session.execute(
                step_query, {"video_id": video_generation_id, "step_name": step.value}
            )
            step_data = step_result.mappings().first()

            return step_data["status"] in ["pending", "failed"] if step_data else False

        except Exception as e:
            print(f"[PIPELINE] Failed to check resume capability: {str(e)}")
            return False

    async def get_pipeline_state(
        self, video_generation_id: str, session: AsyncSession
    ) -> Dict[str, Any]:
        """Get current pipeline state"""
        try:
            query = text(
                """
                SELECT pipeline_state FROM video_generations 
                WHERE id = :id
            """
            )
            result = await session.execute(query, {"id": video_generation_id})
            row = result.mappings().first()

            if row and row.get("pipeline_state"):
                return (
                    json.loads(row["pipeline_state"])
                    if isinstance(row["pipeline_state"], str)
                    else row["pipeline_state"]
                )
            return {}

        except Exception as e:
            print(f"[PIPELINE] Failed to get pipeline state: {str(e)}")
            return {}

    async def reset_step_for_retry(
        self, video_generation_id: str, step: PipelineStep, session: AsyncSession
    ) -> bool:
        """Reset a step for retry"""
        try:
            update_query = text(
                """
                UPDATE pipeline_steps 
                SET status = :status, 
                    started_at = NULL,
                    completed_at = NULL,
                    error_message = NULL
                WHERE video_generation_id = :video_id 
                  AND step_name = :step_name
            """
            )
            await session.execute(
                update_query,
                {
                    "status": PipelineStatus.PENDING.value,
                    "video_id": video_generation_id,
                    "step_name": step.value,
                },
            )
            await session.commit()

            return True

        except Exception as e:
            print(f"[PIPELINE] Failed to reset step: {str(e)}")
            return False
