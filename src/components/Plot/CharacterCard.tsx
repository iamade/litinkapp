import React, { useState, useRef, useEffect } from 'react';
import {
  User,
  Image as ImageIcon,
  Wand2,
  RefreshCw,
  Trash2,
  Eye,
  Save,
  X,
  Edit2,
  Loader2,
  Plus
} from 'lucide-react';

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

interface CharacterCardProps {
  character: Character;
  isGeneratingImage: boolean;
  isSelected: boolean;
  onToggleSelect: (characterId: string) => void;
  onUpdate: (characterId: string, updates: Partial<Character>) => Promise<void>;
  onDelete: (characterId: string, characterName: string) => void;
  onGenerateImage: (characterId: string) => void;
  onRegenerateImage: (characterId: string) => void;
  onViewImage: (imageUrl: string) => void;
}

const CharacterCard: React.FC<CharacterCardProps> = ({
  character,
  isGeneratingImage,
  isSelected,
  onToggleSelect,
  onUpdate,
  onDelete,
  onGenerateImage,
  onRegenerateImage,
  onViewImage
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedCharacter, setEditedCharacter] = useState<Partial<Character>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  const nameInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing && nameInputRef.current) {
      nameInputRef.current.focus();
    }
  }, [isEditing]);

  const handleEditToggle = () => {
    if (isEditing) {
      // Cancel editing
      setEditedCharacter({});
      setIsEditing(false);
    } else {
      // Start editing
      setEditedCharacter({
        name: character.name,
        role: character.role || '',
        physical_description: character.physical_description || '',
        personality: character.personality || '',
        character_arc: character.character_arc || '',
        archetypes: character.archetypes || []
      });
      setIsEditing(true);
    }
  };

  const handleSave = async () => {
    if (!editedCharacter.name?.trim()) {
      return;
    }

    setIsSaving(true);
    try {
      await onUpdate(character.id, editedCharacter);
      setIsEditing(false);
      setEditedCharacter({});
    } finally {
      setIsSaving(false);
    }
  };

  const handleInputChange = (field: keyof Character, value: string) => {
    setEditedCharacter(prev => ({ ...prev, [field]: value }));
  };

  const handleAddArchetype = () => {
    const newArchetype = prompt('Enter archetype name:');
    if (newArchetype?.trim()) {
      const currentArchetypes = editedCharacter.archetypes || character.archetypes || [];
      if (!currentArchetypes.includes(newArchetype.trim())) {
        setEditedCharacter(prev => ({
          ...prev,
          archetypes: [...currentArchetypes, newArchetype.trim()]
        }));
      }
    }
  };

  const handleRemoveArchetype = (archetype: string) => {
    const currentArchetypes = editedCharacter.archetypes || character.archetypes || [];
    setEditedCharacter(prev => ({
      ...prev,
      archetypes: currentArchetypes.filter(a => a !== archetype)
    }));
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const displayValue = (field: keyof Character) => {
    return isEditing ? editedCharacter[field] ?? character[field] : character[field];
  };

  const displayArchetypes = isEditing
    ? editedCharacter.archetypes ?? character.archetypes
    : character.archetypes;

  return (
    <div className={`bg-white rounded-lg shadow-sm border transition-all ${
      isSelected ? 'ring-2 ring-blue-500 bg-blue-50' : isEditing ? 'ring-2 ring-blue-500' : 'hover:shadow-md'
    }`}>
      {/* Image Section */}
      <div className="aspect-[3/4] relative bg-gray-100 rounded-t-lg overflow-hidden">
        {/* Selection Checkbox */}
        <div className="absolute top-2 left-2 z-10">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggleSelect(character.id)}
            className="w-5 h-5 rounded border-2 border-white shadow-lg cursor-pointer accent-blue-600"
            title="Select for bulk action"
          />
        </div>

        {isGeneratingImage ? (
          <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50">
            <div className="text-center p-4">
              <div className="relative">
                <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-3" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Wand2 className="w-6 h-6 text-purple-500" />
                </div>
              </div>
              <span className="text-sm font-medium text-gray-700">Generating Image</span>
              <p className="text-xs text-gray-500 mt-1">This may take 20-30 seconds...</p>
            </div>
          </div>
        ) : character.image_url ? (
          <>
            <img
              src={character.image_url}
              alt={character.name}
              className="w-full h-full object-cover"
            />
            <div className="absolute top-2 right-2 flex space-x-1">
              <button
                onClick={() => onViewImage(character.image_url!)}
                className="p-2 bg-black bg-opacity-50 text-white rounded-md hover:bg-opacity-70 transition-all"
                title="View full size"
              >
                <Eye className="w-4 h-4" />
              </button>
              <button
                onClick={() => onRegenerateImage(character.id)}
                className="p-2 bg-black bg-opacity-50 text-white rounded-md hover:bg-opacity-70 transition-all"
                title="Regenerate image"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <button
              onClick={() => onGenerateImage(character.id)}
              className="flex flex-col items-center space-y-2 text-gray-400 hover:text-blue-600 transition-colors"
            >
              <ImageIcon className="w-12 h-12" />
              <span className="text-sm font-medium">Generate Image</span>
            </button>
          </div>
        )}
      </div>

      {/* Content Section */}
      <div className="p-4 space-y-3">
        {/* Name Field */}
        <div>
          {isEditing ? (
            <input
              ref={nameInputRef}
              type="text"
              value={displayValue('name') as string}
              onChange={(e) => handleInputChange('name', e.target.value)}
              className="w-full text-lg font-semibold text-gray-900 border-b-2 border-blue-500 focus:outline-none px-1"
              placeholder="Character name"
            />
          ) : (
            <h3 className="text-lg font-semibold text-gray-900">{character.name}</h3>
          )}
        </div>

        {/* Role Field */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Role</label>
          {isEditing ? (
            <input
              type="text"
              value={displayValue('role') as string}
              onChange={(e) => handleInputChange('role', e.target.value)}
              className="w-full text-sm text-gray-700 border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Protagonist, Mentor"
            />
          ) : (
            <p className="text-sm text-gray-700">{character.role || 'Not specified'}</p>
          )}
        </div>

        {/* Physical Description */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Physical Description
          </label>
          {isEditing ? (
            <textarea
              value={displayValue('physical_description') as string}
              onChange={(e) => handleInputChange('physical_description', e.target.value)}
              className="w-full text-sm text-gray-700 border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
              placeholder="Describe appearance..."
            />
          ) : (
            <div>
              <p className={`text-sm text-gray-700 ${
                !expandedSections.physical_description ? 'line-clamp-2' : ''
              }`}>
                {character.physical_description || 'Not specified'}
              </p>
              {character.physical_description && character.physical_description.length > 100 && (
                <button
                  onClick={() => toggleSection('physical_description')}
                  className="text-xs text-blue-600 hover:text-blue-700 mt-1"
                >
                  {expandedSections.physical_description ? 'Show less' : 'Show more'}
                </button>
              )}
            </div>
          )}
        </div>

        {/* Personality */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Personality</label>
          {isEditing ? (
            <textarea
              value={displayValue('personality') as string}
              onChange={(e) => handleInputChange('personality', e.target.value)}
              className="w-full text-sm text-gray-700 border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
              placeholder="Describe personality traits..."
            />
          ) : (
            <p className="text-sm text-gray-700 line-clamp-2">
              {character.personality || 'Not specified'}
            </p>
          )}
        </div>

        {/* Archetypes */}
        {(displayArchetypes && displayArchetypes.length > 0) || isEditing ? (
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Archetypes</label>
            <div className="flex flex-wrap gap-1">
              {displayArchetypes?.map((archetype, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs"
                >
                  {archetype}
                  {isEditing && (
                    <button
                      onClick={() => handleRemoveArchetype(archetype)}
                      className="ml-1 hover:text-purple-900"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </span>
              ))}
              {isEditing && (
                <button
                  onClick={handleAddArchetype}
                  className="inline-flex items-center px-2 py-1 bg-gray-100 text-gray-600 rounded-full text-xs hover:bg-gray-200"
                >
                  <Plus className="w-3 h-3 mr-1" />
                  Add
                </button>
              )}
            </div>
          </div>
        ) : null}

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-3 border-t">
          {isEditing ? (
            <div className="flex space-x-2 w-full">
              <button
                onClick={handleSave}
                disabled={isSaving || !editedCharacter.name?.trim()}
                className="flex items-center justify-center space-x-1 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 flex-1 text-sm"
              >
                {isSaving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                <span>{isSaving ? 'Saving...' : 'Save'}</span>
              </button>
              <button
                onClick={handleEditToggle}
                disabled={isSaving}
                className="flex items-center justify-center space-x-1 px-3 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:bg-gray-100 flex-1 text-sm"
              >
                <X className="w-4 h-4" />
                <span>Cancel</span>
              </button>
            </div>
          ) : (
            <>
              <button
                onClick={handleEditToggle}
                className="flex items-center space-x-1 px-3 py-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors text-sm"
              >
                <Edit2 className="w-4 h-4" />
                <span>Edit</span>
              </button>
              <button
                onClick={() => onDelete(character.id, character.name)}
                className="flex items-center space-x-1 px-3 py-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors text-sm"
              >
                <Trash2 className="w-4 h-4" />
                <span>Delete</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default CharacterCard;
