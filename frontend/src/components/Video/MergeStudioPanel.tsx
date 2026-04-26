import React, { useEffect } from 'react';
import { Video } from 'lucide-react';
import { useVideoProduction } from '../../hooks/useVideoProduction';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';
import { useStoryboardOptional } from '../../contexts/StoryboardContext';
import MergePanel from './MergePanel';

interface MergeStudioClip {
  video_url?: string;
  duration?: number;
  scene_number?: number;
  scene_id?: string;
  shot_index?: number;
  target_image?: string;
  source_image?: string;
  status?: string;
}

interface MergeStudioGeneration {
  scene_videos?: MergeStudioClip[];
  video_data?: {
    scene_videos?: MergeStudioClip[];
  };
}

interface MergeStudioPanelProps {
  chapterId: string;
  chapterTitle: string;
  imageUrls?: string[];
  audioFiles?: string[];
  videoGenerations?: MergeStudioGeneration[];
  canRender?: boolean;
  isRenderInProgress?: boolean;
  onRenderVideo?: () => void;
  userTier?: 'free' | 'basic' | 'pro' | 'enterprise';
}

const MergeStudioPanel: React.FC<MergeStudioPanelProps> = ({
  chapterId,
  chapterTitle,
  imageUrls = [],
  audioFiles = [],
  videoGenerations = [],
  canRender = false,
  isRenderInProgress = false,
  onRenderVideo,
  userTier = 'free',
}) => {
  const { selectedScriptId, isSwitching } = useScriptSelection();
  const storyboardContext = useStoryboardOptional();

  const filteredSceneData = React.useMemo(() => {
    if (!storyboardContext) {
      return imageUrls.map((url, idx) => ({
        url,
        sceneNumber: idx + 1,
        shotType: 'key_scene' as const,
        shotIndex: 0,
      }));
    }

    const { sceneImagesMap, excludedImageIds, selectedSceneImages, imageOrderByScene } = storyboardContext;

    if (Object.keys(sceneImagesMap).length > 0) {
      const allIncludedScenes: Array<{
        url: string;
        sceneNumber: number;
        shotType: 'key_scene' | 'suggested_shot';
        shotIndex: number;
      }> = [];

      Object.entries(sceneImagesMap)
        .sort(([a], [b]) => parseInt(a, 10) - parseInt(b, 10))
        .forEach(([sceneNumStr, images]) => {
          const sceneNumber = parseInt(sceneNumStr, 10);
          const sceneOrder = imageOrderByScene[sceneNumber] || [];

          const sortedImages = sceneOrder.length > 0
            ? [...images].sort((a, b) => {
                const aIndex = sceneOrder.indexOf(a.id);
                const bIndex = sceneOrder.indexOf(b.id);
                return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
              })
            : images;

          sortedImages.forEach((img, idx) => {
            if (!excludedImageIds.has(img.id) && img.url) {
              allIncludedScenes.push({
                url: img.url,
                sceneNumber,
                shotType: img.shotType || 'key_scene',
                shotIndex: img.shotIndex !== undefined ? img.shotIndex : idx,
              });
            }
          });
        });

      if (allIncludedScenes.length > 0) {
        return allIncludedScenes;
      }
    }

    if (Object.keys(selectedSceneImages).length > 0) {
      return Object.entries(selectedSceneImages)
        .sort(([a], [b]) => parseInt(a, 10) - parseInt(b, 10))
        .filter(([, url]) => url)
        .map(([sceneNumStr, url]) => ({
          url,
          sceneNumber: parseInt(sceneNumStr, 10),
          shotType: 'key_scene' as const,
          shotIndex: 0,
        }));
    }

    return imageUrls.map((url, idx) => ({
      url,
      sceneNumber: idx + 1,
      shotType: 'key_scene' as const,
      shotIndex: 0,
    }));
  }, [imageUrls, storyboardContext]);

  const filteredImageUrls = React.useMemo(
    () => filteredSceneData.map((scene) => scene.url),
    [filteredSceneData]
  );

  const {
    scenes,
    isLoading,
    initializeScenes,
    editorSettings,
    saveProduction,
  } = useVideoProduction({
    chapterId,
    scriptId: selectedScriptId || undefined,
    imageUrls: filteredImageUrls,
    sceneMetadata: filteredSceneData,
    audioFiles,
  });

  const enrichedScenes = React.useMemo(() => {
    if (!videoGenerations || videoGenerations.length === 0) return scenes;

    return scenes.map((scene) => {
      let foundVideoUrl: string | undefined;
      let foundStatus = scene.status;

      for (const gen of videoGenerations) {
        const clips = gen.video_data?.scene_videos || gen.scene_videos || [];

        const matchedClip = clips.find((sv) => {
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
            const sourceFilename = sv.source_image.split('/').pop()?.split('?')[0];
            if (selectedFilename && sourceFilename && selectedFilename === sourceFilename) return true;
          }

          if (sameSceneNumber && typeof scene.shotIndex !== 'number') return true;
          return false;
        });

        if (matchedClip?.video_url) {
          foundVideoUrl = matchedClip.video_url;
          foundStatus = 'completed';
          break;
        }
      }

      return {
        ...scene,
        video_url: foundVideoUrl || scene.video_url,
        status: foundStatus !== 'pending' ? foundStatus : scene.status,
      };
    });
  }, [scenes, videoGenerations]);

  useEffect(() => {
    if (selectedScriptId && !scenes.length && filteredImageUrls.length && !isSwitching) {
      const timeoutId = window.setTimeout(() => {
        if (!isSwitching) {
          initializeScenes();
        }
      }, 100);
      return () => window.clearTimeout(timeoutId);
    }
  }, [selectedScriptId, scenes.length, filteredImageUrls.length, isSwitching, initializeScenes]);

  if (!selectedScriptId) {
    return (
      <div className="p-4 text-sm text-gray-500">
        Select a script to open Merge Studio.
      </div>
    );
  }

  const generatedCount = enrichedScenes.filter((scene) => !!scene.video_url).length;
  const allScenesHaveVideos = enrichedScenes.length > 0 && generatedCount === enrichedScenes.length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            Merge Studio
          </p>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{chapterTitle}</h3>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Use Tracks, Controls, and Preview to assemble generated scene videos with audio before starting the final merge.
          </p>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Generated scenes: {generatedCount}/{enrichedScenes.length}
          </p>
        </div>

        {!allScenesHaveVideos && onRenderVideo && (
          <button
            type="button"
            onClick={onRenderVideo}
            disabled={isLoading || isSwitching || isRenderInProgress || !canRender}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
            title="Generate missing scene videos before merging"
          >
            <Video className="h-4 w-4" />
            <span>{isRenderInProgress ? 'Generating...' : 'Generate Missing Videos'}</span>
          </button>
        )}
      </div>

      {!allScenesHaveVideos && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
          Merge can be configured now, but the final output needs generated video clips for every scene.
        </div>
      )}

      <MergePanel
        chapterId={chapterId}
        scriptId={selectedScriptId}
        videoGenerations={videoGenerations}
        audioFiles={audioFiles}
        scenes={enrichedScenes}
        editorSettings={editorSettings}
        userTier={userTier}
      />

      <div className="flex justify-end">
        <button
          type="button"
          onClick={saveProduction}
          disabled={isLoading || isSwitching || !enrichedScenes.length}
          className="rounded-lg bg-gray-600 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:cursor-not-allowed disabled:bg-gray-400"
        >
          Save scene order
        </button>
      </div>
    </div>
  );
};

export default MergeStudioPanel;
