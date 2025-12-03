import React from 'react';
import type { PipelineStatus } from '../../types/pipelinestatus';
import { PipelineStep, PipelineVisualizationProps } from "../../types/pipelineVisualization";



const PIPELINE_STEPS: PipelineStep[] = [
  {
    key: 'audio_generation',
    name: 'Audio',
    icon: '🎵',
    description: 'Generating narrator voice, character dialogues, and sound effects',
    estimatedTime: '2-4 min'
  },
  {
    key: 'image_generation', 
    name: 'Images',
    icon: '🖼️',
    description: 'Creating scene images and character visuals',
    estimatedTime: '3-6 min'
  },
  {
    key: 'video_generation',
    name: 'Videos',
    icon: '🎬',
    description: 'Generating video sequences from images',
    estimatedTime: '5-10 min'
  },
  {
    key: 'audio_video_merge',
    name: 'Merge',
    icon: '🔗',
    description: 'Combining audio with video sequences',
    estimatedTime: '1-2 min'
  },
  {
    key: 'lip_sync',
    name: 'Lip Sync',
    icon: '💋',
    description: 'Applying lip synchronization to characters',
    estimatedTime: '2-4 min'
  }
];

const getStepStatus = (stepKey: string, pipelineStatus: PipelineStatus) => {
  const step = pipelineStatus.steps.find(s => s.step_name === stepKey);
  return step?.status || 'pending';
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'bg-green-500 text-white';
    case 'processing':
      return 'bg-blue-500 text-white animate-pulse';
    case 'failed':
      return 'bg-red-500 text-white';
    case 'pending':
      return 'bg-gray-200 text-gray-600';
    case 'skipped':
      return 'bg-yellow-200 text-yellow-800';
    default:
      return 'bg-gray-200 text-gray-600';
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return '✅';
    case 'processing':
      return '⏳';
    case 'failed':
      return '❌';
    case 'pending':
      return '⏸️';
    case 'skipped':
      return '⏭️';
    default:
      return '⏸️';
  }
};

export const PipelineVisualization: React.FC<PipelineVisualizationProps> = ({
  pipelineStatus,
  className = ''
}) => {
  const currentStepIndex = PIPELINE_STEPS.findIndex(
    step => step.key === pipelineStatus.progress.current_step
  );

  return (
    <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          Pipeline Progress
        </h3>
        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-500">
            {pipelineStatus.progress.completed_steps} / {pipelineStatus.progress.total_steps} steps
          </div>
          <div className="text-sm font-medium text-blue-600">
            {pipelineStatus.progress.percentage.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-8">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${pipelineStatus.progress.percentage}%` }}
        />
      </div>

      {/* Pipeline Steps */}
      <div className="relative">
        {/* Connection Line */}
        <div className="absolute top-8 left-8 right-8 h-0.5 bg-gray-200 -z-10">
          <div
            className="bg-blue-500 h-full transition-all duration-500 ease-out"
            style={{
              width: currentStepIndex >= 0 ? `${(currentStepIndex / (PIPELINE_STEPS.length - 1)) * 100}%` : '0%'
            }}
          />
        </div>

        <div className="flex justify-between items-start">
          {PIPELINE_STEPS.map((step, index) => {
            const status = getStepStatus(step.key, pipelineStatus);
            const isActive = step.key === pipelineStatus.progress.current_step;
            const stepData = pipelineStatus.steps.find(s => s.step_name === step.key);

            return (
              <div key={step.key} className="flex flex-col items-center max-w-32">
                {/* Step Circle */}
                <div
                  className={`
                    relative w-16 h-16 rounded-full border-4 flex items-center justify-center text-lg font-medium
                    transition-all duration-300 z-10
                    ${getStatusColor(status)}
                    ${isActive ? 'ring-4 ring-blue-200 scale-110' : ''}
                    ${status === 'failed' ? 'ring-4 ring-red-200' : ''}
                  `}
                >
                  <span className="absolute -top-2 -right-2 text-sm">
                    {getStatusIcon(status)}
                  </span>
                  {step.icon}
                </div>

                {/* Step Info */}
                <div className="mt-3 text-center">
                  <h4 className={`text-sm font-medium ${isActive ? 'text-blue-600' : 'text-gray-900'}`}>
                    {step.name}
                  </h4>
                  <p className="text-xs text-gray-500 mt-1 max-w-24 leading-tight">
                    {step.description}
                  </p>
                  
                  {status === 'processing' && (
                    <div className="mt-2">
                      <div className="text-xs text-blue-600 font-medium">
                        Processing...
                      </div>
                      <div className="text-xs text-gray-400">
                        {step.estimatedTime}
                      </div>
                    </div>
                  )}
                  
                  {status === 'failed' && stepData?.error_message && (
                    <div className="mt-2">
                      <div className="text-xs text-red-600 font-medium">
                        Failed
                      </div>
                      <div className="text-xs text-red-500 max-w-24 leading-tight">
                        {stepData.error_message.substring(0, 30)}...
                      </div>
                    </div>
                  )}
                  
                  {status === 'completed' && stepData?.completed_at && (
                    <div className="mt-2">
                      <div className="text-xs text-green-600 font-medium">
                        ✓ Done
                      </div>
                    </div>
                  )}
                  
                  {status === 'pending' && (
                    <div className="mt-2">
                      <div className="text-xs text-gray-400">
                        {step.estimatedTime}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Current Step Details */}
      {pipelineStatus.progress.current_step && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-center space-x-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span className="text-sm font-medium text-blue-900">
              Currently: {PIPELINE_STEPS.find(s => s.key === pipelineStatus.progress.current_step)?.name}
            </span>
          </div>
          <p className="text-sm text-blue-700 mt-1">
            {PIPELINE_STEPS.find(s => s.key === pipelineStatus.progress.current_step)?.description}
          </p>
        </div>
      )}

      {/* Failed Step Alert */}
      {pipelineStatus.overall_status === 'failed' && pipelineStatus.failed_at_step && (
        <div className="mt-6 p-4 bg-red-50 rounded-lg border border-red-200">
          <div className="flex items-center space-x-2">
            <span className="text-red-500">❌</span>
            <span className="text-sm font-medium text-red-900">
              Failed at: {PIPELINE_STEPS.find(s => s.key === pipelineStatus.failed_at_step)?.name}
            </span>
          </div>
          <p className="text-sm text-red-700 mt-1">
            The pipeline stopped due to an error. You can retry from this step or an earlier one.
          </p>
        </div>
      )}
    </div>
  );
};

export default PipelineVisualization;