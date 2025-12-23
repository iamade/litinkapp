import React, { useEffect, useState } from 'react';
import { BookOpen, Loader2, Wand2 } from 'lucide-react';
import { useProjectPlotGeneration } from '../../hooks/useProjectPlotGeneration';

interface ProjectPlotPanelProps {
  projectId: string;
  projectTitle: string;
  inputPrompt: string;
  projectType: string;
  onCharacterChange?: () => void | Promise<void>;
}

/**
 * Plot panel for prompt-only projects.
 * Uses the project plot generation API instead of the book-based one.
 */
const ProjectPlotPanel: React.FC<ProjectPlotPanelProps> = ({
  projectId,
  projectTitle,
  inputPrompt,
  projectType,
  onCharacterChange,
}) => {
  const {
    plotOverview,
    isGenerating,
    isLoading,
    generatePlot,
    loadPlot,
    deleteCharacter,
  } = useProjectPlotGeneration({ projectId, inputPrompt, projectType });

  const [storyType, setStoryType] = useState('');
  const [genre, setGenre] = useState('');
  const [tone, setTone] = useState('');
  const [audience, setAudience] = useState('');

  useEffect(() => {
    loadPlot();
  }, [loadPlot]);

  const handleGeneratePlot = async () => {
    await generatePlot({
      storyType: storyType || undefined,
      genre: genre || undefined,
      tone: tone || undefined,
      audience: audience || undefined,
    });
    onCharacterChange?.();
  };

  const handleDeleteCharacter = async (characterId: string) => {
    await deleteCharacter(characterId);
    onCharacterChange?.();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
        <span className="ml-3 text-gray-600">Loading plot overview...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-gray-900">Plot Overview</h3>
          <p className="text-gray-600">Generate creative plot for: {projectTitle}</p>
        </div>
      </div>

      {/* Input Prompt Display */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-purple-900 mb-2">Your Creative Prompt</h4>
        <p className="text-gray-700">{inputPrompt}</p>
      </div>

      {/* Generation Options */}
      {!plotOverview && (
        <div className="bg-white rounded-lg border p-6 space-y-4">
          <h4 className="text-lg font-semibold text-gray-900 flex items-center">
            <Wand2 className="h-5 w-5 mr-2 text-purple-600" />
            Generate Plot Overview
          </h4>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Story Type</label>
              <select
                value={storyType}
                onChange={(e) => setStoryType(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500"
              >
                <option value="">Auto-detect</option>
                <option value="hero's journey">Hero's Journey</option>
                <option value="underdog story">Underdog Story</option>
                <option value="transformation">Transformation</option>
                <option value="mystery">Mystery</option>
                <option value="comedy">Comedy</option>
                <option value="documentary">Documentary</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Genre</label>
              <input
                type="text"
                value={genre}
                onChange={(e) => setGenre(e.target.value)}
                placeholder="e.g., Drama, Comedy, Action"
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tone</label>
              <input
                type="text"
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                placeholder="e.g., Inspiring, Humorous, Professional"
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Audience</label>
              <input
                type="text"
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
                placeholder="e.g., General, Young Adults, Professionals"
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>

          <button
            onClick={handleGeneratePlot}
            disabled={isGenerating}
            className="w-full flex items-center justify-center px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isGenerating ? (
              <>
                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                Generating Plot...
              </>
            ) : (
              <>
                <Wand2 className="h-5 w-5 mr-2" />
                Generate Plot Overview
              </>
            )}
          </button>
        </div>
      )}

      {/* Plot Overview Display */}
      {plotOverview && (
        <div className="space-y-6">
          {/* Logline */}
          <div className="bg-white rounded-lg border p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
              <BookOpen className="h-5 w-5 mr-2 text-purple-600" />
              Logline
            </h4>
            <p className="text-gray-700 text-lg leading-relaxed">{plotOverview.logline}</p>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg border p-4">
              <h5 className="text-sm font-medium text-gray-500 mb-1">Story Type</h5>
              <p className="text-gray-900 font-medium">{plotOverview.story_type || 'N/A'}</p>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <h5 className="text-sm font-medium text-gray-500 mb-1">Genre</h5>
              <p className="text-gray-900 font-medium">{plotOverview.genre || 'N/A'}</p>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <h5 className="text-sm font-medium text-gray-500 mb-1">Tone</h5>
              <p className="text-gray-900 font-medium">{plotOverview.tone || 'N/A'}</p>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <h5 className="text-sm font-medium text-gray-500 mb-1">Audience</h5>
              <p className="text-gray-900 font-medium">{plotOverview.audience || 'N/A'}</p>
            </div>
          </div>

          {/* Themes */}
          {plotOverview.themes && plotOverview.themes.length > 0 && (
            <div className="bg-white rounded-lg border p-6">
              <h4 className="text-lg font-semibold text-gray-900 mb-3">Themes</h4>
              <div className="flex flex-wrap gap-2">
                {plotOverview.themes.map((theme, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium"
                  >
                    {theme}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Setting */}
          {plotOverview.setting && (
            <div className="bg-white rounded-lg border p-6">
              <h4 className="text-lg font-semibold text-gray-900 mb-3">Setting</h4>
              <p className="text-gray-700">{plotOverview.setting}</p>
            </div>
          )}

          {/* Characters */}
          {plotOverview.characters && plotOverview.characters.length > 0 && (
            <div className="bg-white rounded-lg border p-6">
              <h4 className="text-lg font-semibold text-gray-900 mb-4">Characters</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {plotOverview.characters.map((char: any, idx) => (
                  <div key={char.id || idx} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between mb-2">
                      <h5 className="font-semibold text-gray-900">{char.name}</h5>
                      <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded-full">
                        {char.role}
                      </span>
                    </div>
                    {char.personality && (
                      <p className="text-sm text-gray-600 mb-2">{char.personality}</p>
                    )}
                    {char.character_arc && (
                      <p className="text-xs text-gray-500 italic">{char.character_arc}</p>
                    )}
                    {char.id && (
                      <button
                        onClick={() => handleDeleteCharacter(char.id)}
                        className="mt-2 text-xs text-red-500 hover:text-red-700"
                      >
                        Remove Character
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Regenerate Button */}
          <div className="flex justify-center">
            <button
              onClick={handleGeneratePlot}
              disabled={isGenerating}
              className="flex items-center px-4 py-2 text-purple-600 border border-purple-600 rounded-lg hover:bg-purple-50 disabled:opacity-50"
            >
              {isGenerating ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4 mr-2" />
              )}
              Regenerate Plot
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectPlotPanel;
