import React, { useEffect, useState } from 'react';
import { X, ChevronLeft, ChevronRight, Check } from 'lucide-react';
import { SceneImage } from '../Images/types';

interface SceneGalleryModalProps {
  isOpen: boolean;
  onClose: () => void;
  sceneNumber: number;
  description: string;
  images: SceneImage[];
  selectedImageUrl?: string;
  initialIndex?: number;
  onSelectImage: (url: string) => void;
}

const SceneGalleryModal: React.FC<SceneGalleryModalProps> = ({
  isOpen,
  onClose,
  sceneNumber,
  description,
  images,
  selectedImageUrl,
  initialIndex = 0,
  onSelectImage
}) => {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);

  // Filter valid images
  const validImages = React.useMemo(() => 
    images.filter(img => img.imageUrl && img.generationStatus === 'completed'),
    [images]
  );

  useEffect(() => {
    if (isOpen) {
      setCurrentIndex(initialIndex);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, initialIndex]);

  useEffect(() => {
      // Handle keyboard navigation
      const handleKeyDown = (e: KeyboardEvent) => {
          if (!isOpen) return;
          if (e.key === 'ArrowLeft') handlePrev();
          if (e.key === 'ArrowRight') handleNext();
          if (e.key === 'Escape') onClose();
      };
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, validImages.length]);

  if (!isOpen) return null;

  const currentImage = validImages[currentIndex];
  const isSelected = currentImage?.imageUrl === selectedImageUrl;

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : validImages.length - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev < validImages.length - 1 ? prev + 1 : 0));
  };

  const handleSelect = () => {
      if (currentImage?.imageUrl) {
          if (isSelected) {
              // Deselect - pass empty string to clear selection
              onSelectImage('');
          } else {
              onSelectImage(currentImage.imageUrl);
          }
      }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-6xl h-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-start mb-4 text-white">
          <div>
            <h3 className="text-xl font-semibold flex items-center gap-3">
               <span className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm font-bold">
                 {sceneNumber}
               </span>
               Scene {sceneNumber} Gallery
            </h3>
            <p className="text-sm text-gray-300 mt-1 max-w-3xl line-clamp-2">
                {description}
            </p>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-full transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex items-center justify-center relative min-h-0">
          {validImages.length > 0 ? (
              <>
                <img 
                    src={currentImage?.imageUrl} 
                    alt={`Scene ${sceneNumber} - Version ${currentIndex + 1}`}
                    className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
                />

                {/* Navigation Buttons */}
                {validImages.length > 1 && (
                    <>
                        <button 
                            onClick={(e) => { e.stopPropagation(); handlePrev(); }}
                            className="absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-black/50 hover:bg-black/70 text-white rounded-full transition-all hover:scale-110 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <ChevronLeft className="w-8 h-8" />
                        </button>
                        <button 
                            onClick={(e) => { e.stopPropagation(); handleNext(); }}
                            className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-black/50 hover:bg-black/70 text-white rounded-full transition-all hover:scale-110 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <ChevronRight className="w-8 h-8" />
                        </button>
                    </>
                )}
              </>
          ) : (
              <div className="text-gray-400">No images available for this scene</div>
          )}
        </div>

        {/* Footer / Controls */}
        <div className="mt-4 flex flex-col items-center gap-4">
            {/* Indicators */}
            {validImages.length > 1 && (
                <div className="flex gap-2 p-2 bg-black/40 rounded-full backdrop-blur-md">
                    {validImages.map((_, idx) => (
                        <button
                            key={idx}
                            onClick={() => setCurrentIndex(idx)}
                            className={`w-2.5 h-2.5 rounded-full transition-all ${
                                idx === currentIndex ? 'bg-blue-500 scale-125' : 'bg-white/30 hover:bg-white/50'
                            }`}
                        />
                    ))}
                </div>
            )}

            {/* Action Bar */}
            <div className="flex items-center gap-4 bg-gray-900/80 p-3 rounded-xl border border-white/10 backdrop-blur-md shadow-xl">
                 <div className="text-sm text-gray-300 px-2 border-r border-white/10 pr-4">
                     Version {currentIndex + 1} of {validImages.length}
                 </div>
                 
                 {isSelected ? (
                     <button
                        onClick={handleSelect}
                        className="flex items-center gap-2 px-6 py-2 bg-emerald-600/20 text-emerald-400 rounded-lg border border-emerald-500/30 hover:bg-red-600/20 hover:text-red-400 hover:border-red-500/30 transition-all cursor-pointer"
                        title="Click to deselect"
                     >
                         <Check className="w-5 h-5" />
                         <span className="font-semibold">Selected for Audio</span>
                     </button>
                 ) : (
                     <button
                        onClick={handleSelect}
                        className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-semibold transition-all shadow-lg hover:shadow-blue-500/20 transform hover:-translate-y-0.5 active:translate-y-0"
                     >
                         Select for Audio
                     </button>
                 )}
            </div>
        </div>
      </div>
    </div>
  );
};

export default SceneGalleryModal;
