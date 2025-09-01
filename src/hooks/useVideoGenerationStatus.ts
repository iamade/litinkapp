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

export interface UseVideoGenerationStatusReturn {
  // Current state
  generation: VideoGeneration | null;
  status: GenerationStatus | null;
  isPolling: boolean;
  error: Error | null;
  retryAttempts: number;
  
  // Progress data
  progress: {
    overall: number;
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
  const [generation, setGeneration] = useState<VideoGeneration | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const currentVideoGenId = useRef<string | null>(null);

  // Calculate overall progress
  const calculateOverallProgress = (status: GenerationStatus | null): number => {
    if (!status) return 0;
    
    switch (status) {
      case 'generating_audio': return 15;
      case 'audio_completed': return 25;
      case 'generating_images': 
        return 25 + ((generation?.image_progress?.success_rate || 0) * 0.25);
      case 'images_completed': return 50;
      case 'generating_video': 
        return 50 + ((generation?.video_progress?.success_rate || 0) * 0.25);
      case 'video_completed': return 75;
      case 'merging_audio': return 85;
      case 'applying_lipsync': return 95;
      case 'lipsync_completed':
      case 'completed': return 100;
      case 'failed':
      case 'lipsync_failed': return 0;
      default: return 0;
    }
  };

  // Polling callbacks
  const callbacks: PollingCallbacks = {
    onUpdate: (updatedGeneration) => {
      setGeneration(updatedGeneration);
      setError(null);
    },
    onError: (pollingError) => {
      setError(pollingError);
      setIsPolling(false);
    },
    onComplete: (completedGeneration) => {
      setGeneration(completedGeneration);
      setIsPolling(false);
    },
    onRetry: (attempt, retryError) => {
      console.log(`Polling retry attempt ${attempt}:`, retryError.message);
    }
  };

  // Start polling function
  const startPolling = useCallback((newVideoGenId: string) => {
    if (currentVideoGenId.current) {
      pollingService.stopPolling(currentVideoGenId.current);
    }
    
    currentVideoGenId.current = newVideoGenId;
    setIsPolling(true);
    setError(null);
    
    pollingService.startPolling(newVideoGenId, callbacks);
  }, []);

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

  // Derived state
  const status = generation?.generation_status || null;
  const isComplete = status ? ['completed', 'lipsync_completed'].includes(status) : false;
  const isFailed = status ? ['failed', 'lipsync_failed'].includes(status) : false;
  const isGenerating = isPolling && !isComplete && !isFailed;
  const retryAttempts = currentVideoGenId.current 
    ? pollingService.getRetryAttempts(currentVideoGenId.current) 
    : 0;

  const progress = {
    overall: calculateOverallProgress(status),
    audio: generation?.audio_progress,
    images: generation?.image_progress,
    video: generation?.video_progress,
    merge: generation?.merge_progress,
    lipSync: generation?.lipsync_progress,
  };

  return {
    // Current state
    generation,
    status,
    isPolling,
    error,
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
  
  const getStatusMessage = (): string => {
    if (!status) return '';
    
    switch (status) {
      case 'generating_audio':
        const audioFiles = generation?.audio_progress;
        if (audioFiles) {
          const total = audioFiles.narrator_files + audioFiles.character_files + audioFiles.sound_effects;
          return `Generating audio files... (${total} files created)`;
        }
        return 'Generating narrator voice and character dialogue...';
        
      case 'generating_images':
        const imageProgress = generation?.image_progress;
        if (imageProgress) {
          return `Creating character images (${imageProgress.characters_completed}/${imageProgress.total_characters} completed)`;
        }
        return 'Generating character images and scene visuals...';
        
      case 'generating_video':
        const videoProgress = generation?.video_progress;
        if (videoProgress) {
          return `Processing Scene ${videoProgress.scenes_completed} of ${videoProgress.total_scenes}...`;
        }
        return 'Creating video segments for each scene...';
        
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