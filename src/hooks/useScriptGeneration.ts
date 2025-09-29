import { useState, useCallback, useEffect } from 'react';
import { userService } from '../services/userService';
import { toast } from 'react-hot-toast';

interface SceneDescription {
  scene_number: number;
  location: string;
  time_of_day: string;
  characters: string[];
  key_actions: string;
  estimated_duration: number;
  visual_description: string;
  audio_requirements: string;
}

interface ChapterScript {
  id: string;
  chapter_id: string;
  script_style: string;
  script_name: string;
  script: string;
  scene_descriptions: SceneDescription[];
  characters: string[];
  character_details: string;
  acts: Act[];
  beats: Beat[];
  scenes: Scene[];
  created_at: string;
  status: 'draft' | 'ready' | 'approved';
}

interface Act {
  act_number: number;
  title: string;
  description: string;
  duration: number;
  scenes: number[];
}

interface Beat {
  beat_number: number;
  act: number;
  title: string;
  description: string;
  emotional_tone: string;
  duration: number;
}

interface Scene {
  scene_number: number;
  act: number;
  beat: string;
  location: string;
  time_of_day: string;
  characters: string[];
  dialogue: string;
  action: string;
  visual_description: string;
  duration: number;
  camera_notes?: string;
  audio_notes?: string;
}

interface ScriptGenerationOptions {
  includeCharacterProfiles: boolean;
  targetDuration?: number | "auto";
  sceneCount?: number;
  focusAreas: string[];
}

export const useScriptGeneration = (chapterId: string) => {
  const [generatedScripts, setGeneratedScripts] = useState<ChapterScript[]>([]);
  const [selectedScript, setSelectedScript] = useState<ChapterScript | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);

  // Reset selectedScript when chapterId changes
  useEffect(() => {
    setSelectedScript(null);
  }, [chapterId]);

  const loadScripts = useCallback(async () => {
    if (!chapterId) return;

    setIsLoading(true);
    try {
      const response = await userService.getChapterScripts(chapterId);
      const scripts = response.scripts || [];
      
      // Convert legacy scripts to new format
      const formattedScripts: ChapterScript[] = scripts.map((script: any) => ({
        id: script.id,
        chapter_id: script.chapter_id,
        script_style: script.script_style,
        script_name: script.script_name || 'Unnamed Script',
        script: script.script,
        scene_descriptions: (script.scene_descriptions || []) as unknown as SceneDescription[],
        characters: script.characters || [],
        character_details: script.character_details || '',
        acts: script.acts || [],
        beats: script.beats || [],
        scenes: script.scenes || [],
        created_at: script.created_at,
        status: script.status || 'draft'
      }));

      setGeneratedScripts(formattedScripts);
      
      // Auto-select first script if none selected
      if (!selectedScript && formattedScripts.length > 0) {
        setSelectedScript(formattedScripts[0]);
      }
    } catch (error) {
      console.error('Error loading scripts:', error);
      toast.error('Failed to load scripts');
    } finally {
      setIsLoading(false);
    }
  }, [chapterId]);

  const generateScript = async (
    scriptStyle: string,
    options: ScriptGenerationOptions
  ) => {
    setIsGeneratingScript(true);
    try {
      const result = await userService.generateScriptAndScenes(
        chapterId,
        scriptStyle,
        {
          targetDuration: options.targetDuration,
          includeCharacterProfiles: options.includeCharacterProfiles,
          sceneCount: options.sceneCount,
          focusAreas: options.focusAreas
        }
      );
      
      // Create new script object
      const newScript: ChapterScript = {
        id: result.script_id || Date.now().toString(),
        chapter_id: chapterId,
        script_style: scriptStyle,
        script_name: result.script_name || 'Unnamed Script',
        script: result.script,
        scene_descriptions: (result.scene_descriptions || []) as unknown as SceneDescription[],
        characters: result.characters || [],
        character_details: result.character_details || '',
        acts: [],
        beats: [],
        scenes: [],
        created_at: new Date().toISOString(),
        status: 'draft'
      };

      setGeneratedScripts(prev => [newScript, ...prev]);
      setSelectedScript(newScript);
      
      toast.success('Script generated successfully!');
      
      // Reload to get updated data from server
      await loadScripts();
    } catch (error) {
      console.error('Error generating script:', error);
      toast.error('Failed to generate script');
    } finally {
      setIsGeneratingScript(false);
    }
  };

  const selectScript = (script: ChapterScript) => {
    setSelectedScript(script);
    toast.success(`Selected ${script.script_style} script`);
  };

  const updateScript = async (scriptId: string, updates: Partial<ChapterScript>) => {
    try {
      // Update locally first
      setGeneratedScripts(prev => 
        prev.map(script => 
          script.id === scriptId ? { ...script, ...updates } : script
        )
      );

      if (selectedScript?.id === scriptId) {
        setSelectedScript(prev => prev ? { ...prev, ...updates } : null);
      }

      // TODO: Send update to backend
      // await userService.updateScript(scriptId, updates);
      
      toast.success('Script updated successfully!');
    } catch (error) {
      console.error('Error updating script:', error);
      toast.error('Failed to update script');
      // Reload on error
      await loadScripts();
    }
  };

  const deleteScript = async (scriptId: string) => {
    if (!confirm('Are you sure you want to delete this script?')) return;

    try {
      // Remove locally first
      setGeneratedScripts(prev => prev.filter(script => script.id !== scriptId));
      
      if (selectedScript?.id === scriptId) {
        const remaining = generatedScripts.filter(script => script.id !== scriptId);
        setSelectedScript(remaining.length > 0 ? remaining[0] : null);
      }

      await userService.deleteScript(scriptId);
      toast.success('Script deleted successfully!');
    } catch (error) {
      console.error('Error deleting script:', error);
      toast.error('Failed to delete script');
      // Reload on error
      await loadScripts();
    }
  };

  return {
    generatedScripts,
    selectedScript,
    isLoading,
    isGeneratingScript,
    loadScripts,
    generateScript,
    selectScript,
    updateScript,
    deleteScript
  };
};