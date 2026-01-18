import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import { StoryboardConfig } from '../services/projectService';

type Reason = 'user' | 'navigation' | 'load' | 'system';
type ScriptSelectionEvent = 'SCRIPT_CHANGED' | 'CHAPTER_CHANGED' | 'SEGMENT_CHANGED' | 'TIMELINE_RECALC_REQUESTED';

type Ids = {
   script_id: string | null;
   chapterId: string | null;
   segmentId: string | null;
 };

export type EventPayload = {
  prev: Ids;
  next: Ids;
  reason: Reason;
  timestamp: number;
  versionToken: number;
};

export type ScriptSelectionState = {
  selectedScriptId: string | null;
  selectedChapterId: string | null;
  selectedSegmentId: string | null;
  versionToken: number;
  isSwitching: boolean;
  lastValidChapterId: string | null; // Ensure type matches
  selectedSceneImages: Record<number, string>; // sceneNumber -> imageUrl (legacy, kept for compatibility)
  // NEW: Storyboard configuration state
  keySceneImages: Record<number, string>;       // sceneNumber -> imageId of key scene
  deselectedImages: Set<string>;                // opt-OUT: image IDs that are excluded
  imageOrderByScene: Record<number, string[]>;  // sceneNumber -> ordered array of image IDs
  storyboardDirty: boolean;                     // true if there are unsaved changes
};

type Listener = (evt: ScriptSelectionEvent, payload: EventPayload) => void;

type ContextValue = ScriptSelectionState & {
  selectScript: (nextScriptId: string | null, opts?: { reason?: Reason }) => void;
  selectChapter: (nextChapterId: string | null, opts?: { reason?: Reason }) => void;
  selectSegment: (nextSegmentId: string | null, opts?: { reason?: Reason }) => void;
  publish: (evt: ScriptSelectionEvent, extra?: Partial<EventPayload>) => void;
  subscribe: (listener: Listener) => () => void;
  stableSelectedChapterId: string | null; // Ensure type matches
  setSelectedSceneImage: (sceneNumber: number, imageUrl: string | null) => void;
  // NEW: Storyboard configuration methods
  setKeySceneImage: (sceneNumber: number, imageId: string | null) => void;
  toggleDeselectedImage: (imageId: string) => void;
  isImageSelected: (imageId: string) => boolean;
  setImageOrder: (sceneNumber: number, orderedIds: string[]) => void;
  loadStoryboardConfig: (config: StoryboardConfig) => void;
  getStoryboardConfig: () => StoryboardConfig;
  markStoryboardClean: () => void;
};

const ScriptSelectionContext = createContext<ContextValue | undefined>(undefined);

export const ScriptSelectionProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const listenersRef = useRef<Set<Listener>>(new Set());

  const [state, setState] = useState<ScriptSelectionState>({
    selectedScriptId: null,
    selectedChapterId: null,
    selectedSegmentId: null,
    versionToken: 0,
    isSwitching: false,
    lastValidChapterId: null, // Ensure type matches
    selectedSceneImages: {},
    // NEW: Storyboard configuration initial state
    keySceneImages: {},
    deselectedImages: new Set<string>(),
    imageOrderByScene: {},
    storyboardDirty: false,
  });

  const emit = useCallback((evt: ScriptSelectionEvent, payload: EventPayload) => {
    for (const l of listenersRef.current) {
      try {
        l(evt, payload);
      } catch {
        // swallow listener errors to not break provider
      }
    }
  }, []);

  const selectScript = useCallback((nextScriptId: string | null, opts?: { reason?: Reason }) => {
    setState(prev => {
      if (prev.selectedScriptId === nextScriptId) return prev;
      const reason = opts?.reason ?? 'user';
      const nextVersion = prev.versionToken + 1;
      const next: ScriptSelectionState = {
        selectedScriptId: nextScriptId,
        selectedChapterId: prev.selectedChapterId, // Preserve previously selected chapter
        selectedSegmentId: null,
        versionToken: nextVersion,
        isSwitching: true,
        lastValidChapterId: prev.lastValidChapterId, // Preserve last valid chapter
        selectedSceneImages: {}, // Reset selections on script change
        // Reset storyboard configuration on script change
        keySceneImages: {},
        deselectedImages: new Set<string>(),
        imageOrderByScene: {},
        storyboardDirty: false,
      };
      // emit after commit via microtask to ensure consumers see latest state
      queueMicrotask(() => {
        emit('SCRIPT_CHANGED', {
          prev: { script_id: prev.selectedScriptId, chapterId: prev.selectedChapterId, segmentId: prev.selectedSegmentId },
          next: { script_id: next.selectedScriptId, chapterId: next.selectedChapterId, segmentId: next.selectedSegmentId },
          reason,
          timestamp: Date.now(),
          versionToken: nextVersion,
        });
        // turn off switching flag after emission
        setState(s => ({ ...s, isSwitching: false }));
      });
      return next;
    });
  }, [emit]);

  const selectChapter = useCallback((nextChapterId: string | null, opts?: { reason?: Reason }) => {
    setState(prev => {
      if (prev.selectedChapterId === nextChapterId) return prev;
      const reason = opts?.reason ?? 'user';
      const nextVersion = prev.versionToken + 1;
      const next: ScriptSelectionState = {
        ...prev,
        selectedChapterId: nextChapterId,
        lastValidChapterId: nextChapterId ?? prev.lastValidChapterId, // Update lastValid on non-null
        selectedSegmentId: null,
        versionToken: nextVersion,
      };
      queueMicrotask(() => {
        emit('CHAPTER_CHANGED', {
          prev: { script_id: prev.selectedScriptId, chapterId: prev.selectedChapterId, segmentId: prev.selectedSegmentId },
          next: { script_id: next.selectedScriptId, chapterId: next.selectedChapterId, segmentId: next.selectedSegmentId },
          reason,
          timestamp: Date.now(),
          versionToken: nextVersion,
        });
      });
      return next;
    });
  }, [emit]);

  const selectSegment = useCallback((nextSegmentId: string | null, opts?: { reason?: Reason }) => {
    setState(prev => {
      if (prev.selectedSegmentId === nextSegmentId) return prev;
      const reason = opts?.reason ?? 'user';
      const nextVersion = prev.versionToken + 1;
      const next: ScriptSelectionState = {
        ...prev,
        selectedSegmentId: nextSegmentId,
        versionToken: nextVersion,
      };
      queueMicrotask(() => {
        emit('SEGMENT_CHANGED', {
          prev: { script_id: prev.selectedScriptId, chapterId: prev.selectedChapterId, segmentId: prev.selectedSegmentId },
          next: { script_id: next.selectedScriptId, chapterId: next.selectedChapterId, segmentId: next.selectedSegmentId },
          reason,
          timestamp: Date.now(),
          versionToken: nextVersion,
        });
      });
      return next;
    });
  }, [emit]);

  const setSelectedSceneImage = useCallback((sceneNumber: number, imageUrl: string | null) => {
    setState(prev => {
        const newImages = { ...prev.selectedSceneImages };
        if (imageUrl) {
            newImages[sceneNumber] = imageUrl;
        } else {
            delete newImages[sceneNumber];
        }
        return {
            ...prev,
            selectedSceneImages: newImages
        };
    });
  }, []);

  // NEW: Set key scene image for a scene
  const setKeySceneImage = useCallback((sceneNumber: number, imageId: string | null) => {
    setState(prev => {
      const newKeySceneImages = { ...prev.keySceneImages };
      if (imageId) {
        newKeySceneImages[sceneNumber] = imageId;
      } else {
        delete newKeySceneImages[sceneNumber];
      }
      return {
        ...prev,
        keySceneImages: newKeySceneImages,
        storyboardDirty: true,
      };
    });
  }, []);

  // NEW: Toggle deselected state for an image (opt-OUT: add to deselected = exclude)
  const toggleDeselectedImage = useCallback((imageId: string) => {
    setState(prev => {
      const newDeselected = new Set(prev.deselectedImages);
      if (newDeselected.has(imageId)) {
        newDeselected.delete(imageId);  // Re-include the image
      } else {
        newDeselected.add(imageId);     // Exclude the image
      }
      return {
        ...prev,
        deselectedImages: newDeselected,
        storyboardDirty: true,
      };
    });
  }, []);

  // NEW: Check if an image is selected (not in deselectedImages)
  const isImageSelected = useCallback((imageId: string) => {
    return !state.deselectedImages.has(imageId);
  }, [state.deselectedImages]);

  // NEW: Set image order for a scene
  const setImageOrder = useCallback((sceneNumber: number, orderedIds: string[]) => {
    setState(prev => {
      return {
        ...prev,
        imageOrderByScene: {
          ...prev.imageOrderByScene,
          [sceneNumber]: orderedIds,
        },
        storyboardDirty: true,
      };
    });
  }, []);

  // NEW: Load storyboard configuration from backend
  const loadStoryboardConfig = useCallback((config: StoryboardConfig) => {
    setState(prev => {
      // Convert key_scene_images from string keys to number keys
      const keySceneImages: Record<number, string> = {};
      for (const [sceneNumStr, imageId] of Object.entries(config.key_scene_images || {})) {
        keySceneImages[Number(sceneNumStr)] = imageId;
      }

      // Convert image_order from string keys to number keys
      const imageOrderByScene: Record<number, string[]> = {};
      for (const [sceneNumStr, imageIds] of Object.entries(config.image_order || {})) {
        imageOrderByScene[Number(sceneNumStr)] = imageIds;
      }

      return {
        ...prev,
        keySceneImages,
        deselectedImages: new Set(config.deselected_images || []),
        imageOrderByScene,
        storyboardDirty: false,  // Just loaded, so it's clean
      };
    });
  }, []);

  // NEW: Get storyboard configuration for saving to backend
  const getStoryboardConfig = useCallback((): StoryboardConfig => {
    // Convert number keys to string keys for API
    const key_scene_images: Record<string, string> = {};
    for (const [sceneNum, imageId] of Object.entries(state.keySceneImages)) {
      key_scene_images[String(sceneNum)] = imageId;
    }

    const image_order: Record<string, string[]> = {};
    for (const [sceneNum, imageIds] of Object.entries(state.imageOrderByScene)) {
      image_order[String(sceneNum)] = imageIds;
    }

    return {
      key_scene_images,
      deselected_images: Array.from(state.deselectedImages),
      image_order,
    };
  }, [state.keySceneImages, state.deselectedImages, state.imageOrderByScene]);

  // NEW: Mark storyboard as clean (after saving)
  const markStoryboardClean = useCallback(() => {
    setState(prev => ({
      ...prev,
      storyboardDirty: false,
    }));
  }, []);

  const publish = useCallback((evt: ScriptSelectionEvent, extra?: Partial<EventPayload>) => {
    const now = Date.now();
    const payload: EventPayload = {
      prev: { script_id: state.selectedScriptId, chapterId: state.selectedChapterId, segmentId: state.selectedSegmentId },
      next: { script_id: state.selectedScriptId, chapterId: state.selectedChapterId, segmentId: state.selectedSegmentId },
      reason: extra?.reason ?? 'system',
      timestamp: extra?.timestamp ?? now,
      versionToken: extra?.versionToken ?? state.versionToken,
    };
    emit(evt, payload);
  }, [emit, state.selectedScriptId, state.selectedChapterId, state.selectedSegmentId, state.versionToken]);

  const subscribe = useCallback((listener: Listener) => {
    listenersRef.current.add(listener);
    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  const stableSelectedChapterId = state.selectedChapterId ?? state.lastValidChapterId; // Ensure type matches

  const value: ContextValue = useMemo(() => ({
    ...state,
    selectScript,
    selectChapter,
    selectSegment,
    publish,
    subscribe,
    stableSelectedChapterId, // Ensure type matches
    setSelectedSceneImage,
    // NEW: Storyboard configuration methods
    setKeySceneImage,
    toggleDeselectedImage,
    isImageSelected,
    setImageOrder,
    loadStoryboardConfig,
    getStoryboardConfig,
    markStoryboardClean,
  }), [
    state,
    selectScript,
    selectChapter,
    selectSegment,
    publish,
    subscribe,
    stableSelectedChapterId,
    setSelectedSceneImage,
    setKeySceneImage,
    toggleDeselectedImage,
    isImageSelected,
    setImageOrder,
    loadStoryboardConfig,
    getStoryboardConfig,
    markStoryboardClean,
  ]);

  return <ScriptSelectionContext.Provider value={value}>{children}</ScriptSelectionContext.Provider>;
};

export function useScriptSelection(): ContextValue {
  const ctx = useContext(ScriptSelectionContext);
  if (!ctx) {
    throw new Error('useScriptSelection must be used within a ScriptSelectionProvider');
  }
  return ctx;
}