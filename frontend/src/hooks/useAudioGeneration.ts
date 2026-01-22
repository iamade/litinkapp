// Migration Note: Legacy AudioAssets interface removed.
// Now using normalized audio file arrays with scriptId property for consistent filtering.
import { useState, useCallback, useRef, useEffect } from 'react';
import { userService } from '../services/userService';

// Legacy hook signature for backward compatibility
export type UseAudioParams = { chapterId?: string | null; scriptId?: string | null; versionToken?: unknown; videoGenerationId?: string | null };
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
  shotType?: 'key_scene' | 'suggested_shot'; // Shot type from backend metadata
  shotIndex?: number; // Shot index within scene
  duration?: number;
  character?: string;
  name?: string;
  status?: string;
  generatedAt?: string;
  waveform?: number[];
  volume?: number;
  startTime?: number;
  endTime?: number;
  text_content?: string;
  text_prompt?: string;
};

type State = {
  files: AudioFile[];
  isLoading: boolean;
  error?: string | null;
};

export function useAudioGeneration({ chapterId, scriptId, versionToken, videoGenerationId }: UseAudioParams) {
  const [state, setState] = useState<State>({ files: [], isLoading: false, error: null });
  const [isGenerating, setIsGenerating] = useState(false);
  const inflightRef = useRef<string | null>(null);
  const isMountedRef = useRef(true);
  
  // Fix for React StrictMode: reset isMountedRef on each mount
  useEffect(() => {
    isMountedRef.current = true;  // Set to true on mount
    return () => { isMountedRef.current = false; };  // Set to false on unmount
  }, []);

  const loadAudio = useCallback(async () => {
    // Allow fetching with just scriptId if chapterId is not available
    if (!scriptId) {
      setState({ files: [], isLoading: false, error: null });
      return;
    }
    // Use scriptId as fallback key when chapterId is null
    const key = chapterId ? `${chapterId}:${scriptId}` : `script:${scriptId}`;
    if (inflightRef.current === key) return;
    inflightRef.current = key;
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      // Prefer getAudioForScriptChapter if present, fallback to userService.getChapterAudio
      let files: AudioFile[] = [];
      let response: any;
      
      // Use scriptId as primary key, chapterId as secondary (can be null)
      const effectiveChapterId = chapterId || scriptId || ''; // Use scriptId as fallback chapter identifier
      
      if (typeof import.meta.env !== "undefined") {
        // @ts-expect-error - Dynamic import check
        if (typeof import('../lib/api').getAudioForScriptChapter === "function") {
          // @ts-expect-error - Dynamic import
          response = await (await import('../lib/api')).getAudioForScriptChapter(effectiveChapterId, scriptId);
        } else {
          // fallback to userService - pass scriptId for backend fallback query
          response = await userService.getChapterAudio(effectiveChapterId, scriptId || undefined);
        }
      } else {
        response = await userService.getChapterAudio(effectiveChapterId, scriptId || undefined);
      }
      
      // Extract audio_files from response (API returns { chapter_id, audio_files, total_count })
      files = response?.audio_files ?? response ?? [];
      
      // Check for early return conditions  
      if (!isMountedRef.current) {
        return;
      }
      if (inflightRef.current !== key) {
        // Don't return - still process the data for the current request
        // return;
      }
      
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

        // Parse scene number - handle various formats
        // Backend may store as: 1, "1", "scene_1", "scene_1.1"
        let sceneNumber: number | undefined = undefined;
        // @ts-expect-error - scene_id comes from backend response
        const rawScene = metadata?.scene ?? f.scene_id ?? null;
        if (rawScene !== null && rawScene !== undefined) {
          if (typeof rawScene === 'number') {
            sceneNumber = Math.floor(rawScene); // Use integer for display
          } else if (typeof rawScene === 'string') {
            // Strip 'scene_' prefix if present
            const cleaned = rawScene.replace(/^scene_/i, '');
            const parsed = parseFloat(cleaned);
            if (!isNaN(parsed)) {
              sceneNumber = Math.floor(parsed); // Use integer for display
            }
          }
        }

        // Parse shot_type and shot_index from metadata
        let shotType = metadata?.shot_type as 'key_scene' | 'suggested_shot' | undefined;
        let shotIndex = typeof metadata?.shot_index === 'number' ? metadata.shot_index : undefined;

        // Fallback: Parse from text content or prompt if metadata is missing
        const textContent = f.text_content || f.text_prompt || f.name || "";
        if (shotIndex === undefined) {
          // Look for "Shot 2", "Shot 3", etc.
          const shotMatch = textContent.match(/Shot[\s_]*(\d+)/i);
          if (shotMatch) {
             // If found "Shot 1", it's index 0. "Shot 2" is index 1.
             const val = parseInt(shotMatch[1]);
             if (!isNaN(val) && val > 0) {
               shotIndex = val - 1;
               shotType = 'suggested_shot';
             }
          }
        }
        
        // Fallback: Check for "Key Scene" explicitly
        if (!shotType && /key[\s_]*scene/i.test(textContent)) {
           shotType = 'key_scene';
           shotIndex = 0;
        }

        // Final Fallback: If sceneAudio is present but shotIndex is missing, default to 0 (Key Scene)
        // This ensures audio doesn't disappear from the UI
        if (shotIndex === undefined) {
          shotIndex = 0;
          if (!shotType) shotType = 'key_scene';
        }

        return {
          ...f,
          url: f.url ?? f.audio_url,
          scriptId: f.script_id ?? f.scriptId ?? null,
          sceneNumber,
          shotType,
          shotIndex,
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

  // Polling logic for active generation
  // Polling logic for active generation
  useEffect(() => {
    if (!videoGenerationId) {
      setIsGenerating(false);
      return;
    }
    
    setIsGenerating(true);  // Mark as generating when we have a videoGenerationId

    let timeoutId: NodeJS.Timeout;
    let isActive = true;

    const pollStatus = async () => {
      try {
        // Dynamic import to avoid circular dependencies if any
        const { userService } = await import('../services/userService');
        const { toast } = await import('react-hot-toast');
        const statusData = await userService.getVideoGenerationStatus(videoGenerationId);
        
        console.log('[useAudioGeneration] Polling status:', statusData.generation_status);

        // Check for completion states
        const isCompleted = ['audio_completed', 'images_completed', 'completed', 'video_completed'].includes(statusData.generation_status);
        const isFailed = statusData.generation_status === 'failed';
        
        if (isCompleted || isFailed) {
          // Refresh files to show newly generated audio
          await loadAudio();
          
          // Clear generating state since we're done
          setIsGenerating(false);
          
          if (isFailed) {
            toast.error(statusData.error_message || 'Audio generation failed');
            setState(prev => ({ ...prev, error: statusData.error_message || "Generation failed" }));
          } else {
            toast.success('Audio generation completed!');
          }
          
          // Stop polling - we're done
          return;
        }

        // Schedule next poll if still active and not finished
        if (isActive) {
          timeoutId = setTimeout(pollStatus, 3000);
        }

      } catch (err) {
        console.error('[useAudioGeneration] Polling error:', err);
        // Retry on error (maybe network blip), but with backoff or just keep trying
        if (isActive) {
           timeoutId = setTimeout(pollStatus, 5000);
        }
      }
    };

    // Initial check
    pollStatus();

    return () => {
      isActive = false;
      setIsGenerating(false);  // Clear generating state on cleanup
      clearTimeout(timeoutId);
    };
  }, [videoGenerationId, loadAudio]);

  return { ...state, isGenerating, loadAudio };
}

// New reactive hook
