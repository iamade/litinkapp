from typing import Dict, List, Optional, Any
from enum import Enum
from app.core.database import get_supabase
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
        self.supabase = get_supabase()
        # Workflow: video generation first, then lip sync, merge is manual
        self.step_order = {
            PipelineStep.VIDEO_GENERATION: 1,
            PipelineStep.LIP_SYNC: 2
        }

    def initialize_pipeline(self, video_generation_id: str) -> bool:
        """Initialize pipeline steps for a video generation"""
        try:
            # Create all pipeline steps
            steps_to_create = []
            for step, order in self.step_order.items():
                steps_to_create.append({
                    'video_generation_id': video_generation_id,
                    'step_name': step.value,
                    'step_order': order,
                    'status': PipelineStatus.PENDING.value
                })
            
            # Batch insert all steps
            self.supabase.table('pipeline_steps').insert(steps_to_create).execute()
            
            # Update video generation
            self.supabase.table('video_generations').update({
                'pipeline_state': {
                    'initialized': True,
                    'current_step': PipelineStep.VIDEO_GENERATION.value,
                    'steps_completed': 0,
                    'total_steps': len(self.step_order)
                },
                'can_resume': True
            }).eq('id', video_generation_id).execute()
            
            return True
            
        except Exception as e:
            print(f"[PIPELINE] Failed to initialize: {str(e)}")
            return False

    def get_pipeline_status(self, video_generation_id: str) -> Dict[str, Any]:
        """Get current pipeline status"""
        try:
            # Get video generation data
            video_response = self.supabase.table('video_generations')\
                .select('*')\
                .eq('id', video_generation_id)\
                .single().execute()
            
            # Get pipeline steps
            steps_response = self.supabase.table('pipeline_steps')\
                .select('*')\
                .eq('video_generation_id', video_generation_id)\
                .order('step_order')\
                .execute()
            
            video_data = video_response.data
            steps_data = steps_response.data or []
            
            # Calculate progress
            completed_steps = len([s for s in steps_data if s['status'] == 'completed'])
            failed_steps = len([s for s in steps_data if s['status'] == 'failed'])
            total_steps = len(steps_data)
            
            progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
            
            # Find current step
            current_step = None
            next_step = None
            
            for step in steps_data:
                if step['status'] in ['processing']:
                    current_step = step['step_name']
                    break
                elif step['status'] == 'pending':
                    next_step = step['step_name']
                    break
            
            return {
                'video_generation_id': video_generation_id,
                'overall_status': video_data.get('generation_status'),
                'can_resume': video_data.get('can_resume', False),
                'failed_at_step': video_data.get('failed_at_step'),
                'retry_count': video_data.get('retry_count', 0),
                'progress': {
                    'completed_steps': completed_steps,
                    'failed_steps': failed_steps,
                    'total_steps': total_steps,
                    'percentage': round(progress_percentage, 1),
                    'current_step': current_step,
                    'next_step': next_step
                },
                'steps': steps_data,
                'pipeline_state': video_data.get('pipeline_state', {})
            }
            
        except Exception as e:
            print(f"[PIPELINE] Failed to get status: {str(e)}")
            return {}

    def mark_step_started(self, video_generation_id: str, step: PipelineStep) -> bool:
        """Mark a step as started"""
        try:
            print(f"[PIPELINE DEBUG] Marking step {step.value} as started for video {video_generation_id}")
            self.supabase.table('pipeline_steps').update({
                'status': PipelineStatus.PROCESSING.value,
                'started_at': datetime.now().isoformat()
            }).eq('video_generation_id', video_generation_id)\
              .eq('step_name', step.value).execute()
            
            # Update video generation current step
            pipeline_state = self.get_pipeline_state(video_generation_id)
            pipeline_state['current_step'] = step.value
            
            self.supabase.table('video_generations').update({
                'pipeline_state': pipeline_state
            }).eq('id', video_generation_id).execute()
            
            return True
            
        except Exception as e:
            print(f"[PIPELINE] Failed to mark step started: {str(e)}")
            return False

    def mark_step_completed(self, video_generation_id: str, step: PipelineStep, step_data: Dict = None) -> bool:
        """Mark a step as completed"""
        try:
            update_data = {
                'status': PipelineStatus.COMPLETED.value,
                'completed_at': datetime.now().isoformat()
            }
            
            if step_data:
                update_data['step_data'] = step_data
            
            self.supabase.table('pipeline_steps').update(update_data)\
                .eq('video_generation_id', video_generation_id)\
                .eq('step_name', step.value).execute()
            
            # Update video generation progress
            pipeline_state = self.get_pipeline_state(video_generation_id)
            pipeline_state['steps_completed'] = pipeline_state.get('steps_completed', 0) + 1
            
            self.supabase.table('video_generations').update({
                'pipeline_state': pipeline_state
            }).eq('id', video_generation_id).execute()
            
            return True
            
        except Exception as e:
            print(f"[PIPELINE] Failed to mark step completed: {str(e)}")
            return False

    def mark_step_failed(self, video_generation_id: str, step: PipelineStep, error_message: str) -> bool:
        """Mark a step as failed"""
        try:
            # Update step status
            self.supabase.table('pipeline_steps').update({
                'status': PipelineStatus.FAILED.value,
                'error_message': error_message,
                'retry_count': self.supabase.table('pipeline_steps')\
                    .select('retry_count')\
                    .eq('video_generation_id', video_generation_id)\
                    .eq('step_name', step.value)\
                    .single().execute().data.get('retry_count', 0) + 1
            }).eq('video_generation_id', video_generation_id)\
              .eq('step_name', step.value).execute()
            
            # Update video generation 
            self.supabase.table('video_generations').update({
                'generation_status': 'failed',
                'failed_at_step': step.value,
                'can_resume': True,
                'retry_count': self.supabase.table('video_generations')\
                    .select('retry_count')\
                    .eq('id', video_generation_id)\
                    .single().execute().data.get('retry_count', 0) + 1
            }).eq('id', video_generation_id).execute()
            
            return True
            
        except Exception as e:
            print(f"[PIPELINE] Failed to mark step failed: {str(e)}")
            return False

    def get_next_step_to_run(self, video_generation_id: str) -> Optional[PipelineStep]:
        """Get the next step that should be run"""
        try:
            steps_response = self.supabase.table('pipeline_steps')\
                .select('*')\
                .eq('video_generation_id', video_generation_id)\
                .order('step_order')\
                .execute()
            
            steps = steps_response.data or []
            
            for step in steps:
                if step['status'] in ['pending', 'failed']:
                    return PipelineStep(step['step_name'])
            
            return None
            
        except Exception as e:
            print(f"[PIPELINE] Failed to get next step: {str(e)}")
            return None

    def can_resume_from_step(self, video_generation_id: str, step: PipelineStep) -> bool:
        """Check if pipeline can resume from a specific step"""
        try:
            # Get the step data
            step_response = self.supabase.table('pipeline_steps')\
                .select('*')\
                .eq('video_generation_id', video_generation_id)\
                .eq('step_name', step.value)\
                .single().execute()
            
            step_data = step_response.data
            return step_data['status'] in ['pending', 'failed'] if step_data else False
            
        except Exception as e:
            print(f"[PIPELINE] Failed to check resume capability: {str(e)}")
            return False

    def get_pipeline_state(self, video_generation_id: str) -> Dict[str, Any]:
        """Get current pipeline state"""
        try:
            response = self.supabase.table('video_generations')\
                .select('pipeline_state')\
                .eq('id', video_generation_id)\
                .single().execute()
            
            return response.data.get('pipeline_state', {}) if response.data else {}
            
        except Exception as e:
            print(f"[PIPELINE] Failed to get pipeline state: {str(e)}")
            return {}

    def reset_step_for_retry(self, video_generation_id: str, step: PipelineStep) -> bool:
        """Reset a step for retry"""
        try:
            self.supabase.table('pipeline_steps').update({
                'status': PipelineStatus.PENDING.value,
                'started_at': None,
                'completed_at': None,
                'error_message': None
            }).eq('video_generation_id', video_generation_id)\
              .eq('step_name', step.value).execute()
            
            return True
            
        except Exception as e:
            print(f"[PIPELINE] Failed to reset step: {str(e)}")
            return False