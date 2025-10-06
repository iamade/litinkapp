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

export const usePlotGeneration = (bookId: string) => {
  const [plotOverview, setPlotOverview] = useState<PlotOverview | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const generatePlot = async () => {
    if (!bookId) return;
    setIsGenerating(true);
    try {
      const result = await userService.generatePlotOverview(bookId);
      setPlotOverview(result);
      toast.success('Plot overview generated successfully!');
      // Refetch plot overview to ensure data is up to date
      await loadPlot();
    } catch (error) {
      console.error('Error generating plot:', error);
      toast.error('Failed to generate plot overview');
    } finally {
      setIsGenerating(false);
    }
  };

  // const savePlot = async (plot: PlotOverview) => {
  //   setIsLoading(true);
  //   try {
  //     await userService.savePlotOverview(bookId, plot);
  //     setPlotOverview(plot);
  //     toast.success('Plot overview saved!');
  //   } catch (error) {
  //     console.error('Error saving plot:', error);
  //     toast.error('Failed to save plot overview');
  //   } finally {
  //     setIsLoading(false);
  //   }
  // };

  const loadPlot = useCallback(async () => {
    if (!bookId) return;
    setIsLoading(true);
    try {
      const result = await userService.getPlotOverview(bookId);
      console.log("[DEBUG] PlotData: ", result);

      setPlotOverview(result);
    } catch (error: any) {
      // Check if it's a 404 (no data found) - treat as success
      if (error.message?.includes('404') || error.message?.includes('Not found')) {
        // No data exists yet - this is expected, set plotOverview to null
        setPlotOverview(null);
      } else {
        // Real error - show toast
        console.error('Error loading plot:', error);
        toast.error('Failed to load plot');
      }
    } finally {
      setIsLoading(false);
    }
  }, [bookId]);

  return {
    plotOverview,
    isGenerating,
    isLoading,
    generatePlot,
    // savePlot,
    loadPlot
  };
};