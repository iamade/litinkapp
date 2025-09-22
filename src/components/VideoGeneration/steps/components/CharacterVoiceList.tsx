import React, { useState } from 'react';
import { Play, Pause, User, Volume2, Check } from 'lucide-react';
import { AudioProgress } from '../../../../lib/videoGenerationApi';

interface CharacterVoice {
  character_name: string;
  voice_type: string;
  audio_url?: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  duration?: number;
}

interface CharacterVoiceListProps {
  characters: CharacterVoice[];
  progress?: AudioProgress;
}

export const CharacterVoiceList: React.FC<CharacterVoiceListProps> = ({
  characters,
  progress
}) => {
  const [playingCharacter, setPlayingCharacter] = useState<string | null>(null);
  const [audioElements, setAudioElements] = useState<{ [key: string]: HTMLAudioElement }>({});

  const handlePlayPause = (characterName: string, audioUrl?: string) => {
    if (!audioUrl) return;

    // Stop currently playing audio
    if (playingCharacter && playingCharacter !== characterName) {
      const currentAudio = audioElements[playingCharacter];
      if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
      }
    }

    const audio = audioElements[characterName] || new Audio(audioUrl);
    
    if (!audioElements[characterName]) {
      audio.addEventListener('ended', () => setPlayingCharacter(null));
      setAudioElements(prev => ({ ...prev, [characterName]: audio }));
    }

    if (playingCharacter === characterName) {
      // Currently playing, pause it
      audio.pause();
      setPlayingCharacter(null);
    } else {
      // Start playing
      audio.play();
      setPlayingCharacter(characterName);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <Check className="w-4 h-4 text-green-500" />;
      case 'generating':
        return <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />;
      case 'failed':
        return <div className="w-4 h-4 bg-red-500 rounded-full" />;
      default:
        return <div className="w-4 h-4 bg-gray-300 rounded-full" />;
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center gap-2 mb-4">
        <User className="w-5 h-5 text-purple-600" />
        <h4 className="text-lg font-semibold text-gray-900">Character Voices</h4>
        <span className="ml-auto text-sm text-gray-500">
          {characters.filter(c => c.status === 'completed').length} of {characters.length} completed
        </span>
      </div>

      <div className="space-y-3">
        {characters.map((character, index) => (
          <div key={character.character_name} className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
            <div className="flex-shrink-0">
              {getStatusIcon(character.status)}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <h5 className="font-medium text-gray-900 truncate">
                  {character.character_name}
                </h5>
                <span className="text-xs text-gray-500 uppercase bg-gray-200 px-2 py-1 rounded-full">
                  {character.voice_type}
                </span>
              </div>
              
              {character.duration && (
                <p className="text-sm text-gray-600 mt-1">
                  Duration: {character.duration.toFixed(1)}s
                </p>
              )}
            </div>

            {/* Play Button */}
            {character.status === 'completed' && character.audio_url && (
              <button
                onClick={() => handlePlayPause(character.character_name, character.audio_url)}
                className="flex-shrink-0 p-2 rounded-full bg-blue-100 hover:bg-blue-200 transition-colors"
                title={playingCharacter === character.character_name ? 'Pause' : 'Play'}
              >
                {playingCharacter === character.character_name ? (
                  <Pause className="w-4 h-4 text-blue-600" />
                ) : (
                  <Play className="w-4 h-4 text-blue-600" />
                )}
              </button>
            )}

            {/* Progress indicator for generating */}
            {character.status === 'generating' && (
              <div className="flex-shrink-0 flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-blue-500 animate-pulse" />
                <span className="text-xs text-blue-600">Generating...</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {characters.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <User className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p>No character voices detected yet</p>
        </div>
      )}
    </div>
  );
};