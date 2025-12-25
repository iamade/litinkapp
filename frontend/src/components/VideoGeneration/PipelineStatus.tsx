import React from 'react';
import { PipelineStatus as PipelineStatusType } from '../../types/pipelinestatus';

interface PipelineStatusProps {
  pipelineStatus: PipelineStatusType;
  isLoading?: boolean;
  onRefresh?: () => void;
  onRetry?: () => void;
  className?: string;
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'text-green-600 bg-green-100';
    case 'processing':
    case 'generating_audio':
    case 'generating_images':
    case 'generating_videos':
    case 'merging_audio':
    case 'applying_lipsync':
      return 'text-blue-600 bg-blue-100';
    case 'failed':
      return 'text-red-600 bg-red-100';
    case 'retrying':
      return 'text-yellow-600 bg-yellow-100';
    case 'queued':
    case 'pending':
      return 'text-gray-600 bg-gray-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return '✅';
    case 'processing':
    case 'generating_audio':
    case 'generating_images': 
    case 'generating_videos':
    case 'merging_audio':
    case 'applying_lipsync':
      return '⏳';
    case 'failed':
      return '❌';
    case 'retrying':
      return '🔄';
    case 'queued':
    case 'pending':
      return '⏸️';
    default:
      return '❓';
  }
};

const formatStatus = (status: string) => {
  return status
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

const formatDuration = (start: string, end?: string) => {
  const startTime = new Date(start);
  const endTime = end ? new Date(end) : new Date();
  const duration = Math.round((endTime.getTime() - startTime.getTime()) / 1000);
  
  if (duration < 60) {
    return `${duration}s`;
  } else if (duration < 3600) {
    return `${Math.round(duration / 60)}m`;
  } else {
    return `${Math.round(duration / 3600)}h ${Math.round((duration % 3600) / 60)}m`;
  }
};

export const PipelineStatus: React.FC<PipelineStatusProps> = ({
  pipelineStatus,
  isLoading = false,
  onRefresh,
  onRetry,
  className = ''
}) => {
  const { overall_status, progress, steps, retry_count, can_resume } = pipelineStatus;
  
  // Check if there are any failed steps with errors
  const failedSteps = steps.filter(step => step.status === 'failed');
  const hasRecoverableErrors = failedSteps.some(step => 
    step.error_message && (
      step.error_message.includes('safety checker') ||
      step.error_message.includes('API') ||
      step.error_message.includes('timeout') ||
      step.error_message.includes('network')
    )
  );

  return (
    <div className={`bg-white rounded-lg border shadow-sm p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <h3 className="text-lg font-semibold text-gray-900">Generation Status</h3>
          <div className={`
            flex items-center space-x-2 px-3 py-1 rounded-full text-sm font-medium
            ${getStatusColor(overall_status)}
          `}>
            <span>{getStatusIcon(overall_status)}</span>
            <span>{formatStatus(overall_status)}</span>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          {retry_count > 0 && (
            <span className="text-sm text-gray-500">
              Retries: {retry_count}
            </span>
          )}
          
          {can_resume && (
            <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
              Resumable
            </span>
          )}
          
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50"
              title="Refresh status"
            >
              <div className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}>
                🔄
              </div>
            </button>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {overall_status === 'failed' && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start space-x-3">
            <span className="text-red-500 text-xl">⚠️</span>
            <div className="flex-1">
              <h4 className="text-red-900 font-semibold mb-2">Generation Failed</h4>
              <p className="text-red-700 text-sm mb-3">
                The video generation process encountered errors and could not complete successfully.
              </p>
              
              {/* Show specific error messages */}
              {failedSteps.length > 0 && (
                <div className="mb-3">
                  <p className="text-red-700 text-sm font-medium mb-2">Failed Steps:</p>
                  <ul className="text-red-700 text-sm space-y-1">
                    {failedSteps.map(step => (
                      <li key={step.step_name} className="flex items-start space-x-2">
                        <span>•</span>
                        <span>
                          <strong>{formatStatus(step.step_name)}:</strong> {step.error_message}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Retry Actions */}
              <div className="flex items-center space-x-3">
                {onRetry && hasRecoverableErrors && (
                  <button
                    onClick={onRetry}
                    disabled={isLoading}
                    className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? 'Retrying...' : 'Retry Generation'}
                  </button>
                )}
                
                {can_resume && (
                  <button
                    onClick={onRetry}
                    disabled={isLoading}
                    className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? 'Resuming...' : 'Resume from Failed Step'}
                  </button>
                )}
                
                <span className="text-red-600 text-xs">
                  You can retry the generation or contact support if the issue persists.
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Progress Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">
            {progress.completed_steps}
          </div>
          <div className="text-sm text-gray-500">Completed</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-red-600">
            {progress.failed_steps}
          </div>
          <div className="text-sm text-gray-500">Failed</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">
            {progress.total_steps}
          </div>
          <div className="text-sm text-gray-500">Total Steps</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">
            {progress.percentage.toFixed(0)}%
          </div>
          <div className="text-sm text-gray-500">Progress</div>
        </div>
      </div>

      {/* Current Step */}
      {progress.current_step && overall_status !== 'failed' && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-center space-x-2 mb-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span className="font-medium text-blue-900">
              Current: {formatStatus(progress.current_step)}
            </span>
          </div>
          <p className="text-sm text-blue-700">
            This step is currently being processed...
          </p>
        </div>
      )}

      {/* Step Details */}
      <div className="space-y-3">
        <h4 className="font-medium text-gray-900 mb-3">Step Details</h4>
        
        {steps.map((step, index) => (
          <div
            key={step.step_name}
            className={`
              p-3 rounded-lg border transition-colors
              ${step.status === 'processing' ? 'border-blue-200 bg-blue-50' : 
                step.status === 'completed' ? 'border-green-200 bg-green-50' :
                step.status === 'failed' ? 'border-red-200 bg-red-50' :
                'border-gray-200 bg-gray-50'
              }
            `}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={`
                  flex items-center justify-center w-8 h-8 rounded-full border
                  ${step.status === 'completed' ? 'bg-green-100 border-green-300 text-green-700' :
                    step.status === 'failed' ? 'bg-red-100 border-red-300 text-red-700' :
                    step.status === 'processing' ? 'bg-blue-100 border-blue-300 text-blue-700' :
                    'bg-white border-gray-300 text-gray-700'
                  }
                `}>
                  <span className="text-sm font-medium">
                    {index + 1}
                  </span>
                </div>
                
                <div>
                  <h5 className="font-medium text-gray-900">
                    {formatStatus(step.step_name)}
                  </h5>
                  <div className="flex items-center space-x-4 text-sm text-gray-600 mt-1">
                    {step.started_at && (
                      <span>
                        Started: {new Date(step.started_at).toLocaleTimeString()}
                      </span>
                    )}
                    {step.completed_at && (
                      <span>
                        Duration: {formatDuration(step.started_at!, step.completed_at)}
                      </span>
                    )}
                    {step.retry_count > 0 && (
                      <span className="text-yellow-600">
                        Retries: {step.retry_count}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                <span className={`
                  px-2 py-1 text-xs rounded-full font-medium
                  ${getStatusColor(step.status)}
                `}>
                  {getStatusIcon(step.status)} {formatStatus(step.status)}
                </span>
              </div>
            </div>
            
            {step.error_message && (
              <div className="mt-3 p-3 bg-red-100 rounded border border-red-200">
                <p className="text-sm text-red-700">
                  <strong>Error:</strong> {step.error_message}
                </p>
                {step.error_message.includes('safety checker') && (
                  <p className="text-xs text-red-600 mt-1">
                    This appears to be a configuration issue with the image generation API. Retry should resolve this.
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Next Step Preview */}
      {progress.next_step && overall_status !== 'failed' && (
        <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div className="flex items-center space-x-2">
            <span className="text-gray-500">⏭️</span>
            <span className="font-medium text-gray-700">
              Next: {formatStatus(progress.next_step)}
            </span>
          </div>
        </div>
      )}

      {/* Troubleshooting Tips */}
      {overall_status === 'failed' && failedSteps.length > 0 && (
        <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <h5 className="text-yellow-900 font-semibold mb-2">💡 Troubleshooting Tips</h5>
          <ul className="text-yellow-800 text-sm space-y-1">
            {failedSteps.some(s => s.error_message?.includes('safety checker')) && (
              <li>• API configuration issue detected - retry should resolve this automatically</li>
            )}
            {failedSteps.some(s => s.error_message?.includes('timeout')) && (
              <li>• Network timeout detected - check your internet connection and retry</li>
            )}
            {failedSteps.some(s => s.error_message?.includes('No valid scene videos')) && (
              <li>• Video generation failed - try reducing complexity or changing the script</li>
            )}
            <li>• If issues persist, try refreshing the page and starting over</li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default PipelineStatus;