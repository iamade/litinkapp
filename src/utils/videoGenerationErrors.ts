import { toast } from 'react-hot-toast';

export interface VideoGenerationError {
  status: string;
  message?: string;
  error?: string;
  step?: string;
  generationId?: string;
}

/**
 * Maps backend error messages to user-friendly messages
 */
export const getErrorMessage = (error: VideoGenerationError): string => {
  const errorMessage = error.error || error.message || 'Unknown error occurred';
  
  // Handle specific error patterns
  if (errorMessage.includes('[MERGE] No valid scene videos found')) {
    return 'Video generation failed: No valid videos were created to merge. This could be due to content restrictions or generation issues.';
  }
  
  if (errorMessage.includes('Audio/Video merge failed')) {
    return 'Failed to combine audio and video. Please try again or contact support.';
  }
  
  if (errorMessage.includes('safety checker')) {
    return 'Content was flagged by safety filters. Please modify your script and try again.';
  }
  
  if (errorMessage.includes('API') || errorMessage.includes('timeout')) {
    return 'Service temporarily unavailable. Please try again in a moment.';
  }
  
  if (errorMessage.includes('network') || errorMessage.includes('connection')) {
    return 'Network connection issue. Please check your internet and try again.';
  }
  
  if (errorMessage.includes('No valid scene videos')) {
    return 'Video generation failed to create any valid scenes. Please check your script content.';
  }
  
  // Generic error mapping based on step
  if (error.step) {
    switch (error.step) {
      case 'video_generation':
        return 'Failed to generate video scenes. Please try again with different content.';
      case 'merge':
        return 'Failed to merge video components. Please try again.';
      case 'audio_generation':
        return 'Failed to generate audio. Please check your script and try again.';
      case 'image_generation':
        return 'Failed to generate images. Please modify character descriptions and try again.';
      case 'lip_sync':
        return 'Failed to apply lip sync. Please try again.';
      default:
        return `Failed during ${error.step.replace('_', ' ')}. Please try again.`;
    }
  }
  
  // Fallback to original message with some cleaning
  return errorMessage.replace(/\[.*?\]/g, '').trim() || 'An unexpected error occurred.';
};

/**
 * Shows a user-friendly error notification for video generation failures
 */
export const showVideoGenerationError = (error: VideoGenerationError): void => {
  const userMessage = getErrorMessage(error);
  const generationInfo = error.generationId ? ` (Generation: ${error.generationId.slice(-8)})` : '';
  
  const errorDetails = `Video Generation Failed${generationInfo}\n\n${userMessage}\n\nYou can retry the generation or contact support if the issue persists.`;
  
  toast.error(errorDetails, {
    duration: 15000, // 15 seconds for users to read
    position: 'top-right',
    style: {
      background: '#fef2f2',
      border: '1px solid #fecaca',
      color: '#991b1b',
      maxWidth: '400px',
    },
  });
};

/**
 * Shows a success notification for completed generation
 */
export const showVideoGenerationSuccess = (generationId?: string): void => {
  const generationInfo = generationId ? ` (${generationId.slice(-8)})` : '';
  
  toast.success(
    `Video Generation Complete${generationInfo}\nYour video has been successfully generated and is ready to view.`,
    {
      duration: 8000, // 8 seconds
      position: 'top-right',
    }
  );
};

/**
 * Checks if a pipeline status indicates failure and shows appropriate notification
 */
interface PipelineStep {
  step_name: string;
  status: string;
  error_message?: string;
}

interface PipelineStatus {
  overall_status: string;
  message?: string;
  error?: string;
  steps: PipelineStep[];
}

export const handlePipelineStatusError = (
  pipelineStatus: PipelineStatus | null,
  generationId?: string
): boolean => {
  if (!pipelineStatus) return false;
  
  const { overall_status, steps = [] } = pipelineStatus;
  
  // Check for overall failure
  if (overall_status === 'failed') {
    const failedSteps = steps.filter((step: PipelineStep) => step.status === 'failed');
    const firstFailedStep = failedSteps[0];
    
    showVideoGenerationError({
      status: 'failed',
      message: pipelineStatus.message,
      error: firstFailedStep?.error_message || pipelineStatus.error,
      step: firstFailedStep?.step_name,
      generationId,
    });
    
    return true;
  }
  
  // Check for individual step failures even if overall status isn't failed yet
  const failedSteps = steps.filter((step: PipelineStep) => step.status === 'failed');
  if (failedSteps.length > 0 && overall_status !== 'failed') {
    const firstFailedStep = failedSteps[0];
    
    showVideoGenerationError({
      status: 'step_failed',
      message: `Step failed: ${firstFailedStep.step_name}`,
      error: firstFailedStep.error_message,
      step: firstFailedStep.step_name,
      generationId,
    });
    
    return true;
  }
  
  return false;
};

/**
 * Checks if a video generation status indicates failure and shows appropriate notification
 */
interface VideoGeneration {
  generation_status: string;
  error_message?: string;
}

export const handleVideoGenerationStatusError = (
  generation: VideoGeneration | null,
  generationId?: string
): boolean => {
  if (!generation) return false;
  
  const { generation_status, error_message } = generation;
  
  // Check for failure statuses
  if (['failed', 'lipsync_failed'].includes(generation_status)) {
    showVideoGenerationError({
      status: generation_status,
      message: error_message,
      error: error_message,
      generationId,
    });
    
    return true;
  }
  
  return false;
};