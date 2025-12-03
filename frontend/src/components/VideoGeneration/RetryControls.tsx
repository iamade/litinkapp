import React, { useState } from 'react';
import { RetryControlsProps, RetryOption } from '../../types/retryControls';



const RETRY_OPTIONS: RetryOption[] = [
  {
    value: 'audio_generation',
    label: 'Audio Generation',
    description: 'Regenerate all audio (narrator, characters, effects)',
    icon: '🎵'
  },
  {
    value: 'image_generation',
    label: 'Image Generation',
    description: 'Regenerate scene images and character visuals',
    icon: '🖼️'
  },
  {
    value: 'video_generation',
    label: 'Video Generation',
    description: 'Regenerate video sequences from images',
    icon: '🎬'
  },
  {
    value: 'audio_video_merge',
    label: 'Audio-Video Merge',
    description: 'Re-merge audio with video sequences',
    icon: '🔗'
  },
  {
    value: 'lip_sync',
    label: 'Lip Synchronization',
    description: 'Reapply lip sync to character videos',
    icon: '💋'
  }
];

export const RetryControls: React.FC<RetryControlsProps> = ({
  pipelineStatus,
  onRetry,
  isRetrying,
  retryError,
  className = ''
}) => {
  const [selectedStep, setSelectedStep] = useState<string>('');
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [showStepSelector, setShowStepSelector] = useState(false);

  // Check if generation can be retried
  const canRetry = pipelineStatus.can_resume && 
                  ['failed', 'completed'].includes(pipelineStatus.overall_status);

  // Get failed step for quick retry
  const failedStep = pipelineStatus.failed_at_step;
  const failedStepOption = RETRY_OPTIONS.find(option => option.value === failedStep);

  // Get available retry options (only steps that are pending or failed)
  const availableRetryOptions = RETRY_OPTIONS.filter(option => {
    const step = pipelineStatus.steps.find(s => s.step_name === option.value);
    return step && ['pending', 'failed'].includes(step.status);
  });

  const handleQuickRetry = () => {
    if (failedStep) {
      setSelectedStep(failedStep);
      setShowConfirmDialog(true);
    } else {
      // Retry from next pending step
      const nextStep = pipelineStatus.progress.next_step;
      if (nextStep) {
        setSelectedStep(nextStep);
        setShowConfirmDialog(true);
      }
    }
  };

  const handleCustomRetry = () => {
    setShowStepSelector(true);
  };

  const handleRetryConfirm = async () => {
    if (selectedStep) {
      await onRetry(selectedStep);
      setShowConfirmDialog(false);
      setShowStepSelector(false);
      setSelectedStep('');
    }
  };

  const handleRetryCancel = () => {
    setShowConfirmDialog(false);
    setShowStepSelector(false);
    setSelectedStep('');
  };

  if (!canRetry) {
    return null;
  }

  return (
    <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Retry Generation
        </h3>
        {pipelineStatus.retry_count > 0 && (
          <span className="text-sm text-gray-500">
            Retries: {pipelineStatus.retry_count}
          </span>
        )}
      </div>

      {retryError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">{retryError}</p>
        </div>
      )}

      <div className="space-y-4">
        {/* Quick Retry Button */}
        {failedStep && failedStepOption && (
          <div>
            <p className="text-sm text-gray-600 mb-3">
              Generation failed at <strong>{failedStepOption.label}</strong>. 
              You can retry from this step or choose a different step.
            </p>
            <button
              onClick={handleQuickRetry}
              disabled={isRetrying}
              className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRetrying ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                <span>{failedStepOption.icon}</span>
              )}
              <span>Retry from {failedStepOption.label}</span>
            </button>
          </div>
        )}

        {/* Custom Step Selector */}
        <div>
          <button
            onClick={handleCustomRetry}
            disabled={isRetrying}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span>⚙️</span>
            <span>Choose Step to Retry From</span>
          </button>
        </div>
      </div>

      {/* Step Selector Modal */}
      {showStepSelector && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 max-h-96 overflow-y-auto">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">
              Select Step to Retry From
            </h4>
            
            <div className="space-y-3 mb-6">
              {availableRetryOptions.map((option) => {
                const step = pipelineStatus.steps.find(s => s.step_name === option.value);
                const isSelected = selectedStep === option.value;
                
                return (
                  <div
                    key={option.value}
                    onClick={() => setSelectedStep(option.value)}
                    className={`
                      p-3 rounded-lg border cursor-pointer transition-colors
                      ${isSelected 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-gray-200 hover:border-gray-300'
                      }
                    `}
                  >
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">{option.icon}</span>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <h5 className="font-medium text-gray-900">
                            {option.label}
                          </h5>
                          <span className={`
                            text-xs px-2 py-1 rounded-full
                            ${step?.status === 'failed' 
                              ? 'bg-red-100 text-red-800' 
                              : 'bg-gray-100 text-gray-800'
                            }
                          `}>
                            {step?.status || 'pending'}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">
                          {option.description}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-end space-x-3">
              <button
                onClick={handleRetryCancel}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowStepSelector(false);
                  setShowConfirmDialog(true);
                }}
                disabled={!selectedStep}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Dialog */}
      {showConfirmDialog && selectedStep && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">
              Confirm Retry
            </h4>
            
            <div className="mb-6">
              <p className="text-gray-700 mb-3">
                Are you sure you want to retry generation from:
              </p>
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-center space-x-2">
                  <span className="text-lg">
                    {RETRY_OPTIONS.find(o => o.value === selectedStep)?.icon}
                  </span>
                  <span className="font-medium text-blue-900">
                    {RETRY_OPTIONS.find(o => o.value === selectedStep)?.label}
                  </span>
                </div>
                <p className="text-sm text-blue-700 mt-1">
                  {RETRY_OPTIONS.find(o => o.value === selectedStep)?.description}
                </p>
              </div>
              <p className="text-sm text-gray-600 mt-3">
                This will restart the generation process from this step onwards. 
                Any existing content from this step will be replaced.
              </p>
            </div>

            <div className="flex items-center justify-end space-x-3">
              <button
                onClick={handleRetryCancel}
                disabled={isRetrying}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleRetryConfirm}
                disabled={isRetrying}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isRetrying ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                ) : (
                  <span>🔄</span>
                )}
                <span>{isRetrying ? 'Retrying...' : 'Confirm Retry'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RetryControls;