// src/components/Video/VideoProductionPanel.tsx
import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import {
  Video,
  Download,
  Settings,
  Save,
  RefreshCw,
  Film,
  Layers,
  Monitor
} from 'lucide-react';
import { useVideoProduction } from '../../hooks/useVideoProduction';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';
import SceneTimeline from './SceneTimeline';
import EditorSettingsPanel from './EditorSettingsPanel';
import VideoPreview from './VideoPreview';
import RenderingProgress from './RenderingProgress';
import MergePanel from './MergePanel';
import type { VideoScene } from '../../types/videoProduction';

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
  acts: unknown[];
  beats: unknown[];
  scenes: unknown[];
  created_at: string;
  status: 'draft' | 'ready' | 'approved';
}

interface VideoProductionPanelProps {
  chapterId: string;
  chapterTitle: string;
  imageUrls?: string[];
  audioFiles?: string[];
  onGenerateVideo?: () => void;
  videoStatus?: string | null;
  canGenerateVideo?: boolean;
  videoUrl?: string; // Final generated video URL from API response
  selectedScript?: ChapterScript | null; // Script data for synchronization
}

const VideoProductionPanel: React.FC<VideoProductionPanelProps> = ({
  chapterId,
  chapterTitle,
  imageUrls = [],
  audioFiles = [],
  onGenerateVideo,
  videoStatus,
  canGenerateVideo,
  videoUrl,
  selectedScript
}) => {
  const {
    selectedScriptId,
    isSwitching
  } = useScriptSelection();

  // Move hooks before any conditional returns
  const {
    videoProduction,
    scenes,
    editorSettings,
    isLoading,
    isRendering,
    renderingProgress,
    initializeScenes,
    updateScene,
    reorderScenes,
    addTransition,
    updateEditorSettings,
    processWithFFmpeg,
    downloadVideo,
    saveProduction
  } = useVideoProduction({
    chapterId,
    scriptId: selectedScriptId || undefined,
    imageUrls,
    audioFiles
  });

  const [activeView, setActiveView] = useState<'timeline' | 'preview' | 'settings' | 'merge'>('timeline');
  const [selectedScene, setSelectedScene] = useState<VideoScene | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // Disable actions during switching or loading
  const controlsDisabled = isSwitching || isLoading;

  // Delay scene initialization until script switch completes
  useEffect(() => {
    if (selectedScriptId && !scenes.length && imageUrls.length && !isSwitching) {
      const timeoutId = window.setTimeout(() => {
        if (!isSwitching) {
          initializeScenes();
        }
      }, 100);
      return () => window.clearTimeout(timeoutId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedScriptId, imageUrls, scenes.length, isSwitching]);

  // Guarded empty state for no selected script
  if (!selectedScriptId) {
    return (
      <div className="p-4 text-sm text-gray-500">
        Select a script to manage video production.
      </div>
    );
  }

  // Guarded empty state for no scenes with selected script
  if (!scenes.length && selectedScriptId) {
    return (
      <div className="p-4 text-sm text-gray-500">
        No scenes available for the selected script. Generate images and audio first.
      </div>
    );
  }

  const handleSceneSelect = (scene: VideoScene) => {
    setSelectedScene(scene);
    setActiveView('preview');
  };


  const handleDownload = (quality?: 'low' | 'medium' | 'high' | 'ultra') => {
    downloadVideo(quality);
  };

  const getTotalDuration = () => {
    return scenes.reduce((total, scene) => total + scene.duration, 0);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-3">
            <h3 className="text-xl font-semibold text-gray-900">
              Video Production Studio
            </h3>
            <div className="flex items-center space-x-2">
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                Active script: {selectedScriptId.substring(0, 8)}...
              </span>
              {isSwitching && (
                <span className="text-xs text-gray-500">Switching script...</span>
              )}
            </div>
          </div>
          <p className="text-gray-600">
            Create and edit your video for "{chapterTitle}"
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={saveProduction}
            disabled={controlsDisabled || !scenes.length}
            className="flex items-center space-x-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:bg-gray-400"
          >
            <Save className="w-4 h-4" />
            <span>Save</span>
          </button>
          {/* Repurposed Render Video button (disabled for now) */}
          <button
            onClick={() => toast('This button will be repurposed for a new function.')}
            disabled={controlsDisabled}
            className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400"
          >
            <Video className="w-4 h-4" />
            <span>Render Video</span>
          </button>
        </div>
      </div>
      {/* Generate Video Button */}
      <div className="flex justify-end">
        <button
          onClick={onGenerateVideo}
          disabled={controlsDisabled || !canGenerateVideo}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          <Video className="w-4 h-4" />
          <span>
            {videoStatus === "processing" || videoStatus === "starting"
              ? "Generating Video..."
              : "Generate Video"}
          </span>
        </button>
      </div>

      {/* View Tabs */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="border-b">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            <button
              onClick={() => setActiveView('timeline')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'timeline'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Film className="w-4 h-4" />
                <span>Timeline</span>
              </div>
            </button>
            <button
              onClick={() => setActiveView('preview')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'preview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Monitor className="w-4 h-4" />
                <span>Preview</span>
              </div>
            </button>
            <button
              onClick={() => setActiveView('settings')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'settings'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Settings className="w-4 h-4" />
                <span>Settings</span>
              </div>
            </button>
            <button
              onClick={() => setActiveView('merge')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'merge'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Layers className="w-4 h-4" />
                <span>Merge</span>
              </div>
            </button>
          </nav>
        </div>

        {/* Content Area */}
        <div className="p-6">
          {isRendering && (
            <RenderingProgress
              progress={renderingProgress}
              status="rendering"
              currentStep="Processing video scenes..."
            />
          )}

          {activeView === 'timeline' && (
            <SceneTimeline
              scenes={scenes}
              onSceneSelect={handleSceneSelect}
              onSceneUpdate={updateScene}
              onReorder={reorderScenes}
              onAddTransition={addTransition}
              selectedScript={selectedScript}
            />
          )}

          {activeView === 'preview' && (
            <VideoPreview
              scenes={scenes}
              currentSceneIndex={selectedScene ? scenes.findIndex(s => s.id === selectedScene.id) : 0}
              isPlaying={isPlaying}
              onPlayPause={() => setIsPlaying(!isPlaying)}
              onSceneChange={(index) => setSelectedScene(scenes[index])}
              videoUrl={videoUrl}
              selectedScript={selectedScript}
            />
          )}

          {activeView === 'settings' && (
            <EditorSettingsPanel
              settings={editorSettings}
              onUpdateSettings={updateEditorSettings}
            />
          )}

          {activeView === 'merge' && (
            <MergePanel />
          )}
        </div>
      </div>

      {/* Video Info & Actions */}
      {videoProduction?.finalVideoUrl && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="text-lg font-semibold text-gray-900">
                Rendered Video
              </h4>
              <div className="flex items-center space-x-4 mt-2 text-sm text-gray-600">
                <span>Duration: {getTotalDuration()}s</span>
                <span>•</span>
                <span>Resolution: {editorSettings.resolution}</span>
                <span>•</span>
                <span>Format: {editorSettings.outputFormat.toUpperCase()}</span>
                {videoProduction.metadata?.fileSize && (
                  <>
                    <span>•</span>
                    <span>Size: {(videoProduction.metadata.fileSize / 1024 / 1024).toFixed(2)} MB</span>
                  </>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => processWithFFmpeg()}
                disabled={controlsDisabled}
                className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:bg-gray-400"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Reprocess</span>
              </button>
              <div className="relative group">
                <button
                  disabled={controlsDisabled}
                  className="flex items-center space-x-2 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-gray-400"
                >
                  <Download className="w-3 h-3" />
                  <span>Download</span>
                </button>
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                  <button
                    onClick={() => handleDownload('low')}
                    className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-50"
                  >
                    Low Quality (480p)
                  </button>
                  <button
                    onClick={() => handleDownload('medium')}
                    className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-50"
                  >
                    Medium Quality (720p)
                  </button>
                  <button
                    onClick={() => handleDownload('high')}
                    className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-50"
                  >
                    High Quality (1080p)
                  </button>
                  <button
                    onClick={() => handleDownload('ultra')}
                    className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-50"
                  >
                    Ultra Quality (4K)
                  </button>
                </div>
              </div>
            </div>
          </div>

          <video
            src={videoProduction.finalVideoUrl}
            controls
            className="w-full rounded-lg"
          />
        </div>
      )}

      {/* Empty State */}
      {!scenes.length && !isLoading && (
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <Video className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No scenes available
          </h3>
          <p className="text-gray-600 mb-4">
            Generate images and audio first to create video scenes
          </p>
          <button
            onClick={initializeScenes}
            disabled={controlsDisabled || !imageUrls.length}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            Initialize Scenes
          </button>
        </div>
      )}
    </div>
  );
};

export default VideoProductionPanel;
