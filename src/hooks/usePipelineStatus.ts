import { useState, useEffect, useCallback, useRef } from 'react';
import { aiService, PipelineStatus } from '../services/aiService';
import { toast } from 'react-hot-toast';
import { UsePipelineStatusOptions, UsePipelineStatusReturn } from '../types/usePipelineStatus';


export const usePipelineStatus = (
  videoGenerationId: string,
  options: UsePipelineStatusOptions = {}
): UsePipelineStatusReturn => {
  const {
    autoRefresh = true,
    refreshInterval = 3000,
    onStatusChange,
    onError
  } = options;

  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Fetch pipeline status
  const fetchPipelineStatus = useCallback(async () => {
    if (!videoGenerationId || !mountedRef.current) return;

    try {
      setError(null);
      const status = await aiService.getPipelineStatus(videoGenerationId);
      
      if (!mountedRef.current) return;
      
      setPipelineStatus(status);
      
      // Call status change callback
      if (onStatusChange) {
        onStatusChange(status);
      }
      
      // Auto-stop polling if generation is complete or failed (and not retryable)
      if (autoRefresh && isPolling) {
        const isComplete = ['completed', 'failed'].includes(status.overall_status);
        const cannotResume = !status.can_resume;
        
        if (isComplete && cannotResume) {
          stopPolling();
        }
      }
      
    } catch (err) {
      if (!mountedRef.current) return;
      
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch pipeline status';
      setError(errorMessage);
      
      if (onError) {
        onError(err instanceof Error ? err : new Error(errorMessage));
      }
    }
  }, [videoGenerationId, onStatusChange, onError, autoRefresh, isPolling]);

  // Initial load
  const refreshStatus = useCallback(async () => {
    if (!mountedRef.current) return;
    setIsLoading(true);
    await fetchPipelineStatus();
    if (mountedRef.current) {
      setIsLoading(false);
    }
  }, [fetchPipelineStatus]);

  // Start polling
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current || !autoRefresh) return;
    
    setIsPolling(true);
    pollingIntervalRef.current = setInterval(fetchPipelineStatus, refreshInterval);
  }, [fetchPipelineStatus, refreshInterval, autoRefresh]);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Retry generation
  const retryGeneration = useCallback(async (step?: string) => {
    if (!videoGenerationId || !mountedRef.current) return;

    setIsRetrying(true);
    setRetryError(null);

    try {
      const result = await aiService.retryVideoGeneration(videoGenerationId, step);
      
      if (!mountedRef.current) return;
      
      toast.success(result.message);
      
      // Refresh status after retry
      await fetchPipelineStatus();
      
      // Start polling if not already polling
      if (autoRefresh && !isPolling) {
        startPolling();
      }
      
    } catch (err) {
      if (!mountedRef.current) return;
      
      const errorMessage = err instanceof Error ? err.message : 'Failed to retry generation';
      setRetryError(errorMessage);
      toast.error(errorMessage);
    } finally {
      if (mountedRef.current) {
        setIsRetrying(false);
      }
    }
  }, [videoGenerationId, fetchPipelineStatus, autoRefresh, isPolling, startPolling]);

  // Initial load and polling setup
  useEffect(() => {
    if (!videoGenerationId) return;

    refreshStatus();

    if (autoRefresh) {
      startPolling();
    }

    return () => {
      stopPolling();
    };
  }, [videoGenerationId, refreshStatus, autoRefresh, startPolling, stopPolling]);

  return {
    pipelineStatus,
    isLoading,
    error,
    refreshStatus,
    retryGeneration,
    isRetrying,
    retryError,
    startPolling,
    stopPolling,
    isPolling
  };
};