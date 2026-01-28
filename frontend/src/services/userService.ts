import { apiClient } from "../lib/api";

interface Book {
  id: string;
  title: string;
  author_name?: string;
  description?: string;
  cover_image_url?: string;
  book_type: string;
  difficulty?: string;
  tags?: any;
  language?: string;
  user_id: string;
  status: string;
  total_chapters?: number;
  estimated_duration?: any;
  created_at: string;
  updated_at: string;
  chapters?: any[];
}

interface VideoGenerationResponse {
  video_generation_id: string;
  script_id: string;
  status: string;
  audio_task_id?: string;
  task_status?: string;
  message: string;
  script_info: {
    script_style: string;
    video_style: string;
    scenes: number;
    characters: number;
    created_at: string;
  };
}

// Update VideoStatus interface to include task metadata
interface VideoStatus {
  generation_status: string;
  quality_tier: string;
  video_url?: string;
  created_at: string;
  script_id?: string;
  error_message?: string;
  task_metadata?: {
    audio_task_id?: string;
    audio_task_state?: string;
    started_at?: string;
  };
}

interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  role: "author" | "explorer";
  avatar_url?: string;
  bio?: string;
}

interface UserStats {
  books_read: number;
  total_time_hours: number;
  badges_earned: number;
  quizzes_taken: number;
  average_quiz_score: number;
  books_uploaded: number;
}

interface LearningContentResult {
  id: string;
  audio_url?: string;
  video_url?: string;
  duration: number;
  status: string;
}

interface ScriptResult {
  script: string;
  scene_descriptions: string[];
  characters: string[];
  character_details: string;
  script_style: string;
  script_id: string;
  script_name: string;
}

interface GeneratedScript {
  id: string;
  script_name: string;
  script: string;
  scene_descriptions: string[];
  characters: string[];
  character_details: string;
  script_style: string;
  status: string;
  created_at: string;
  chapter_id: string;
}

// Image generation interfaces
interface ChapterImagesResponse {
  chapter_id: string;
  images: ImageRecord[];
  total_count: number;
}

interface ImageRecord {
  id: string;
  user_id: string;
  image_type: string;
  scene_description?: string;
  character_name?: string;
  image_url?: string;
  thumbnail_url?: string;
  image_prompt?: string;
  status: string;
  generation_time_seconds?: number;
  width?: number;
  height?: number;
  file_size_bytes?: number;
  metadata: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

interface ImageGenerationResponse {
  record_id: string;
  image_url: string;
  prompt_used: string;
  metadata: Record<string, any>;
  generation_time?: number;
  message: string;
}

interface SceneImageRequest {
  scene_description: string;
  style?: string;
  aspect_ratio?: string;
  custom_prompt?: string;
}

interface CharacterImageRequest {
  character_name: string;
  character_description: string;
  style?: string;
  aspect_ratio?: string;
  custom_prompt?: string;
}

interface DeleteImageResponse {
  success: boolean;
  message: string;
  record_id: string;
}

interface ImageStatusResponse {
  record_id: string;
  status: string; // 'pending', 'processing', 'completed', 'failed'
  image_url?: string;
  prompt?: string;
  script_id?: string;
  error_message?: string;
  generation_time_seconds?: number;
  created_at: string;
  updated_at?: string;
}

interface AudioStatusResponse {
  record_id: string;
  status: string; // 'pending', 'processing', 'completed', 'failed'
  audio_url?: string;
  error_message?: string;
  duration?: number;
  created_at: string;
  updated_at?: string;
}

interface ImageGenerationQueuedResponse {
  task_id: string;
  status: string;
  message: string;
  estimated_time_seconds?: number;
  record_id?: string;
}

export const userService = {
  getProfile: async (): Promise<UserProfile> => {
    return apiClient.get<UserProfile>("/users/me");
  },
  updateProfile: async (data: Partial<UserProfile>) => {
    return apiClient.put<UserProfile>("/users/me", data);
  },
  getStats: async (): Promise<UserStats> => {
    return apiClient.get<UserStats>("/users/me/stats");
  },
  getMyBooks: async () => {
    return apiClient.get("/books");
  },
  retryBookProcessing: async (bookId: string) => {
    return apiClient.post(`/books/${bookId}/retry`, {});
  },
  deleteBook: async (bookId: string) => {
    return apiClient.delete(`/books/${bookId}`);
  },
  getBook: async (bookId: string): Promise<Book> => {
    return apiClient.get<Book>(`/books/${bookId}`);
  },
  getChapters: async (bookId: string) => {
    return apiClient.get(`/books/${bookId}/chapters`);
  },
  generateAudioNarration: async (
    chapterId: string
  ): Promise<LearningContentResult> => {
    return apiClient.post<LearningContentResult>(
      `/ai/generate-audio-narration`,
      {
        chapter_id: chapterId,
      }
    );
  },
  generateRealisticVideo: async (
    chapterId: string
  ): Promise<LearningContentResult> => {
    return apiClient.post<LearningContentResult>(
      `/ai/generate-realistic-video`,
      {
        chapter_id: chapterId,
      }
    );
  },
  // Get user's own learning books (not superadmin books)
  getMyLearningBooks: async () => {
    return apiClient.get("/books?book_type=learning");
  },

  // Get user's own entertainment books (not superadmin books)
  getMyEntertainmentBooks: async () => {
    return apiClient.get("/books?book_type=entertainment");
  },

  getLearningBooksWithProgress: async () => {
    return apiClient.get("/books/learning-progress");
  },

  // These are for the Explore page - superadmin curated content
  getSuperadminLearningBooks: async () => {
    return apiClient.get("/books/superadmin-learning-books");
  },
  getSuperadminEntertainmentBooks: async () => {
    return apiClient.get("/books/superadmin-entertainment-books");
  },

  // Script Generation Functions
  generateScriptAndScenes: async (
    chapterId: string,
    scriptStyle: string = "cinematic_movie",
    options?: {
      includeCharacterProfiles?: boolean;
      targetDuration?: number | "auto";
      sceneCount?: number;
      focusAreas?: string[];
      scriptStoryType?: string;
      customLogline?: string;
    }
  ): Promise<ScriptResult> => {
    const requestPayload = {
      chapter_id: chapterId,
      script_style: scriptStyle,
      target_duration: options?.targetDuration,
      include_character_profiles: options?.includeCharacterProfiles,
      scene_count: options?.sceneCount,
      focus_areas: options?.focusAreas,
      scriptStoryType: options?.scriptStoryType,
      custom_logline: options?.customLogline,
    };
    return apiClient.post<ScriptResult>(`/ai/generate-script-and-scenes`, requestPayload);
  },

  updatePlotOverview: async (
    plotId: string,
    updates: { logline?: string; [key: string]: any }
  ) => {
    return apiClient.put(`/plots/${plotId}`, updates);
  },

  getChapterScripts: async (
    chapterId: string
  ): Promise<{ chapter_id: string; scripts: GeneratedScript[] }> => {
    return apiClient.get<{ chapter_id: string; scripts: GeneratedScript[] }>(
      `/ai/scripts/${chapterId}`
    );
  },

  getScriptDetails: async (scriptId: string): Promise<GeneratedScript> => {
    return apiClient.get<GeneratedScript>(`/ai/script/${scriptId}`);
  },

  deleteScript: async (scriptId: string) => {
    return apiClient.delete(`/ai/delete-script/${scriptId}`);
  },

  updateScript: async (scriptId: string, updates: Partial<GeneratedScript>) => {
    return apiClient.patch<GeneratedScript>(`/ai/script/${scriptId}`, updates);
  },

  // Video Generation Functions
  generateEntertainmentVideo: async (
    chapterId: string,
    qualityTier: string = "basic",
    videoStyle: string = "realistic",
    scriptId?: string
  ): Promise<VideoGenerationResponse> => {
    return apiClient.post<VideoGenerationResponse>(
      `/ai/generate-entertainment-video`,
      {
        chapter_id: chapterId,
        quality_tier: qualityTier,
        video_style: videoStyle,
        script_id: scriptId,
      }
    );
  },

  getVideoGenerationStatus: async (
    videoGenId: string
  ): Promise<VideoStatus> => {
    return apiClient.get<VideoStatus>(
      `/ai/video-generation-status/${videoGenId}`
    );
  },

  // Image generation methods
  async getChapterImages(chapterId: string): Promise<ChapterImagesResponse> {
    return apiClient.get<ChapterImagesResponse>(
      `/chapters/${chapterId}/images`
    );
  },

  async getScriptImages(scriptId: string): Promise<ChapterImagesResponse> {
    return apiClient.get<ChapterImagesResponse>(
      `/ai/script/${scriptId}/images`
    );
  },

  async generateSceneImage(
    chapterId: string,
    sceneNumber: number,
    request: SceneImageRequest
  ): Promise<ImageGenerationQueuedResponse> {
    return apiClient.post<ImageGenerationQueuedResponse>(
      `/chapters/${chapterId}/images/scenes/${sceneNumber}`,
      request
    );
  },

  async generateCharacterImage(
    chapterId: string,
    request: CharacterImageRequest
  ): Promise<ImageGenerationQueuedResponse> {
    return apiClient.post<ImageGenerationQueuedResponse>(
      `/chapters/${chapterId}/images/characters`,
      request
    );
  },

  async linkCharacterImage(
    chapterId: string,
    request: {
      character_name: string;
      image_url: string;
      script_id?: string;
      prompt?: string;
    }
  ): Promise<{ success: boolean; record_id: string; message: string }> {
    return apiClient.post(
      `/chapters/${chapterId}/images/characters/link`,
      request
    );
  },

  // Create a placeholder character in plot overview (for books)
  async createPlotCharacter(
    bookId: string,
    characterName: string,
    entityType: 'character' | 'object' | 'location' = 'character'
  ): Promise<{
    id: string;
    name: string;
    role?: string;
    physical_description?: string;
    personality?: string;
    image_url?: string;
    entity_type?: string;
    message: string;
  }> {
    return apiClient.post(
      `/plots/books/${bookId}/characters?character_name=${encodeURIComponent(characterName)}&entity_type=${entityType}`,
      {}
    );
  },

  // Create a placeholder character in project plot overview (for Creator mode)
  async createProjectCharacter(
    projectId: string,
    characterName: string,
    entityType: 'character' | 'object' | 'location' = 'character'
  ): Promise<{
    id: string;
    name: string;
    role?: string;
    physical_description?: string;
    personality?: string;
    image_url?: string;
    entity_type?: string;
    message: string;
  }> {
    return apiClient.post(
      `/plots/projects/${projectId}/characters?character_name=${encodeURIComponent(characterName)}&entity_type=${entityType}`,
      {}
    );
  },

  async deleteSceneImage(
    chapterId: string,
    sceneNumber: number
  ): Promise<DeleteImageResponse> {
    return apiClient.delete<DeleteImageResponse>(
      `/chapters/${chapterId}/images/scenes/${sceneNumber}`
    );
  },

  async deleteCharacterImage(
    chapterId: string,
    characterName: string
  ): Promise<DeleteImageResponse> {
    return apiClient.delete<DeleteImageResponse>(
      `/chapters/${chapterId}/images/characters/${characterName}`
    );
  },

  async getImageGenerationStatus(
    chapterId: string,
    recordId: string
  ): Promise<ImageStatusResponse> {
    return apiClient.get<ImageStatusResponse>(
      `/chapters/${chapterId}/images/status/${recordId}`
    );
  },

  async getSceneImageStatus(
    chapterId: string,
    sceneNumber: number
  ): Promise<ImageStatusResponse> {
    return apiClient.get<ImageStatusResponse>(
      `/chapters/${chapterId}/images/scenes/${sceneNumber}/status`
    );
  },

  async deleteImageGenerations(ids: string[]): Promise<{ success: boolean; message: string }> {
    return apiClient.post<{ success: boolean; message: string }>(
      `/image-generations/delete`,
      { ids }
    );
  },

  async deleteAllSceneGenerations(scriptId: string): Promise<{ success: boolean; message: string }> {
    return apiClient.post<{ success: boolean; message: string }>(
      `/image-generations/delete-all`,
      { script_id: scriptId }
    );
  },

  // Audio generation methods
  async getChapterAudio(chapterId: string, scriptId?: string) {
    const params = scriptId ? `?script_id=${scriptId}` : '';
    return apiClient.get<any>(`/chapters/${chapterId}/audio${params}`);
  },

  async generateSceneDialogue(
    chapterId: string,
    sceneNumber: number,
    data: any
  ) {
    try {
      const response = await apiClient.post<any>(
        `/chapters/${chapterId}/audio/dialogue/${sceneNumber}`,
        data
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  async generateSceneNarration(
    chapterId: string,
    sceneNumber: number,
    data: any
  ) {
    try {
      const response = await apiClient.post<any>(
        `/chapters/${chapterId}/audio/narrator/${sceneNumber}`,
        data
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  async generateSceneMusic(chapterId: string, sceneNumber: number, data: any) {
    try {
      const response = await apiClient.post<any>(
        `/chapters/${chapterId}/audio/music/${sceneNumber}`,
        data
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  async generateSceneEffects(
    chapterId: string,
    sceneNumber: number,
    data: any
  ) {
    try {
      const response = await apiClient.post<any>(
        `/chapters/${chapterId}/audio/sound_effect/${sceneNumber}`,
        data
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  async generateSceneAmbiance(
    chapterId: string,
    sceneNumber: number,
    data: any
  ) {
    try {
      const response = await apiClient.post<any>(
        `/chapters/${chapterId}/audio/background_music/${sceneNumber}`,
        data
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  async deleteAudioFile(chapterId: string, audioId: string) {
    return apiClient.delete<any>(
      `/chapters/${chapterId}/audio/${audioId}`
    );
  },

  async exportAudioMix(chapterId: string, audioAssets: any) {
    return apiClient.post<any>(
      `/chapters/${chapterId}/audio/export`,
      { audio_assets: audioAssets }
    );
  },

  async getAudioGenerationStatus(
    chapterId: string,
    recordId: string
  ): Promise<AudioStatusResponse> {
    return apiClient.get<AudioStatusResponse>(
      `/chapters/${chapterId}/audio/status/${recordId}`
    );
  },

  // Plot and script methods (if not already present)
  async generatePlotOverview(bookId: string, options?: {
    refinementPrompt?: string;
    storyType?: string;
    genre?: string;
    tone?: string;
    audience?: string;
  }) {
    return apiClient.post<any>(
      `/plots/books/${bookId}/generate`,
      {
        refinement_prompt: options?.refinementPrompt,
        story_type: options?.storyType,
        genre: options?.genre,
        tone: options?.tone,
        audience: options?.audience,
      }
    );
  },

  // Project plot generation (for prompt-only projects)
  async generateProjectPlotOverview(projectId: string, inputPrompt: string, options?: {
    projectType?: string;
    storyType?: string;
    genre?: string;
    tone?: string;
    audience?: string;
    refinementPrompt?: string;
  }) {
    return apiClient.post<any>(
      `/plots/projects/${projectId}/generate`,
      {
        input_prompt: inputPrompt,
        project_type: options?.projectType,
        story_type: options?.storyType,
        genre: options?.genre,
        tone: options?.tone,
        audience: options?.audience,
        refinement_prompt: options?.refinementPrompt,
      }
    );
  },

  async getPlotOverview(bookId: string) {
    const response = await apiClient.get<any>(
      `/plots/books/${bookId}/overview`
    );
    return response;
  },

  // Auto-add more characters to an existing plot (without replacing existing ones)
  async autoAddCharacters(bookId: string): Promise<{
    message: string;
    characters_added: number;
    total_characters: number;
    new_characters?: Array<{
      id: string;
      name: string;
      role: string;
      physical_description: string;
      personality: string;
    }>;
  }> {
    return apiClient.post(
      `/plots/books/${bookId}/auto-add-characters`,
      {}
    );
  },

  // Auto-add more characters to an existing project plot (for Creator mode)
  async autoAddProjectCharacters(projectId: string): Promise<{
    message: string;
    characters_added: number;
    total_characters: number;
    new_characters?: Array<{
      id: string;
      name: string;
      role: string;
      physical_description: string;
      personality: string;
    }>;
  }> {
    return apiClient.post(
      `/plots/projects/${projectId}/auto-add-characters`,
      {}
    );
  },

  // Get project plot overview (uses project-specific endpoint)
  async getProjectPlotOverview(projectId: string) {
    const response = await apiClient.get<any>(
      `/plots/projects/${projectId}/overview`
    );
    return response;
  },

  async deleteCharacter(characterId: string) {
    return apiClient.delete(`/characters/${characterId}`);
  },

  async bulkDeleteCharacters(characterIds: string[]) {
    return apiClient.post(`/characters/bulk-delete`, characterIds);
  },

  async createCharacter(plotOverviewId: string, characterData: {
    name: string;
    role?: string;
    physical_description?: string;
    personality?: string;
    character_arc?: string;
    archetypes?: string[];
    want?: string;
    need?: string;
    lie?: string;
    ghost?: string;
  }) {
    return apiClient.post(`/characters/plot/${plotOverviewId}`, {
      ...characterData,
      plot_overview_id: plotOverviewId,
      book_id: '', // Will be filled by backend
      user_id: '', // Will be filled by backend
    });
  },

  async updateCharacter(characterId: string, updates: {
    name?: string;
    role?: string;
    physical_description?: string;
    personality?: string;
    character_arc?: string;
    archetypes?: string[];
  }) {
    return apiClient.put(`/characters/${characterId}`, updates);
  },

  async generateCharacterImageGlobal(characterId: string, customPrompt?: string) {
    return apiClient.post(`/characters/${characterId}/generate-image`, {
      prompt: customPrompt,
      character_id: characterId,
      user_id: '' // Will be set by backend from auth token
    });
  },

  async getCharacterImageStatus(characterId: string): Promise<{
    character_id: string;
    status: string;
    task_id?: string;
    image_url?: string;
    metadata?: any;
    error?: string;
  }> {
    return apiClient.get(`/characters/${characterId}/image-status`);
  },

  async setDefaultCharacterImage(characterId: string, imageUrl: string) {
    return apiClient.put(`/characters/${characterId}/image/default`, { image_url: imageUrl });
  },

  async deleteCharacterHistoryImage(characterId: string, imageId: string) {
    return apiClient.delete<{ success: boolean; message: string }>(`/characters/${characterId}/image/${imageId}`);
  },

  async generateCharacterDetailsWithAI(
    characterName: string,
    bookId: string,
    role?: string
  ): Promise<{
    success: boolean;
    character_details: {
      name: string;
      role: string;
      physical_description: string;
      personality: string;
      character_arc: string;
      want: string;
      need: string;
      lie: string;
      ghost: string;
    };
    message: string;
  }> {
    const params = new URLSearchParams({
      character_name: characterName,
      book_id: bookId,
    });

    if (role) {
      params.append('role', role);
    }

    return apiClient.post(`/characters/generate-details?${params.toString()}`, null);
  },

  // Add these methods to userService.ts

  async getVideoProduction(chapterId: string) {
    // Mock implementation - returns null for new productions
    return Promise.resolve(null);
  },

  async saveVideoProduction(data: {
    chapterId: string;
    scenes: any[];
    editorSettings: any;
    scriptId?: string;
  }) {
    // Mock implementation
    return Promise.resolve({
      id: `video-prod-${Date.now()}`,
      chapterId: data.chapterId,
      scenes: data.scenes || [],
      finalVideoUrl: null,
      renderingProgress: 0,
      editorSettings: data.editorSettings,
      status: "idle" as const,
      metadata: {
        totalDuration: 0,
        fileSize: 0,
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      scriptId: data.scriptId,
    });
  },

  // AI Assist - Enhance scene prompt for image generation
  enhanceScenePrompt: async (request: {
    scene_description: string;
    scene_context?: string;
    characters_in_scene?: string[];
    shot_type?: string;
    style?: string;
  }): Promise<{
    original_description: string;
    enhanced_description: string;
    detected_shot_type: string | null;
    suggested_shot_types: string[];
    enhancement_notes: string | null;
  }> => {
    return apiClient.post("/ai/enhance-scene-prompt", {
      scene_description: request.scene_description,
      scene_context: request.scene_context,
      characters_in_scene: request.characters_in_scene,
      shot_type: request.shot_type,
      style: request.style || "cinematic",
    });
  },

  // Script Expansion - AI-powered story content expansion
  expandScript: async (request: {
    content: string;
    expansion_prompt?: string;
    target_length_increase?: number;
    focus_areas?: string[];
    artifact_id?: string;
    script_id?: string;
  }): Promise<{
    expanded_content: string;
    original_length: number;
    expanded_length: number;
    expansion_ratio: number;
    saved: boolean;
    message: string;
  }> => {
    return apiClient.post("/ai/expand-script", request);
  },

};

export async function deleteBook(bookId: string) {
  const response = await fetch(`/api/v1/books/${bookId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error("Failed to delete book");
  }
  return await response.json();
}
