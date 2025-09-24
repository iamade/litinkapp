import React, { useState, useEffect } from 'react';
import { BookOpen, Users, Edit2, Save, X, Plus, Trash2, Image, Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

interface PlotOverview {
  logline: string;
  themes: string[];
  storyType: string;
  genre: string;
  tone: string;
  audience: string;
  setting: string;
  characters: Character[];
}

interface Character {
  name: string;
  role: string;
  characterArc: string;
  physicalDescription: string;
  personality: string;
  archetypes: string[];
  want: string;
  need: string;
  lie: string;
  ghost: string;
  imageUrl?: string;
}

interface PlotOverviewPanelProps {
  bookId: string;
  plotOverview: PlotOverview | null;
  isGenerating: boolean;
  onGenerate: () => void;
  onSave: (plotOverview: PlotOverview) => void;
}

const PlotOverviewPanel: React.FC<PlotOverviewPanelProps> = ({
  bookId,
  plotOverview,
  isGenerating,
  onGenerate,
  onSave
}) => {
  const [editMode, setEditMode] = useState(false);
  const [editedPlot, setEditedPlot] = useState<PlotOverview | null>(null);
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [isGeneratingImage, setIsGeneratingImage] = useState<string | null>(null);

  useEffect(() => {
    if (plotOverview) {
      setEditedPlot(plotOverview);
    }
  }, [plotOverview]);

  const handleSave = () => {
    if (editedPlot) {
      onSave(editedPlot);
      setEditMode(false);
      toast.success('Plot overview saved!');
    }
  };

  const handleCancel = () => {
    setEditedPlot(plotOverview);
    setEditMode(false);
  };

  const updatePlotField = (field: keyof PlotOverview, value: any) => {
    if (editedPlot) {
      setEditedPlot({ ...editedPlot, [field]: value });
    }
  };

  const addTheme = () => {
    if (editedPlot) {
      setEditedPlot({
        ...editedPlot,
        themes: [...editedPlot.themes, '']
      });
    }
  };

  const updateTheme = (index: number, value: string) => {
    if (editedPlot) {
      const newThemes = [...editedPlot.themes];
      newThemes[index] = value;
      setEditedPlot({ ...editedPlot, themes: newThemes });
    }
  };

  const removeTheme = (index: number) => {
    if (editedPlot) {
      const newThemes = editedPlot.themes.filter((_, i) => i !== index);
      setEditedPlot({ ...editedPlot, themes: newThemes });
    }
  };

  const addCharacter = () => {
    if (editedPlot) {
      const newCharacter: Character = {
        name: '',
        role: '',
        characterArc: '',
        physicalDescription: '',
        personality: '',
        archetypes: [],
        want: '',
        need: '',
        lie: '',
        ghost: '',
        imageUrl: undefined
      };
      setEditedPlot({
        ...editedPlot,
        characters: [...editedPlot.characters, newCharacter]
      });
    }
  };

  const updateCharacter = (index: number, character: Character) => {
    if (editedPlot) {
      const newCharacters = [...editedPlot.characters];
      newCharacters[index] = character;
      setEditedPlot({ ...editedPlot, characters: newCharacters });
    }
  };

  const removeCharacter = (index: number) => {
    if (editedPlot) {
      const newCharacters = editedPlot.characters.filter((_, i) => i !== index);
      setEditedPlot({ ...editedPlot, characters: newCharacters });
    }
  };

  const generateCharacterImage = async (characterIndex: number) => {
    const character = editedPlot?.characters[characterIndex];
    if (!character) return;

    setIsGeneratingImage(character.name);
    try {
      // TODO: Replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 2000)); // Mock delay
      
      // Mock generated image URL
      const mockImageUrl = `https://via.placeholder.com/200x250/4F46E5/ffffff?text=${encodeURIComponent(character.name)}`;
      
      updateCharacter(characterIndex, {
        ...character,
        imageUrl: mockImageUrl
      });
      
      toast.success(`Generated image for ${character.name}`);
    } catch (error) {
      toast.error('Failed to generate character image');
    } finally {
      setIsGeneratingImage(null);
    }
  };

  if (!plotOverview && !editMode) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">Plot Overview</h3>
            <p className="text-gray-600">Generate comprehensive story analysis and character profiles</p>
          </div>
          <button
            onClick={onGenerate}
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
          <p>Generate a plot overview to see story analysis and character details</p>
        </div>
      </div>
    );
  }

  const currentPlot = editMode ? editedPlot : plotOverview;
  if (!currentPlot) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-gray-900">Plot Overview</h3>
          <p className="text-gray-600">Story analysis and character profiles</p>
        </div>
        <div className="flex items-center space-x-2">
          {!editMode ? (
            <>
              <button
                onClick={onGenerate}
                disabled={isGenerating}
                className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-400 text-sm"
              >
                <BookOpen className="w-4 h-4" />
                <span>Regenerate</span>
              </button>
              <button
                onClick={() => setEditMode(true)}
                className="flex items-center space-x-2 px-3 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm"
              >
                <Edit2 className="w-4 h-4" />
                <span>Edit</span>
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleCancel}
                className="flex items-center space-x-2 px-3 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm"
              >
                <X className="w-4 h-4" />
                <span>Cancel</span>
              </button>
              <button
                onClick={handleSave}
                className="flex items-center space-x-2 px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
              >
                <Save className="w-4 h-4" />
                <span>Save</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Plot Overview Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-4">
          {/* Logline */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="font-semibold text-gray-900 mb-2">Logline</h4>
            {editMode ? (
              <textarea
                value={currentPlot.logline}
                onChange={(e) => updatePlotField('logline', e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md resize-none"
                rows={3}
                placeholder="A compelling one-sentence summary of the story..."
              />
            ) : (
              <p className="text-gray-700">{currentPlot.logline}</p>
            )}
          </div>

          {/* Genre, Tone, Audience */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="font-semibold text-gray-900 mb-3">Genre & Tone</h4>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Genre</label>
                {editMode ? (
                  <input
                    type="text"
                    value={currentPlot.genre}
                    onChange={(e) => updatePlotField('genre', e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded-md"
                  />
                ) : (
                  <p className="text-gray-700">{currentPlot.genre}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tone</label>
                {editMode ? (
                  <input
                    type="text"
                    value={currentPlot.tone}
                    onChange={(e) => updatePlotField('tone', e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded-md"
                  />
                ) : (
                  <p className="text-gray-700">{currentPlot.tone}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Audience</label>
                {editMode ? (
                  <input
                    type="text"
                    value={currentPlot.audience}
                    onChange={(e) => updatePlotField('audience', e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded-md"
                  />
                ) : (
                  <p className="text-gray-700">{currentPlot.audience}</p>
                )}
              </div>
            </div>
          </div>

          {/* Setting */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="font-semibold text-gray-900 mb-2">Setting</h4>
            {editMode ? (
              <textarea
                value={currentPlot.setting}
                onChange={(e) => updatePlotField('setting', e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md resize-none"
                rows={2}
                placeholder="Where and when the story takes place..."
              />
            ) : (
              <p className="text-gray-700">{currentPlot.setting}</p>
            )}
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-4">
          {/* Themes */}
          <div className="bg-white p-4 rounded-lg border">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-gray-900">Themes</h4>
              {editMode && (
                <button
                  onClick={addTheme}
                  className="flex items-center space-x-1 px-2 py-1 text-blue-600 hover:bg-blue-50 rounded text-sm"
                >
                  <Plus className="w-3 h-3" />
                  <span>Add</span>
                </button>
              )}
            </div>
            <div className="space-y-2">
              {currentPlot.themes.map((theme, idx) => (
                <div key={idx} className="flex items-center space-x-2">
                  {editMode ? (
                    <>
                      <input
                        type="text"
                        value={theme}
                        onChange={(e) => updateTheme(idx, e.target.value)}
                        className="flex-1 p-2 border border-gray-300 rounded-md"
                        placeholder="Theme..."
                      />
                      <button
                        onClick={() => removeTheme(idx)}
                        className="text-red-600 hover:bg-red-50 p-1 rounded"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
                  ) : (
                    <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                      {theme}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Story Type */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="font-semibold text-gray-900 mb-2">Story Type</h4>
            {editMode ? (
              <input
                type="text"
                value={currentPlot.storyType}
                onChange={(e) => updatePlotField('storyType', e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md"
                placeholder="Type of story structure..."
              />
            ) : (
              <p className="text-gray-700">{currentPlot.storyType}</p>
            )}
          </div>
        </div>
      </div>

      {/* Characters Section */}
      <div className="bg-white rounded-lg border">
        <div className="p-4 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Users className="w-5 h-5 text-gray-600" />
              <h4 className="text-lg font-semibold text-gray-900">Characters</h4>
              <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded-full text-xs">
                {currentPlot.characters.length}
              </span>
            </div>
            {editMode && (
              <button
                onClick={addCharacter}
                className="flex items-center space-x-1 px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
              >
                <Plus className="w-3 h-3" />
                <span>Add Character</span>
              </button>
            )}
          </div>
        </div>

        <div className="p-4">
          {currentPlot.characters.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Users className="mx-auto h-8 w-8 mb-2 opacity-50" />
              <p>No characters defined</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {currentPlot.characters.map((character, idx) => (
                <CharacterCard
                  key={idx}
                  character={character}
                  index={idx}
                  editMode={editMode}
                  onUpdate={(updatedCharacter) => updateCharacter(idx, updatedCharacter)}
                  onRemove={() => removeCharacter(idx)}
                  onGenerateImage={() => generateCharacterImage(idx)}
                  isGeneratingImage={isGeneratingImage === character.name}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Character Card Component
interface CharacterCardProps {
  character: Character;
  index: number;
  editMode: boolean;
  onUpdate: (character: Character) => void;
  onRemove: () => void;
  onGenerateImage: () => void;
  isGeneratingImage: boolean;
}

const CharacterCard: React.FC<CharacterCardProps> = ({
  character,
  index,
  editMode,
  onUpdate,
  onRemove,
  onGenerateImage,
  isGeneratingImage
}) => {
  const [expanded, setExpanded] = useState(false);

  const updateField = (field: keyof Character, value: any) => {
    onUpdate({ ...character, [field]: value });
  };

  const addArchetype = () => {
    updateField('archetypes', [...character.archetypes, '']);
  };

  const updateArchetype = (idx: number, value: string) => {
    const newArchetypes = [...character.archetypes];
    newArchetypes[idx] = value;
    updateField('archetypes', newArchetypes);
  };

  const removeArchetype = (idx: number) => {
    const newArchetypes = character.archetypes.filter((_, i) => i !== idx);
    updateField('archetypes', newArchetypes);
  };

  return (
    <div className="border rounded-lg p-4 space-y-3">
      {/* Character Header */}
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          {character.imageUrl ? (
            <img
              src={character.imageUrl}
              alt={character.name}
              className="w-16 h-20 object-cover rounded-md"
            />
          ) : (
            <div className="w-16 h-20 bg-gray-200 rounded-md flex items-center justify-center">
              <Users className="w-6 h-6 text-gray-400" />
            </div>
          )}
          {editMode && (
            <button
              onClick={onGenerateImage}
              disabled={isGeneratingImage}
              className="mt-2 w-full flex items-center justify-center space-x-1 px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100 disabled:opacity-50"
            >
              {isGeneratingImage ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Image className="w-3 h-3" />
              )}
              <span>Generate</span>
            </button>
          )}
        </div>

        <div className="flex-1 min-w-0">
          {editMode ? (
            <input
              type="text"
              value={character.name}
              onChange={(e) => updateField('name', e.target.value)}
              className="w-full font-medium text-gray-900 bg-transparent border-b border-gray-300 focus:border-blue-500 outline-none"
              placeholder="Character name..."
            />
          ) : (
            <h5 className="font-medium text-gray-900 truncate">{character.name || 'Unnamed Character'}</h5>
          )}
          
          {editMode ? (
            <input
              type="text"
              value={character.role}
              onChange={(e) => updateField('role', e.target.value)}
              className="w-full text-sm text-gray-600 bg-transparent border-b border-gray-200 focus:border-blue-500 outline-none mt-1"
              placeholder="Character role..."
            />
          ) : (
            <p className="text-sm text-gray-600">{character.role}</p>
          )}
        </div>

        <div className="flex items-center space-x-1">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-gray-400 hover:text-gray-600"
          >
            <ChevronRight className={`w-4 h-4 transform transition-transform ${expanded ? 'rotate-90' : ''}`} />
          </button>
          {editMode && (
            <button
              onClick={onRemove}
              className="text-red-400 hover:text-red-600"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Expanded Character Details */}
      {expanded && (
        <div className="space-y-3 pt-3 border-t">
          {/* Character Arc */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Character Arc</label>
            {editMode ? (
              <textarea
                value={character.characterArc}
                onChange={(e) => updateField('characterArc', e.target.value)}
                className="w-full p-2 border border-gray-300 rounded text-xs resize-none"
                rows={2}
                placeholder="Character's journey and growth..."
              />
            ) : (
              <p className="text-xs text-gray-700">{character.characterArc}</p>
            )}
          </div>

          {/* Physical Description */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Physical Description</label>
            {editMode ? (
              <textarea
                value={character.physicalDescription}
                onChange={(e) => updateField('physicalDescription', e.target.value)}
                className="w-full p-2 border border-gray-300 rounded text-xs resize-none"
                rows={2}
                placeholder="How the character looks..."
              />
            ) : (
              <p className="text-xs text-gray-700">{character.physicalDescription}</p>
            )}
          </div>

          {/* Personality */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Personality</label>
            {editMode ? (
              <textarea
                value={character.personality}
                onChange={(e) => updateField('personality', e.target.value)}
                className="w-full p-2 border border-gray-300 rounded text-xs resize-none"
                rows={2}
                placeholder="Character's personality traits..."
              />
            ) : (
              <p className="text-xs text-gray-700">{character.personality}</p>
            )}
          </div>

          {/* Archetypes */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-medium text-gray-700">Archetypes</label>
              {editMode && (
                <button
                  onClick={addArchetype}
                  className="text-blue-600 hover:text-blue-800"
                >
                  <Plus className="w-3 h-3" />
                </button>
              )}
            </div>
            <div className="space-y-1">
              {character.archetypes.map((archetype, idx) => (
                <div key={idx} className="flex items-center space-x-1">
                  {editMode ? (
                    <>
                      <input
                        type="text"
                        value={archetype}
                        onChange={(e) => updateArchetype(idx, e.target.value)}
                        className="flex-1 p-1 border border-gray-300 rounded text-xs"
                        placeholder="Archetype..."
                      />
                      <button
                        onClick={() => removeArchetype(idx)}
                        className="text-red-600 hover:text-red-800"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </>
                  ) : (
                    <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs">
                      {archetype}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Want, Need, Lie, Ghost */}
          <div className="grid grid-cols-2 gap-2">
            {[
              { field: 'want', label: 'Want' },
              { field: 'need', label: 'Need' },
              { field: 'lie', label: 'Lie' },
              { field: 'ghost', label: 'Ghost' }
            ].map(({ field, label }) => (
              <div key={field}>
                <label className="block text-xs font-medium text-gray-700 mb-1">{label}</label>
                {editMode ? (
                  <textarea
                    value={character[field as keyof Character] as string}
                    onChange={(e) => updateField(field as keyof Character, e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded text-xs resize-none"
                    rows={2}
                    placeholder={`Character's ${label.toLowerCase()}...`}
                  />
                ) : (
                  <p className="text-xs text-gray-700">{character[field as keyof Character] as string}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PlotOverviewPanel;