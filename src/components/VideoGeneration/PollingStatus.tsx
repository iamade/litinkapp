import React from 'react';
import { RefreshCw, Clock, AlertCircle, CheckCircle } from 'lucide-react';
import { pollingService } from '../../services/videoGenerationPolling';

interface PollingStatusProps {
  videoGenId?: string;
  className?: string;
  showDetails?: boolean;
}

export const PollingStatus: React.FC<PollingStatusProps> = ({
  videoGenId,
  className = '',
  showDetails = true
}) => {
  if (!videoGenId) return null;

  const pollingAttempts = pollingService.getPollingAttempts(videoGenId);
  const pollingElapsedTime = pollingService.getPollingElapsedTime(videoGenId);
  const isFallbackRetrieval = pollingService.isFallbackRetrieval(videoGenId);
  
  // Calculate polling progress for 2-minute window
  const pollingProgress = Math.min(100, (pollingElapsedTime / (2 * 60 * 1000)) * 100);
  const pollingTimeRemaining = Math.max(0, (2 * 60 * 1000) - pollingElapsedTime);
  
  // Format time remaining
  const formatTimeRemaining = (ms: number): string => {
    const seconds = Math.ceil(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <div className={`bg-blue-50 border border-blue-200 rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <RefreshCw className="w-4 h-4 text-blue-600 animate-spin" />
          <h5 className="text-blue-800 font-medium text-sm">
            {isFallbackRetrieval ? 'Fallback Retrieval' : 'Polling for Video Completion'}
          </h5>
        </div>
        <div className="text-blue-700 text-sm font-medium">
          Attempt {pollingAttempts}/24
        </div>
      </div>
      
      {/* Polling Progress Bar */}
      <div className="mb-2">
        <div className="flex items-center justify-between text-xs text-blue-600 mb-1">
          <span>Polling Progress</span>
          <span>{Math.round(pollingProgress)}%</span>
        </div>
        <div className="w-full bg-blue-200 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all duration-500 ${
              isFallbackRetrieval 
                ? 'bg-gradient-to-r from-orange-500 to-orange-600' 
                : 'bg-gradient-to-r from-blue-500 to-blue-600'
            }`}
            style={{ width: `${pollingProgress}%` }}
          />
        </div>
      </div>
      
      {showDetails && (
        <>
          {/* Additional Polling Info */}
          <div className="grid grid-cols-2 gap-3 text-xs text-blue-700 mb-2">
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>Time Remaining: {formatTimeRemaining(pollingTimeRemaining)}</span>
            </div>
            <div className="flex items-center gap-1">
              {isFallbackRetrieval ? (
                <AlertCircle className="w-3 h-3 text-orange-500" />
              ) : (
                <CheckCircle className="w-3 h-3 text-green-500" />
              )}
              <span>Status: {isFallbackRetrieval ? 'Fallback Active' : 'Standard'}</span>
            </div>
          </div>
          
          {/* Status Message */}
          <div className="text-xs text-blue-600">
            {isFallbackRetrieval ? (
              <div className="flex items-center gap-1">
                <AlertCircle className="w-3 h-3 text-orange-500" />
                <span>Using alternative retrieval method to ensure video availability</span>
              </div>
            ) : (
              <span>Checking video generation status every 5 seconds</span>
            )}
          </div>
        </>
      )}
    </div>
  );
};

// Simplified inline polling status for compact display
export const InlinePollingStatus: React.FC<{ videoGenId?: string }> = ({ videoGenId }) => {
  if (!videoGenId) return null;

  const pollingAttempts = pollingService.getPollingAttempts(videoGenId);
  const isFallbackRetrieval = pollingService.isFallbackRetrieval(videoGenId);

  return (
    <div className="flex items-center gap-2 text-xs text-blue-600">
      <RefreshCw className="w-3 h-3 animate-spin" />
      <span>
        Polling ({pollingAttempts}/24)
        {isFallbackRetrieval && (
          <span className="text-orange-600 ml-1">• Fallback Active</span>
        )}
      </span>
    </div>
  );
};