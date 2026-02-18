
import React, { useState, useEffect } from 'react';
import { X, Search, Sparkles, Box, MapPin, Wand2, Loader2, RotateCcw } from 'lucide-react';
import { CharacterImage } from './types';
import { userService } from '../../services/userService';
import { toast } from 'react-hot-toast';

// Tier-based character reference limits
const TIER_CHARACTER_LIMITS: Record<string, number> = {
  free: 4,
  basic: 5,
  standard: 6,
  premium: 8,
  professional: 10,
  enterprise: 99, // Effectively unlimited
};

// Tier-based AI assist limits
const TIER_AI_ASSIST_LIMITS: Record<string, number> = {
  free: 3,
  basic: 10,
  standard: 25,
  premium: 50,
  professional: 100,
  enterprise: 999, // Effectively unlimited
};

interface SceneGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  sceneNumber: number;
  initialDescription: string;
  chapterTitle?: string;
  availableCharacters: CharacterImage[];
  onGenerate: (description: string, characterIds: string[]) => void;
  isGenerating: boolean;
  parentSceneImageUrl?: string;  // For suggested shots - shows reference for consistency
  isSuggestedShot?: boolean;     // Flag to show "suggested shot" context in UI
  userTier?: string;             // User subscription tier for character limits
  sceneContext?: string;         // Additional context from the script for AI enhancement
}

const SceneGenerationModal: React.FC<SceneGenerationModalProps> = ({
  isOpen,
  onClose,
  sceneNumber,
  initialDescription,
  chapterTitle,
  availableCharacters,
  onGenerate,
  isGenerating,
  parentSceneImageUrl,
  isSuggestedShot = false,
  userTier = 'free',
  sceneContext
}) => {
  const [description, setDescription] = useState(initialDescription);
  const [selectedCharacterIds, setSelectedCharacterIds] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [showUpgradeHint, setShowUpgradeHint] = useState(false);

  // AI Assist state
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [hasEnhanced, setHasEnhanced] = useState(false);
  const [originalDescription, setOriginalDescription] = useState('');
  const [suggestedShotTypes, setSuggestedShotTypes] = useState<string[]>([]);

  // Get character limit for user's tier
  const characterLimit = TIER_CHARACTER_LIMITS[userTier.toLowerCase()] || TIER_CHARACTER_LIMITS.free;
  const aiAssistLimit = TIER_AI_ASSIST_LIMITS[userTier.toLowerCase()] || TIER_AI_ASSIST_LIMITS.free;

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setDescription(initialDescription);
      setSelectedCharacterIds(new Set());
      setSearchTerm('');
      setShowUpgradeHint(false);
      setIsEnhancing(false);
      setHasEnhanced(false);
      setOriginalDescription('');
      setSuggestedShotTypes([]);
    }
  }, [isOpen, initialDescription]);

  // AI Assist: Enhance description
  const handleEnhanceDescription = async () => {
    if (isEnhancing || !description.trim()) return;

    setIsEnhancing(true);
    setOriginalDescription(description);

    try {
      // Get selected character names for context
      const selectedCharNames = availableCharacters
        .filter(c => selectedCharacterIds.has(c.id || ''))
        .map(c => c.name)
        .filter((n): n is string => !!n);

      const result = await userService.enhanceScenePrompt({
        scene_description: description,
        scene_context: sceneContext,
        characters_in_scene: selectedCharNames.length > 0 ? selectedCharNames : undefined,
        style: 'cinematic',
      });

      setDescription(result.enhanced_description);
      setSuggestedShotTypes(result.suggested_shot_types || []);
      setHasEnhanced(true);
      toast.success('Description enhanced for better image generation');
    } catch (error: any) {
      console.error('Failed to enhance description:', error);
      // Extract error message from API response
      const errorDetail = error?.response?.data?.detail;
      if (error?.response?.status === 429 && errorDetail?.message) {
        toast.error(errorDetail.message);
      } else if (typeof errorDetail === 'string') {
        toast.error(errorDetail);
      } else {
        toast.error('Failed to enhance description. Please try again.');
      }
    } finally {
      setIsEnhancing(false);
    }
  };

  // Revert to original description
  const handleRevertDescription = () => {
    if (originalDescription) {
      setDescription(originalDescription);
      setHasEnhanced(false);
      setSuggestedShotTypes([]);
      toast.success('Reverted to original description');
    }
  };

  // Apply a suggested shot type
  const applyShotType = (shotType: string) => {
    const shotPrefix = `${shotType} of `;
    if (!description.toLowerCase().startsWith(shotType.toLowerCase())) {
      setDescription(shotPrefix + description);
    }
  };

  if (!isOpen) return null;

  const toggleCharacterSelection = (characterId: string | undefined) => {
    if (!characterId) return;
    const newSelected = new Set(selectedCharacterIds);
    if (newSelected.has(characterId)) {
      newSelected.delete(characterId);
      setShowUpgradeHint(false);
    } else {
      if (newSelected.size >= characterLimit) {
        // Show upgrade hint instead of silently blocking
        setShowUpgradeHint(true);
        return; 
      }
      newSelected.add(characterId);
      setShowUpgradeHint(false);
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
            {isSuggestedShot && (
              <span className="mt-1 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-900/50 text-blue-300">
                Suggested Shot
              </span>
            )}
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Parent Scene Reference (for suggested shots) */}
          {parentSceneImageUrl && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">
                Reference Scene
                <span className="ml-2 text-xs text-gray-500 font-normal">
                  (Your shot will match this scene's style and characters)
                </span>
              </label>
              <div className="relative rounded-lg overflow-hidden border border-gray-700 w-48 h-28">
                <img 
                  src={parentSceneImageUrl} 
                  alt="Parent scene reference" 
                  className="w-full h-full object-cover"
                />
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                  <span className="text-xs text-gray-300">Main Scene</span>
                </div>
              </div>
            </div>
          )}

          {/* Detailed Scene Description */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-300">
                Scene Description
                <span className="ml-2 text-xs text-gray-500 font-normal">
                  (Used as the generation prompt)
                </span>
              </label>
              <div className="flex items-center gap-2">
                {hasEnhanced && (
                  <button
                    onClick={handleRevertDescription}
                    className="flex items-center gap-1 px-2 py-1 text-xs text-gray-400 hover:text-gray-200 bg-gray-800 hover:bg-gray-700 rounded transition-colors"
                    title="Revert to original"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Revert
                  </button>
                )}
                <button
                  onClick={handleEnhanceDescription}
                  disabled={isEnhancing || !description.trim()}
                  className={`
                    flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all
                    ${isEnhancing
                      ? 'bg-purple-900/50 text-purple-300 cursor-wait'
                      : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-500/20'}
                    ${!description.trim() ? 'opacity-50 cursor-not-allowed' : ''}
                  `}
                  title={`Enhance with AI (${aiAssistLimit}/day limit)`}
                >
                  {isEnhancing ? (
                    <>
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Enhancing...
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-3 h-3" />
                      AI Enhance
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="relative">
              <textarea
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  if (hasEnhanced) setHasEnhanced(false);
                }}
                className={`
                  w-full h-32 bg-[#141414] border rounded-lg p-3 text-gray-200
                  focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500
                  transition-colors resize-none
                  ${hasEnhanced ? 'border-purple-500/50 ring-1 ring-purple-500/20' : 'border-gray-800'}
                `}
                placeholder="Describe the scene in detail..."
              />
              {hasEnhanced && (
                <div className="absolute top-2 right-2">
                  <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-purple-300 bg-purple-900/50 rounded-full">
                    <Sparkles className="w-3 h-3" />
                    Enhanced
                  </span>
                </div>
              )}
            </div>

            {/* Suggested Shot Types */}
            {suggestedShotTypes.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="text-xs text-gray-500">Suggested shots:</span>
                {suggestedShotTypes.map((shot) => (
                  <button
                    key={shot}
                    onClick={() => applyShotType(shot)}
                    className="px-2 py-1 text-xs text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-full transition-colors"
                  >
                    {shot}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Character References */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-300">
                Reference Characters
                <span className="ml-2 text-xs text-gray-500 font-normal">
                  (Select up to {characterLimit})
                </span>
              </label>
              <span className="text-xs text-indigo-400 font-medium">
                {selectedCharacterIds.size}/{characterLimit} selected
              </span>
            </div>

            {/* Upgrade Notification */}
            {showUpgradeHint && (
              <div className="flex items-center gap-2 p-3 bg-gradient-to-r from-indigo-900/40 to-purple-900/40 border border-indigo-700/50 rounded-lg">
                <Sparkles className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                <p className="text-xs text-indigo-200">
                  You've reached your limit of {characterLimit} characters.{' '}
                  <a href="/pricing" className="text-indigo-400 hover:text-indigo-300 underline font-medium">
                    Upgrade your subscription
                  </a>
                  {' '}for more character references.
                </p>
              </div>
            )}

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
              ) : filteredCharacters.map((char) => {
                const entityType = (char as any).entity_type || 'character';
                const isObject = entityType === 'object';
                const isLocation = entityType === 'location';
                const borderColorSelected = isObject 
                  ? 'border-purple-500 ring-2 ring-purple-500/20' 
                  : isLocation 
                    ? 'border-amber-500 ring-2 ring-amber-500/20'
                    : 'border-indigo-500 ring-2 ring-indigo-500/20';
                const indicatorColor = isObject 
                  ? 'bg-purple-500' 
                  : isLocation 
                    ? 'bg-amber-500' 
                    : 'bg-indigo-500';

                return (
                  <button
                    key={`${char.id}-${entityType}`}
                    onClick={() => toggleCharacterSelection(char.id)}
                    className={`
                      group relative aspect-square rounded-lg overflow-hidden border-2 transition-all
                      ${selectedCharacterIds.has(char.id || '') 
                        ? borderColorSelected 
                        : 'border-transparent hover:border-gray-600'}
                    `}
                  >
                    <img 
                      src={char.imageUrl || ''} 
                      alt={char.name || 'Character'} 
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-100" />
                    
                    {/* Entity Type Icon */}
                    {(isObject || isLocation) && (
                      <div className={`absolute top-2 left-2 p-1 rounded ${isObject ? 'bg-purple-600' : 'bg-amber-600'}`}>
                        {isObject ? <Box className="w-3 h-3 text-white" /> : <MapPin className="w-3 h-3 text-white" />}
                      </div>
                    )}
                    
                    <span className="absolute bottom-1.5 left-2 right-2 text-xs font-medium text-white truncate text-left">
                      {char.name || 'Unknown'}
                    </span>
                    
                    {/* Selection Indicator */}
                    {selectedCharacterIds.has(char.id || '') && (
                      <div className={`absolute top-2 right-2 w-5 h-5 ${indicatorColor} rounded-full flex items-center justify-center shadow-sm`}>
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    )}
                  </button>
                );
              })}
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
