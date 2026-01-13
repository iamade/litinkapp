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
  Wand2,
  Edit2,
  X,
  UserPlus,
  Check
} from 'lucide-react';
import { userService } from '../../services/userService';
import { Tables } from '../../types/supabase';
import { toast } from 'react-hot-toast';
import { useImageGeneration } from '../../hooks/useImageGeneration';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';
import { SceneImage, CharacterImage, ImageGenerationOptions } from './types';

import { projectService } from '../../services/projectService';
import SceneGenerationModal from './SceneGenerationModal';

interface ImagesPanelProps {
  chapterId: string;
  chapterTitle: string;
  selectedScript: unknown;
  plotOverview: { characters?: Array<{ name: string; role?: string; physical_description?: string; personality?: string; image_url?: string }> } | null;
  onRefreshPlotOverview?: () => void | Promise<void>;
}

const ImagesPanel: React.FC<ImagesPanelProps> = ({
  chapterId,
  chapterTitle,
  selectedScript,
  plotOverview
}) => {
  const {
    selectedScriptId,
    versionToken,
    isSwitching
  } = useScriptSelection();

  const [activeTab, setActiveTab] = useState<'scenes' | 'characters'>('characters');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showSettings, setShowSettings] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState<'scenes' | 'characters' | null>(null);
  const [selectedSceneIds, setSelectedSceneIds] = useState<Set<string>>(new Set());
  const [showDeleteConfirmModal, setShowDeleteConfirmModal] = useState(false);
  const [deleteAction, setDeleteAction] = useState<'selected' | 'all' | null>(null);
  const [generationOptions, setGenerationOptions] = useState<ImageGenerationOptions>({
    style: 'cinematic',
    quality: 'hd',
    aspectRatio: '16:9',
    useCharacterReferences: true,
    includeBackground: true,
    lightingMood: 'natural'
  });

  // Scene Generation Modal State
  const [showSceneGenerationModal, setShowSceneGenerationModal] = useState(false);
  const [selectedSceneForGeneration, setSelectedSceneForGeneration] = useState<{
    sceneNumber: number;
    description: string;
    isRegenerate: boolean;
  } | null>(null);

  // Character management state
  const [excludedCharacters, setExcludedCharacters] = useState<Set<string>>(new Set());
  const [characterRenames] = useState<Map<string, string>>(new Map());



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
    deleteGenerations,
    deleteAllSceneGenerations,
    generateAllSceneImages,
    generateAllCharacterImages,
    setCharacterImage
  } = useImageGeneration(chapterId, selectedScriptId);

  // Trigger refresh on selection/version changes
  useEffect(() => {
    if (!chapterId) {
      return;
    }
    loadImages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapterId, versionToken]);

  // Empty state when no script or chapter is selected
  if (!selectedScriptId || !chapterId) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <div className="text-center">
          <Camera className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p className="text-lg font-medium">Select a script to view images</p>
          <p className="text-sm">Choose a script from the sidebar to generate and view scene images</p>
          {!chapterId && (
            <p className="text-xs text-orange-500 mt-2">Chapter ID not available</p>
          )}
        </div>
      </div>
    );
  }

  // Disable actions during switching
  const isDisabled = isSwitching;


  // Get scenes from selected script by parsing script text (like ScriptGenerationPanel does)
  const scenes = React.useMemo(() => {
    if (typeof selectedScript !== "object" || selectedScript === null) {
      return [];
    }

    const script = selectedScript as { script?: string; scene_descriptions?: any[]; scenes?: any[] };
    const scriptText = script.script || '';
    const parsedScenes: { scene_number: number; visual_description: string; description: string; header: string; location: string }[] = [];

    // First try to parse scenes from structured scenes array
    if (script.scenes && Array.isArray(script.scenes) && script.scenes.length > 0) {
      return script.scenes.map((scene: any, idx: number) => ({
        scene_number: scene.scene_number || idx + 1,
        visual_description: scene.visual_description || scene.description || '',
        description: scene.description || scene.visual_description || '',
        header: scene.header || `Scene ${idx + 1}`,
        location: scene.location || ''
      }));
    }

    // Parse scenes from script text using ACT-SCENE headers (most reliable)
    const scenePattern = /(\*?\*?ACT\s+[IVX]+\s*-?\s*SCENE\s+\d+\*?\*?)/gi;
    const matches = [...scriptText.matchAll(scenePattern)];

    if (matches.length > 0) {
      matches.forEach((match, idx) => {
        const startIdx = match.index!;
        const endIdx = idx < matches.length - 1 ? matches[idx + 1].index! : scriptText.length;
        const sceneContent = scriptText.substring(startIdx, endIdx).trim();

        // Extract location (INT./EXT. line)
        const locationMatch = sceneContent.match(/(?:INT\.|EXT\.)[^\n]+/i);
        const location = locationMatch ? locationMatch[0] : '';

        // Get content for visual description (excluding header and location)
        const lines = sceneContent.split('\n').slice(1, 6);
        const contentLines = lines.filter(l => l.trim() && !l.trim().match(/^(?:INT\.|EXT\.)/i));
        const content = contentLines.join(' ').substring(0, 300);

        parsedScenes.push({
          scene_number: idx + 1,
          visual_description: content || location || `Scene ${idx + 1}`,
          description: content || location || `Scene ${idx + 1}`,
          header: match[0].replace(/\*/g, '').trim(),
          location: location
        });
      });

      return parsedScenes;
    }

    // Fallback to scene_descriptions if available
    if (script.scene_descriptions && Array.isArray(script.scene_descriptions) && script.scene_descriptions.length > 0) {
      // Filter out duplicates - only count entries that have ACT header or every other one
      const filteredDescriptions = script.scene_descriptions.filter((desc: any, idx: number) => {
        const text = typeof desc === 'string' ? desc : desc?.visual_description || '';
        return text.match(/^\*?\*?ACT\s+[IVX]+\s*-?\s*SCENE/i) || idx % 2 === 0;
      });

      return filteredDescriptions.map((scene: any, idx: number) => {
        if (typeof scene === 'object' && scene !== null && ('visual_description' in scene || 'description' in scene)) {
          return {
            scene_number: scene.scene_number || idx + 1,
            visual_description: scene.visual_description || scene.description || '',
            description: scene.description || scene.visual_description || '',
            header: `Scene ${idx + 1}`,
            location: ''
          };
        }

        if (typeof scene === 'string') {
          return {
            scene_number: idx + 1,
            visual_description: scene,
            description: scene,
            header: `Scene ${idx + 1}`,
            location: ''
          };
        }

        return {
          scene_number: idx + 1,
          visual_description: String(scene),
          description: String(scene),
          header: `Scene ${idx + 1}`,
          location: ''
        };
      });
    }

    return [];
  }, [selectedScript]);

  // Get characters from selected script and enrich with plot overview data
  const characters = React.useMemo(() => {
    let baseCharacters: any[] = [];
    
    // First priority: characters from the selected script
    if (typeof selectedScript === "object" && selectedScript !== null && "characters" in selectedScript) {
      const scriptCharacters = (selectedScript as { characters?: any[] }).characters || [];
      if (scriptCharacters.length > 0) {
        // Convert to normalized format and enrich with plot overview data
        baseCharacters = scriptCharacters.map((char) => {
          const charName = typeof char === 'string' ? char : char.name;

          // Try to find matching character in plot overview for enriched data
          const plotChar = plotOverview?.characters?.find(pc => {
            // Normalize strings for comparison
            const normalizeName = (n: string) => n.trim().toLowerCase().replace(/[.,]/g, '');
            const pName = normalizeName(pc.name);
            const sName = normalizeName(charName);

            // Exact match
            if (pName === sName) return true;

            // Partial match (e.g., "Harry" matches "Harry Potter")
            // Ensure we aren't matching just on common prefixes
            if (pName.includes(sName) || sName.includes(pName)) {
              return true;
            }

            // Remove common honorifics/titles for first name check
            const honorifics = ['mr', 'mrs', 'ms', 'dr', 'prof', 'professor', 'sir', 'lady', 'lord', 'king', 'queen', 'father', 'mother', 'uncle', 'aunt'];


            // Tokenize and check for conflicts
            const tokenize = (name: string) => name.split(' ').filter(p => !honorifics.includes(p));
            const pTokens = tokenize(pName);
            const sTokens = tokenize(sName);

            // Check for strict honorific mismatch (e.g. Mr vs Mrs)
            // We use the original non-normalized names to detect 'Mr.' vs 'Mrs.' accurately if needed, 
            // but normalized 'mr' vs 'mrs' works too.
            const maleTitles = ['mr', 'lord', 'sir', 'king', 'father', 'uncle'];
            const femaleTitles = ['mrs', 'miss', 'ms', 'lady', 'queen', 'mother', 'aunt'];
            
            const hasTitle = (name: string, titles: string[]) => 
                name.split(' ').some(part => titles.includes(part));

            if (
                (hasTitle(pName, maleTitles) && hasTitle(sName, femaleTitles)) ||
                (hasTitle(pName, femaleTitles) && hasTitle(sName, maleTitles))
            ) {
                return false;
            }

            // If empty tokens (rare), no match unless exact match handled above
            if (pTokens.length === 0 || sTokens.length === 0) return false;

            // Check intersection
            const intersection = pTokens.filter(t => sTokens.includes(t));
            
            // If they share no significant words, it's not a match
            if (intersection.length === 0) return false;

            // If they share words, verify no CONFLICTing unique words
            // e.g. "Lily Potter" vs "Harry Potter". Intersection="potter".
            // UniqueP="harry", UniqueS="lily". Both distinct and non-empty => Conflict.
            const uniqueP = pTokens.filter(t => !intersection.includes(t));
            const uniqueS = sTokens.filter(t => !intersection.includes(t));

            if (uniqueP.length > 0 && uniqueS.length > 0) {
                // Strong conflict if both have unique parts remaining
                // Exception: "Dumbledore" matching "Albus Dumbledore"? 
                // pTokens=[albus, dumbledore], sTokens=[dumbledore]. Intersection=[dumbledore].
                // uniqueP=[albus], uniqueS=[]. No conflict. Match.
                
                // Exception: "Professor McGonagall" vs "Minerva McGonagall"?
                // p=[minerva, mcgonagall], s=[professor, mcgonagall] (prof removed) -> s=[mcgonagall].
                // No conflict.
                
                return false;
            }

            // If we are here, one is a subset of the other (or exact match tokens)
            return true;

            return false;
          });

          // Merge script character with plot overview data if found
          if (plotChar) {
            return {
              ...plotChar,
              originalName: charName,
              // Keep original name from script for display
              displayName: charName
            };
          }

          // Return basic character if not found in plot overview
          return typeof char === 'string' 
            ? { name: char, originalName: char, displayName: char } 
            : { ...char, originalName: char.name, displayName: char.name };
        });
      }
    }

    // If no script characters, use plot overview characters
    if (baseCharacters.length === 0 && plotOverview?.characters && plotOverview.characters.length > 0) {
      baseCharacters = plotOverview.characters.map(char => ({ 
        ...char, 
        originalName: char.name,
        displayName: char.name 
      }));
    }



    // Filter out excluded characters
    baseCharacters = baseCharacters.filter(char => {
      const charKey = char.originalName || char.name;
      return !excludedCharacters.has(charKey);
    });

    // Apply renames
    baseCharacters = baseCharacters.map(char => {
      const charKey = char.originalName || char.name;
      const newName = characterRenames.get(charKey);
      if (newName) {
        return { ...char, displayName: newName };
      }
      return char;
    });

    return baseCharacters;
  }, [selectedScriptId, selectedScript, plotOverview, excludedCharacters, characterRenames]);

 











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
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Scene Images</h3>
        <p className="text-gray-600 dark:text-gray-300">Generate character and scene visualizations for {chapterTitle}</p>
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

  const handleSelectAllScenes = () => {
    const filteredSceneImages = Object.entries(sceneImages || {}).reduce((acc, [key, images]) => {
      const firstImage = images?.[0];
      const normalizedScriptId = firstImage?.script_id ?? (firstImage as any)?.scriptId;
      if (!selectedScriptId || normalizedScriptId === selectedScriptId) {
        acc[key] = images;
      }
      return acc;
    }, {} as Record<string | number, SceneImage[]>);

    const allIds = Object.values(filteredSceneImages)
      .flat()
      .filter(img => img.id)
      .map(img => img.id!);

    if (selectedSceneIds.size === allIds.length) {
      setSelectedSceneIds(new Set());
    } else {
      setSelectedSceneIds(new Set(allIds));
    }
  };

  const handleDeleteSelected = () => {
    if (selectedSceneIds.size === 0) return;
    setDeleteAction('selected');
    setShowDeleteConfirmModal(true);
  };

  const handleDeleteAllScenes = () => {
    setDeleteAction('all');
    setShowDeleteConfirmModal(true);
  };

  const handleConfirmDelete = async () => {
    setShowDeleteConfirmModal(false);

    if (deleteAction === 'selected') {
      await deleteGenerations(Array.from(selectedSceneIds));
      setSelectedSceneIds(new Set());
    } else if (deleteAction === 'all') {
      await deleteAllSceneGenerations(selectedScriptId!);
    }

    setDeleteAction(null);
  };

  // Handle opening the generation modal
  const handleGenerateSceneImage = (
    sceneNumber: number, 
    isRef = false,
    currentDescription = ""
  ) => {
    setSelectedSceneForGeneration({
      sceneNumber,
      description: currentDescription,
      isRegenerate: isRef
    });
    setShowSceneGenerationModal(true);
  };

  // Handle actual generation from modal
  const handleModalGenerate = async (description: string, characterIds: string[]) => {
    if (!selectedSceneForGeneration) return;

    const { sceneNumber } = selectedSceneForGeneration;
    const currentChapterId = chapterId; // Use prop directly since we have it
    
    if (!currentChapterId) {
        console.error("No chapter ID");
        return;
    }

    // Close modal immediately
    setShowSceneGenerationModal(false);
    setSelectedSceneForGeneration(null);



    try {
      // 1. Update scene description first
      await projectService.updateSceneDescription(
        currentChapterId,
        selectedScriptId!, // scriptId
        sceneNumber,
        description
      );

      // 2. Resolve character URLs from IDs/Names
      const resolvedImageUrls: string[] = [];
      const resolvedIds: string[] = [];

      characterIds.forEach(idOrName => {
        // Find character by ID or Name
        // Note: characters list contains both script characters and plot characters merged
        const char = characters.find(c => 
          c.id === idOrName || 
          c.name === idOrName || 
          c.originalName === idOrName ||
          c.displayName === idOrName
        );

        if (char) {
          const imageUrl = char.imageUrl || char.image_url;
          if (imageUrl) {
            resolvedImageUrls.push(imageUrl);
          }
          
          // Still pass valid UUIDs as IDs for backward compatibility/logging
          if (char.id && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(char.id)) {
            resolvedIds.push(char.id);
          }
        }
      });

      console.log(`[ImagesPanel] Resolved ${resolvedImageUrls.length} image URLs from ${characterIds.length} selections`);

      // 3. Generate image using hook (handles polling automatically)
      // Call generateSceneImage with both IDs and URLs
      await generateSceneImage(
        sceneNumber,
        description,
        generationOptions,
        resolvedIds.length > 0 ? resolvedIds : characterIds, // usage of characterIds as fallback if no valid UUIDs
        resolvedImageUrls
      );
      
    } catch (error) {
      console.error('Error generating scene image:', error);
      toast.error("Failed to start scene image generation.");

    }
  };

  const renderScenesTab = () => {
    // Filter images by selected script_id, accepting both script_id and scriptId fields
    const filteredSceneImages = Object.entries(sceneImages || {}).reduce((acc, [key, image]) => {
      // image is SceneImage[]
      const firstImage = image[0];
      const normalizedScriptId = firstImage?.script_id ?? (firstImage as any)?.scriptId;
      if (!selectedScriptId || normalizedScriptId === selectedScriptId) {
        acc[key] = image;
      }
      return acc;
    }, {} as Record<string | number, SceneImage[]>);

    // Create a lookup helper that works with both composite keys and plain scene numbers
    const getSceneImages = (sceneNumber: number): SceneImage[] => {
      // Try composite key first (preferred)
      const compositeKey = `${selectedScriptId}_${sceneNumber}`;
      if (filteredSceneImages[compositeKey]) {
        return filteredSceneImages[compositeKey];
      }
      // Fallback to plain scene number
      if (filteredSceneImages[sceneNumber]) {
        return filteredSceneImages[sceneNumber];
      }
      return [];
    };

    const sourceSceneImages = filteredSceneImages;
    const hasImages = Object.keys(sourceSceneImages).length > 0;
    const allSceneIds = Object.values(sourceSceneImages)
      .flat() // Flatten arrays of images
      .filter(img => img.id)
      .map(img => img.id!);
    const isAllSelected = allSceneIds.length > 0 && selectedSceneIds.size === allSceneIds.length;
    const isIndeterminate = selectedSceneIds.size > 0 && selectedSceneIds.size < allSceneIds.length;

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h4 className="text-lg font-semibold text-gray-900">Scene Images</h4>
            {selectedSceneIds.size > 0 && (
              <span className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                {selectedSceneIds.size} selected
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            {hasImages && (
              <>
                <button
                  onClick={handleSelectAllScenes}
                  className="flex items-center space-x-2 px-3 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                  title={isAllSelected ? "Deselect all" : "Select all"}
                >
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    ref={(el) => {
                      if (el) el.indeterminate = isIndeterminate;
                    }}
                    readOnly
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span>{isAllSelected ? "Deselect All" : "Select All"}</span>
                </button>
                <button
                  onClick={handleDeleteSelected}
                  disabled={selectedSceneIds.size === 0}
                  className="flex items-center space-x-2 px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-400"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Delete Selected</span>
                </button>
                <button
                  onClick={handleDeleteAllScenes}
                  disabled={!hasImages}
                  className="flex items-center space-x-2 px-3 py-2 bg-red-700 text-white rounded-md hover:bg-red-800 disabled:bg-gray-400"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Delete All</span>
                </button>
              </>
            )}
            <button
              onClick={handleGenerateAllScenes}
              disabled={!scenes.length || generatingScenes.size > 0}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
            >
              <Wand2 className="w-4 h-4" />
              <span>Generate All Scenes</span>
            </button>
          </div>
        </div>

        {!scenes.length ? (
          <div className="text-center py-12 text-gray-500">
            <Camera className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">No scenes available</p>
            <p className="text-sm">Generate a script first to create scene images</p>
          </div>
        ) : (
          <>
            {!hasImages && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <p className="text-sm text-blue-800">
                  <strong>{scenes.length} scene{scenes.length !== 1 ? 's' : ''}</strong> found in the selected script.
                  Generate images individually or use "Generate All Scenes" button.
                </p>
              </div>
            )}
            <div className={`${
              viewMode === 'grid'
                ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
                : 'space-y-4'
            }`}>
              {scenes.map((scene: any, idx: number) => {
                const sceneNumber = scene.scene_number || idx + 1;
                const images = getSceneImages(sceneNumber);
                
                return (
                  <SceneImageCard
                    key={sceneNumber}
                    scene={scene}
                    sceneImages={images}
                    isGenerating={generatingScenes.has(sceneNumber)}
                    selectedIds={selectedSceneIds}
                    onSelect={(selected, imageId) => {
                      if (!imageId) return;
                      setSelectedSceneIds(prev => {
                        const newSet = new Set(prev);
                        if (selected) {
                          newSet.add(imageId);
                        } else {
                          newSet.delete(imageId);
                        }
                        return newSet;
                      });
                    }}
                    onGenerate={() => handleGenerateSceneImage(
                      sceneNumber,
                      false,
                      scene.visual_description
                    )}
                    onRegenerate={() => handleGenerateSceneImage(
                      sceneNumber,
                      true,
                      scene.visual_description
                    )}
                    onDelete={(imageId) => deleteImage('scene', sceneNumber, imageId)}
                    onView={(url) => setSelectedImage(url)}
                  />
                );
              })}
            </div>
          </>
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
                // Use originalName for image lookup (persisted key), name for display/matching
                const characterKey = typeof character === "string" ? character : (character.originalName || character.name);
                const displayName = typeof character === "object" && character.displayName ? character.displayName : (character.name || characterKey);

                // Check for script-specific image first, then fall back to plot overview image
                let characterImage = filteredCharacterImages?.[characterKey];

                // If no script-specific image, check if plot overview has an image
                const plotImageUrl = typeof character === "object" && character.image_url ? character.image_url : null;

                  // Check if this is a derived/fallback image
                  const isFallbackImage = !characterImage && !!plotImageUrl;

                  if (isFallbackImage) {
                    // Create a pseudo-image object from plot overview
                    characterImage = {
                      name: characterKey,
                      imageUrl: plotImageUrl!,
                      prompt: '',
                      generationStatus: 'completed',
                      id: undefined
                    } as CharacterImage;
                  }

                return (
                  <CharacterImageCard
                    key={characterKey}
                    characterName={displayName}
                    characterImage={characterImage}
                    characterDetails={character}
                    isGenerating={generatingCharacters.has(characterKey)}
                    viewMode={viewMode}
                    fromPlotOverview={!!plotImageUrl && !filteredCharacterImages?.[characterKey]}
                    plotCharacters={plotOverview?.characters || []}
                    onGenerate={async (selectedPlotCharName) => {
                      // If user selected a plot character, check if they have an existing image
                      if (selectedPlotCharName) {
                        const plotChar = plotOverview?.characters?.find(c => c.name === selectedPlotCharName);
                        if (plotChar) {
                          // If plot character has an existing image, use it immediately
                          if (plotChar.image_url) {
                            // First update local state for immediate feedback
                            const prompt = `${plotChar.physical_description || ''}. ${plotChar.personality || ''}. ${plotChar.role || ''}`.trim();
                            setCharacterImage(characterKey, {
                              name: characterKey,
                              imageUrl: plotChar.image_url,
                              prompt: prompt,
                              generationStatus: 'completed',
                              generatedAt: new Date().toISOString(),
                              script_id: selectedScriptId ?? undefined
                            });

                            // Persist to database
                            try {
                              await userService.linkCharacterImage(chapterId, {
                                character_name: characterKey,
                                image_url: plotChar.image_url,
                                script_id: selectedScriptId ?? undefined,
                                prompt: prompt
                              });
                              toast.success(`Using image from ${selectedPlotCharName}`);
                            } catch (error) {
                              console.error('Failed to persist character image:', error);
                              toast.error('Image displayed but not saved. Please try again.');
                            }
                            return;
                          }

                          // If no image exists, generate one using their description
                          const description = `${plotChar.physical_description || ''}. ${plotChar.personality || ''}. ${plotChar.role || ''}`.trim();
                          if (description) {
                            generateCharacterImage(characterKey, description, generationOptions);
                            return;
                          }
                        }
                      }

                      // Fall back to current character details if no selection or description found
                      const description =
                        typeof character === "object" && character.physical_description && character.personality && character.role
                          ? `${character.physical_description}. ${character.personality}. ${character.role}`
                          : `Portrait of ${characterKey}, detailed character design`;

                      generateCharacterImage(characterKey, description, generationOptions);
                    }}
                    onRegenerate={() => {
                      if (characterImage?.id && !isFallbackImage) {
                        regenerateImage('character', characterKey, generationOptions);
                      } else {
                        // For fallback images or missing IDs, treat regenerate as generate new
                        const description =
                        typeof character === "object" && character.physical_description && character.personality && character.role
                          ? `${character.physical_description}. ${character.personality}. ${character.role}`
                          : `Portrait of ${characterKey}, detailed character design`;
                        generateCharacterImage(characterKey, description, generationOptions);
                      }
                    }}
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

      {/* Delete Confirmation Modal */}
      {showDeleteConfirmModal && (
        <ConfirmationModal
          isOpen={showDeleteConfirmModal}
          onClose={() => {
            setShowDeleteConfirmModal(false);
            setDeleteAction(null);
          }}
          onConfirm={handleConfirmDelete}
          title={
            deleteAction === 'selected'
              ? `Delete ${selectedSceneIds.size} Selected Image${selectedSceneIds.size !== 1 ? 's' : ''}`
              : 'Delete All Generated Scene Images'
          }
          message={
            deleteAction === 'selected'
              ? `Are you sure you want to delete ${selectedSceneIds.size} selected image${selectedSceneIds.size !== 1 ? 's' : ''}? This action cannot be undone.`
              : `Are you sure you want to delete all generated scene images for this script? This action cannot be undone.`
          }
          confirmText={deleteAction === 'selected' ? 'Delete Selected' : 'Delete All'}
          confirmButtonClass="bg-red-600 hover:bg-red-700"
        />
      )}

      {/* Scene Generation Modal */}
      <SceneGenerationModal 
        isOpen={showSceneGenerationModal}
        onClose={() => setShowSceneGenerationModal(false)}
        sceneNumber={selectedSceneForGeneration?.sceneNumber || 0}
        initialDescription={selectedSceneForGeneration?.description || ''}
        chapterTitle={chapterTitle}
        availableCharacters={characters.filter(c => c.image_url || c.imageUrl).map(c => ({
          name: c.name,
          imageUrl: c.image_url || c.imageUrl || '',
          id: c.id || c.name,
          prompt: '',
          generationStatus: 'completed'
        }))}
        onGenerate={handleModalGenerate}
        isGenerating={generatingScenes.has(selectedSceneForGeneration?.sceneNumber || -1)}
      />
    </div>
  );
};

// Scene Image Card Component
interface SceneImageCardProps {
  scene: any;
  sceneImages?: SceneImage[];
  isGenerating: boolean;
  selectedIds?: Set<string>;
  onSelect?: (selected: boolean, imageId: string) => void;
  onGenerate: () => void;
  onRegenerate: () => void;
  onDelete: (imageId: string) => void;
  onView: (imageUrl: string) => void;
}

const SceneImageCard: React.FC<SceneImageCardProps> = ({
  scene,
  sceneImages = [],
  isGenerating,
  selectedIds,
  onSelect,
  onGenerate,
  onRegenerate,
  onDelete,
  onView,
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);

  // Reset index if images change significantly (e.g. filtered out)
  useEffect(() => {
    if (currentIndex >= sceneImages.length && sceneImages.length > 0) {
      setCurrentIndex(0);
    }
  }, [sceneImages.length, currentIndex]);

  const currentImage = sceneImages[currentIndex];
  // If no images but generating, we might want to show a placeholder state or use the "generating" status from the parent
  // However, the hook now prepends a temporary image with 'generating' status, so currentImage should exist if generating.
  
  // Handlers for carousel navigation
  const handlePrev = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : sceneImages.length - 1));
  };

  const handleNext = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev < sceneImages.length - 1 ? prev + 1 : 0));
  };

  // Determine effective status for display
  const displayStatus = isGenerating ? 'generating' : currentImage?.generationStatus;
  
  // Calculate if the CURRENT image is selected
  // The parent passes `isSelected` which might be for the scene in general or specific image?
  // The parent logic for `isSelected` passed a boolean based on a specific image ID.
  // We need to change how `isSelected` is determined or genericized.
  // Actually, we should probably check selection state inside here or rely on parent passing "is CURRENT image selected".
  // For now, let's assume `isSelected` passed from parent matches the `currentImage.id`.

  return (
    <div className="bg-white border rounded-lg overflow-hidden group">
      <div className="aspect-video relative bg-gray-100">
        <ImageThumbnail
          imageUrl={currentImage?.imageUrl}
          isGenerating={isGenerating || displayStatus === 'generating'}
          status={displayStatus}
          alt={`Scene ${scene.scene_number} - Image ${currentIndex + 1}`}
          size="large"
        />

        <div className="absolute top-2 left-2 flex items-center space-x-2">
          <span className="px-2 py-1 bg-black bg-opacity-70 text-white text-xs rounded">
            Scene {scene.scene_number}
          </span>
          {sceneImages.length > 1 && (
             <span className="px-2 py-1 bg-black bg-opacity-50 text-white text-xs rounded">
               {currentIndex + 1} / {sceneImages.length}
             </span>
          )}
        </div>

        {/* Carousel Controls */}
        {sceneImages.length > 1 && (
            <>
                <button 
                    onClick={handlePrev}
                    className="absolute left-2 top-1/2 transform -translate-y-1/2 p-1 bg-black bg-opacity-30 hover:bg-opacity-70 text-white rounded-full transition-all opacity-0 group-hover:opacity-100"
                >
                    <div className="w-6 h-6 flex items-center justify-center">‹</div>
                </button>
                <button 
                    onClick={handleNext}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1 bg-black bg-opacity-30 hover:bg-opacity-70 text-white rounded-full transition-all opacity-0 group-hover:opacity-100"
                >
                     <div className="w-6 h-6 flex items-center justify-center">›</div>
                </button>
            </>
        )}

        {/* Selection Checkbox for CURRENT Image */}
        {currentImage?.id && (currentImage.generationStatus === 'completed' || currentImage.generationStatus === 'failed' || currentImage.imageUrl) && (
          <div className="absolute top-2 left-1/2 transform -translate-x-1/2">
            <input
              type="checkbox"
              checked={selectedIds?.has(currentImage.id) ?? false} 
              onChange={(e) => onSelect?.(e.target.checked, currentImage.id!)}
              className="w-4 h-4 text-blue-600 bg-white border-2 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer shadow-sm"
              aria-label={`Select scene ${scene.scene_number} image ${currentIndex + 1}`}
            />
          </div>
        )}

        <div className="absolute top-2 right-2">
          <ImageActions
            hasImage={!!currentImage?.imageUrl}
            isGenerating={isGenerating || displayStatus === 'generating'}
            onGenerate={onGenerate}
            onRegenerate={onRegenerate}
            onDelete={currentImage?.id ? () => onDelete(currentImage.id!) : undefined}
            onView={() => currentImage?.imageUrl && onView(currentImage.imageUrl)}
            compact
          />
        </div>
      </div>

      <div className="p-4">
        <h5 className="font-medium text-gray-900 mb-2 truncate" title={scene.location}>
          {scene.location}
        </h5>
        
        <p className="text-sm text-gray-600 line-clamp-3 mb-3 h-10">
          {currentImage?.prompt || scene.visual_description}
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
  fromPlotOverview?: boolean;
  plotCharacters?: Array<{ name: string; role?: string; physical_description?: string; personality?: string; image_url?: string }>;
  onGenerate: (selectedPlotCharName?: string) => void;
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
  fromPlotOverview = false,
  plotCharacters = [],
  onGenerate,
  onRegenerate,
  onDelete,
  onView
}) => {
  const [selectedPlotCharacter, setSelectedPlotCharacter] = useState<string>('');
  const [showSelector, setShowSelector] = useState(false);

  // Get selected plot character details
  const selectedPlotCharDetails = React.useMemo(() => {
    if (!selectedPlotCharacter) return null;
    return plotCharacters.find(c => c.name === selectedPlotCharacter);
  }, [selectedPlotCharacter, plotCharacters]);
  if (viewMode === 'list') {
    return (
      <div className="bg-white border rounded-lg p-4">
        <div className="flex items-center space-x-4">
          <div className="flex-shrink-0">
            <ImageThumbnail
              imageUrl={characterImage?.imageUrl}
              isGenerating={isGenerating}
              status={characterImage?.generationStatus}
              alt={characterName}
              size="small"
            />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h5 className="font-medium text-gray-900">{characterName}</h5>
              {fromPlotOverview && characterImage?.imageUrl && (
                <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded">
                  From Plot Overview
                </span>
              )}
            </div>
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
              onGenerate={() => onGenerate(selectedPlotCharacter)}
              onRegenerate={onRegenerate}
              onDelete={fromPlotOverview ? undefined : onDelete}
              onView={onView}
              selectedPlotCharHasImage={!!selectedPlotCharDetails?.image_url}
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
          status={characterImage?.generationStatus}
          alt={characterName}
          size="large"
        />

        {fromPlotOverview && characterImage?.imageUrl && (
          <div className="absolute top-2 left-2">
            <span className="px-2 py-1 bg-green-600 text-white text-xs rounded shadow-lg">
              From Plot Overview
            </span>
          </div>
        )}

        <div className="absolute top-2 right-2">
          <ImageActions
            hasImage={!!characterImage?.imageUrl}
            isGenerating={isGenerating}
            onGenerate={() => onGenerate(selectedPlotCharacter)}
            onRegenerate={onRegenerate}
            onDelete={fromPlotOverview ? undefined : onDelete}
            onView={onView}
            compact
            selectedPlotCharHasImage={!!selectedPlotCharDetails?.image_url}
          />
        </div>
      </div>

      <div className="p-4">
        <h5 className="font-medium text-gray-900 mb-1">{characterName}</h5>

        {/* Character Selector for matching with Plot Overview */}
        {plotCharacters && plotCharacters.length > 0 && !fromPlotOverview && (
          <div className="mb-2">
            <button
              onClick={() => setShowSelector(!showSelector)}
              className="text-xs text-blue-600 hover:text-blue-800 underline"
            >
              {showSelector ? 'Hide' : 'Match with Plot Character'}
            </button>

            {showSelector && (
              <div className="mt-2 p-2 bg-gray-50 rounded border border-gray-200">
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Select matching character from Plot Overview:
                </label>
                <select
                  value={selectedPlotCharacter}
                  onChange={(e) => setSelectedPlotCharacter(e.target.value)}
                  className="w-full text-xs border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">-- Select Character --</option>
                  {plotCharacters.map((char, idx) => (
                    <option key={idx} value={char.name}>
                      {char.name} {char.role ? `(${char.role})` : ''} {char.image_url ? '✓' : ''}
                    </option>
                  ))}
                </select>
                {selectedPlotCharDetails && (
                  <div className="mt-2 p-2 bg-white rounded border border-gray-200">
                    <div className="flex items-start space-x-2">
                      {selectedPlotCharDetails.image_url && (
                        <img
                          src={selectedPlotCharDetails.image_url}
                          alt={selectedPlotCharDetails.name}
                          className="w-12 h-12 object-cover rounded"
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-900">
                          {selectedPlotCharDetails.name}
                        </p>
                        {selectedPlotCharDetails.role && (
                          <p className="text-xs text-gray-600">
                            {selectedPlotCharDetails.role}
                          </p>
                        )}
                        {selectedPlotCharDetails.image_url ? (
                          <p className="text-xs text-green-600 mt-1">
                            ✓ Has existing image
                          </p>
                        ) : (
                          <p className="text-xs text-orange-600 mt-1">
                            No image - will generate new
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

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
  status?: string;
  alt: string;
  size: 'small' | 'large';
}

const ImageThumbnail: React.FC<ImageThumbnailProps> = ({ 
  imageUrl, 
  isGenerating, 
  status,
  alt, 
  size 
}) => {
  const sizeClasses = size === 'small' 
    ? 'w-16 h-16' 
    : 'w-full h-full';

  const isLoading = isGenerating || status === 'pending' || status === 'in_progress' || status === 'generating';

  if (isLoading) {
    return (
      <div className={`${sizeClasses} bg-gray-100 flex items-center justify-center rounded-md`}>
        <div className="text-center">
          <Loader2 className="w-6 h-6 animate-spin text-blue-500 mx-auto mb-2" />
          <span className="text-xs text-blue-600 font-medium">Generating...</span>
        </div>
      </div>
    );
  }


  if (status === 'failed') {
    return (
      <div className={`${sizeClasses} bg-red-50 flex items-center justify-center rounded-md border border-red-100`}>
        <div className="text-center px-2">
          <X className="w-6 h-6 text-red-400 mx-auto mb-1" />
          <span className="text-xs text-red-500 font-medium block">Generation Failed</span>
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
  onDelete?: () => void;
  onView: () => void;
  compact?: boolean;
  selectedPlotCharHasImage?: boolean;
}

const ImageActions: React.FC<ImageActionsProps> = ({
  hasImage,
  isGenerating,
  onGenerate,
  onRegenerate,
  onDelete,
  onView,
  compact = false,
  selectedPlotCharHasImage = false
}) => {
  if (compact) {
    return (
      <div className="flex space-x-1">
        {hasImage ? (
          <>
            <button
              onClick={onView}
              className="p-1 bg-black bg-opacity-50 text-white rounded hover:bg-opacity-70"
              title="View"
            >
              <Eye className="w-4 h-4" />
            </button>
            <button
              onClick={onRegenerate}
              disabled={isGenerating}
              className="p-1 bg-black bg-opacity-50 text-white rounded hover:bg-opacity-70 disabled:opacity-50"
              title="Regenerate"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </>
        ) : (
          <button
            onClick={onGenerate}
            disabled={isGenerating}
            className="p-1 bg-black bg-opacity-50 text-white rounded hover:bg-opacity-70 disabled:opacity-50"
            title={selectedPlotCharHasImage ? "Use existing image" : "Generate image"}
          >
            {selectedPlotCharHasImage ? (
              <Download className="w-4 h-4" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
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
          {onDelete && (
            <button
              onClick={onDelete}
              className="p-2 text-red-600 hover:bg-red-50 rounded"
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </>
      ) : (
        <button
          onClick={onGenerate}
          disabled={isGenerating}
          className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-blue-400"
        >
          {selectedPlotCharHasImage ? (
            <>
              <Download className="w-4 h-4" />
              <span>Use Image</span>
            </>
          ) : (
            <>
              <Plus className="w-4 h-4" />
              <span>Generate</span>
            </>
          )}
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
};// Confirmation Modal Component
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