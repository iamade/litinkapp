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

class VideoGenerationPolling {
  private timers: Map<string, NodeJS.Timeout> = new Map();
  private retryAttempts: Map<string, number> = new Map();
  
  private getPollingInterval(status: GenerationStatus): number {
    // Smart polling - adjust interval based on generation phase
    switch (status) {
      case 'generating_audio':
      case 'generating_images': 
        return 2000; // 2 seconds - these are longer processes
      case 'generating_video':
        return 3000; // 3 seconds - video generation is slowest
      case 'merging_audio':
      case 'applying_lipsync':
        return 1500; // 1.5 seconds - shorter processes
      case 'audio_completed':
      case 'images_completed':
      case 'video_completed':
        return 1000; // 1 second - transition states
      default:
        return 2500; // 2.5 seconds default
    }
  }

  private isCompleteStatus(status: GenerationStatus): boolean {
    return ['completed', 'failed', 'lipsync_failed'].includes(status);
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
    
    // Reset retry attempts
    this.retryAttempts.set(videoGenId, 0);

    const poll = async () => {
      try {
        const generation = await videoGenerationAPI.getGenerationStatus(videoGenId);
        
        // Reset retry attempts on successful poll
        this.retryAttempts.set(videoGenId, 0);
        
        // Check for errors and show notifications
        handleVideoGenerationStatusError(generation, videoGenId);

        // Call update callback
        callbacks.onUpdate(generation);

        // Check if generation is complete
        if (this.isCompleteStatus(generation.generation_status)) {
          // Show success notification for completed generation
          if (generation.generation_status === 'completed') {
            showVideoGenerationSuccess(videoGenId);
          }
          
          callbacks.onComplete(generation);
          
          if (finalConfig.stopOnComplete) {
            this.stopPolling(videoGenId);
            return;
          }
        }

        // Schedule next poll with smart interval
        const nextInterval = this.getPollingInterval(generation.generation_status);
        const timer = setTimeout(poll, nextInterval);
        this.timers.set(videoGenId, timer);

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
}

// Export singleton instance
export const pollingService = new VideoGenerationPolling();
export default pollingService;