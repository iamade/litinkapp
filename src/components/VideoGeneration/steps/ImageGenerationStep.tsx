import React from 'react';
import { Image, Eye, Grid, AlertCircle } from 'lucide-react';
import { useVideoGeneration } from '../../../contexts/VideoGenerationContext';

export const ImageGenerationStep: React.FC = () => {
  const { state } = useVideoGeneration();
  const generation = state.currentGeneration;
  const imageProgress = generation?.image_progress;

  if (!generation) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading image generation status...</div>
      </div>
    );
  }

  const progressPercentage = imageProgress 
    ? Math.round((imageProgress.characters_completed / Math.max(1, imageProgress.total_characters)) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Image className="w-8 h-8 text-green-600" />
          <h3 className="text-2xl font-bold text-gray-900">Image Generation</h3>
        </div>
        <p className="text-gray-600">
          Creating character images and scene visuals
        </p>
      </div>

      {/* Image Progress Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h4 className="text-lg font-semibold text-gray-900">Image Generation Progress</h4>
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">{progressPercentage}%</div>
            <div className="text-sm text-gray-500">Completed</div>
          </div>
        </div>

        {generation.error_message && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
            <div>
              <div className="text-red-800 font-medium text-sm">Image Generation Error</div>
              <div className="text-red-700 text-sm mt-1">{generation.error_message}</div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-green-50 border-2 border-green-100">
              <Image className="w-6 h-6 text-green-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {imageProgress?.total_images_generated || 0}
            </div>
            <div className="text-sm text-gray-600">Images Created</div>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-purple-50 border-2 border-purple-100">
              <Eye className="w-6 h-6 text-purple-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {imageProgress?.characters_completed || 0}/{imageProgress?.total_characters || 0}
            </div>
            <div className="text-sm text-gray-600">Characters</div>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-blue-50 border-2 border-blue-100">
              <Grid className="w-6 h-6 text-blue-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {imageProgress?.scenes_completed || 0}/{imageProgress?.total_scenes || 0}
            </div>
            <div className="text-sm text-gray-600">Scenes</div>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-orange-50 border-2 border-orange-100">
              <div className="text-orange-500 font-bold text-lg">%</div>
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {Math.round(imageProgress?.success_rate || 0)}%
            </div>
            <div className="text-sm text-gray-600">Success Rate</div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Overall Image Progress</span>
            <span className="text-sm text-gray-600">{progressPercentage}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-gradient-to-r from-green-500 to-blue-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
        </div>
      </div>

      {/* Character Images Preview */}
      {generation.character_images && generation.character_images.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">Character Images</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {generation.character_images.map((image: any, index: number) => (
              <div key={index} className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
                {image.image_url ? (
                  <img 
                    src={image.image_url} 
                    alt={image.character_name || `Character ${index + 1}`}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto mb-2"></div>
                      <p className="text-xs text-gray-500">Generating...</p>
                    </div>
                  </div>
                )}
                <div className="p-2 bg-white">
                  <p className="text-sm font-medium truncate">
                    {image.character_name || `Character ${index + 1}`}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Status Message */}
      <div className="text-center py-4">
        {generation.generation_status === 'generating_images' ? (
          <div className="flex items-center justify-center gap-2 text-green-600">
            <div className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></div>
            <span className="text-sm">Generating character and scene images...</span>
          </div>
        ) : generation.generation_status === 'images_completed' ? (
          <div className="flex items-center justify-center gap-2 text-green-600">
            <Image className="w-4 h-4" />
            <span className="text-sm font-medium">Image generation completed!</span>
          </div>
        ) : null}
      </div>
    </div>
  );
};