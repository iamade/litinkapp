// Migration Note: Legacy AudioAssets interface removed. 
// Now using normalized audio file arrays with scriptId property for consistent filtering.
import React, { useState, useEffect, useRef } from 'react';
import {
  Music,
  Volume2,
  Headphones,
  Wind,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Download,
  Trash2,
  Settings,
  Layers,
  Wand2,
  Loader2,
  VolumeX,
  Volume1,
  Mic,
  Clapperboard
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useAudioGeneration, type AudioFile } from '../../hooks/useAudioGeneration';
import { useImageGeneration } from '../../hooks/useImageGeneration';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';

import AudioTimeline from './AudioTimeline';
import { AudioGenerationModal } from './AudioGenerationModal';
import AudioStoryboardSceneRow from './AudioStoryboardSceneRow';
import SceneGalleryModal from './SceneGalleryModal';
import { deleteAudio } from '../../lib/api';
import { projectService } from '../../services/projectService';
import { useStoryboardOptional } from '../../contexts/StoryboardContext';

interface AudioPanelProps {
  // Props are now optional since we use context for script selection
  chapterId?: string;
  chapterTitle?: string;
  selectedScript?: {
    script_style?: string;
    scene_descriptions?: any[];
    characters?: string[];
    script?: string;
    emotional_map?: any[];
  } | null;
  plotOverview?: unknown;
}

const AudioPanel: React.FC<AudioPanelProps> = ({
  chapterTitle,
  selectedScript
}) => {
  // Safe fallback for exportAudioMix to prevent ReferenceError
  const exportAudioMix = React.useCallback(() => {
  }, []);
  // Use script selection context for global state management
  const {
    selectedScriptId,
    stableSelectedChapterId,
    selectedSegmentId,
    versionToken,
    selectedSceneImages,
    setSelectedSceneImage,
    // NEW: Storyboard configuration
    keySceneImages,
    deselectedImages,
    imageOrderByScene,
    loadStoryboardConfig,
  } = useScriptSelection();

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const prevIsGeneratingRef = useRef(false);  // Track previous isGenerating value
  const [activeTab, setActiveTab] = useState<'scenes' | 'narration' | 'music' | 'effects' | 'ambiance' | 'timeline'>('scenes');
  const [showSettings, setShowSettings] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration] = useState(0);
  const [videoGenerationId, setVideoGenerationId] = useState<string | null>(null);
  const [generatingScenesAudio, setGeneratingScenesAudio] = useState<Set<number>>(new Set());
  
  const [generationOptions, setGenerationOptions] = useState({
    voiceModel: selectedScript?.script_style === 'cinematic' ? 'elevenlabs_conversational' : 'elevenlabs_narrator',
    musicStyle: 'cinematic',
    effectsIntensity: 'moderate' as 'subtle' | 'moderate' | 'dramatic',
    ambianceType: 'natural',
    audioQuality: 'high' as 'standard' | 'high' | 'premium',
    generateNarration: selectedScript?.script_style !== 'cinematic',
    generateMusic: true,
    generateEffects: true,
    generateAmbiance: true,
    characterVoices: {} as Record<string, string> // Map character names to voice models
  });

  const [showGenerationModal, setShowGenerationModal] = useState(false);

  // Fallback parser if scene_descriptions is missing or incomplete
  const parseScriptScenes = (scriptText: string): string[] => {
    if (!scriptText) return [];
    
    // Split by common scene headers (e.g. **ACT I - SCENE 1**, INT., EXT.)
    // This is a simplified parser to ensure we get *something* for the UI
    const lines = scriptText.split('\n');
    const extractedScenes: string[] = [];
    let currentBuffer: string[] = [];
    
    // Regex to detect scene start
    // Matches: **ACT I - SCENE 1**, SCENE 1, ACT 1 SCENE 1, SCENE 1.1, SCENE 1.2
    const sceneStartRegex = /^(?:\*\*)?(?:ACT\s+[IVX\d]+\s*[-–]\s*)?SCENE\s+\d+(?:\.\d+)?(?:[-–].*)?(?:\*\*)?/i;
    
    lines.forEach((line) => {
        const trimmed = line.trim();
        const isSceneHeader = sceneStartRegex.test(trimmed);
        
        // If we hit a new explicit scene header, push previous buffer
        if (isSceneHeader) {
            if (currentBuffer.length > 0) {
                // Join buffer and clean up
                const sceneText = currentBuffer.join('\n').trim();
                // Avoid empty scenes or just title scenes
                if (sceneText.length > 20) extractedScenes.push(sceneText);
            }
            currentBuffer = [line]; // Start new buffer with header
        } else {
            currentBuffer.push(line);
        }
    });
    
    // Push last buffer
    if (currentBuffer.length > 0) {
        const sceneText = currentBuffer.join('\n').trim();
        if (sceneText.length > 10) extractedScenes.push(sceneText);
    }
    
    return extractedScenes;
  };
  
  // Use scene_descriptions if valid/complete, otherwise fallback to parsing script
  const scenes = React.useMemo(() => {
    const fromMeta = selectedScript?.scene_descriptions || [];
    // If metadata seems suspiciously short relative to script length, try parsing
    if (selectedScript?.script && (fromMeta.length <= 1 && selectedScript.script.length > 500)) {
        // Fallback to parsing script text if scene metadata is incomplete
        const parsed = parseScriptScenes(selectedScript.script);
        if (parsed.length > fromMeta.length) return parsed;
    }
    return fromMeta;
  }, [selectedScript]);

  const {
    files,
    isGenerating,
    loadAudio,
    reassignAudio,
  } = useAudioGeneration({
    chapterId: stableSelectedChapterId,
    scriptId: selectedScriptId,
    versionToken,
    videoGenerationId,
  });

  const {
    sceneImages,
    loadImages,
  } = useImageGeneration(stableSelectedChapterId, selectedScriptId, scenes);

  // Load images when entering component or scenes update
  useEffect(() => {
    if (selectedScriptId) {
       // We can load images securely using just the script ID now that the backend supports it/we have fallback
      loadImages();
    }
  }, [stableSelectedChapterId, selectedScriptId, scenes, loadImages]);

  // Local selection state for audio file cards
  const [selectedAudioFiles, setSelectedAudioFiles] = useState<Set<string>>(new Set());

  // Gallery Modal State
  const [galleryState, setGalleryState] = useState<{
    isOpen: boolean;
    sceneIndex: number;
    initialImageIndex: number;
  }>({ isOpen: false, sceneIndex: -1, initialImageIndex: 0 });

  const openGallery = (sceneIndex: number, imageIndex: number = 0) => {
    setGalleryState({ isOpen: true, sceneIndex, initialImageIndex: imageIndex });
  };

  const closeGallery = () => {
    setGalleryState(prev => ({ ...prev, isOpen: false }));
  };

  // Helper function to compute seek start time
  const computeSeekStart = (): number => {
    // TODO: Implement using available segment/chapter metadata
    // For now, return 0 as default
    return 0;
  };

  // Sync state to StoryboardContext for Video tab consumption
  // NOTE: Audio tab ONLY syncs audio files - images come from Images tab storyboard
  const storyboardContext = useStoryboardOptional();

  // Sync audio files to context when they update
  // Using ref to track previous state and avoid infinite loops
  const prevAudioSyncRef = React.useRef<string>('');
  
  useEffect(() => {
    if (!storyboardContext || !files || files.length === 0) return;
    
    // Group audio files by scene number
    const audioByScene: Record<number, any[]> = {};
    files.forEach((file: AudioFile) => {
      const sceneNum = file.sceneNumber || 1;
      if (!audioByScene[sceneNum]) {
        audioByScene[sceneNum] = [];
      }
      audioByScene[sceneNum].push({
        id: file.id,
        type: file.type,
        sceneNumber: sceneNum,
        shotType: file.shotType, // Include shot type for filtering
        shotIndex: file.shotIndex, // Include shot index for per-shot audio
        url: file.url,
        duration: file.duration,
        character: file.character,
        status: file.status,
        text_content: file.text_content,  // Add text content for display
        text_prompt: file.text_prompt,    // Add text prompt for display
      });
    });
    
    // Only update if data has changed (prevent infinite loop)
    const newSyncKey = JSON.stringify(audioByScene);
    if (prevAudioSyncRef.current === newSyncKey) return;
    prevAudioSyncRef.current = newSyncKey;
    
    // Update context with audio for each scene
    Object.entries(audioByScene).forEach(([sceneNum, audioFiles]) => {
      storyboardContext.setSceneAudio(parseInt(sceneNum), audioFiles);
    });
  }, [storyboardContext, files]);

  // Load/refresh on script/chapter/version change
  useEffect(() => {
    if (stableSelectedChapterId && selectedScriptId) {
      loadAudio();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stableSelectedChapterId, selectedScriptId, versionToken]);

  // NEW: Load storyboard configuration when script changes
  useEffect(() => {
    if (stableSelectedChapterId && selectedScriptId) {
      projectService.getStoryboardConfig(stableSelectedChapterId, selectedScriptId)
        .then((config) => {
          loadStoryboardConfig(config);
        })
        .catch((error) => {
          console.log('[AudioPanel] No storyboard config found or error loading:', error);
          // This is expected for new scripts, just use empty config
        });
    }
  }, [stableSelectedChapterId, selectedScriptId, loadStoryboardConfig]);

  // Seek on chapter/segment change without reloading audio
  useEffect(() => {
    if (!stableSelectedChapterId) return; // guard to avoid running before context is ready
    const start = computeSeekStart();
    if (audioRef.current) {
      audioRef.current.currentTime = start;
    }
  }, [stableSelectedChapterId, selectedSegmentId]);
  
  // Clear audio generation state when generation completes (isGenerating transitions from true to false)
  useEffect(() => {
    // Only clear when isGenerating transitions from true → false (not when it's initially false)
    const wasGenerating = prevIsGeneratingRef.current;
    prevIsGeneratingRef.current = isGenerating;
    
    if (wasGenerating && !isGenerating) {
      // Generation just completed - clear the state
      setGeneratingScenesAudio(new Set());
      setVideoGenerationId(null);
    }
  }, [isGenerating]);



  const characters = selectedScript?.characters || [];
  useEffect(() => {
    if (selectedScript && characters.length > 0) {
      // Initialize character voices with defaults if not already set
      setGenerationOptions(prev => {
        const updatedVoices = { ...prev.characterVoices };
        characters.forEach((character: string) => {
          if (!updatedVoices[character]) {
            // Default to conversational for cinematic scripts, narrator for others
            updatedVoices[character] = selectedScript.script_style === 'cinematic'
              ? 'elevenlabs_conversational'
              : 'elevenlabs_narrator';
          }
        });
        return {
          ...prev,
          characterVoices: updatedVoices
        };
      });
    }
  }, [selectedScript, characters]);

  useEffect(() => {
    if (selectedScript) {

      setGenerationOptions(prev => ({
        ...prev,
        voiceModel: selectedScript.script_style === 'cinematic' ? 'elevenlabs_conversational' : 'elevenlabs_narrator',
        generateNarration: selectedScript.script_style !== 'cinematic'
      }));

      // Auto-regenerate audio when script changes
      // Note: Audio regeneration logic will be handled by the hook when script changes
    }
  }, [selectedScript]);

  // Show all chapter audio files regardless of script association
  // Backend returns chapter-level audio files, not script-specific

  // Filter audio files by selected script_id, accepting both script_id and scriptId fields
  // Include files without script_id (legacy data or chapter-level audio)
  const filteredAudioFiles = (files ?? []).filter((file) => {
    const normalizedScriptId = file.script_id ?? file.scriptId;
    // Keep file if:
    // 1. No selectedScriptId filter is active, OR
    // 2. File's script_id matches selectedScriptId, OR
    // 3. File has no script_id (legacy data - include it anyway)
    return !selectedScriptId || normalizedScriptId === selectedScriptId || !normalizedScriptId;
  });

  // Filtering audio files by script_id

  // Disable controls during switching/prep
  const getTabInfo = (type: string) => {
    const tabFiles = filteredAudioFiles.filter((f: AudioFile) => f.type === type) || [];
    // Use generation_status (from API) or status field for status checks
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const completedCount = tabFiles.filter((f: AudioFile) => ((f as any).generation_status || f.status) === 'completed').length;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const generatingCount = tabFiles.filter((f: AudioFile) => ((f as any).generation_status || f.status) === 'generating').length;
    return { completedCount, generatingCount, totalCount: tabFiles.length };
  };

  const audioTabs = [
    { id: 'scenes', label: 'Storyboard', icon: Clapperboard, completedCount: null, generatingCount: 0, totalCount: scenes.length },
    // Conditionally show Narration or Dialogue based on script type
    ...(selectedScript?.script_style === 'cinematic' || selectedScript?.script_style === 'cinematic_movie' 
        ? [{ id: 'dialogue', label: 'Dialogue', icon: Mic, ...getTabInfo('dialogue') }]
        : [{ id: 'narration', label: 'Narration', icon: Volume2, ...getTabInfo('narration') }]
    ),
    { id: 'music', label: 'Music', icon: Music, ...getTabInfo('music') },
    { id: 'effects', label: 'Effects', icon: Headphones, ...getTabInfo('effects') },
    { id: 'ambiance', label: 'Ambiance', icon: Wind, ...getTabInfo('ambiance') },
    { id: 'timeline', label: 'Timeline', icon: Layers, completedCount: null, generatingCount: 0, totalCount: null }
  ];

  const handleGenerateAll = () => {
    if (!scenes.length) {
      toast.error('No scenes available to generate audio for');
      return;
    }

    // Require emotional map for cinematic scripts
    const isCinematic = selectedScript?.script_style === 'cinematic' || 
                        selectedScript?.script_style === 'cinematic_movie';
    const hasEmotionalMap = selectedScript?.emotional_map && 
                            Array.isArray(selectedScript.emotional_map) && 
                            selectedScript.emotional_map.length > 0;
    
    if (isCinematic && !hasEmotionalMap) {
      toast.error('Please generate the Cinematic Emotional Map in the Script tab first. This provides the audio design for sound effects and music.');
      return;
    }

    setShowGenerationModal(true);
  };

  // Render empty state when no script is selected
  if (!selectedScriptId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Audio Production</h3>
            <p className="text-gray-600 dark:text-gray-400">Select a script to preview audio</p>
          </div>
        </div>
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <Music className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p className="text-lg font-medium">No script selected</p>
          <p className="text-sm">Select a script from the script panel to preview audio</p>
        </div>
      </div>
    );
  }


  const handleConfirmGeneration = async () => {

    if (!selectedScriptId) {
      console.error('[AudioPanel] Missing Script ID');
      toast.error('Unable to generate: Missing Script ID');
      return;
    }

    try {
      // Extract selected scene numbers as integers
      const selectedScenes = Object.keys(selectedSceneImages)
        .map(Number)
        .filter(n => !isNaN(n));

      // Filter out scenes where all images are excluded (deselectedImages from storyboard config)
      // For each scene, check if it has any non-excluded images
      const scenesWithIncludedImages = scenes
        .map((_, idx) => idx + 1)
        .filter(sceneNum => {
          // Get images for this scene
          const sceneImgs = sceneImages[sceneNum] || [];
          // Check if at least one image is not excluded
          return sceneImgs.some(img => img.id && !deselectedImages.has(img.id));
        });

      // If user has selected specific scenes, filter to only those
      // Otherwise use all scenes with included images
      let sceneNumbersToGenerate: number[] | undefined;
      if (selectedScenes.length > 0) {
        // Intersect user-selected scenes with scenes that have included images
        sceneNumbersToGenerate = selectedScenes.filter(sn => scenesWithIncludedImages.includes(sn));
      } else {
        sceneNumbersToGenerate = scenesWithIncludedImages.length > 0 ? scenesWithIncludedImages : undefined;
      }

      // Mark scenes for generating
      if (sceneNumbersToGenerate && sceneNumbersToGenerate.length > 0) {
        setGeneratingScenesAudio(new Set(sceneNumbersToGenerate));
      } else {
        // If no specific scenes, mark all scenes
        setGeneratingScenesAudio(new Set(scenes.map((_, i) => i + 1)));
      }

      const response = await import('../../lib/api').then(m => m.generateScriptAudio(stableSelectedChapterId, selectedScriptId, sceneNumbersToGenerate));
      if (response && response.video_generation_id) {
          setVideoGenerationId(response.video_generation_id);
      }
      setShowGenerationModal(false);
      toast.success('Audio generation started');
      // Reload will happen automatically via poll or manually
      loadAudio();
    } catch (error) {
      console.error('Failed to start generation:', error);
      toast.error('Failed to start audio generation');
      // Clear generating state on error
      setGeneratingScenesAudio(new Set());
    }
  };


  const handlePlayPause = () => {
    if (isPlaying) {
      // TODO: Implement stop audio logic
      setIsPlaying(false);
    } else {
      // TODO: Implement play audio logic
      setIsPlaying(true);
    }
  };

  const renderHeader = () => {
    // Use isGenerating from useAudioGeneration to track active generation polling
    // isGenerating is properly managed by the hook and becomes false when polling completes
    const isGeneratingAudio = isGenerating;
    console.log('[AudioPanel renderHeader] isGenerating:', isGenerating, 'generatingScenesAudio:', [...generatingScenesAudio]);
    return (
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Audio Production</h3>
          <p className="text-gray-600 dark:text-gray-400">Generate and manage audio for {chapterTitle}</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="flex items-center space-x-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg shadow-sm hover:shadow-md hover:bg-gray-50 transition-all duration-200"
          >
            <Settings className="w-4 h-4" />
            <span>Settings</span>
          </button>
          <button
            onClick={handleGenerateAll}
            disabled={!scenes.length || isGeneratingAudio}
            className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg shadow-md hover:shadow-lg hover:from-purple-700 hover:to-indigo-700 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            {isGeneratingAudio ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Wand2 className="w-4 h-4" />
            )}
            <span>{isGeneratingAudio ? 'Generating...' : 'Generate All Audio'}</span>
          </button>
          <button
            onClick={exportAudioMix}
            disabled={!filteredAudioFiles || filteredAudioFiles.length === 0}
            className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-lg shadow-md hover:shadow-lg hover:from-emerald-600 hover:to-teal-600 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            <Download className="w-4 h-4" />
            <span>Export Mix</span>
          </button>
        </div>
      </div>
    );
  };

  const renderSettings = () => (
    showSettings && (
      <div className="bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg p-6 mb-6">
        <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Audio Generation Settings</h4>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
           {generationOptions.generateNarration && (
             <div>
               <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                 Voice Model
                 {selectedScript?.script_style === 'cinematic' && (
                   <span className="text-xs text-blue-600 dark:text-blue-400 ml-2">(Character Dialogue)</span>
                 )}
               </label>
               <select
                 value={generationOptions.voiceModel}
                 onChange={(e) => setGenerationOptions(prev => ({ ...prev, voiceModel: e.target.value }))}
                 className="w-full border rounded-md px-3 py-2 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
               >
                 <option value="elevenlabs_narrator">Professional Narrator (Storytelling)</option>
                 <option value="elevenlabs_conversational">Conversational (Character Dialogue)</option>
                 <option value="elevenlabs_expressive">Expressive (Dramatic Reading)</option>
                 <option value="openai_tts">OpenAI TTS (Natural)</option>
                 <option value="google_wavenet">Google WaveNet (Clear)</option>
               </select>
               <p className="text-xs text-gray-500 mt-1">
                 {selectedScript?.script_style === 'cinematic'
                   ? 'For character dialogue scripts, conversational voices work best'
                   : 'For narration scripts, professional narrator voices provide the best experience'
                 }
               </p>
             </div>
           )}

           <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Music Style</label>
            <select
              value={generationOptions.musicStyle}
              onChange={(e) => setGenerationOptions(prev => ({ ...prev, musicStyle: e.target.value }))}
              className="w-full border dark:border-gray-600 rounded-md px-3 py-2 dark:bg-gray-700 dark:text-white"
            >
              <option value="cinematic">Cinematic</option>
              <option value="orchestral">Orchestral</option>
              <option value="electronic">Electronic</option>
              <option value="ambient">Ambient</option>
              <option value="dramatic">Dramatic</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Audio Quality</label>
            <select
              value={generationOptions.audioQuality}
              onChange={(e) => setGenerationOptions(prev => ({ ...prev, audioQuality: e.target.value as 'standard' | 'high' | 'premium' }))}
              className="w-full border dark:border-gray-600 rounded-md px-3 py-2 dark:bg-gray-700 dark:text-white"
            >
              <option value="standard">Standard</option>
              <option value="high">High Quality</option>
              <option value="premium">Premium</option>
            </select>
          </div>
        </div>

        {/* Character Voice Mapping */}
        {generationOptions.generateNarration && characters.length > 0 && (
          <div className="mt-4">
            <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Character Voice Mapping</h5>
            <div className="space-y-3">
              {characters.map((character: string) => (
                <div key={character} className="flex items-center space-x-3">
                  <span className="text-sm text-gray-600 dark:text-gray-400 w-24 flex-shrink-0">{character}:</span>
                  <select
                    value={generationOptions.characterVoices[character] || ''}
                    onChange={(e) => setGenerationOptions(prev => ({
                      ...prev,
                      characterVoices: {
                        ...prev.characterVoices,
                        [character]: e.target.value
                      }
                    }))}
                    className="flex-1 border dark:border-gray-600 rounded-md px-3 py-2 text-sm dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">Use default ({generationOptions.voiceModel})</option>
                    <option value="elevenlabs_narrator">Professional Narrator</option>
                    <option value="elevenlabs_conversational">Conversational</option>
                    <option value="elevenlabs_expressive">Expressive</option>
                    <option value="openai_tts">OpenAI TTS</option>
                    <option value="google_wavenet">Google WaveNet</option>
                  </select>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Assign specific voice models to characters for more authentic dialogue
            </p>
          </div>
        )}

        <div className="mt-4 space-y-3">
           <label className="flex items-center">
             <input
               type="checkbox"
               checked={generationOptions.generateNarration}
               onChange={(e) => setGenerationOptions(prev => ({ ...prev, generateNarration: e.target.checked }))}
               className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
             />
             <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Generate narration</span>
           </label>

           <label className="flex items-center">
             <input
               type="checkbox"
               checked={generationOptions.generateMusic}
               onChange={(e) => setGenerationOptions(prev => ({ ...prev, generateMusic: e.target.checked }))}
               className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
             />
             <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Generate background music</span>
           </label>
         </div>
      </div>
    )
  );

  const renderTabNavigation = () => (
    <div className="flex space-x-1 bg-white/20 backdrop-blur-md border border-white/20 rounded-xl p-1 mb-6 shadow-sm overflow-x-auto">
      {audioTabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id as any)} // Use any to bypass strict type checking for dynamic tabs
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 ${
            activeTab === tab.id
              ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md transform scale-[1.02]'
              : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-white/40 dark:hover:bg-white/10'
          }`}
        >
          <tab.icon className="w-4 h-4" />
          <span>{tab.label}</span>
          {tab.totalCount !== null && (
            <div className="flex items-center space-x-1 ml-2">
              <span className={`px-2 py-0.5 rounded-full text-xs ${
                activeTab === tab.id ? 'bg-white/20 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
              }`}>
                {tab.completedCount}
              </span>
              {tab.generatingCount > 0 && (
                <div className="flex items-center space-x-1 px-2 py-0.5 bg-blue-100 text-blue-600 rounded-full text-xs animate-pulse">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>{tab.generatingCount}</span>
                </div>
              )}
            </div>
          )}
        </button>
      ))}
    </div>
  );

  const renderAudioPlayer = () => (
    <div className="bg-gradient-to-br from-gray-900 to-gray-800 text-white rounded-xl p-6 mb-6 shadow-xl border border-white/10 relative overflow-hidden group">
      {/* Decorative background glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-purple-600/20 rounded-full blur-3xl -mr-32 -mt-32 opacity-50 group-hover:opacity-70 transition-opacity duration-700" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-blue-600/20 rounded-full blur-3xl -ml-32 -mb-32 opacity-30 group-hover:opacity-50 transition-opacity duration-700" />
      
      <div className="relative z-10 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => {}}
            className="p-2 hover:bg-gray-800 rounded"
          >
            <SkipBack className="w-5 h-5" />
          </button>
          
          <button
            onClick={handlePlayPause}
            className="p-3 bg-purple-600 hover:bg-purple-700 rounded-full"
          >
            {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
          </button>
          
          <button
            onClick={() => {}}
            className="p-2 hover:bg-gray-800 rounded"
          >
            <SkipForward className="w-5 h-5" />
          </button>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-sm">{formatTime(currentTime)}</span>
          <div className="w-64 h-1 bg-gray-700 rounded-full">
            <div 
              className="h-full bg-purple-600 rounded-full"
              style={{ width: `${(currentTime / duration) * 100}%` }}
            />
          </div>
          <span className="text-sm">{formatTime(duration)}</span>
        </div>

        <div className="flex items-center space-x-3">
          <Volume2 className="w-4 h-4 text-gray-400" />
          <div className="w-24 h-1 bg-gray-700/50 rounded-full overflow-hidden cursor-pointer">
            <div className="w-3/4 h-full bg-gray-400 hover:bg-white transition-colors rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );

  const renderContent = () => {
    if (activeTab === 'timeline') {
      return (
        <AudioTimeline
          files={filteredAudioFiles}
          duration={duration}
          currentTime={currentTime}
          onTimeUpdate={setCurrentTime}
          onAudioSelect={(audioId) => {
            setSelectedAudioFiles(prev => {
              const newSet = new Set(prev);
              if (newSet.has(audioId)) {
                newSet.delete(audioId);
              } else {
                newSet.add(audioId);
              }
              return newSet;
            });
          }}
        />
      );
    }
    
    if (activeTab === 'scenes') {
        // Helper function to check if a scene has any audio files
        const sceneHasAudio = (sceneNum: number): boolean => {
            return filteredAudioFiles.some((f: AudioFile) => f.sceneNumber === sceneNum);
        };

        // Handler for per-scene audio generation
        const handleGenerateSceneAudio = async (sceneNum: number) => {
            if (!selectedScriptId) {
                toast.error('No script selected');
                return;
            }

            try {
                setGeneratingScenesAudio(prev => new Set(prev).add(sceneNum));
                const response = await import('../../lib/api').then(m => 
                    m.generateScriptAudio(stableSelectedChapterId, selectedScriptId, [sceneNum])
                );
                if (response?.video_generation_id) {
                    setVideoGenerationId(response.video_generation_id);
                }
                toast.success(`Audio generation started for Scene ${sceneNum}`);
                loadAudio();
            } catch (error) {
                console.error('Failed to start scene audio generation:', error);
                toast.error(`Failed to start audio generation for Scene ${sceneNum}`);
                setGeneratingScenesAudio(prev => {
                    const newSet = new Set(prev);
                    newSet.delete(sceneNum);
                    return newSet;
                });
            }
        };

        return (
            <div className="space-y-6">
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-900 rounded-lg p-4">
                    <p className="text-sm text-blue-800 dark:text-blue-300">
                        <strong>Storyboard Selection:</strong> Select your preferred image for each scene. 
                        Only selected scene images will be used for final video generation.
                    </p>
                </div>

                <div className="space-y-6">
                    {scenes.map((scene: any, idx: number) => {
                        const sceneNum = idx + 1;
                        const rawImages = sceneImages[`${selectedScriptId}_${sceneNum}`] || sceneImages[sceneNum] || [];

                        // Sort images according to stored order
                        const storedOrder = imageOrderByScene[sceneNum];
                        const sortedImages = storedOrder && storedOrder.length > 0
                            ? [...rawImages].sort((a: any, b: any) => {
                                const aIndex = a.id ? storedOrder.indexOf(a.id) : -1;
                                const bIndex = b.id ? storedOrder.indexOf(b.id) : -1;
                                if (aIndex === -1 && bIndex === -1) return 0;
                                if (aIndex === -1) return 1;
                                if (bIndex === -1) return -1;
                                return aIndex - bIndex;
                            })
                            : rawImages;

                        // Filter out excluded images for display
                        const visibleImages = sortedImages.filter((img: any) =>
                            !img.id || !deselectedImages.has(img.id)
                        );

                        // Skip scenes where all images are excluded
                        if (visibleImages.length === 0 && rawImages.length > 0) {
                            return null;
                        }

                        return (
                            <AudioStoryboardSceneRow
                                key={idx}
                                sceneNumber={sceneNum}
                                description={typeof scene === 'string' ? scene : (scene.visual_description || scene.description)}
                                images={sortedImages}
                                keySceneImageId={keySceneImages[sceneNum]}
                                deselectedImages={deselectedImages}
                                isGeneratingAudio={generatingScenesAudio.has(sceneNum)}
                                hasAudio={sceneHasAudio(sceneNum)}
                                onGenerateAudio={() => handleGenerateSceneAudio(sceneNum)}
                                onView={(_url) => openGallery(idx)}
                            />
                        );
                    })}
                </div>
                
                {scenes.length === 0 && (
                    <div className="text-center py-12 text-gray-500">
                        <Clapperboard className="mx-auto h-12 w-12 mb-4 opacity-50" />
                        <p className="text-lg font-medium">No scenes found</p>
                    </div>
                )}

                {galleryState.isOpen && galleryState.sceneIndex !== -1 && scenes[galleryState.sceneIndex] && (() => {
                    const sceneNum = galleryState.sceneIndex + 1;
                    const rawGalleryImages = sceneImages[`${selectedScriptId}_${sceneNum}`] || sceneImages[sceneNum] || [];
                    // Filter out excluded images - only show images not in deselectedImages
                    const includedGalleryImages = rawGalleryImages.filter((img: any) =>
                        !img.id || !deselectedImages.has(img.id)
                    );
                    return (
                        <SceneGalleryModal
                            isOpen={galleryState.isOpen}
                            onClose={closeGallery}
                            sceneNumber={sceneNum}
                            description={typeof scenes[galleryState.sceneIndex] === 'string' 
                                ? scenes[galleryState.sceneIndex] 
                                : (scenes[galleryState.sceneIndex].visual_description || scenes[galleryState.sceneIndex].description)}
                            images={includedGalleryImages}
                            selectedImageUrl={selectedSceneImages[sceneNum]}
                            initialIndex={galleryState.initialImageIndex}
                            onSelectImage={(url) => setSelectedSceneImage(sceneNum, url || null)}
                        />
                    );
                })()}
            </div>
        );
    }

    const audioType = activeTab;
    const tabFiles = filteredAudioFiles.filter((f: AudioFile) => f.type === audioType) || [];

    return (
      <div className="space-y-4">
        {tabFiles.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Music className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">No audio found for this script and chapter</p>
            <p className="text-sm">Select a different script or chapter to see audio files.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {tabFiles
              .sort((a: AudioFile, b: AudioFile) => {
                const statusOrder: Record<string, number> = { generating: 0, completed: 1, failed: 2, pending: 3 };
                return statusOrder[a.status ?? 'completed'] - statusOrder[b.status ?? 'completed'];
              })
              .map((file: AudioFile) => (
                <AudioFileCard
                  key={file.id}
                  file={file}
                  isSelected={selectedAudioFiles.has(file.id)}
                  onSelect={() => {
                    setSelectedAudioFiles(prev => {
                      const newSet = new Set(prev);
                      if (newSet.has(file.id)) {
                        newSet.delete(file.id);
                      } else {
                        newSet.add(file.id);
                      }
                      return newSet;
                    });
                  }}
                  onPlay={() => {
                    const audioEl = document.getElementById(`audio-${file.id}`) as HTMLAudioElement | null;
                    audioEl?.play();
                  }}
                  onPause={() => {
                    const audioEl = document.getElementById(`audio-${file.id}`) as HTMLAudioElement | null;
                    audioEl?.pause();
                  }}
                  onVolumeChange={(volume) => {
                    const audioEl = document.getElementById(`audio-${file.id}`) as HTMLAudioElement | null;
                    if (audioEl) audioEl.volume = volume;
                  }}
                  onDelete={async () => {
                    console.log('[AudioPanel] Delete clicked for:', file.id, 'file.chapter_id:', (file as any).chapter_id, 'context chapterId:', stableSelectedChapterId);
                    
                    // Get chapter ID - try from file first, then from context
                    const chapterId = (file as any).chapter_id || stableSelectedChapterId;
                    
                    if (!chapterId) {
                      console.error('[AudioPanel] Cannot delete: chapter ID is missing from both file and context');
                      toast.error('Cannot delete: chapter ID not available');
                      return;
                    }
                    
                    if (!file.id) {
                      console.error('[AudioPanel] Cannot delete: audio file ID is missing');
                      toast.error('Cannot delete: audio file ID not available');
                      return;
                    }
                    
                    try {
                      console.log('[AudioPanel] Calling deleteAudio API...', chapterId, file.id);
                      await deleteAudio(chapterId, file.id);
                      toast.success('Audio deleted successfully');
                      // Reload audio to refresh the list
                      loadAudio();
                    } catch (error) {
                      console.error('Failed to delete audio:', error);
                      toast.error('Failed to delete audio');
                    }
                    
                    // Also remove from local selection state
                    setSelectedAudioFiles(prev => {
                      const newSet = new Set(prev);
                      newSet.delete(file.id);
                      return newSet;
                    });
                  }}
                  audioRef={(el) => {
                    if (el) el.id = `audio-${file.id}`;
                  }}
                  onReassign={async (newShotIndex) => {
                    const success = await reassignAudio(file.id, newShotIndex);
                    if (success) {
                      toast.success(`Audio assigned to ${newShotIndex === 0 ? 'Key Scene' : `Shot ${newShotIndex}`}`);
                    } else {
                      toast.error('Failed to reassign audio');
                    }
                  }}
                />
              ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {renderHeader()}
      {renderSettings()}
      {renderAudioPlayer()}
      {renderTabNavigation()}
      {renderContent()}
      <AudioGenerationModal
        isOpen={showGenerationModal}
        onClose={() => setShowGenerationModal(false)}
        onConfirm={handleConfirmGeneration}
        sceneCount={Object.keys(selectedSceneImages).length > 0 ? Object.keys(selectedSceneImages).length : scenes.length}
      />
    </div>
  );
};

// Helper component for audio file cards
const AudioFileCard: React.FC<{
  file: {
    id: string;
    type?: string;
    status?: string;
    name?: string;
    sceneNumber?: number;
    duration?: number;
    character?: string;
    url?: string;
    volume?: number;
    script_id?: string;
    scriptId?: string | null;
    chapter_id?: string;
    shotType?: 'key_scene' | 'suggested_shot';
    shotIndex?: number;
    text_content?: string;  // For display text
    text_prompt?: string;   // Fallback display text
  };
  isSelected: boolean;
  maxShotIndex?: number; // Maximum suggested shot index for this scene
  onSelect: () => void;
  onPlay: () => void;
  onPause: () => void;
  onVolumeChange: (volume: number) => void;
  onDelete: () => void;
  onReassign?: (newShotIndex: number) => void;
  audioRef: (el: HTMLAudioElement | null) => void;
}> = ({ file, isSelected, maxShotIndex = 5, onSelect, onPlay, onPause, onVolumeChange, onDelete, onReassign, audioRef }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const isGenerating = file.status === 'generating';
  const isFailed = file.status === 'failed';

  return (
    <div className={`bg-white border rounded-lg p-4 ${isSelected ? 'border-purple-500' : ''} ${isGenerating ? 'border-blue-300 bg-blue-50' : ''} ${isFailed ? 'border-red-300 bg-red-50' : ''}`}>
      {file.url && <audio ref={audioRef} src={file.url} />}

      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onSelect}
            className="rounded border-gray-300 text-purple-600"
            disabled={isGenerating}
          />
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h5 className="font-medium text-gray-900">{file.text_content || file.text_prompt || file.name}</h5>
              {isGenerating && (
                <div className="flex items-center space-x-1 text-blue-600">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Generating...</span>
                </div>
              )}
              {isFailed && (
                <span className="text-sm text-red-600">Failed</span>
              )}
            </div>
            <p className="text-sm text-gray-500">
              Scene {file.sceneNumber ?? 'Unknown'}
              {file.shotType && (
                <span className={`ml-2 px-1.5 py-0.5 text-xs rounded ${file.shotType === 'key_scene' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}`}>
                  {file.shotType === 'key_scene' ? 'Key Scene' : 'Suggested Shot'}
                </span>
              )}
              {file.shotIndex !== undefined && file.shotIndex > 0 && ` • Shot ${file.shotIndex}`}
              {file.duration && file.duration > 0 && ` • ${formatTime(file.duration)}`}
              {file.character && ` • ${file.character}`}
            </p>
            {/* Shot Assignment Dropdown - always show if onReassign is provided */}
            {onReassign && !isGenerating && (
              <div className="flex items-center mt-1 space-x-2">
                <span className="text-xs text-gray-400">Assign to:</span>
                <select
                  value={file.shotIndex ?? 0}
                  onChange={(e) => onReassign(parseInt(e.target.value, 10))}
                  className="text-xs border border-gray-200 rounded px-2 py-0.5 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-white hover:border-purple-400 focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
                >
                  <option value={0}>Key Scene</option>
                  {[...Array(maxShotIndex)].map((_, i) => (
                    <option key={i + 1} value={i + 1}>Shot {i + 1}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {!isGenerating && !isFailed && (
            <button
              onClick={() => {
                if (isPlaying) {
                  onPause();
                  setIsPlaying(false);
                } else {
                  onPlay();
                  setIsPlaying(true);
                }
              }}
              className="p-2 text-purple-600 hover:bg-purple-50 rounded"
              disabled={!file.url}
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
          )}

          <button
            onClick={onDelete}
            className="p-2 text-red-600 hover:bg-red-50 rounded"
            disabled={isGenerating}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Waveform visualization or generating placeholder */}
      <div className="h-12 bg-gray-100 rounded mb-3">
        <div className="h-full flex items-center justify-center">
          {isGenerating ? (
            <div className="flex items-center space-x-2 text-blue-600">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">Processing audio...</span>
            </div>
          ) : file.url ? (
            <div className="flex space-x-1">
              {[...Array(30)].map((_, i) => (
                <div
                  key={i}
                  className="w-1 bg-purple-400 rounded"
                  style={{ height: `${Math.random() * 100}%` }}
                />
              ))}
            </div>
          ) : (
            <span className="text-sm text-gray-500">Audio not ready</span>
          )}
        </div>
      </div>

      {/* Volume control - only show for completed files */}
      {file.status === 'completed' && (
        <div className="flex items-center space-x-2">
          <Volume1 className="w-4 h-4 text-gray-500" />
          <input
            type="range"
            min="0"
            max="100"
            defaultValue={(file.volume || 1) * 100}
            onChange={(e) => onVolumeChange(parseInt(e.target.value) / 100)}
            className="flex-1"
          />
          <Volume2 className="w-4 h-4 text-gray-500" />
        </div>
      )}
    </div>
  );
};

// Helper function to format time
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export default AudioPanel;

// Replace any remaining selectedChapterId references with stableSelectedChapterId
