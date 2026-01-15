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
  customPrompt?: string;
}

export const useImageGeneration = (
  chapterId: string | null, 
  selectedScriptId: string | null,
  scenes?: string[] // Optional: providing scenes allows for recovery of missing scene numbers
) => {
  const [sceneImages, setSceneImages] = useState<Record<string | number, SceneImage[]>>({});
  const [characterImages, setCharacterImages] = useState<Record<string, CharacterImage>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [generatingScenes, setGeneratingScenes] = useState<Set<number>>(new Set());
  const [generatingCharacters, setGeneratingCharacters] = useState<Set<string>>(new Set());
  const [pollingIntervals, setPollingIntervals] = useState<Map<string, NodeJS.Timeout>>(new Map());

  const inflightRef = useRef<string | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;
      // Clear all polling intervals on unmount
      pollingIntervals.forEach(interval => clearInterval(interval));
    };
  }, [pollingIntervals]);

  const loadImages = useCallback(async () => {

    // Allow loading if either chapterId or selectedScriptId is present
    if (!chapterId && !selectedScriptId) {
      setSceneImages({});
      setCharacterImages({});
      setIsLoading(false);
      return;
    }

    // Use scriptId as fallback request key if chapterId is missing
    const requestKey = chapterId || selectedScriptId || 'unknown';

    // Remove strict inflight check to allow re-runs when 'scenes' updates for recovery
    // if (inflightRef.current === requestKey) {
    //   return; // prevent duplicate fetch
    // }

    inflightRef.current = requestKey;

    setIsLoading(true);
    try {
      let response;
      if (chapterId) {
        response = await userService.getChapterImages(chapterId);
      } else if (selectedScriptId) {
        response = await userService.getScriptImages(selectedScriptId);
      } else {
        return; // Should be caught by earlier guard, but safe fallback
      }

      if (!isMountedRef.current) {
        return; 
      }
      const sceneImagesMap: Record<string | number, SceneImage[]> = {};
      const characterImagesMap: Record<string, CharacterImage> = {};

      if (response.images && Array.isArray(response.images)) {
        // Sort images by created_at descending (newest first) for the carousel
        const sortedImages = [...response.images].sort((a, b) => {
          const dateA = new Date(a.created_at || 0).getTime();
          const dateB = new Date(b.created_at || 0).getTime();
          return dateB - dateA;
        });

        sortedImages.forEach((img: { id: string; image_url?: string; image_type?: string; character_name?: string; scene_number?: number; scene_description?: string; image_prompt?: string; metadata?: { image_type?: string; scene_number?: number; character_name?: string; image_prompt?: string }; status?: string; created_at?: string; script_id?: string; scriptId?: string }) => {
          const metadata = img.metadata ?? {};
          const url = img.image_url ?? "";
          const imageType = img.image_type || metadata.image_type;
          const characterName = img.character_name || metadata.character_name;
          // Read scene_number from root level first, then fall back to metadata
          let sceneNumber = img.scene_number ?? metadata.scene_number;

          // Normalize script_id from either field
          const normalizedScriptId = img.script_id ?? img.scriptId;
          
          // Filter by script_id if provided
          if (selectedScriptId && normalizedScriptId && normalizedScriptId !== selectedScriptId) {
             return;
          }

          const prompt = img.image_prompt || metadata.image_prompt || "No prompt available";

          // RECOVERY LOGIC: If sceneNumber is missing but we have scenes and a description
          if ((sceneNumber === undefined || sceneNumber === null) && imageType === 'scene' && scenes && scenes.length > 0 && img.scene_description) {
            // Try to match the image's scene_description to a scene text
            const cleanDesc = img.scene_description.trim().substring(0, 50).toLowerCase();
            const matchedIndex = scenes.findIndex(s => s.toLowerCase().includes(cleanDesc) || cleanDesc.includes(s.toLowerCase().substring(0, 50)));
            
            if (matchedIndex !== -1) {
                sceneNumber = matchedIndex + 1; // 1-based index
            }
          }

          if (imageType === 'scene' && (sceneNumber || sceneNumber === 0)) {
            const sn = Number(sceneNumber);

            // Use composite key to match state structure
            const sceneKey = selectedScriptId && normalizedScriptId === selectedScriptId
                ? `${selectedScriptId}_${sn}` 
                : sn;

            if (!sceneImagesMap[sceneKey]) {
              sceneImagesMap[sceneKey] = [];
            }
            // Map database status to UI status
            let uiStatus: 'pending' | 'generating' | 'completed' | 'failed' = 'pending';
            if (img.status === 'completed') {
              uiStatus = 'completed';
            } else if (img.status === 'failed') {
              uiStatus = 'failed';
            } else if (img.status === 'in_progress' || img.status === 'processing') {
              uiStatus = 'generating';
            } else {
              uiStatus = 'pending';
            }

            sceneImagesMap[sceneKey].push({
              sceneNumber: sn,
              imageUrl: url,
              prompt: prompt,
              characters: [],
              generationStatus: uiStatus,
              generatedAt: img.created_at,
              id: img.id,
              script_id: normalizedScriptId,
            });

            characterImagesMap[characterName] = {
              name: characterName,
              imageUrl: url,
              prompt: metadata.image_prompt ?? "",
              generationStatus: uiStatus,
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
      if (!isMountedRef.current || inflightRef.current !== requestKey) return;
      if ((error as Error).message?.includes('404') || (error as Error).message?.includes('Not found')) {
        setSceneImages({});
        setCharacterImages({});
      } else {
        toast.error('Failed to load images');
      }
    } finally {
      if (inflightRef.current === requestKey) inflightRef.current = null;
      if (isMountedRef.current) setIsLoading(false);
    }
  }, [chapterId, selectedScriptId]);

  // Auto-load images when chapterId or selectedScriptId changes
  useEffect(() => {
    loadImages();
  }, [chapterId, selectedScriptId, loadImages]);

  const generateSceneImage = async (
    sceneNumber: number,
    sceneDescription: string,
    options: ImageGenerationOptions,
    characterIds?: string[],
    characterImageUrls?: string[]
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

      // Use composite key if possible to match loadImages logic
      const sceneKey = selectedScriptId 
        ? `${selectedScriptId}_${sceneNumber}` 
        : sceneNumber;

      setSceneImages((prev) => ({ 
        ...prev, 
        [sceneKey]: [tempImage, ...(prev[sceneKey] || [])]
      }));

      const request = {
        scene_description: sceneDescription,
        style: options.style,
        aspect_ratio: options.aspectRatio,
        custom_prompt: options.customPrompt 
          ? `${options.customPrompt} ${options.lightingMood ? `Lighting mood: ${options.lightingMood}` : ''}`.trim()
          : (options.lightingMood ? `Lighting mood: ${options.lightingMood}` : undefined),
        script_id: selectedScriptId ?? undefined,
        character_ids: characterIds,
        character_image_urls: characterImageUrls
      };

      const result = await userService.generateSceneImage(chapterId!, sceneNumber, request);

      if (result.record_id) {
        // Start polling for this scene's image status
        startPollingSceneImage(sceneNumber, result.record_id);
      } else {
        setSceneImages((prev) => {
            const currentImages = prev[sceneKey] || [];
            // Replace the temp generated image with the real one, or just prepend if not found?
            // Actually simpler to just map:
            const updatedImages = currentImages.map(img => 
                img.generationStatus === 'generating' && img.prompt === sceneDescription 
                    ? {
                        ...tempImage,
                        generationStatus: 'completed' as const,
                        generatedAt: new Date().toISOString(),
                        id: result.record_id,
                        script_id: selectedScriptId ?? undefined
                      }
                    : img
            );
            return {
                ...prev,
                [sceneKey]: updatedImages
            };
        });
        setGeneratingScenes((prev) => {
          const newSet = new Set(prev);
          newSet.delete(sceneNumber);
          return newSet;
        });
        toast.success(`Generated image for Scene ${sceneNumber}`);
      }
    } catch (error: unknown) {

      setSceneImages((prev) => {
          // Mark the specific temp image as failed?
          // Since we might have multiple generating, we need to be careful.
          // For now, let's mark the most recent 'generating' one as failed.
          const sceneKey = selectedScriptId ? `${selectedScriptId}_${sceneNumber}` : sceneNumber;
          const currentImages = prev[sceneKey] || [];
          const updatedImages = currentImages.map(img => 
             img.generationStatus === 'generating' && img.prompt === sceneDescription
             ? { ...img, generationStatus: 'failed' as const }
             : img
          );
           return {
            ...prev,
            [sceneKey]: updatedImages
          };
      });

      setGeneratingScenes((prev) => {
        const newSet = new Set(prev);
        newSet.delete(sceneNumber);
        return newSet;
      });

      toast.error(`Failed to generate image for Scene ${sceneNumber}`);
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
        setGeneratingCharacters((prev) => {
          const newSet = new Set(prev);
          newSet.delete(characterName);
          return newSet;
        });
        toast.success(`Generated image for ${characterName}`);
      }
    } catch (error: unknown) {

      setCharacterImages((prev) => ({
        ...prev,
        [characterName]: {
          ...prev[characterName],
          generationStatus: 'failed'
        }
      }));

      setGeneratingCharacters((prev) => {
        const newSet = new Set(prev);
        newSet.delete(characterName);
        return newSet;
      });

      toast.error(`Failed to generate image for ${characterName}`);
    }
  };

  const regenerateImage = async (
    type: 'scene' | 'character',
    identifier: number | string,
    options: ImageGenerationOptions
  ) => {
    if (type === 'scene' && typeof identifier === 'number') {
      // Try composite key first, then number
      const sceneKey = selectedScriptId ? `${selectedScriptId}_${identifier}` : identifier;
      const images = sceneImages[sceneKey] || sceneImages[identifier];
      // Use the most recent image for prompt
      const existingImage = Array.isArray(images) && images.length > 0 ? images[0] : null;
      
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

  const deleteImage = async (type: 'scene' | 'character', identifier: number | string, imageId?: string) => {
    try {
      let targetId: string | undefined = imageId;

      if (type === 'scene' && typeof identifier === 'number') {
        // Look up image ID
        const sceneKey = selectedScriptId ? `${selectedScriptId}_${identifier}` : identifier;
        const images = sceneImages[sceneKey] || sceneImages[identifier];
        
        if (!targetId && Array.isArray(images) && images.length > 0) {
            targetId = images[0].id;
        }

        if (targetId) {
          await userService.deleteImageGenerations([targetId]);
          
          setSceneImages(prev => {
            const updated = { ...prev };
            // Remove specific image from array
            const key = selectedScriptId ? `${selectedScriptId}_${identifier}` : identifier;
            if (updated[key]) {
                 updated[key] = updated[key].filter(img => img.id !== targetId);
                 if (updated[key].length === 0) {
                     delete updated[key];
                 }
            }
            // cleanup fallback key if needed? (Usually keys are consistent)
            return updated;
          });
          toast.success(`Deleted image for Scene ${identifier}`);
        }
      } else if (type === 'character' && typeof identifier === 'string') {
        const image = characterImages[identifier];
        targetId = image?.id;

        if (targetId) {
          await userService.deleteImageGenerations([targetId]);
          
          setCharacterImages(prev => {
            const updated = { ...prev };
            delete updated[identifier];
            return updated;
          });
          toast.success(`Deleted image for ${identifier}`);
        }
      }
    } catch (error) {
      console.error('Failed to delete image:', error);
      toast.error('Failed to delete image');
    }
  };

  const generateAllSceneImages = async (
    scenes: Array<{ scene_number?: number; visual_description?: string; description?: string }>,
    options: ImageGenerationOptions
  ) => {
    if (!chapterId) {
      toast.error('Chapter ID is required to generate images');
      return;
    }

    for (const [idx, scene] of scenes.entries()) {
      const sceneNumber = scene.scene_number || idx + 1;
      const description = scene.visual_description || scene.description || '';

      if (description) {
        await generateSceneImage(sceneNumber, description, options);
      } else {
      }
    }

    // Reload images from database to ensure everything is in sync
    await loadImages();
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
    Promise.all(promises).catch(() => {
    });
  };
  
  const startPollingSceneImage = (sceneNumber: number, recordId: string) => {
    if (!chapterId) return;

    const pollInterval = setInterval(async () => {
      try {
        const status = await userService.getSceneImageStatus(chapterId, sceneNumber);

        if (status.status === 'completed' && status.image_url) {
          // Update scene image with completed data
          setSceneImages((prev) => {
            const sceneKey = status.script_id ? `${status.script_id}_${sceneNumber}` : sceneNumber;
            const currentImages = prev[sceneKey] || [];
            
            const existingIndex = currentImages.findIndex(img => img.id === recordId);
            let updatedImages = [...currentImages];

            if (existingIndex >= 0) {
                 updatedImages[existingIndex] = {
                    ...updatedImages[existingIndex],
                    imageUrl: status.image_url!,
                    generationStatus: 'completed',
                    id: recordId,
                    prompt: status.prompt || ''
                 };
            } else {
                // Find first generating image
                const genIndex = updatedImages.findIndex(img => img.generationStatus === 'generating');
                if (genIndex >= 0) {
                     updatedImages[genIndex] = {
                        ...updatedImages[genIndex],
                        imageUrl: status.image_url!,
                        generationStatus: 'completed',
                        id: recordId,
                        prompt: status.prompt || ''
                     };
                } else {
                    // Just prepend
                     updatedImages = [{
                        sceneNumber,
                        imageUrl: status.image_url!,
                        prompt: status.prompt || '',
                        characters: [],
                        generationStatus: 'completed',
                        generatedAt: new Date().toISOString(),
                        id: recordId,
                        script_id: status.script_id ?? selectedScriptId ?? undefined
                     }, ...updatedImages];
                }
            }

            return {
                ...prev,
                [sceneKey]: updatedImages
            };
          });

          // Remove from generating set
          setGeneratingScenes((prev) => {
            const newSet = new Set(prev);
            newSet.delete(sceneNumber);
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

          toast.success(`Generated image for Scene ${sceneNumber}`);
        } else if (status.status === 'failed') {
          // Update as failed
          setSceneImages((prev) => {
             const sceneKey = status.script_id ? `${status.script_id}_${sceneNumber}` : sceneNumber;
             const currentImages = prev[sceneKey] || [];
             const updatedImages = currentImages.map(img => 
                // Best effort match
                (img.id === recordId || img.generationStatus === 'generating') 
                ? { ...img, generationStatus: 'failed' as const }
                : img
             );
             return { ...prev, [sceneKey]: updatedImages };
          });

          // Remove from generating set
          setGeneratingScenes((prev) => {
            const newSet = new Set(prev);
            newSet.delete(sceneNumber);
            return newSet;
          });

          // Clear this interval
          clearInterval(pollInterval);
          setPollingIntervals(prev => {
            const newMap = new Map(prev);
            newMap.delete(recordId);
            return newMap;
          });

          toast.error(`Failed to generate image for Scene ${sceneNumber}`);
        }
      } catch (error) {
           // ignore errors during polling
      }
    }, 3000); // Poll every 3 seconds

    // Store the interval
    setPollingIntervals(prev => new Map(prev).set(recordId, pollInterval));

    // Timeout
    setTimeout(() => {
      clearInterval(pollInterval);
      setPollingIntervals(prev => {
        const newMap = new Map(prev);
        newMap.delete(recordId);
        return newMap;
      });

      // Check if still generating and mark as failed
      setGeneratingScenes((prev) => {
        if (prev.has(sceneNumber)) {
          setSceneImages((prevImages: Record<string | number, SceneImage[]>) => {
              const sceneKey = selectedScriptId ? `${selectedScriptId}_${sceneNumber}` : sceneNumber;
              const currentImages = prevImages[sceneKey] || [];
               const updatedImages = currentImages.map(img => 
                (img.id === recordId || img.generationStatus === 'generating') 
                ? { ...img, generationStatus: 'failed' as const }
                : img
             );
            return {
                ...prevImages,
                [sceneKey]: updatedImages
            };
          });
          toast.error(`Image generation timeout for Scene ${sceneNumber}`);

          const newSet = new Set(prev);
          newSet.delete(sceneNumber);
          return newSet;
        }
        return prev;
      });
    }, 300000); // 5 minutes
  };

  const deleteGenerations = async (ids: string[]) => {
    try {
      await userService.deleteImageGenerations(ids);
      // Remove deleted images from local state
      setSceneImages(prev => {
        const updated = { ...prev };
        Object.keys(updated).forEach(key => {
          const images = updated[key];
          if (Array.isArray(images)) {
             updated[key] = images.filter(img => img.id && !ids.includes(img.id));
             if (updated[key].length === 0) {
                 delete updated[key];
             }
          }
        });
        return updated;
      });
      setCharacterImages(prev => {
        const updated = { ...prev };
        Object.keys(updated).forEach(key => {
          const charImage = updated[key];
          if (charImage.id && ids.includes(charImage.id)) {
            delete updated[key];
          }
        });
        return updated;
      });
      toast.success(`Deleted ${ids.length} image${ids.length > 1 ? 's' : ''}`);

      // Reload images from server to ensure consistency
      await loadImages();
    } catch (error) {
      toast.error('Failed to delete selected images');
      throw error;
    }
  };

  const deleteAllSceneGenerations = async (scriptId: string) => {
    try {
      await userService.deleteAllSceneGenerations(scriptId);
      // Remove scene images for this specific script from local state
      setSceneImages(prev => {
        const updated = { ...prev };
        Object.keys(updated).forEach(key => {
          const images = updated[key];
           if (Array.isArray(images) && images.length > 0) {
               // Check if ANY image in the group belongs to this script
               // Typically all images in a key group belong to same script/scene combo
               const normalizedScriptId = images[0].script_id ?? (images[0] as any).scriptId;
               if (normalizedScriptId === scriptId) {
                  delete updated[key];
               }
           }
        });
        return updated;
      });
      toast.success('Deleted all generated scene images for this script');

      // Reload images from server to ensure consistency
      await loadImages();
    } catch (error) {
      toast.error('Failed to delete all scene images');
      throw error;
    }
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

  const setCharacterImage = useCallback((characterName: string, imageData: CharacterImage) => {
    setCharacterImages(prev => ({
      ...prev,
      [characterName]: imageData
    }));
  }, []);

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
    deleteGenerations,
    deleteAllSceneGenerations,
    generateAllSceneImages,
    generateAllCharacterImages,
    setCharacterImage
  };
};