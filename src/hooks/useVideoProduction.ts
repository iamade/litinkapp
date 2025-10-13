// src/hooks/useVideoProduction.ts
import { useState, useCallback, useEffect, useRef } from 'react';
import { toast } from 'react-hot-toast';
import { userService } from '../services/userService';
import type {
  VideoProduction,
  VideoScene,
  EditorSettings,
  Transition
} from '../types/videoProduction';

interface FFmpegOptions {
  quality?: 'low' | 'medium' | 'high' | 'ultra';
  videoUrl?: string;
}

// New params type for reactive hook
type UseVideoProductionParams = {
  scriptId?: string;
  versionKey?: number;
  chapterId?: string;
  imageUrls?: string[];
  audioFiles?: string[];
};

// Legacy hook signature for backward compatibility
export const useVideoProduction = (props: {
  chapterId: string;
  scriptId?: string;
  imageUrls?: string[];
  audioFiles?: string[];
}) => {
  return useVideoProductionWithParams(props);
};

// New reactive hook
export function useVideoProductionWithParams(params: UseVideoProductionParams) {
  const { scriptId, versionKey, chapterId, imageUrls = [], audioFiles = [] } = params;
  
  const [videoProduction, setVideoProduction] = useState<VideoProduction | null>(null);
  const [scenes, setScenes] = useState<VideoScene[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [renderingProgress, setRenderingProgress] = useState(0);
  const [editorSettings, setEditorSettings] = useState<EditorSettings>({
    resolution: '1080p',
    fps: 30,
    aspectRatio: '16:9',
    outputFormat: 'mp4',
    quality: 'high'
  });
  
  // Refs for cancellation and stale update protection
  const activeScriptIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Update active scriptId ref
  useEffect(() => { 
    activeScriptIdRef.current = scriptId ?? null; 
  }, [scriptId]);

  // Load existing video production
  const loadVideoProduction = useCallback(async () => {
    if (!chapterId) return;
    
    // Abort previous request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsLoading(true);
    try {
      const data = await userService.getVideoProduction(chapterId);

      // Guard against stale scriptId
      if (activeScriptIdRef.current !== scriptId) return;

      if (data) {
        setVideoProduction(data);
        setScenes((data as any).scenes || []);
        setEditorSettings((data as any).editorSettings || editorSettings);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
      }
    }
  }, [chapterId, scriptId, versionKey]);

  // Initialize scenes from images and audio with script context
  const initializeScenes = useCallback(async () => {
    if (!imageUrls.length) {
      toast.error('No images available to create scenes');
      return;
    }

    // Reset scenes when script changes to ensure proper mapping
    if (activeScriptIdRef.current !== scriptId) {
      setScenes([]);
      return;
    }

    const newScenes: VideoScene[] = imageUrls.map((imageUrl, index) => ({
      id: `scene-${Date.now()}-${index}-${scriptId || 'no-script'}`,
      sceneNumber: index + 1,
      imageUrl,
      audioFiles: audioFiles[index] ? [audioFiles[index]] : [],
      duration: 5, // Default 5 seconds per scene
      transitions: [{
        type: index === 0 ? 'none' : 'fade',
        duration: 0.5
      }],
      status: 'pending'
    }));

    // Guard against stale scriptId
    if (activeScriptIdRef.current === scriptId) {
      setScenes(newScenes);
      toast.success(`Initialized ${newScenes.length} scenes for script ${scriptId?.substring(0, 8)}...`);
    }
  }, [imageUrls, audioFiles, scriptId]);

  // Update scene
  const updateScene = useCallback((sceneId: string, updates: Partial<VideoScene>) => {
    setScenes(prev => prev.map(scene => 
      scene.id === sceneId ? { ...scene, ...updates } : scene
    ));
  }, []);

  // Reorder scenes
  const reorderScenes = useCallback((fromIndex: number, toIndex: number) => {
    setScenes(prev => {
      const newScenes = [...prev];
      const [movedScene] = newScenes.splice(fromIndex, 1);
      newScenes.splice(toIndex, 0, movedScene);
      
      // Update scene numbers
      return newScenes.map((scene, index) => ({
        ...scene,
        sceneNumber: index + 1
      }));
    });
  }, []);

  // Add transition
  const addTransition = useCallback((sceneId: string, transition: Transition) => {
    setScenes(prev => prev.map(scene => 
      scene.id === sceneId 
        ? { ...scene, transitions: [...scene.transitions, transition] }
        : scene
    ));
  }, []);

  // Update editor settings
  const updateEditorSettings = useCallback((settings: Partial<EditorSettings>) => {
    setEditorSettings(prev => ({ ...prev, ...settings }));
  }, []);

  // Render video - disabled per architecture (should use AI generation pipeline)
  const renderWithOpenShot = useCallback(async () => {
    toast.error('Video rendering is handled through the AI generation pipeline. Use the "Generate Video" feature instead.');
    return;
  }, []);

  // Process with FFmpeg - disabled per architecture (should use backend processing)
  const processWithFFmpeg = useCallback(async () => {
    toast.error('Video processing is handled in the backend. Use the AI generation pipeline for video processing.');
    return;
  }, []);

  // Download video
  const downloadVideo = useCallback(async (quality?: 'low' | 'medium' | 'high' | 'ultra') => {
    if (!videoProduction?.finalVideoUrl) {
      toast.error('No video available for download');
      return;
    }

    try {
      // For now, just download the existing video
      // Video processing should be done through the AI generation pipeline
      const downloadUrl = videoProduction.finalVideoUrl;

      // Create download link
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `video-${chapterId}-${quality || editorSettings.quality}.${editorSettings.outputFormat}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast.success('Download started');
    } catch (error) {
      toast.error('Failed to download video');
    }
  }, [videoProduction, chapterId, editorSettings]);

  // Save production
  const saveProduction = useCallback(async () => {
    if (!chapterId) {
      toast.error('Chapter ID is required for saving video production');
      return;
    }

    setIsLoading(true);
    try {
      const data = {
        chapterId,
        scenes,
        editorSettings,
        scriptId
      };

      const result = await userService.saveVideoProduction(data);
      setVideoProduction(result as any);
      toast.success('Video production saved');
    } catch (error) {
      toast.error('Failed to save video production');
    } finally {
      setIsLoading(false);
    }
  }, [chapterId, scenes, editorSettings, scriptId]);

  // Start video pipeline
  const startPipeline = useCallback(async () => {
    if (!scriptId) {
      toast.error('Script ID is required to start video pipeline');
      return;
    }

    setIsRendering(true);
    try {
      // This would call the backend to start the video generation pipeline
      // For now, we'll just show a message
      toast.success(`Starting video pipeline for script: ${scriptId}`);
      // TODO: Implement actual pipeline start
    } catch (error) {
      toast.error('Failed to start video pipeline');
    } finally {
      setIsRendering(false);
    }
  }, [scriptId]);

  // Render video
  const renderVideo = useCallback(async () => {
    if (!scriptId) {
      toast.error('Script ID is required to render video');
      return;
    }

    setIsRendering(true);
    try {
      // This would call the backend to render the video
      // For now, we'll just show a message
      toast.success(`Rendering video for script: ${scriptId}`);
      // TODO: Implement actual video rendering
    } catch (error) {
      toast.error('Failed to render video');
    } finally {
      setIsRendering(false);
    }
  }, [scriptId]);

  // Auto-load video production when dependencies change
  useEffect(() => {
    loadVideoProduction();
  }, [loadVideoProduction]);

  // Reset scenes when script changes to prevent stale data
  useEffect(() => {
    // Only clear when switching to a real new script (avoid transient null clears)
    if (scriptId && activeScriptIdRef.current !== scriptId) {
      setScenes([]);
      activeScriptIdRef.current = scriptId;
    }
  }, [scriptId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const refetch = useCallback(() => {
    loadVideoProduction();
  }, [loadVideoProduction]);

  return {
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
    renderWithOpenShot,
    processWithFFmpeg,
    downloadVideo,
    saveProduction,
    startPipeline,
    renderVideo,
    refetch
  };
}
