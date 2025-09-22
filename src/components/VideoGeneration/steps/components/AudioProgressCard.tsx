import React from 'react';
import { Mic, User, Music, Volume2, AlertTriangle } from 'lucide-react';
import { AudioProgress, GenerationStatus } from '../../../../lib/videoGenerationApi';

interface AudioProgressCardProps {
  progress?: AudioProgress;
  status: GenerationStatus;
  error?: string | null;
}

export const AudioProgressCard: React.FC<AudioProgressCardProps> = ({
  progress,
  status,
  error
}) => {
  if (!progress) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-center p-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Preparing audio generation...</span>
        </div>
      </div>
    );
  }

  const totalFiles = progress.narrator_files + progress.character_files + 
                    progress.sound_effects + progress.background_music;

  const audioTypes = [
    {
      label: 'Narrator Voice',
      count: progress.narrator_files,
      icon: <Mic className="w-5 h-5 text-blue-500" />,
      color: 'blue'
    },
    {
      label: 'Character Voices',
      count: progress.character_files,
      icon: <User className="w-5 h-5 text-purple-500" />,
      color: 'purple'
    },
    {
      label: 'Sound Effects',
      count: progress.sound_effects,
      icon: <Volume2 className="w-5 h-5 text-green-500" />,
      color: 'green'
    },
    {
      label: 'Background Music',
      count: progress.background_music,
      icon: <Music className="w-5 h-5 text-orange-500" />,
      color: 'orange'
    }
  ];

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h4 className="text-lg font-semibold text-gray-900">Audio Generation Progress</h4>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">{totalFiles}</div>
          <div className="text-sm text-gray-500">Files Generated</div>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
          <div>
            <div className="text-red-800 font-medium text-sm">Audio Generation Error</div>
            <div className="text-red-700 text-sm mt-1">{error}</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {audioTypes.map((type) => (
          <div key={type.label} className="text-center">
            <div className={`w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center bg-${type.color}-50 border-2 border-${type.color}-100`}>
              {type.icon}
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">{type.count}</div>
            <div className="text-sm text-gray-600">{type.label}</div>
            
            {/* Progress indicator */}
            {status === 'generating_audio' && type.count > 0 && (
              <div className="mt-2">
                <div className="w-full bg-gray-200 rounded-full h-1">
                  <div className={`bg-${type.color}-500 h-1 rounded-full animate-pulse`} style={{ width: '60%' }} />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Overall Progress */}
      {status === 'generating_audio' && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Overall Audio Progress</span>
            <span className="text-sm text-gray-600">Processing...</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full animate-pulse" style={{ width: '45%' }} />
          </div>
        </div>
      )}
    </div>
  );
};