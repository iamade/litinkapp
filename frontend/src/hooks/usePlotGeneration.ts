import { useState, useCallback } from 'react';
import { userService } from '../services/userService';
import { toast } from 'react-hot-toast';

interface PlotOverview {
  id: string;
  book_id: string;
  logline: string;
  original_prompt?: string;
  themes: string[];
  story_type: string;
  genre: string;
  tone: string;
  audience: string;
  setting: string;
  characters: Character[];
  script_story_type: string;
  // New categorization fields
  medium?: string;      // Animation, Live Action, Hybrid, etc.
  format?: string;      // Film, TV Series, Short Film, etc.
  vibe_style?: string;  // Satire, Cinematic, Sitcom, etc.
}

interface Character {
  id: string;  // Added for character linking
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

interface UsePlotGenerationOptions {
  isProject?: boolean;
  inputPrompt?: string;
  projectType?: string;
}

export const usePlotGeneration = (
  bookOrProjectId: string,
  options: UsePlotGenerationOptions = {}
) => {
  const { isProject = false, inputPrompt, projectType } = options;
  const [plotOverview, setPlotOverview] = useState<PlotOverview | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);

  const generatePlot = async (refinementPrompt?: string) => {
    if (!bookOrProjectId) return;
    setIsGenerating(true);
    try {
      let result;
      if (isProject) {
        // Use project-specific plot generation
        result = await userService.generateProjectPlotOverview(
          bookOrProjectId,
          inputPrompt || '',
          { 
            projectType,
            refinementPrompt,
          }
        );
      } else {
        // Use book-specific plot generation (with refinement support)
        result = await userService.generatePlotOverview(
          bookOrProjectId,
          { 
            refinementPrompt,
          }
        );
      }
      setPlotOverview(result);
      if (refinementPrompt) {
        toast.success('Plot refined successfully!');
      } else {
        toast.success('Plot overview generated successfully!');
      }
      // Refetch plot overview to ensure data is up to date
      await loadPlot();
    } catch (error) {
      toast.error('Failed to generate plot overview');
    } finally {
      setIsGenerating(false);
    }
  };

  const loadPlot = useCallback(async () => {
    if (!bookOrProjectId) return;
    setIsLoading(true);
    try {
      let result;
      if (isProject) {
        result = await userService.getProjectPlotOverview(bookOrProjectId);
      } else {
        result = await userService.getPlotOverview(bookOrProjectId);
      }
      setPlotOverview(result);
    } catch (error: any) {
      // Check if it's a 404 (no data found) - treat as success
      if (error.message?.includes('404') || error.message?.includes('Not found')) {
        // No data exists yet - this is expected, set plotOverview to null
        setPlotOverview(null);
      } else {
        // Real error - show toast
        toast.error('Failed to load plot');
      }
    } finally {
      setIsLoading(false);
    }
  }, [bookOrProjectId, isProject]);

  const deleteCharacter = async (characterId: string) => {
    try {
      await userService.deleteCharacter(characterId);

      // Update local state by removing the character
      setPlotOverview(prev => {
        if (!prev) return null;
        return {
          ...prev,
          characters: prev.characters.filter(char => {
            // Character might have id or might be identified by name
            // Backend returns character with id field
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

  // Update plot overview fields (for inline editing)
  const updatePlot = async (updates: Partial<PlotOverview>) => {
    if (!plotOverview?.id) {
      toast.error('No plot to update');
      return;
    }

    setIsUpdating(true);
    try {
      await userService.updatePlotOverview(plotOverview.id, updates);
      
      // Optimistically update local state
      setPlotOverview(prev => prev ? { ...prev, ...updates } : null);
      
      toast.success('Plot updated successfully');
    } catch (error) {
      toast.error('Failed to update plot');
      // Reload to get correct state
      await loadPlot();
    } finally {
      setIsUpdating(false);
    }
  };

  return {
    plotOverview,
    isGenerating,
    isLoading,
    isUpdating,
    generatePlot,
    loadPlot,
    deleteCharacter,
    updatePlot
  };
};