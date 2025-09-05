import { PipelineStatus } from "../services/aiService";

export interface RetryControlsProps {
  pipelineStatus: PipelineStatus;
  onRetry: (step?: string) => Promise<void>;
  isRetrying: boolean;
  retryError: string | null;
  className?: string;
}

export interface RetryOption {
  value: string;
  label: string;
  description: string;
  icon: string;
}