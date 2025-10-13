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
  getLearningBooksWithProgress: async () => {
    return apiClient.get("/books/learning-progress");
  },
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
    };
    return apiClient.post<ScriptResult>(`/ai/generate-script-and-scenes`, requestPayload);
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

  async generateSceneImage(
    chapterId: string,
    sceneNumber: number,
    request: SceneImageRequest
  ): Promise<ImageGenerationResponse> {
    return apiClient.post<ImageGenerationResponse>(
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

  // Audio generation methods
  async getChapterAudio(chapterId: string) {
    return apiClient.get<any>(`/chapters/${chapterId}/audio`);
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
  async generatePlotOverview(bookId: string) {
    return apiClient.post<any>(
      `/plots/books/${bookId}/generate`,
      {}
    );
  },

  // async savePlotOverview(bookId: string, plot: any) {
  //   const response = await apiClient.post<any>(`/books/${bookId}/plot/save`, plot);
  //   return response.data;
  // },

  async getPlotOverview(bookId: string) {
    const response = await apiClient.get<any>(
      `/plots/books/${bookId}/overview`
    );
    return response;
  },

  async deleteCharacter(characterId: string) {
    return apiClient.delete(`/characters/${characterId}`);
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
