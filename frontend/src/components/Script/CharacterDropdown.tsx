import React, { useState, useEffect, useRef } from 'react';
import { Check, User, Box, MapPin } from 'lucide-react';

export interface PlotCharacter {
  id: string;
  name: string;
  role?: string;
  physical_description?: string;
  personality?: string;
  image_url?: string;
  entity_type?: 'character' | 'object' | 'location';
}

interface CharacterDropdownProps {
  value: string;  // Current character name being edited
  plotCharacters: PlotCharacter[];
  linkedCharacterId?: string;  // If already linked to a plot character
  onSelect: (character: PlotCharacter) => void;
  onCreateNew: (name: string, entityType: 'character' | 'object' | 'location') => void;
  onCancel: () => void;
  autoFocus?: boolean;
}

const CharacterDropdown: React.FC<CharacterDropdownProps> = ({
  value,
  plotCharacters,
  linkedCharacterId,
  onSelect,
  onCreateNew,
  onCancel,
  autoFocus = true
}) => {
  const [searchText, setSearchText] = useState(value);
  // showDropdown state removed as it was unused (always true)
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Filter characters based on search text
  const filteredCharacters = plotCharacters.filter(char =>
    char.name.toLowerCase().includes(searchText.toLowerCase())
  );

  // Check if exact match exists
  const exactMatch = plotCharacters.find(
    char => char.name.toLowerCase() === searchText.toLowerCase()
  );

  // Find currently linked character
  const linkedCharacter = linkedCharacterId 
    ? plotCharacters.find(c => c.id === linkedCharacterId)
    : null;

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [autoFocus]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        onCancel();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onCancel]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onCancel();
    } else if (e.key === 'Enter' && exactMatch) {
      onSelect(exactMatch);
    }
  };

  return (
    <div ref={dropdownRef} className="relative z-50">
      {/* Input field */}
      <div className="flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/50 rounded-full">
        <input
          ref={inputRef}
          type="text"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          onKeyDown={handleKeyDown}
          className="w-36 px-2 py-0.5 text-sm rounded border border-blue-300 dark:border-blue-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
          placeholder="Type to search..."
        />
        <button
          onClick={onCancel}
          className="p-0.5 hover:bg-red-200 dark:hover:bg-red-800 rounded text-red-600 dark:text-red-400"
        >
          ×
        </button>
      </div>

      {/* Dropdown */}
      <div className="absolute top-full left-0 mt-1 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-64 overflow-y-auto">
          {/* Currently linked indicator */}
          {linkedCharacter && (
            <div className="px-3 py-2 bg-green-50 dark:bg-green-900/30 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 text-xs text-green-700 dark:text-green-400">
                <Check className="w-3 h-3" />
                <span>Linked to: {linkedCharacter.name}</span>
              </div>
            </div>
          )}

          {/* Filtered results */}
          {filteredCharacters.length > 0 ? (
            <div className="py-1">
              <div className="px-3 py-1 text-xs text-gray-500 dark:text-gray-400 font-medium">
                Plot Characters
              </div>
              {filteredCharacters.map((char) => (
                <button
                  key={char.id}
                  onClick={() => onSelect(char)}
                  className="w-full px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                >
                  {char.image_url ? (
                    <img 
                      src={char.image_url} 
                      alt={char.name}
                      className="w-6 h-6 rounded-full object-cover"
                    />
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
                      {char.entity_type === 'location' ? (
                        <MapPin className="w-3 h-3 text-gray-500" />
                      ) : char.entity_type === 'object' ? (
                        <Box className="w-3 h-3 text-gray-500" />
                      ) : (
                        <User className="w-3 h-3 text-gray-500" />
                      )}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {char.name}
                    </div>
                    {char.role && (
                      <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {char.role}
                      </div>
                    )}
                  </div>
                  {char.image_url && (
                    <span className="text-xs text-green-600 dark:text-green-400">✓ has image</span>
                  )}
                  {char.id === linkedCharacterId && (
                    <Check className="w-4 h-4 text-green-600" />
                  )}
                </button>
              ))}
            </div>
          ) : (
            <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
              No matching characters found
            </div>
          )}

  
          {searchText.trim() && !exactMatch && (
            <div className="p-2 border-t border-gray-100 dark:border-gray-700">
               <div className="text-xs text-gray-500 mb-2 px-2">Create "{searchText.trim()}" as:</div>
               <div className="flex flex-col gap-1">
                 <button
                    onClick={() => onCreateNew(searchText.trim(), 'character')}
                    className="flex items-center gap-2 w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md"
                 >
                    <User className="w-4 h-4" />
                    <span>Character</span>
                 </button>
                 <button
                    onClick={() => onCreateNew(searchText.trim(), 'object')}
                    className="flex items-center gap-2 w-full text-left px-3 py-2 text-sm text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-md"
                 >
                    <Box className="w-4 h-4" />
                    <span>Object</span>
                 </button>
                  <button
                    onClick={() => onCreateNew(searchText.trim(), 'location')}
                    className="flex items-center gap-2 w-full text-left px-3 py-2 text-sm text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-md"
                 >
                    <MapPin className="w-4 h-4" />
                    <span>Location</span>
                 </button>
               </div>
            </div>
          )}
        </div>
      </div>
  );
};

export default CharacterDropdown;
