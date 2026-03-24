// src/contexts/StoryboardContext.tsx
// Shared state for storyboard selections across Audio and Video tabs

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  useEffect,
  useRef,
  ReactNode
} from 'react';
import { userService } from '../services/userService';
import { projectService, StoryboardConfig } from '../services/projectService';
import { useScriptSelection } from './ScriptSelectionContext';

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
        // Deselecting — remove it
        const next = new Set(prev);
        next.delete(audioId);
        return next;
      } else {
        // Selecting — replace any existing selection (max 1 audio allowed)
        return new Set([audioId]);
      }
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

  // Bulk operations
  const resetStoryboard = useCallback(() => {
    setSelectedSceneImagesState({});
    setExcludedImageIds(new Set());
    setSceneAudioMap({});
    setSceneImagesMap({});
    setImageOrderBySceneState({});
    setAudioAssignments({});
    setSelectedAudioIds(new Set());
  }, []);

  const loadEmptyStoryboardConfig = useCallback(() => {
    loadStoryboardConfig({
      key_scene_images: {},
      deselected_images: [],
      image_order: {},
    });
  }, [loadStoryboardConfig]);

  const normalizeSceneImages = useCallback((images: any[], scriptId: string): Record<number, SceneImage[]> => {
    const nextSceneImagesMap: Record<number, SceneImage[]> = {};

    images.forEach((img, index) => {
      const metadata = img?.metadata ?? {};
      const normalizedScriptId = img?.script_id ?? img?.scriptId ?? metadata?.script_id;
      if (normalizedScriptId && normalizedScriptId !== scriptId) return;

      const imageType = img?.image_type ?? metadata?.image_type;
      if (imageType !== 'scene') return;

      const sceneNumRaw = img?.scene_number ?? metadata?.scene_number;
      const sceneNumber = Number(sceneNumRaw);
      if (!Number.isFinite(sceneNumber)) return;

      const shotIndexRaw = img?.shot_index ?? metadata?.shot_index;
      const shotIndex = typeof shotIndexRaw === 'number' ? shotIndexRaw : undefined;
      const normalizedImage: SceneImage = {
        id: img?.id ?? `${sceneNumber}-${index}`,
        url: img?.image_url ?? img?.url ?? '',
        sceneNumber,
        shotType: shotIndex === 0 ? 'key_scene' : 'suggested_shot',
        shotIndex,
      };

      if (!nextSceneImagesMap[sceneNumber]) {
        nextSceneImagesMap[sceneNumber] = [];
      }
      nextSceneImagesMap[sceneNumber].push(normalizedImage);
    });

    Object.values(nextSceneImagesMap).forEach(sceneImages => {
      sceneImages.sort((a, b) => (a.shotIndex ?? Number.MAX_SAFE_INTEGER) - (b.shotIndex ?? Number.MAX_SAFE_INTEGER));
    });

    return nextSceneImagesMap;
  }, []);

  const loadStoryboardForScript = useCallback(async (chapterId: string, scriptId: string) => {
    scriptChangeAbortRef.current?.abort();
    const controller = new AbortController();
    scriptChangeAbortRef.current = controller;

    setStatus('loading');
    setError(null);
    resetStoryboard();

    try {
      const imagesResponse = await userService.getChapterImages(chapterId);
      if (controller.signal.aborted) return;

      setSceneImagesMap(normalizeSceneImages(imagesResponse.images || [], scriptId));

      try {
        const config = await projectService.getStoryboardConfig(chapterId, scriptId);
        if (!controller.signal.aborted) {
          loadStoryboardConfig(config);
        }
      } catch {
        if (!controller.signal.aborted) {
          loadEmptyStoryboardConfig();
        }
      }

      if (!controller.signal.aborted) {
        setStatus('ready');
      }
    } catch (err) {
      if (controller.signal.aborted) return;
      const message = err instanceof Error ? err.message : 'Failed to load storyboard state';
      setError(message);
      setStatus('error');
      loadEmptyStoryboardConfig();
    }
  }, [loadEmptyStoryboardConfig, loadStoryboardConfig, normalizeSceneImages, resetStoryboard]);

  useEffect(() => {
    if (isSwitching) return;
    storyboardSnapshotRef.current = {
      chapterId: stableSelectedChapterId,
      scriptId: selectedScriptId,
      storyboardDirty,
      config: getStoryboardConfig(),
    };
  }, [stableSelectedChapterId, selectedScriptId, storyboardDirty, getStoryboardConfig, isSwitching]);

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
          loadEmptyStoryboardConfig();
          setStatus('idle');
          setError(null);
          return;
        }

        await loadStoryboardForScript(nextChapterId, nextScriptId);
      };

      void run();
    });

    return () => {
      unsubscribe();
      scriptChangeAbortRef.current?.abort();
    };
  }, [loadEmptyStoryboardConfig, loadStoryboardForScript, markStoryboardClean, resetStoryboard, stableSelectedChapterId, subscribe]);

  useEffect(() => {
    if (!stableSelectedChapterId || !selectedScriptId) {
      scriptChangeAbortRef.current?.abort();
      resetStoryboard();
      loadEmptyStoryboardConfig();
      setStatus('idle');
      setError(null);
      lastLoadedKeyRef.current = null;
      return;
    }

    const loadKey = `${stableSelectedChapterId}:${selectedScriptId}`;
    if (lastLoadedKeyRef.current === loadKey) return;
    lastLoadedKeyRef.current = loadKey;
    void loadStoryboardForScript(stableSelectedChapterId, selectedScriptId);
  }, [loadEmptyStoryboardConfig, loadStoryboardForScript, resetStoryboard, selectedScriptId, stableSelectedChapterId]);

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
    status,
    error,
    audioAssignments,
    selectedAudioIds,
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
    status,
    error,
    audioAssignments,
    selectedAudioIds,
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
