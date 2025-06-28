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
  metadata?: Record<string, unknown>;
  elevenlabs_content?: string;
  klingai_prompt?: string;
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
    scriptStyle: string = "screenplay"
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
};
