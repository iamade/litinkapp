import React from 'react';
import { Users, MessageSquare, Eye, AlertCircle } from 'lucide-react';
import { useVideoGeneration } from '../../../contexts/VideoGenerationContext';

export const LipSyncStep: React.FC = () => {
  const { state } = useVideoGeneration();
  const generation = state.currentGeneration;
  const lipSyncProgress = generation?.lipsync_progress;

  if (!generation) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading lip sync status...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Users className="w-8 h-8 text-pink-600" />
          <h3 className="text-2xl font-bold text-gray-900">Lip Sync Application</h3>
        </div>
        <p className="text-gray-600">
          Applying realistic lip movements to character dialogue
        </p>
      </div>

      {/* Lip Sync Progress Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h4 className="text-lg font-semibold text-gray-900">Lip Sync Progress</h4>
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">
              {lipSyncProgress?.characters_lip_synced || 0}
            </div>
            <div className="text-sm text-gray-500">Characters Synced</div>
          </div>
        </div>

        {generation.error_message && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
            <div>
              <div className="text-red-800 font-medium text-sm">Lip Sync Error</div>
              <div className="text-red-700 text-sm mt-1">{generation.error_message}</div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-pink-50 border-2 border-pink-100">
              <Users className="w-6 h-6 text-pink-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {lipSyncProgress?.characters_lip_synced || 0}
            </div>
            <div className="text-sm text-gray-600">Characters</div>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-blue-50 border-2 border-blue-100">
              <MessageSquare className="w-6 h-6 text-blue-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {lipSyncProgress?.scenes_processed || 0}
            </div>
            <div className="text-sm text-gray-600">Scenes Processed</div>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-green-50 border-2 border-green-100">
              <Eye className="w-6 h-6 text-green-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {lipSyncProgress?.scenes_with_lipsync || 0}
            </div>
            <div className="text-sm text-gray-600">Synced Scenes</div>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-purple-50 border-2 border-purple-100">
              <div className="text-purple-500 font-bold text-lg">AI</div>
            </div>
            <div className="text-xs font-bold text-gray-900 mb-1 uppercase">
              {lipSyncProgress?.processing_method || 'Advanced'}
            </div>
            <div className="text-sm text-gray-600">Method</div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Lip Sync Progress</span>
            <span className="text-sm text-gray-600">
              {lipSyncProgress && lipSyncProgress.total_scenes_processed > 0 
                ? Math.round((lipSyncProgress.scenes_with_lipsync / lipSyncProgress.total_scenes_processed) * 100)
                : 0
              }%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-gradient-to-r from-pink-500 to-purple-500 h-2 rounded-full transition-all duration-500"
              style={{ 
                width: lipSyncProgress && lipSyncProgress.total_scenes_processed > 0
                  ? `${(lipSyncProgress.scenes_with_lipsync / lipSyncProgress.total_scenes_processed) * 100}%`
                  : '0%'
              }}
            />
          </div>
        </div>
      </div>

      {/* Lip Sync Details */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Lip Sync Process</h4>
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-3 bg-pink-50 rounded-lg">
            <Eye className="w-5 h-5 text-pink-600" />
            <div className="flex-1">
              <h5 className="font-medium text-gray-900">Face Detection</h5>
              <p className="text-sm text-gray-600">Identifying character faces in video frames</p>
            </div>
            <div className="text-pink-600">
              {['applying_lipsync', 'lipsync_completed'].includes(generation.generation_status) ? (
                <div className="w-4 h-4 bg-pink-600 rounded-full"></div>
              ) : (
                <div className="w-4 h-4 bg-gray-300 rounded-full"></div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg">
            <MessageSquare className="w-5 h-5 text-purple-600" />
            <div className="flex-1">
              <h5 className="font-medium text-gray-900">Audio Analysis</h5>
              <p className="text-sm text-gray-600">Analyzing character dialogue timing and phonemes</p>
            </div>
            <div className="text-purple-600">
              {['applying_lipsync', 'lipsync_completed'].includes(generation.generation_status) ? (
                <div className="w-4 h-4 bg-purple-600 rounded-full"></div>
              ) : (
                <div className="w-4 h-4 bg-gray-300 rounded-full"></div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
            <Users className="w-5 h-5 text-blue-600" />
            <div className="flex-1">
              <h5 className="font-medium text-gray-900">Lip Movement Generation</h5>
              <p className="text-sm text-gray-600">Applying realistic mouth movements to match audio</p>
            </div>
            <div className="text-blue-600">
              {generation.generation_status === 'applying_lipsync' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              ) : generation.generation_status === 'lipsync_completed' ? (
                <div className="w-4 h-4 bg-blue-600 rounded-full"></div>
              ) : (
                <div className="w-4 h-4 bg-gray-300 rounded-full"></div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Status Message */}
      <div className="text-center py-4">
        {generation.generation_status === 'applying_lipsync' ? (
          <div className="flex items-center justify-center gap-2 text-pink-600">
            <div className="w-2 h-2 bg-pink-600 rounded-full animate-pulse"></div>
            <span className="text-sm">Applying lip sync to character dialogue...</span>
          </div>
        ) : generation.generation_status === 'lipsync_completed' ? (
          <div className="flex items-center justify-center gap-2 text-pink-600">
            <Users className="w-4 h-4" />
            <span className="text-sm font-medium">Lip sync completed!</span>
          </div>
        ) : generation.generation_status === 'lipsync_failed' ? (
          <div className="flex items-center justify-center gap-2 text-orange-600">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">Lip sync failed, but video is available without it</span>
          </div>
        ) : null}
      </div>
    </div>
  );
};