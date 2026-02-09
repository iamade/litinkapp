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

// Safe mapper to normalize backend status strings to our union
export const normalizeGenerationStatus = (status: string | null | undefined): GenerationStatus => {
  if (!status) return 'failed';
  
  const normalizedStatus = status.toLowerCase().trim();
  
  switch (normalizedStatus) {
    case 'generating_audio':
    case 'audio_generation':
      return 'generating_audio';
    case 'audio_completed':
    case 'audio_complete':
      return 'audio_completed';
    case 'generating_images':
    case 'image_generation':
      return 'generating_images';
    case 'images_completed':
    case 'images_complete':
      return 'images_completed';
    case 'generating_video':
    case 'video_generation':
      return 'generating_video';
    case 'video_completed':
    case 'video_complete':
      return 'video_completed';
    case 'merging_audio':
    case 'audio_merge':
      return 'merging_audio';
    case 'applying_lipsync':
    case 'lipsync':
      return 'applying_lipsync';
    case 'lipsync_completed':
    case 'lipsync_complete':
      return 'lipsync_completed';
    case 'completed':
    case 'complete':
    case 'success':
      return 'completed';
    case 'failed':
    case 'error':
    case 'lipsync_failed':
    case 'retrieval_failed':
      return 'failed';
    default:
      // Unknown values map to 'failed' for safety
      return 'failed';
  }
};

// Safe coalescing for progress data with defaults
export const safeAudioProgress = (progress: Partial<AudioProgress> | null | undefined): AudioProgress => ({
  narrator_files: progress?.narrator_files ?? 0,
  character_files: progress?.character_files ?? 0,
  sound_effects: progress?.sound_effects ?? 0,
  background_music: progress?.background_music ?? 0,
});

export const safeImageProgress = (progress: Partial<ImageProgress> | null | undefined): ImageProgress => ({
  total_characters: progress?.total_characters ?? 0,
  characters_completed: progress?.characters_completed ?? 0,
  total_scenes: progress?.total_scenes ?? 0,
  scenes_completed: progress?.scenes_completed ?? 0,
  total_images_generated: progress?.total_images_generated ?? 0,
  success_rate: progress?.success_rate ?? 0,
});

export const safeVideoProgress = (progress: Partial<VideoProgress> | null | undefined): VideoProgress => ({
  total_scenes: progress?.total_scenes ?? 0,
  scenes_completed: progress?.scenes_completed ?? 0,
  total_videos_generated: progress?.total_videos_generated ?? 0,
  successful_videos: progress?.successful_videos ?? 0,
  failed_videos: progress?.failed_videos ?? 0,
  success_rate: progress?.success_rate ?? 0,
});

export const safeMergeProgress = (progress: Partial<MergeProgress> | null | undefined): MergeProgress => ({
  total_scenes_merged: progress?.total_scenes_merged ?? 0,
  total_duration: progress?.total_duration ?? 0,
  audio_tracks_mixed: progress?.audio_tracks_mixed ?? 0,
  file_size_mb: progress?.file_size_mb ?? 0,
  processing_time: progress?.processing_time ?? 0,
  sync_accuracy: progress?.sync_accuracy ?? 'unknown',
});

export const safeLipSyncProgress = (progress: Partial<LipSyncProgress> | null | undefined): LipSyncProgress => ({
  characters_lip_synced: progress?.characters_lip_synced ?? 0,
  scenes_processed: progress?.scenes_processed ?? 0,
  processing_method: progress?.processing_method ?? 'unknown',
  total_scenes_processed: progress?.total_scenes_processed ?? 0,
  scenes_with_lipsync: progress?.scenes_with_lipsync ?? 0,
});

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
  chapter_id: string;
  quality_tier: 'free' | 'premium' | 'professional';
  selected_shot_ids?: string[];  // Optional: only generate for these specific shots
  selected_audio_ids?: string[]; // Optional: only use these audio files
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
     chapterId: string,
     qualityTier: 'free' | 'premium' | 'professional',
     selectedShotIds?: string[],
     selectedAudioIds?: string[]
   ): Promise<StartVideoGenerationResponse> {
     const payload: StartVideoGenerationRequest = {
       script_id: scriptId,
       chapter_id: chapterId,
       quality_tier: qualityTier,
     };
     
     // Only include selected_shot_ids if shots are selected
     if (selectedShotIds && selectedShotIds.length > 0) {
       payload.selected_shot_ids = selectedShotIds;
     }
     
     // Only include selected_audio_ids if audio files are selected
     if (selectedAudioIds && selectedAudioIds.length > 0) {
       payload.selected_audio_ids = selectedAudioIds;
     }
     
     return apiClient.post<StartVideoGenerationResponse>('/ai/generate-entertainment-video', payload);
   }

  /**
   * Get overall generation status and progress with null-safe normalization
   */
  async getGenerationStatus(videoGenId: string): Promise<VideoGeneration> {
    try {
      const response = await apiClient.get<VideoGeneration>(`/ai/video-generation-status/${videoGenId}`);
      
      // Handle 204 No Content response
      if (!response) {
        throw new Error('No generation data available (204 No Content)');
      }
      
      // Normalize and coalesce the response data
      const normalized: VideoGeneration = {
        ...response,
        generation_status: normalizeGenerationStatus(response.generation_status),
        audio_progress: response.audio_progress ? safeAudioProgress(response.audio_progress) : undefined,
        image_progress: response.image_progress ? safeImageProgress(response.image_progress) : undefined,
        video_progress: response.video_progress ? safeVideoProgress(response.video_progress) : undefined,
        merge_progress: response.merge_progress ? safeMergeProgress(response.merge_progress) : undefined,
        lipsync_progress: response.lipsync_progress ? safeLipSyncProgress(response.lipsync_progress) : undefined,
        error_message: response.error_message ?? undefined,
        video_url: response.video_url ?? undefined,
      };
      
      return normalized;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get enhanced generation status with step-by-step progress
   */
  async getEnhancedGenerationStatus(videoGenId: string): Promise<{
    status: 'pending' | 'processing' | 'completed' | 'failed';
    current_step: string;
    progress_percentage: number;
    steps: {
      image_generation: { status: string; progress: number };
      audio_generation: { status: string; progress: number };
      video_generation: { status: string; progress: number };
      audio_video_merge: { status: string; progress: number };
    };
    error: string | null;
    video_url: string | null;
  }> {
    return apiClient.get(`/ai/video-generation/${videoGenId}/status`);
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
      audio_progress: safeAudioProgress(response.audio_progress),
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
      image_progress: safeImageProgress(response.image_progress),
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
      video_progress: safeVideoProgress(response.video_progress),
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

  async getChapterVideoGenerations(chapterId: string): Promise<{
    chapter_id: string;
    generations: any[];
    total: number;
  }> {
    return apiClient.get(`/ai/chapter-video-generations/${chapterId}`);
  }
}



// Export singleton instance
export const videoGenerationAPI = new VideoGenerationAPI();
export default videoGenerationAPI;