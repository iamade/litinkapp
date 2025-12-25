import React, { useEffect, useState, useMemo } from "react";
import { BookOpen, Loader2, AlertCircle, Wand2, Users, Plus, Trash2, Search, X, Sparkles } from "lucide-react";
import { usePlotGeneration } from "../../hooks/usePlotGeneration";
import CharacterCard from "./CharacterCard";
import { userService } from "../../services/userService";
import { toast } from "react-hot-toast";

interface PlotOverviewPanelProps {
  bookId: string;
  /** Optional callback invoked after character create/delete to refresh plot overview in parent. */
  onCharacterChange?: () => void | Promise<void>;
  /** Set to true when this is a project (not a book) */
  isProject?: boolean;
  /** Input prompt for project-based plot generation */
  inputPrompt?: string;
  /** Project type for project-based plot generation */
  projectType?: string;
}

interface Character {
  id: string;
  name: string;
  role?: string;
  character_arc?: string;
  physical_description?: string;
  personality?: string;
  archetypes?: string[];
  want?: string;
  need?: string;
  lie?: string;
  ghost?: string;
  image_url?: string;
}

const PlotOverviewPanel: React.FC<PlotOverviewPanelProps> = ({
  bookId,
  onCharacterChange,
  isProject = false,
  inputPrompt,
  projectType
}) => {
  const { plotOverview, isGenerating, isLoading, generatePlot, loadPlot, deleteCharacter } =
    usePlotGeneration(bookId, { isProject, inputPrompt, projectType });

  const [deletingCharacterId, setDeletingCharacterId] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [characterToDelete, setCharacterToDelete] = useState<{ id: string; name: string } | null>(null);
  const [generatingImages, setGeneratingImages] = useState<Set<string>>(new Set());
  const [showImageModal, setShowImageModal] = useState<string | null>(null);
  const [showGenerateAllModal, setShowGenerateAllModal] = useState(false);

  // Bulk selection state
  const [selectedCharacters, setSelectedCharacters] = useState<Set<string>>(new Set());
  const [showBulkDeleteModal, setShowBulkDeleteModal] = useState(false);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);

  // Create character modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreatingCharacter, setIsCreatingCharacter] = useState(false);
  const [isGeneratingWithAI, setIsGeneratingWithAI] = useState(false);
  const [newCharacter, setNewCharacter] = useState({
    name: '',
    role: '',
    physical_description: '',
    personality: '',
    character_arc: '',
    want: '',
    need: '',
    lie: '',
    ghost: '',
  });

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  
  // Refinement prompt state
  const [refinementPrompt, setRefinementPrompt] = useState('');

  // Filter characters based on search query
  const filteredCharacters = useMemo(() => {
    if (!plotOverview?.characters) return [];

    if (!searchQuery.trim()) {
      return plotOverview.characters;
    }

    const query = searchQuery.toLowerCase().trim();
    return plotOverview.characters.filter((character: Character) => {
      return (
        character.name?.toLowerCase().includes(query) ||
        character.role?.toLowerCase().includes(query) ||
        character.physical_description?.toLowerCase().includes(query) ||
        character.personality?.toLowerCase().includes(query)
      );
    });
  }, [plotOverview?.characters, searchQuery]);

  useEffect(() => {
    loadPlot();
  }, [bookId, loadPlot]);

  const handleDeleteClick = (characterId: string, characterName: string) => {
    setCharacterToDelete({ id: characterId, name: characterName });
    setShowDeleteModal(true);
  };

  const handleConfirmDelete = async () => {
    if (!characterToDelete) return;

    setDeletingCharacterId(characterToDelete.id);
    try {
      await deleteCharacter(characterToDelete.id);

      // Invoke parent callback to refresh plot overview
      if (onCharacterChange) {
        try {
          await onCharacterChange();
        } catch (callbackError) {
          console.warn('onCharacterChange callback failed:', callbackError);
        }
      }

      setShowDeleteModal(false);
      setCharacterToDelete(null);
    } catch (error) {
      // Error is already handled in the hook
    } finally {
      setDeletingCharacterId(null);
    }
  };

  const handleUpdateCharacter = async (characterId: string, updates: Partial<Character>) => {
    try {
      await userService.updateCharacter(characterId, updates);

      // Check if physical description changed significantly
      const character = plotOverview?.characters.find((c: any) => c.id === characterId);
      if (character && updates.physical_description && updates.physical_description !== character.physical_description) {
        const shouldRegenerate = window.confirm(
          "Character description changed. Would you like to regenerate the character image?"
        );
        if (shouldRegenerate && character.image_url) {
          await handleRegenerateImage(characterId);
        }
      }

      // Reload plot to get updated data
      await loadPlot();
      toast.success("Character updated successfully");
    } catch (error) {
      toast.error("Failed to update character");
      throw error;
    }
  };

  const handleGenerateImage = async (characterId: string) => {
    setGeneratingImages(prev => new Set(prev).add(characterId));

    try {
      const result = await userService.generateCharacterImageGlobal(characterId);

      if (result.status === 'queued') {
        toast.success(`Image generation queued for ${result.estimated_time_seconds || 60}s`);

        // Start polling for status
        pollCharacterImageStatus(characterId);
      }
    } catch (error) {
      toast.error("Failed to queue character image generation");
      setGeneratingImages(prev => {
        const newSet = new Set(prev);
        newSet.delete(characterId);
        return newSet;
      });
    }
  };

  const pollCharacterImageStatus = async (characterId: string) => {
    const maxAttempts = 120; // 2 minutes with 1s intervals
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await userService.getCharacterImageStatus(characterId);

        if (status.status === 'completed' && status.image_url) {
          // Dismiss loading toast
          toast.dismiss(`gen-${characterId}`);

          setGeneratingImages(prev => {
            const newSet = new Set(prev);
            newSet.delete(characterId);
            return newSet;
          });
          await loadPlot();
          toast.success("Character image generated successfully");
          return;
        } else if (status.status === 'failed') {
          // Dismiss loading toast
          toast.dismiss(`gen-${characterId}`);

          setGeneratingImages(prev => {
            const newSet = new Set(prev);
            newSet.delete(characterId);
            return newSet;
          });
          toast.error(status.error || "Image generation failed");
          return;
        } else if (status.status === 'generating') {
          // Show progress update
          if (attempts % 10 === 0) {
            toast.loading("Generating character image...", { id: `gen-${characterId}` });
          }
        }

        // Continue polling if still pending or generating
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 1000);
        } else {
          // Dismiss loading toast
          toast.dismiss(`gen-${characterId}`);

          setGeneratingImages(prev => {
            const newSet = new Set(prev);
            newSet.delete(characterId);
            return newSet;
          });
          toast.error("Image generation timed out. Please check status later.");
        }
      } catch (error) {
        // Dismiss loading toast
        toast.dismiss(`gen-${characterId}`);

        setGeneratingImages(prev => {
          const newSet = new Set(prev);
          newSet.delete(characterId);
          return newSet;
        });
        toast.error("Failed to check image generation status");
      }
    };

    setTimeout(poll, 1000); // Start polling after 1 second
  };

  const handleRegenerateImage = async (characterId: string) => {
    await handleGenerateImage(characterId);
  };

  const handleGenerateAllImages = async () => {
    setShowGenerateAllModal(false);

    if (!plotOverview?.characters || plotOverview.characters.length === 0) {
      toast.error("No characters available to generate images");
      return;
    }

    const charactersWithoutImages = plotOverview.characters.filter(
      (char: Character) => !char.image_url
    );

    if (charactersWithoutImages.length === 0) {
      toast.error("All characters already have images");
      return;
    }

    toast.success(`Generating images for ${charactersWithoutImages.length} characters...`);

    // Generate images in parallel
    const promises = charactersWithoutImages.map((character: Character) =>
      handleGenerateImage(character.id)
    );

    try {
      await Promise.allSettled(promises);
      toast.success("Image generation completed");
    } catch (error) {
      toast.error("Some images failed to generate");
    }
  };

  // Bulk selection handlers
  const handleToggleSelect = (characterId: string) => {
    setSelectedCharacters(prev => {
      const newSet = new Set(prev);
      if (newSet.has(characterId)) {
        newSet.delete(characterId);
      } else {
        newSet.add(characterId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedCharacters.size === filteredCharacters.length) {
      setSelectedCharacters(new Set());
    } else {
      const allIds = filteredCharacters.map((c: Character) => c.id);
      setSelectedCharacters(new Set(allIds));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedCharacters.size === 0) return;

    setIsBulkDeleting(true);
    try {
      const ids = Array.from(selectedCharacters);
      await userService.bulkDeleteCharacters(ids);

      // Invoke parent callback to refresh plot overview
      if (onCharacterChange) {
        try {
          await onCharacterChange();
        } catch (callbackError) {
          console.warn('onCharacterChange callback failed:', callbackError);
        }
      }

      toast.success(`Deleted ${ids.length} character${ids.length > 1 ? 's' : ''}`);
      setSelectedCharacters(new Set());
      setShowBulkDeleteModal(false);

      // Reload plot data
      await loadPlot();
    } catch (error) {
      toast.error("Failed to delete characters");
    } finally {
      setIsBulkDeleting(false);
    }
  };

  // AI Assist handler
  const handleAIAssist = async () => {
    if (!newCharacter.name.trim()) {
      toast.error("Please enter a character name first");
      return;
    }

    if (!plotOverview?.book_id) {
      toast.error("Book information not available");
      return;
    }

    setIsGeneratingWithAI(true);
    const loadingToast = toast.loading("AI is analyzing the book to generate character details...");

    try {
      const response = await userService.generateCharacterDetailsWithAI(
        newCharacter.name,
        plotOverview.book_id,
        newCharacter.role || undefined
      );

      if (response.success && response.character_details) {
        setNewCharacter(prev => ({
          ...prev,
          physical_description: response.character_details.physical_description || prev.physical_description,
          personality: response.character_details.personality || prev.personality,
          character_arc: response.character_details.character_arc || prev.character_arc,
          want: response.character_details.want || prev.want,
          need: response.character_details.need || prev.need,
          lie: response.character_details.lie || prev.lie,
          ghost: response.character_details.ghost || prev.ghost,
        }));

        toast.success("Character details generated successfully! Review and edit as needed.", {
          id: loadingToast,
          duration: 4000
        });
      } else {
        throw new Error("Invalid response from AI service");
      }
    } catch (error: any) {
      console.error("AI generation error:", error);
      toast.error(error?.message || "Failed to generate character details with AI", {
        id: loadingToast
      });
    } finally {
      setIsGeneratingWithAI(false);
    }
  };

  // Create character handlers
  const handleCreateCharacter = async () => {
    if (!newCharacter.name.trim()) {
      toast.error("Character name is required");
      return;
    }

    if (!plotOverview?.id) {
      toast.error("Plot overview not found");
      return;
    }

    setIsCreatingCharacter(true);
    try {
      await userService.createCharacter(plotOverview.id, newCharacter);

      // Invoke parent callback to refresh plot overview
      if (onCharacterChange) {
        try {
          await onCharacterChange();
        } catch (callbackError) {
          console.warn('onCharacterChange callback failed:', callbackError);
        }
      }

      toast.success(`Character "${newCharacter.name}" created successfully`);
      setShowCreateModal(false);
      setNewCharacter({
        name: '',
        role: '',
        physical_description: '',
        personality: '',
        character_arc: '',
        want: '',
        need: '',
        lie: '',
        ghost: '',
      });

      // Reload plot data
      await loadPlot();
    } catch (error) {
      toast.error("Failed to create character");
    } finally {
      setIsCreatingCharacter(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          <span className="ml-2 text-gray-600">Loading plot overview...</span>
        </div>
      </div>
    );
  }

  if (!plotOverview) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Plot Overview</h3>
            <p className="text-gray-600 dark:text-gray-400">Generate comprehensive story analysis</p>
          </div>
          <button
            onClick={() => generatePlot()}
            disabled={isGenerating}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <BookOpen className="w-4 h-4" />
                <span>Generate Plot</span>
              </>
            )}
          </button>
        </div>

        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <BookOpen className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p>Generate a plot overview to see story analysis</p>
        </div>
      </div>
    );
  }

  const normalizedGenre = plotOverview.genre?.toLowerCase() || "";
  const charactersWithoutImages = plotOverview.characters?.filter((char: Character) => !char.image_url).length || 0;
  const hasCharacters = plotOverview.characters && plotOverview.characters.length > 0;

  return (
    <div className="space-y-8">
      {/* Header with Refinement */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Plot Overview</h3>
            <p className="text-gray-600 dark:text-gray-400">Story analysis and character management</p>
          </div>
          <button
            onClick={() => {
              generatePlot(refinementPrompt || undefined);
              if (refinementPrompt) setRefinementPrompt('');
            }}
            disabled={isGenerating}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-400 text-sm"
          >
            {isGenerating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <BookOpen className="w-4 h-4" />
            )}
            <span>{refinementPrompt ? 'Refine Plot' : 'Regenerate'}</span>
          </button>
        </div>
        
        {/* Refinement Prompt Input */}
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/30 dark:to-blue-900/30 border border-purple-200 dark:border-purple-700 rounded-lg p-4">
          <label className="block text-sm font-medium text-purple-900 dark:text-purple-300 mb-2">
            🎯 Customize Your Plot (Optional)
          </label>
          <textarea
            value={refinementPrompt}
            onChange={(e) => setRefinementPrompt(e.target.value)}
            placeholder="Describe changes you'd like, e.g., 'Make it Boondocks style animation' or 'Add more dramatic tension' or 'Change the protagonist to be older'"
            className="w-full border border-purple-300 dark:border-purple-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none text-sm placeholder-gray-500 dark:placeholder-gray-400"
            rows={2}
            disabled={isGenerating}
          />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Enter your customization prompt and click "{refinementPrompt ? 'Refine Plot' : 'Regenerate'}" to apply changes.
          </p>
        </div>
      </div>

      {/* Plot Overview Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-4">
          {/* Logline */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Logline</h4>
            <p className="text-gray-700 dark:text-gray-300">{plotOverview.logline}</p>
          </div>
          {/* Genre, Tone, Audience */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-3">Genre & Tone</h4>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-400 mb-1">
                  Genre
                </label>
                <p className="text-gray-700 dark:text-gray-300">{plotOverview.genre}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-400 mb-1">
                  Tone
                </label>
                <p className="text-gray-700 dark:text-gray-300">{plotOverview.tone}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-400 mb-1">
                  Audience
                </label>
                <p className="text-gray-700 dark:text-gray-300">{plotOverview.audience}</p>
              </div>
            </div>
          </div>
          {/* Setting */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Setting</h4>
            <p className="text-gray-700 dark:text-gray-300">{plotOverview.setting}</p>
          </div>
          {/* Script Story Type */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Script Story Type</h4>
            <p className="text-gray-700 dark:text-gray-300">{plotOverview.script_story_type}</p>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-4">
          {/* Themes */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Themes</h4>
            <div className="flex flex-wrap gap-2">
              {plotOverview.themes.map((theme, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1 bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300 rounded-full text-sm"
                >
                  {theme}
                </span>
              ))}
            </div>
          </div>

          {/* Story Type */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Story Type</h4>
            <p className="text-gray-700 dark:text-gray-300">{plotOverview.story_type}</p>
          </div>
        </div>
      </div>

      {/* Characters Section */}
      <div className="space-y-4">
        {/* Characters Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Users className="w-6 h-6 text-gray-700 dark:text-gray-300" />
            <div>
              <h4 className="text-lg font-semibold text-gray-900 dark:text-white">Characters</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {hasCharacters ? `${plotOverview.characters.length} character${plotOverview.characters.length !== 1 ? 's' : ''}` : 'No characters yet'}
                {hasCharacters && charactersWithoutImages > 0 && ` • ${charactersWithoutImages} without images`}
                {selectedCharacters.size > 0 && ` • ${selectedCharacters.size} selected`}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {selectedCharacters.size > 0 && (
              <button
                onClick={() => setShowBulkDeleteModal(true)}
                className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm"
              >
                <Trash2 className="w-4 h-4" />
                <span>Delete Selected ({selectedCharacters.size})</span>
              </button>
            )}
            {hasCharacters && (
              <button
                onClick={handleSelectAll}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 text-sm"
              >
                {selectedCharacters.size === filteredCharacters.length && filteredCharacters.length > 0 ? 'Deselect All' : 'Select All'}
              </button>
            )}
            {hasCharacters && charactersWithoutImages > 0 && (
              <button
                onClick={() => setShowGenerateAllModal(true)}
                disabled={generatingImages.size > 0}
                className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 text-sm"
              >
                <Wand2 className="w-4 h-4" />
                <span>Generate All Images</span>
              </button>
            )}
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Create Character</span>
            </button>
          </div>
        </div>

        {/* Search Bar */}
        {hasCharacters && (
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-400 dark:text-gray-500" />
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search characters by name, role, description..."
              className="block w-full pl-10 pr-10 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 placeholder-gray-500 dark:placeholder-gray-400"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
              >
                <X className="h-5 w-5 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300" />
              </button>
            )}
          </div>
        )}

        {/* Search Results Info */}
        {hasCharacters && searchQuery && (
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Found {filteredCharacters.length} character{filteredCharacters.length !== 1 ? 's' : ''} matching "{searchQuery}"
          </div>
        )}

        {/* Characters Grid */}
        {hasCharacters ? (
          filteredCharacters.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredCharacters.map((character: Character) => (
              <CharacterCard
                key={character.id}
                character={character}
                isGeneratingImage={generatingImages.has(character.id)}
                isSelected={selectedCharacters.has(character.id)}
                onToggleSelect={handleToggleSelect}
                onUpdate={handleUpdateCharacter}
                onDelete={handleDeleteClick}
                onGenerateImage={handleGenerateImage}
                onRegenerateImage={handleRegenerateImage}
                onViewImage={(url) => setShowImageModal(url)}
              />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600">
              <Search className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500 mb-4" />
              <p className="text-gray-600 dark:text-gray-400 mb-2">No characters found matching "{searchQuery}"</p>
              <button
                onClick={() => setSearchQuery('')}
                className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 text-sm font-medium"
              >
                Clear search
              </button>
            </div>
          )
        ) : (
          <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600">
            <Users className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500 mb-4" />
            <p className="text-gray-600 dark:text-gray-400 mb-4">No characters yet</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              <span>Create Your First Character</span>
            </button>
          </div>
        )}
      </div>

      {/* Create Character Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-gray-900">Create New Character</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                disabled={isCreatingCharacter}
                className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Character Name *
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newCharacter.name}
                    onChange={(e) => setNewCharacter(prev => ({ ...prev, name: e.target.value }))}
                    className="flex-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter character name"
                    disabled={isCreatingCharacter || isGeneratingWithAI}
                  />
                  <button
                    onClick={handleAIAssist}
                    disabled={isCreatingCharacter || isGeneratingWithAI || !newCharacter.name.trim()}
                    className="px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-md hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium transition-all"
                    title="Use AI to generate character details based on the book"
                  >
                    {isGeneratingWithAI ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="hidden sm:inline">AI Generating...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        <span className="hidden sm:inline">AI Assist</span>
                      </>
                    )}
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Enter a character name, then click AI Assist to generate details from the book
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Role
                </label>
                <select
                  value={newCharacter.role}
                  onChange={(e) => setNewCharacter(prev => ({ ...prev, role: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isCreatingCharacter || isGeneratingWithAI}
                >
                  <option value="">Select role</option>
                  <option value="protagonist">Protagonist</option>
                  <option value="antagonist">Antagonist</option>
                  <option value="supporting">Supporting</option>
                  <option value="mentor">Mentor</option>
                  <option value="sidekick">Sidekick</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Physical Description
                </label>
                <textarea
                  value={newCharacter.physical_description}
                  onChange={(e) => setNewCharacter(prev => ({ ...prev, physical_description: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="Describe the character's appearance"
                  disabled={isCreatingCharacter || isGeneratingWithAI}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Personality
                </label>
                <textarea
                  value={newCharacter.personality}
                  onChange={(e) => setNewCharacter(prev => ({ ...prev, personality: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="Describe the character's personality traits"
                  disabled={isCreatingCharacter || isGeneratingWithAI}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Character Arc
                </label>
                <textarea
                  value={newCharacter.character_arc}
                  onChange={(e) => setNewCharacter(prev => ({ ...prev, character_arc: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={2}
                  placeholder="How does this character change throughout the story?"
                  disabled={isCreatingCharacter || isGeneratingWithAI}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Want
                  </label>
                  <input
                    type="text"
                    value={newCharacter.want}
                    onChange={(e) => setNewCharacter(prev => ({ ...prev, want: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="What they want"
                    disabled={isCreatingCharacter || isGeneratingWithAI}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Need
                  </label>
                  <input
                    type="text"
                    value={newCharacter.need}
                    onChange={(e) => setNewCharacter(prev => ({ ...prev, need: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="What they need"
                    disabled={isCreatingCharacter || isGeneratingWithAI}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Lie They Believe
                  </label>
                  <input
                    type="text"
                    value={newCharacter.lie}
                    onChange={(e) => setNewCharacter(prev => ({ ...prev, lie: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Their false belief"
                    disabled={isCreatingCharacter || isGeneratingWithAI}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ghost (Past Trauma)
                  </label>
                  <input
                    type="text"
                    value={newCharacter.ghost}
                    onChange={(e) => setNewCharacter(prev => ({ ...prev, ghost: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Their past trauma"
                    disabled={isCreatingCharacter || isGeneratingWithAI}
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                disabled={isCreatingCharacter || isGeneratingWithAI}
                className="flex-1 px-4 py-3 bg-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-300 transition-all disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateCharacter}
                disabled={isCreatingCharacter || isGeneratingWithAI || !newCharacter.name.trim()}
                className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-all disabled:opacity-50"
              >
                {isCreatingCharacter ? (
                  <span className="flex items-center justify-center">
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    Creating...
                  </span>
                ) : (
                  'Create Character'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Delete Confirmation Modal */}
      {showBulkDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900">Delete Multiple Characters?</h3>
            </div>

            <p className="text-gray-600 mb-6">
              Are you sure you want to delete <strong>{selectedCharacters.size} character{selectedCharacters.size > 1 ? 's' : ''}</strong>? This action cannot be undone.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setShowBulkDeleteModal(false)}
                disabled={isBulkDeleting}
                className="flex-1 px-4 py-3 bg-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-300 transition-all disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleBulkDelete}
                disabled={isBulkDeleting}
                className="flex-1 px-4 py-3 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 transition-all disabled:opacity-50"
              >
                {isBulkDeleting ? "Deleting..." : `Yes, Delete ${selectedCharacters.size}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Image Viewer Modal */}
      {showImageModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4">
          <div className="bg-white rounded-lg max-w-4xl max-h-[90vh] w-full overflow-auto">
            <div className="flex justify-between items-center p-4 border-b">
              <h3 className="text-lg font-semibold">Character Image</h3>
              <button
                onClick={() => setShowImageModal(null)}
                className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
              >
                ×
              </button>
            </div>
            <div className="p-4 flex justify-center">
              <img
                src={showImageModal}
                alt="Character"
                className="max-w-full max-h-[70vh] object-contain rounded"
              />
            </div>
          </div>
        </div>
      )}

      {/* Generate All Images Confirmation Modal */}
      {showGenerateAllModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <Wand2 className="w-6 h-6 text-green-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900">Generate All Character Images</h3>
            </div>

            <p className="text-gray-600 mb-6">
              Generate images for all <strong>{charactersWithoutImages} character{charactersWithoutImages !== 1 ? 's' : ''}</strong> without images? This may take several minutes.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setShowGenerateAllModal(false)}
                className="flex-1 px-4 py-3 bg-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-300 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerateAllImages}
                className="flex-1 px-4 py-3 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 transition-all"
              >
                Generate All
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && characterToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900">Delete Character?</h3>
            </div>

            <p className="text-gray-600 mb-6">
              Are you sure you want to delete <strong>{characterToDelete.name}</strong>? This will permanently remove the character from the plot overview. This action cannot be undone.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setCharacterToDelete(null);
                }}
                disabled={deletingCharacterId !== null}
                className="flex-1 px-4 py-3 bg-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-300 transition-all disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                disabled={deletingCharacterId !== null}
                className="flex-1 px-4 py-3 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 transition-all disabled:opacity-50"
              >
                {deletingCharacterId ? "Deleting..." : "Yes, Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlotOverviewPanel;
