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
  script_id?: string;
}

interface CharacterImage {
  name: string;
  imageUrl: string;
  prompt: string;
  generationStatus: 'pending' | 'generating' | 'completed' | 'failed';
  generatedAt?: string;
  id?: string;
  script_id?: string;
}

interface ImageGenerationOptions {
  style: 'realistic' | 'cartoon' | 'cinematic' | 'fantasy' | 'sketch';
  quality: 'standard' | 'hd';
  aspectRatio: '16:9' | '4:3' | '1:1' | '9:16';
  useCharacterReferences: boolean;
  includeBackground: boolean;
  lightingMood: string;
}

export const useImageGeneration = (chapterId: string | null, selectedScriptId: string | null) => {
  const [sceneImages, setSceneImages] = useState<Record<string | number, SceneImage>>({});
  const [characterImages, setCharacterImages] = useState<Record<string, CharacterImage>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [generatingScenes, setGeneratingScenes] = useState<Set<number>>(new Set());
  const [generatingCharacters, setGeneratingCharacters] = useState<Set<string>>(new Set());
  const [pollingIntervals, setPollingIntervals] = useState<Map<string, NodeJS.Timeout>>(new Map());

  const inflightRef = useRef<string | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    console.log('[DEBUG useImageGeneration] Component mounted, setting isMountedRef to true');
    isMountedRef.current = true;

    return () => {
      console.log('[DEBUG useImageGeneration] Component unmounting, setting isMountedRef to false');
      isMountedRef.current = false;
      // Clear all polling intervals on unmount
      pollingIntervals.forEach(interval => clearInterval(interval));
    };
  }, [pollingIntervals]);

  const loadImages = useCallback(async () => {
    console.log('[DEBUG useImageGeneration] loadImages ENTRY - chapterId:', chapterId);

    if (!chapterId) {
      console.warn("useImageGeneration: No chapterId; clearing images and skipping fetch");
      setSceneImages({});
      setCharacterImages({});
      setIsLoading(false);
      return;
    }

    console.log('[DEBUG useImageGeneration] loadImages proceeding for chapterId:', chapterId);
    const requestKey = chapterId;

    if (inflightRef.current === requestKey) {
      console.log('[DEBUG useImageGeneration] Duplicate request detected, skipping');
      return; // prevent duplicate fetch
    }

    inflightRef.current = requestKey;

    setIsLoading(true);
    try {
      console.log('[DEBUG useImageGeneration] Calling userService.getChapterImages...');
      const response = await userService.getChapterImages(chapterId);
      console.log('[DEBUG useImageGeneration] Got response:', response);
      console.log('[DEBUG useImageGeneration] Checking staleness:', {
        isMounted: isMountedRef.current,
        inflightRef: inflightRef.current,
        requestKey,
        isStale: !isMountedRef.current || inflightRef.current !== requestKey
      });
      if (!isMountedRef.current || inflightRef.current !== requestKey) {
        console.warn('[DEBUG useImageGeneration] STALE REQUEST - aborting image processing');
        return; // stale
      }
      const sceneImagesMap: Record<string | number, SceneImage> = {};
      const characterImagesMap: Record<string, CharacterImage> = {};

      if (response.images && Array.isArray(response.images)) {
        response.images.forEach((img: { id: string; image_url?: string; image_type?: string; character_name?: string; metadata?: { image_type?: string; scene_number?: number; character_name?: string; image_prompt?: string }; status?: string; created_at?: string; script_id?: string; scriptId?: string }) => {
          const metadata = img.metadata ?? {};
          const url = img.image_url ?? "";
          const imageType = img.image_type || metadata.image_type;
          const characterName = img.character_name || metadata.character_name;

          // Normalize script_id from either field
          const normalizedScriptId = img.script_id ?? img.scriptId;

          console.log('[DEBUG useImageGeneration] Processing image:', {
            id: img.id,
            imageType,
            characterName,
            hasUrl: !!url,
            scriptId: normalizedScriptId,
            selectedScriptId
          });

          // Scene images: accept explicit scene or fallback when image_type missing but URL exists
          if (
            (imageType === "scene" || !imageType) &&
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
              script_id: normalizedScriptId,
            };
            return;
          }

          // Character images: use character_name from top level or metadata
          if (imageType === "character" && characterName) {
            characterImagesMap[characterName] = {
              name: characterName,
              imageUrl: url,
              prompt: metadata.image_prompt ?? "",
              generationStatus: img.status === "completed" ? "completed" : "failed",
              generatedAt: img.created_at,
              id: img.id,
              script_id: normalizedScriptId,
            };
            return;
          }
          // Optionally ignore other types without logging noise
        });
      }

      setSceneImages(sceneImagesMap);
      setCharacterImages(characterImagesMap);
    } catch (error: unknown) {
      console.error('[DEBUG useImageGeneration] Error in loadImages:', error);
      if (!isMountedRef.current || inflightRef.current !== requestKey) return;
      if ((error as Error).message?.includes('404') || (error as Error).message?.includes('Not found')) {
        console.log('[DEBUG useImageGeneration] 404 error, clearing images');
        setSceneImages({});
        setCharacterImages({});
      } else {
        console.error('[DEBUG useImageGeneration] Unexpected error loading images:', error);
        toast.error('Failed to load images');
      }
    } finally {
      console.log('[DEBUG useImageGeneration] loadImages FINALLY block');
      if (inflightRef.current === requestKey) inflightRef.current = null;
      if (isMountedRef.current) setIsLoading(false);
    }
  }, [chapterId, selectedScriptId]);

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
        custom_prompt: options.lightingMood ? `Lighting mood: ${options.lightingMood}` : undefined,
        script_id: selectedScriptId ?? undefined
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
        custom_prompt: options.lightingMood ? `Lighting mood: ${options.lightingMood}` : undefined,
        script_id: selectedScriptId ?? undefined
      };

      const result = await userService.generateCharacterImage(chapterId!, request);

      if (result.record_id) {
        // Start polling for this character's image status
        startPollingCharacterImage(characterName, result.record_id);
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

  const regenerateImage = async (
    type: 'scene' | 'character',
    identifier: number | string,
    options: ImageGenerationOptions
  ) => {
    if (type === 'scene' && typeof identifier === 'number') {
      const existingImage = sceneImages[identifier];
      if (existingImage) {
        await generateSceneImage(identifier, existingImage.prompt, options);
      }
    } else if (type === 'character' && typeof identifier === 'string') {
      const existingImage = characterImages[identifier];
      if (existingImage) {
        await generateCharacterImage(identifier, existingImage.prompt, options);
      }
    }
  };

  const deleteImage = async (type: 'scene' | 'character', identifier: number | string) => {
    // TODO: Implement actual deletion via API
    if (type === 'scene' && typeof identifier === 'number') {
      setSceneImages(prev => {
        const updated = { ...prev };
        delete updated[identifier];
        return updated;
      });
    } else if (type === 'character' && typeof identifier === 'string') {
      setCharacterImages(prev => {
        const updated = { ...prev };
        delete updated[identifier];
        return updated;
      });
    }
  };

  const generateAllSceneImages = async (
    scenes: Array<{ scene_number?: number; visual_description?: string; description?: string }>,
    options: ImageGenerationOptions
  ) => {
    for (const [idx, scene] of scenes.entries()) {
      const sceneNumber = scene.scene_number || idx + 1;
      const description = scene.visual_description || scene.description || '';
      if (description) {
        await generateSceneImage(sceneNumber, description, options);
      }
    }
  };

  const generateAllCharacterImages = async (
    characters: string[],
    characterDetails: Record<string, string>,
    options: ImageGenerationOptions
  ) => {
    // Queue all character image generations without awaiting
    const promises = characters.map(async (character) => {
      const description = characterDetails[character] || `Portrait of ${character}, detailed character design`;
      await generateCharacterImage(character, description, options);
    });

    // Don't await - let them generate in parallel and poll individually
    Promise.all(promises).catch(err => {
      console.error('Error in batch character generation:', err);
    });
  };

  const startPollingCharacterImage = (characterName: string, recordId: string) => {
    if (!chapterId) return;

    const pollInterval = setInterval(async () => {
      try {
        const status = await userService.getImageGenerationStatus(chapterId, recordId);

        if (status.status === 'completed' && status.image_url) {
          // Update character image with completed data
          setCharacterImages((prev) => ({
            ...prev,
            [characterName]: {
              name: characterName,
              imageUrl: status.image_url!,
              prompt: status.prompt || '',
              generationStatus: 'completed',
              generatedAt: new Date().toISOString(),
              id: recordId,
              script_id: status.script_id ?? selectedScriptId ?? undefined
            }
          }));

          // Remove from generating set
          setGeneratingCharacters((prev) => {
            const newSet = new Set(prev);
            newSet.delete(characterName);
            return newSet;
          });

          // Clear this interval
          clearInterval(pollInterval);
          setPollingIntervals(prev => {
            const newMap = new Map(prev);
            newMap.delete(recordId);
            return newMap;
          });

          // Reload all images from database to get the complete data
          loadImages();

          toast.success(`Generated image for ${characterName}`);
        } else if (status.status === 'failed') {
          // Update as failed
          setCharacterImages((prev) => ({
            ...prev,
            [characterName]: {
              ...prev[characterName],
              generationStatus: 'failed'
            }
          }));

          // Remove from generating set
          setGeneratingCharacters((prev) => {
            const newSet = new Set(prev);
            newSet.delete(characterName);
            return newSet;
          });

          // Clear this interval
          clearInterval(pollInterval);
          setPollingIntervals(prev => {
            const newMap = new Map(prev);
            newMap.delete(recordId);
            return newMap;
          });

          toast.error(`Failed to generate image for ${characterName}`);
        }
        // If status is still 'pending' or 'processing', keep polling
      } catch (error) {
        console.error(`Error polling status for ${characterName}:`, error);
      }
    }, 3000); // Poll every 3 seconds

    // Store the interval so we can clear it later
    setPollingIntervals(prev => new Map(prev).set(recordId, pollInterval));

    // Set a timeout to stop polling after 5 minutes
    setTimeout(() => {
      clearInterval(pollInterval);
      setPollingIntervals(prev => {
        const newMap = new Map(prev);
        newMap.delete(recordId);
        return newMap;
      });

      // Check if still generating and mark as failed
      setGeneratingCharacters((prev) => {
        if (prev.has(characterName)) {
          setCharacterImages((prevImages) => ({
            ...prevImages,
            [characterName]: {
              ...prevImages[characterName],
              generationStatus: 'failed'
            }
          }));
          toast.error(`Image generation timeout for ${characterName}`);

          const newSet = new Set(prev);
          newSet.delete(characterName);
          return newSet;
        }
        return prev;
      });
    }, 300000); // 5 minutes timeout
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