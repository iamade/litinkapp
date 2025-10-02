import React from 'react';
import { Video, Play, Clock, AlertCircle, CheckCircle } from 'lucide-react';
import { useVideoGeneration } from '../../../contexts/VideoGenerationContext';
import { PollingStatus } from '../PollingStatus';

export const VideoGenerationStep: React.FC = () => {
  const { state } = useVideoGeneration();
  const generation = state.currentGeneration;
  const videoProgress = generation?.video_progress;

  if (!generation) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading video generation status...</div>
      </div>
    );
  }

  const progressPercentage = videoProgress 
    ? Math.round((videoProgress.scenes_completed / Math.max(1, videoProgress.total_scenes)) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Video className="w-8 h-8 text-purple-600" />
          <h3 className="text-2xl font-bold text-gray-900">Video Generation</h3>
        </div>
        <p className="text-gray-600">
          Creating video segments for each scene
        </p>
      </div>

      {/* Video Progress Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h4 className="text-lg font-semibold text-gray-900">Video Generation Progress</h4>
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">{progressPercentage}%</div>
            <div className="text-sm text-gray-500">Completed</div>
          </div>
        </div>

        {/* Polling Status */}
        {generation?.generation_status === 'generating_video' && generation?.id && (
          <div className="mb-4">
            <PollingStatus
              videoGenId={generation.id}
              showDetails={true}
            />
            
            {/* Current Scene Info */}
            {videoProgress && (
              <div className="mt-3 p-3 bg-purple-50 border border-purple-200 rounded-lg">
                <div className="flex items-center justify-between text-sm text-purple-800">
                  <span className="font-medium">Current Scene Progress</span>
                  <span>
                    Scene {videoProgress.scenes_completed + 1} of {videoProgress.total_scenes}
                  </span>
                </div>
                {videoProgress.success_rate > 0 && (
                  <div className="mt-1 text-xs text-purple-600">
                    Success Rate: {Math.round(videoProgress.success_rate)}%
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Error Display */}
        {generation?.error_message && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <h5 className="text-red-800 font-medium text-sm mb-1">Video Generation Error</h5>
                <div className="text-red-700 text-sm mb-2">{generation.error_message}</div>
                
                {/* Actionable Error Suggestions */}
                {getErrorSuggestions(generation.error_message)}
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-purple-50 border-2 border-purple-100">
              <Video className="w-6 h-6 text-purple-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {videoProgress?.scenes_completed || 0}/{videoProgress?.total_scenes || 0}
            </div>
            <div className="text-sm text-gray-600">Scenes</div>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-blue-50 border-2 border-blue-100">
              <Play className="w-6 h-6 text-blue-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {videoProgress?.total_videos_generated || 0}
            </div>
            <div className="text-sm text-gray-600">Videos Created</div>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-green-50 border-2 border-green-100">
              <div className="text-green-500 font-bold text-lg">✓</div>
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {videoProgress?.successful_videos || 0}
            </div>
            <div className="text-sm text-gray-600">Successful</div>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-orange-50 border-2 border-orange-100">
              <div className="text-orange-500 font-bold text-lg">%</div>
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {Math.round(videoProgress?.success_rate || 0)}%
            </div>
            <div className="text-sm text-gray-600">Success Rate</div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Overall Video Progress</span>
            <span className="text-sm text-gray-600">{progressPercentage}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
        </div>
      </div>

      {/* Scene Videos Preview */}
      {generation.scene_videos && generation.scene_videos.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">Scene Videos</h4>
          <div className="space-y-4">
            {generation.scene_videos.map((video, index: number) => (
              <div key={index} className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-shrink-0">
                  <div className="w-16 h-12 bg-gray-200 rounded overflow-hidden">
                    {video.video_url ? (
                      <video 
                        className="w-full h-full object-cover"
                        poster={video.thumbnail_url}
                      >
                        <source src={video.video_url} type="video/mp4" />
                      </video>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-600"></div>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="flex-1">
                  <h5 className="font-medium text-gray-900">
                    Scene {index + 1}
                  </h5>
                  {video.duration && (
                    <p className="text-sm text-gray-600 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {video.duration.toFixed(1)}s
                    </p>
                  )}
                </div>
                
                {video.video_url && (
                  <button className="p-2 rounded-full bg-purple-100 hover:bg-purple-200 transition-colors">
                    <Play className="w-4 h-4 text-purple-600" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Status Message */}
      <div className="text-center py-4">
        {generation.generation_status === 'generating_video' ? (
          <div className="space-y-2">
            <div className="flex items-center justify-center gap-2 text-purple-600">
              <div className="w-2 h-2 bg-purple-600 rounded-full animate-pulse"></div>
              <span className="text-sm">
                Generating video segments... This may take several minutes
              </span>
            </div>
            {generation?.id && (
              <div className="text-xs text-blue-600">
                <PollingStatus videoGenId={generation.id} showDetails={false} />
              </div>
            )}
          </div>
        ) : generation.generation_status === 'video_completed' ? (
          <div className="flex items-center justify-center gap-2 text-green-600">
            <CheckCircle className="w-4 h-4" />
            <span className="text-sm font-medium">Video generation completed!</span>
          </div>
        ) : null}
      </div>
    </div>
  );
};

// Helper function to provide actionable error suggestions
const getErrorSuggestions = (errorMessage: string): React.ReactNode => {
  const errorLower = errorMessage.toLowerCase();
  
  if (errorLower.includes('generation_failed') || errorLower.includes('failed to generate')) {
    return (
      <div className="bg-red-100 p-2 rounded text-xs text-red-800">
        <strong>Suggested Action:</strong> The video generation service may be experiencing high load.
        Please wait a moment and try again, or try with a shorter script.
      </div>
    );
  }
  
  if (errorLower.includes('timeout') || errorLower.includes('timed out')) {
    return (
      <div className="bg-red-100 p-2 rounded text-xs text-red-800">
        <strong>Suggested Action:</strong> The operation timed out. This can happen with longer videos.
        Try generating a shorter video or check your internet connection.
      </div>
    );
  }
  
  if (errorLower.includes('retrieval_failed') || errorLower.includes('fallback')) {
    return (
      <div className="bg-orange-100 p-2 rounded text-xs text-orange-800">
        <strong>Suggested Action:</strong> Video was generated but retrieval failed.
        The system is automatically trying alternative methods. Please wait or try again in a moment.
      </div>
    );
  }
  
  if (errorLower.includes('safety') || errorLower.includes('content policy')) {
    return (
      <div className="bg-yellow-100 p-2 rounded text-xs text-yellow-800">
        <strong>Suggested Action:</strong> Content was flagged by safety filters.
        Please review your script for potentially restricted content and try again.
      </div>
    );
  }
  
  return (
    <div className="bg-red-100 p-2 rounded text-xs text-red-800">
      <strong>Suggested Action:</strong> Please try again in a moment. If the issue persists,
      contact support with the error details.
    </div>
  );
};