// src/hooks/useVideoProduction.ts
import { useState, useCallback, useEffect } from 'react';
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

interface UseVideoProductionProps {
  chapterId: string;
  scriptId?: string;
  imageUrls?: string[];
  audioFiles?: string[];
}

export const useVideoProduction = ({
  chapterId,
  scriptId,
  imageUrls = [],
  audioFiles = []
}: UseVideoProductionProps) => {
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

  // Load existing video production
  const loadVideoProduction = useCallback(async () => {
    if (!chapterId) return;
    
    setIsLoading(true);
    try {
      const data = await userService.getVideoProduction(chapterId);
      if (data) {
        setVideoProduction(data);
        setScenes(data.scenes || []);
        setEditorSettings(data.editorSettings || editorSettings);
      }
    } catch (error) {
      console.error('Error loading video production:', error);
    } finally {
      setIsLoading(false);
    }
  }, [chapterId]);

  // Initialize scenes from images and audio
  const initializeScenes = useCallback(async () => {
    if (!imageUrls.length) {
      toast.error('No images available to create scenes');
      return;
    }

    const newScenes: VideoScene[] = imageUrls.map((imageUrl, index) => ({
      id: `scene-${Date.now()}-${index}`,
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

    setScenes(newScenes);
    toast.success(`Initialized ${newScenes.length} scenes`);
  }, [imageUrls, audioFiles]);

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
  const processWithFFmpeg = useCallback(async (options?: Partial<FFmpegOptions>) => {
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
      console.error('Error downloading video:', error);
      toast.error('Failed to download video');
    }
  }, [videoProduction, chapterId, editorSettings]);

  // Save production
  const saveProduction = useCallback(async () => {
    if (!chapterId) return;

    setIsLoading(true);
    try {
      const data = {
        chapterId,
        scenes,
        editorSettings,
        scriptId
      };

      const result = await userService.saveVideoProduction(data);
      setVideoProduction(result);
      toast.success('Video production saved');
    } catch (error) {
      console.error('Error saving production:', error);
      toast.error('Failed to save video production');
    } finally {
      setIsLoading(false);
    }
  }, [chapterId, scenes, editorSettings, scriptId]);

  useEffect(() => {
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
    saveProduction
  };
};
