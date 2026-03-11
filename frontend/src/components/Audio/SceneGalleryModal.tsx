import React, { useEffect } from 'react';
import { X, Volume2, Loader2 } from 'lucide-react';
import { SceneImage } from '../Images/types';

interface DialogueLine {
  character: string;
  text: string;
}

interface ExpressionLine {
  character: string;
  action: string;
}

interface SceneGalleryModalProps {
  isOpen: boolean;
  onClose: () => void;
  sceneNumber: number;
  description: string;
  images: SceneImage[];
  selectedImageUrl?: string;
  initialIndex?: number;
  clickedImageUrl?: string; // URL of the specific image the user clicked
  onSelectImage: (url: string) => void;
  dialogue?: DialogueLine[];
  expression?: ExpressionLine[];
  onGenerateAudio?: (shotIndex?: number) => void;
  isGeneratingAudio?: boolean;
}

const SceneGalleryModal: React.FC<SceneGalleryModalProps> = ({
  isOpen,
  onClose,
  sceneNumber,
  description,
  images,
  selectedImageUrl: _selectedImageUrl,
  initialIndex = 0,
  clickedImageUrl,
  onSelectImage: _onSelectImage,
  dialogue,
  expression,
  onGenerateAudio,
  isGeneratingAudio = false,
}) => {
  // Filter valid images
  const validImages = React.useMemo(() =>
    images.filter(img => img.imageUrl && img.generationStatus === 'completed'),
    [images]
  );

  // Show the clicked image if provided, otherwise fall back to initialIndex
  const displayImage = React.useMemo(() => {
    if (clickedImageUrl) {
      const found = validImages.find(img => img.imageUrl === clickedImageUrl);
      if (found) return found;
    }
    return validImages[initialIndex] || validImages[0];
  }, [clickedImageUrl, validImages, initialIndex]);
  // selectedImageUrl and onSelectImage kept in interface for callers but unused in this modal


  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-5xl max-h-[92vh] flex flex-col bg-gray-900 rounded-2xl shadow-2xl border border-white/10 overflow-hidden">
        
        {/* Header */}
        <div className="flex justify-between items-start px-6 py-4 border-b border-white/10">
          <div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-3">
              <span className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-sm font-bold shrink-0">
                {sceneNumber}
              </span>
              Scene {sceneNumber} — View Details
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-full transition-colors ml-4 shrink-0"
          >
            <X className="w-5 h-5 text-gray-300" />
          </button>
        </div>

        {/* Body: image + info side by side */}
        <div className="flex flex-col md:flex-row flex-1 min-h-0 overflow-hidden">

          {/* Left: Image */}
          <div className="flex-1 bg-black flex items-center justify-center p-4 min-h-[260px]">
            {displayImage ? (
              <img
                src={displayImage.imageUrl}
                alt={`Scene ${sceneNumber}`}
                className="max-w-full max-h-[55vh] object-contain rounded-lg shadow-2xl"
              />
            ) : (
              <div className="text-gray-500 text-sm">No image available for this scene</div>
            )}
          </div>

          {/* Right: Info panel */}
          <div className="w-full md:w-80 flex flex-col border-l border-white/10 bg-gray-900/80 overflow-y-auto">
            
            {/* Scene Description */}
            <div className="p-5 border-b border-white/10">
              <h4 className="text-xs uppercase tracking-widest text-gray-400 font-semibold mb-2">Scene Description</h4>
              <p className="text-sm text-gray-200 leading-relaxed">{description || 'No description available.'}</p>
            </div>

            {/* Expression */}
            {expression && expression.length > 0 && (
              <div className="p-5 border-b border-white/10">
                <h4 className="text-xs uppercase tracking-widest text-gray-400 font-semibold mb-3">Expression</h4>
                <div className="space-y-2">
                  {expression.map((exp, idx) => (
                    <div key={idx} className="text-sm">
                      <span className="text-purple-400 font-semibold uppercase text-xs tracking-wide block mb-0.5">
                        {exp.character}
                      </span>
                      <span className="text-gray-300 italic">({exp.action})</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Dialogue */}
            {dialogue && dialogue.length > 0 && (
              <div className="p-5 border-b border-white/10">
                <h4 className="text-xs uppercase tracking-widest text-gray-400 font-semibold mb-3">Dialogue</h4>
                <div className="space-y-3">
                  {dialogue.map((line, idx) => (
                    <div key={idx} className="text-sm">
                      <span className="text-blue-400 font-semibold uppercase text-xs tracking-wide block mb-0.5">
                        {line.character}
                      </span>
                      <span className="text-gray-300 italic">"{line.text}"</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* No dialogue/expression notice */}
            {(!dialogue || dialogue.length === 0) && (!expression || expression.length === 0) && (
              <div className="p-5 border-b border-white/10">
                <h4 className="text-xs uppercase tracking-widest text-gray-400 font-semibold mb-2">Dialogue</h4>
                <p className="text-xs text-gray-500 italic">No dialogue in this scene</p>
              </div>
            )}

            {/* Spacer */}
            <div className="flex-1" />

            {/* Actions */}
            <div className="p-5 flex flex-col gap-3 border-t border-white/10">
              {/* Generate Audio button */}
              {onGenerateAudio && (
                <button
                  onClick={() => onGenerateAudio(displayImage?.shot_index ?? 0)}
                  disabled={isGeneratingAudio}
                  className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm transition-all shadow-lg ${
                    isGeneratingAudio
                      ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                      : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white hover:shadow-purple-500/20 transform hover:-translate-y-0.5 active:translate-y-0'
                  }`}
                >
                  {isGeneratingAudio ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Generating Audio...</span>
                    </>
                  ) : (
                    <>
                      <Volume2 className="w-4 h-4" />
                      <span>Generate Audio</span>
                    </>
                  )}
                </button>
              )}


            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SceneGalleryModal;
