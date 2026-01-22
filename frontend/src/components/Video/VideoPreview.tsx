import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, Maximize2, Music } from 'lucide-react';
import { VideoScene } from '../../types/videoProduction';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';
import { useStoryboardOptional } from '../../contexts/StoryboardContext';


interface SceneDescription {
  scene_number: number;
  location: string;
  time_of_day: string;
  characters: string[];
  key_actions: string;
  estimated_duration: number;
  visual_description: string;
  audio_requirements: string;
}

interface ChapterScript {
  id: string;
  chapter_id: string;
  script_style: string;
  script_name: string;
  script: string;
  scene_descriptions: SceneDescription[];
  characters: string[];
  character_details: string;
  acts: any[];
  beats: any[];
  scenes: any[];
  created_at: string;
  status: 'draft' | 'ready' | 'approved';
}

interface VideoPreviewProps {
  scenes: VideoScene[];
  currentSceneIndex?: number;
  isPlaying: boolean;
  onSceneChange?: (index: number) => void;
  onPlayPause?: () => void;
  videoUrl?: string; // Final generated video URL
  selectedScript?: ChapterScript | null; // Script data for synchronization
}

const VideoPreview: React.FC<VideoPreviewProps> = (props) => {
  const { scenes, currentSceneIndex = 0, isPlaying, onSceneChange, onPlayPause, videoUrl, selectedScript } = props;

  // Script selection context integration
  const {
    selectedScriptId,
    selectedChapterId,
    selectedSegmentId,
    versionToken,
    isSwitching,
    publish,
    subscribe,
  } = useScriptSelection();

  // Storyboard context for audio access
  const storyboardContext = useStoryboardOptional();

  // DEBUG: Log props to diagnose data flow
  useEffect(() => {
    if (scenes && scenes.length > 0) {
    }
  }, [scenes, currentSceneIndex, isPlaying, videoUrl, selectedScript]);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [showControls, setShowControls] = useState(true);
  const [videoError, setVideoError] = useState(false);
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const controlsTimeoutRef = useRef<NodeJS.Timeout>();
  const audioRefs = useRef<Record<string, HTMLAudioElement>>({});

  const currentScene = scenes && scenes[currentSceneIndex];
  const totalDuration = scenes ? scenes.reduce((sum, scene) => sum + scene.duration, 0) : 0;
  
  // Get audio files for current scene/shot from StoryboardContext
  // Uses shotIndex to get only audio for this specific shot
  const sceneAudio = currentScene ? 
    storyboardContext?.getAudioForShot(currentScene.sceneNumber, currentScene.shotIndex) || [] : 
    [];

  // Get current scene's script data
  const getCurrentSceneScript = () => {
    if (!selectedScript || !currentScene) return null;

    const sceneNumber = currentScene.sceneNumber;
    const sceneData = selectedScript.scene_descriptions.find(
      (scene: SceneDescription) => scene.scene_number === sceneNumber
    );

    return sceneData;
  };

  // Extract dialogue segments from script text for current scene
  const getCurrentSceneDialogue = () => {
    if (!selectedScript?.script || !currentScene) return null;

    const sceneNumber = currentScene.sceneNumber;
    const scriptLines = selectedScript.script.split('\n');
    const dialogueSegments: Array<{character: string, text: string}> = [];

    let currentCharacter = '';
    let inScene = false;

    for (let i = 0; i < scriptLines.length; i++) {
      const line = scriptLines[i].trim();

      // Check if we're entering the current scene
      if (line.toLowerCase().includes(`scene ${sceneNumber}`) ||
          line.toLowerCase().includes(`scene ${sceneNumber}:`) ||
          (line.match(/INT\.|EXT\./) && line.includes(`SCENE ${sceneNumber}`))) {
        inScene = true;
        continue;
      }

      // Check if we're entering the next scene (end current scene)
      if (inScene && (line.match(/INT\.|EXT\./) && !line.includes(`SCENE ${sceneNumber}`))) {
        break;
      }

      if (!inScene) continue;

      // Detect character names (uppercase, typically 2-20 chars)
      if (line === line.toUpperCase() && line.length > 1 && line.length < 20 &&
          !line.includes('.') && !line.includes('(') && !line.includes(')')) {
        currentCharacter = line;
        continue;
      }

      // Detect dialogue (lines that follow character names)
      if (currentCharacter && line.length > 0 && !line.startsWith('(') && !line.startsWith('[')) {
        // Clean up dialogue text
        let dialogueText = line;
        if (dialogueText.startsWith('"') && dialogueText.endsWith('"')) {
          dialogueText = dialogueText.slice(1, -1);
        }

        dialogueSegments.push({
          character: currentCharacter,
          text: dialogueText
        });

        currentCharacter = ''; // Reset after dialogue
      }
    }

    return dialogueSegments.length > 0 ? dialogueSegments : null;
  };

  const currentSceneScript = getCurrentSceneScript();
  const currentSceneDialogue = getCurrentSceneDialogue();

  // Clear and re-load overlays on script change
  useEffect(() => {
    let cancelled = false;
    
    // Clear prior overlays/state when script changes
    if (!selectedScriptId) {
      // No script selected - render empty state
      return;
    }

    // If we have a selectedScript prop and it matches the selectedScriptId, trigger a re-fetch
    if (selectedScript && selectedScript.id === selectedScriptId) {
      // Force re-render of script overlay when script changes
      setCurrentTime(currentTime); // Trigger re-calculation
      
      // Publish timeline recalculation when overlays are ready
      if (!cancelled) {
        publish('TIMELINE_RECALC_REQUESTED', { reason: 'system' });
      }
    }

    return () => {
      cancelled = true;
    };
  }, [selectedScriptId, versionToken, selectedScript, publish, currentTime]);

  // Seek preview on chapter/segment change
  useEffect(() => {
    if (!selectedSegmentId || !scenes || scenes.length === 0) return;
    
    // Find the scene that corresponds to the selected segment
    // This is a placeholder - you'll need to implement computeSegmentStart based on your data structure
    const targetScene = scenes.find(scene =>
      scene.id === selectedSegmentId ||
      scene.sceneNumber.toString() === selectedSegmentId
    );
    
    if (targetScene && videoRef.current) {
      // Calculate the start time of the scene
      const sceneIndex = scenes.findIndex(s => s.id === targetScene.id);
      const sceneStartTime = scenes.slice(0, sceneIndex).reduce((sum, s) => sum + s.duration, 0);
      
      // Seek to the beginning of the scene
      videoRef.current.currentTime = sceneStartTime;
      
      // Update current scene if needed
      if (sceneIndex !== currentSceneIndex) {
        onSceneChange?.(sceneIndex);
      }
    }
  }, [selectedChapterId, selectedSegmentId, scenes, currentSceneIndex, onSceneChange]);

  // Listen for timeline recalculation requests
  useEffect(() => {
    const unsub = subscribe((evt) => {
      if (evt === 'TIMELINE_RECALC_REQUESTED') {
        // Recompute overlay layout if needed
        // Force re-render of overlays
        setCurrentTime(prev => prev); // Trigger re-calculation
      }
    });
    return unsub;
  }, [subscribe]);

  // Only auto-change scenes based on time when video is actively playing
  // This prevents the scene from resetting to 0 on component mount
  useEffect(() => {
    if (!scenes || !isPlaying) return;
    // Calculate which scene should be showing based on current time
    let accumulatedTime = 0;
    for (let i = 0; i < scenes.length; i++) {
      if (currentTime < accumulatedTime + scenes[i].duration) {
        if (i !== currentSceneIndex) {
          onSceneChange?.(i);
        }
        break;
      }
      accumulatedTime += scenes[i].duration;
    }
  }, [currentTime, scenes, currentSceneIndex, onSceneChange, isPlaying]);

  useEffect(() => {
    // Auto-hide controls after 3 seconds of inactivity
    if (showControls) {
      clearTimeout(controlsTimeoutRef.current);
      controlsTimeoutRef.current = setTimeout(() => {
        setShowControls(false);
      }, 3000);
    }

    return () => {
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
    };
  }, [showControls]);

  const handleMouseMove = () => {
    setShowControls(true);
  };

  const handlePreviousScene = () => {
    if (currentSceneIndex > 0) {
      onSceneChange?.(currentSceneIndex - 1);
    }
  };

  const handleNextScene = () => {
    if (currentSceneIndex < scenes.length - 1) {
      onSceneChange?.(currentSceneIndex + 1);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (videoRef.current) {
      videoRef.current.volume = newVolume;
    }
  };

  const handleFullscreen = () => {
    if (videoRef.current) {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        videoRef.current.requestFullscreen();
      }
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleVideoError = () => {
    setVideoError(true);
  };

  const handleVideoLoad = () => {
    setVideoError(false);
  };

  // Reset video error state when scene changes
  useEffect(() => {
    setVideoError(false);
  }, [currentSceneIndex]);

  // If videoUrl is provided, show the final generated video
  if (videoUrl) {
    return (
      <div
        className="relative bg-black rounded-lg overflow-hidden group"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setShowControls(false)}
      >
        <div className="aspect-video relative">
          <video
            ref={videoRef}
            src={videoUrl}
            className="w-full h-full object-contain"
            controls={false}
            autoPlay={isPlaying}
            muted={volume === 0}
            onError={handleVideoError}
            onLoadedData={handleVideoLoad}
            onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
          />
          
          {/* Final Video Info Overlay */}
          <div className="absolute top-4 left-4 bg-black/70 text-white px-3 py-1 rounded">
            Final Generated Video
          </div>

          {/* Controls Overlay for Final Video */}
          <div className={`absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-4 transition-opacity duration-300 ${
            showControls ? 'opacity-100' : 'opacity-0'
          }`}>
            {/* Progress Bar */}
            <div className="mb-4">
              <input
                type="range"
                min="0"
                max={videoRef.current?.duration || 0}
                value={currentTime}
                onChange={handleSeek}
                className="w-full h-1 bg-gray-600 rounded-lg appearance-none cursor-pointer slider"
                style={{
                  background: `linear-gradient(to right, #3B82F6 0%, #3B82F6 ${(currentTime / (videoRef.current?.duration || 1)) * 100}%, #4B5563 ${(currentTime / (videoRef.current?.duration || 1)) * 100}%, #4B5563 100%)`
                }}
              />
              <div className="flex justify-between text-xs text-gray-300 mt-1">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(videoRef.current?.duration || 0)}</span>
              </div>
            </div>

            {/* Control Buttons */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                {/* Play/Pause */}
                <button
                  onClick={onPlayPause || (() => {})}
                  className="text-white hover:text-blue-400 transition-colors"
                >
                  {isPlaying ? (
                    <Pause className="w-8 h-8" />
                  ) : (
                    <Play className="w-8 h-8" />
                  )}
                </button>

                {/* Volume */}
                <div className="flex items-center space-x-2">
                  <Volume2 className="w-5 h-5 text-white" />
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={volume}
                    onChange={handleVolumeChange}
                    className="w-20 h-1 bg-gray-600 rounded-lg appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, #3B82F6 0%, #3B82F6 ${volume * 100}%, #4B5563 ${volume * 100}%, #4B5563 100%)`
                    }}
                  />
                </div>
              </div>

              {/* Fullscreen */}
              <button
                onClick={handleFullscreen}
                className="text-white hover:text-blue-400 transition-colors"
              >
                <Maximize2 className="w-6 h-6" />
              </button>
            </div>
          </div>
        </div>

        {/* Video error indicator */}
        {videoError && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80">
            <div className="text-center text-white">
              <p className="text-lg font-semibold mb-2">Video Failed to Load</p>
              <p className="text-sm text-gray-300">Unable to load final video</p>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Fallback to scene-by-scene display when no videoUrl is provided
  if (!selectedScriptId) {
    return (
      <div className="bg-black rounded-lg aspect-video flex items-center justify-center">
        <p className="text-gray-400">Select a script to preview video</p>
      </div>
    );
  }

  if (!currentScene) {
    return (
      <div className="bg-black rounded-lg aspect-video flex items-center justify-center">
        <p className="text-gray-400">No scene selected</p>
      </div>
    );
  }

  // Disable interactions during switching
  const disabled = isSwitching;

  return (
    <div
      className={`relative bg-black rounded-lg overflow-hidden group ${
        disabled ? 'opacity-50 pointer-events-none' : ''
      }`}
      onMouseMove={disabled ? undefined : handleMouseMove}
      onMouseLeave={disabled ? undefined : () => setShowControls(false)}
    >
      {/* Audio Panel for Current Scene */}
      {sceneAudio.length > 0 && (
        <div className="mb-4 bg-gray-900 rounded-lg p-4 z-10 relative border-b border-gray-800">
          <div className="flex items-center space-x-2 mb-3">
            <Music className="w-4 h-4 text-blue-400" />
            <span className="text-white text-sm font-medium">
              Audio for Scene {currentScene.sceneNumber} ({sceneAudio.length} files)
            </span>
          </div>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {sceneAudio.map((audio) => (
              <div 
                key={audio.id} 
                className="flex items-center justify-between bg-gray-800 rounded px-3 py-2"
              >
                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => {
                      if (playingAudioId === audio.id) {
                        audioRefs.current[audio.id]?.pause();
                        setPlayingAudioId(null);
                      } else {
                        // Stop any currently playing audio
                        Object.values(audioRefs.current).forEach(el => el.pause());
                        audioRefs.current[audio.id]?.play();
                        setPlayingAudioId(audio.id);
                      }
                    }}
                    className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center hover:bg-blue-500 transition-colors"
                  >
                    {playingAudioId === audio.id ? (
                      <Pause className="w-4 h-4 text-white" />
                    ) : (
                      <Play className="w-4 h-4 text-white ml-0.5" />
                    )}
                  </button>
                  <div>
                    <span className="text-white text-sm">{audio.character || audio.type}</span>
                    <span className={`ml-2 px-1.5 py-0.5 text-xs rounded ${
                      audio.type === 'dialogue' ? 'bg-purple-600' :
                      audio.type === 'music' ? 'bg-green-600' :
                      audio.type === 'effects' ? 'bg-orange-600' :
                      'bg-blue-600'
                    }`}>
                      {audio.type}
                    </span>
                  </div>
                </div>
                {audio.url && (
                  <audio
                    ref={(el) => { if (el) audioRefs.current[audio.id] = el; }}
                    src={audio.url}
                    onEnded={() => setPlayingAudioId(null)}
                    className="hidden"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Video/Image Display */}
      <div className="aspect-video relative">
        {/* Priority 1: Video URL (if available and no error) */}
        {currentScene.video_url && !videoError ? (
          <video
            ref={videoRef}
            src={currentScene.video_url}
            className="w-full h-full object-cover"
            controls={false}
            autoPlay={isPlaying}
            muted={volume === 0}
            onError={handleVideoError}
            onLoadedData={handleVideoLoad}
            onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
          />
        ) : (
          /* Priority 2: Image URL (fallback from video or primary) */
          currentScene.imageUrl ? (
            <img
              src={currentScene.imageUrl}
              alt={`Scene ${currentScene.sceneNumber}`}
              className="w-full h-full object-cover"
            />
          ) : (
            /* Priority 3: Placeholder (no video or image) */
            <div className="w-full h-full flex items-center justify-center bg-gray-900">
              <p className="text-gray-400">Scene {currentScene.sceneNumber}</p>
            </div>
          )
        )}

        {/* Scene Info Overlay */}
        <div className="absolute top-4 left-4 bg-black/70 text-white px-3 py-1 rounded">
          Scene {currentScene.sceneNumber} of {scenes.length}
        </div>

        {/* Enhanced Script Text Overlay */}
        {currentSceneScript && (
          <div className="absolute bottom-20 left-4 right-4 bg-black/80 text-white p-4 rounded max-h-48 overflow-y-auto">
            <div className="text-sm font-semibold mb-2">
              Scene {currentSceneScript.scene_number}: {currentSceneScript.location} - {currentSceneScript.time_of_day}
            </div>
            <div className="text-sm mb-2">
              {currentSceneScript.visual_description}
            </div>
            {currentSceneScript.key_actions && (
              <div className="text-sm mb-2 text-blue-200">
                <strong>Action:</strong> {currentSceneScript.key_actions}
              </div>
            )}
            {currentSceneScript.characters && currentSceneScript.characters.length > 0 && (
              <div className="text-xs text-gray-300 mb-2">
                <strong>Characters:</strong> {currentSceneScript.characters.join(', ')}
              </div>
            )}

            {/* Dialogue Segments */}
            {currentSceneDialogue && currentSceneDialogue.length > 0 && (
              <div className="text-xs mb-2">
                <strong className="text-yellow-200">Dialogue:</strong>
                <div className="mt-1 space-y-1">
                  {currentSceneDialogue.slice(0, 2).map((dialogue, idx) => (
                    <div key={idx} className="bg-gray-700/50 p-2 rounded">
                      <span className="font-semibold text-yellow-300">{dialogue.character}:</span>
                      <span className="ml-1 italic">"{dialogue.text.length > 60 ? dialogue.text.substring(0, 60) + '...' : dialogue.text}"</span>
                    </div>
                  ))}
                  {currentSceneDialogue.length > 2 && (
                    <div className="text-gray-400 text-xs">
                      +{currentSceneDialogue.length - 2} more dialogue lines...
                    </div>
                  )}
                </div>
              </div>
            )}

            {currentSceneScript.audio_requirements && (
              <div className="text-xs text-green-200">
                <strong>Audio:</strong> {currentSceneScript.audio_requirements}
              </div>
            )}
            <div className="text-xs text-gray-400 mt-1">
              Duration: {currentSceneScript.estimated_duration}s
            </div>
          </div>
        )}

        {/* Controls Overlay */}
      <div className={`absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-4 transition-opacity duration-300 ${
        showControls ? 'opacity-100' : 'opacity-0'
      }`}>
        {/* Progress Bar with Scene Markers */}
        <div className="mb-4">
          <div className="relative">
            <input
              type="range"
              min="0"
              max={totalDuration}
              value={currentTime}
              onChange={handleSeek}
              className="w-full h-1 bg-gray-600 rounded-lg appearance-none cursor-pointer slider"
              style={{
                background: `linear-gradient(to right, #3B82F6 0%, #3B82F6 ${(currentTime / totalDuration) * 100}%, #4B5563 ${(currentTime / totalDuration) * 100}%, #4B5563 100%)`
              }}
            />
            {/* Scene Markers */}
            {scenes.map((scene, index) => {
              const sceneStartTime = scenes.slice(0, index).reduce((sum, s) => sum + s.duration, 0);
              const markerPosition = (sceneStartTime / totalDuration) * 100;
              const isCurrentScene = index === currentSceneIndex;

              return (
                <div
                  key={scene.id}
                  className={`absolute top-0 w-0.5 h-3 transform -translate-x-0.5 ${
                    isCurrentScene ? 'bg-blue-400' : 'bg-gray-400'
                  }`}
                  style={{ left: `${markerPosition}%` }}
                  title={`Scene ${scene.sceneNumber}: ${scene.duration}s`}
                />
              );
            })}
          </div>
          <div className="flex justify-between text-xs text-gray-300 mt-1">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(totalDuration)}</span>
          </div>
          {/* Scene Labels */}
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            {scenes.map((scene, index) => (
              <span
                key={scene.id}
                className={index === currentSceneIndex ? 'text-blue-400 font-semibold' : ''}
              >
                {scene.sceneNumber}
              </span>
            ))}
          </div>
        </div>

          {/* Control Buttons */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              {/* Play/Pause */}
              <button
                onClick={disabled ? undefined : (onPlayPause || (() => {}))}
                className={`text-white transition-colors ${
                  disabled ? 'text-gray-500 cursor-not-allowed' : 'hover:text-blue-400'
                }`}
                disabled={disabled}
              >
                {isPlaying ? (
                  <Pause className="w-8 h-8" />
                ) : (
                  <Play className="w-8 h-8" />
                )}
              </button>

              {/* Previous/Next */}
              <button
                onClick={disabled ? undefined : handlePreviousScene}
                disabled={disabled || currentSceneIndex === 0}
                className={`transition-colors ${
                  disabled || currentSceneIndex === 0
                    ? 'text-gray-500 cursor-not-allowed'
                    : 'text-white hover:text-blue-400'
                }`}
              >
                <SkipBack className="w-6 h-6" />
              </button>
              <button
                onClick={disabled ? undefined : handleNextScene}
                disabled={disabled || currentSceneIndex === scenes.length - 1}
                className={`transition-colors ${
                  disabled || currentSceneIndex === scenes.length - 1
                    ? 'text-gray-500 cursor-not-allowed'
                    : 'text-white hover:text-blue-400'
                }`}
              >
                <SkipForward className="w-6 h-6" />
              </button>

              {/* Volume */}
              <div className="flex items-center space-x-2">
                <Volume2 className="w-5 h-5 text-white" />
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={volume}
                  onChange={handleVolumeChange}
                  className="w-20 h-1 bg-gray-600 rounded-lg appearance-none cursor-pointer"
                  style={{
                    background: `linear-gradient(to right, #3B82F6 0%, #3B82F6 ${volume * 100}%, #4B5563 ${volume * 100}%, #4B5563 100%)`
                  }}
                />
              </div>
            </div>

            {/* Fullscreen */}
            <button
              onClick={disabled ? undefined : handleFullscreen}
              className={`transition-colors ${
                disabled ? 'text-gray-500 cursor-not-allowed' : 'text-white hover:text-blue-400'
              }`}
              disabled={disabled}
            >
              <Maximize2 className="w-6 h-6" />
            </button>
          </div>
        </div>
      </div>

      {/* Video error indicator */}
      {videoError && currentScene.video_url && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/80">
          <div className="text-center text-white">
            <p className="text-lg font-semibold mb-2">Video Failed to Load</p>
            <p className="text-sm text-gray-300">Falling back to image preview</p>
          </div>
        </div>
      )}


    </div>
  );
};

export default VideoPreview;