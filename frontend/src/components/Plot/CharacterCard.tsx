import React, { useState, useRef, useEffect } from 'react';
import {
  Image as ImageIcon,
  Wand2,
  RefreshCw,
  Trash2,
  Eye,
  Save,
  X,
  Edit2,
  Loader2,
  Plus,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Star,
  AlertCircle
} from 'lucide-react';
import toast from 'react-hot-toast';
import { userService } from '../../services/userService';

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
  accent?: string;
  voice_characteristics?: string;
  voice_gender?: string;
}

interface CharacterCardProps {
  character: Character;
  isGeneratingImage: boolean;
  isSelected: boolean;
  bookId?: string;
  onToggleSelect: (characterId: string) => void;
  onUpdate: (characterId: string, updates: Partial<Character>) => Promise<void>;
  onDelete: (characterId: string, characterName: string) => void;
  onGenerateImage: (characterId: string) => void;
  onRegenerateImage: (characterId: string) => void;
  onViewImage: (imageUrl: string) => void;
  onDeleteImage?: (characterId: string, imageId: string) => Promise<void>;
  onSetDefaultImage?: (characterId: string, imageUrl: string) => Promise<void>;
}

const CharacterCard: React.FC<CharacterCardProps> = ({
  character,
  isGeneratingImage,
  isSelected,
  bookId,
  onToggleSelect,
  onUpdate,
  onDelete,
  onGenerateImage,
  onRegenerateImage,
  onViewImage,
  onDeleteImage,
  onSetDefaultImage
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedCharacter, setEditedCharacter] = useState<Partial<Character>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [isGeneratingWithAI, setIsGeneratingWithAI] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [showDeleteImageModal, setShowDeleteImageModal] = useState(false);

  const isObject = character.entity_type === 'object' || character.entity_type === 'location';
  
  // Carousel Logic
  const validImages = React.useMemo(() => {
    const images = character.images?.filter(img => img.status === 'completed' && img.image_url) || [];
    // If no history but we have a main image, treat it as the only image
    if (images.length === 0 && character.image_url) {
        return [{ id: 'legacy', image_url: character.image_url, created_at: '', status: 'completed' }];
    }
    // Sort by created_at desc
    return images.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [character.images, character.image_url]);

  const currentImage = validImages[currentImageIndex] || validImages[0];
  const hasMultipleImages = validImages.length > 1;

  const handleNextImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentImageIndex((prev) => (prev + 1) % validImages.length);
  };

  const handlePrevImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentImageIndex((prev) => (prev - 1 + validImages.length) % validImages.length);
  };

  const handleSetDefaultImage = async (e: React.MouseEvent) => {
      e.stopPropagation();
      if (!currentImage || currentImage.image_url === character.image_url) return;
      
      try {
          if (onSetDefaultImage) {
              await onSetDefaultImage(character.id, currentImage.image_url);
          } else {
              await onUpdate(character.id, { image_url: currentImage.image_url });
          }
          toast.success("Default image updated");
      } catch (error) {
          toast.error("Failed to update default image");
      }
  };

  const handleDeleteCurrentImage = async (e: React.MouseEvent) => {
      e.stopPropagation();
      if (!currentImage || !onDeleteImage) return;
      setShowDeleteImageModal(true);
  };

  const confirmDeleteImage = async () => {
      if (!currentImage || !onDeleteImage) return;

      try {
          await onDeleteImage(character.id, currentImage.id);
          // Adjust index if needed
          setCurrentImageIndex(prev => Math.max(0, prev - 1));
          setShowDeleteImageModal(false);
      } catch (error) {
          // Error handled by parent usually
      }
  };
  
  // Archetype modal state
  const [showArchetypeModal, setShowArchetypeModal] = useState(false);
  const [newArchetypeName, setNewArchetypeName] = useState('');
  const [archetypeError, setArchetypeError] = useState('');

  const nameInputRef = useRef<HTMLInputElement>(null);
  const archetypeInputRef = useRef<HTMLInputElement>(null);

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
      // Start editing with all fields
      setEditedCharacter({
        name: character.name,
        role: character.role || '',
        physical_description: character.physical_description || '',
        personality: character.personality || '',
        character_arc: character.character_arc || '',
        want: character.want || '',
        need: character.need || '',
        lie: character.lie || '',
        ghost: character.ghost || '',
        archetypes: character.archetypes || [],
        accent: character.accent || 'neutral',
        voice_characteristics: character.voice_characteristics || '',
        voice_gender: character.voice_gender || 'auto'
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

  // AI Assist handler
  const handleAIAssist = async () => {
    const name = editedCharacter.name?.trim() || character.name;
    if (!name) {
      toast.error("Character name is required for AI Assist");
      return;
    }

    if (!bookId) {
      toast.error("Book information not available for AI Assist");
      return;
    }

    setIsGeneratingWithAI(true);
    const loadingToast = toast.loading("AI is analyzing the book to generate character details...");

    try {
      const response = await userService.generateCharacterDetailsWithAI(
        name,
        bookId,
        editedCharacter.role || character.role || undefined
      );

      if (response.success && response.character_details) {
        setEditedCharacter(prev => ({
          ...prev,
          physical_description: response.character_details.physical_description || prev.physical_description,
          personality: response.character_details.personality || prev.personality,
          character_arc: response.character_details.character_arc || prev.character_arc,
          want: response.character_details.want || prev.want,
          need: response.character_details.need || prev.need,
          lie: response.character_details.lie || prev.lie,
          ghost: response.character_details.ghost || prev.ghost,
        }));

        toast.success("Character details generated! Review and edit as needed.", {
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

  const handleAddArchetype = () => {
    setShowArchetypeModal(true);
    setNewArchetypeName('');
    setArchetypeError('');
  };

  const handleConfirmAddArchetype = () => {
    const trimmedName = newArchetypeName.trim();
    
    if (!trimmedName) {
      setArchetypeError('Archetype name is required');
      return;
    }

    const currentArchetypes = editedCharacter.archetypes || character.archetypes || [];
    if (currentArchetypes.includes(trimmedName)) {
      setArchetypeError('This archetype already exists');
      return;
    }

    setEditedCharacter(prev => ({
      ...prev,
      archetypes: [...currentArchetypes, trimmedName]
    }));
    
    setShowArchetypeModal(false);
    setNewArchetypeName('');
    setArchetypeError('');
  };

  const handleCancelAddArchetype = () => {
    setShowArchetypeModal(false);
    setNewArchetypeName('');
    setArchetypeError('');
  };

  const handleArchetypeKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleConfirmAddArchetype();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleCancelAddArchetype();
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
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border dark:border-gray-700 transition-all ${
      isSelected ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20' : isEditing ? 'ring-2 ring-blue-500' : 'hover:shadow-md'
    }`}>
      {/* Image Section */}
      <div className="aspect-[3/4] relative bg-gray-100 dark:bg-gray-700 rounded-t-lg overflow-hidden">
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
          <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/30 dark:to-purple-900/30">
            <div className="text-center p-4">
              <div className="relative">
                <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-3" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Wand2 className="w-6 h-6 text-purple-500" />
                </div>
              </div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Generating Image</span>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">This may take 20-30 seconds...</p>
            </div>
          </div>
        ) : currentImage ? (
          <>
            <img
              src={currentImage.image_url}
              alt={character.name}
              className="w-full h-full object-cover transition-opacity duration-300"
            />
            
            {/* Carousel Controls */}
            {hasMultipleImages && (
                <>
                    <button 
                        onClick={handlePrevImage}
                        className="absolute left-2 top-1/2 -translate-y-1/2 p-1 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors"
                    >
                        <ChevronLeft className="w-5 h-5" />
                    </button>
                    <button 
                        onClick={handleNextImage}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors"
                    >
                        <ChevronRight className="w-5 h-5" />
                    </button>
                    <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex space-x-1.5">
                        {validImages.map((_, idx) => (
                            <div 
                                key={idx}
                                className={`w-1.5 h-1.5 rounded-full ${idx === currentImageIndex ? 'bg-white' : 'bg-white/50'}`}
                            />
                        ))}
                    </div>
                </>
            )}

            {/* Action Overlay */}
            <div className="absolute top-2 right-2 flex space-x-1">
              <button
                onClick={() => onViewImage(currentImage.image_url)}
                className="p-1.5 bg-black bg-opacity-50 text-white rounded-md hover:bg-opacity-70 transition-all"
                title="View full size"
              >
                <Eye className="w-4 h-4" />
              </button>
              
              {/* Set as Default (if not already) */}
              {currentImage.image_url !== character.image_url && (
                  <button
                    onClick={handleSetDefaultImage}
                    className="p-1.5 bg-black bg-opacity-50 text-yellow-400 rounded-md hover:bg-opacity-70 transition-all"
                    title="Set as Default Image"
                  >
                    <Star className="w-4 h-4" />
                  </button>
              )}

               {/* Delete Specific Image */}
               {validImages.length > 0 && onDeleteImage && currentImage.id !== 'legacy' && (
                  <button
                    onClick={handleDeleteCurrentImage}
                    className="p-1.5 bg-black bg-opacity-50 text-red-400 rounded-md hover:bg-opacity-70 transition-all"
                    title="Delete this image"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
              )}

              <button
                onClick={() => onRegenerateImage(character.id)}
                className="p-1.5 bg-black bg-opacity-50 text-white rounded-md hover:bg-opacity-70 transition-all"
                title="Generate New Variation"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <button
              onClick={() => onGenerateImage(character.id)}
              className="flex flex-col items-center space-y-2 text-gray-400 dark:text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              <ImageIcon className="w-12 h-12" />
              <span className="text-sm font-medium">Generate Image</span>
            </button>
          </div>
        )}
      </div>

      {/* Content Section */}
      <div className="p-4 space-y-3">
        {/* Name Field with AI Assist */}
        <div>
          {isEditing ? (
            <div className="space-y-1">
              <div className="flex gap-2">
                <input
                  ref={nameInputRef}
                  type="text"
                  value={displayValue('name') as string}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  className="flex-1 text-lg font-semibold text-gray-900 dark:text-white bg-transparent border-b-2 border-blue-500 focus:outline-none px-1"
                  placeholder="Character name"
                  disabled={isGeneratingWithAI}
                />
                {bookId && (
                  <button
                    onClick={handleAIAssist}
                    disabled={isSaving || isGeneratingWithAI || !editedCharacter.name?.trim()}
                    className="px-3 py-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-md hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 text-sm font-medium transition-all"
                    title="Use AI to generate character details based on the book"
                  >
                    {isGeneratingWithAI ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Sparkles className="w-4 h-4" />
                    )}
                    <span className="hidden sm:inline">{isGeneratingWithAI ? 'AI...' : 'AI Assist'}</span>
                  </button>
                )}
              </div>
              {bookId && (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Click AI Assist to auto-fill details from the book
                </p>
              )}
            </div>
          ) : (
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{character.name}</h3>
          )}
        </div>

        {/* Role Field - Dropdown in edit mode - Hide for Objects if not needed, or keep optional */}
        {/* Only show role for characters, or if it has a value for objects */}
        {(!isObject || displayValue('role')) && (
            <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Role</label>
            {isEditing ? (
                <select
                value={displayValue('role') as string}
                onChange={(e) => handleInputChange('role', e.target.value)}
                className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isGeneratingWithAI}
                >
                <option value="">Select role</option>
                <option value="protagonist">Protagonist</option>
                <option value="antagonist">Antagonist</option>
                <option value="supporting">Supporting</option>
                <option value="mentor">Mentor</option>
                <option value="sidekick">Sidekick</option>
                {isObject && <option value="object">Object/Item</option>}
                {isObject && <option value="location">Location</option>}
                </select>
            ) : (
                <p className="text-sm text-gray-700 dark:text-gray-300 capitalize">{character.role || 'Not specified'}</p>
            )}
            </div>
        )}

        {/* Voice and Accent Settings - Single Row */}
        {!isObject && (
          <div className="pt-2 border-t border-gray-100 dark:border-gray-700">
             <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Voice & Accent</label>
             
             <div className="grid grid-cols-2 gap-2 mb-2">
                <div>
                   <label className="block text-[10px] text-gray-400 uppercase tracking-wider mb-1">Accent</label>
                   {isEditing ? (
                      <select
                        value={displayValue('accent') as string || 'neutral'}
                        onChange={(e) => handleInputChange('accent', e.target.value)}
                        className="w-full text-xs text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        disabled={isGeneratingWithAI}
                      >
                        <option value="neutral">Neutral</option>
                        <option value="nigerian">Nigerian</option>
                        <option value="british">British</option>
                        <option value="american">American</option>
                        <option value="indian">Indian</option>
                        <option value="australian">Australian</option>
                        <option value="jamaican">Jamaican</option>
                        <option value="french">French</option>
                        <option value="german">German</option>
                      </select>
                   ) : (
                      <span className="text-xs font-medium px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-md text-gray-700 dark:text-gray-300 capitalize">
                         {character.accent || 'Neutral'}
                      </span>
                   )}
                </div>

                <div>
                   <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Voice Gender</label>
                    {isEditing ? (
                      <select
                        value={displayValue('voice_gender') as string || 'auto'}
                        onChange={(e) => handleInputChange('voice_gender', e.target.value)}
                        className="w-full text-xs text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        disabled={isGeneratingWithAI}
                      >
                        <option value="auto">Auto (Detect)</option>
                        <option value="male">Male</option>
                        <option value="female">Female</option>
                      </select>
                   ) : (
                      <span className="text-xs font-medium px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-md text-gray-700 dark:text-gray-300 capitalize">
                         {character.voice_gender || 'Auto'}
                      </span>
                   )}
                </div>
             </div>

             {/* Voice Characteristics */}
             {isEditing ? (
                <textarea
                  value={displayValue('voice_characteristics') as string || ''}
                  onChange={(e) => handleInputChange('voice_characteristics', e.target.value)}
                  className="w-full text-xs text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder-gray-400 resize-none"
                  rows={2}
                  placeholder="Voice traits (e.g., deep, raspy, warm, cheerful)..."
                  disabled={isGeneratingWithAI}
                />
             ) : character.voice_characteristics && (
                <p className="text-xs text-gray-600 dark:text-gray-400 italic">
                   "{character.voice_characteristics}"
                </p>
             )}
          </div>
        )}



        {/* Physical Description */}
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            Physical Description
          </label>
          {isEditing ? (
            <textarea
              value={displayValue('physical_description') as string}
              onChange={(e) => handleInputChange('physical_description', e.target.value)}
              className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
              placeholder="Describe appearance..."
              disabled={isGeneratingWithAI}
            />
          ) : (
            <div>
              <p className={`text-sm text-gray-700 dark:text-gray-300 ${
                !expandedSections.physical_description ? 'line-clamp-2' : ''
              }`}>
                {character.physical_description || 'Not specified'}
              </p>
              {character.physical_description && character.physical_description.length > 100 && (
                <button
                  onClick={() => toggleSection('physical_description')}
                  className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 mt-1"
                >
                  {expandedSections.physical_description ? 'Show less' : 'Show more'}
                </button>
              )}
            </div>
          )}
        </div>

        {/* Personality - Hide for Objects unless editing or present */}
        {!isObject && (
            <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Personality</label>
            {isEditing ? (
                <textarea
                value={displayValue('personality') as string}
                onChange={(e) => handleInputChange('personality', e.target.value)}
                className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={2}
                placeholder="Describe personality traits..."
                disabled={isGeneratingWithAI}
                />
            ) : (
                <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
                {character.personality || 'Not specified'}
                </p>
            )}
            </div>
        )}

        {/* Character Arc - Only show in for Characters */}
        {!isObject && (isEditing || character.character_arc) && (
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Character Arc</label>
            {isEditing ? (
              <textarea
                value={displayValue('character_arc') as string}
                onChange={(e) => handleInputChange('character_arc', e.target.value)}
                className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={2}
                placeholder="How does this character change throughout the story?"
                disabled={isGeneratingWithAI}
              />
            ) : (
              <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
                {character.character_arc}
              </p>
            )}
          </div>
        )}

        {/* Want / Need - Hide for Objects */}
        {!isObject && (isEditing || character.want || character.need) && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Want</label>
              {isEditing ? (
                <input
                  type="text"
                  value={displayValue('want') as string}
                  onChange={(e) => handleInputChange('want', e.target.value)}
                  className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="What they want"
                  disabled={isGeneratingWithAI}
                />
              ) : (
                <p className="text-sm text-gray-700 dark:text-gray-300">{character.want || '-'}</p>
              )}
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Need</label>
              {isEditing ? (
                <input
                  type="text"
                  value={displayValue('need') as string}
                  onChange={(e) => handleInputChange('need', e.target.value)}
                  className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="What they need"
                  disabled={isGeneratingWithAI}
                />
              ) : (
                <p className="text-sm text-gray-700 dark:text-gray-300">{character.need || '-'}</p>
              )}
            </div>
          </div>
        )}

        {/* Lie / Ghost - Hide for Objects */}
        {!isObject && (isEditing || character.lie || character.ghost) && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Lie They Believe</label>
              {isEditing ? (
                <input
                  type="text"
                  value={displayValue('lie') as string}
                  onChange={(e) => handleInputChange('lie', e.target.value)}
                  className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Their false belief"
                  disabled={isGeneratingWithAI}
                />
              ) : (
                <p className="text-sm text-gray-700 dark:text-gray-300">{character.lie || '-'}</p>
              )}
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Ghost (Past Trauma)</label>
              {isEditing ? (
                <input
                  type="text"
                  value={displayValue('ghost') as string}
                  onChange={(e) => handleInputChange('ghost', e.target.value)}
                  className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Their past trauma"
                  disabled={isGeneratingWithAI}
                />
              ) : (
                <p className="text-sm text-gray-700 dark:text-gray-300">{character.ghost || '-'}</p>
              )}
            </div>
          </div>
        )}

        {/* Archetypes - Hide for Objects */}
        { !isObject && ((displayArchetypes && displayArchetypes.length > 0) || isEditing) ? (
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Archetypes</label>
            <div className="flex flex-wrap gap-1">
              {displayArchetypes?.map((archetype, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center px-2 py-1 bg-purple-100 dark:bg-purple-900/50 text-purple-800 dark:text-purple-300 rounded-full text-xs"
                >
                  {archetype}
                  {isEditing && (
                    <button
                      onClick={() => handleRemoveArchetype(archetype)}
                      className="ml-1 hover:text-purple-900 dark:hover:text-purple-100"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </span>
              ))}
              {isEditing && (
                <button
                  onClick={handleAddArchetype}
                  className="inline-flex items-center px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full text-xs hover:bg-gray-200 dark:hover:bg-gray-600"
                >
                  <Plus className="w-3 h-3 mr-1" />
                  Add
                </button>
              )}
            </div>
          </div>
        ) : null}

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-3 border-t dark:border-gray-700">
          {isEditing ? (
            <div className="flex space-x-2 w-full">
              <button
                onClick={handleSave}
                disabled={isSaving || isGeneratingWithAI || !editedCharacter.name?.trim()}
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
                disabled={isSaving || isGeneratingWithAI}
                className="flex items-center justify-center space-x-1 px-3 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 disabled:bg-gray-100 dark:disabled:bg-gray-800 flex-1 text-sm"
              >
                <X className="w-4 h-4" />
                <span>Cancel</span>
              </button>
            </div>
          ) : (
            <>
              <button
                onClick={handleEditToggle}
                className="flex items-center space-x-1 px-3 py-2 text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-md transition-colors text-sm"
              >
                <Edit2 className="w-4 h-4" />
                <span>Edit</span>
              </button>
              <button
                onClick={() => onDelete(character.id, character.name)}
                className="flex items-center space-x-1 px-3 py-2 text-gray-600 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-md transition-colors text-sm"
              >
                <Trash2 className="w-4 h-4" />
                <span>Delete</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Add Archetype Modal */}
      {showArchetypeModal && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={handleCancelAddArchetype}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-2xl max-w-md w-full p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">Add Archetype</h3>
              <button
                onClick={handleCancelAddArchetype}
                className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 text-2xl font-bold"
              >
                ×
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Enter archetype name:
              </label>
              <input
                ref={archetypeInputRef}
                type="text"
                value={newArchetypeName}
                onChange={(e) => {
                  setNewArchetypeName(e.target.value);
                  setArchetypeError('');
                }}
                onKeyDown={handleArchetypeKeyDown}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Hero, Mentor, Trickster"
              />
              {archetypeError && (
                <p className="text-red-600 dark:text-red-400 text-sm mt-1">{archetypeError}</p>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleCancelAddArchetype}
                className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-xl font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAddArchetype}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-all"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Delete Image Confirmation Modal */}
      {showDeleteImageModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={(e) => e.stopPropagation()}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center flex-shrink-0">
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">Delete Image?</h3>
            </div>

            <p className="text-gray-600 dark:text-gray-300 mb-6 text-sm">
              Are you sure you want to delete this image? This action cannot be undone.
            </p>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteImageModal(false)}
                className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors text-sm font-medium"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteImage}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors shadow-sm text-sm font-medium"
              >
                Delete Image
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CharacterCard;
