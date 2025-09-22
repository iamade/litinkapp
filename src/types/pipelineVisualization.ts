import { PipelineStatus } from "./pipelinestatus";

export interface PipelineVisualizationProps {
  pipelineStatus: PipelineStatus;
  className?: string;
}

export interface PipelineStep {
  key: string;
  name: string;
  icon: string;
  description: string;
  estimatedTime: string;
}

export interface PipelineStepDetail {
  step_name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'skipped';
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  retry_count: number;
}

export interface PipelineProgress {
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
  current_step?: string;
  next_step?: string;
  percentage: number;
}

// This should match the one in aiService.ts
export interface PipelineStatusDetailed {
  overall_status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: PipelineProgress;
  steps: PipelineStepDetail[];
  retry_count: number;
  can_resume: boolean;
  failed_at_step?: string;
  started_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface RetryResponse {
  message: string;
  video_generation_id: string;
  retry_count: number;
  status: string;
}