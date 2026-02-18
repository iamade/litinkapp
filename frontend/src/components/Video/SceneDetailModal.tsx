import React, { useState, useRef, useEffect } from 'react';
import { X, Play, Pause, Check, Video, Volume2 } from 'lucide-react';
import { VideoScene } from '../../types/videoProduction';
import { useStoryboardOptional } from '../../contexts/StoryboardContext';

interface SceneDetailModalProps {
  scene: VideoScene;
  onClose: () => void;
  onGenerate: (audioId?: string) => void;
  isGenerating?: boolean;
}

export const SceneDetailModal: React.FC<SceneDetailModalProps> = ({
  scene,
  onClose,
  onGenerate,
  isGenerating
}) => {
  const storyboardContext = useStoryboardOptional();
  
  // Audio state
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const audioRefs = useRef<Record<string, HTMLAudioElement>>({});
  const [selectedAudioId, setSelectedAudioId] = useState<string | null>(null);

  // Get all audio for this scene number
  const allSceneAudio = storyboardContext?.sceneAudioMap[scene.sceneNumber] || [];
  
  // "Original" audio = Audio assigned to this specific shot index
  // If no specific assignment, it might be based on order or default
  // We'll use the getAudioForShot logic here if possible, or filter manually
  const originalAudio = allSceneAudio.filter(audio => {
     const assignedShotIndex = storyboardContext?.audioAssignments[audio.id]?.shotIndex;
     // If assigned explicitly to this shot
     if (assignedShotIndex === scene.shotIndex) return true;
     // If not assigned explicitly, but matches default order (fallback logic if needed)
     return false; 
  });
  // Note: getAudioForShot in context might be better source if available publicly
  // but we can filter `allSceneAudio` based on `audioAssignments` from context.

  // "Managed" audio = All other audio for this scene (or just all audio to allow switching)
  // The user wants to "override" it, so listing ALL audio for the scene seems best.
  
  // Auto-select the first "original" audio if available and nothing else selected
  useEffect(() => {
    // If we have original audio and haven't selected anything yet
    if (originalAudio.length > 0 && !selectedAudioId) {
        // Default to the first one? Or leave null to mean "use default"?
        // User said: "have a chance to override it by selecting an audio in the managed audio"
        // This implies there's a default. Let's select the first original audio by default.
        setSelectedAudioId(originalAudio[0].id);
    }
  }, [originalAudio, selectedAudioId]);

  // ...
  const handlePlay = (id: string, _url: string) => { // Rename to _url or just remove if not needed
    if (playingAudioId === id) {
      audioRefs.current[id]?.pause();
      setPlayingAudioId(null);
    } else {
      // Stop others
      Object.keys(audioRefs.current).forEach(key => {
         audioRefs.current[key]?.pause();
      });
      
      setPlayingAudioId(id);
      // We might need to handle play promise here
      setTimeout(() => audioRefs.current[id]?.play(), 0);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden border border-gray-200 dark:border-gray-700">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
            <div>
                <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                    Scene {scene.sceneNumber} Detail
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                    {scene.shotType === 'key_scene' ? 'Key Scene' : 'Suggested Shot'} • Shot {typeof scene.shotIndex === 'number' ? scene.shotIndex + 1 : 1}
                </p>
            </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors">
            <X className="w-6 h-6 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto flex flex-col md:flex-row">
            {/* Left: Image Preview (Expanded) */}
            <div className="w-full md:w-2/3 bg-black flex items-center justify-center p-4 relative min-h-[300px]">
                {scene.imageUrl ? (
                    <img 
                        src={scene.imageUrl} 
                        alt={`Scene ${scene.sceneNumber}`}
                        className="max-w-full max-h-[60vh] object-contain shadow-lg rounded"
                    />
                ) : (
                    <div className="text-gray-500">No Image Available</div>
                )}
            </div>

            {/* Right: Audio & Controls */}
            <div className="w-full md:w-1/3 border-l dark:border-gray-700 flex flex-col bg-gray-50 dark:bg-gray-800/50">
                <div className="p-4 flex-1 overflow-y-auto">
                    <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
                        <Volume2 className="w-4 h-4" />
                        Audio Selection
                    </h4>

                    {/* Classification: Original vs Others */}
                    {allSceneAudio.length === 0 ? (
                        <p className="text-sm text-gray-500 italic">No audio available for this scene.</p>
                    ) : (
                        <div className="space-y-4">
                            {/* List ALL Scene Audio with "Original" badge for assigned ones */}
                            <div className="space-y-2">
                                {allSceneAudio.map(audio => {
                                    const isOriginal = storyboardContext?.audioAssignments[audio.id]?.shotIndex === scene.shotIndex;
                                    const isSelected = selectedAudioId === audio.id;

                                    return (
                                        <div 
                                            key={audio.id}
                                            onClick={() => setSelectedAudioId(audio.id)}
                                            className={`p-3 rounded-lg border cursor-pointer transition-all ${
                                                isSelected 
                                                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-1 ring-blue-500' 
                                                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-300'
                                            }`}
                                        >
                                            <div className="flex items-start gap-3">
                                                {/* Play Button */}
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handlePlay(audio.id, audio.url);
                                                    }}
                                                    className="shrink-0 w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                                                >
                                                    {playingAudioId === audio.id ? (
                                                        <Pause className="w-4 h-4 text-gray-700 dark:text-gray-200" />
                                                    ) : (
                                                        <Play className="w-4 h-4 text-gray-700 dark:text-gray-200 ml-0.5" />
                                                    )}
                                                </button>
                                                
                                                {/* Audio Details */}
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate block">
                                                            {audio.character || "Voiceover"}
                                                        </span>
                                                        {isOriginal && (
                                                            <span className="text-[10px] uppercase font-bold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-1.5 py-0.5 rounded">
                                                                Original
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                                                        {audio.text_content || "No text content"}
                                                    </p>
                                                    <div className="mt-1 flex items-center gap-2 text-[10px] text-gray-400">
                                                        <span>{audio.duration?.toFixed(1)}s</span>
                                                        <span>•</span>
                                                        <span className="capitalize">{audio.type}</span>
                                                    </div>
                                                </div>

                                                {/* Selection Indicator */}
                                                <div className={`w-5 h-5 rounded-full border flex items-center justify-center ${
                                                    isSelected 
                                                        ? 'bg-blue-500 border-blue-500' 
                                                        : 'border-gray-300 dark:border-gray-600'
                                                }`}>
                                                    {isSelected && <Check className="w-3 h-3 text-white" />}
                                                </div>
                                            </div>
                                            <audio
                                                ref={el => { if (el) audioRefs.current[audio.id] = el; }}
                                                src={audio.url}
                                                onEnded={() => setPlayingAudioId(null)}
                                            />
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer Actions */}
                <div className="p-4 border-t dark:border-gray-700 bg-white dark:bg-gray-900">
                    <button
                        onClick={() => onGenerate(selectedAudioId || undefined)}
                        disabled={isGenerating || !selectedAudioId}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors shadow-sm"
                    >
                        {isGenerating ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                <span>Generating...</span>
                            </>
                        ) : (
                            <>
                                <Video className="w-5 h-5" />
                                <span>Generate Video for Scene</span>
                            </>
                        )}
                    </button>
                    {!selectedAudioId && (
                        <p className="text-xs text-center text-red-500 mt-2">
                            Please select an audio track to generate video.
                        </p>
                    )}
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};
