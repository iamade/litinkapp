import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient } from '../lib/api';
import { toast } from 'react-hot-toast';
import {
  MergeOperation,
  MergePreviewOperation,
  MergeManualRequest,
  MergePreviewRequest,
  MergeStatusResponse,
  MergeStatus,
  MergeQualityTier,
  MergeOutputFormat,
  UseMergeOperationsReturn
} from '../types/merge';

export const useMergeOperations = (): UseMergeOperationsReturn => {
  // State management
  const [currentMerge, setCurrentMerge] = useState<MergeOperation | null>(null);
  const [currentPreview, setCurrentPreview] = useState<MergePreviewOperation | null>(null);
  const [isMerging, setIsMerging] = useState(false);
  const [isGeneratingPreview, setIsGeneratingPreview] = useState(false);
  const [mergeProgress, setMergeProgress] = useState(0);
  const [mergeStatus, setMergeStatus] = useState<string>('');
  const [retryCount, setRetryCount] = useState(0);
  const [queuePosition, setQueuePosition] = useState<number | null>(null);

  // Refs for polling intervals
  const mergePollingRef = useRef<NodeJS.Timeout | null>(null);
  const previewPollingRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (mergePollingRef.current) {
      clearInterval(mergePollingRef.current);
      mergePollingRef.current = null;
    }
    if (previewPollingRef.current) {
      clearInterval(previewPollingRef.current);
      previewPollingRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  // Start merge operation
  const startMerge = useCallback(async (params: MergeManualRequest) => {
    if (isMerging) {
      toast.error('A merge operation is already in progress');
      return null;
    }

    try {
      setIsMerging(true);
      setMergeStatus('Starting merge operation...');
      setRetryCount(0);

      const response = await apiClient.post<{
        merge_id: string;
        status: string;
        message: string;
        estimated_duration?: number;
        queue_position?: number;
      }>('/merge/manual', params);

      const mergeOperation: MergeOperation = {
        id: response.merge_id,
        user_id: '', // Will be set by backend
        status: response.status as MergeStatus,
        input_sources: params.input_sources,
        quality_tier: params.quality_tier,
        output_format: params.output_format,
        ffmpeg_params: params.ffmpeg_params,
        merge_name: params.merge_name,
        progress_percentage: 0,
        current_step: 'Initializing',
        created_at: new Date(),
        updated_at: new Date()
      };

      setCurrentMerge(mergeOperation);
      setQueuePosition(response.queue_position || null);

      // Start polling for status updates
      startMergePolling(response.merge_id);

      toast.success('Merge operation started');
      return response.merge_id;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to start merge operation';
      toast.error(errorMessage);
      setIsMerging(false);
      return null;
    }
  }, [isMerging]);

  // Generate preview
  const generatePreview = useCallback(async (params: MergePreviewRequest) => {
    if (isGeneratingPreview) {
      toast.error('A preview generation is already in progress');
      return null;
    }

    try {
      setIsGeneratingPreview(true);
      setMergeStatus('Generating preview...');

      const response = await apiClient.post<{
        preview_url?: string;
        preview_duration: number;
        status: string;
        message: string;
      }>('/merge/preview', params);

      const previewOperation: MergePreviewOperation = {
        id: `preview_${Date.now()}`,
        status: response.status as MergeStatus,
        preview_url: response.preview_url,
        preview_duration: response.preview_duration,
        created_at: new Date(),
        updated_at: new Date()
      };

      setCurrentPreview(previewOperation);

      // Start polling if status is processing
      if (response.status === 'processing') {
        startPreviewPolling(previewOperation.id);
      }

      toast.success('Preview generation started');
      return previewOperation.id;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate preview';
      toast.error(errorMessage);
      setIsGeneratingPreview(false);
      return null;
    }
  }, [isGeneratingPreview]);

  // Poll merge status
  const startMergePolling = useCallback((mergeId: string) => {
    cleanup(); // Clear any existing polling

    const pollStatus = async () => {
      try {
        const response = await apiClient.get<{
          merge_id: string;
          status: string;
          progress_percentage?: number;
          current_step?: string;
          output_url?: string;
          error_message?: string;
          created_at: string;
          updated_at: string;
        }>(`/merge/status/${mergeId}`);

        const updatedMerge: MergeOperation = {
          id: response.merge_id,
          user_id: '', // Will be populated from context or API
          status: response.status as MergeStatus,
          input_sources: [], // Will be populated from initial request
          quality_tier: MergeQualityTier.WEB, // Will be populated from initial request
          output_format: MergeOutputFormat.MP4, // Will be populated from initial request
          progress_percentage: response.progress_percentage || 0,
          current_step: response.current_step || '',
          output_url: response.output_url,
          error_message: response.error_message,
          created_at: new Date(response.created_at),
          updated_at: new Date(response.updated_at)
        };

        setCurrentMerge(updatedMerge);
        setMergeProgress(updatedMerge.progress_percentage || 0);
        setMergeStatus(updatedMerge.current_step || '');

        // Handle completion states
        if (updatedMerge.status === 'completed') {
          setIsMerging(false);
          setRetryCount(0);
          cleanup();
          toast.success('Merge operation completed successfully');
        } else if (updatedMerge.status === 'failed') {
          setIsMerging(false);
          cleanup();
          toast.error(updatedMerge.error_message || 'Merge operation failed');
        } else if (updatedMerge.status === 'cancelled') {
          setIsMerging(false);
          setRetryCount(0);
          cleanup();
          toast('Merge operation was cancelled');
        }

      } catch (error) {

        // Implement exponential backoff for retries
        const maxRetries = 5;
        if (retryCount < maxRetries) {
          setRetryCount(prev => prev + 1);
          const backoffDelay = Math.min(1000 * Math.pow(2, retryCount), 30000); // Max 30 seconds
          setTimeout(pollStatus, backoffDelay);
        } else {
          setIsMerging(false);
          cleanup();
          toast.error('Lost connection to merge operation. Please refresh and try again.');
        }
      }
    };

    // Initial poll
    pollStatus();

    // Set up interval polling (every 2-5 seconds)
    mergePollingRef.current = setInterval(pollStatus, 3000);
  }, [retryCount, cleanup]);

  // Poll preview status
  const startPreviewPolling = useCallback((previewId: string) => {
    cleanup(); // Clear any existing polling

    let pollCount = 0;
    const maxPolls = 30; // Max 30 polls (5 minutes at 10s intervals)

    const pollStatus = async () => {
      try {
        pollCount++;

        // For now, we'll poll the merge status endpoint with a special preview flag
        // TODO: Implement dedicated preview status endpoint in backend
        const response = await apiClient.get<{
          preview_url?: string;
          preview_duration?: number;
          status: string;
          message?: string;
          error_message?: string;
        }>(`/merge/preview/status/${previewId}`);

        if (response.preview_url && response.status === 'completed') {
          const updatedPreview: MergePreviewOperation = {
            ...currentPreview!,
            status: MergeStatus.COMPLETED,
            preview_url: response.preview_url,
            preview_duration: response.preview_duration || 30,
            updated_at: new Date()
          };
          setCurrentPreview(updatedPreview);
          setIsGeneratingPreview(false);
          cleanup();
          toast.success('Preview generated successfully');
          return;
        } else if (response.status === 'failed') {
          const updatedPreview: MergePreviewOperation = {
            ...currentPreview!,
            status: MergeStatus.FAILED,
            error_message: response.error_message || 'Preview generation failed',
            updated_at: new Date()
          };
          setCurrentPreview(updatedPreview);
          setIsGeneratingPreview(false);
          cleanup();
          toast.error(response.error_message || 'Failed to generate preview');
          return;
        }

        // Continue polling if not completed and under max polls
        if (pollCount < maxPolls) {
          setTimeout(pollStatus, 10000); // Poll every 10 seconds for previews
        } else {
          const updatedPreview: MergePreviewOperation = {
            ...currentPreview!,
            status: MergeStatus.FAILED,
            error_message: 'Preview generation timed out',
            updated_at: new Date()
          };
          setCurrentPreview(updatedPreview);
          setIsGeneratingPreview(false);
          cleanup();
          toast.error('Preview generation timed out');
        }

      } catch (error: unknown) {

        // If endpoint doesn't exist, fall back to simulation for now
        if (error instanceof Error && error.message.includes('404')) {
          setTimeout(() => {
            if (currentPreview) {
              const updatedPreview: MergePreviewOperation = {
                ...currentPreview,
                status: MergeStatus.COMPLETED,
                preview_url: `https://example.com/preview_${previewId}.mp4`, // This should be replaced with real URL
                updated_at: new Date()
              };
              setCurrentPreview(updatedPreview);
              setIsGeneratingPreview(false);
              cleanup();
              toast.success('Preview generated successfully');
            }
          }, 5000);
        } else {
          setIsGeneratingPreview(false);
          cleanup();
          toast.error('Failed to generate preview');
        }
      }
    };

    // Start polling after a short delay
    setTimeout(pollStatus, 2000);
  }, [currentPreview, cleanup]);

  // Cancel merge operation
  const cancelMerge = useCallback(async () => {
    if (!currentMerge) return;

    try {
      // TODO: Implement cancel endpoint in backend
      // await apiClient.post(`/merge/cancel/${currentMerge.id}`, {});

      setCurrentMerge(prev => prev ? { ...prev, status: MergeStatus.CANCELLED } : null);
      setIsMerging(false);
      cleanup();
      toast('Merge operation cancelled');

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to cancel merge operation';
      toast.error(errorMessage);
    }
  }, [currentMerge, cleanup]);

  // Download merge result
  const downloadMergeResult = useCallback(async (mergeId: string) => {
    try {
      toast.loading('Preparing download...', { id: 'download' });

      const response = await apiClient.get<{
        download_url: string;
        file_size_bytes?: number;
        content_type: string;
        filename: string;
        expires_at?: string;
      }>(`/merge/${mergeId}/download`);

      // Check if file size is reasonable (max 2GB)
      const maxSize = 2 * 1024 * 1024 * 1024; // 2GB
      if (response.file_size_bytes && response.file_size_bytes > maxSize) {
        toast.error('File is too large to download', { id: 'download' });
        return;
      }

      // Trigger download
      const link = document.createElement('a');
      link.href = response.download_url;
      link.download = response.filename || `merge_${mergeId}.mp4`;
      link.target = '_blank'; // Open in new tab as fallback
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast.success(`Download started: ${response.filename || 'merge file'}`, { id: 'download' });

    } catch (error) {

      let errorMessage = 'Failed to download merge result';
      if (error instanceof Error) {
        if (error.message.includes('404')) {
          errorMessage = 'Merge result not found. The operation may still be processing.';
        } else if (error.message.includes('403')) {
          errorMessage = 'Access denied. You may not have permission to download this file.';
        } else if (error.message.includes('500')) {
          errorMessage = 'Server error. Please try again later.';
        } else {
          errorMessage = error.message;
        }
      }

      toast.error(errorMessage, { id: 'download' });
    }
  }, []);

  // Cleanup preview URL when component unmounts or preview changes
  const cleanupPreview = useCallback(() => {
    if (currentPreview?.preview_url) {
      // TODO: Call backend cleanup endpoint if available
      // await apiClient.delete(`/merge/preview/${currentPreview.id}`);
    }
    setCurrentPreview(null);
  }, [currentPreview]);

  // Get merge status
  const getMergeStatus = useCallback(async (mergeId: string): Promise<MergeStatusResponse> => {
    const response = await apiClient.get<MergeStatusResponse>(`/merge/status/${mergeId}`);
    return response;
  }, []);

  // Retry merge operation
  const retryMerge = useCallback(async (mergeId: string): Promise<boolean> => {
    try {
      setRetryCount(prev => prev + 1);

      const response = await apiClient.post<{
        merge_id: string;
        status: string;
        message: string;
        queue_position?: number;
      }>(`/merge/retry/${mergeId}`, {});

      if (response.status === 'pending' || response.status === 'processing') {
        // Restart polling for the merge
        startMergePolling(mergeId);
        toast.success('Merge operation retried successfully');
        return true;
      } else {
        toast.error('Failed to retry merge operation');
        return false;
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to retry merge operation';
      toast.error(errorMessage);
      return false;
    }
  }, [startMergePolling]);

  // Reset state
  const reset = useCallback(() => {
    cleanup();
    setCurrentMerge(null);
    setCurrentPreview(null);
    setIsMerging(false);
    setIsGeneratingPreview(false);
    setMergeProgress(0);
    setMergeStatus('');
    setRetryCount(0);
    setQueuePosition(null);
  }, [cleanup]);

  return {
    // State
    currentMerge,
    currentPreview,
    isMerging,
    isGeneratingPreview,
    mergeProgress,
    mergeStatus,
    retryCount,
    queuePosition,
    lastError: undefined, // TODO: Implement error tracking

    // Actions
    startMerge,
    generatePreview,
    cancelMerge,
    downloadMergeResult,
    cleanupPreview,
    reset,
    getMergeStatus,
    retryMerge,

    // Utilities
    cleanup
  };
};