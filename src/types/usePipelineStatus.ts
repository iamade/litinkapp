import { PipelineStatus } from "../services/aiService";

export interface UsePipelineStatusOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
  onStatusChange?: (status: PipelineStatus) => void;
  onError?: (error: Error) => void;
}

export interface UsePipelineStatusReturn {
  pipelineStatus: PipelineStatus | null;
  isLoading: boolean;
  error: string | null;
  refreshStatus: () => Promise<void>;
  retryGeneration: (step?: string) => Promise<void>;
  isRetrying: boolean;
  retryError: string | null;
  startPolling: () => void;
  stopPolling: () => void;
  isPolling: boolean;
}
