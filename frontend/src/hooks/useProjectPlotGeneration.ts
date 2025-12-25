import { useState, useCallback } from 'react';
import { userService } from '../services/userService';
import { toast } from 'react-hot-toast';

interface PlotOverview {
  logline: string;
  themes: string[];
  story_type: string;
  genre: string;
  tone: string;
  audience: string;
  setting: string;
  characters: Character[];
  script_story_type: string;
}

interface Character {
  name: string;
  role: string;
  character_arc: string;
  physical_description: string;
  personality: string;
  archetypes: string[];
  want: string;
  need: string;
  lie: string;
  ghost: string;
  image_url?: string;
}

interface UseProjectPlotGenerationOptions {
  projectId: string;
  inputPrompt: string;
  projectType?: string;
}

export const useProjectPlotGeneration = ({ projectId, inputPrompt, projectType }: UseProjectPlotGenerationOptions) => {
  const [plotOverview, setPlotOverview] = useState<PlotOverview | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const generatePlot = async (options?: {
    storyType?: string;
    genre?: string;
    tone?: string;
    audience?: string;
    refinementPrompt?: string;
  }) => {
    if (!projectId || !inputPrompt) {
      toast.error('Project ID and prompt are required');
      return;
    }
    
    setIsGenerating(true);
    try {
      const result = await userService.generateProjectPlotOverview(
        projectId,
        inputPrompt,
        {
          projectType,
          storyType: options?.storyType,
          genre: options?.genre,
          tone: options?.tone,
          audience: options?.audience,
          refinementPrompt: options?.refinementPrompt,
        }
      );
      
      // Extract plot_overview from response structure
      const plotData = result.plot_overview || result;
      setPlotOverview(plotData);
      
      if (options?.refinementPrompt) {
        toast.success('Plot refined successfully!');
      } else {
        toast.success('Plot overview generated successfully!');
      }
      
      // Refetch to ensure data is up to date
      await loadPlot();
    } catch (error: any) {
      console.error('Failed to generate project plot:', error);
      toast.error(error.message || 'Failed to generate plot overview');
    } finally {
      setIsGenerating(false);
    }
  };

  /**
   * Refine the current plot with a follow-up prompt
   */
  const refinePlot = async (refinementPrompt: string) => {
    return generatePlot({ refinementPrompt });
  };

  const loadPlot = useCallback(async () => {
    if (!projectId) return;
    setIsLoading(true);
    try {
      const result = await userService.getProjectPlotOverview(projectId);
      setPlotOverview(result);
    } catch (error: any) {
      // Check if it's a 404 (no data found) - treat as success
      if (error.message?.includes('404') || error.message?.includes('Not found')) {
        // No data exists yet - this is expected
        setPlotOverview(null);
      } else {
        // Real error - show toast
        console.error('Failed to load project plot:', error);
        toast.error('Failed to load plot');
      }
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  const deleteCharacter = async (characterId: string) => {
    try {
      await userService.deleteCharacter(characterId);

      // Update local state by removing the character
      setPlotOverview(prev => {
        if (!prev) return null;
        return {
          ...prev,
          characters: prev.characters.filter(char => {
            const charId = (char as any).id;
            return charId !== characterId;
          })
        };
      });

      toast.success('Character deleted successfully');
    } catch (error) {
      toast.error('Failed to delete character');
      throw error;
    }
  };

  return {
    plotOverview,
    isGenerating,
    isLoading,
    generatePlot,
    refinePlot,
    loadPlot,
    deleteCharacter
  };
};
