import { apiClient } from "../lib/api";

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

interface VideoGenerationResult {
  video_generation_id: string;
  script_id: string;
  status: string;
  message: string;
  script_info: {
    script_style: string;
    video_style: string;
    scenes: number;
    characters: number;
  };
}

interface VideoStatus {
  status: string;
  quality_tier: string;
  video_url?: string;
  created_at: string;
  script_id?: string;
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
  ): Promise<VideoGenerationResult> => {
    return apiClient.post<VideoGenerationResult>(`/ai/generate-entertainment-video`, {
      chapter_id: chapterId,
      quality_tier: qualityTier,
      video_style: videoStyle,
      script_id: scriptId,
    });
  },

  getVideoGenerationStatus: async (videoGenId: string): Promise<VideoStatus> => {
    return apiClient.get<VideoStatus>(`/ai/video-generation-status/${videoGenId}`);
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
