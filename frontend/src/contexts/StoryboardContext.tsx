// src/contexts/StoryboardContext.tsx
// Shared state for storyboard selections across Audio and Video tabs
// KAN-143: Self-managing — subscribes to SCRIPT_CHANGED events to prevent cross-script data bleeding

import React, { createContext, useContext, useState, useCallback, useMemo, useEffect, useRef, ReactNode } from 'react';
import { useScriptSelection } from './ScriptSelectionContext';
import { userService } from '../services/userService';
import { projectService, StoryboardConfig } from '../services/projectService';

// Types for scene-audio linking
interface SceneImage {
  id: string;
  url: string;
  sceneNumber: number;
  shotType: 'key_scene' | 'suggested_shot';
  shotIndex?: number;
}

interface AudioFile {
  id: string;
  type: 'dialogue' | 'narration' | 'music' | 'effects' | 'ambiance';
  sceneNumber: number;
  shotType?: 'key_scene' | 'suggested_shot';
  shotIndex?: number; // Shot index within scene
  url?: string;
  duration?: number;
  character?: string;
  status?: string;
  text_content?: string;
  text_prompt?: string;
}

interface StoryboardState {
  // Selected image URL for each scene (sceneNumber -> imageUrl)
  selectedSceneImages: Record<number, string>;
  
  // Excluded image IDs (not shown in storyboard)
  excludedImageIds: Set<string>;
  
  // Manual overrides for audio assignment (audioId -> { sceneNumber, shotIndex })
  audioAssignments: Record<string, { sceneNumber: number; shotIndex: number }>;
  
  // Selected audio IDs for video generation
  selectedAudioIds: Set<string>;
  
  // Audio files grouped by scene number
  sceneAudioMap: Record<number, AudioFile[]>;
  
  // All available images per scene
  sceneImagesMap: Record<number, SceneImage[]>;
  
  // Image order for each scene
  imageOrderByScene: Record<number, string[]>;

  // Lifecycle status for script-scoped storyboard loading
  status: 'idle' | 'loading' | 'ready' | 'error';
  error: string | null;
}

interface StoryboardContextValue extends StoryboardState {
  // Actions
  setSelectedSceneImage: (sceneNumber: number, imageUrl: string | null) => void;
  excludeImage: (imageId: string) => void;
  includeImage: (imageId: string) => void;
  setSceneAudio: (sceneNumber: number, audioFiles: AudioFile[]) => void;
  setSceneImages: (sceneNumber: number, images: SceneImage[]) => void;
  setImageOrder: (sceneNumber: number, imageIds: string[]) => void;
  
  // Audio Assignment Actions
  assignAudioToShot: (audioId: string, sceneNumber: number, shotIndex: number) => void;
  unassignAudio: (audioId: string) => void;
  
  // Audio Selection Actions
  selectAudio: (audioId: string) => void;
  deselectAudio: (audioId: string) => void;
  toggleAudioSelection: (audioId: string) => void;
  isAudioSelected: (audioId: string) => boolean;
  
  // Computed values
  getIncludedImagesForScene: (sceneNumber: number) => SceneImage[];
  getAudioCountForScene: (sceneNumber: number) => number;
  getAudioForShot: (sceneNumber: number, shotIndex?: number) => AudioFile[]; 
  getSelectedImageForScene: (sceneNumber: number) => string | null;
  findAudioById: (audioId: string) => AudioFile | undefined;
  
  // Bulk operations
  resetStoryboard: () => void;
  importFromAudioPanel: (data: Partial<StoryboardState>) => void;
}

const StoryboardContext = createContext<StoryboardContextValue | null>(null);

// Helper: map raw audio files to AudioFile objects grouped by scene
function mapAudioFiles(rawFiles: any[], scriptId: string): Record<number, AudioFile[]> {
  const filteredAudio = rawFiles.filter((file: any) => {
    const normalizedScriptId = file.script_id ?? file.scriptId;
    return normalizedScriptId === scriptId || !normalizedScriptId;
  });

  const groupedAudio: Record<number, AudioFile[]> = {};
  filteredAudio.forEach((file: any) => {
    const metadata = file.metadata || file.audio_metadata || {};
    const rawScene = metadata?.scene ?? file.scene_id ?? file.scene_number ?? null;
    let sceneNumber = 1;
    if (typeof rawScene === 'number') {
      sceneNumber = Math.floor(rawScene);
    } else if (typeof rawScene === 'string') {
      const cleaned = rawScene.replace(/^scene_/i, '');
      const parsed = parseFloat(cleaned);
      if (!isNaN(parsed)) sceneNumber = Math.floor(parsed);
    }

    let type: AudioFile['type'] = 'narration';
    const audioType = file.audio_type || file.type;
    if (audioType === 'narrator') type = 'narration';
    else if (audioType === 'character') type = 'dialogue';
    else if (audioType === 'music' || audioType === 'background_music') type = 'music';
    else if (audioType === 'sound_effects' || audioType === 'sfx') type = 'effects';
    else if (audioType === 'ambiance' || audioType === 'ambient') type = 'ambiance';

    const mapped: AudioFile = {
      id: file.id,
      type,
      sceneNumber,
      shotType: metadata?.shot_type,
      shotIndex: typeof metadata?.shot_index === 'number' ? metadata.shot_index : undefined,
      url: file.url ?? file.audio_url,
      duration: file.duration ?? file.duration_seconds,
      character: file.character_name ?? metadata?.character_name,
      status: file.generation_status ?? file.status,
      text_content: file.text_content,
      text_prompt: file.text_prompt,
    };

    if (!groupedAudio[sceneNumber]) groupedAudio[sceneNumber] = [];
    groupedAudio[sceneNumber].push(mapped);
  });

  return groupedAudio;
}

export const StoryboardProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const {
    selectedScriptId,
    stableSelectedChapterId,
    storyboardDirty,
    isSwitching,
    getStoryboardConfig,
    loadStoryboardConfig,
    markStoryboardClean,
    subscribe,
  } = useScriptSelection();

  const [selectedSceneImages, setSelectedSceneImagesState] = useState<Record<number, string>>({});
  const [excludedImageIds, setExcludedImageIds] = useState<Set<string>>(new Set());
  const [sceneAudioMap, setSceneAudioMap] = useState<Record<number, AudioFile[]>>({});
  const [sceneImagesMap, setSceneImagesMap] = useState<Record<number, SceneImage[]>>({});
  const [imageOrderByScene, setImageOrderBySceneState] = useState<Record<number, string[]>>({});
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const [audioAssignments, setAudioAssignments] = useState<Record<string, { sceneNumber: number; shotIndex: number }>>({});
  const [selectedAudioIds, setSelectedAudioIds] = useState<Set<string>>(new Set());

  // Refs for script-change subscription lifecycle
  const scriptChangeAbortRef = useRef<AbortController | null>(null);
  const lastLoadedKeyRef = useRef<string | null>(null);
  const storyboardSnapshotRef = useRef<{
    chapterId: string | null;
    scriptId: string | null;
    storyboardDirty: boolean;
    config: StoryboardConfig;
  }>({
    chapterId: stableSelectedChapterId,
    scriptId: selectedScriptId,
    storyboardDirty,
    config: getStoryboardConfig(),
  });

  // Bulk operations (defined early — needed by useEffect hooks below)
  const resetStoryboard = useCallback(() => {
    setSelectedSceneImagesState({});
    setExcludedImageIds(new Set());
    setSceneAudioMap({});
    setSceneImagesMap({});
    setImageOrderBySceneState({});
    setAudioAssignments({});
    setSelectedAudioIds(new Set());
  }, []);

  // Keep snapshot ref up to date (but not during switching)
  useEffect(() => {
    if (isSwitching) return;
    storyboardSnapshotRef.current = {
      chapterId: stableSelectedChapterId,
      scriptId: selectedScriptId,
      storyboardDirty,
      config: getStoryboardConfig(),
    };
  }, [stableSelectedChapterId, selectedScriptId, storyboardDirty, getStoryboardConfig, isSwitching]);

  // Subscribe to SCRIPT_CHANGED events from ScriptSelectionContext
  // This handles cross-script data bleeding by auto-resetting + auto-saving
  useEffect(() => {
    const unsubscribe = subscribe((evt, payload) => {
      if (evt !== 'SCRIPT_CHANGED') return;

      const nextChapterId = payload.next.chapterId ?? stableSelectedChapterId;
      const nextScriptId = payload.next.script_id;
      const nextLoadKey = nextChapterId && nextScriptId ? `${nextChapterId}:${nextScriptId}` : null;
      lastLoadedKeyRef.current = nextLoadKey;

      const snapshot = storyboardSnapshotRef.current;
      const prevChapterId = payload.prev.chapterId ?? snapshot.chapterId;
      const prevScriptId = payload.prev.script_id ?? snapshot.scriptId;

      const run = async () => {
        // Auto-save dirty storyboard before switching away
        if (snapshot.storyboardDirty && prevChapterId && prevScriptId) {
          try {
            await projectService.saveStoryboardConfig(prevChapterId, prevScriptId, snapshot.config);
            markStoryboardClean();
          } catch (saveErr) {
            console.error('Failed to auto-save storyboard before script switch:', saveErr);
          }
        }

        if (!nextChapterId || !nextScriptId) {
          scriptChangeAbortRef.current?.abort();
          resetStoryboard();
          setStatus('idle');
          setError(null);
          return;
        }

        // Reset and reload for new script
        setStatus('loading');
        setError(null);
        resetStoryboard();

        const controller = new AbortController();
        scriptChangeAbortRef.current = controller;

        try {
          // Fetch images
          const imagesRes = await userService.getChapterImages(nextChapterId);
          if (controller.signal.aborted) return;

          const allImages = imagesRes.images || [];
          const scriptImages = allImages.filter((img: any) => {
            const normalizedScriptId = img.script_id ?? img.scriptId;
            return normalizedScriptId === nextScriptId && img.image_type === 'scene';
          });

          // Fetch storyboard config
          let config: { key_scene_images?: Record<string, string>; deselected_images?: string[]; image_order?: Record<string, string[]> } = {};
          try {
            config = await projectService.getStoryboardConfig(nextChapterId, nextScriptId);
          } catch {
            // config may not exist yet
          }
          if (controller.signal.aborted) return;

          loadStoryboardConfig(config);

          const keySceneImages: Record<string, string> = config?.key_scene_images || {};
          const deselectedImages: string[] = config?.deselected_images || [];
          const imageOrder: Record<string, string[]> = config?.image_order || {};

          // Group by scene number
          const grouped: Record<number, SceneImage[]> = {};
          scriptImages.forEach((img: any) => {
            const sceneNum = img.scene_number ?? img.metadata?.scene_number ?? 1;
            const sn = Number(sceneNum);
            if (!grouped[sn]) grouped[sn] = [];
            const isKey = keySceneImages[String(sn)] === img.id;
            grouped[sn].push({
              id: img.id,
              url: img.image_url || '',
              sceneNumber: sn,
              shotType: isKey ? 'key_scene' : 'suggested_shot',
              shotIndex: img.shot_index ?? img.metadata?.shot_index ?? grouped[sn].length,
            });
          });
          setSceneImagesMap(grouped);

          // Apply config state
          const selected: Record<number, string> = {};
          Object.entries(keySceneImages).forEach(([sceneNum, imageId]) => {
            const img = scriptImages.find((i: any) => i.id === imageId);
            if (img) selected[parseInt(sceneNum)] = img.image_url || '';
          });
          setSelectedSceneImagesState(selected);
          setExcludedImageIds(new Set(deselectedImages));

          const orderMap: Record<number, string[]> = {};
          Object.entries(imageOrder).forEach(([sceneNum, ids]) => {
            orderMap[parseInt(sceneNum)] = ids;
          });
          setImageOrderBySceneState(orderMap);

          // Fetch audio
          try {
            const audioRes = await userService.getChapterAudio(nextChapterId, nextScriptId);
            if (controller.signal.aborted) return;
            setSceneAudioMap(mapAudioFiles(audioRes?.audio_files ?? [], nextScriptId));
          } catch (audioErr: any) {
            if (audioErr.name !== 'AbortError') {
              console.error('[StoryboardContext] Failed to fetch audio data:', audioErr);
            }
          }

          if (!controller.signal.aborted) {
            setStatus('ready');
          }
        } catch (err: any) {
          if (err.name === 'AbortError') return;
          const message = err instanceof Error ? err.message : 'Failed to load storyboard';
          setError(message);
          setStatus('error');
        }
      };

      void run();
    });

    return () => {
      unsubscribe();
      scriptChangeAbortRef.current?.abort();
    };
  }, [subscribe, stableSelectedChapterId, loadStoryboardConfig, markStoryboardClean, resetStoryboard]);

  // Initial load: fetch storyboard data on mount when script is already selected
  useEffect(() => {
    if (!stableSelectedChapterId || !selectedScriptId) {
      scriptChangeAbortRef.current?.abort();
      resetStoryboard();
      setStatus('idle');
      setError(null);
      lastLoadedKeyRef.current = null;
      return;
    }

    const loadKey = `${stableSelectedChapterId}:${selectedScriptId}`;
    if (lastLoadedKeyRef.current === loadKey) return;
    lastLoadedKeyRef.current = loadKey;

    const controller = new AbortController();
    scriptChangeAbortRef.current = controller;

    setStatus('loading');
    setError(null);

    (async () => {
      try {
        // Fetch images
        const chapterImagesRes = await userService.getChapterImages(stableSelectedChapterId);
        if (controller.signal.aborted) return;

        const allImages = chapterImagesRes.images || [];

        // Fetch storyboard config
        let storyboardConfig: { key_scene_images?: Record<string, string>; deselected_images?: string[]; image_order?: Record<string, string[]> } = {};
        try {
          storyboardConfig = await projectService.getStoryboardConfig(stableSelectedChapterId, selectedScriptId);
        } catch {
          // config may not exist yet
        }
        if (controller.signal.aborted) return;

        // Filter images for this script
        const scriptImages = allImages.filter((img: any) => {
          const normalizedScriptId = img.script_id ?? img.scriptId;
          return normalizedScriptId === selectedScriptId && img.image_type === 'scene';
        });

        const keySceneImages: Record<string, string> = storyboardConfig?.key_scene_images || {};
        const deselectedImages: string[] = storyboardConfig?.deselected_images || [];
        const imageOrder: Record<string, string[]> = storyboardConfig?.image_order || {};

        // Group by scene number
        const grouped: Record<number, SceneImage[]> = {};
        scriptImages.forEach((img: any) => {
          const sceneNum = img.scene_number ?? img.metadata?.scene_number ?? 1;
          const sn = Number(sceneNum);
          if (!grouped[sn]) grouped[sn] = [];
          const isKey = keySceneImages[String(sn)] === img.id;
          grouped[sn].push({
            id: img.id,
            url: img.image_url || '',
            sceneNumber: sn,
            shotType: isKey ? 'key_scene' : 'suggested_shot',
            shotIndex: img.shot_index ?? img.metadata?.shot_index ?? grouped[sn].length,
          });
        });

        setSceneImagesMap(grouped);
        setExcludedImageIds(new Set(deselectedImages));

        const selected: Record<number, string> = {};
        Object.entries(keySceneImages).forEach(([sceneNum, imageId]) => {
          const img = scriptImages.find((i: any) => i.id === imageId);
          if (img) selected[parseInt(sceneNum)] = img.image_url || '';
        });
        setSelectedSceneImagesState(selected);

        const orderMap: Record<number, string[]> = {};
        Object.entries(imageOrder).forEach(([sceneNum, ids]) => {
          orderMap[parseInt(sceneNum)] = ids;
        });
        setImageOrderBySceneState(orderMap);

        // Fetch audio
        try {
          const audioRes = await userService.getChapterAudio(stableSelectedChapterId, selectedScriptId);
          if (controller.signal.aborted) return;
          setSceneAudioMap(mapAudioFiles(audioRes?.audio_files ?? [], selectedScriptId));
        } catch (audioErr: any) {
          if (audioErr.name !== 'AbortError') {
            console.error('[StoryboardContext] Failed to fetch audio data:', audioErr);
          }
        }

        setStatus('ready');
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        const message = err instanceof Error ? err.message : 'Failed to load storyboard state';
        console.error('[StoryboardContext] Failed to fetch storyboard data:', err);
        setError(message);
        setStatus('error');
      }
    })();

    return () => controller.abort();
  }, [stableSelectedChapterId, selectedScriptId, loadStoryboardConfig, resetStoryboard]);

  // Actions
  const setSelectedSceneImage = useCallback((sceneNumber: number, imageUrl: string | null) => {
    setSelectedSceneImagesState(prev => {
      if (imageUrl === null) {
        const { [sceneNumber]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [sceneNumber]: imageUrl };
    });
  }, []);

  const excludeImage = useCallback((imageId: string) => {
    setExcludedImageIds(prev => new Set([...prev, imageId]));
  }, []);

  const includeImage = useCallback((imageId: string) => {
    setExcludedImageIds(prev => {
      const next = new Set(prev);
      next.delete(imageId);
      return next;
    });
  }, []);

  const setSceneAudio = useCallback((sceneNumber: number, audioFiles: AudioFile[]) => {
    setSceneAudioMap(prev => ({ ...prev, [sceneNumber]: audioFiles }));
  }, []);

  const setSceneImages = useCallback((sceneNumber: number, images: SceneImage[]) => {
    setSceneImagesMap(prev => ({ ...prev, [sceneNumber]: images }));
  }, []);

  const setImageOrder = useCallback((sceneNumber: number, imageIds: string[]) => {
    setImageOrderBySceneState(prev => ({ ...prev, [sceneNumber]: imageIds }));
  }, []);
  
  // Audio Assignment Actions
  const assignAudioToShot = useCallback((audioId: string, sceneNumber: number, shotIndex: number) => {
    setAudioAssignments(prev => ({
      ...prev,
      [audioId]: { sceneNumber, shotIndex }
    }));
  }, []);

  const unassignAudio = useCallback((audioId: string) => {
    setAudioAssignments(prev => {
      const next = { ...prev };
      delete next[audioId];
      return next;
    });
  }, []);

  // Audio Selection Actions
  const selectAudio = useCallback((audioId: string) => {
    setSelectedAudioIds(prev => new Set([...prev, audioId]));
  }, []);

  const deselectAudio = useCallback((audioId: string) => {
    setSelectedAudioIds(prev => {
      const next = new Set(prev);
      next.delete(audioId);
      return next;
    });
  }, []);

  const toggleAudioSelection = useCallback((audioId: string) => {
    setSelectedAudioIds(prev => {
      if (prev.has(audioId)) {
        const next = new Set(prev);
        next.delete(audioId);
        return next;
      }

      const next = new Set(prev);
      next.add(audioId);
      return next;
    });
  }, []);

  const isAudioSelected = useCallback((audioId: string) => {
    return selectedAudioIds.has(audioId);
  }, [selectedAudioIds]);

  // Computed values
  const getIncludedImagesForScene = useCallback((sceneNumber: number): SceneImage[] => {
    const images = sceneImagesMap[sceneNumber] || [];
    return images.filter(img => !excludedImageIds.has(img.id));
  }, [sceneImagesMap, excludedImageIds]);

  const getAudioCountForScene = useCallback((sceneNumber: number): number => {
    return (sceneAudioMap[sceneNumber] || []).length;
  }, [sceneAudioMap]);

  // Helper to find audio by ID across all scenes
  const findAudioById = useCallback((audioId: string): AudioFile | undefined => {
    for (const files of Object.values(sceneAudioMap)) {
      const found = files.find(f => f.id === audioId);
      if (found) return found;
    }
    return undefined;
  }, [sceneAudioMap]);

  // Helper to resolve effective location of an audio file
  const getAudioLocation = useCallback((audio: AudioFile): { sceneNumber: number; shotIndex: number } => {
    const assigned = audioAssignments[audio.id];
    if (assigned) {
      return assigned;
    }
    return {
      sceneNumber: audio.sceneNumber,
      shotIndex: audio.shotIndex ?? 0 // Default to 0 (Key Scene) if undefined
    };
  }, [audioAssignments]);

  // Get audio files for a specific shot (sceneNumber + optional shotIndex)
  // NOW RESPECTS MANUAL ASSIGNMENTS
  const getAudioForShot = useCallback((sceneNumber: number, shotIndex?: number): AudioFile[] => {
    const result: AudioFile[] = [];
    
    // Iterate all audio to find matches (handling moves across scenes)
    Object.values(sceneAudioMap).forEach(files => {
      files.forEach(audio => {
        const loc = getAudioLocation(audio);
        const matchScene = loc.sceneNumber === sceneNumber;
        const matchShot = shotIndex === undefined || loc.shotIndex === shotIndex;
        
        if (matchScene && matchShot) {
          result.push(audio);
        }
      });
    });
    
    return result;
  }, [sceneAudioMap, getAudioLocation]);

  const getSelectedImageForScene = useCallback((sceneNumber: number): string | null => {
    return selectedSceneImages[sceneNumber] || null;
  }, [selectedSceneImages]);

  const importFromAudioPanel = useCallback((data: Partial<StoryboardState>) => {
    if (data.selectedSceneImages) setSelectedSceneImagesState(data.selectedSceneImages);
    if (data.excludedImageIds) setExcludedImageIds(data.excludedImageIds);
    if (data.sceneAudioMap) setSceneAudioMap(data.sceneAudioMap);
    if (data.sceneImagesMap) setSceneImagesMap(data.sceneImagesMap);
    if (data.imageOrderByScene) setImageOrderBySceneState(data.imageOrderByScene);
    if (data.audioAssignments) setAudioAssignments(data.audioAssignments);
    if (data.selectedAudioIds) setSelectedAudioIds(data.selectedAudioIds);
  }, []);

  const value = useMemo<StoryboardContextValue>(() => ({
    selectedSceneImages,
    excludedImageIds,
    sceneAudioMap,
    sceneImagesMap,
    imageOrderByScene,
    audioAssignments,
    selectedAudioIds,
    status,
    error,
    setSelectedSceneImage,
    excludeImage,
    includeImage,
    setSceneAudio,
    setSceneImages,
    setImageOrder,
    assignAudioToShot,
    unassignAudio,
    selectAudio,
    deselectAudio,
    toggleAudioSelection,
    isAudioSelected,
    getIncludedImagesForScene,
    getAudioCountForScene,
    getAudioForShot,
    getSelectedImageForScene,
    findAudioById,
    resetStoryboard,
    importFromAudioPanel,
  }), [
    selectedSceneImages,
    excludedImageIds,
    sceneAudioMap,
    sceneImagesMap,
    imageOrderByScene,
    audioAssignments,
    selectedAudioIds,
    status,
    error,
    setSelectedSceneImage,
    excludeImage,
    includeImage,
    setSceneAudio,
    setSceneImages,
    setImageOrder,
    assignAudioToShot,
    unassignAudio,
    selectAudio,
    deselectAudio,
    toggleAudioSelection,
    isAudioSelected,
    getIncludedImagesForScene,
    getAudioCountForScene,
    getAudioForShot,
    getSelectedImageForScene,
    findAudioById,
    resetStoryboard,
    importFromAudioPanel,
  ]);

  return (
    <StoryboardContext.Provider value={value}>
      {children}
    </StoryboardContext.Provider>
  );
};


export const useStoryboard = (): StoryboardContextValue => {
  const context = useContext(StoryboardContext);
  if (!context) {
    throw new Error('useStoryboard must be used within a StoryboardProvider');
  }
  return context;
};

// Optional hook that doesn't throw - for components that may be outside provider
export const useStoryboardOptional = (): StoryboardContextValue | null => {
  return useContext(StoryboardContext);
};

export default StoryboardContext;
