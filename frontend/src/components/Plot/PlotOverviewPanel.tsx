import React, { useEffect, useState, useMemo } from "react";
import { BookOpen, Loader2, AlertCircle, Wand2, Users, Plus, Trash2, Search, X, Sparkles, ChevronDown, ChevronRight } from "lucide-react";
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
  /** User mode: 'explorer' or 'creator'. Customize plot section only shows for creator mode */
  mode?: 'explorer' | 'creator';
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
  entity_type?: 'character' | 'object' | 'location';
  images?: Array<{
    id: string;
    image_url: string;
    created_at: string;
    status: string;
  }>;
}

const PlotOverviewPanel: React.FC<PlotOverviewPanelProps> = ({
  bookId,
  onCharacterChange,
  isProject = false,
  inputPrompt,
  projectType,
  mode = 'creator'
}) => {
  const { plotOverview, isGenerating, isLoading, isUpdating, generatePlot, loadPlot, deleteCharacter, updatePlot } =
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

  // Bulk selection state (Objects & Locations)
  const [selectedObjects, setSelectedObjects] = useState<Set<string>>(new Set());
  const [showBulkDeleteObjectsModal, setShowBulkDeleteObjectsModal] = useState(false);
  const [isBulkDeletingObjects, setIsBulkDeletingObjects] = useState(false);

  // Regenerate image confirmation modal state
  const [showRegenerateModal, setShowRegenerateModal] = useState(false);
  const [pendingRegenerateCharacterId, setPendingRegenerateCharacterId] = useState<string | null>(null);

  // Create character modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreatingCharacter, setIsCreatingCharacter] = useState(false);
  const [isGeneratingWithAI, setIsGeneratingWithAI] = useState(false);
  const [isAutoAddingCharacters, setIsAutoAddingCharacters] = useState(false);
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
    entity_type: 'character' as 'character' | 'object' | 'location',
  });

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  
  // Refinement prompt state
  const [refinementPrompt, setRefinementPrompt] = useState('');
  
  // Editing state for click-to-edit fields
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  
  // AI Reimagine section collapsed state
  const [isAiReimaginExpanded, setIsAiReimaginExpanded] = useState(false);
  
  // Section collapsed states
  const [isCharactersExpanded, setIsCharactersExpanded] = useState(true);
  const [isObjectsExpanded, setIsObjectsExpanded] = useState(true);
  
  // Inline EditableField component for click-to-edit
  const EditableField: React.FC<{
    fieldKey: string;
    value: string | undefined;
    label: string;
    isTextarea?: boolean;
    options?: string[];
  }> = ({ fieldKey, value, isTextarea = false, options }) => {
    const isEditing = editingField === fieldKey;
    const isCreatorMode = mode === 'creator';
    
    const handleStartEdit = () => {
      if (!isCreatorMode) return;
      setEditingField(fieldKey);
      setEditValue(value || '');
    };
    
    const handleSave = async () => {
      if (editValue !== value) {
        await updatePlot({ [fieldKey]: editValue });
      }
      setEditingField(null);
      setEditValue('');
    };
    
    const handleCancel = () => {
      setEditingField(null);
      setEditValue('');
    };
    
    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !isTextarea) {
        e.preventDefault();
        handleSave();
      } else if (e.key === 'Escape') {
        handleCancel();
      }
    };
    
    if (isEditing) {
      return (
        <div className="space-y-2">
          {options ? (
            // Combo box: input with datalist for suggestions
            <div className="relative">
              <input
                type="text"
                list={`${fieldKey}-options`}
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type or select..."
                className="w-full border border-blue-400 dark:border-blue-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                autoFocus
              />
              <datalist id={`${fieldKey}-options`}>
                {options.map((opt) => (
                  <option key={opt} value={opt} />
                ))}
              </datalist>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Select from suggestions or type custom value
              </p>
            </div>
          ) : isTextarea ? (
            <textarea
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full border border-blue-400 dark:border-blue-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 resize-none"
              rows={3}
              autoFocus
            />
          ) : (
            <input
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full border border-blue-400 dark:border-blue-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
          )}
          <div className="flex gap-2 justify-end">
            <button
              onClick={handleCancel}
              className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isUpdating}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-blue-400"
            >
              {isUpdating ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      );
    }
    
    return (
      <p
        onClick={handleStartEdit}
        className={`text-gray-700 dark:text-gray-300 ${isCreatorMode ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 rounded px-1 -mx-1 transition-colors' : ''}`}
        title={isCreatorMode ? 'Click to edit' : undefined}
      >
        {value || <span className="text-gray-400 italic">Not set</span>}
      </p>
    );
  };

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
      if (character && updates.physical_description && updates.physical_description !== character.physical_description && character.image_url) {
        // Show regenerate modal instead of window.confirm
        setPendingRegenerateCharacterId(characterId);
        setShowRegenerateModal(true);
      }

      // Reload plot to get updated data
      await loadPlot();
      toast.success("Character updated successfully");
    } catch (error) {
      toast.error("Failed to update character");
      throw error;
    }
  };

  const handleConfirmRegenerate = async () => {
    if (pendingRegenerateCharacterId) {
      await handleRegenerateImage(pendingRegenerateCharacterId);
    }
    setShowRegenerateModal(false);
    setPendingRegenerateCharacterId(null);
  };

  const handleCancelRegenerate = () => {
    setShowRegenerateModal(false);
    setPendingRegenerateCharacterId(null);
  };

  const handleDeleteCharacterImage = async (characterId: string, imageId: string) => {
    try {
      await userService.deleteCharacterHistoryImage(characterId, imageId);
      toast.success("Image deleted");
      // Reload to update history
      await loadPlot();
    } catch (error) {
      console.error("Failed to delete character image:", error);
      toast.error("Failed to delete image");
    }
  };

  const handleSetDefaultImage = async (characterId: string, imageUrl: string) => {
    try {
      await userService.setDefaultCharacterImage(characterId, imageUrl);
      toast.success("Default image updated");
      // Reload to update UI
      await loadPlot();
    } catch (error) {
       console.error("Failed to set default character image:", error);
       toast.error("Failed to set default image");
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
    } catch (error: any) {
      // Extract the actual error message from the API response
      const errorMessage = error?.message || "Failed to queue character image generation";
      toast.error(errorMessage);
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
          
          // Notify parent to refresh other components (Script tab, Images tab, etc.)
          if (onCharacterChange) {
            try {
              await onCharacterChange();
            } catch (callbackError) {
              console.warn('onCharacterChange callback failed:', callbackError);
            }
          }
          
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

  // Generate images for selected characters
  const handleGenerateSelectedImages = async () => {
    if (selectedCharacters.size === 0) return;

    const selectedIds = Array.from(selectedCharacters);
    const charactersToGenerate = plotOverview?.characters?.filter(
      (char: Character) => selectedIds.includes(char.id) && !char.image_url
    ) || [];

    if (charactersToGenerate.length === 0) {
      toast.error("All selected characters already have images");
      return;
    }

    toast.success(`Generating images for ${charactersToGenerate.length} selected character${charactersToGenerate.length !== 1 ? 's' : ''}...`);

    // Generate images in parallel
    const promises = charactersToGenerate.map((character: Character) =>
      handleGenerateImage(character.id)
    );

    try {
      await Promise.allSettled(promises);
      toast.success("Image generation completed for selected characters");
      setSelectedCharacters(new Set()); // Clear selection after generation
    } catch (error) {
      toast.error("Some images failed to generate");
    }
  };



  // Object Bulk Action Handlers
  const handleToggleSelectObject = (characterId: string) => {
    const newSelected = new Set(selectedObjects);
    if (newSelected.has(characterId)) {
      newSelected.delete(characterId);
    } else {
      newSelected.add(characterId);
    }
    setSelectedObjects(newSelected);
  };

  const handleSelectAllObjects = () => {
    // Filter objects/locations from displayed list
    const objectChars = filteredCharacters.filter((c: Character) => c.entity_type === 'object' || c.entity_type === 'location');
    
    // Check if all displayed objects are currently selected
    const allSelected = objectChars.every((c: Character) => selectedObjects.has(c.id));
    
    if (allSelected && objectChars.length > 0) {
      // Deselect all displayed objects
      const newSelected = new Set(selectedObjects);
      objectChars.forEach((c: Character) => newSelected.delete(c.id));
      setSelectedObjects(newSelected);
    } else {
      // Select all displayed objects
      const newSelected = new Set(selectedObjects);
      objectChars.forEach((c: Character) => newSelected.add(c.id));
      setSelectedObjects(newSelected);
    }
  };

  const handleBulkDeleteObjects = async () => {
    setIsBulkDeletingObjects(true);
    try {
      await userService.bulkDeleteCharacters(Array.from(selectedObjects));
      
      if (onCharacterChange) {
         await onCharacterChange();
      }
      
      setSelectedObjects(new Set());
      setShowBulkDeleteObjectsModal(false);
      await loadPlot();
      toast.success("Selected items deleted successfully");
    } catch (error) {
      console.error("Bulk delete failed:", error);
      toast.error("Failed to delete selected items");
    } finally {
      setIsBulkDeletingObjects(false);
    }
  };

  const handleGenerateSelectedObjectImages = async () => {
    const idsToGenerate = Array.from(selectedObjects);
    if (idsToGenerate.length === 0) return;

    idsToGenerate.forEach(id => {
      setGeneratingImages(prev => new Set(prev).add(id));
    });

    try {
      const promises = idsToGenerate.map(id => handleGenerateImage(id));
      await Promise.allSettled(promises);
      toast.success(`Started generation for ${idsToGenerate.length} items`);
    } catch (error) {
      toast.error("Some generations failed to start");
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
      // Ensure entity_type is set correctly based on what we are creating
      const characterData = {
        ...newCharacter,
        entity_type: newCharacter.entity_type || 'character' 
      };
      
      await userService.createCharacter(plotOverview.id, characterData);

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
        entity_type: 'character',
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
  const normalizedStoryType = plotOverview.story_type?.toLowerCase().replace(/'/g, "") || "";

  // Filter out "Uploaded from..." pattern from prompts - this is not a real user prompt
  const cleanPrompt = (prompt: string | null | undefined): string | null => {
    if (!prompt) return null;
    // Check if it matches the "Uploaded from..." pattern
    if (prompt.startsWith("Uploaded from ") || prompt.startsWith("Book uploaded from ")) {
      return null;
    }
    return prompt;
  };

  const userPrompt = cleanPrompt(plotOverview.original_prompt) || cleanPrompt(inputPrompt);

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
        
        {/* AI Reimagine Section - Collapsible, creator mode only */}
        {mode === 'creator' && (
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <button
              onClick={() => setIsAiReimaginExpanded(!isAiReimaginExpanded)}
              className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                ✨ AI Reimagine (optional) - Regenerate with creative direction
              </span>
              {isAiReimaginExpanded ? (
                <ChevronDown className="w-4 h-4 text-gray-500" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-500" />
              )}
            </button>
            {isAiReimaginExpanded && (
              <div className="p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border-t border-gray-200 dark:border-gray-700">
                <textarea
                  value={refinementPrompt}
                  onChange={(e) => setRefinementPrompt(e.target.value)}
                  placeholder="Describe changes you'd like, e.g., 'Make it Boondocks style animation' or 'Add more dramatic tension'"
                  className="w-full border border-purple-300 dark:border-purple-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none text-sm placeholder-gray-500 dark:placeholder-gray-400"
                  rows={2}
                  disabled={isGenerating}
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  💡 Use this for broad creative changes. AI will regenerate all plot fields based on your prompt.
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Plot Overview Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-4">
          {/* Original User Prompt - Show if exists or allow input */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Original User Prompt</h4>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
              Your creative input for this project
            </p>
            {!userPrompt ? (
              <div className="text-sm text-gray-500 dark:text-gray-400 italic bg-gray-50 dark:bg-gray-900/50 p-3 rounded">
                No user prompt provided. Use "✨ AI Reimagine" below to add creative direction.
              </div>
            ) : (
              <EditableField 
                fieldKey="original_prompt" 
                value={userPrompt} 
                label="Original Prompt" 
                isTextarea 
              />
            )}
          </div>
          {/* Logline */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Logline</h4>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
              AI-generated story summary
            </p>
            <EditableField fieldKey="logline" value={plotOverview.logline} label="Logline" isTextarea />
          </div>
          {/* Creative Directive */}
          <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border-2 border-blue-200 dark:border-blue-700">
            <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">Creative Directive</h4>
            <p className="text-xs text-blue-600 dark:text-blue-400 mb-2">
              Combined direction used for AI generation (script, characters, images, audio)
            </p>
            <EditableField 
              fieldKey="creative_directive" 
              value={(plotOverview as any).creative_directive || plotOverview.logline || plotOverview.original_prompt || ""} 
              label="Creative Directive" 
              isTextarea 
            />
          </div>
          {/* Genre, Tone, Audience */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-3">Genre & Tone</h4>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-400 mb-1">
                  Genre
                </label>
                <EditableField fieldKey="genre" value={plotOverview.genre} label="Genre" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-400 mb-1">
                  Tone
                </label>
                <EditableField fieldKey="tone" value={plotOverview.tone} label="Tone" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-400 mb-1">
                  Audience
                </label>
                <EditableField fieldKey="audience" value={plotOverview.audience} label="Audience" />
              </div>
            </div>
          </div>
          {/* Setting */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Setting</h4>
            <EditableField fieldKey="setting" value={plotOverview.setting} label="Setting" isTextarea />
          </div>
          {/* Script Story Type */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Script Story Type</h4>
            <EditableField 
              fieldKey="script_story_type" 
              value={plotOverview.script_story_type} 
              label="Script Story Type"
              options={['fiction', 'non-fiction', 'documentary', 'hybrid']}
            />
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
            <EditableField fieldKey="story_type" value={plotOverview.story_type} label="Story Type" />
          </div>
          
          {/* Medium - NEW */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Medium</h4>
            <EditableField 
              fieldKey="medium" 
              value={(plotOverview as any).medium} 
              label="Medium"
              options={['Animation', 'Live Action', 'Hybrid / Mixed Media', 'Puppetry / Animatronics', 'Stop-Motion']}
            />
          </div>
          
          {/* Format - NEW */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Format</h4>
            <EditableField 
              fieldKey="format" 
              value={(plotOverview as any).format} 
              label="Format"
              options={['Film', 'TV Series', 'Limited Series / Miniseries', 'Anthology Series', 'Short Film', 'Special', 'Featurette']}
            />
          </div>
          
          {/* Vibe/Style - NEW */}
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Vibe / Style</h4>
            <EditableField 
              fieldKey="vibe_style" 
              value={(plotOverview as any).vibe_style} 
              label="Vibe/Style"
              options={[
                'Satire / Social Commentary',
                'Cinematic / Fantasy',
                'Sitcom / Comedy',
                'Sitcom / Rom-Com',
                'Cinematic / Crime Thriller',
                'Cinematic / Superhero',
                'Anthology / Sci-Fi',
                'Cinematic / Horror',
                'Cinematic / Crime Drama',
                'Documentary Style',
                'Action / Adventure',
                'Family / Animated',
                'Dramedy',
                'Dark Comedy',
                'Psychological Thriller',
                'Coming-of-Age'
              ]}
            />
          </div>
        </div>
      </div>

      {/* Characters Section */}
      <div className="space-y-4">
        {/* Characters Header */}
        <div
          className="flex items-center justify-between w-full group"
        >
          <div 
            onClick={() => setIsCharactersExpanded(!isCharactersExpanded)}
            className="flex items-center space-x-3 cursor-pointer"
          >
             <div className="flex items-center gap-2">
                {isCharactersExpanded ? <ChevronDown className="w-5 h-5 text-gray-500" /> : <ChevronRight className="w-5 h-5 text-gray-500" />}
                <Users className="w-6 h-6 text-gray-700 dark:text-gray-300" />
             </div>
            <div className="text-left">
              <h4 className="text-lg font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">Characters</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 font-normal">
                {hasCharacters ? `${plotOverview.characters.length} character${plotOverview.characters.length !== 1 ? 's' : ''}` : 'No characters yet'}
                {hasCharacters && charactersWithoutImages > 0 && ` • ${charactersWithoutImages} without images`}
                {selectedCharacters.size > 0 && ` • ${selectedCharacters.size} selected`}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {selectedCharacters.size > 0 && (
              <>
                <button
                  onClick={handleGenerateSelectedImages}
                  disabled={generatingImages.size > 0}
                  className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 text-sm"
                >
                  <Wand2 className="w-4 h-4" />
                  <span>Generate Selected ({selectedCharacters.size})</span>
                </button>
                <button
                  onClick={() => setShowBulkDeleteModal(true)}
                  className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Delete Selected ({selectedCharacters.size})</span>
                </button>
              </>
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
              onClick={() => {
                setNewCharacter(prev => ({ ...prev, entity_type: 'character', name: searchQuery || '' }));
                setShowCreateModal(true);
              }}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Create Character</span>
            </button>
            <button
              onClick={async () => {
                if (isAutoAddingCharacters) return;
                setIsAutoAddingCharacters(true);
                const loadingToast = toast.loading(isProject 
                  ? 'AI is generating more characters...' 
                  : 'AI is finding more characters from the book...');
                try {
                  // Call correct endpoint based on whether it's a project or book
                  const result = isProject 
                    ? await userService.autoAddProjectCharacters(bookId)
                    : await userService.autoAddCharacters(bookId);
                  if (result.characters_added > 0) {
                    toast.success(result.message, { id: loadingToast });
                    // Reload plot to show new characters
                    await loadPlot();
                    if (onCharacterChange) {
                      await onCharacterChange();
                    }
                  } else {
                    toast.success(result.message, { id: loadingToast });
                  }
                } catch (error: any) {
                  toast.error(error?.message || 'Failed to add characters', { id: loadingToast });
                } finally {
                  setIsAutoAddingCharacters(false);
                }
              }}
              disabled={isAutoAddingCharacters || !plotOverview?.id}
              className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-purple-400 text-sm"
            >
              {isAutoAddingCharacters ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Adding...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Auto Add Characters</span>
                </>
              )}
            </button>
          </div>
        </div>

        {isCharactersExpanded && (
          <>

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
                type="button" 
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
              {filteredCharacters
                .filter((character: Character) => character.entity_type !== 'object')
                .map((character: Character) => (
                <CharacterCard
                  key={character.id}
                  character={character}
                  isGeneratingImage={generatingImages.has(character.id)}
                  isSelected={selectedCharacters.has(character.id)}
                  bookId={plotOverview?.book_id}
                  onToggleSelect={handleToggleSelect}
                  onUpdate={handleUpdateCharacter}
                  onDelete={handleDeleteClick}
                  onGenerateImage={handleGenerateImage}
                  onRegenerateImage={handleRegenerateImage}
                  onViewImage={(url) => setShowImageModal(url)}
                  onDeleteImage={handleDeleteCharacterImage}
                  onSetDefaultImage={handleSetDefaultImage}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600">
              <Search className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500 mb-4" />
              <p className="text-gray-600 dark:text-gray-400 mb-2">No characters found matching "{searchQuery}"</p>
              
               <div className="flex flex-col items-center gap-3 mt-4">
                 <button
                    onClick={() => {
                        setNewCharacter(prev => ({ ...prev, entity_type: 'character', name: searchQuery || '' }));
                        setShowCreateModal(true);
                    }}
                    className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Create "{searchQuery}" as Character</span>
                  </button>
                  <div className="flex gap-3">
                     <button
                      onClick={() => {
                           setNewCharacter(prev => ({ ...prev, entity_type: 'object', name: searchQuery || '' }));
                           setShowCreateModal(true);
                      }}
                      className="inline-flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm"
                    >
                      <Plus className="w-4 h-4" />
                      <span>Create as Object</span>
                    </button>
                    <button
                      onClick={() => {
                           setNewCharacter(prev => ({ ...prev, entity_type: 'location', name: searchQuery || '' }));
                           setShowCreateModal(true);
                      }}
                      className="inline-flex items-center space-x-2 px-4 py-2 bg-amber-600 text-white rounded-md hover:bg-amber-700 text-sm"
                    >
                      <Plus className="w-4 h-4" />
                      <span>Create as Location</span>
                    </button>
                  </div>
               </div>

              <button
                onClick={() => setSearchQuery('')}
                className="mt-6 text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 text-sm font-medium"
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
              onClick={() => {
                   setNewCharacter(prev => ({ ...prev, entity_type: 'character', name: searchQuery || '' }));
                   setShowCreateModal(true);
              }}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              <span>Create Your First Character</span>
            </button>
            {searchQuery && (
              <div className="flex gap-2 mt-4 justify-center">
                 <button
                  onClick={() => {
                       setNewCharacter(prev => ({ ...prev, entity_type: 'object', name: searchQuery || '' }));
                       setShowCreateModal(true);
                  }}
                  className="inline-flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm"
                >
                  <Plus className="w-4 h-4" />
                  <span>Create "{searchQuery}" as Object</span>
                </button>
                <button
                  onClick={() => {
                       setNewCharacter(prev => ({ ...prev, entity_type: 'location', name: searchQuery || '' }));
                       setShowCreateModal(true);
                  }}
                  className="inline-flex items-center space-x-2 px-4 py-2 bg-amber-600 text-white rounded-md hover:bg-amber-700 text-sm"
                >
                  <Plus className="w-4 h-4" />
                  <span>Create "{searchQuery}" as Location</span>
                </button>
              </div>
            )}
          </div>
        )}
        </>
      )}
      </div>

       {/* Objects & Locations Section */}
       {(filteredCharacters.some((c: Character) => c.entity_type === 'object') || mode === 'creator') && (
        <div className="space-y-4 pt-8 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
               <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                  <BookOpen className="w-5 h-5 text-purple-600 dark:text-purple-400" />
               </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Objects & Locations</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {filteredCharacters.filter((c: Character) => c.entity_type === 'object' || c.entity_type === 'location').length} items
                  {selectedObjects.size > 0 && ` • ${selectedObjects.size} selected`}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {selectedObjects.size > 0 && (
                <>
                  <button
                    onClick={handleGenerateSelectedObjectImages}
                    disabled={generatingImages.size > 0}
                    className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 text-sm"
                  >
                    <Wand2 className="w-4 h-4" />
                    <span>Generate Selected ({selectedObjects.size})</span>
                  </button>
                  <button
                    onClick={() => setShowBulkDeleteObjectsModal(true)}
                    className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm"
                  >
                    <Trash2 className="w-4 h-4" />
                    <span>Delete Selected ({selectedObjects.size})</span>
                  </button>
                </>
              )}
              
              {filteredCharacters.filter((c: Character) => c.entity_type === 'object' || c.entity_type === 'location').length > 0 && (
                <button
                  onClick={handleSelectAllObjects}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 text-sm"
                >
                  {selectedObjects.size === filteredCharacters.filter((c: Character) => c.entity_type === 'object' || c.entity_type === 'location').length ? 'Deselect All' : 'Select All'}
                </button>
              )}

              {mode === 'creator' && (
                <button
                  onClick={() => {
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
                      entity_type: 'object',
                    });
                    setShowCreateModal(true);
                  }}
                  className="flex items-center space-x-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 text-sm border border-gray-200 dark:border-gray-700"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Object/Location</span>
                </button>
              )}
            </div>
          </div>
          
          <button
            onClick={() => setIsObjectsExpanded(!isObjectsExpanded)}
            className="flex items-center justify-between w-full group py-2"
          >
             <div className="flex items-center space-x-2 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
               {isObjectsExpanded ? "Hide" : "Show"} Objects & Locations
               {isObjectsExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
             </div>
          </button>

          {isObjectsExpanded && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredCharacters
              .filter((c: Character) => c.entity_type === 'object' || c.entity_type === 'location')
              .map((character: Character) => (
                <CharacterCard
                  key={character.id}
                  character={character}
                  isGeneratingImage={generatingImages.has(character.id)}
                  isSelected={selectedObjects.has(character.id)}
                  bookId={plotOverview?.book_id}
                  onToggleSelect={handleToggleSelectObject}
                  onUpdate={handleUpdateCharacter}
                  onDelete={handleDeleteClick}
                  onGenerateImage={handleGenerateImage}
                  onRegenerateImage={handleRegenerateImage}
                  onViewImage={(url) => setShowImageModal(url)}
                  onDeleteImage={handleDeleteCharacterImage}
                  onSetDefaultImage={handleSetDefaultImage}
                />
              ))}
              
              {filteredCharacters.filter((c: Character) => c.entity_type === 'object').length === 0 && (
                <div className="col-span-full py-8 text-center text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
                  <p>No objects or locations added yet.</p>
                </div>
              )}
          </div>
          )}
        </div>
       )}
      
      {/* Create Character Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">Create New Character</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                disabled={isCreatingCharacter}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-2xl font-bold"
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Character Name *
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newCharacter.name}
                    onChange={(e) => setNewCharacter(prev => ({ ...prev, name: e.target.value }))}
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Enter a character name, then click AI Assist to generate details from the book
                </p>
              </div>

              {(newCharacter.entity_type === 'character') && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Role
                    </label>
                    <select
                      value={newCharacter.role}
                      onChange={(e) => setNewCharacter(prev => ({ ...prev, role: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                </>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {newCharacter.entity_type === 'object' ? 'Object Description' : newCharacter.entity_type === 'location' ? 'Location Description' : 'Physical Description'}
                </label>
                <textarea
                  value={newCharacter.physical_description}
                  onChange={(e) => setNewCharacter(prev => ({ ...prev, physical_description: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder={newCharacter.entity_type === 'character' ? "Describe the character's appearance" : "Describe it..."}
                  disabled={isCreatingCharacter || isGeneratingWithAI}
                />
              </div>

              {(newCharacter.entity_type === 'character') && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Personality
                    </label>
                    <textarea
                      value={newCharacter.personality}
                      onChange={(e) => setNewCharacter(prev => ({ ...prev, personality: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      rows={3}
                      placeholder="Describe the character's personality traits"
                      disabled={isCreatingCharacter || isGeneratingWithAI}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Character Arc
                    </label>
                    <textarea
                      value={newCharacter.character_arc}
                      onChange={(e) => setNewCharacter(prev => ({ ...prev, character_arc: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      rows={2}
                      placeholder="How does this character change throughout the story?"
                      disabled={isCreatingCharacter || isGeneratingWithAI}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Want
                      </label>
                      <input
                        type="text"
                        value={newCharacter.want}
                        onChange={(e) => setNewCharacter(prev => ({ ...prev, want: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="What they want"
                        disabled={isCreatingCharacter || isGeneratingWithAI}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Need
                      </label>
                      <input
                        type="text"
                        value={newCharacter.need}
                        onChange={(e) => setNewCharacter(prev => ({ ...prev, need: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="What they need"
                        disabled={isCreatingCharacter || isGeneratingWithAI}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Lie They Believe
                      </label>
                      <input
                        type="text"
                        value={newCharacter.lie}
                        onChange={(e) => setNewCharacter(prev => ({ ...prev, lie: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Their false belief"
                        disabled={isCreatingCharacter || isGeneratingWithAI}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Ghost (Past Trauma)
                      </label>
                      <input
                        type="text"
                        value={newCharacter.ghost}
                        onChange={(e) => setNewCharacter(prev => ({ ...prev, ghost: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Their past trauma"
                        disabled={isCreatingCharacter || isGeneratingWithAI}
                      />
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                disabled={isCreatingCharacter || isGeneratingWithAI}
                className="flex-1 px-4 py-3 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-xl font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-all disabled:opacity-50"
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

      {/* Regenerate Image Confirmation Modal */}
      {showRegenerateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/50 rounded-full flex items-center justify-center">
                <Wand2 className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">Regenerate Image?</h3>
            </div>

            <p className="text-gray-600 dark:text-gray-300 mb-6">
              Character description changed. Would you like to regenerate the character image to match the new description?
            </p>

            <div className="flex gap-3">
              <button
                onClick={handleCancelRegenerate}
                className="flex-1 px-4 py-3 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-xl font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-all"
              >
                No, Keep Current
              </button>
              <button
                onClick={handleConfirmRegenerate}
                className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-all"
              >
                Yes, Regenerate
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
      {/* Object Bulk Delete Confirmation Modal */}
      {showBulkDeleteObjectsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900">Delete Multiple Items?</h3>
            </div>

            <p className="text-gray-600 mb-6">
              Are you sure you want to delete <strong>{selectedObjects.size} item{selectedObjects.size > 1 ? 's' : ''}</strong>? This action cannot be undone.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setShowBulkDeleteObjectsModal(false)}
                disabled={isBulkDeletingObjects}
                className="flex-1 px-4 py-3 bg-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-300 transition-all disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleBulkDeleteObjects}
                disabled={isBulkDeletingObjects}
                className="flex-1 px-4 py-3 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 transition-all disabled:opacity-50"
              >
                {isBulkDeletingObjects ? "Deleting..." : `Yes, Delete ${selectedObjects.size}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlotOverviewPanel;
