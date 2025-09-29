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
  Play,
  Loader2,
  Eye,
  Plus,
  Wand2
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useImageGeneration } from '../../hooks/useImageGeneration';

interface SceneImage {
  sceneNumber: number;
  imageUrl: string;
  prompt: string;
  characters: string[];
  generationStatus: 'pending' | 'generating' | 'completed' | 'failed';
  generatedAt?: string;
  id?: string;
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
  chapterId: string;
  chapterTitle: string;
  selectedScript: any;
  plotOverview: any;
}

const ImagesPanel: React.FC<ImagesPanelProps> = ({
  chapterId,
  chapterTitle,
  selectedScript,
  plotOverview
}) => {
  const [activeTab, setActiveTab] = useState<'scenes' | 'characters'>('characters');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showSettings, setShowSettings] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
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
    isLoading,
    generatingScenes,
    generatingCharacters,
    loadImages,
    generateSceneImage,
    generateCharacterImage,
    regenerateImage,
    deleteImage,
    generateAllSceneImages,
    generateAllCharacterImages
  } = useImageGeneration(chapterId);

  useEffect(() => {
    loadImages();
  }, [loadImages]);

  const scenes = selectedScript?.scene_descriptions || [];
  const characters = selectedScript?.characters || plotOverview?.characters?.map((c: any) => c.name) || [];

  const handleGenerateAllScenes = async () => {
    if (!scenes.length) {
      toast.error('No scenes available to generate images for');
      return;
    }
    
    if (!confirm(`Generate images for all ${scenes.length} scenes? This may take several minutes.`)) {
      return;
    }

    await generateAllSceneImages(scenes, generationOptions);
  };

  const handleGenerateAllCharacters = async () => {
    if (!characters.length) {
      toast.error('No characters available to generate images for');
      return;
    }

    if (!confirm(`Generate images for all ${characters.length} characters?`)) {
      return;
    }

    // Build character details from plot overview
    const characterDetails: Record<string, string> = {};
    if (plotOverview?.characters) {
      plotOverview.characters.forEach((char: any) => {
        characterDetails[char.name] = `${char.physicalDescription}. ${char.personality}. ${char.role}`;
      });
    } else {
      // Fallback to basic descriptions
      characters.forEach((char: string) => {
        characterDetails[char] = `Portrait of ${char}, detailed character design`;
      });
    }

    await generateAllCharacterImages(characters, characterDetails, generationOptions);
  };

  const renderHeader = () => (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h3 className="text-xl font-semibold text-gray-900">Scene Images</h3>
        <p className="text-gray-600">Generate character and scene visualizations for {chapterTitle}</p>
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="flex items-center space-x-2 px-3 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
        >
          <Settings className="w-4 h-4" />
          <span>Settings</span>
        </button>
        <div className="flex border rounded-md">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-2 ${viewMode === 'grid' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <Grid3X3 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-2 ${viewMode === 'list' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:bg-gray-100'}`}
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

  const renderScenesTab = () => (
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
      ) : (
        <div className={`${
          viewMode === 'grid' 
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
            : 'space-y-4'
        }`}>
          {scenes.map((scene: any, idx: number) => (
            <SceneImageCard
              key={scene.scene_number || idx}
              scene={scene}
              sceneImage={sceneImages[scene.scene_number || idx + 1]}
              isGenerating={generatingScenes.has(scene.scene_number || idx + 1)}
              viewMode={viewMode}
              onGenerate={() => generateSceneImage(
                scene.scene_number || idx + 1,
                scene.visual_description || scene.description || '',
                generationOptions
              )}
              onRegenerate={() => regenerateImage(
                'scene',
                scene.scene_number || idx + 1,
                generationOptions
              )}
              onDelete={() => deleteImage('scene', scene.scene_number || idx + 1)}
              onView={() => setSelectedImage(sceneImages[scene.scene_number || idx + 1]?.imageUrl || null)}
            />
          ))}
        </div>
      )}
    </div>
  );

  const renderCharactersTab = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-lg font-semibold text-gray-900">Character Images</h4>
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
          <p className="text-sm">Generate a plot overview or script to create character images</p>
        </div>
      ) : (
        <div className={`${
          viewMode === 'grid'
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'
            : 'space-y-4'
        }`}>
          {characters.map((character: string) => (
            <CharacterImageCard
              key={character}
              characterName={character}
              characterImage={characterImages[character]}
              characterDetails={plotOverview?.characters?.find((c: any) => c.name === character)}
              isGenerating={generatingCharacters.has(character)}
              viewMode={viewMode}
              onGenerate={() => {
                const char = plotOverview?.characters?.find((c: any) => c.name === character);
                const description = char 
                  ? `${char.physicalDescription}. ${char.personality}. ${char.role}`
                  : `Portrait of ${character}, detailed character design`;
                generateCharacterImage(character, description, generationOptions);
              }}
              onRegenerate={() => regenerateImage('character', character, generationOptions)}
              onDelete={() => deleteImage('character', character)}
              onView={() => setSelectedImage(characterImages[character]?.imageUrl || null)}
            />
          ))}
        </div>
      )}
    </div>
  );

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
  characterDetails?: any;
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
            <p className="text-sm text-gray-600">{characterDetails?.role}</p>
            {characterDetails?.physicalDescription && (
              <p className="text-sm text-gray-500 line-clamp-2 mt-1">
                {characterDetails.physicalDescription}
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
        <p className="text-sm text-gray-600 mb-2">{characterDetails?.role}</p>
        
        {characterDetails?.physicalDescription && (
          <p className="text-xs text-gray-500 line-clamp-3">
            {characterDetails.physicalDescription}
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

export default ImagesPanel;