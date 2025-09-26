import { apiClient } from "../lib/api";

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
}

interface GeneratedScript {
  id: string;
  script: string;
  scene_descriptions: string[];
  characters: string[];
  character_details: string;
  script_style: string;
  status: string;
  created_at: string;
  chapter_id: string;
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
  getBook: async (bookId: string) => {
    return apiClient.get(`/books/${bookId}`);
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
    scriptStyle: string = "cinematic_movie"
  ): Promise<ScriptResult> => {
    return apiClient.post<ScriptResult>(`/ai/generate-script-and-scenes`, {
      chapter_id: chapterId,
      script_style: scriptStyle,
    });
  },

  getChapterScripts: async (chapterId: string): Promise<{chapter_id: string, scripts: GeneratedScript[]}> => {
    return apiClient.get<{chapter_id: string, scripts: GeneratedScript[]}>(`/ai/scripts/${chapterId}`);
  },

  getScriptDetails: async (scriptId: string): Promise<GeneratedScript> => {
    return apiClient.get<GeneratedScript>(`/ai/script/${scriptId}`);
  },

  // Video Generation Functions
  generateEntertainmentVideo: async (
    chapterId: string,
    qualityTier: string = "basic",
    videoStyle: string = "realistic",
    scriptId?: string
  ): Promise<VideoGenerationResponse> => {
    return apiClient.post<VideoGenerationResponse>(`/ai/generate-entertainment-video`, {
      chapter_id: chapterId,
      quality_tier: qualityTier,
      video_style: videoStyle,
      script_id: scriptId,
    });
  },

  getVideoGenerationStatus: async (videoGenId: string): Promise<VideoStatus> => {
    return apiClient.get<VideoStatus>(`/ai/video-generation-status/${videoGenId}`);
  },

  // Image generation methods
   async getChapterImages(chapterId: string) {
    const response = await apiClient.get<any>(`/chapters/${chapterId}/images`);
    return response.data;
  },

  async generateSceneImage(chapterId: string, sceneNumber: number, data: any) {
    const response = await apiClient.post<any>(`/chapters/${chapterId}/images/scenes/${sceneNumber}`, data);
    return response.data;
  },

  async generateCharacterImage(chapterId: string, data: any) {
    const response = await apiClient.post<any>(`/chapters/${chapterId}/images/characters`, data);
    return response.data;
  },

  async deleteSceneImage(chapterId: string, sceneNumber: number) {
    const response = await apiClient.delete<any>(`/chapters/${chapterId}/images/scenes/${sceneNumber}`);
    return response.data;
  },

  async deleteCharacterImage(chapterId: string, characterName: string) {
    const response = await apiClient.delete<any>(`/chapters/${chapterId}/images/characters/${characterName}`);
    return response.data;
  },


// Audio generation methods
async getChapterAudio(chapterId: string) {
  const response = await apiClient.get<any>(`/chapters/${chapterId}/audio`);
  return response.data;
},

async generateSceneDialogue(chapterId: string, sceneNumber: number, data: any) {
  const response = await apiClient.post<any>(`/chapters/${chapterId}/audio/dialogue/${sceneNumber}`, data);
  return response.data;
},

async generateSceneNarration(chapterId: string, sceneNumber: number, data: any) {
  const response = await apiClient.post<any>(`/chapters/${chapterId}/audio/narration/${sceneNumber}`, data);
  return response.data;
},

async generateSceneMusic(chapterId: string, sceneNumber: number, data: any) {
  const response = await apiClient.post<any>(`/chapters/${chapterId}/audio/music/${sceneNumber}`, data);
  return response.data;
},

async generateSceneEffects(chapterId: string, sceneNumber: number, data: any) {
  const response = await apiClient.post<any>(`/chapters/${chapterId}/audio/effects/${sceneNumber}`, data);
  return response.data;
},

async generateSceneAmbiance(chapterId: string, sceneNumber: number, data: any) {
  const response = await apiClient.post<any>(`/chapters/${chapterId}/audio/ambiance/${sceneNumber}`, data);
  return response.data;
},

async deleteAudioFile(chapterId: string, audioId: string) {
  const response = await apiClient.delete<any>(`/chapters/${chapterId}/audio/${audioId}`);
  return response.data;
},

async exportAudioMix(chapterId: string, audioAssets: any) {
  const response = await apiClient.post<any>(`/chapters/${chapterId}/audio/export`, { audio_assets: audioAssets });
  return response.data;
},

// Plot and script methods (if not already present)
async generatePlotOverview(bookId: string) {
  const response = await apiClient.post<any>(`/plots/books/${bookId}/generate`, {});
  return response.data;
},

// async savePlotOverview(bookId: string, plot: any) {
//   const response = await apiClient.post<any>(`/books/${bookId}/plot/save`, plot);
//   return response.data;
// },

async getPlotOverview(bookId: string) {
  const response = await apiClient.get<any>(`/plots/books/${bookId}`);
  return response.data;
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
    status: 'idle' as const,
    metadata: {
      totalDuration: 0,
      fileSize: 0
    },
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  });
},

async createOpenShotProject(data: {
  chapterId: string;
  scenes: any[];
  editorSettings: any;
  scriptId?: string;
}) {
  // Mock implementation
  return Promise.resolve({
    project_id: `openshot-${Date.now()}`,
    status: 'created',
    message: 'OpenShot project created successfully'
  });
},

async getOpenShotProjectStatus(projectId: string) {
  // Mock implementation - simulates progress
  const progress = Math.min(100, Math.random() * 100);
  return Promise.resolve({
    project_id: projectId,
    status: progress >= 100 ? 'completed' : 'rendering',
    progress,
    videoProduction: progress >= 100 ? {
      id: `video-prod-${Date.now()}`,
      chapterId: 'mock-chapter',
      scenes: [],
      finalVideoUrl: 'https://example.com/mock-video.mp4',
      renderingProgress: 100,
      editorSettings: {
        resolution: '1080p' as const,
        fps: 30,
        aspectRatio: '16:9' as const,
        outputFormat: 'mp4' as const,
        quality: 'high' as const
      },
      status: 'completed' as const,
      metadata: {
        totalDuration: 120,
        fileSize: 50000000
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    } : null
  });
},

async processVideoWithFFmpeg(data: {
  videoUrl: string;
  quality?: string;
  [key: string]: any;
}) {
  // Mock implementation
  return Promise.resolve({
    processedUrl: 'https://example.com/processed-video.mp4',
    fileSize: 45000000,
    duration: 120,
    message: 'Video processed successfully'
  });
}


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


