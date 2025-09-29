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
