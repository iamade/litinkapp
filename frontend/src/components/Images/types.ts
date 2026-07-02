
export interface SceneImage {
  sceneNumber: number;
  imageUrl: string;
  watermarkedImageUrl?: string;
  prompt: string;
  characters: string[];
  generationStatus: 'pending' | 'generating' | 'completed' | 'failed';
  generatedAt?: string;
  id?: string;
  script_id?: string;
  shot_index?: number;
}

export interface CharacterImage {
  name: string;
  imageUrl: string;
  watermarkedImageUrl?: string;
  prompt: string;
  generationStatus: 'pending' | 'generating' | 'completed' | 'failed';
  generatedAt?: string;
  id?: string;
  script_id?: string;
  entity_type?: 'character' | 'object' | 'location';
}

export interface ImageGenerationOptions {
  style: 'realistic' | 'cartoon' | 'cinematic' | 'fantasy' | 'sketch';
  quality: 'standard' | 'hd';
  aspectRatio: '16:9' | '4:3' | '1:1' | '9:16';
  useCharacterReferences: boolean;
  includeBackground: boolean;
  lightingMood: string;
  customPrompt?: string; // Added to fix lint error
}
