import React from 'react';
import { Music, Video, Combine, Clock, HardDrive, AlertCircle } from 'lucide-react';
import { useVideoGeneration } from '../../../contexts/VideoGenerationContext';

export const MergeStep: React.FC = () => {
  const { state } = useVideoGeneration();
  const generation = state.currentGeneration;
  const mergeProgress = generation?.merge_progress;

  if (!generation) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading merge status...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Combine className="w-8 h-8 text-orange-600" />
          <h3 className="text-2xl font-bold text-gray-900">Audio/Video Merge</h3>
        </div>
        <p className="text-gray-600">
          Synchronizing audio with video content
        </p>
      </div>

      {/* Merge Progress Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h4 className="text-lg font-semibold text-gray-900">Merge Progress</h4>
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">
              {mergeProgress?.total_scenes_merged || 0}
            </div>
            <div className="text-sm text-gray-500">Scenes Merged</div>
          </div>
        </div>

        {generation.error_message && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
            <div>
              <div className="text-red-800 font-medium text-sm">Merge Error</div>
              <div className="text-red-700 text-sm mt-1">{generation.error_message}</div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-orange-50 border-2 border-orange-100">
              <Music className="w-6 h-6 text-orange-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {mergeProgress?.audio_tracks_mixed || 0}
            </div>
            <div className="text-sm text-gray-600">Audio Tracks</div>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-blue-50 border-2 border-blue-100">
              <Clock className="w-6 h-6 text-blue-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {mergeProgress?.total_duration?.toFixed(1) || '0.0'}s
            </div>
            <div className="text-sm text-gray-600">Duration</div>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-green-50 border-2 border-green-100">
              <HardDrive className="w-6 h-6 text-green-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {mergeProgress?.file_size_mb?.toFixed(1) || '0.0'}MB
            </div>
            <div className="text-sm text-gray-600">File Size</div>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-purple-50 border-2 border-purple-100">
              <div className="text-purple-500 font-bold text-lg">⚡</div>
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {mergeProgress?.processing_time?.toFixed(1) || '0.0'}s
            </div>
            <div className="text-sm text-gray-600">Process Time</div>
          </div>
        </div>

        {/* Sync Accuracy */}
        {mergeProgress?.sync_accuracy && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Sync Accuracy</span>
              <span className="text-sm text-green-600 font-medium">{mergeProgress.sync_accuracy}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-gradient-to-r from-orange-500 to-green-500 h-2 rounded-full animate-pulse" style={{ width: '85%' }} />
            </div>
          </div>
        )}
      </div>

      {/* Merge Details */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Merge Process</h4>
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-3 bg-orange-50 rounded-lg">
            <Video className="w-5 h-5 text-orange-600" />
            <div className="flex-1">
              <h5 className="font-medium text-gray-900">Video Synchronization</h5>
              <p className="text-sm text-gray-600">Aligning video frames with audio timeline</p>
            </div>
            <div className="text-orange-600">
              {generation.generation_status === 'merging_audio' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-orange-600"></div>
              ) : (
                <div className="w-4 h-4 bg-orange-600 rounded-full"></div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
            <Music className="w-5 h-5 text-blue-600" />
            <div className="flex-1">
              <h5 className="font-medium text-gray-900">Audio Mixing</h5>
              <p className="text-sm text-gray-600">Combining narrator, character voices, and effects</p>
            </div>
            <div className="text-blue-600">
              {generation.generation_status === 'merging_audio' ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              ) : (
                <div className="w-4 h-4 bg-blue-600 rounded-full"></div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Status Message */}
      <div className="text-center py-4">
        {generation.generation_status === 'merging_audio' ? (
          <div className="flex items-center justify-center gap-2 text-orange-600">
            <div className="w-2 h-2 bg-orange-600 rounded-full animate-pulse"></div>
            <span className="text-sm">Merging audio and video tracks...</span>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-2 text-green-600">
            <Combine className="w-4 h-4" />
            <span className="text-sm font-medium">Merge process completed!</span>
          </div>
        )}
      </div>
    </div>
  );
};