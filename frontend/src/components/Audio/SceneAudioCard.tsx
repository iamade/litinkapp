import React from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Check,
  Play,
  Pause,
  RefreshCw,
  Image as ImageIcon,
  Loader2,
  Music,
  Star,
  X
} from 'lucide-react';
import { SceneImage } from '../Images/types';
import { toast } from 'react-hot-toast';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';

interface SceneAudioCardProps {
  sceneNumber: number;
  description: string;
  images: SceneImage[];
  selectedImageUrl?: string;
  selectedScriptId: string;
  selectedSceneImage?: string;
  onSelectImage: (url: string) => void;
  onGenerateImage: (sceneNumber: number, prompt: string) => void;
  isGenerating: boolean;
  isGeneratingAudio?: boolean;  // Audio generation in progress for this scene
  onView?: (url: string) => void;
  // Future: specific audio controls
}

const SceneAudioCard: React.FC<SceneAudioCardProps> = ({
  sceneNumber,
  description,
  images,
  selectedScriptId,
  selectedSceneImage,
  onSelectImage,
  onGenerateImage,
  isGenerating,
  isGeneratingAudio = false,
  onView
}) => {
  // Debug: Log audio generation state for loading spinner debugging
  console.log(`[SceneAudioCard] Scene ${sceneNumber} isGeneratingAudio:`, isGeneratingAudio);
  const [currentImageIndex, setCurrentImageIndex] = React.useState(0);

  // Get storyboard configuration from context
  const { keySceneImages, deselectedImages } = useScriptSelection();

  // Filter for valid images only
  const validImages = React.useMemo(() =>
    images.filter(img => img.generationStatus === 'completed' && img.imageUrl),
    [images]
  );

  const currentImage = validImages[currentImageIndex];

  // Check if current image is key scene or excluded
  const isKeyScene = currentImage?.id === keySceneImages[sceneNumber];
  const isExcluded = currentImage?.id ? deselectedImages.has(currentImage.id) : false;

  const handlePrev = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentImageIndex(prev => (prev - 1 + validImages.length) % validImages.length);
  };

  const handleNext = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentImageIndex(prev => (prev + 1) % validImages.length);
  };

  const handleSelect = () => {
    if (currentImage?.imageUrl) {
      if (isSelected) {
        // Deselect - pass empty string to clear selection
        onSelectImage('');
        toast.success(`Scene ${sceneNumber} deselected`);
      } else {
        // Select
        onSelectImage(currentImage.imageUrl);
        toast.success(`Image selected for Scene ${sceneNumber}`);
      }
    }
  };

  const isSelected = currentImage?.imageUrl === selectedSceneImage;

  // Determine card styling based on state
  const cardBorderClass = isExcluded
    ? 'border-gray-300 opacity-60'  // Excluded: grayed out
    : isKeyScene
    ? 'border-yellow-500 ring-2 ring-yellow-500/20'  // Key scene: yellow
    : isSelected
    ? 'border-purple-500 ring-2 ring-purple-500/20'  // Selected: purple
    : 'border-gray-200 dark:border-gray-700';  // Default

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border transition-all duration-200 ${cardBorderClass}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center bg-gray-50/50 dark:bg-gray-800/50 rounded-t-xl">
        <h4 className="font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <span className="w-6 h-6 rounded-full bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 flex items-center justify-center text-xs font-bold">
            {sceneNumber}
          </span>
          <span className="text-sm">Scene {sceneNumber}</span>
        </h4>
        <div className="flex items-center gap-2">
          {/* Key Scene Badge */}
          {isKeyScene && !isExcluded && (
            <span className="flex items-center gap-1 text-xs font-medium text-yellow-700 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 px-2 py-1 rounded-full">
              <Star className="w-3 h-3 fill-current" />
              Key Scene
            </span>
          )}
          {/* Excluded Badge */}
          {isExcluded && (
            <span className="flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded-full">
              <X className="w-3 h-3" />
              Excluded
            </span>
          )}
          {/* Selected Badge */}
          {isSelected && !isKeyScene && !isExcluded && (
            <span className="flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 px-2 py-1 rounded-full">
              <Check className="w-3 h-3" />
              Selected
            </span>
          )}
          {(isGenerating || isGeneratingAudio) && (
            <span className="flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded-full animate-pulse">
              <Loader2 className="w-3 h-3 animate-spin" />
              {isGeneratingAudio ? 'Generating Audio...' : 'Generating...'}
            </span>
          )}
        </div>
      </div>

      <div className="p-4 flex flex-col gap-4">
        {/* Image Carousel with optional generation overlay */}
        <div 
            className="relative aspect-video bg-gray-100 dark:bg-gray-900 rounded-lg overflow-hidden group cursor-pointer"
            onClick={() => onView && currentImage?.imageUrl && onView(currentImage.imageUrl)}
        >
          {/* Audio Generation Overlay */}
          {isGeneratingAudio && (
            <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm">
              <div className="p-3 bg-purple-600/20 rounded-full mb-3">
                <Music className="w-8 h-8 text-purple-400 animate-pulse" />
              </div>
              <Loader2 className="w-6 h-6 text-white animate-spin mb-2" />
              <span className="text-white text-sm font-medium">Generating Audio...</span>
              <span className="text-white/60 text-xs mt-1">This may take a moment</span>
            </div>
          )}
          {validImages.length > 0 ? (
            <>
              <img 
                src={currentImage?.imageUrl} 
                alt={`Scene ${sceneNumber}`}
                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
              />
              
              {/* Overlay Gradient */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

              {/* Navigation */}
              {validImages.length > 1 && (
                <>
                  <button onClick={handlePrev} className="absolute left-2 top-1/2 -translate-y-1/2 p-1.5 bg-black/50 hover:bg-black/70 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button onClick={handleNext} className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-black/50 hover:bg-black/70 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronRight className="w-4 h-4" />
                  </button>
                  
                  {/* Indicators */}
                  <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    {validImages.map((_, idx) => (
                      <div 
                        key={idx}
                        className={`w-1.5 h-1.5 rounded-full transition-all ${
                          idx === currentImageIndex ? 'bg-white scale-125' : 'bg-white/50'
                        }`} 
                      />
                    ))}
                  </div>
                </>
              )}

              {/* Selection Button Over Image */}
              {!isSelected && (
                <button
                    onClick={handleSelect}
                    className="absolute top-2 right-2 px-3 py-1.5 bg-white/90 hover:bg-white text-gray-900 rounded-full text-xs font-semibold shadow-lg opacity-0 group-hover:opacity-100 transition-all transform hover:scale-105"
                >
                    Select this Version
                </button>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-2">
              <ImageIcon className="w-8 h-8 opacity-50" />
              <span className="text-xs">No images generated</span>
            </div>
          )}
        </div>

        {/* Text Description */}
        <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-3 leading-relaxed">
          {description}
        </p>

        {/* Footer info */}
        <div className="flex justify-between items-center text-xs text-gray-500 pt-2 border-t border-gray-100 dark:border-gray-800">
             <span>{validImages.length} versions available</span>
             {isExcluded ? (
               <span className="text-gray-400 font-medium">Excluded from Audio</span>
             ) : isKeyScene ? (
               <span className="text-yellow-600 font-medium">Key Scene for Audio</span>
             ) : isSelected ? (
               <span className="text-purple-600 font-medium">Ready for Audio</span>
             ) : null}
        </div>
      </div>
    </div>
  );
};

export default SceneAudioCard;
