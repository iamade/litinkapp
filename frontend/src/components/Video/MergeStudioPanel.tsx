import React, { useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { Save, Video, ArrowUp, ArrowDown, CheckCircle2 } from 'lucide-react';
import { useVideoProduction } from '../../hooks/useVideoProduction';
import { useScriptSelection } from '../../contexts/ScriptSelectionContext';
import { useStoryboardOptional } from '../../contexts/StoryboardContext';

interface MergeStudioPanelProps {
  chapterId: string;
  chapterTitle: string;
  imageUrls?: string[];
  audioFiles?: string[];
  videoGenerations?: any[];
  canRender?: boolean;
  isRenderInProgress?: boolean;
  onRenderVideo?: () => void;
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
    reorderScenes,
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

  if (!enrichedScenes.length) {
    return (
      <div className="p-4 text-sm text-gray-500">
        No scenes available. Generate scene videos first in the Video tab.
      </div>
    );
  }

  const generatedCount = enrichedScenes.filter((scene) => !!scene.video_url).length;
  const allScenesHaveVideos = generatedCount === enrichedScenes.length;

  const handleRender = () => {
    if (!onRenderVideo) {
      toast.error('Render is not available right now.');
      return;
    }
    onRenderVideo();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Merge Studio</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Assemble scene videos for "{chapterTitle}" and render the final output.
          </p>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Generated scenes: {generatedCount}/{enrichedScenes.length}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={saveProduction}
            disabled={isLoading || isSwitching || !enrichedScenes.length}
            className="flex items-center gap-2 rounded-lg bg-gray-600 px-4 py-2 text-white hover:bg-gray-700 disabled:cursor-not-allowed disabled:bg-gray-400"
          >
            <Save className="h-4 w-4" />
            <span>Save</span>
          </button>
          <button
            onClick={handleRender}
            disabled={isLoading || isSwitching || isRenderInProgress || !canRender || !allScenesHaveVideos}
            className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-400"
            title={!allScenesHaveVideos ? 'Render is enabled after all scenes have generated videos' : undefined}
          >
            <Video className="h-4 w-4" />
            <span>{isRenderInProgress ? 'Rendering...' : 'Render Video'}</span>
          </button>
        </div>
      </div>

      {!allScenesHaveVideos && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
          Render is disabled until every scene has a generated video.
        </div>
      )}

      <div className="space-y-3">
        {enrichedScenes.map((scene, index) => {
          const hasVideo = Boolean(scene.video_url);
          return (
            <div
              key={scene.id}
              className="flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800 md:flex-row md:items-center"
            >
              <div className="h-24 w-full overflow-hidden rounded-md bg-gray-100 md:w-40">
                {hasVideo ? (
                  <video
                    src={scene.video_url}
                    className="h-full w-full object-cover"
                    muted
                    playsInline
                    preload="metadata"
                  />
                ) : (
                  <img src={scene.imageUrl} alt={`Scene ${scene.sceneNumber}`} className="h-full w-full object-cover" />
                )}
              </div>

              <div className="flex-1">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-gray-100">
                  <span>Scene {scene.sceneNumber}</span>
                  {scene.shotType && (
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                      {scene.shotType === 'key_scene' ? 'Key scene' : 'Suggested shot'}
                    </span>
                  )}
                  {hasVideo ? (
                    <span className="inline-flex items-center gap-1 rounded bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-300">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Video ready
                    </span>
                  ) : (
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                      Awaiting video
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Duration: {scene.duration}s</p>
              </div>

              <div className="flex items-center gap-2 self-end md:self-center">
                <button
                  onClick={() => reorderScenes(index, index - 1)}
                  disabled={index === 0 || isLoading || isSwitching}
                  className="rounded border border-gray-300 p-2 text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                  title="Move up"
                >
                  <ArrowUp className="h-4 w-4" />
                </button>
                <button
                  onClick={() => reorderScenes(index, index + 1)}
                  disabled={index === enrichedScenes.length - 1 || isLoading || isSwitching}
                  className="rounded border border-gray-300 p-2 text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                  title="Move down"
                >
                  <ArrowDown className="h-4 w-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MergeStudioPanel;
