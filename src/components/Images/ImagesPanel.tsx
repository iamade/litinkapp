import React, { useState, useEffect } from 'react';
import {
  Image,
  Users,
  Camera,
  Download,
  Trash2,
  RefreshCw,
  Settings,
  Grid3X3,
  List,
  Loader2,
  Eye,
  Plus,
  Wand2
} from 'lucide-react';
import { userService } from '../../services/userService';
import { Tables } from '../../types/supabase';
import { toast } from 'react-hot-toast';
import { useImageGeneration } from '../../hooks/useImageGeneration';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';

interface SceneImage {
  sceneNumber: number;
  imageUrl: string;
  prompt: string;
  characters: string[];
  generationStatus: 'pending' | 'generating' | 'completed' | 'failed';
  generatedAt?: string;
  id?: string;
  script_id?: string;
}

interface CharacterImage {
  name: string;
  imageUrl: string;
  prompt: string;
  generationStatus: 'pending' | 'generating' | 'completed' | 'failed';
  generatedAt?: string;
  id?: string;
}

interface ImageGenerationOptions {
  style: 'realistic' | 'cartoon' | 'cinematic' | 'fantasy' | 'sketch';
  quality: 'standard' | 'hd';
  aspectRatio: '16:9' | '4:3' | '1:1' | '9:16';
  useCharacterReferences: boolean;
  includeBackground: boolean;
  lightingMood: string;
}

interface ImagesPanelProps {
  chapterTitle: string;
  selectedScript: unknown;
  plotOverview: { characters?: Array<{ name: string; role?: string; physical_description?: string; personality?: string }> } | null;
}

const ImagesPanel: React.FC<ImagesPanelProps> = ({
  chapterTitle,
  selectedScript,
  plotOverview
}) => {
  const {
    selectedScriptId,
    stableSelectedChapterId,
    versionToken,
    isSwitching
  } = useScriptSelection();

  const [activeTab, setActiveTab] = useState<'scenes' | 'characters'>('characters');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showSettings, setShowSettings] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState<'scenes' | 'characters' | null>(null);
  const [generationOptions, setGenerationOptions] = useState<ImageGenerationOptions>({
    style: 'cinematic',
    quality: 'hd',
    aspectRatio: '16:9',
    useCharacterReferences: true,
    includeBackground: true,
    lightingMood: 'natural'
  });

  const {
    sceneImages,
    characterImages,
    generatingScenes,
    generatingCharacters,
    loadImages,
    generateSceneImage,
    generateCharacterImage,
    regenerateImage,
    deleteImage,
    generateAllSceneImages,
    generateAllCharacterImages
  } = useImageGeneration(stableSelectedChapterId ?? '', selectedScriptId);

  // Trigger refresh on selection/version changes
  useEffect(() => {
    if (!stableSelectedChapterId) {
      return;
    }
    loadImages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stableSelectedChapterId, versionToken]);

  // Empty state when no script or chapter is selected
  if (!selectedScriptId || !stableSelectedChapterId) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <div className="text-center">
          <Camera className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p className="text-lg font-medium">Select a script to view images</p>
          <p className="text-sm">Choose a script from the sidebar to generate and view scene images</p>
          {!stableSelectedChapterId && (
            <p className="text-xs text-orange-500 mt-2">Chapter ID not available</p>
          )}
        </div>
      </div>
    );
  }

  // Disable actions during switching
  const isDisabled = isSwitching;


  // Get scenes from selected script and normalize format
  const scenes = React.useMemo(() => {
    if (typeof selectedScript === "object" && selectedScript !== null && "scene_descriptions" in selectedScript) {
      const sceneDescriptions = (selectedScript as { scene_descriptions?: any[] }).scene_descriptions || [];

      // Transform scene_descriptions to proper scene objects
      return sceneDescriptions.map((scene, idx) => {
        // If it's already an object with the right structure, return it
        if (typeof scene === 'object' && scene !== null && ('visual_description' in scene || 'description' in scene)) {
          return {
            scene_number: scene.scene_number || idx + 1,
            visual_description: scene.visual_description || scene.description || '',
            ...scene
          };
        }

        // If it's a string, convert it to an object
        if (typeof scene === 'string') {
          return {
            scene_number: idx + 1,
            visual_description: scene,
            description: scene
          };
        }

        // Fallback for any other format
        return {
          scene_number: idx + 1,
          visual_description: String(scene),
          description: String(scene)
        };
      });
    }
    return [];
  }, [selectedScript]);

  // Get characters from selected script (primary source) or fallback to plot overview
  const characters = React.useMemo(() => {

    // First priority: characters from the selected script
    if (typeof selectedScript === "object" && selectedScript !== null && "characters" in selectedScript) {
      const scriptCharacters = (selectedScript as { characters?: any[] }).characters || [];
      if (scriptCharacters.length > 0) {
        // Convert simple string array to object format if needed
        return scriptCharacters.map(char =>
          typeof char === 'string' ? { name: char } : char
        );
      }
    }

    // Fallback: use plot overview characters
    if (plotOverview?.characters && plotOverview.characters.length > 0) {
      return plotOverview.characters;
    }

    return [];
  }, [selectedScriptId, selectedScript, plotOverview]);

  const handleGenerateAllScenes = async () => {
    if (!scenes.length) {
      toast.error('No scenes available to generate images for');
      return;
    }

    setConfirmAction('scenes');
    setShowConfirmModal(true);
  };

  const handleGenerateAllCharacters = async () => {
    if (!characters.length) {
      toast.error('No characters available to generate images for');
      return;
    }

    setConfirmAction('characters');
    setShowConfirmModal(true);
  };

  const handleConfirmGeneration = async () => {
    setShowConfirmModal(false);

    if (confirmAction === 'scenes') {
      await generateAllSceneImages(scenes, generationOptions);
    } else if (confirmAction === 'characters') {
      // Build character details from plot overview
      const characterDetails: Record<string, string> = {};
      if (plotOverview?.characters) {
        (plotOverview?.characters ?? []).forEach((char) => {
          if (typeof char === "object" && char !== null && "name" in char) {
            characterDetails[(char as { name: string }).name] =
              `${(char as any).physical_description ?? ""}. ${(char as any).personality ?? ""}. ${(char as any).role ?? ""}`;
          }
        });
      } else {
        // Fallback to basic descriptions
        characters.forEach((char) => {
          const name = typeof char === "string" ? char : (char as { name: string }).name;
          characterDetails[name] = `Portrait of ${name}, detailed character design`;
        });
      }

      await generateAllCharacterImages(
        characters.map((char) => (typeof char === "string" ? char : (char as { name: string }).name)),
        characterDetails,
        generationOptions
      );
    }

    setConfirmAction(null);
  };

  const renderHeader = () => (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h3 className="text-xl font-semibold text-gray-900">Scene Images</h3>
        <p className="text-gray-600">Generate character and scene visualizations for {chapterTitle}</p>
        {isSwitching && (
          <div className="flex items-center space-x-2 mt-1 text-sm text-blue-600">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Switching script...</span>
          </div>
        )}
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={() => setShowSettings(!showSettings)}
          disabled={isDisabled}
          className="flex items-center space-x-2 px-3 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Settings className="w-4 h-4" />
          <span>Settings</span>
        </button>
        <div className="flex border rounded-md">
          <button
            onClick={() => setViewMode('grid')}
            disabled={isDisabled}
            className={`p-2 ${viewMode === 'grid' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:bg-gray-100'} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <Grid3X3 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            disabled={isDisabled}
            className={`p-2 ${viewMode === 'list' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:bg-gray-100'} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  const renderGenerationSettings = () => (
    showSettings && (
      <div className="bg-white border rounded-lg p-6 mb-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Generation Settings</h4>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Style</label>
            <select
              value={generationOptions.style}
              onChange={(e) => setGenerationOptions(prev => ({ 
                ...prev, 
                style: e.target.value as any 
              }))}
              className="w-full border rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="realistic">Realistic</option>
              <option value="cinematic">Cinematic</option>
              <option value="cartoon">Cartoon</option>
              <option value="fantasy">Fantasy</option>
              <option value="sketch">Sketch</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Quality</label>
            <select
              value={generationOptions.quality}
              onChange={(e) => setGenerationOptions(prev => ({ 
                ...prev, 
                quality: e.target.value as any 
              }))}
              className="w-full border rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="standard">Standard</option>
              <option value="hd">High Definition</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Aspect Ratio</label>
            <select
              value={generationOptions.aspectRatio}
              onChange={(e) => setGenerationOptions(prev => ({ 
                ...prev, 
                aspectRatio: e.target.value as any 
              }))}
              className="w-full border rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="16:9">16:9 (Widescreen)</option>
              <option value="4:3">4:3 (Standard)</option>
              <option value="1:1">1:1 (Square)</option>
              <option value="9:16">9:16 (Portrait)</option>
            </select>
          </div>
        </div>

        <div className="mt-4 space-y-3">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={generationOptions.useCharacterReferences}
              onChange={(e) => setGenerationOptions(prev => ({ 
                ...prev, 
                useCharacterReferences: e.target.checked 
              }))}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="ml-2 text-sm text-gray-700">Use character reference images</span>
          </label>

          <label className="flex items-center">
            <input
              type="checkbox"
              checked={generationOptions.includeBackground}
              onChange={(e) => setGenerationOptions(prev => ({ 
                ...prev, 
                includeBackground: e.target.checked 
              }))}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="ml-2 text-sm text-gray-700">Include detailed backgrounds</span>
          </label>
        </div>

        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Lighting Mood</label>
          <input
            type="text"
            value={generationOptions.lightingMood}
            onChange={(e) => setGenerationOptions(prev => ({ 
              ...prev, 
              lightingMood: e.target.value 
            }))}
            className="w-full border rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., natural, dramatic, soft, moody"
          />
        </div>
      </div>
    )
  );

  const renderTabNavigation = () => (
    <div className="flex space-x-1 bg-gray-100 rounded-lg p-1 mb-6">
      <button
        onClick={() => setActiveTab('characters')}
        className={`flex items-center space-x-2 px-4 py-2 rounded-md font-medium text-sm transition-colors ${
          activeTab === 'characters'
            ? 'bg-white text-blue-600 shadow-sm'
            : 'text-gray-600 hover:text-gray-800'
        }`}
      >
        <Users className="w-4 h-4" />
        <span>Characters</span>
        <span className="px-2 py-1 bg-gray-200 text-gray-600 rounded-full text-xs">
          {characters.length}
        </span>
      </button>

      <button
        onClick={() => setActiveTab('scenes')}
        className={`flex items-center space-x-2 px-4 py-2 rounded-md font-medium text-sm transition-colors ${
          activeTab === 'scenes'
            ? 'bg-white text-blue-600 shadow-sm'
            : 'text-gray-600 hover:text-gray-800'
        }`}
      >
        <Camera className="w-4 h-4" />
        <span>Scenes</span>
        <span className="px-2 py-1 bg-gray-200 text-gray-600 rounded-full text-xs">
          {scenes.length}
        </span>
      </button>
    </div>
  );

  const renderScenesTab = () => {
    // Filter images by selected script_id, accepting both script_id and scriptId fields
    const filteredSceneImages = Object.entries(sceneImages || {}).reduce((acc, [key, image]) => {
      const normalizedScriptId = image.script_id ?? (image as any).scriptId;
      if (!selectedScriptId || normalizedScriptId === selectedScriptId) {
        acc[key] = image;
      }
      return acc;
    }, {} as Record<string | number, SceneImage>);
    const sourceSceneImages = filteredSceneImages;
    const hasImages = Object.keys(sourceSceneImages).length > 0;

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-lg font-semibold text-gray-900">Scene Images</h4>
          <button
            onClick={handleGenerateAllScenes}
            disabled={!scenes.length || generatingScenes.size > 0}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
          >
            <Wand2 className="w-4 h-4" />
            <span>Generate All Scenes</span>
          </button>
        </div>

        {!scenes.length ? (
          <div className="text-center py-12 text-gray-500">
            <Camera className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">No scenes available</p>
            <p className="text-sm">Generate a script first to create scene images</p>
          </div>
        ) : !hasImages ? (
          <div className="text-center py-8 text-gray-500">
            <Camera className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">No images generated yet</p>
            <p className="text-sm">Generate images for the current chapter scenes</p>
          </div>
        ) : (
          <div className={`${
            viewMode === 'grid'
              ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
              : 'space-y-4'
          }`}>
            {scenes.map((scene: any, idx: number) => {
              const sceneNumber = scene.scene_number || idx + 1;
              const sceneImage = sourceSceneImages?.[sceneNumber];
              return (
                <SceneImageCard
                  key={sceneNumber}
                  scene={scene}
                  sceneImage={sceneImage}
                  isGenerating={generatingScenes.has(sceneNumber)}
                  viewMode={viewMode}
                  onGenerate={() => generateSceneImage(
                    sceneNumber,
                    scene.visual_description || scene.description || '',
                    generationOptions
                  )}
                  onRegenerate={() => regenerateImage(
                    'scene',
                    sceneNumber,
                    generationOptions
                  )}
                  onDelete={() => deleteImage('scene', sceneNumber)}
                  onView={() => setSelectedImage(sceneImage?.imageUrl || null)}
                />
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const renderCharactersTab = () => {
    // Filter character images by selected script_id, accepting both script_id and scriptId fields
    // Include images that match the selected script OR have no script_id (legacy images)
    const filteredCharacterImages = Object.entries(characterImages || {}).reduce((acc, [key, image]) => {
      const normalizedScriptId = image.script_id ?? (image as any).scriptId;
      const shouldInclude = !selectedScriptId || !normalizedScriptId || normalizedScriptId === selectedScriptId;
      if (shouldInclude) {
        acc[key] = image;
      }
      return acc;
    }, {} as Record<string, CharacterImage>);
    const hasCharacterImages = filteredCharacterImages && Object.keys(filteredCharacterImages).length > 0;

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-lg font-semibold text-gray-900">Character Images for Current Script</h4>
            <p className="text-xs text-gray-500 mt-1">
              Scene-specific character images. Global character images are managed in Plot Overview.
            </p>
          </div>
          <button
            onClick={handleGenerateAllCharacters}
            disabled={!characters.length || generatingCharacters.size > 0}
            className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-gray-400"
          >
            <Wand2 className="w-4 h-4" />
            <span>Generate All Characters</span>
          </button>
        </div>

        {!characters.length ? (
          <div className="text-center py-12 text-gray-500">
            <Users className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">No characters available</p>
            <p className="text-sm">Generate a script to see character images</p>
          </div>
        ) : (
          <>
            {!hasCharacterImages && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <p className="text-sm text-blue-800">
                  <strong>{characters.length} character{characters.length !== 1 ? 's' : ''}</strong> found in the selected script.
                  Generate images individually or use "Generate All Characters" button.
                </p>
              </div>
            )}
            <div className={`${
              viewMode === 'grid'
                ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'
                : 'space-y-4'
            }`}>
              {characters.map((character) => {
                const characterKey = typeof character === "string" ? character : character.name;
                const characterImage = filteredCharacterImages?.[characterKey];
                return (
                  <CharacterImageCard
                    key={characterKey}
                    characterName={characterKey}
                    characterImage={characterImage}
                    characterDetails={character}
                    isGenerating={generatingCharacters.has(characterKey)}
                    viewMode={viewMode}
                    onGenerate={() => {
                      const description =
                        typeof character === "object" && character.physical_description && character.personality && character.role
                          ? `${character.physical_description}. ${character.personality}. ${character.role}`
                          : `Portrait of ${characterKey}, detailed character design`;
                      generateCharacterImage(characterKey, description, generationOptions);
                    }}
                    onRegenerate={() => regenerateImage('character', characterKey, generationOptions)}
                    onDelete={() => deleteImage('character', characterKey)}
                    onView={() => setSelectedImage(characterImage?.imageUrl || null)}
                  />
                );
              })}
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {renderHeader()}
      {renderGenerationSettings()}
      {renderTabNavigation()}
      
      {activeTab === 'characters' && renderCharactersTab()}
      {activeTab === 'scenes' && renderScenesTab()}

      {/* Image Viewer Modal */}
      {selectedImage && (
        <ImageViewerModal
          imageUrl={selectedImage}
          onClose={() => setSelectedImage(null)}
        />
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <ConfirmationModal
          isOpen={showConfirmModal}
          onClose={() => {
            setShowConfirmModal(false);
            setConfirmAction(null);
          }}
          onConfirm={handleConfirmGeneration}
          title={confirmAction === 'scenes' ? 'Generate All Scene Images' : 'Generate All Character Images'}
          message={
            confirmAction === 'scenes'
              ? `Generate images for all ${scenes.length} scene${scenes.length !== 1 ? 's' : ''}? This may take several minutes.`
              : `Generate images for all ${characters.length} character${characters.length !== 1 ? 's' : ''}? This will create image references for every character in the script.`
          }
          confirmText="Generate All"
          confirmButtonClass="bg-blue-600 hover:bg-blue-700"
        />
      )}
    </div>
  );
};

// Scene Image Card Component
interface SceneImageCardProps {
  scene: any;
  sceneImage?: SceneImage;
  isGenerating: boolean;
  viewMode: 'grid' | 'list';
  onGenerate: () => void;
  onRegenerate: () => void;
  onDelete: () => void;
  onView: () => void;
}

const SceneImageCard: React.FC<SceneImageCardProps> = ({
  scene,
  sceneImage,
  isGenerating,
  viewMode,
  onGenerate,
  onRegenerate,
  onDelete,
  onView
}) => {
  if (viewMode === 'list') {
    return (
      <div className="bg-white border rounded-lg p-4">
        <div className="flex items-center space-x-4">
          <div className="flex-shrink-0">
            <ImageThumbnail
              imageUrl={sceneImage?.imageUrl}
              isGenerating={isGenerating}
              alt={`Scene ${scene.scene_number}`}
              size="small"
            />
          </div>
          
          <div className="flex-1 min-w-0">
            <h5 className="font-medium text-gray-900 truncate">
              Scene {scene.scene_number}: {scene.location}
            </h5>
            <p className="text-sm text-gray-600 line-clamp-2">
              {scene.visual_description}
            </p>
            {scene.characters && scene.characters.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {scene.characters.slice(0, 3).map((char: string, idx: number) => (
                  <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                    {char}
                  </span>
                ))}
                {scene.characters.length > 3 && (
                  <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                    +{scene.characters.length - 3} more
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <ImageActions
              hasImage={!!sceneImage?.imageUrl}
              isGenerating={isGenerating}
              onGenerate={onGenerate}
              onRegenerate={onRegenerate}
              onDelete={onDelete}
              onView={onView}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border rounded-lg overflow-hidden">
      <div className="aspect-video relative">
        <ImageThumbnail
          imageUrl={sceneImage?.imageUrl}
          isGenerating={isGenerating}
          alt={`Scene ${scene.scene_number}`}
          size="large"
        />
        
        <div className="absolute top-2 left-2">
          <span className="px-2 py-1 bg-black bg-opacity-70 text-white text-xs rounded">
            Scene {scene.scene_number}
          </span>
        </div>

        <div className="absolute top-2 right-2">
          <ImageActions
            hasImage={!!sceneImage?.imageUrl}
            isGenerating={isGenerating}
            onGenerate={onGenerate}
            onRegenerate={onRegenerate}
            onDelete={onDelete}
            onView={onView}
            compact
          />
        </div>
      </div>

      <div className="p-4">
        <h5 className="font-medium text-gray-900 mb-2">
          {scene.location}
        </h5>
        <p className="text-sm text-gray-600 line-clamp-3 mb-3">
          {scene.visual_description}
        </p>
        
        {scene.characters && scene.characters.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {scene.characters.slice(0, 2).map((char: string, idx: number) => (
              <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                {char}
              </span>
            ))}
            {scene.characters.length > 2 && (
              <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                +{scene.characters.length - 2}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Character Image Card Component
interface CharacterImageCardProps {
  characterName: string;
  characterImage?: CharacterImage;
  characterDetails?: Tables<'characters'> | string;
  isGenerating: boolean;
  viewMode: 'grid' | 'list';
  onGenerate: () => void;
  onRegenerate: () => void;
  onDelete: () => void;
  onView: () => void;
}

const CharacterImageCard: React.FC<CharacterImageCardProps> = ({
  characterName,
  characterImage,
  characterDetails,
  isGenerating,
  viewMode,
  onGenerate,
  onRegenerate,
  onDelete,
  onView
}) => {
  if (viewMode === 'list') {
    return (
      <div className="bg-white border rounded-lg p-4">
        <div className="flex items-center space-x-4">
          <div className="flex-shrink-0">
            <ImageThumbnail
              imageUrl={characterImage?.imageUrl}
              isGenerating={isGenerating}
              alt={characterName}
              size="small"
            />
          </div>
          
          <div className="flex-1 min-w-0">
            <h5 className="font-medium text-gray-900">{characterName}</h5>
            <p className="text-sm text-gray-600">
              {typeof characterDetails === "object" && characterDetails !== null
                ? (characterDetails as any).role ?? ""
                : ""}
            </p>
            {typeof characterDetails === "object" &&
              characterDetails !== null &&
              (characterDetails as any).physical_description && (
                <p className="text-sm text-gray-500 line-clamp-2 mt-1">
                  {(characterDetails as any).physical_description}
                </p>
              )}
          </div>

          <div className="flex items-center space-x-2">
            <ImageActions
              hasImage={!!characterImage?.imageUrl}
              isGenerating={isGenerating}
              onGenerate={onGenerate}
              onRegenerate={onRegenerate}
              onDelete={onDelete}
              onView={onView}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border rounded-lg overflow-hidden">
      <div className="aspect-[3/4] relative">
        <ImageThumbnail
          imageUrl={characterImage?.imageUrl}
          isGenerating={isGenerating}
          alt={characterName}
          size="large"
        />
        
        <div className="absolute top-2 right-2">
          <ImageActions
            hasImage={!!characterImage?.imageUrl}
            isGenerating={isGenerating}
            onGenerate={onGenerate}
            onRegenerate={onRegenerate}
            onDelete={onDelete}
            onView={onView}
            compact
          />
        </div>
      </div>

      <div className="p-4">
        <h5 className="font-medium text-gray-900 mb-1">{characterName}</h5>
        <p className="text-sm text-gray-600 mb-2">
          {typeof characterDetails === "object" && characterDetails !== null
            ? (characterDetails as any).role ?? ""
            : ""}
        </p>
        {typeof characterDetails === "object" &&
          characterDetails !== null &&
          (characterDetails as any).physical_description && (
            <p className="text-xs text-gray-500 line-clamp-3">
              {(characterDetails as any).physical_description}
            </p>
          )}
      </div>
    </div>
  );
};

// Image Thumbnail Component
interface ImageThumbnailProps {
  imageUrl?: string;
  isGenerating: boolean;
  alt: string;
  size: 'small' | 'large';
}

const ImageThumbnail: React.FC<ImageThumbnailProps> = ({ 
  imageUrl, 
  isGenerating, 
  alt, 
  size 
}) => {
  const sizeClasses = size === 'small' 
    ? 'w-16 h-16' 
    : 'w-full h-full';

  if (isGenerating) {
    return (
      <div className={`${sizeClasses} bg-gray-100 flex items-center justify-center rounded-md`}>
        <div className="text-center">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400 mx-auto mb-2" />
          <span className="text-xs text-gray-500">Generating...</span>
        </div>
      </div>
    );
  }


  if (imageUrl) {
    return (
      <img
        src={imageUrl}
        alt={alt}
        className={`${sizeClasses} object-cover rounded-md`}
      />
    );
  }

  return (
    <div className={`${sizeClasses} bg-gray-100 flex items-center justify-center rounded-md`}>
      <Image className="w-6 h-6 text-gray-400" />
    </div>
  );
};

// Image Actions Component
interface ImageActionsProps {
  hasImage: boolean;
  isGenerating: boolean;
  onGenerate: () => void;
  onRegenerate: () => void;
  onDelete: () => void;
  onView: () => void;
  compact?: boolean;
}

const ImageActions: React.FC<ImageActionsProps> = ({
  hasImage,
  isGenerating,
  onGenerate,
  onRegenerate,
  onDelete,
  onView,
  compact = false
}) => {
  if (compact) {
    return (
      <div className="flex space-x-1">
        {hasImage ? (
          <>
            <button
              onClick={onView}
              className="p-1 bg-black bg-opacity-50 text-white rounded hover:bg-opacity-70"
            >
              <Eye className="w-4 h-4" />
            </button>
            <button
              onClick={onRegenerate}
              disabled={isGenerating}
              className="p-1 bg-black bg-opacity-50 text-white rounded hover:bg-opacity-70 disabled:opacity-50"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </>
        ) : (
          <button
            onClick={onGenerate}
            disabled={isGenerating}
            className="p-1 bg-black bg-opacity-50 text-white rounded hover:bg-opacity-70 disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex space-x-1">
      {hasImage ? (
        <>
          <button
            onClick={onView}
            className="p-2 text-blue-600 hover:bg-blue-50 rounded"
            title="View"
          >
            <Eye className="w-4 h-4" />
          </button>
          <button
            onClick={onRegenerate}
            disabled={isGenerating}
            className="p-2 text-gray-600 hover:bg-gray-50 rounded disabled:opacity-50"
            title="Regenerate"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-2 text-red-600 hover:bg-red-50 rounded"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </>
      ) : (
        <button
          onClick={onGenerate}
          disabled={isGenerating}
          className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-blue-400"
        >
          <Plus className="w-4 h-4" />
          <span>Generate</span>
        </button>
      )}
    </div>
  );
};

// Image Viewer Modal
interface ImageViewerModalProps {
  imageUrl: string;
  onClose: () => void;
}

const ImageViewerModal: React.FC<ImageViewerModalProps> = ({ imageUrl, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75">
      <div className="bg-white rounded-lg p-4 max-w-4xl max-h-[90vh] w-full mx-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Image Preview</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
          >
            ×
          </button>
        </div>
        
        <div className="flex justify-center">
          <img
            src={imageUrl}
            alt="Generated image"
            className="max-w-full max-h-[70vh] object-contain rounded"
          />
        </div>
        
        <div className="mt-4 flex justify-end space-x-2">
          <a
            href={imageUrl}
            download
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            <Download className="w-4 h-4" />
            <span>Download</span>
          </a>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

// Confirmation Modal Component
interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText: string;
  confirmButtonClass?: string;
}

const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText,
  confirmButtonClass = 'bg-blue-600 hover:bg-blue-700'
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        />

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div className="sm:flex sm:items-start">
            <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
              <Wand2 className="h-6 w-6 text-blue-600" />
            </div>
            <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                {title}
              </h3>
              <div className="mt-2">
                <p className="text-sm text-gray-500">
                  {message}
                </p>
              </div>
            </div>
          </div>
          <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              onClick={onConfirm}
              className={`w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 text-base font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm ${confirmButtonClass}`}
            >
              {confirmText}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:w-auto sm:text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImagesPanel;