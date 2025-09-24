import { useState } from 'react';
import { userService } from '../services/userService';
import { toast } from 'react-hot-toast';

interface PlotOverview {
  logline: string;
  themes: string[];
  storyType: string;
  genre: string;
  tone: string;
  audience: string;
  setting: string;
  characters: Character[];
}

interface Character {
  name: string;
  role: string;
  characterArc: string;
  physicalDescription: string;
  personality: string;
  archetypes: string[];
  want: string;
  need: string;
  lie: string;
  ghost: string;
  imageUrl?: string;
}

export const usePlotGeneration = (bookId: string) => {
  const [plotOverview, setPlotOverview] = useState<PlotOverview | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const generatePlot = async () => {
    setIsGenerating(true);
    try {
      const result = await userService.generatePlotOverview(bookId);
      setPlotOverview(result);
      toast.success('Plot overview generated successfully!');
    } catch (error) {
      console.error('Error generating plot:', error);
      toast.error('Failed to generate plot overview');
    } finally {
      setIsGenerating(false);
    }
  };

  const savePlot = async (plot: PlotOverview) => {
    setIsLoading(true);
    try {
      await userService.savePlotOverview(bookId, plot);
      setPlotOverview(plot);
      toast.success('Plot overview saved!');
    } catch (error) {
      console.error('Error saving plot:', error);
      toast.error('Failed to save plot overview');
    } finally {
      setIsLoading(false);
    }
  };

  const loadPlot = async () => {
    setIsLoading(true);
    try {
      const result = await userService.getPlotOverview(bookId);
      setPlotOverview(result);
    } catch (error) {
      console.error('Error loading plot:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    plotOverview,
    isGenerating,
    isLoading,
    generatePlot,
    savePlot,
    loadPlot
  };
};