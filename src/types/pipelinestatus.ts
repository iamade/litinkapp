// ✅ NEW: Pipeline Status Interface
export interface PipelineStatus {
  video_generation_id: string;
  overall_status: string;
  can_resume: boolean;
  failed_at_step?: string;
  retry_count: number;
  progress: {
    completed_steps: number;
    failed_steps: number;
    total_steps: number;
    percentage: number;
    current_step?: string;
    next_step?: string;
  };
  steps: Array<{
    step_name: string;
    step_order: number;
    status: 'pending' | 'processing' | 'completed' | 'failed' | 'skipped';
    started_at?: string;
    completed_at?: string;
    error_message?: string;
    retry_count: number;
  }>;
  pipeline_state: Record<string, any>;
}

export interface RetryResponse {
  message: string;
  video_generation_id: string;
  retry_step: string;
  task_id?: string;
  retry_count: number;
  new_status: string;
  existing_progress?: {
    audio_files_count: number;
    images_count: number;
    videos_count: number;
    has_final_video: boolean;
    last_completed_step: string;
    progress_percentage: number;
  };
}
