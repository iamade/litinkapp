import React, { useEffect, useState } from "react";
import { BookOpen, Loader2, Trash2, AlertCircle } from "lucide-react";
import { usePlotGeneration } from "../../hooks/usePlotGeneration";

interface PlotOverviewPanelProps {
  bookId: string;
}

const PlotOverviewPanel: React.FC<PlotOverviewPanelProps> = ({ bookId }) => {
  const { plotOverview, isGenerating, isLoading, generatePlot, loadPlot, deleteCharacter } =
    usePlotGeneration(bookId);

  const [deletingCharacterId, setDeletingCharacterId] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [characterToDelete, setCharacterToDelete] = useState<{ id: string; name: string } | null>(null);

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-gray-900">Plot Overview</h3>
          <p className="text-gray-600">Story analysis</p>
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
          {/* Conditional Story Type */}
          <div className="bg-white p-4 rounded-lg border">
            {normalizedGenre.includes("non-fiction") || normalizedGenre.includes("nonfiction") ? (
              <>
                <h4 className="font-semibold text-gray-900 mb-2">Script Story Type</h4>
                <p className="text-gray-700">{plotOverview.script_story_type}</p>
              </>
            ) : (
              <>
                <h4 className="font-semibold text-gray-900 mb-2">Script Story Type</h4>
                <p className="text-gray-700">{plotOverview.script_story_type}</p>
              </>
            )}
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-4">
          {/* Themes */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="font-semibold text-gray-900 mb-2">Themes</h4>
            <div className="space-y-2">
              {plotOverview.themes.map((theme, idx) => (
                <span
                  key={idx}
                  className="inline-block px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm mr-2 mb-2"
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

          {/* Characters */}
          {plotOverview.characters && plotOverview.characters.length > 0 && (
            <div className="bg-white p-4 rounded-lg border">
              <h4 className="font-semibold text-gray-900 mb-3">Characters</h4>
              <div className="space-y-4">
                {plotOverview.characters.map((character, idx) => {
                  const charId = (character as any).id;
                  const isDeleting = deletingCharacterId === charId;

                  return (
                    <div
                      key={idx}
                      className="border-b border-gray-200 pb-4 last:border-b-0 last:pb-0 relative"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h5 className="font-medium text-gray-900">{character.name}</h5>
                        {charId && (
                          <button
                            onClick={() => handleDeleteClick(charId, character.name)}
                            disabled={isDeleting}
                            className="text-red-600 hover:text-red-700 disabled:opacity-50 p-1 rounded-md hover:bg-red-50 transition-colors"
                            title="Delete character"
                          >
                            {isDeleting ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Trash2 className="w-4 h-4" />
                            )}
                          </button>
                        )}
                      </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="font-medium text-gray-700">Role:</span>{" "}
                        {character.role}
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">Personality:</span>{" "}
                        {character.personality}
                      </div>
                      <div className="md:col-span-2">
                        <span className="font-medium text-gray-700">
                          Physical Description:
                        </span>{" "}
                        {character.physical_description}
                      </div>
                      <div className="md:col-span-2">
                        <span className="font-medium text-gray-700">Character Arc:</span>{" "}
                        {character.character_arc}
                      </div>
                      {character.archetypes && character.archetypes.length > 0 && (
                        <div className="md:col-span-2">
                          <span className="font-medium text-gray-700">Archetypes:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {character.archetypes.map((archetype, archIdx) => (
                              <span
                                key={archIdx}
                                className="px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs"
                              >
                                {archetype}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

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
