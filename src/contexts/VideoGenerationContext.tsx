import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
} from "react";
import {
  VideoGeneration,
  GenerationStatus,
  videoGenerationAPI,
} from "../lib/videoGenerationApi";
import { pollingService } from "../services/videoGenerationPolling";

// Simplified state interface
export interface VideoGenerationState {
  currentGeneration: VideoGeneration | null;
  isGenerating: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

// Context interface
interface VideoGenerationContextType {
  state: VideoGenerationState;
  startGeneration: (
    scriptId: string,
    chapterId: string,
    qualityTier: "free" | "premium" | "professional"
  ) => Promise<string>;
  stopPolling: () => void;
  resetGeneration: () => void;
  clearError: () => void;
}

// Create context
const VideoGenerationContext = createContext<
  VideoGenerationContextType | undefined
>(undefined);

// Provider component
export const VideoGenerationProvider: React.FC<{
  children: React.ReactNode;
}> = ({ children }) => {
  const [state, setState] = useState<VideoGenerationState>({
    currentGeneration: null,
    isGenerating: false,
    error: null,
    lastUpdated: null,
  });

  const currentVideoGenId = useRef<string | null>(null);

  // Start polling for status updates
  const startPolling = useCallback((videoGenId: string) => {
    currentVideoGenId.current = videoGenId;

    pollingService.startPolling(videoGenId, {
      onUpdate: (generation) => {
        setState((prev) => ({
          ...prev,
          currentGeneration: generation,
          isGenerating: !["completed", "failed", "lipsync_failed"].includes(
            generation.generation_status
          ),
          lastUpdated: new Date(),
          error: generation.error_message || null,
        }));
      },
      onError: (error) => {
        setState((prev) => ({
          ...prev,
          error: error.message,
          lastUpdated: new Date(),
        }));
      },
      onComplete: (generation) => {
        setState((prev) => ({
          ...prev,
          currentGeneration: generation,
          isGenerating: false,
          lastUpdated: new Date(),
        }));
      },
    });
  }, []);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (currentVideoGenId.current) {
      pollingService.stopPolling(currentVideoGenId.current);
      currentVideoGenId.current = null;
    }
  }, []);

  // Start video generation
  const startGeneration = useCallback(
    async (
      scriptId: string,
      chapterId: string,
      qualityTier: "free" | "premium" | "professional"
    ): Promise<string> => {
      try {
        setState((prev) => ({ ...prev, error: null }));

        const response = await videoGenerationAPI.startVideoGeneration(
          scriptId,
          chapterId,
          qualityTier
        );

        setState((prev) => ({
          ...prev,
          isGenerating: true,
          error: null,
          lastUpdated: new Date(),
        }));

        // Start polling for updates
        startPolling(response.video_generation_id);

        return response.video_generation_id;
      } catch (error) {
        const errorMessage =
          error instanceof Error
            ? error.message
            : "Failed to start video generation";
        setState((prev) => ({
          ...prev,
          error: errorMessage,
          isGenerating: false,
          lastUpdated: new Date(),
        }));
        throw error;
      }
    },
    [startPolling]
  );

  // Reset generation
  const resetGeneration = useCallback(() => {
    stopPolling();
    setState({
      currentGeneration: null,
      isGenerating: false,
      error: null,
      lastUpdated: null,
    });
  }, [stopPolling]);

  // Clear error
  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  // Context value
  const value: VideoGenerationContextType = {
    state,
    startGeneration,
    stopPolling,
    resetGeneration,
    clearError,
  };

  return (
    <VideoGenerationContext.Provider value={value}>
      {children}
    </VideoGenerationContext.Provider>
  );
};

// Custom hook to use the context
export const useVideoGeneration = (): VideoGenerationContextType => {
  const context = useContext(VideoGenerationContext);
  if (!context) {
    throw new Error(
      "useVideoGeneration must be used within a VideoGenerationProvider"
    );
  }
  return context;
};

// Helper hooks for specific data
export const useGenerationStatus = (): GenerationStatus | null => {
  const { state } = useVideoGeneration();
  return state.currentGeneration?.generation_status || null;
};

export const useGenerationProgress = () => {
  const { state } = useVideoGeneration();
  const generation = state.currentGeneration;

  if (!generation) return null;

  // Calculate overall progress based on status
  const calculateProgress = (status: GenerationStatus): number => {
    switch (status) {
      case "generating_audio":
        return 15;
      case "audio_completed":
        return 25;
      case "generating_images":
        return 25 + (generation.image_progress?.success_rate || 0) * 0.25;
      case "images_completed":
        return 50;
      case "generating_video":
        return 50 + (generation.video_progress?.success_rate || 0) * 0.25;
      case "video_completed":
        return 75;
      case "merging_audio":
        return 85;
      case "applying_lipsync":
        return 95;
      case "lipsync_completed":
      case "completed":
        return 100;
      case "failed":
      case "lipsync_failed":
        return 0;
      default:
        return 0;
    }
  };

  return {
    overall: calculateProgress(generation.generation_status),
    audio: generation.audio_progress,
    images: generation.image_progress,
    video: generation.video_progress,
    merge: generation.merge_progress,
    lipSync: generation.lipsync_progress,
  };
};

export default VideoGenerationContext;
