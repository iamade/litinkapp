import React, { useState, useRef, useEffect } from 'react';
import { X, Play, Pause, Video, Volume2, Music, Wind, Headphones, Mic, FileText, Loader2 } from 'lucide-react';
import { VideoScene } from '../../types/videoProduction';
import { useStoryboardOptional } from '../../contexts/StoryboardContext';
import ProtectedImage from '../Common/ProtectedImage';

interface SceneDetailModalProps {
  scene: VideoScene;
  onClose: () => void;
  onGenerate: (audioId?: string) => void;
  isGenerating?: boolean;
  selectedScript?: {
    script?: string;
    scene_descriptions?: Array<{
      scene_number: number;
      visual_description?: string;
      key_actions?: string;
      location?: string;
      characters?: string[];
    }>;
  } | null;
}

type AudioType = 'dialogue' | 'narration' | 'music' | 'effects' | 'ambiance' | string;

const AUDIO_TYPE_CONFIG: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  dialogue: { label: 'Dialogue', icon: <Mic className="w-3.5 h-3.5" />, color: 'blue' },
  narration: { label: 'Narration', icon: <FileText className="w-3.5 h-3.5" />, color: 'indigo' },
  music: { label: 'Music', icon: <Music className="w-3.5 h-3.5" />, color: 'purple' },
  ambiance: { label: 'Ambiance', icon: <Wind className="w-3.5 h-3.5" />, color: 'teal' },
  effects: { label: 'Effects', icon: <Headphones className="w-3.5 h-3.5" />, color: 'orange' },
};

const COLOR_CLASSES: Record<string, { bg: string; text: string; border: string }> = {
  blue:   { bg: 'bg-blue-100 dark:bg-blue-900/30',   text: 'text-blue-700 dark:text-blue-300',   border: 'border-blue-200 dark:border-blue-800' },
  indigo: { bg: 'bg-indigo-100 dark:bg-indigo-900/30', text: 'text-indigo-700 dark:text-indigo-300', border: 'border-indigo-200 dark:border-indigo-800' },
  purple: { bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-700 dark:text-purple-300', border: 'border-purple-200 dark:border-purple-800' },
  teal:   { bg: 'bg-teal-100 dark:bg-teal-900/30',   text: 'text-teal-700 dark:text-teal-300',   border: 'border-teal-200 dark:border-teal-800' },
  orange: { bg: 'bg-orange-100 dark:bg-orange-900/30', text: 'text-orange-700 dark:text-orange-300', border: 'border-orange-200 dark:border-orange-800' },
  gray:   { bg: 'bg-gray-100 dark:bg-gray-900/30',   text: 'text-gray-600 dark:text-gray-300',   border: 'border-gray-200 dark:border-gray-700' },
};

// Priority order for auto-suggesting best audio for video generation
const AUDIO_PRIORITY: AudioType[] = ['dialogue', 'narration', 'ambiance', 'music', 'effects'];

export const SceneDetailModal: React.FC<SceneDetailModalProps> = ({
  scene,
  onClose,
  onGenerate,
  isGenerating,
  selectedScript,
}) => {
  const storyboardContext = useStoryboardOptional();
  
  // Audio state
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const audioRefs = useRef<Record<string, HTMLAudioElement>>({});
  const [selectedAudioId, setSelectedAudioId] = useState<string | null>(null);

  // Real-time duration detection: map from audioId → actual seconds
  const [detectedDurations, setDetectedDurations] = useState<Record<string, number>>({});

  const getAudioDuration = (audio: { id: string; duration?: number }) =>
    detectedDurations[audio.id] ?? audio.duration ?? 0;

  // Get all audio for this scene's sceneNumber (all shots)
  const allSceneAudio = storyboardContext?.sceneAudioMap[scene.sceneNumber] || [];

  // Group audio by type
  const audioByType = React.useMemo(() => {
    const grouped: Record<string, typeof allSceneAudio> = {};
    allSceneAudio.forEach(audio => {
      const type = audio.type || 'other';
      if (!grouped[type]) grouped[type] = [];
      grouped[type].push(audio);
    });
    return grouped;
  }, [allSceneAudio]);

  // Auto-suggest best audio: use priority order, pick first found per priority
  useEffect(() => {
    if (selectedAudioId) return; // user already selected something
    for (const type of AUDIO_PRIORITY) {
      const audioOfType = audioByType[type];
      if (audioOfType && audioOfType.length > 0) {
        setSelectedAudioId(audioOfType[0].id);
        return;
      }
    }
    // Fallback to first available audio
    if (allSceneAudio.length > 0) {
      setSelectedAudioId(allSceneAudio[0].id);
    }
  }, [audioByType, allSceneAudio, selectedAudioId]);

  // Extract scene description from script
  const sceneDescription = React.useMemo(() => {
    if (!selectedScript?.scene_descriptions) return null;
    return selectedScript.scene_descriptions.find(
      d => d.scene_number === scene.sceneNumber
    );
  }, [selectedScript, scene.sceneNumber]);

  // Extract dialogue from script text for this scene using header-key approach (mirrors ImagesPanel)
  const sceneDialogue = React.useMemo(() => {
    if (!selectedScript?.script) return [];
    const scriptLines = selectedScript.script.split('\n');
    
    // Build dialogueMoments map keyed by scene header (e.g. "ACT I - SCENE 1")
    const moments: Record<string, Array<{character: string; text: string}>> = {};
    let currentSceneKey = '';
    let currentCharacter: string | null = null;
    
    for (const rawLine of scriptLines) {
      const trimmed = rawLine.trim();
      if (!trimmed) continue;
      
      // Detect scene headers
      const sceneMatch = trimmed.match(/^(\*?\*?ACT\s+[IVX0-9]+\s*-?\s*SCENE\s+\d+(?:\.\d+)?)\*?\*?/i);
      if (sceneMatch) {
        currentSceneKey = sceneMatch[1].replace(/\*/g, '').trim().toUpperCase();
        currentCharacter = null;
        continue;
      }
      
      // Detect character names (ALL CAPS, short)
      if (
        trimmed === trimmed.toUpperCase() &&
        trimmed.length <= 30 &&
        trimmed.length > 1 &&
        !trimmed.startsWith('INT.') &&
        !trimmed.startsWith('EXT.') &&
        !trimmed.startsWith('ACT') &&
        !trimmed.startsWith('SCENE') &&
        !trimmed.startsWith('FADE') &&
        !trimmed.startsWith('CUT') &&
        !trimmed.startsWith('(') &&
        !trimmed.startsWith('*')
      ) {
        currentCharacter = trimmed.replace("(CONT'D)", '').replace('(V.O.)', '').trim();
        continue;
      }
      
      // Capture dialogue line
      if (currentCharacter && currentSceneKey && !trimmed.startsWith('(') && !trimmed.startsWith('*') && trimmed.length > 10) {
        if (!moments[currentSceneKey]) moments[currentSceneKey] = [];
        moments[currentSceneKey].push({
          character: currentCharacter,
          text: trimmed.slice(0, 80) + (trimmed.length > 80 ? '...' : ''),
        });
        currentCharacter = null;
      }
    }
    
    // Find the header key that matches this scene's number
    const matchingKey = Object.keys(moments).find(key => {
      const match = key.match(/SCENE\s+(\d+)/i);
      return match && parseInt(match[1], 10) === scene.sceneNumber;
    });
    
    return matchingKey ? moments[matchingKey] : [];
  }, [selectedScript, scene.sceneNumber]);

  const handlePlay = (id: string) => {
    if (playingAudioId === id) {
      audioRefs.current[id]?.pause();
      setPlayingAudioId(null);
    } else {
      Object.keys(audioRefs.current).forEach(key => audioRefs.current[key]?.pause());
      setPlayingAudioId(id);
      setTimeout(() => audioRefs.current[id]?.play(), 0);
    }
  };

  const selectedCount = selectedAudioId ? 1 : 0;
  
  // Validation for selected audio
  const selectedAudioItem = React.useMemo(() => 
    allSceneAudio.find(a => a.id === selectedAudioId), 
  [allSceneAudio, selectedAudioId]);

  const [isValidDuration, durationWarning, isTooShort] = React.useMemo(() => {
    if (!selectedAudioItem) return [true, '', false]; // No audio selected yet
    // Use real-time detected duration (from loadedmetadata) if available, else stored value
    const duration = getAudioDuration(selectedAudioItem);
    if (duration > 0 && duration < 5) return [false, `Audio is too short (${duration.toFixed(1)}s). ModelsLab I2V requires at least 5 seconds.`, true];
    if (duration > 28) return [false, `Audio is too long (${duration.toFixed(1)}s). Maximum supported duration is 28 seconds — the model will trim it.`, false];
    return [true, '', false];
  }, [selectedAudioItem, detectedDurations]);   // re-validate when detected durations update

  // Format duration for display
  const formatDuration = (s: number) => {
    if (!s || s <= 0) return null;
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  const getDurationColor = (s: number) => {
    if (s <= 0) return 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400';
    if (s < 5)  return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
    if (s > 28) return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300';
    return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden border border-gray-200 dark:border-gray-700">
        
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b dark:border-gray-700 shrink-0">
          <div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">
              Scene {scene.sceneNumber} Detail
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {scene.shotType === 'key_scene' ? '⭐ Key Scene' : '🎬 Suggested Shot'}
              {typeof scene.shotIndex === 'number' && ` • Shot ${scene.shotIndex + 1}`}
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 min-h-0 overflow-y-auto flex flex-col md:flex-row">

          {/* Left: Image + Scene Info */}
          <div className="w-full md:w-[55%] flex flex-col">
            {/* Image */}
            <div className="bg-black flex items-center justify-center min-h-[200px] md:min-h-[260px] p-4">
              {scene.imageUrl ? (
                <ProtectedImage
                  src={scene.imageUrl}
                  alt={`Scene ${scene.sceneNumber}`}
                  className="max-w-full max-h-[240px] object-contain shadow-lg rounded"
                />
              ) : (
                <div className="text-gray-500 text-sm">No Image Available</div>
              )}
            </div>

            {/* Scene Description */}
            <div className="p-4 border-t border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
              <h4 className="text-xs uppercase tracking-widest text-gray-500 font-semibold mb-2">Scene Description</h4>
              {sceneDescription?.visual_description ? (
                <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                  {sceneDescription.visual_description}
                </p>
              ) : scene.imageUrl ? (
                <p className="text-sm text-gray-500 italic">Visual scene — no text description available</p>
              ) : (
                <p className="text-sm text-gray-500 italic">No description available</p>
              )}
              {sceneDescription?.location && (
                <p className="text-xs text-gray-400 mt-1">📍 {sceneDescription.location}</p>
              )}
            </div>

            {/* Dialogue */}
            <div className="p-4 bg-gray-50 dark:bg-gray-800/30">
              <h4 className="text-xs uppercase tracking-widest text-gray-500 font-semibold mb-2">Dialogue</h4>
              {sceneDialogue.length > 0 ? (
                <div className="space-y-2 max-h-[140px] overflow-y-auto pr-1">
                  {sceneDialogue.map((line, idx) => (
                    <div key={idx} className="text-sm">
                      <span className="text-blue-600 dark:text-blue-400 font-semibold text-xs uppercase tracking-wide">{line.character}: </span>
                      <span className="text-gray-600 dark:text-gray-400 italic">"{line.text}"</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-400 italic">No dialogue in this scene</p>
              )}
            </div>
          </div>

          {/* Right: Audio Selection */}
          <div className="w-full md:w-[45%] flex flex-col border-l dark:border-gray-700">
            <div className="p-4 border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2 text-sm">
                  <Volume2 className="w-4 h-4" />
                  Audio Selection
                </h4>
                {/* Counter */}
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  selectedCount === 1 
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                    : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                }`}>
                  {selectedCount} of 1 selected (max 1)
                </span>
              </div>
              {selectedCount === 0 && (
                <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">Select an audio track to generate video</p>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {allSceneAudio.length === 0 ? (
                <div className="text-center py-8">
                  <Volume2 className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
                  <p className="text-sm text-gray-500 italic">No generated audio found for this scene.</p>
                  <p className="text-xs text-gray-400 mt-1">Generate audio in the Audio tab for the active script, then return here. The Video tab will load matching tracks automatically.</p>
                </div>
              ) : (
                // Render grouped by type
                AUDIO_PRIORITY.concat(
                  Object.keys(audioByType).filter(t => !AUDIO_PRIORITY.includes(t))
                ).filter(type => audioByType[type]?.length > 0).map(type => {
                  const config = AUDIO_TYPE_CONFIG[type] || { label: type, icon: <Volume2 className="w-3.5 h-3.5" />, color: 'gray' };
                  const colors = COLOR_CLASSES[config.color] || COLOR_CLASSES.gray;
                  const isSuggested = selectedAudioId && audioByType[type]?.some(a => a.id === selectedAudioId) && 
                    AUDIO_PRIORITY.indexOf(type) === AUDIO_PRIORITY.findIndex(t => audioByType[t]?.length > 0);

                  return (
                    <div key={type}>
                      {/* Group header */}
                      <div className={`flex items-center gap-2 px-2 py-1 rounded-md mb-2 ${colors.bg} ${colors.border} border`}>
                        <span className={colors.text}>{config.icon}</span>
                        <span className={`text-xs font-semibold uppercase tracking-wide ${colors.text}`}>{config.label}</span>
                        {isSuggested && (
                          <span className="ml-auto text-[10px] px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded font-medium">
                            ✨ Suggested
                          </span>
                        )}
                      </div>

                      {/* Audio items in this group */}
                      <div className="space-y-1.5 pl-1">
                        {audioByType[type].map(audio => {
                          const isSelected = selectedAudioId === audio.id;
                          const isOriginal = storyboardContext?.audioAssignments[audio.id]?.shotIndex === scene.shotIndex;

                          return (
                            <div
                              key={audio.id}
                              onClick={() => setSelectedAudioId(audio.id)}
                              className={`p-2.5 rounded-lg border cursor-pointer transition-all ${
                                isSelected
                                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-1 ring-blue-500'
                                  : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-300'
                              }`}
                            >
                              <div className="flex items-center gap-2">
                                {/* Play Button */}
                                <button
                                  onClick={e => { e.stopPropagation(); handlePlay(audio.id); }}
                                  className="shrink-0 w-7 h-7 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                                >
                                  {playingAudioId === audio.id
                                    ? <Pause className="w-3.5 h-3.5 text-gray-700 dark:text-gray-200" />
                                    : <Play className="w-3.5 h-3.5 text-gray-700 dark:text-gray-200 ml-0.5" />}
                                </button>

                                {/* Info */}
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="text-xs font-medium text-gray-800 dark:text-gray-200 truncate">
                                      {audio.character || (audio.text_content ? audio.text_content.slice(0, 30) + '...' : 'Audio')}
                                    </span>
                                    {isOriginal && (
                                      <span className="shrink-0 text-[9px] uppercase font-bold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-1 py-0.5 rounded">
                                        Assigned
                                      </span>
                                    )}
                                    {/* Duration badge */}
                                    {(() => {
                                      const dur = getAudioDuration(audio);
                                      const label = formatDuration(dur);
                                      return label ? (
                                        <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${getDurationColor(dur)}`}>
                                          ⏱ {label}
                                        </span>
                                      ) : (
                                        <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded-full font-semibold bg-gray-100 text-gray-400 dark:bg-gray-700 dark:text-gray-500">
                                          ⏱ –
                                        </span>
                                      );
                                    })()}
                                  </div>
                                  {audio.text_content && (
                                    <p className="text-[10px] text-gray-400 truncate mt-0.5">{audio.text_content}</p>
                                  )}
                                </div>

                                {/* Radio button */}
                                <div className={`shrink-0 w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                                  isSelected ? 'bg-blue-500 border-blue-500' : 'border-gray-300 dark:border-gray-600'
                                }`}>
                                  {isSelected && <div className="w-1.5 h-1.5 bg-white rounded-full" />}
                                </div>

                                <audio
                                  ref={el => {
                                    if (el) {
                                      audioRefs.current[audio.id] = el;
                                      // Detect real duration from audio metadata
                                      el.onloadedmetadata = () => {
                                        if (el.duration && isFinite(el.duration) && el.duration > 0) {
                                          setDetectedDurations(prev => ({ ...prev, [audio.id]: el.duration }));
                                        }
                                      };
                                    }
                                  }}
                                  src={audio.url}
                                  preload="metadata"
                                  onEnded={() => setPlayingAudioId(null)}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Footer: Generate button */}
            <div className="p-4 border-t dark:border-gray-700 bg-white dark:bg-gray-900 shrink-0">
              <button
                onClick={() => onGenerate(selectedAudioId || undefined)}
                disabled={isGenerating || !selectedAudioId || isTooShort}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors shadow-sm"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Generating Video...</span>
                  </>
                ) : (
                  <>
                    <Video className="w-5 h-5" />
                    <span>Generate Video for Scene</span>
                  </>
                )}
              </button>
              
              {!selectedAudioId && !isGenerating && (
                <p className="text-xs text-center text-amber-600 dark:text-amber-400 mt-2">
                  Select an audio track above to enable generation
                </p>
              )}
              {selectedAudioId && !isValidDuration && !isGenerating && (
                <p className="text-xs text-center text-red-600 dark:text-red-400 mt-2 font-medium bg-red-50 dark:bg-red-900/20 py-1.5 px-2 rounded">
                  ⚠️ {durationWarning}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
