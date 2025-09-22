import React from 'react';
import { Mic, Play, Pause, Volume2, Music, AlertCircle } from 'lucide-react';
import { useVideoGeneration } from '../../../contexts/VideoGenerationContext';
import { AudioProgressCard } from './components/AudioProgressCard';
import { CharacterVoiceList } from './components/CharacterVoiceList';
import { AudioFilesPreview } from './components/AudioFilesPreview';

export const AudioGenerationStep: React.FC = () => {
  const { state } = useVideoGeneration();
  const generation = state.currentGeneration;
  const audioProgress = generation?.audio_progress;

  if (!generation) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading audio generation status...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Mic className="w-8 h-8 text-blue-600" />
          <h3 className="text-2xl font-bold text-gray-900">Audio Generation</h3>
        </div>
        <p className="text-gray-600">
          Creating narrator voices, character dialogue, and sound effects
        </p>
      </div>

      {/* Audio Progress Overview */}
      <AudioProgressCard 
        progress={audioProgress} 
        status={generation.generation_status}
        error={generation.error_message}
      />

      {/* Character Voices */}
      {generation.audio_files?.characters && generation.audio_files.characters.length > 0 && (
        <CharacterVoiceList 
          characters={generation.audio_files.characters}
          progress={audioProgress}
        />
      )}

      {/* Audio Files Preview */}
      {generation.audio_files && (
        <AudioFilesPreview 
          audioFiles={generation.audio_files}
          isGenerating={generation.generation_status === 'generating_audio'}
        />
      )}

      {/* Status Message */}
      <div className="text-center py-4">
        {generation.generation_status === 'generating_audio' ? (
          <div className="flex items-center justify-center gap-2 text-blue-600">
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
            <span className="text-sm">Generating audio files... This may take a few minutes</span>
          </div>
        ) : generation.generation_status === 'audio_completed' ? (
          <div className="flex items-center justify-center gap-2 text-green-600">
            <Volume2 className="w-4 h-4" />
            <span className="text-sm font-medium">Audio generation completed!</span>
          </div>
        ) : null}
      </div>
    </div>
  );
};