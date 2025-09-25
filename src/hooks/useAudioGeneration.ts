import { useState, useCallback, useRef } from 'react';
import { toast } from 'react-hot-toast';
import { userService } from '../services/userService';

interface AudioFile {
  id: string;
  type: 'dialogue' | 'narration' | 'music' | 'effects' | 'ambiance';
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
  dialogue: AudioFile[];
  narration: AudioFile[];
  music: AudioFile[];
  effects: AudioFile[];
  ambiance: AudioFile[];
}

interface AudioGenerationOptions {
  voiceModel: string;
  musicStyle: string;
  effectsIntensity: 'subtle' | 'moderate' | 'dramatic';
  ambianceType: string;
  audioQuality: 'standard' | 'high' | 'premium';
  generateDialogue: boolean;
  generateNarration: boolean;
  generateMusic: boolean;
  generateEffects: boolean;
  generateAmbiance: boolean;
}

export const useAudioGeneration = (chapterId: string) => {
  const [audioAssets, setAudioAssets] = useState<AudioAssets>({
    dialogue: [],
    narration: [],
    music: [],
    effects: [],
    ambiance: []
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [generatingAudio, setGeneratingAudio] = useState<Set<string>>(new Set());
  const [selectedAudioFiles, setSelectedAudioFiles] = useState<Set<string>>(new Set());
  const audioRefs = useRef<{ [key: string]: HTMLAudioElement }>({});

  const loadAudioAssets = useCallback(async () => {
    if (!chapterId) return;

    setIsLoading(true);
    try {
      const response = await userService.getChapterAudio(chapterId);
      
      // Organize audio by type
      const organized: AudioAssets = {
        dialogue: [],
        narration: [],
        music: [],
        effects: [],
        ambiance: []
      };

      response.audio_files?.forEach((file: any) => {
        const audioFile: AudioFile = {
          id: file.id,
          type: file.type,
          sceneNumber: file.scene_number,
          url: file.url,
          duration: file.duration,
          character: file.character,
          name: file.name || `${file.type}_${file.scene_number}`,
          status: 'completed',
          generatedAt: file.created_at,
          waveform: file.waveform,
          volume: file.volume || 1.0,
          startTime: file.start_time || 0,
          endTime: file.end_time || file.duration
        };

        organized[file.type].push(audioFile);
      });

      setAudioAssets(organized);
    } catch (error: any) {
      // Check if it's a 404 (no data found) - treat as success
      if (error.message?.includes('404') || error.message?.includes('Not found')) {
        // No data exists yet - this is expected, set empty AudioAssets state
        setAudioAssets({
          dialogue: [],
          narration: [],
          music: [],
          effects: [],
          ambiance: []
        });
      } else {
        // Real error - show toast
        console.error('Error loading audio assets:', error);
        toast.error('Failed to load audio assets');
      }
    } finally {
      setIsLoading(false);
    }
  }, [chapterId]);

  const generateAudioForScene = async (
    sceneNumber: number,
    sceneData: any,
    options: AudioGenerationOptions
  ) => {
    const generationId = `scene_${sceneNumber}`;
    setGeneratingAudio(prev => new Set(prev).add(generationId));

    try {
      const promises = [];

      // Generate dialogue if needed
      if (options.generateDialogue && sceneData.dialogue) {
        promises.push(
          userService.generateSceneDialogue(chapterId, sceneNumber, {
            dialogue: sceneData.dialogue,
            characters: sceneData.characters,
            voiceModel: options.voiceModel,
            quality: options.audioQuality
          })
        );
      }

      // Generate narration if needed
      if (options.generateNarration && sceneData.narration) {
        promises.push(
          userService.generateSceneNarration(chapterId, sceneNumber, {
            narration: sceneData.narration,
            voiceModel: options.voiceModel,
            quality: options.audioQuality
          })
        );
      }

      // Generate music
      if (options.generateMusic) {
        promises.push(
          userService.generateSceneMusic(chapterId, sceneNumber, {
            mood: sceneData.mood || 'neutral',
            style: options.musicStyle,
            duration: sceneData.duration,
            quality: options.audioQuality
          })
        );
      }

      // Generate sound effects
      if (options.generateEffects) {
        promises.push(
          userService.generateSceneEffects(chapterId, sceneNumber, {
            actions: sceneData.key_actions,
            intensity: options.effectsIntensity,
            quality: options.audioQuality
          })
        );
      }

      // Generate ambiance
      if (options.generateAmbiance) {
        promises.push(
          userService.generateSceneAmbiance(chapterId, sceneNumber, {
            location: sceneData.location,
            timeOfDay: sceneData.time_of_day,
            type: options.ambianceType,
            quality: options.audioQuality
          })
        );
      }

      const results = await Promise.all(promises);
      
      // Update audio assets with new files
      await loadAudioAssets();
      
      toast.success(`Generated audio for Scene ${sceneNumber}`);
    } catch (error) {
      console.error('Error generating audio:', error);
      toast.error(`Failed to generate audio for Scene ${sceneNumber}`);
    } finally {
      setGeneratingAudio(prev => {
        const newSet = new Set(prev);
        newSet.delete(generationId);
        return newSet;
      });
    }
  };

  const generateAllAudio = async (
    scenes: any[],
    options: AudioGenerationOptions
  ) => {
    toast.success(`Starting audio generation for ${scenes.length} scenes`);
    
    for (const scene of scenes) {
      if (scene.scene_number) {
        await generateAudioForScene(scene.scene_number, scene, options);
        // Add delay to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
  };

  const playAudio = (audioId: string) => {
    const audio = audioRefs.current[audioId];
    if (audio) {
      audio.play();
    }
  };

  const pauseAudio = (audioId: string) => {
    const audio = audioRefs.current[audioId];
    if (audio) {
      audio.pause();
    }
  };

  const stopAllAudio = () => {
    Object.values(audioRefs.current).forEach(audio => {
      audio.pause();
      audio.currentTime = 0;
    });
  };

  const setAudioVolume = (audioId: string, volume: number) => {
    const audio = audioRefs.current[audioId];
    if (audio) {
      audio.volume = Math.max(0, Math.min(1, volume));
    }

    // Update in state
    setAudioAssets(prev => {
      const updated = { ...prev };
      Object.keys(updated).forEach(type => {
        updated[type as keyof AudioAssets] = updated[type as keyof AudioAssets].map(file =>
          file.id === audioId ? { ...file, volume } : file
        );
      });
      return updated;
    });
  };

  const deleteAudio = async (audioId: string, type: keyof AudioAssets) => {
    try {
      await userService.deleteAudioFile(chapterId, audioId);
      
      setAudioAssets(prev => ({
        ...prev,
        [type]: prev[type].filter(file => file.id !== audioId)
      }));
      
      toast.success('Audio file deleted');
    } catch (error) {
      console.error('Error deleting audio:', error);
      toast.error('Failed to delete audio file');
    }
  };

  const exportAudioMix = async () => {
    try {
      const response = await userService.exportAudioMix(chapterId, audioAssets);
      
      // Download the mixed audio file
      const link = document.createElement('a');
      link.href = response.url;
      link.download = `chapter_${chapterId}_audio_mix.mp3`;
      link.click();
      
      toast.success('Audio mix exported successfully');
    } catch (error) {
      console.error('Error exporting audio mix:', error);
      toast.error('Failed to export audio mix');
    }
  };

  return {
    audioAssets,
    isLoading,
    generatingAudio,
    selectedAudioFiles,
    audioRefs,
    loadAudioAssets,
    generateAudioForScene,
    generateAllAudio,
    playAudio,
    pauseAudio,
    stopAllAudio,
    setAudioVolume,
    deleteAudio,
    exportAudioMix,
    setSelectedAudioFiles
  };
};
