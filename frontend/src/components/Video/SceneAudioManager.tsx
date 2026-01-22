import React from 'react';
import { X, Play, Pause, Check } from 'lucide-react';
import { useStoryboard } from '../../contexts/StoryboardContext';
import { VideoScene } from '../../types/videoProduction';

interface SceneAudioManagerProps {
  sceneNumber: number;
  availableShots: VideoScene[]; // All scene objects for this scene # (Key + Suggested)
  onClose: () => void;
}

export const SceneAudioManager: React.FC<SceneAudioManagerProps> = ({
  sceneNumber,
  availableShots,
  onClose,
}) => {
  const { 
    sceneAudioMap, 
    audioAssignments,
    toggleAudioSelection, 
    isAudioSelected,
    assignAudioToShot
  } = useStoryboard();

  const [playingId, setPlayingId] = React.useState<string | null>(null);
  const audioRefs = React.useRef<Record<string, HTMLAudioElement>>({});

  const audioFiles = sceneAudioMap[sceneNumber] || [];

  // Sort audio: assigned ones first? or just by creation?
  // Let's sort by current shot index assignment to group them visually
  const sortedAudio = [...audioFiles].sort((a, b) => {
    const shotA = audioAssignments[a.id]?.shotIndex ?? a.shotIndex ?? 0;
    const shotB = audioAssignments[b.id]?.shotIndex ?? b.shotIndex ?? 0;
    return shotA - shotB;
  });

  const getEffectiveShotIndex = (audioId: string, defaultIndex: number) => {
    return audioAssignments[audioId]?.shotIndex ?? defaultIndex ?? 0;
  };

  const handlePlay = (id: string) => {
    if (playingId === id) {
      audioRefs.current[id]?.pause();
      setPlayingId(null);
    } else {
      // Stop others
      Object.keys(audioRefs.current).forEach(key => {
        if (key !== id) audioRefs.current[key]?.pause();
      });
      if (audioRefs.current[id]) {
        audioRefs.current[id].play();
        setPlayingId(id);
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900">
            Manage Audio - Scene {sceneNumber}
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-full">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="bg-blue-50 text-blue-800 text-sm p-3 rounded-md mb-4">
             Select audio files to include in generation and assign them to specific shots.
          </div>

          {!audioFiles.length && (
            <div className="text-center py-8 text-gray-500">
              No audio files found for this scene.
            </div>
          )}

          {sortedAudio.map(audio => {
            const currentShotIndex = getEffectiveShotIndex(audio.id, audio.shotIndex || 0);
            const isSelected = isAudioSelected(audio.id);

            return (
              <div key={audio.id} className={`flex items-center p-3 rounded-lg border ${isSelected ? 'border-blue-300 bg-blue-50/30' : 'border-gray-200 hover:border-blue-300'}`}>
                {/* Selection Checkbox */}
                <div className="mr-4">
                  <button
                    onClick={() => toggleAudioSelection(audio.id)}
                    className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                      isSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-400 bg-white'
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5 text-white" />}
                  </button>
                </div>

                {/* Play Button */}
                <button
                  onClick={() => handlePlay(audio.id)}
                  className="w-8 h-8 flex-shrink-0 bg-gray-200 rounded-full flex items-center justify-center hover:bg-blue-100 mr-3"
                >
                  {playingId === audio.id ? (
                    <Pause className="w-4 h-4 text-gray-700" />
                  ) : (
                    <Play className="w-4 h-4 text-gray-700 ml-0.5" />
                  )}
                </button>
                <audio
                  ref={el => { if (el) audioRefs.current[audio.id] = el; }}
                  src={audio.url}
                  onEnded={() => setPlayingId(null)}
                  className="hidden"
                />

                {/* Info */}
                <div className="flex-1 min-w-0 mr-4">
                  <div className="font-medium text-sm text-gray-900 truncate">
                    {audio.text_content || audio.character || "Unknown Audio"}
                  </div>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-xs text-gray-500 capitalize px-2 py-0.5 bg-gray-100 rounded">
                      {audio.type}
                    </span>
                    <span className="text-xs text-gray-400">
                      {audio.duration ? `${audio.duration.toFixed(1)}s` : ''}
                    </span>
                  </div>
                </div>

                {/* Shot Assignment Dropdown */}
                <div className="flex-shrink-0">
                  <select
                    value={currentShotIndex}
                    onChange={(e) => assignAudioToShot(audio.id, sceneNumber, parseInt(e.target.value))}
                    className="text-sm border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 py-1.5 pl-3 pr-8"
                  >
                    {availableShots.map((shot) => (
                      <option key={shot.id} value={shot.shotIndex ?? 0}>
                         {shot.shotType === 'key_scene' ? 'Key Scene' : `Shot ${(shot.shotIndex ?? 0) + 1}`}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
