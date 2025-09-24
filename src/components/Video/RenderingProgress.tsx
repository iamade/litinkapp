import React from 'react';
import { Loader2, CheckCircle, AlertCircle, Clock, Film } from 'lucide-react';

interface RenderingProgressProps {
  progress: number;
  status: 'idle' | 'rendering' | 'processing' | 'completed' | 'error';
  currentStep?: string;
  estimatedTimeRemaining?: number;
  onCancel?: () => void;
}

const RenderingProgress: React.FC<RenderingProgressProps> = ({
  progress,
  status,
  currentStep,
  estimatedTimeRemaining,
  onCancel,
}) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'rendering':
      case 'processing':
        return <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-8 h-8 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-8 h-8 text-red-500" />;
      default:
        return <Film className="w-8 h-8 text-gray-400" />;
    }
  };

  const getStatusMessage = () => {
    switch (status) {
      case 'rendering':
        return 'Rendering video...';
      case 'processing':
        return 'Processing with FFmpeg...';
      case 'completed':
        return 'Video rendering completed!';
      case 'error':
        return 'Rendering failed. Please try again.';
      default:
        return 'Ready to render';
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    if (mins > 0) {
      return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
  };

  const getProgressSteps = () => {
    return [
      { name: 'Initializing', completed: progress > 0 },
      { name: 'Processing Scenes', completed: progress > 25 },
      { name: 'Applying Transitions', completed: progress > 50 },
      { name: 'Adding Audio', completed: progress > 75 },
      { name: 'Finalizing', completed: progress >= 100 },
    ];
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Rendering Progress</h3>
        {status === 'rendering' && onCancel && (
          <button
            onClick={onCancel}
            className="text-sm text-red-600 hover:text-red-700 font-medium"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Status Icon and Message */}
      <div className="flex items-center space-x-4 mb-6">
        {getStatusIcon()}
        <div className="flex-1">
          <p className="text-gray-900 font-medium">{getStatusMessage()}</p>
          {currentStep && status === 'rendering' && (
            <p className="text-sm text-gray-600 mt-1">{currentStep}</p>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              status === 'error' 
                ? 'bg-red-500' 
                : status === 'completed'
                ? 'bg-green-500'
                : 'bg-blue-500'
            }`}
            style={{ width: `${progress}%` }}
          >
            {status === 'rendering' && (
              <div className="h-full bg-white/20 animate-pulse" />
            )}
          </div>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="space-y-2 mb-6">
        {getProgressSteps().map((step, index) => (
          <div key={index} className="flex items-center space-x-3">
            <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
              step.completed 
                ? 'border-green-500 bg-green-500' 
                : 'border-gray-300 bg-white'
            }`}>
              {step.completed && (
                <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </div>
            <span className={`text-sm ${
              step.completed ? 'text-gray-900 font-medium' : 'text-gray-500'
            }`}>
              {step.name}
            </span>
          </div>
        ))}
      </div>

      {/* Estimated Time */}
      {estimatedTimeRemaining && status === 'rendering' && (
        <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
          <div className="flex items-center space-x-2">
            <Clock className="w-4 h-4 text-blue-600" />
            <span className="text-sm text-blue-900">Estimated time remaining:</span>
          </div>
          <span className="text-sm font-medium text-blue-900">
            {formatTime(estimatedTimeRemaining)}
          </span>
        </div>
      )}

      {/* Error Message */}
      {status === 'error' && (
        <div className="p-3 bg-red-50 rounded-lg">
          <p className="text-sm text-red-800">
            An error occurred during rendering. Please check your settings and try again.
          </p>
        </div>
      )}

      {/* Success Message */}
      {status === 'completed' && (
        <div className="p-3 bg-green-50 rounded-lg">
          <p className="text-sm text-green-800">
            Your video has been successfully rendered and is ready for download!
          </p>
        </div>
      )}

      {/* Technical Details (collapsible) */}
      <details className="mt-6">
        <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-900">
          Technical Details
        </summary>
        <div className="mt-3 p-3 bg-gray-50 rounded text-xs font-mono text-gray-700 space-y-1">
          <div>Status: {status}</div>
          <div>Progress: {progress.toFixed(2)}%</div>
          {currentStep && <div>Current Step: {currentStep}</div>}
          {estimatedTimeRemaining && (
            <div>ETA: {formatTime(estimatedTimeRemaining)}</div>
          )}
          <div>Renderer: OpenShot Cloud API / FFmpeg</div>
        </div>
      </details>
    </div>
  );
};

export default RenderingProgress;