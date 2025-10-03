import { useState, useCallback, useRef, useEffect } from 'react';
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

export const useImageGeneration = (chapterId: string | null) => {
  const [sceneImages, setSceneImages] = useState<Record<number, SceneImage>>({});
  const [characterImages, setCharacterImages] = useState<Record<string, CharacterImage>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [generatingScenes, setGeneratingScenes] = useState<Set<number>>(new Set());
  const [generatingCharacters, setGeneratingCharacters] = useState<Set<string>>(new Set());

  const inflightRef = useRef<string | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const loadImages = useCallback(async () => {
    if (!chapterId) {
      console.warn("useImageGeneration: No chapterId; clearing images and skipping fetch");
      setSceneImages({});
      setCharacterImages({});
      setIsLoading(false);
      return;
    }

    const requestKey = chapterId;
    if (inflightRef.current === requestKey) return; // prevent duplicate fetch
    inflightRef.current = requestKey;

    setIsLoading(true);
    try {
      const response = await userService.getChapterImages(chapterId);
      if (!isMountedRef.current || inflightRef.current !== requestKey) return; // stale
      const sceneImagesMap: Record<number, SceneImage> = {};
      const characterImagesMap: Record<string, CharacterImage> = {};

      if (response.images && Array.isArray(response.images)) {
        response.images.forEach((img: { id: string; image_url?: string; metadata?: { image_type?: string; scene_number?: number; character_name?: string; image_prompt?: string }; status?: string; created_at?: string }) => {
          const metadata = img.metadata ?? {};
          const url = img.image_url ?? "";

          // Scene images: accept explicit scene or fallback when image_type missing but URL exists
          if (
            (metadata.image_type === "scene" || !metadata.image_type) &&
            (typeof metadata.scene_number === "number" || url)
          ) {
            // Use scene_number if present, else fallback to index or hash if needed
            const sceneKey =
              typeof metadata.scene_number === "number"
                ? metadata.scene_number
                : img.id || url;
            sceneImagesMap[sceneKey] = {
              sceneNumber: metadata.scene_number ?? -1,
              imageUrl: url,
              prompt: metadata.image_prompt ?? "",
              characters: [],
              generationStatus: img.status === "completed" ? "completed" : "failed",
              generatedAt: img.created_at,
              id: img.id,
            };
            return;
          }

          // Character images: keep explicit match but avoid throwing away items for missing non-critical fields
          if (metadata.image_type === "character" && metadata.character_name) {
            characterImagesMap[metadata.character_name] = {
              name: metadata.character_name,
              imageUrl: url,
              prompt: metadata.image_prompt ?? "",
              generationStatus: img.status === "completed" ? "completed" : "failed",
              generatedAt: img.created_at,
              id: img.id,
            };
            return;
          }
          // Optionally ignore other types without logging noise
        });
      }

      setSceneImages(sceneImagesMap);
      setCharacterImages(characterImagesMap);
    } catch (error: unknown) {
      if (!isMountedRef.current || inflightRef.current !== requestKey) return;
      if ((error as Error).message?.includes('404') || (error as Error).message?.includes('Not found')) {
        setSceneImages({});
        setCharacterImages({});
      } else {
        console.error('Error loading images:', error);
        toast.error('Failed to load images');
      }
    } finally {
      if (inflightRef.current === requestKey) inflightRef.current = null;
      if (isMountedRef.current) setIsLoading(false);
    }
  }, [chapterId]);

  const generateSceneImage = async (
    sceneNumber: number,
    sceneDescription: string,
    options: ImageGenerationOptions
  ) => {
    setGeneratingScenes((prev) => new Set(prev).add(sceneNumber));

    try {
      const tempImage: SceneImage = {
        sceneNumber,
        imageUrl: '',
        prompt: sceneDescription,
        characters: [],
        generationStatus: 'generating'
      };

      setSceneImages((prev) => ({ ...prev, [sceneNumber]: tempImage }));

      const request = {
        scene_description: sceneDescription,
        style: options.style,
        aspect_ratio: options.aspectRatio,
        custom_prompt: options.lightingMood ? `Lighting mood: ${options.lightingMood}` : undefined
      };

      const result = await userService.generateSceneImage(chapterId!, sceneNumber, request);

      setSceneImages((prev) => ({
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
    } catch (error: unknown) {
      console.error('Error generating scene image:', error);

      setSceneImages((prev) => ({
        ...prev,
        [sceneNumber]: {
          ...prev[sceneNumber],
          generationStatus: 'failed'
        }
      }));

      toast.error(`Failed to generate image for Scene ${sceneNumber}`);
    } finally {
      setGeneratingScenes((prev) => {
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
    setGeneratingCharacters((prev) => new Set(prev).add(characterName));

    try {
      const tempImage: CharacterImage = {
        name: characterName,
        imageUrl: '',
        prompt: characterDescription,
        generationStatus: 'generating'
      };

      setCharacterImages((prev) => ({ ...prev, [characterName]: tempImage }));

      const request = {
        character_name: characterName,
        character_description: characterDescription,
        style: options.style,
        aspect_ratio: options.aspectRatio,
        custom_prompt: options.lightingMood ? `Lighting mood: ${options.lightingMood}` : undefined
      };

      const result = await userService.generateCharacterImage(chapterId!, request);

      if (result.record_id) {
        // Commenting out pollCharacterImageStatus as it is undefined
        // pollCharacterImageStatus(characterName, result.record_id);
      } else {
        setCharacterImages((prev) => ({
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
    } catch (error: unknown) {
      console.error('Error generating character image:', error);

      setCharacterImages((prev) => ({
        ...prev,
        [characterName]: {
          ...prev[characterName],
          generationStatus: 'failed'
        }
      }));

      toast.error(`Failed to generate image for ${characterName}`);
    } finally {
      setGeneratingCharacters((prev) => {
        const newSet = new Set(prev);
        newSet.delete(characterName);
        return newSet;
      });
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
    generateCharacterImage
  };
};