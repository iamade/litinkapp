import { useState, useCallback } from 'react';
import { userService } from '../services/userService';
import { toast } from 'react-hot-toast';

interface SceneImage {
  sceneNumber: number;
  imageUrl: string;
  prompt: string;
  characters: string[];
  generationStatus: 'pending' | 'generating' | 'completed' | 'failed';
  generatedAt?: string;
  id?: string;
}

interface CharacterImage {
  name: string;
  imageUrl: string;
  prompt: string;
  generationStatus: 'pending' | 'generating' | 'completed' | 'failed';
  generatedAt?: string;
  id?: string;
}

interface ImageGenerationOptions {
  style: 'realistic' | 'cartoon' | 'cinematic' | 'fantasy' | 'sketch';
  quality: 'standard' | 'hd';
  aspectRatio: '16:9' | '4:3' | '1:1' | '9:16';
  useCharacterReferences: boolean;
  includeBackground: boolean;
  lightingMood: string;
}

export const useImageGeneration = (chapterId: string) => {
  const [sceneImages, setSceneImages] = useState<Record<number, SceneImage>>({});
  const [characterImages, setCharacterImages] = useState<Record<string, CharacterImage>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [generatingScenes, setGeneratingScenes] = useState<Set<number>>(new Set());
  const [generatingCharacters, setGeneratingCharacters] = useState<Set<string>>(new Set());

  const loadImages = useCallback(async () => {
    if (!chapterId) return;

    setIsLoading(true);
    try {
      const response = await userService.getChapterImages(chapterId);

      // Organize images by type from the unified images array
      const sceneImagesMap: Record<number, SceneImage> = {};
      const characterImagesMap: Record<string, CharacterImage> = {};

      response.images.forEach((img: any) => {
        const metadata = img.metadata || {};
        if (metadata.image_type === 'scene') {
          sceneImagesMap[metadata.scene_number] = {
            sceneNumber: metadata.scene_number,
            imageUrl: img.image_url || '',
            prompt: img.image_prompt || '',
            characters: [], // Could be extracted from metadata if available
            generationStatus: img.status === 'completed' ? 'completed' : 'failed',
            generatedAt: img.created_at,
            id: img.id
          };
        } else if (metadata.image_type === 'character') {
          characterImagesMap[metadata.character_name] = {
            name: metadata.character_name,
            imageUrl: img.image_url || '',
            prompt: img.image_prompt || '',
            generationStatus: img.status === 'completed' ? 'completed' : 'failed',
            generatedAt: img.created_at,
            id: img.id
          };
        }
      });

      setSceneImages(sceneImagesMap);
      setCharacterImages(characterImagesMap);

    } catch (error: any) {
      // Check if it's a 404 (no data found) - treat as success
      if (error.message?.includes('404') || error.message?.includes('Not found')) {
        // No data exists yet - this is expected, set empty state
        setSceneImages({});
        setCharacterImages({});
      } else {
        // Real error - show toast
        console.error('Error loading images:', error);
        toast.error('Failed to load images');
      }
    } finally {
      setIsLoading(false);
    }
  }, [chapterId]);

  const generateSceneImage = async (
    sceneNumber: number,
    sceneDescription: string,
    options: ImageGenerationOptions
  ) => {
    setGeneratingScenes(prev => new Set(prev).add(sceneNumber));

    try {
      // Create initial scene image entry
      const tempImage: SceneImage = {
        sceneNumber,
        imageUrl: '',
        prompt: sceneDescription,
        characters: [],
        generationStatus: 'generating'
      };

      setSceneImages(prev => ({ ...prev, [sceneNumber]: tempImage }));

      const request = {
        scene_description: sceneDescription,
        style: options.style,
        aspect_ratio: options.aspectRatio,
        custom_prompt: options.lightingMood ? `Lighting mood: ${options.lightingMood}` : undefined
      };

      const result = await userService.generateSceneImage(chapterId, sceneNumber, request);

      // Update with generated image
      setSceneImages(prev => ({
        ...prev,
        [sceneNumber]: {
          ...tempImage,
          imageUrl: result.image_url,
          generationStatus: 'completed',
          generatedAt: new Date().toISOString(),
          id: result.record_id
        }
      }));

      toast.success(`Generated image for Scene ${sceneNumber}`);

    } catch (error: any) {
      console.error('Error generating scene image:', error);

      setSceneImages(prev => ({
        ...prev,
        [sceneNumber]: {
          ...prev[sceneNumber],
          generationStatus: 'failed'
        }
      }));

      toast.error(`Failed to generate image for Scene ${sceneNumber}`);
    } finally {
      setGeneratingScenes(prev => {
        const newSet = new Set(prev);
        newSet.delete(sceneNumber);
        return newSet;
      });
    }
  };

  const generateCharacterImage = async (
    characterName: string,
    characterDescription: string,
    options: ImageGenerationOptions
  ) => {
    setGeneratingCharacters(prev => new Set(prev).add(characterName));

    try {
      const tempImage: CharacterImage = {
        name: characterName,
        imageUrl: '',
        prompt: characterDescription,
        generationStatus: 'generating'
      };

      setCharacterImages(prev => ({ ...prev, [characterName]: tempImage }));

      const request = {
        character_name: characterName,
        character_description: characterDescription,
        style: options.style,
        aspect_ratio: options.aspectRatio,
        custom_prompt: options.lightingMood ? `Lighting mood: ${options.lightingMood}` : undefined
      };

      const result = await userService.generateCharacterImage(chapterId, request);

      // Start polling for status if we have a record_id
      if (result.record_id) {
        pollCharacterImageStatus(characterName, result.record_id);
      } else {
        // Fallback: mark as completed immediately (shouldn't happen with new implementation)
        setCharacterImages(prev => ({
          ...prev,
          [characterName]: {
            ...tempImage,
            generationStatus: 'completed',
            generatedAt: new Date().toISOString(),
            id: result.record_id
          }
        }));
        toast.success(`Generated image for ${characterName}`);
      }

    } catch (error: any) {
      console.error('Error generating character image:', error);

      setCharacterImages(prev => ({
        ...prev,
        [characterName]: {
          ...prev[characterName],
          generationStatus: 'failed'
        }
      }));

      toast.error(`Failed to generate image for ${characterName}`);
    } finally {
      setGeneratingCharacters(prev => {
        const newSet = new Set(prev);
        newSet.delete(characterName);
        return newSet;
      });
    }
  };

  const regenerateImage = async (
    type: 'scene' | 'character',
    identifier: number | string,
    options: ImageGenerationOptions
  ) => {
    if (type === 'scene') {
      const sceneImage = sceneImages[identifier as number];
      if (sceneImage) {
        await generateSceneImage(identifier as number, sceneImage.prompt, options);
      }
    } else {
      const characterImage = characterImages[identifier as string];
      if (characterImage) {
        await generateCharacterImage(
          identifier as string,
          characterImage.prompt,
          options
        );
      }
    }
  };

  const deleteImage = async (type: 'scene' | 'character', identifier: number | string) => {
    try {
      if (type === 'scene') {
        await userService.deleteSceneImage(chapterId, identifier as number);
        setSceneImages(prev => {
          const newImages = { ...prev };
          delete newImages[identifier as number];
          return newImages;
        });
      } else {
        await userService.deleteCharacterImage(chapterId, identifier as string);
        setCharacterImages(prev => {
          const newImages = { ...prev };
          delete newImages[identifier as string];
          return newImages;
        });
      }
      
      toast.success('Image deleted successfully');
    } catch (error) {
      console.error('Error deleting image:', error);
      toast.error('Failed to delete image');
    }
  };

  const generateAllSceneImages = async (
    scenes: any[],
    options: ImageGenerationOptions
  ) => {
    toast.success(`Starting generation of ${scenes.length} scene images`);

    for (const scene of scenes) {
      if (typeof scene === 'object' && scene.scene_number) {
        const sceneDescription = scene.visual_description || scene.description || '';
        await generateSceneImage(scene.scene_number, sceneDescription, options);
        // Add small delay between generations to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
  };

  const pollCharacterImageStatus = async (characterName: string, recordId: string) => {
    const pollInterval = 2000; // Poll every 2 seconds
    const maxPolls = 30; // Maximum 30 polls (60 seconds)

    for (let i = 0; i < maxPolls; i++) {
      try {
        const statusResponse = await userService.getImageGenerationStatus(chapterId, recordId);

        if (statusResponse.status === 'completed') {
          // Update with completed image
          setCharacterImages(prev => ({
            ...prev,
            [characterName]: {
              ...prev[characterName],
              imageUrl: statusResponse.image_url || '',
              generationStatus: 'completed',
              generatedAt: new Date().toISOString(),
              id: recordId
            }
          }));
          toast.success(`Generated image for ${characterName}`);
          return;
        } else if (statusResponse.status === 'failed') {
          // Update with failed status
          setCharacterImages(prev => ({
            ...prev,
            [characterName]: {
              ...prev[characterName],
              generationStatus: 'failed'
            }
          }));
          toast.error(`Failed to generate image for ${characterName}`);
          return;
        }

        // Still processing, wait and poll again
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      } catch (error) {
        console.error('Error polling character image status:', error);
        // Continue polling on error
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }

    // Timeout reached
    setCharacterImages(prev => ({
      ...prev,
      [characterName]: {
        ...prev[characterName],
        generationStatus: 'failed'
      }
    }));
    toast.error(`Image generation for ${characterName} timed out`);
  };

  const generateAllCharacterImages = async (
    characters: string[],
    characterDetails: Record<string, string>,
    options: ImageGenerationOptions
  ) => {
    toast.success(`Starting generation of ${characters.length} character images`);

    for (const character of characters) {
      const description = characterDetails[character] || `Portrait of ${character}`;
      await generateCharacterImage(character, description, options);
      // Add small delay between generations
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  };

  return {
    sceneImages,
    characterImages,
    isLoading,
    generatingScenes,
    generatingCharacters,
    loadImages,
    generateSceneImage,
    generateCharacterImage,
    regenerateImage,
    deleteImage,
    generateAllSceneImages,
    generateAllCharacterImages
  };
};