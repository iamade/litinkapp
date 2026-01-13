// Migration Note: Legacy AudioAssets interface removed.
// Now using normalized audio file arrays with scriptId property for consistent filtering.
import { useState, useCallback, useRef, useEffect } from 'react';
import { userService } from '../services/userService';

// Legacy hook signature for backward compatibility
export type UseAudioParams = { chapterId?: string | null; scriptId?: string | null; versionToken?: unknown };
export type AudioFile = {
  id: string;
  chapter_id?: string;
  script_id?: string;
  scriptId?: string | null; // Add camelCase version for frontend consistency (null when neither script_id nor scriptId present)
  url: string;
  audio_url?: string; // Backend field name for audio URL
  duration_ms?: number;
  created_at?: string;
  kind?: "narration" | "dialogue" | "sfx" | "music";
  // legacy fields
  type?: string;
  sceneNumber?: number;
  duration?: number;
  character?: string;
  name?: string;
  status?: string;
  generatedAt?: string;
  waveform?: number[];
  volume?: number;
  startTime?: number;
  endTime?: number;
};

type State = {
  files: AudioFile[];
  isLoading: boolean;
  error?: string | null;
};

export function useAudioGeneration({ chapterId, scriptId, versionToken }: UseAudioParams) {
  const [state, setState] = useState<State>({ files: [], isLoading: false, error: null });
  const inflightRef = useRef<string | null>(null);
  const isMountedRef = useRef(true);
  useEffect(() => () => { isMountedRef.current = false; }, []);

  const loadAudio = useCallback(async () => {
    if (!chapterId || !scriptId) {
      setState({ files: [], isLoading: false, error: null });
      return;
    }
    const key = `${chapterId}:${scriptId}`;
    if (inflightRef.current === key) return;
    inflightRef.current = key;
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      // Prefer getAudioForScriptChapter if present, fallback to userService.getChapterAudio
      let files: AudioFile[] = [];
      if (typeof import.meta.env !== "undefined") {
        // @ts-expect-error - Dynamic import check
        if (typeof import('../lib/api').getAudioForScriptChapter === "function") {
          // @ts-expect-error - Dynamic import
          files = await (await import('../lib/api')).getAudioForScriptChapter(chapterId, scriptId);
        } else {
          // fallback to userService
          files = await userService.getChapterAudio(chapterId);
        }
      } else {
        files = await userService.getChapterAudio(chapterId);
      }
      if (!isMountedRef.current || inflightRef.current !== key) return;
      
      // Normalize fields for consistent frontend filtering
      // Map backend snake_case fields to frontend camelCase expectations
      const normalizedFiles = (files ?? []).map(f => {
        // Map backend audio_type to frontend categories
        let kind = f.type || 'narration';
        
        // Handle backend audio_type mapping
        // @ts-expect-error - Backend field access
        const audioType = f.audio_type || f.type;
        // @ts-expect-error - Metadata access
        const metadata = f.metadata || f.audio_metadata || {};

        if (audioType === 'narrator') kind = 'narration';
        else if (audioType === 'character') kind = 'dialogue';
        else if (audioType === 'sound_effects' || audioType === 'sfx') kind = 'effects';
        else if (audioType === 'background_music' || audioType === 'music') {
          // Distinguish music vs ambiance
          if (metadata.music_type === 'ambient' || metadata.music_type === 'ambiance' || 
              metadata.effect_type === 'ambient' || metadata.effect_type === 'environmental') {
            kind = 'ambiance';
          } else {
            kind = 'music';
          }
        }

        return {
          ...f,
          url: f.url ?? f.audio_url,
          scriptId: f.script_id ?? f.scriptId ?? null,
          type: kind // Override type with normalized kind
        };
      });
      
      setState({ files: normalizedFiles, isLoading: false, error: null });
    } catch (e: unknown) {
      if (!isMountedRef.current || inflightRef.current !== key) return;
      setState(prev => ({ ...prev, isLoading: false, error: (e as Error)?.message ?? "Failed to load audio" }));
    } finally {
      if (inflightRef.current === key) inflightRef.current = null;
    }
  }, [chapterId, scriptId]);

  useEffect(() => {
    loadAudio();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapterId, scriptId, versionToken]);

  return { ...state, loadAudio };
}

// New reactive hook
