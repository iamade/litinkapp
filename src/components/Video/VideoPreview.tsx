import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, SkipBack, SkipForward, Volume2, Maximize2 } from 'lucide-react';
import { VideoScene } from '../../types/videoProduction';

interface VideoPreviewProps {
  scenes: VideoScene[];
  currentSceneIndex?: number;
  isPlaying: boolean;
  onSceneChange?: (index: number) => void;
  onPlayPause?: () => void;
}

const VideoPreview: React.FC<VideoPreviewProps> = (props) => {
  const { scenes, currentSceneIndex = 0, isPlaying, onSceneChange, onPlayPause } = props;
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [showControls, setShowControls] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);
  const controlsTimeoutRef = useRef<NodeJS.Timeout>();

  const currentScene = scenes && scenes[currentSceneIndex];
  const totalDuration = scenes ? scenes.reduce((sum, scene) => sum + scene.duration, 0) : 0;

  useEffect(() => {
    if (!scenes) return;
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
  }, [currentTime, scenes, currentSceneIndex, onSceneChange]);

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

  if (!currentScene) {
    return (
      <div className="bg-black rounded-lg aspect-video flex items-center justify-center">
        <p className="text-gray-400">No scene selected</p>
      </div>
    );
  }

  return (
    <div 
      className="relative bg-black rounded-lg overflow-hidden group"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setShowControls(false)}
    >
      {/* Video/Image Display */}
      <div className="aspect-video relative">
        {currentScene.imageUrl ? (
          <img
            src={currentScene.imageUrl}
            alt={`Scene ${currentScene.sceneNumber}`}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gray-900">
            <p className="text-gray-400">Scene {currentScene.sceneNumber}</p>
          </div>
        )}

        {/* Scene Info Overlay */}
        <div className="absolute top-4 left-4 bg-black/70 text-white px-3 py-1 rounded">
          Scene {currentScene.sceneNumber} of {scenes.length}
        </div>

        {/* Controls Overlay */}
        <div className={`absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-4 transition-opacity duration-300 ${
          showControls ? 'opacity-100' : 'opacity-0'
        }`}>
          {/* Progress Bar */}
          <div className="mb-4">
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
            <div className="flex justify-between text-xs text-gray-300 mt-1">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(totalDuration)}</span>
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

              {/* Previous/Next */}
              <button
                onClick={handlePreviousScene}
                disabled={currentSceneIndex === 0}
                className="text-white hover:text-blue-400 disabled:text-gray-600 transition-colors"
              >
                <SkipBack className="w-6 h-6" />
              </button>
              <button
                onClick={handleNextScene}
                disabled={currentSceneIndex === scenes.length - 1}
                className="text-white hover:text-blue-400 disabled:text-gray-600 transition-colors"
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
              onClick={handleFullscreen}
              className="text-white hover:text-blue-400 transition-colors"
            >
              <Maximize2 className="w-6 h-6" />
            </button>
          </div>
        </div>
      </div>

      {/* Hidden video element for future video playback */}
      <video
        ref={videoRef}
        className="hidden"
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
      />
    </div>
  );
};

export default VideoPreview;