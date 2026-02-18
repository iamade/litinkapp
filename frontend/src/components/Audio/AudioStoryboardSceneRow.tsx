import React from 'react';
import { SceneImage } from '../../hooks/useImageGeneration';
import { Maximize2, Star, X, Music, Loader2, Check, Volume2 } from 'lucide-react';

interface AudioStoryboardSceneRowProps {
  sceneNumber: number;
  description: string;
  images: SceneImage[];
  // Audio-specific props
  isGeneratingAudio?: boolean;
  hasAudio?: boolean;
  onGenerateAudio?: () => void;
  onView?: (url: string) => void;
  // Storyboard configuration (read-only from Image tab)
  keySceneImageId?: string;
  deselectedImages?: Set<string>;
}

// Individual image card for the audio storyboard (read-only, no drag)
const AudioImageCard = ({
  image,
  isKeyScene,
  isExcluded,
  shotIndex,
  onView,
}: {
  image: SceneImage;
  isKeyScene?: boolean;
  isExcluded?: boolean;
  shotIndex?: number;
  onView?: () => void;
}) => {
  // Determine card styling based on state
  const cardBorderClass = isExcluded
    ? 'border-gray-300 opacity-50'  // Excluded: grayed out
    : isKeyScene
    ? 'border-yellow-500 shadow-lg ring-2 ring-yellow-500/20'  // Key scene: yellow
    : 'border-transparent shadow hover:border-gray-300 hover:shadow-md';  // Default

  return (
    <div
      className={`relative group w-full bg-white dark:bg-gray-800 rounded-lg border-2 transition-all duration-200 ${cardBorderClass}`}
    >
      {/* Image Container */}
      <div className="aspect-video bg-gray-200 relative rounded-t-lg overflow-hidden">
        <img
          src={image.imageUrl}
          alt={image.prompt}
          className={`w-full h-full object-cover ${isExcluded ? 'grayscale' : ''}`}
        />

        {/* View button on hover */}
        {onView && (
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all flex items-start justify-end p-2 opacity-0 group-hover:opacity-100">
            <button
              onClick={(e) => { e.stopPropagation(); onView(); }}
              className="p-1.5 bg-black/60 text-white rounded-full hover:bg-black/80"
              title="View Fullscreen"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Key Scene Label (bottom-left) */}
        {isKeyScene && !isExcluded && (
          <div className="absolute bottom-2 left-2 pointer-events-none">
            <span className="px-2 py-0.5 bg-yellow-400 text-yellow-900 text-xs font-bold rounded shadow-sm flex items-center">
              <Star className="w-3 h-3 mr-1 fill-current" /> Key Scene
            </span>
          </div>
        )}

        {/* Excluded Label (bottom-left) */}
        {isExcluded && (
          <div className="absolute bottom-2 left-2 pointer-events-none">
            <span className="px-2 py-0.5 bg-gray-500 text-white text-xs font-bold rounded shadow-sm flex items-center">
              <X className="w-3 h-3 mr-1" /> Excluded
            </span>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-gray-100 dark:border-gray-700">
        <div className="flex items-center justify-between mb-1">
          <span className={`text-xs font-bold uppercase tracking-wider ${
            isExcluded
              ? 'text-gray-400'
              : isKeyScene
              ? 'text-yellow-600'
              : 'text-gray-500'
          }`}>
            {isExcluded ? 'Excluded' : isKeyScene ? 'Key Scene' : (shotIndex !== undefined && shotIndex > 0) ? `Shot ${shotIndex}` : 'Shot'}
          </span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2" title={image.prompt}>
          {image.prompt}
        </p>
      </div>
    </div>
  );
};

export const AudioStoryboardSceneRow: React.FC<AudioStoryboardSceneRowProps> = ({
  sceneNumber,
  description,
  images,
  isGeneratingAudio = false,
  hasAudio = false,
  onGenerateAudio,
  onView,
  keySceneImageId,
  deselectedImages,
}) => {
  // Filter out excluded images - only show images not in deselectedImages
  const visibleImages = images.filter(img =>
    !img.id || !deselectedImages?.has(img.id)
  );

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
      <div className="flex justify-between items-start mb-4 border-b border-gray-100 dark:border-gray-700 pb-3">
        <div className="flex items-start flex-1">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs font-bold rounded uppercase">
                Scene {sceneNumber}
              </span>
              {/* Audio status badges */}
              {isGeneratingAudio && (
                <span className="flex items-center gap-1 text-xs font-medium text-blue-600 bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded-full animate-pulse">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Generating Audio...
                </span>
              )}
              {hasAudio && !isGeneratingAudio && (
                <span className="flex items-center gap-1 text-xs font-medium text-green-600 bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded-full">
                  <Check className="w-3 h-3" />
                  Audio Ready
                </span>
              )}
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2 max-w-4xl font-medium">
              {description}
            </p>
          </div>
        </div>

        {/* Generate Audio Button */}
        {onGenerateAudio && (
          <button
            onClick={onGenerateAudio}
            disabled={isGeneratingAudio}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              isGeneratingAudio
                ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:from-purple-700 hover:to-indigo-700 hover:shadow-md'
            }`}
          >
            {isGeneratingAudio ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Volume2 className="w-4 h-4" />
            )}
            <span>{isGeneratingAudio ? 'Generating...' : 'Generate Audio'}</span>
          </button>
        )}
      </div>

      {/* Images Grid */}
      {visibleImages.length === 0 ? (
        <div className="p-8 bg-gray-50 dark:bg-gray-900/50 text-center rounded-lg border-2 border-dashed border-gray-200 dark:border-gray-700">
          <Music className="w-8 h-8 text-gray-400 mx-auto mb-2" />
          <p className="text-gray-500 text-sm">No images for this scene.</p>
          <p className="text-gray-400 text-xs mt-1">Generate images in the Images tab first.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {visibleImages.map((img) => (
            <AudioImageCard
              key={img.imageUrl}
              image={img}
              isKeyScene={img.id === keySceneImageId}
              isExcluded={img.id ? deselectedImages?.has(img.id) : false}
              shotIndex={img.shot_index}
              onView={onView ? () => onView(img.imageUrl) : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default AudioStoryboardSceneRow;
