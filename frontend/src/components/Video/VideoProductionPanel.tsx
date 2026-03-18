// src/components/Video/VideoProductionPanel.tsx
import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import {
  Video,
  Download,
  RefreshCw,
  Film,
  Monitor
} from 'lucide-react';
import { useVideoProduction } from '../../hooks/useVideoProduction';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';
import SceneTimeline from './SceneTimeline';
import EditorSettingsPanel from './EditorSettingsPanel';
import VideoPreview from './VideoPreview';
import RenderingProgress from './RenderingProgress';
import type { VideoScene } from '../../types/videoProduction';
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
  acts: unknown[];
  beats: unknown[];
  scenes: unknown[];
  created_at: string;
  status: 'draft' | 'ready' | 'approved';
}

interface GenerationProgress {
  overall: number;
  currentStep: string;
  stepProgress: {
    image_generation: { status: string; progress: number };
    audio_generation: { status: string; progress: number };
    video_generation: { status: string; progress: number };
    audio_video_merge: { status: string; progress: number };
  };
}

interface VideoProductionPanelProps {
  chapterId: string;
  chapterTitle: string;
  imageUrls?: string[];
  audioFiles?: string[];
  onGenerateVideo?: (selectedShotIds?: string[], overrideAudioIds?: string[]) => void;
  videoStatus?: string | null;
  canGenerateVideo?: boolean;
  videoUrl?: string; // Final generated video URL from API response
  videoGenerations?: any[]; // All generations for this chapter
  selectedScript?: ChapterScript | null; // Script data for synchronization
  generatingShotIds?: Set<string>; // Shot IDs currently being generated
  generationProgress?: GenerationProgress; // Progress data from polling
  onDeleteGeneration?: (genId: string) => void; // Callback to delete a failed generation
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
  videoGenerations = [],
  selectedScript,
  generatingShotIds = new Set(),
  generationProgress,
  onDeleteGeneration
}) => {
  const {
    selectedScriptId,
    isSwitching
  } = useScriptSelection();

  const storyboardContext = useStoryboardOptional();
  
  // Build scene metadata from storyboard including shotType
  // Returns array of { url, sceneNumber, shotType, shotIndex } for proper scene initialization
  const filteredSceneData = React.useMemo(() => {
    if (!storyboardContext) {
      // Fallback to simple URLs when no context
      return imageUrls.map((url, idx) => ({
        url,
        sceneNumber: idx + 1,
        shotType: 'key_scene' as const,
        shotIndex: 0,
      }));
    }
    
    const { sceneImagesMap, excludedImageIds, selectedSceneImages, imageOrderByScene } = storyboardContext;
    
    // If we have scene images map, use it to get all non-excluded images with metadata
    if (Object.keys(sceneImagesMap).length > 0) {
      const allIncludedScenes: Array<{
        url: string;
        sceneNumber: number;
        shotType: 'key_scene' | 'suggested_shot';
        shotIndex: number;
        imageId: string;
      }> = [];
      
      // Sort by scene number and get all non-excluded images with their metadata
      Object.entries(sceneImagesMap)
        .sort(([a], [b]) => parseInt(a) - parseInt(b))
        .forEach(([sceneNumStr, images]) => {
          const sceneNumber = parseInt(sceneNumStr);
          const sceneOrder = imageOrderByScene[sceneNumber] || [];
          
          // Sort images by their position in imageOrderByScene if available
          const sortedImages = sceneOrder.length > 0
            ? [...images].sort((a, b) => {
                const aIndex = sceneOrder.indexOf(a.id);
                const bIndex = sceneOrder.indexOf(b.id);
                // If not in order array, put at end
                return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
              })
            : images;
          
          sortedImages.forEach((img, idx) => {
            // Include image if it's not in excluded list
            if (!excludedImageIds.has(img.id) && img.url) {
              allIncludedScenes.push({
                url: img.url,
                sceneNumber,
                shotType: img.shotType || 'key_scene',
                shotIndex: (img.shotIndex !== undefined) ? img.shotIndex : idx,  // Use metadata shotIndex if available, else position
                imageId: img.id,
              });
            }
          });
        });
      
      if (allIncludedScenes.length > 0) {
        return allIncludedScenes;
      }
    }
    
    // Fallback: If we only have selectedSceneImages, use those as key scenes
    if (Object.keys(selectedSceneImages).length > 0) {
      return Object.entries(selectedSceneImages)
        .sort(([a], [b]) => parseInt(a) - parseInt(b))
        .filter(([, url]) => url)
        .map(([sceneNumStr, url]) => ({
          url,
          sceneNumber: parseInt(sceneNumStr),
          shotType: 'key_scene' as const,
          shotIndex: 0,
        }));
    }
    
    // Otherwise, return all images as key scenes
    return imageUrls.map((url, idx) => ({
      url,
      sceneNumber: idx + 1,
      shotType: 'key_scene' as const,
      shotIndex: 0,
    }));
  }, [imageUrls, storyboardContext]);

  // Extract just URLs for useVideoProduction (backward compatible)
  const filteredImageUrls = React.useMemo(() => 
    filteredSceneData.map(s => s.url), 
    [filteredSceneData]
  );

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
  } = useVideoProduction({
    chapterId,
    scriptId: selectedScriptId || undefined,
    imageUrls: filteredImageUrls,
    sceneMetadata: filteredSceneData, // Pass scene data with shotType/shotIndex
    audioFiles
  });

  // Enrich scenes with generation status and video URLs from videoGenerations
  const enrichedScenes = React.useMemo(() => {
    if (!videoGenerations || videoGenerations.length === 0) return scenes;

    return scenes.map(scene => {
      let foundVideoUrl: string | undefined = undefined;
      let foundStatus = scene.status;

      for (const gen of videoGenerations) {
        const clips = gen.video_data?.scene_videos || [];
        
        const matchedClip = clips.find((sv: any) => {
          if (!sv) return false;
          const sameSceneNumber =
            sv.scene_number === scene.sceneNumber ||
            sv.scene_id === `scene_${scene.sceneNumber}`;

          if (
            sameSceneNumber &&
            typeof sv.shot_index === 'number' &&
            typeof scene.shotIndex === 'number'
          ) {
            return sv.shot_index === scene.shotIndex;
          }

          if (scene.imageUrl && sv.target_image) {
            if (sv.target_image === scene.imageUrl) return true;
            const selectedFilename = scene.imageUrl.split('/').pop()?.split('?')[0];
            const targetFilename = sv.target_image.split('/').pop()?.split('?')[0];
            if (selectedFilename && targetFilename && selectedFilename === targetFilename) return true;
          }

          if (scene.imageUrl && sv.source_image) {
            if (sv.source_image === scene.imageUrl) return true;
            const selectedFilename = scene.imageUrl.split('/').pop()?.split('?')[0];
            const svFilename = sv.source_image.split('/').pop()?.split('?')[0];
            if (selectedFilename && svFilename && selectedFilename === svFilename) return true;
          }
          if (sameSceneNumber && typeof scene.shotIndex !== 'number') return true;
          // IMPORTANT: Do NOT match sv.scene_sequence to scene.sceneNumber, 
          // as scene_sequence is the batch sequence index, not the absolute script scene number!
          return false;
        });

        // Also check if the generation explicitly targeted this scene ID via task_meta
        const targetedSceneIds = gen.task_meta?.selected_shot_ids || [];
        const matchesTarget = targetedSceneIds.includes(scene.id) || targetedSceneIds.includes('__all__');

        if (matchedClip || (matchesTarget && gen.generation_status === 'failed')) {
          if (matchedClip?.video_url) {
            foundVideoUrl = matchedClip.video_url;
            foundStatus = 'completed';
            break; // Found the most recent successful generation for this scene
          } else if (gen.generation_status === 'failed') {
            foundStatus = 'error';
            // Continue looking to see if an older generation actually succeeded
          }
        }
      }

      return {
        ...scene,
        video_url: foundVideoUrl || scene.video_url,
        status: foundStatus !== 'pending' ? foundStatus : scene.status
      };
    });
  }, [scenes, videoGenerations]);

  const [activeView, setActiveView] = useState<'timeline' | 'preview'>('timeline');
  const [selectedSceneIndex, setSelectedSceneIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedShotIds, setSelectedShotIds] = useState<string[]>([]);
  
  const handleScenePreviewChange = React.useCallback((index: number) => {
    setSelectedSceneIndex(index);
  }, []);

  // Helper to toggle individual shot selection for per-shot video generation
  const toggleShotSelection = (shotId: string) => {
    setSelectedShotIds(prev => 
      prev.includes(shotId) 
        ? prev.filter(id => id !== shotId)
        : [...prev, shotId]
    );
  };

  // Disable actions during switching or loading
  const controlsDisabled = isSwitching || isLoading;

  // Delay scene initialization until script switch completes
  // Uses filteredImageUrls from Images tab storyboard (not Audio tab)
  useEffect(() => {
    if (selectedScriptId && !scenes.length && filteredImageUrls.length && !isSwitching) {
      const timeoutId = window.setTimeout(() => {
        if (!isSwitching) {
          console.log(`[VideoProductionPanel] Initializing scenes with ${filteredImageUrls.length} images from Images tab storyboard`);
          initializeScenes();
        }
      }, 100);
      return () => window.clearTimeout(timeoutId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedScriptId, filteredImageUrls.length, scenes.length, isSwitching]);

  // Guarded empty state for no selected script
  if (!selectedScriptId) {
    return (
      <div className="p-4 text-sm text-gray-500">
        Select a script to manage video production.
      </div>
    );
  }

  // Guarded empty state for no scenes with selected script
  if (!enrichedScenes.length && selectedScriptId) {
    return (
      <div className="p-4 text-sm text-gray-500">
        No scenes available for the selected script. Generate images and audio first.
      </div>
    );
  }

  const handleSceneSelect = (scene: VideoScene) => {
    // Find the index of the scene in the scenes array
    const index = enrichedScenes.findIndex(s => s.id === scene.id);
    setSelectedSceneIndex(index >= 0 ? index : 0);
  };


  const handleDownload = (quality?: 'low' | 'medium' | 'high' | 'ultra') => {
    downloadVideo(quality);
  };


  const getTotalDuration = () => {
    return enrichedScenes.reduce((total, scene) => total + scene.duration, 0);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-3">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Video Production Studio
            </h3>
            <div className="flex items-center space-x-2">
              <span className="text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 px-2 py-1 rounded">
                Active script: {selectedScriptId.substring(0, 8)}...
              </span>
              {isSwitching && (
                <span className="text-xs text-gray-500 dark:text-gray-400">Switching script...</span>
              )}
            </div>
          </div>
          <p className="text-gray-600 dark:text-gray-400">
            Create and edit your video for "{chapterTitle}"
          </p>
        </div>
      </div>
      {/* Video Generation Controls */}
      <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg mb-4">
        <div className="flex items-center justify-between">
          {/* Selection Info */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {selectedShotIds.length > 0 
                ? `${selectedShotIds.length} shot${selectedShotIds.length > 1 ? 's' : ''} selected`
                : 'Click checkboxes on shots to select for generation'}
            </span>
            {selectedShotIds.length > 0 && (
              <button
                onClick={() => setSelectedShotIds([])}
                className="text-xs text-blue-500 hover:text-blue-700 underline"
              >
                Clear selection
              </button>
            )}
          </div>
          
          {/* Generation Buttons */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => onGenerateVideo?.(selectedShotIds)}
              disabled={controlsDisabled || !canGenerateVideo || selectedShotIds.length === 0}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              <Video className="w-4 h-4" />
              <span>
                {videoStatus === "processing" || videoStatus === "starting"
                  ? "Generating..."
                  : `Generate Selected (${selectedShotIds.length})`}
              </span>
            </button>
            <button
              onClick={() => onGenerateVideo?.()}
              disabled={controlsDisabled || !canGenerateVideo}
              className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              <Video className="w-4 h-4" />
              <span>
                {videoStatus === "processing" || videoStatus === "starting"
                  ? "Generating..."
                  : "Generate All Videos"}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Generation Progress */}
      {generatingShotIds.size > 0 && generationProgress && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
              {generationProgress.currentStep || 'Starting generation...'}
            </span>
            <span className="text-sm text-blue-600 dark:text-blue-400">
              {generationProgress.overall}%
            </span>
          </div>
          <div className="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${generationProgress.overall}%` }}
            />
          </div>
        </div>
      )}

      {/* View Tabs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border dark:border-gray-700">
        <div className="border-b dark:border-gray-700">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            <button
              onClick={() => setActiveView('timeline')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'timeline'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
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
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Monitor className="w-4 h-4" />
                <span>Preview</span>
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
            <div className="space-y-4">
              {/* Inline Settings Panel (compact mode) */}
              <EditorSettingsPanel
                settings={editorSettings}
                onUpdateSettings={updateEditorSettings}
                compact={true}
                userTier="free"
              />
              
              {/* Scene Timeline */}
              <SceneTimeline
                scenes={enrichedScenes}
                onSceneSelect={handleSceneSelect}
                onSceneUpdate={updateScene}
                onReorder={reorderScenes}
                onAddTransition={addTransition}
                selectedScript={selectedScript}
                selectedShotIds={selectedShotIds}
                onToggleShotSelection={toggleShotSelection}
                generatingShotIds={generatingShotIds}
                onGenerateVideo={onGenerateVideo}
              />
            </div>
          )}

          {activeView === 'preview' && (
            <VideoPreview
              scenes={enrichedScenes}
              currentSceneIndex={selectedSceneIndex}
              isPlaying={isPlaying}
              onPlayPause={() => setIsPlaying(!isPlaying)}
              onSceneChange={handleScenePreviewChange}
              videoUrl={videoUrl}
              videoGenerations={videoGenerations}
              selectedScript={selectedScript}
              selectedScene={enrichedScenes[selectedSceneIndex] || null}
              onDeleteGeneration={onDeleteGeneration}
            />
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
      {!enrichedScenes.length && !isLoading && (
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
