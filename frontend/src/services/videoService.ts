import { apiClient } from "../lib/api";

export interface VideoScene {
  id: string;
  title: string;
  description: string;
  video_url: string;
  thumbnail_url: string;
  duration: number;
  status: string;
  chapter_id?: string;
  book_id?: string;
  book_type?: string;
  script?: string;
  characters?: string[];
  character_details?: string;
  scene_prompt?: string;
  metadata?: Record<string, unknown>;
  elevenlabs_content?: string;
  klingai_prompt?: string;
  enhanced_audio_url?: string;
  merged_video_url?: string;
  klingai_video_url?: string;
  logs?: string[];
  parsed_sections?: {
    scene_descriptions?: string[];
    narrator_dialogue?: string[];
    character_dialogue?: string[];
    narration_text?: string[];
  };
  service_inputs?: {
    elevenlabs: {
      content: string;
      content_type: string;
      character_count: number;
    };
    klingai: {
      content: string;
      content_type: string;
      character_count: number;
    };
  };
}

export interface AvatarConfig {
  avatarId: string;
  voice: string;
  background: string;
  style: string;
}

interface VideoGenerationResponse {
  id: string;
  status: "ready" | "processing" | "failed" | "timeout";
  video_url?: string;
  content_url?: string;
  tavus_url?: string;
  tavus_video_id?: string;
  duration?: number;
  error_message?: string;
  progress?: string;
}

interface VideoStatusResponse {
  id: string;
  status:
    | "ready"
    | "processing"
    | "failed"
    | "timeout"
    | "completed_no_download";
  video_url?: string;
  content_url?: string;
  tavus_url?: string;
  tavus_video_id?: string;
  duration?: number;
  error_message?: string;
  progress?: string;
  message?: string;
}

interface VideoCombineResponse {
  combined_video_url: string;
  source_videos: string[];
  status: "success";
}

interface LearningContentItem {
  id: string;
  content_type: string;
  content_url?: string;
  tavus_url?: string;
  status: string;
  duration: number;
  created_at: string;
  updated_at: string;
}

interface LearningContentResponse {
  chapter_id: string;
  content: LearningContentItem[];
}

interface AudioGenerationResponse {
  id: string;
  audio_url?: string;
  duration: number;
  status: "ready" | "processing" | "failed";
  error_message?: string;
}

export const videoService = {
  // RAG-based video generation from chapters
  generateVideoFromChapter: async (
    chapterId: string,
    videoStyle: string = "realistic",
    includeContext: boolean = true
  ): Promise<VideoScene> => {
    const response = await apiClient.post<VideoScene>(
      `/ai/generate-video-from-chapter?chapter_id=${encodeURIComponent(
        chapterId
      )}&video_style=${encodeURIComponent(
        videoStyle
      )}&include_context=${includeContext}`,
      {}
    );
    return response;
  },

  // Tutorial video generation for learning content
  generateTutorialVideo: async (
    chapterId: string,
    tutorialStyle: string = "udemy"
  ): Promise<VideoScene> => {
    const response = await apiClient.post<VideoScene>(
      `/ai/generate-tutorial-video?chapter_id=${encodeURIComponent(
        chapterId
      )}&tutorial_style=${encodeURIComponent(tutorialStyle)}`,
      {}
    );
    return response;
  },

  // Entertainment video generation for story content
  generateEntertainmentVideo: async (
    chapterId: string,
    animationStyle: string = "animated",
    scriptStyle: string = "cinematic_movie"
  ): Promise<VideoScene> => {
    const response = await apiClient.post<VideoScene>(
      `/ai/generate-entertainment-video?chapter_id=${encodeURIComponent(
        chapterId
      )}&animation_style=${encodeURIComponent(
        animationStyle
      )}&script_style=${encodeURIComponent(scriptStyle)}`,
      {}
    );
    return response;
  },

  // Get available avatars for video generation
  getAvailableAvatars: async (): Promise<AvatarConfig[]> => {
    const response = await apiClient.get<{ avatars: AvatarConfig[] }>(
      "/ai/video-avatars"
    );
    return response.avatars;
  },

  generateRealisticVideo: async (
    chapterId: string
  ): Promise<VideoGenerationResponse> => {
    // Only send required parameters for Tavus integration (chapter_id)
    try {
      const response = await apiClient.post<VideoGenerationResponse>(
        "/ai/generate-realistic-video",
        {
          chapter_id: chapterId,
        }
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  checkVideoStatus: async (contentId: string): Promise<VideoStatusResponse> => {
    try {
      const response = await apiClient.get<VideoStatusResponse>(
        `/ai/check-video-status/${contentId}`
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  combineVideos: async (videoUrls: string[]): Promise<VideoCombineResponse> => {
    try {
      const response = await apiClient.post<VideoCombineResponse>(
        "/ai/combine-videos",
        {
          video_urls: videoUrls,
        }
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  getLearningContent: async (
    chapterId: string
  ): Promise<LearningContentResponse> => {
    try {
      const response = await apiClient.get<LearningContentResponse>(
        `/ai/learning-content/${chapterId}`
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  generateAudioNarration: async (
    chapterId: string
  ): Promise<AudioGenerationResponse> => {
    try {
      const response = await apiClient.post<AudioGenerationResponse>(
        "/ai/generate-audio-narration",
        {
          chapter_id: chapterId,
        }
      );
      return response;
    } catch (error) {
      throw error;
    }
  },

  generateScriptAndScenes: async (
    chapterId: string,
    scriptStyle: string = "cinematic_movie"
  ): Promise<{
    script: string;
    scene_descriptions: string[];
    characters: string[];
    character_details: string;
    script_style: string;
  }> => {
    const response = await apiClient.post<{
      script: string;
      scene_descriptions: string[];
      characters: string[];
      character_details: string;
      script_style: string;
    }>(
      `/ai/generate-script-and-scenes?chapter_id=${encodeURIComponent(
        chapterId
      )}&script_style=${encodeURIComponent(scriptStyle)}`,
      {}
    );
    return response;
  },
};
