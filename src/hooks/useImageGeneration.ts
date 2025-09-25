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
      
      // Organize scene images by scene number
      const sceneImagesMap: Record<number, SceneImage> = {};
      response.scene_images?.forEach((img: any) => {
        sceneImagesMap[img.scene_number] = {
          sceneNumber: img.scene_number,
          imageUrl: img.image_url,
          prompt: img.prompt,
          characters: img.characters || [],
          generationStatus: img.status || 'completed',
          generatedAt: img.created_at,
          id: img.id
        };
      });
      setSceneImages(sceneImagesMap);

      // Organize character images by character name
      const characterImagesMap: Record<string, CharacterImage> = {};
      response.character_images?.forEach((img: any) => {
        characterImagesMap[img.character_name] = {
          name: img.character_name,
          imageUrl: img.image_url,
          prompt: img.prompt,
          generationStatus: img.status || 'completed',
          generatedAt: img.created_at,
          id: img.id
        };
      });
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
    sceneDescription: any,
    options: ImageGenerationOptions
  ) => {
    setGeneratingScenes(prev => new Set(prev).add(sceneNumber));
    
    try {
      // Create initial scene image entry
      const tempImage: SceneImage = {
        sceneNumber,
        imageUrl: '',
        prompt: sceneDescription.visual_description || '',
        characters: sceneDescription.characters || [],
        generationStatus: 'generating'
      };
      
      setSceneImages(prev => ({ ...prev, [sceneNumber]: tempImage }));

      const result = await userService.generateSceneImage(
        chapterId,
        sceneNumber,
        {
          scene_description: sceneDescription,
          options
        }
      );

      // Update with generated image
      setSceneImages(prev => ({
        ...prev,
        [sceneNumber]: {
          ...tempImage,
          imageUrl: result.image_url,
          generationStatus: 'completed',
          generatedAt: new Date().toISOString(),
          id: result.image_id
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

      const result = await userService.generateCharacterImage(
        chapterId,
        {
          character_name: characterName,
          description: characterDescription,
          options
        }
      );

      setCharacterImages(prev => ({
        ...prev,
        [characterName]: {
          ...tempImage,
          imageUrl: result.image_url,
          generationStatus: 'completed',
          generatedAt: new Date().toISOString(),
          id: result.image_id
        }
      }));

      toast.success(`Generated image for ${characterName}`);
      
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
        // Find scene description from script (you'll need to pass this data)
        await generateSceneImage(identifier as number, {
          visual_description: sceneImage.prompt,
          characters: sceneImage.characters
        }, options);
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
        await generateSceneImage(scene.scene_number, scene, options);
        // Add small delay between generations to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
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