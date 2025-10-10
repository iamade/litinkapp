import { useState, useEffect, useCallback, useRef } from 'react';
import {
  VideoGeneration,
  GenerationStatus,
  AudioProgress,
  ImageProgress,
  VideoProgress,
  MergeProgress,
  LipSyncProgress
} from '../lib/videoGenerationApi';
import { pollingService, PollingCallbacks } from '../services/videoGenerationPolling';

// Debug logging guard
const DEBUG = false;

export interface UseVideoGenerationStatusReturn {
  // Stable return shape as requested
  data: VideoGeneration | null;
  error: Error | null;
  isLoading: boolean;
  refetch: () => void;
  
  // Additional state for backward compatibility
  generation: VideoGeneration | null;
  status: GenerationStatus | null;
  isPolling: boolean;
  retryAttempts: number;
  
  // Enhanced progress data
  progress: {
    overall: number;
    currentStep: string;
    stepProgress: {
      image_generation: { status: string; progress: number };
      audio_generation: { status: string; progress: number };
      video_generation: { status: string; progress: number };
      audio_video_merge: { status: string; progress: number };
    };
    audio?: AudioProgress;
    images?: ImageProgress;
    video?: VideoProgress;
    merge?: MergeProgress;
    lipSync?: LipSyncProgress;
  };
  
  // Control functions
  startPolling: (videoGenId: string) => void;
  stopPolling: () => void;
  retry: () => void;
  clearError: () => void;
  
  // Status checks
  isComplete: boolean;
  isFailed: boolean;
  isGenerating: boolean;
}

export const useVideoGenerationStatus = (
  videoGenId?: string
): UseVideoGenerationStatusReturn => {
  // Initialize with isLoading=true, data=null as required
  const [generation, setGeneration] = useState<VideoGeneration | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [isLoading, setIsLoading] = useState(true); // Start with loading state
  const [currentStep, setCurrentStep] = useState<string>('');
  const [stepProgress, setStepProgress] = useState({
    image_generation: { status: 'pending', progress: 0 },
    audio_generation: { status: 'pending', progress: 0 },
    video_generation: { status: 'pending', progress: 0 },
    audio_video_merge: { status: 'pending', progress: 0 }
  });
  const currentVideoGenId = useRef<string | null>(null);

  // Calculate overall progress from step progress
  const calculateOverallProgress = (): number => {
    const totalSteps = Object.values(stepProgress).length;
    const totalProgress = Object.values(stepProgress).reduce(
      (sum, step) => sum + step.progress,
      0
    );
    return Math.round(totalProgress / totalSteps);
  };

  // Debug logging with safe types
  const logDebug = (message: string, data?: unknown) => {
    if (DEBUG) {
      console.log(`[useVideoGenerationStatus] ${message}`, data);
    }
  };

  // Reset state when generationId changes
  useEffect(() => {
    if (videoGenId !== currentVideoGenId.current) {
      logDebug('Resetting state for new videoGenId', { old: currentVideoGenId.current, new: videoGenId });
      setGeneration(null);
      setError(null);
      setIsLoading(true);
      setCurrentStep('');
      setStepProgress({
        image_generation: { status: 'pending', progress: 0 },
        audio_generation: { status: 'pending', progress: 0 },
        video_generation: { status: 'pending', progress: 0 },
        audio_video_merge: { status: 'pending', progress: 0 }
      });
    }
  }, [videoGenId]);

  // Polling callbacks with proper structure
  const callbacks: PollingCallbacks = {
    onUpdate: useCallback((updatedGeneration: VideoGeneration) => {
      logDebug('Received generation update', updatedGeneration);
      
      // Handle 204 No Content or null responses
      if (!updatedGeneration) {
        logDebug('Received null/undefined generation, setting data to null');
        setGeneration(null);
        setError(null);
        setIsLoading(false);
        setStepProgress({
          image_generation: { status: "pending", progress: 0 },
          audio_generation: { status: "pending", progress: 0 },
          video_generation: { status: "pending", progress: 0 },
          audio_video_merge: { status: "pending", progress: 0 },
        });
        return;
      }

      setGeneration(updatedGeneration);
      setError(null);
      setIsLoading(false);
      
      // Null-safe access to generation status
      const status = updatedGeneration?.generation_status ?? null;
      let newCurrentStep = '';
      let newStepProgress = { ...stepProgress };
      
      switch (status) {
        case 'generating_audio':
          newCurrentStep = 'Audio Generation';
          newStepProgress.audio_generation = { status: 'processing', progress: 50 };
          break;
        case 'audio_completed':
          newCurrentStep = 'Audio Generation';
          newStepProgress.audio_generation = { status: 'completed', progress: 100 };
          break;
        case 'generating_images':
          newCurrentStep = 'Image Generation';
          newStepProgress.image_generation = { status: 'processing', progress: 50 };
          break;
        case 'images_completed':
          newCurrentStep = 'Image Generation';
          newStepProgress.image_generation = { status: 'completed', progress: 100 };
          break;
        case 'generating_video':
          newCurrentStep = 'Video Generation';
          newStepProgress.video_generation = { status: 'processing', progress: 50 };
          break;
        case 'video_completed':
          newCurrentStep = 'Video Generation';
          newStepProgress.video_generation = { status: 'completed', progress: 100 };
          break;
        case 'merging_audio':
          newCurrentStep = 'Audio/Video Merge';
          newStepProgress.audio_video_merge = { status: 'processing', progress: 50 };
          break;
        case 'applying_lipsync':
          newCurrentStep = 'Lip Sync';
          newStepProgress.audio_video_merge = { status: 'completed', progress: 100 };
          break;
        case 'completed':
          newCurrentStep = 'Complete';
          newStepProgress = {
            image_generation: { status: 'completed', progress: 100 },
            audio_generation: { status: 'completed', progress: 100 },
            video_generation: { status: 'completed', progress: 100 },
            audio_video_merge: { status: 'completed', progress: 100 }
          };
          break;
        case 'failed':
        case 'lipsync_failed':
          newCurrentStep = 'Failed';
          // Set all steps to failed
          Object.keys(newStepProgress).forEach(key => {
            newStepProgress[key as keyof typeof newStepProgress] = { status: 'failed', progress: 0 };
          });
          break;
      }
      
      setCurrentStep(newCurrentStep);
      setStepProgress(newStepProgress);
    }, [stepProgress]),
    
    onError: useCallback((pollingError: Error) => {
      logDebug('Polling error occurred', pollingError);
      setError(pollingError);
      setIsPolling(false);
      setIsLoading(false);
    }, []),
    
    onComplete: useCallback((completedGeneration: VideoGeneration) => {
      logDebug('Polling completed', completedGeneration);
      setGeneration(completedGeneration);
      setIsPolling(false);
      setIsLoading(false);
    }, []),
    
    onRetry: useCallback((attempt: number, retryError: Error) => {
      logDebug(`Polling retry attempt ${attempt}`, retryError);
    }, [])
  };

  // Start polling function with proper state management
  const startPolling = useCallback((newVideoGenId: string) => {
    logDebug('Starting polling', { newVideoGenId });
    
    if (currentVideoGenId.current) {
      pollingService.stopPolling(currentVideoGenId.current);
    }
    
    currentVideoGenId.current = newVideoGenId;
    setIsPolling(true);
    setIsLoading(true);
    setError(null);
    
    pollingService.startPolling(newVideoGenId, callbacks);
  }, [callbacks]);

  // Refetch function for stable return shape
  const refetch = useCallback(() => {
    if (currentVideoGenId.current) {
      logDebug('Refetching data', { videoGenId: currentVideoGenId.current });
      startPolling(currentVideoGenId.current);
    }
  }, [startPolling]);

  // Stop polling function
  const stopPolling = useCallback(() => {
    if (currentVideoGenId.current) {
      pollingService.stopPolling(currentVideoGenId.current);
      setIsPolling(false);
    }
  }, []);

  // Retry function
  const retry = useCallback(() => {
    if (currentVideoGenId.current) {
      startPolling(currentVideoGenId.current);
    }
  }, [startPolling]);

  // Clear error function
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Auto-start polling if videoGenId is provided
  useEffect(() => {
    if (videoGenId && videoGenId !== currentVideoGenId.current) {
      startPolling(videoGenId);
    }
    
    return () => {
      stopPolling();
    };
  }, [videoGenId, startPolling, stopPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  // Derived state with null-safe guards
  const status = generation?.generation_status ?? null;
  const isComplete = status ? ['completed', 'lipsync_completed'].includes(status) : false;
  const isFailed = status ? ['failed', 'lipsync_failed'].includes(status) : false;
  const isGenerating = isPolling && !isComplete && !isFailed;
  const retryAttempts = currentVideoGenId.current
    ? pollingService.getRetryAttempts(currentVideoGenId.current)
    : 0;

  // Safe progress calculation with defaults
  const progress = {
    overall: calculateOverallProgress(),
    currentStep,
    stepProgress,
    audio: generation?.audio_progress,
    images: generation?.image_progress,
    video: generation?.video_progress,
    merge: generation?.merge_progress,
    lipSync: generation?.lipsync_progress,
  };

  return {
    // Stable return shape as requested
    data: generation,
    error,
    isLoading,
    refetch,
    
    // Additional state for backward compatibility
    generation,
    status,
    isPolling,
    retryAttempts,
    
    // Progress data
    progress,
    
    // Control functions
    startPolling,
    stopPolling,
    retry,
    clearError,
    
    // Status checks
    isComplete,
    isFailed,
    isGenerating,
  };
};

// Additional specialized hooks
export const useGenerationProgress = (videoGenId?: string) => {
  const { progress } = useVideoGenerationStatus(videoGenId);
  return progress;
};

export const useGenerationMessages = (videoGenId?: string) => {
  const { generation, status } = useVideoGenerationStatus(videoGenId);
  
    // Update the getStatusMessage function in useGenerationMessages:
  const getStatusMessage = (): string => {
    if (!status) return '';
    
    switch (status) {
      case 'generating_audio': {
        // ✅ Fix: Wrap in braces to create block scope
        const audioFiles = generation?.audio_progress;
        if (audioFiles) {
          const total = audioFiles.narrator_files + audioFiles.character_files + audioFiles.sound_effects;
          return `Generating audio files... (${total} files created)`;
        }
        return 'Generating narrator voice and character dialogue...';
      }
      
      case 'generating_images': {
        // ✅ Fix: Wrap in braces to create block scope
        const imageProgress = generation?.image_progress;
        if (imageProgress) {
          return `Creating character images (${imageProgress.characters_completed}/${imageProgress.total_characters} completed)`;
        }
        return 'Generating character images and scene visuals...';
      }
      
      case 'generating_video': {
        // ✅ Fix: Wrap in braces to create block scope
        const videoProgress = generation?.video_progress;
        if (videoProgress) {
          return `Processing Scene ${videoProgress.scenes_completed} of ${videoProgress.total_scenes}...`;
        }
        return 'Creating video segments for each scene...';
      }
      
      case 'merging_audio':
        return 'Merging audio tracks with video content...';
      
      case 'applying_lipsync':
        return 'Applying lip sync to character dialogue...';
      
      case 'completed':
        return 'Video generation completed successfully!';
      
      default:
        return 'Processing...';
    }
  };
  
  return {
    currentMessage: getStatusMessage(),
    generation,
    status
  };
};