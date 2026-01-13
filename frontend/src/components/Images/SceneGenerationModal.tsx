
import React, { useState, useEffect } from 'react';
import { X, Search } from 'lucide-react';
import { CharacterImage } from './types';

interface SceneGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  sceneNumber: number;
  initialDescription: string;
  chapterTitle?: string;
  availableCharacters: CharacterImage[];
  onGenerate: (description: string, characterIds: string[]) => void;
  isGenerating: boolean;
}

const SceneGenerationModal: React.FC<SceneGenerationModalProps> = ({
  isOpen,
  onClose,
  sceneNumber,
  initialDescription,
  chapterTitle,
  availableCharacters,
  onGenerate,
  isGenerating
}) => {
  const [description, setDescription] = useState(initialDescription);
  const [selectedCharacterIds, setSelectedCharacterIds] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setDescription(initialDescription);
      setSelectedCharacterIds(new Set());
      setSearchTerm('');
    }
  }, [isOpen, initialDescription]);

  if (!isOpen) return null;

  const toggleCharacterSelection = (characterId: string | undefined) => {
    if (!characterId) return;
    const newSelected = new Set(selectedCharacterIds);
    if (newSelected.has(characterId)) {
      newSelected.delete(characterId);
    } else {
      if (newSelected.size >= 3) {
        // Optional: limit number of characters if needed, but 3 is reasonable for i2i
        // For now preventing more than 3 to avoid clutter/poor results
        return; 
      }
      newSelected.add(characterId);
    }
    setSelectedCharacterIds(newSelected);
  };

  const filteredCharacters = availableCharacters.filter(char => 
    char.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-[#1e1e1e] rounded-xl shadow-2xl border border-gray-800 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <div>
            <h2 className="text-xl font-semibold text-white">Generate Scene {sceneNumber}</h2>
            {chapterTitle && <p className="text-sm text-gray-400 mt-1">{chapterTitle}</p>}
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Detailed Scene Description */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-gray-300">
              Scene Description
              <span className="ml-2 text-xs text-gray-500 font-normal">
                (This will be saved to the script and used as the generation prompt)
              </span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full h-32 bg-[#141414] border border-gray-800 rounded-lg p-3 text-gray-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors resize-none"
              placeholder="Describe the scene in detail..."
            />
          </div>

          {/* Character References */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-300">
                Reference Characters
                <span className="ml-2 text-xs text-gray-500 font-normal">
                  (Select up to 3)
                </span>
              </label>
              <span className="text-xs text-indigo-400 font-medium">
                {selectedCharacterIds.size} selected
              </span>
            </div>

            {/* Search */}
            <div className="relative">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search characters..."
                className="w-full bg-[#141414] border border-gray-800 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-indigo-500"
              />
              <Search className="absolute left-3 top-2.5 text-gray-500" size={14} />
            </div>

            {/* Character Grid */}
            <div className={`grid grid-cols-3 sm:grid-cols-4 gap-3 max-h-60 overflow-y-auto pr-1 ${availableCharacters.length === 0 ? 'flex items-center justify-center h-20 bg-[#141414] rounded-lg border border-dashed border-gray-800' : ''}`}>
              {availableCharacters.length === 0 ? (
                <div className="col-span-full flex flex-col items-center justify-center py-8 text-center px-4">
                  <span className="text-gray-400 text-sm font-medium mb-1">No generated characters available</span>
                  <p className="text-gray-500 text-xs">Generate character images in the "Characters" tab first to use them as references here.</p>
                </div>
              ) : filteredCharacters.map((char) => (
                <button
                  key={char.id}
                  onClick={() => toggleCharacterSelection(char.id)}
                  className={`
                    group relative aspect-square rounded-lg overflow-hidden border-2 transition-all
                    ${selectedCharacterIds.has(char.id || '') 
                      ? 'border-indigo-500 ring-2 ring-indigo-500/20' 
                      : 'border-transparent hover:border-gray-600'}
                  `}
                >
                  <img 
                    src={char.imageUrl || ''} 
                    alt={char.name || 'Character'} 
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-100" />
                  <span className="absolute bottom-1.5 left-2 right-2 text-xs font-medium text-white truncate text-left">
                    {char.name || 'Unknown'}
                  </span>
                  
                  {/* Selection Indicator */}
                  {selectedCharacterIds.has(char.id || '') && (
                    <div className="absolute top-2 right-2 w-5 h-5 bg-indigo-500 rounded-full flex items-center justify-center shadow-sm">
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-800 flex justify-end gap-3 bg-[#141414]/50 rounded-b-xl">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-300 hover:text-white hover:bg-gray-800 rounded-lg transition-colors text-sm font-medium"
            disabled={isGenerating}
          >
            Cancel
          </button>
          <button
            onClick={() => onGenerate(description, Array.from(selectedCharacterIds))}
            disabled={isGenerating}
            className={`
              px-6 py-2 rounded-lg text-sm font-medium text-white shadow-lg shadow-indigo-500/20 
              transition-all flex items-center gap-2
              ${isGenerating 
                ? 'bg-indigo-500/50 cursor-not-allowed' 
                : 'bg-indigo-600 hover:bg-indigo-500 hover:scale-[1.02] active:scale-[0.98]'}
            `}
          >
            {isGenerating ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Save & Generate
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SceneGenerationModal;
