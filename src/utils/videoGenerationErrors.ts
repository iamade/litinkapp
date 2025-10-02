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
  
  // Handle polling-specific error patterns
  if (errorMessage.includes('generation_failed') || errorMessage.includes('failed to generate')) {
    return 'Video generation failed: The AI service was unable to create the video. This may be due to content complexity or service limitations.';
  }
  
  if (errorMessage.includes('timeout') || errorMessage.includes('timed out')) {
    return 'Video generation timeout: The operation took too long to complete. This can happen with longer videos or during high service load.';
  }
  
  if (errorMessage.includes('retrieval_failed') || errorMessage.includes('fallback')) {
    return 'Video retrieval failed: The video was generated but we encountered issues retrieving it. The system is automatically trying alternative methods.';
  }
  
  if (errorMessage.includes('polling') && errorMessage.includes('max attempts')) {
    return 'Video polling timeout: Unable to retrieve video status after multiple attempts. The system will continue trying in the background.';
  }
  
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
  
  if (errorMessage.includes('API') || errorMessage.includes('service unavailable')) {
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
  
  // Add specific suggestions based on error type
  let suggestion = '';
  const errorLower = (error.error || error.message || '').toLowerCase();
  
  if (errorLower.includes('generation_failed')) {
    suggestion = '\n\n💡 Try generating a shorter video or simplifying your script content.';
  } else if (errorLower.includes('timeout')) {
    suggestion = '\n\n⏱️ This can happen with longer videos. Try generating a shorter version first.';
  } else if (errorLower.includes('retrieval_failed') || errorLower.includes('fallback')) {
    suggestion = '\n\n🔄 The system is automatically trying alternative retrieval methods. Please wait a moment.';
  } else if (errorLower.includes('polling')) {
    suggestion = '\n\n🔄 The system will continue polling in the background. You can check back later.';
  } else {
    suggestion = '\n\n🔄 You can retry the generation or contact support if the issue persists.';
  }
  
  const errorDetails = `Video Generation Failed${generationInfo}\n\n${userMessage}${suggestion}`;
  
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