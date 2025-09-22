import React, { useState } from 'react';
import { Play, Pause, Download, Mic, Music, Volume2 } from 'lucide-react';
import { AudioFiles } from '../../../../lib/videoGenerationApi';

interface AudioFilesPreviewProps {
  audioFiles: AudioFiles;
  isGenerating: boolean;
}

interface AudioFile {
  name: string;
  url: string;
  duration?: number;
  type: 'narrator' | 'character' | 'sound_effect' | 'background_music';
  character_name?: string;
}

export const AudioFilesPreview: React.FC<AudioFilesPreviewProps> = ({
  audioFiles,
  isGenerating
}) => {
  const [playingFile, setPlayingFile] = useState<string | null>(null);
  const [audioElements, setAudioElements] = useState<{ [key: string]: HTMLAudioElement }>({});

  // Flatten all audio files into a single array
  const allAudioFiles: AudioFile[] = [
    ...audioFiles.narrator.map(file => ({ ...file, type: 'narrator' as const })),
    ...audioFiles.characters.map(file => ({ ...file, type: 'character' as const })),
    ...audioFiles.sound_effects.map(file => ({ ...file, type: 'sound_effect' as const })),
    ...audioFiles.background_music.map(file => ({ ...file, type: 'background_music' as const }))
  ];

  const handlePlayPause = (fileName: string, audioUrl: string) => {
    // Stop currently playing audio
    if (playingFile && playingFile !== fileName) {
      const currentAudio = audioElements[playingFile];
      if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
      }
    }

    const audio = audioElements[fileName] || new Audio(audioUrl);
    
    if (!audioElements[fileName]) {
      audio.addEventListener('ended', () => setPlayingFile(null));
      setAudioElements(prev => ({ ...prev, [fileName]: audio }));
    }

    if (playingFile === fileName) {
      audio.pause();
      setPlayingFile(null);
    } else {
      audio.play();
      setPlayingFile(fileName);
    }
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'narrator':
        return <Mic className="w-4 h-4 text-blue-500" />;
      case 'character':
        return <Volume2 className="w-4 h-4 text-purple-500" />;
      case 'sound_effect':
        return <Volume2 className="w-4 h-4 text-green-500" />;
      case 'background_music':
        return <Music className="w-4 h-4 text-orange-500" />;
      default:
        return <Volume2 className="w-4 h-4 text-gray-500" />;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'narrator':
        return 'Narrator';
      case 'character':
        return 'Character';
      case 'sound_effect':
        return 'Sound Effect';
      case 'background_music':
        return 'Background Music';
      default:
        return 'Audio';
    }
  };

  if (allAudioFiles.length === 0 && !isGenerating) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="text-center py-8 text-gray-500">
          <Volume2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p>No audio files available yet</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-lg font-semibold text-gray-900">Audio Files Preview</h4>
        <span className="text-sm text-gray-500">
          {allAudioFiles.length} file{allAudioFiles.length !== 1 ? 's' : ''}
        </span>
      </div>

      {isGenerating && allAudioFiles.length === 0 && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Generating audio files...</p>
        </div>
      )}

      <div className="space-y-3">
        {allAudioFiles.map((file, index) => (
          <div key={`${file.type}-${index}`} className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
            <div className="flex-shrink-0">
              {getFileIcon(file.type)}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h5 className="font-medium text-gray-900 truncate">
                  {file.character_name || file.name}
                </h5>
                <span className="text-xs text-gray-500 uppercase bg-gray-200 px-2 py-1 rounded-full">
                  {getTypeLabel(file.type)}
                </span>
              </div>
              
              {file.duration && (
                <p className="text-sm text-gray-600 mt-1">
                  Duration: {file.duration.toFixed(1)}s
                </p>
              )}
            </div>

            <div className="flex items-center gap-2">
              {/* Play/Pause Button */}
              <button
                onClick={() => handlePlayPause(`${file.type}-${index}`, file.url)}
                className="p-2 rounded-full bg-white border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition-colors"
                title={playingFile === `${file.type}-${index}` ? 'Pause' : 'Play'}
              >
                {playingFile === `${file.type}-${index}` ? (
                  <Pause className="w-4 h-4 text-blue-600" />
                ) : (
                  <Play className="w-4 h-4 text-gray-600" />
                )}
              </button>

              {/* Download Button */}
              <a
                href={file.url}
                download={file.name}
                className="p-2 rounded-full bg-white border border-gray-200 hover:bg-green-50 hover:border-green-200 transition-colors"
                title="Download"
              >
                <Download className="w-4 h-4 text-gray-600" />
              </a>
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      {allAudioFiles.length > 0 && (
        <div className="mt-6 pt-4 border-t border-gray-200">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-lg font-semibold text-blue-600">{audioFiles.narrator.length}</div>
              <div className="text-xs text-gray-500">Narrator</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-purple-600">{audioFiles.characters.length}</div>
              <div className="text-xs text-gray-500">Characters</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-green-600">{audioFiles.sound_effects.length}</div>
              <div className="text-xs text-gray-500">Sound Effects</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-orange-600">{audioFiles.background_music.length}</div>
              <div className="text-xs text-gray-500">Music</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};