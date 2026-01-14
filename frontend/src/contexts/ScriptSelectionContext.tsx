import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';

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
  selectedSceneImages: Record<number, string>; // sceneNumber -> imageUrl
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
  }), [state, selectScript, selectChapter, selectSegment, publish, subscribe, stableSelectedChapterId, setSelectedSceneImage]);

  return <ScriptSelectionContext.Provider value={value}>{children}</ScriptSelectionContext.Provider>;
};

export function useScriptSelection(): ContextValue {
  const ctx = useContext(ScriptSelectionContext);
  if (!ctx) {
    throw new Error('useScriptSelection must be used within a ScriptSelectionProvider');
  }
  return ctx;
}