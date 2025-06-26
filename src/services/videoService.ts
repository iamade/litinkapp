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
  metadata?: any;
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
      "/ai/generate-video-from-chapter",
      {
        chapter_id: chapterId,
        video_style: videoStyle,
        include_context: includeContext,
      }
    );
    return response;
  },

  // Tutorial video generation for learning content
  generateTutorialVideo: async (
    chapterId: string,
    tutorialStyle: string = "udemy"
  ): Promise<VideoScene> => {
    const response = await apiClient.post<VideoScene>(
      "/ai/generate-tutorial-video",
      {
        chapter_id: chapterId,
        tutorial_style: tutorialStyle,
      }
    );
    return response;
  },

  // Entertainment video generation for story content
  generateEntertainmentVideo: async (
    chapterId: string,
    animationStyle: string = "animated"
  ): Promise<VideoScene> => {
    const response = await apiClient.post<VideoScene>(
      "/ai/generate-entertainment-video",
      {
        chapter_id: chapterId,
        animation_style: animationStyle,
      }
    );
    return response;
  },

  // Get available avatars for video generation
  getAvailableAvatars: async (): Promise<any[]> => {
    const response = await apiClient.get<{ avatars: any[] }>(
      "/ai/video-avatars"
    );
    return response.avatars;
  },

  // Legacy methods for backward compatibility
  generateStoryScene: async (
    sceneDescription: string,
    dialogue: string,
    avatarConfig: AvatarConfig
  ): Promise<VideoScene> => {
    console.warn(
      "Using legacy generateStoryScene method. Consider using generateVideoFromChapter instead."
    );

    // For now, return a mock response
    return {
      id: `scene_${Date.now()}`,
      title: sceneDescription,
      description: "AI-generated story scene (Legacy)",
      video_url:
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
      thumbnail_url:
        "https://images.pexels.com/photos/1029621/pexels-photo-1029621.jpeg?auto=compress&cs=tinysrgb&w=400",
      duration: 180,
      status: "ready",
    };
  },

  // Mock functionality for development (fallback)
  generateVideo: async (script: string, avatarId: string): Promise<string> => {
    console.warn(
      "Video service: Using mock video URL. Use generateVideoFromChapter for RAG-based generation."
    );
    console.log(
      `Generating video for script: "${script}" with avatar: ${avatarId}`
    );
    // Simulate network delay
    await new Promise((res) => setTimeout(res, 1500));
    return "https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4";
  },
};
