import { videoGenerationAPI, VideoGeneration, GenerationStatus } from '../lib/videoGenerationApi';
import { handleVideoGenerationStatusError, showVideoGenerationSuccess } from '../utils/videoGenerationErrors';

export interface PollingConfig {
  interval: number;
  maxRetries: number;
  retryDelay: number;
  stopOnComplete: boolean;
}

export interface PollingCallbacks {
  onUpdate: (generation: VideoGeneration) => void;
  onError: (error: Error) => void;
  onComplete: (generation: VideoGeneration) => void;
  onRetry?: (attempt: number, error: Error) => void;
}

// New types for the enhanced status response
export interface VideoGenerationStatusResponse {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  current_step: string;
  progress_percentage: number;
  steps: {
    image_generation: { status: string; progress: number };
    audio_generation: { status: string; progress: number };
    video_generation: { status: string; progress: number };
    audio_video_merge: { status: string; progress: number };
  };
  error: string | null;
  video_url: string | null;
}

class VideoGenerationPolling {
  private timers: Map<string, NodeJS.Timeout> = new Map();
  private retryAttempts: Map<string, number> = new Map();
  private pollingAttempts: Map<string, number> = new Map();
  private pollingStartTimes: Map<string, number> = new Map();
  
  private getPollingInterval(status: string): number {
    // Smart polling - adjust interval based on generation phase
    switch (status) {
      case 'pending':
        return 3000; // 3 seconds - initial state
      case 'processing':
        return 2000; // 2 seconds - active processing
      case 'completed':
        return 0; // Stop polling
      case 'failed':
        return 0; // Stop polling
      default:
        return 2500; // 2.5 seconds default
    }
  }

  private isCompleteStatus(status: string): boolean {
    return ['completed', 'failed'].includes(status);
  }

  // Helper method to convert new status response to existing VideoGeneration format
  private convertStatusResponse(
    videoGenId: string,
    statusResponse: VideoGenerationStatusResponse
  ): VideoGeneration {
    // Map the new status format to the existing VideoGeneration structure
    const generationStatus: GenerationStatus = this.mapStatusToGenerationStatus(statusResponse.status);
    
    return {
      id: videoGenId,
      script_id: '', // Will be populated from existing data
      user_id: '', // Will be populated from existing data
      quality_tier: 'free', // Default, will be updated
      generation_status: generationStatus,
      video_url: statusResponse.video_url || undefined,
      created_at: new Date().toISOString(),
      error_message: statusResponse.error || undefined,
      // Map step progress to existing progress structures
      audio_progress: {
        narrator_files: 0,
        character_files: 0,
        sound_effects: 0,
        background_music: 0
      },
      image_progress: {
        total_characters: 0,
        characters_completed: 0,
        total_scenes: 0,
        scenes_completed: 0,
        total_images_generated: 0,
        success_rate: statusResponse.steps.image_generation.progress
      },
      video_progress: {
        total_scenes: 0,
        scenes_completed: 0,
        total_videos_generated: 0,
        successful_videos: 0,
        failed_videos: 0,
        success_rate: statusResponse.steps.video_generation.progress
      },
      merge_progress: {
        total_scenes_merged: 0,
        total_duration: 0,
        audio_tracks_mixed: 0,
        file_size_mb: 0,
        processing_time: 0,
        sync_accuracy: 'pending'
      },
      lipsync_progress: {
        characters_lip_synced: 0,
        scenes_processed: 0,
        processing_method: 'pending',
        total_scenes_processed: 0,
        scenes_with_lipsync: 0
      }
    };
  }

  private mapStatusToGenerationStatus(status: string): GenerationStatus {
    switch (status) {
      case 'pending':
        return 'generating_audio';
      case 'processing':
        return 'generating_video';
      case 'completed':
        return 'completed';
      case 'failed':
        return 'failed';
      default:
        return 'generating_audio';
    }
  }

  async startPolling(
    videoGenId: string,
    callbacks: PollingCallbacks,
    config: Partial<PollingConfig> = {}
  ): Promise<void> {
    const finalConfig: PollingConfig = {
      interval: 2500,
      maxRetries: 5,
      retryDelay: 2000,
      stopOnComplete: true,
      ...config
    };

    // Stop existing polling for this ID
    this.stopPolling(videoGenId);
    
    // Reset retry attempts and start tracking polling
    this.retryAttempts.set(videoGenId, 0);
    this.pollingAttempts.set(videoGenId, 0);
    this.pollingStartTimes.set(videoGenId, Date.now());

    const poll = async () => {
      try {
        // Increment polling attempt counter
        const currentPollingAttempt = (this.pollingAttempts.get(videoGenId) || 0) + 1;
        this.pollingAttempts.set(videoGenId, currentPollingAttempt);
        
        // Use the new backend endpoint for status polling
        const statusResponse = await videoGenerationAPI.getEnhancedGenerationStatus(videoGenId);
        
        // Reset retry attempts on successful poll
        this.retryAttempts.set(videoGenId, 0);
        
        // Convert to existing VideoGeneration format for compatibility
        const generation = this.convertStatusResponse(videoGenId, statusResponse);
        
        // Check for errors and show notifications
        handleVideoGenerationStatusError(generation, videoGenId);

        // Call update callback with enhanced polling info
        const enhancedGeneration = {
          ...generation,
          polling_info: {
            attempt: currentPollingAttempt,
            max_attempts: 24, // 2 minutes at 5-second intervals
            elapsed_time: Date.now() - (this.pollingStartTimes.get(videoGenId) || Date.now()),
            is_fallback_retrieval: currentPollingAttempt > 12 // After 1 minute, start fallback
          }
        };
        
        callbacks.onUpdate(enhancedGeneration);

        // Check if generation is complete
        if (this.isCompleteStatus(statusResponse.status)) {
          // Show success notification for completed generation
          if (statusResponse.status === 'completed') {
            showVideoGenerationSuccess(videoGenId);
          }
          
          callbacks.onComplete(enhancedGeneration);
          
          if (finalConfig.stopOnComplete) {
            this.stopPolling(videoGenId);
            return;
          }
        }

        // Schedule next poll with smart interval
        const nextInterval = this.getPollingInterval(statusResponse.status);
        if (nextInterval > 0) {
          const timer = setTimeout(poll, nextInterval);
          this.timers.set(videoGenId, timer);
        }

      } catch (error) {
        const currentAttempts = this.retryAttempts.get(videoGenId) || 0;
        
        if (currentAttempts < finalConfig.maxRetries) {
          // Increment retry attempts
          this.retryAttempts.set(videoGenId, currentAttempts + 1);
          
          // Call retry callback if provided
          if (callbacks.onRetry) {
            callbacks.onRetry(currentAttempts + 1, error as Error);
          }
          
          // Schedule retry with delay
          const timer = setTimeout(poll, finalConfig.retryDelay);
          this.timers.set(videoGenId, timer);
        } else {
          // Max retries reached, call error callback
          callbacks.onError(error as Error);
          this.stopPolling(videoGenId);
        }
      }
    };

    // Start polling immediately
    poll();
  }

  stopPolling(videoGenId: string): void {
    const timer = this.timers.get(videoGenId);
    if (timer) {
      clearTimeout(timer);
      this.timers.delete(videoGenId);
    }
    this.retryAttempts.delete(videoGenId);
    this.pollingAttempts.delete(videoGenId);
    this.pollingStartTimes.delete(videoGenId);
  }

  stopAllPolling(): void {
    for (const [videoGenId] of this.timers) {
      this.stopPolling(videoGenId);
    }
  }

  isPolling(videoGenId: string): boolean {
    return this.timers.has(videoGenId);
  }

  getRetryAttempts(videoGenId: string): number {
    return this.retryAttempts.get(videoGenId) || 0;
  }

  getPollingAttempts(videoGenId: string): number {
    return this.pollingAttempts.get(videoGenId) || 0;
  }

  getPollingElapsedTime(videoGenId: string): number {
    const startTime = this.pollingStartTimes.get(videoGenId);
    return startTime ? Date.now() - startTime : 0;
  }

  isFallbackRetrieval(videoGenId: string): boolean {
    const attempts = this.pollingAttempts.get(videoGenId) || 0;
    return attempts > 12; // After 1 minute (12 attempts at 5s intervals)
  }
}

// Export singleton instance
export const pollingService = new VideoGenerationPolling();
export default pollingService;