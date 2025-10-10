// Re-export types from API service for easier imports
export type {
  VideoGeneration,
  GenerationStatus,
  AudioProgress,
  ImageProgress,
  VideoProgress,
  MergeProgress,
  LipSyncProgress,
  GenerationError,
  AudioFiles,
  ImageData,
  VideoData,
  MergeData,
  LipSyncData,
  StartVideoGenerationRequest,
  StartVideoGenerationResponse,
} from "../lib/videoGenerationApi";

// Discriminated union for video job status with safe defaults
export type VideoJobStatus =
  | 'queued'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'canceled'
  | 'retrying'
  | 'unknown';

// Safe mapper for status labels with default fallback
export const getStatusLabel = (status: VideoJobStatus | string | null | undefined): string => {
  switch (status) {
    case 'queued':
      return 'Queued';
    case 'processing':
      return 'Processing';
    case 'completed':
      return 'Completed';
    case 'failed':
      return 'Failed';
    case 'canceled':
      return 'Canceled';
    case 'retrying':
      return 'Retrying';
    case 'unknown':
    default:
      return 'Unknown';
  }
};

// Additional frontend-specific types
export interface StepProgressInfo {
  step: number;
  title: string;
  description: string;
  status: "pending" | "active" | "completed" | "error";
  progress: number;
}

export interface VideoGenerationUIState {
  showModal: boolean;
  activeStep: number;
  steps: StepProgressInfo[];
  canCancel: boolean;
  canRetry: boolean;
}

export interface QualityTierOption {
  id: "free" | "premium" | "professional";
  name: string;
  description: string;
  features: string[];
  price: string;
  recommended?: boolean;
}
