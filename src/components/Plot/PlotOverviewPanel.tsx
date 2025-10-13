import React, { useEffect, useState } from "react";
import { BookOpen, Loader2, AlertCircle, Wand2, Users } from "lucide-react";
import { usePlotGeneration } from "../../hooks/usePlotGeneration";
import CharacterCard from "./CharacterCard";
import { userService } from "../../services/userService";
import { toast } from "react-hot-toast";

interface PlotOverviewPanelProps {
  bookId: string;
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

const PlotOverviewPanel: React.FC<PlotOverviewPanelProps> = ({ bookId }) => {
  const { plotOverview, isGenerating, isLoading, generatePlot, loadPlot, deleteCharacter } =
    usePlotGeneration(bookId);

  const [deletingCharacterId, setDeletingCharacterId] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [characterToDelete, setCharacterToDelete] = useState<{ id: string; name: string } | null>(null);
  const [generatingImages, setGeneratingImages] = useState<Set<string>>(new Set());
  const [showImageModal, setShowImageModal] = useState<string | null>(null);
  const [showGenerateAllModal, setShowGenerateAllModal] = useState(false);

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

      // Reload plot to get updated character with image_url
      await loadPlot();
      toast.success("Character image generated successfully");
    } catch (error) {
      toast.error("Failed to generate character image");
    } finally {
      setGeneratingImages(prev => {
        const newSet = new Set(prev);
        newSet.delete(characterId);
        return newSet;
      });
    }
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
            <h3 className="text-xl font-semibold text-gray-900">Plot Overview</h3>
            <p className="text-gray-600">Generate comprehensive story analysis</p>
          </div>
          <button
            onClick={generatePlot}
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

        <div className="text-center py-12 text-gray-500">
          <BookOpen className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p>Generate a plot overview to see story analysis</p>
        </div>
      </div>
    );
  }

  const normalizedGenre = plotOverview.genre?.toLowerCase() || "";
  const charactersWithoutImages = plotOverview.characters?.filter((char: Character) => !char.image_url).length || 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-gray-900">Plot Overview</h3>
          <p className="text-gray-600">Story analysis and character management</p>
        </div>
        <button
          onClick={generatePlot}
          disabled={isGenerating}
          className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-400 text-sm"
        >
          <BookOpen className="w-4 h-4" />
          <span>Regenerate</span>
        </button>
      </div>

      {/* Plot Overview Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-4">
          {/* Logline */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="font-semibold text-gray-900 mb-2">Logline</h4>
            <p className="text-gray-700">{plotOverview.logline}</p>
          </div>
          {/* Genre, Tone, Audience */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="font-semibold text-gray-900 mb-3">Genre & Tone</h4>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Genre
                </label>
                <p className="text-gray-700">{plotOverview.genre}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tone
                </label>
                <p className="text-gray-700">{plotOverview.tone}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Audience
                </label>
                <p className="text-gray-700">{plotOverview.audience}</p>
              </div>
            </div>
          </div>
          {/* Setting */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="font-semibold text-gray-900 mb-2">Setting</h4>
            <p className="text-gray-700">{plotOverview.setting}</p>
          </div>
          {/* Script Story Type */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="font-semibold text-gray-900 mb-2">Script Story Type</h4>
            <p className="text-gray-700">{plotOverview.script_story_type}</p>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-4">
          {/* Themes */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="font-semibold text-gray-900 mb-2">Themes</h4>
            <div className="flex flex-wrap gap-2">
              {plotOverview.themes.map((theme, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                >
                  {theme}
                </span>
              ))}
            </div>
          </div>

          {/* Story Type */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="font-semibold text-gray-900 mb-2">Story Type</h4>
            <p className="text-gray-700">{plotOverview.story_type}</p>
          </div>
        </div>
      </div>

      {/* Characters Section */}
      {plotOverview.characters && plotOverview.characters.length > 0 && (
        <div className="space-y-4">
          {/* Characters Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Users className="w-6 h-6 text-gray-700" />
              <div>
                <h4 className="text-lg font-semibold text-gray-900">Characters</h4>
                <p className="text-sm text-gray-600">
                  {plotOverview.characters.length} character{plotOverview.characters.length !== 1 ? 's' : ''} • {charactersWithoutImages} without images
                </p>
              </div>
            </div>
            {charactersWithoutImages > 0 && (
              <button
                onClick={() => setShowGenerateAllModal(true)}
                disabled={generatingImages.size > 0}
                className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 text-sm"
              >
                <Wand2 className="w-4 h-4" />
                <span>Generate All Character Images</span>
              </button>
            )}
          </div>

          {/* Characters Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {plotOverview.characters.map((character: Character) => (
              <CharacterCard
                key={character.id}
                character={character}
                isGeneratingImage={generatingImages.has(character.id)}
                onUpdate={handleUpdateCharacter}
                onDelete={handleDeleteClick}
                onGenerateImage={handleGenerateImage}
                onRegenerateImage={handleRegenerateImage}
                onViewImage={(url) => setShowImageModal(url)}
              />
            ))}
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
