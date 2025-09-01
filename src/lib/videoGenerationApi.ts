import { apiClient } from './api';

// Types for API responses
export interface VideoGeneration {
  id: string;
  script_id: string;
  user_id: string;
  quality_tier: 'free' | 'premium' | 'professional';
  generation_status: GenerationStatus;
  video_url?: string;
  created_at: string;
  audio_files?: AudioFiles;
  image_data?: ImageData;
  video_data?: VideoData;
  merge_data?: MergeData;
  lipsync_data?: LipSyncData;
  error_message?: string;
  audio_progress?: AudioProgress;
  image_progress?: ImageProgress;
  video_progress?: VideoProgress;
  merge_progress?: MergeProgress;
  lipsync_progress?: LipSyncProgress;
  character_images?: any[];
  scene_videos?: any[];
}

export type GenerationStatus = 
  | 'generating_audio' 
  | 'audio_completed' 
  | 'generating_images' 
  | 'images_completed' 
  | 'generating_video' 
  | 'video_completed' 
  | 'merging_audio' 
  | 'applying_lipsync' 
  | 'lipsync_completed'
  | 'completed' 
  | 'failed'
  | 'lipsync_failed';

export interface AudioProgress {
  narrator_files: number;
  character_files: number;
  sound_effects: number;
  background_music: number;
}

export interface ImageProgress {
  total_characters: number;
  characters_completed: number;
  total_scenes: number;
  scenes_completed: number;
  total_images_generated: number;
  success_rate: number;
}

export interface VideoProgress {
  total_scenes: number;
  scenes_completed: number;
  total_videos_generated: number;
  successful_videos: number;
  failed_videos: number;
  success_rate: number;
}

export interface MergeProgress {
  total_scenes_merged: number;
  total_duration: number;
  audio_tracks_mixed: number;
  file_size_mb: number;
  processing_time: number;
  sync_accuracy: string;
}

export interface LipSyncProgress {
  characters_lip_synced: number;
  scenes_processed: number;
  processing_method: string;
  total_scenes_processed: number;
  scenes_with_lipsync: number;
}

export interface GenerationError {
  step: string;
  message: string;
  timestamp: string;
  details?: any;
}

export interface AudioFiles {
  narrator: any[];
  characters: any[];
  sound_effects: any[];
  background_music: any[];
}

export interface ImageData {
  character_images: any[];
  scene_images: any[];
  statistics: ImageProgress;
}

export interface VideoData {
  scene_videos: any[];
  statistics: VideoProgress;
}

export interface MergeData {
  final_video_url: string;
  merge_statistics: MergeProgress;
  processing_details: any;
  quality_versions: any[];
}

export interface LipSyncData {
  lip_synced_scenes: any[];
  statistics: LipSyncProgress;
}

export interface StartVideoGenerationRequest {
  script_id: string;
  quality_tier: 'free' | 'premium' | 'professional';
}

export interface StartVideoGenerationResponse {
  video_generation_id: string;
  message: string;
  status: string;
}

// Video Generation API class using existing apiClient
class VideoGenerationAPI {
  /**
   * Start video generation for a script
   */
  async startVideoGeneration(
    scriptId: string, 
    qualityTier: 'free' | 'premium' | 'professional'
  ): Promise<StartVideoGenerationResponse> {
    return apiClient.post<StartVideoGenerationResponse>('/ai/generate-video', {
      script_id: scriptId,
      quality_tier: qualityTier
    });
  }

  /**
   * Get overall generation status and progress
   */
  async getGenerationStatus(videoGenId: string): Promise<VideoGeneration> {
    return apiClient.get<VideoGeneration>(`/ai/video-generation-status/${videoGenId}`);
  }

  /**
   * Get detailed audio generation progress
   */
  async getAudioProgress(videoGenId: string): Promise<{
    video_generation_id: string;
    audio_progress: AudioProgress;
    audio_files?: AudioFiles;
    status: GenerationStatus;
  }> {
    const response = await this.getGenerationStatus(videoGenId);
    return {
      video_generation_id: videoGenId,
      audio_progress: response.audio_progress || {
        narrator_files: 0,
        character_files: 0,
        sound_effects: 0,
        background_music: 0
      },
      audio_files: response.audio_files,
      status: response.generation_status
    };
  }

  /**
   * Get detailed image generation progress
   */
  async getImageProgress(videoGenId: string): Promise<{
    video_generation_id: string;
    image_progress: ImageProgress;
    character_images?: any[];
    status: GenerationStatus;
  }> {
    const response = await this.getGenerationStatus(videoGenId);
    return {
      video_generation_id: videoGenId,
      image_progress: response.image_progress || {
        total_characters: 0,
        characters_completed: 0,
        total_scenes: 0,
        scenes_completed: 0,
        total_images_generated: 0,
        success_rate: 0
      },
      character_images: response.character_images,
      status: response.generation_status
    };
  }

  /**
   * Get detailed video generation progress
   */
  async getVideoProgress(videoGenId: string): Promise<{
    video_generation_id: string;
    video_progress: VideoProgress;
    scene_videos?: any[];
    status: GenerationStatus;
  }> {
    const response = await this.getGenerationStatus(videoGenId);
    return {
      video_generation_id: videoGenId,
      video_progress: response.video_progress || {
        total_scenes: 0,
        scenes_completed: 0,
        total_videos_generated: 0,
        successful_videos: 0,
        failed_videos: 0,
        success_rate: 0
      },
      scene_videos: response.scene_videos,
      status: response.generation_status
    };
  }

  /**
   * Get audio/video merge status
   */
  async getMergeStatus(videoGenId: string): Promise<{
    video_generation_id: string;
    merge_status: GenerationStatus;
    is_merging: boolean;
    is_completed: boolean;
    final_video_url?: string;
    merge_statistics?: MergeProgress;
    error_message?: string;
  }> {
    return apiClient.get(`/ai/merge-status/${videoGenId}`);
  }

  /**
   * Get lip sync status and progress
   */
  async getLipSyncStatus(videoGenId: string): Promise<{
    video_generation_id: string;
    lipsync_status: GenerationStatus;
    is_applying_lipsync: boolean;
    is_lipsync_completed: boolean;
    lipsync_statistics?: LipSyncProgress;
    lip_synced_scenes?: any[];
    error_message?: string;
  }> {
    return apiClient.get(`/ai/lip-sync-status/${videoGenId}`);
  }

  /**
   * Get final completed video
   */
  async getFinalVideo(videoGenId: string): Promise<{
    video_generation_id: string;
    final_video_url: string;
    status: string;
    merge_statistics: MergeProgress;
    quality_versions: any[];
    processing_details: any;
  }> {
    return apiClient.get(`/ai/final-video/${videoGenId}`);
  }

  /**
   * Get all audio files for a generation
   */
  async getAudioFiles(videoGenId: string): Promise<{
    video_generation_id: string;
    audio_files: any[];
    total_files: number;
    total_duration: number;
  }> {
    return apiClient.get(`/ai/audio-files/${videoGenId}`);
  }

  /**
   * Get character images for a generation
   */
  async getCharacterImages(videoGenId: string): Promise<{
    video_generation_id: string;
    character_images: any[];
    total_characters: number;
  }> {
    return apiClient.get(`/ai/character-images/${videoGenId}`);
  }

  /**
   * Get scene videos for a generation
   */
  async getSceneVideos(videoGenId: string): Promise<{
    video_generation_id: string;
    scene_videos: any[];
    total_scenes: number;
    total_duration: number;
  }> {
    return apiClient.get(`/ai/scene-videos/${videoGenId}`);
  }

  /**
   * Get lip synced videos
   */
  async getLipSyncedVideos(videoGenId: string): Promise<{
    video_generation_id: string;
    lip_synced_videos: any[];
    total_scenes: number;
    total_duration: number;
    characters_with_lipsync: number;
  }> {
    return apiClient.get(`/ai/lip-synced-videos/${videoGenId}`);
  }

  /**
   * Manually trigger lip sync (if needed)
   */
  async triggerLipSync(videoGenId: string): Promise<{
    message: string;
    task_id: string;
    video_generation_id: string;
    character_dialogues: number;
  }> {
    return apiClient.post(`/ai/trigger-lip-sync/${videoGenId}`, {});
  }

  /**
   * Cancel video generation (if supported)
   */
  async cancelGeneration(videoGenId: string): Promise<{
    message: string;
    video_generation_id: string;
  }> {
    return apiClient.post(`/ai/cancel-generation/${videoGenId}`, {});
  }
}

// Export singleton instance
export const videoGenerationAPI = new VideoGenerationAPI();
export default videoGenerationAPI;