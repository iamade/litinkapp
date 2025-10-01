import { useState, useCallback, useRef } from 'react';
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
}

export const useAudioGeneration = (chapterId: string) => {
  const [audioAssets, setAudioAssets] = useState<AudioAssets>({
    narration: [],
    music: [],
    effects: [],
    ambiance: [],
    character: [],
    sfx: []
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
        narration: [],
        music: [],
        effects: [],
        ambiance: [],
        character: [],
        sfx: []
      };

      response.audio_files?.forEach((file: any) => {
        console.log('[DEBUG] Audio file from backend:', { id: file.id, type: file.type, audio_type: file.audio_type });
        const frontendType = mapDbTypeToFrontend(file.audio_type || file.type);
        const audioFile: AudioFile = {
          id: file.id,
          type: frontendType,
          sceneNumber: file.metadata?.scene_number || 0,
          url: file.audio_url,
          duration: file.duration,
          character: file.character_name,
          name: file.text_content || `${frontendType}_${file.metadata?.scene_number || 0}`,
          status: file.generation_status || 'completed',
          generatedAt: file.created_at,
          waveform: file.waveform,
          volume: file.volume || 1.0,
          startTime: file.start_time || 0,
          endTime: file.end_time || file.duration
        };

        organized[frontendType].push(audioFile);
      });

      setAudioAssets(organized);
    } catch (error: any) {
      // Check if it's a 404 (no data found) - treat as success
      if (error.message?.includes('404') || error.message?.includes('Not found')) {
        // No data exists yet - this is expected, set empty AudioAssets state
        setAudioAssets({
          narration: [],
          music: [],
          effects: [],
          ambiance: [],
          character: [],
          sfx: []
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

    // DEBUG: Log the actual scene data structure
    console.log('[DEBUG] Scene data structure:', JSON.stringify(sceneData, null, 2));
    console.log('[DEBUG] Scene data keys:', Object.keys(sceneData));

    try {
      const generationPromises: Array<{ promise: Promise<any>, type: keyof AudioAssets }> = [];

      // Generate narration if needed
      if (options.generateNarration && sceneData.narration) {
        generationPromises.push({
          promise: userService.generateSceneNarration(chapterId, sceneNumber, {
            narration: sceneData.narration,
            voiceModel: options.voiceModel,
            quality: options.audioQuality
          }),
          type: 'narration'
        });
      }

      // Generate music
      if (options.generateMusic) {
        generationPromises.push({
          promise: userService.generateSceneMusic(chapterId, sceneNumber, {
            mood: sceneData.mood || 'neutral',
            style: options.musicStyle,
            duration: sceneData.duration || sceneData.estimated_duration || 30,
            quality: options.audioQuality
          }),
          type: 'music'
        });
      }

      // Generate sound effects
      if (options.generateEffects) {
        generationPromises.push({
          promise: userService.generateSceneEffects(chapterId, sceneNumber, {
            actions: sceneData.key_actions || sceneData.narration || '',
            intensity: options.effectsIntensity,
            quality: options.audioQuality
          }),
          type: 'effects'
        });
      }

      // Generate ambiance
      if (options.generateAmbiance) {
        generationPromises.push({
          promise: userService.generateSceneAmbiance(chapterId, sceneNumber, {
            location: sceneData.location || 'unknown',
            timeOfDay: sceneData.time_of_day || 'day',
            type: options.ambianceType,
            quality: options.audioQuality
          }),
          type: 'ambiance'
        });
      }

      const results = await Promise.all(generationPromises.map(p => p.promise));
      const recordIds: string[] = [];

      // Process results and add temporary entries to audioAssets
      results.forEach((result, index) => {
        if (result.record_id) {
          const type = generationPromises[index].type;
          const tempAudioFile: AudioFile = {
            id: result.record_id,
            type: type,
            sceneNumber: sceneNumber,
            url: '',
            duration: 0,
            name: `${type}_${sceneNumber}`,
            status: 'generating',
            volume: 1.0,
            startTime: 0,
            endTime: 0
          };

          setAudioAssets(prev => ({
            ...prev,
            [type]: [...prev[type], tempAudioFile]
          }));

          recordIds.push(result.record_id);
        }
      });

      // Start polling if we have record IDs
      if (recordIds.length > 0) {
        pollAudioStatus(recordIds);
      }

      toast.success(`Started audio generation for Scene ${sceneNumber}`);
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
    console.log('[DEBUG] generateAllAudio called with scenes:', scenes);
    console.log('[DEBUG] generateAllAudio scenes length:', scenes.length);
    toast.success(`Starting audio generation for ${scenes.length} scenes`);

    for (let i = 0; i < scenes.length; i++) {
      const scene = scenes[i];
      console.log('[DEBUG] Processing scene:', scene);

      // Handle both string and object formats
      let sceneData: any;
      let sceneNumber: number;

      if (typeof scene === 'string') {
        // Convert string scene to object format
        sceneNumber = i + 1;
        sceneData = {
          scene_number: sceneNumber,
          narration: scene,
          mood: 'neutral',
          key_actions: scene,
          duration: 30, // default duration
          location: 'unknown',
          time_of_day: 'day'
        };
        console.log('[DEBUG] Converted string scene to object:', sceneData);
      } else if (typeof scene === 'object' && scene !== null) {
        // Object format - use as is
        sceneNumber = scene.scene_number || i + 1;
        sceneData = scene;
        console.log('[DEBUG] Using object scene data:', sceneData);
      } else {
        console.log('[DEBUG] Invalid scene format:', scene);
        continue;
      }

      console.log('[DEBUG] Calling generateAudioForScene for scene_number:', sceneNumber);
      await generateAudioForScene(sceneNumber, sceneData, options);
      // Add delay to avoid rate limiting
      await new Promise(resolve => setTimeout(resolve, 1000));
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

  const deleteAllAudio = async (type: keyof AudioAssets) => {
    const filesToDelete = audioAssets[type];
    if (filesToDelete.length === 0) {
      toast.error('No audio files to delete');
      return;
    }

    try {
      // Delete all files of this type
      const deletePromises = filesToDelete.map(file => userService.deleteAudioFile(chapterId, file.id));
      await Promise.all(deletePromises);

      // Update state to remove all files of this type
      setAudioAssets(prev => ({
        ...prev,
        [type]: []
      }));

      toast.success(`All ${type} audio files deleted`);
    } catch (error) {
      console.error('Error deleting all audio files:', error);
      toast.error(`Failed to delete all ${type} audio files`);
    }
  };

  const pollAudioStatus = async (recordIds: string[]) => {
    const pollInterval = 2000; // Poll every 2 seconds
    const maxPolls = 30; // Maximum 30 polls (60 seconds)
    const pollingIds = new Set(recordIds);

    for (let i = 0; i < maxPolls && pollingIds.size > 0; i++) {
      const pollPromises = Array.from(pollingIds).map(async (recordId) => {
        try {
          const statusResponse = await userService.getAudioGenerationStatus(chapterId, recordId);

          if (statusResponse.status === 'completed') {
            // Update the audio file with completed status and URL
            setAudioAssets(prev => {
              const updated = { ...prev };
              Object.keys(updated).forEach(type => {
                updated[type as keyof AudioAssets] = updated[type as keyof AudioAssets].map(file =>
                  file.id === recordId ? {
                    ...file,
                    status: 'completed',
                    url: statusResponse.audio_url || file.url,
                    duration: statusResponse.duration || file.duration,
                    generatedAt: new Date().toISOString()
                  } : file
                );
              });
              return updated;
            });
            pollingIds.delete(recordId);
            toast.success(`Audio generation completed`);
          } else if (statusResponse.status === 'failed') {
            // Update with failed status
            setAudioAssets(prev => {
              const updated = { ...prev };
              Object.keys(updated).forEach(type => {
                updated[type as keyof AudioAssets] = updated[type as keyof AudioAssets].map(file =>
                  file.id === recordId ? { ...file, status: 'failed' } : file
                );
              });
              return updated;
            });
            pollingIds.delete(recordId);
            toast.error(`Audio generation failed`);
          }
          // Still processing, continue polling
        } catch (error) {
          console.error('Error polling audio status:', error);
          // Continue polling on error
        }
      });

      await Promise.all(pollPromises);

      if (pollingIds.size > 0) {
        // Wait before next poll
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }

    // Timeout for remaining IDs
    if (pollingIds.size > 0) {
      setAudioAssets(prev => {
        const updated = { ...prev };
        Array.from(pollingIds).forEach(recordId => {
          Object.keys(updated).forEach(type => {
            updated[type as keyof AudioAssets] = updated[type as keyof AudioAssets].map(file =>
              file.id === recordId ? { ...file, status: 'failed' } : file
            );
          });
        });
        return updated;
      });
      toast.error(`Audio generation timed out`);
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
    pollAudioStatus,
    playAudio,
    pauseAudio,
    stopAllAudio,
    setAudioVolume,
    deleteAudio,
    deleteAllAudio,
    exportAudioMix,
    setSelectedAudioFiles
  };
};
