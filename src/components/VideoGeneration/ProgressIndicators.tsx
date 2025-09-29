import React from 'react';
import { Check, Clock, AlertCircle } from 'lucide-react';
import { GenerationStatus } from '../../lib/videoGenerationApi';

interface Step {
  number: number;
  title: string;
  description: string;
}

interface ProgressIndicatorsProps {
  currentStep: number;
  overallProgress: number;
  status: GenerationStatus | null;
}

const steps: Step[] = [
  {
    number: 1,
    title: 'Audio Generation',
    description: 'Creating narrator voices and character dialogue'
  },
  {
    number: 2,
    title: 'Image Generation',
    description: 'Generating character images and scene visuals'
  },
  {
    number: 3,
    title: 'Video Generation',
    description: 'Creating video segments for each scene'
  },
  {
    number: 4,
    title: 'Audio/Video Merge',
    description: 'Synchronizing audio with video content'
  },
  {
    number: 5,
    title: 'Lip Sync',
    description: 'Applying realistic lip movements'
  },
  {
    number: 6,
    title: 'Complete',
    description: 'Your video is ready!'
  }
];

export const ProgressIndicators: React.FC<ProgressIndicatorsProps> = ({
  currentStep,
  overallProgress,
  status
}) => {
  const getStepStatus = (stepNumber: number) => {
    if (currentStep === -1) return 'error'; // Failed
    if (stepNumber < currentStep) return 'completed';
    if (stepNumber === currentStep) return 'active';
    return 'pending';
  };

  const getStepIcon = (stepNumber: number, stepStatus: string) => {
    switch (stepStatus) {
      case 'completed':
        return <Check className="w-4 h-4 text-white" />;
      case 'active':
        return <Clock className="w-4 h-4 text-white animate-spin" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-white" />;
      default:
        return <span className="text-white text-sm font-medium">{stepNumber}</span>;
    }
  };

  const getStepColor = (stepStatus: string) => {
    switch (stepStatus) {
      case 'completed':
        return 'bg-green-500';
      case 'active':
        return 'bg-blue-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-300';
    }
  };

  return (
    <div className="space-y-6">
      {/* Overall Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="font-medium text-gray-700">Overall Progress</span>
          <span className="text-gray-600">{Math.round(overallProgress)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className="bg-gradient-to-r from-blue-500 to-purple-500 h-full rounded-full transition-all duration-1000 ease-out"
            style={{ width: `${overallProgress}%` }}
          />
        </div>
      </div>

      {/* Step Indicators */}
      <div className="relative">
        {/* Progress Line */}
        <div className="absolute top-6 left-6 right-6 h-0.5 bg-gray-200">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-1000 ease-out"
            style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
          />
        </div>

        {/* Steps */}
        <div className="relative grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {steps.map((step) => {
            const stepStatus = getStepStatus(step.number);
            return (
              <div key={step.number} className="flex flex-col items-center text-center">
                {/* Step Circle */}
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center ${getStepColor(
                    stepStatus
                  )} transition-colors duration-300 relative z-10`}
                >
                  {getStepIcon(step.number, stepStatus)}
                </div>

                {/* Step Content */}
                <div className="mt-3 space-y-1 max-w-[120px]">
                  <h4
                    className={`text-sm font-medium ${
                      stepStatus === 'active'
                        ? 'text-blue-600'
                        : stepStatus === 'completed'
                        ? 'text-green-600'
                        : stepStatus === 'error'
                        ? 'text-red-600'
                        : 'text-gray-500'
                    }`}
                  >
                    {step.title}
                  </h4>
                  <p className="text-xs text-gray-500 leading-relaxed">
                    {step.description}
                  </p>
                  
                  {/* Status indicator */}
                  {stepStatus === 'active' && (
                    <div className="flex items-center justify-center gap-1 mt-2">
                      <div className="w-1 h-1 bg-blue-500 rounded-full animate-pulse"></div>
                      <div className="w-1 h-1 bg-blue-500 rounded-full animate-pulse delay-100"></div>
                      <div className="w-1 h-1 bg-blue-500 rounded-full animate-pulse delay-200"></div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Current Status Message */}
      {status && (
        <div className="text-center py-2">
          <p className="text-sm text-gray-600">
            {getStatusMessage(status)}
          </p>
        </div>
      )}
    </div>
  );
};

const getStatusMessage = (status: GenerationStatus): string => {
  switch (status) {
    case 'generating_audio':
      return 'Generating character voices and narrator audio...';
    case 'audio_completed':
      return 'Audio generation completed! Moving to image generation...';
    case 'generating_images':
      return 'Creating character images and scene visuals...';
    case 'images_completed':
      return 'Image generation completed! Starting video creation...';
    case 'generating_video':
      return 'Generating video segments for each scene...';
    case 'video_completed':
      return 'Video generation completed! Merging audio and video...';
    case 'merging_audio':
      return 'Synchronizing audio with video content...';
    case 'applying_lipsync':
      return 'Applying realistic lip movements to characters...';
    case 'lipsync_completed':
      return 'Lip sync completed! Finalizing your video...';
    case 'completed':
      return 'Video generation completed successfully!';
    case 'failed':
      return 'Video generation failed. Please try again.';
    case 'lipsync_failed':
      return 'Lip sync failed, but your video is still available without lip sync.';
    default:
      return 'Processing...';
  }
};