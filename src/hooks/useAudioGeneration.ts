import { useState, useCallback, useRef, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { userService } from '../services/userService';

interface AudioFile {
  id: string;
  type: 'narration' | 'music' | 'effects' | 'ambiance' | 'character' | 'sfx';
  sceneNumber: number;
  url: string;
  duration: number;
  character?: string;
  name: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  generatedAt?: string;
  waveform?: number[];
  volume: number;
  startTime: number;
  endTime: number;
}

interface AudioAssets {
  narration: AudioFile[];
  music: AudioFile[];
  effects: AudioFile[];
  ambiance: AudioFile[];
  character: AudioFile[];
  sfx: AudioFile[];
}

// Map DB enum values to frontend types
const mapDbTypeToFrontend = (dbType: string): keyof AudioAssets => {
  const mapping: Record<string, keyof AudioAssets> = {
    'narrator': 'narration',
    'music': 'music',
    'sound_effect': 'effects',
    'background_music': 'ambiance',
    'character': 'character',
    'sfx': 'sfx'
  };
  return mapping[dbType] || 'narration'; // fallback
};

interface AudioGenerationOptions {
  voiceModel: string;
  musicStyle: string;
  effectsIntensity: 'subtle' | 'moderate' | 'dramatic';
  ambianceType: string;
  audioQuality: 'standard' | 'high' | 'premium';
  generateNarration: boolean;
  generateMusic: boolean;
  generateEffects: boolean;
  generateAmbiance: boolean;
  characterVoices: Record<string, string>; // Map character names to voice models
}

// New params type for reactive hook
type UseAudioGenerationParams = {
  scriptId?: string;
  chapterId?: string;
  segmentId?: string;
  versionKey?: number; // passed from callers (e.g., context.versionToken)
};

// Legacy hook signature for backward compatibility
export type UseAudioParams = { chapterId?: string | null; scriptId?: string | null; versionToken?: any };
export type AudioFile = {
  id: string;
  chapter_id?: string;
  script_id?: string;
  url: string;
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
        // @ts-ignore
        if (typeof import('../lib/api').getAudioForScriptChapter === "function") {
          // @ts-ignore
          files = await (await import('../lib/api')).getAudioForScriptChapter(chapterId, scriptId);
        } else {
          // fallback to userService
          files = await userService.getChapterAudio(chapterId, scriptId);
        }
      } else {
        files = await userService.getChapterAudio(chapterId, scriptId);
      }
      if (!isMountedRef.current || inflightRef.current !== key) return;
      setState({ files: files ?? [], isLoading: false, error: null });
    } catch (e: any) {
      if (!isMountedRef.current || inflightRef.current !== key) return;
      console.warn("useAudioGeneration: loadAudio failed", e);
      setState(prev => ({ ...prev, isLoading: false, error: e?.message ?? "Failed to load audio" }));
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
