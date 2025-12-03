// src/types/merge.ts
// Comprehensive TypeScript types for merge operations

// ============================================================================
// ENUMS AND CONSTANTS
// ============================================================================

/**
 * Quality tiers for merge operations
 */
export enum MergeQualityTier {
  WEB = 'web',
  MEDIUM = 'medium',
  HIGH = 'high',
  CUSTOM = 'custom'
}

/**
 * Output format options for merge operations
 */
export enum MergeOutputFormat {
  MP4 = 'mp4',
  WEBM = 'webm',
  MOV = 'mov'
}

/**
 * Processing mode options
 */
export enum MergeProcessingMode {
  FFMPEG_ONLY = 'ffmpeg_only',
  FFMPEG_OPENSHOT = 'ffmpeg_openshot'
}

/**
 * FFmpeg video codec options
 */
export enum FFmpegVideoCodec {
  LIBX264 = 'libx264',
  LIBX265 = 'libx265',
  LIBVPX_VP9 = 'libvpx-vp9'
}

/**
 * FFmpeg audio codec options
 */
export enum FFmpegAudioCodec {
  AAC = 'aac',
  MP3 = 'mp3',
  OPUS = 'libopus'
}

/**
 * Merge operation status states
 */
export enum MergeStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

/**
 * Input source types
 */
export enum MergeInputSourceType {
  PIPELINE_OUTPUT = 'pipeline_output',
  CUSTOM_UPLOAD = 'custom_upload'
}

/**
 * File upload status
 */
export enum FileUploadStatus {
  PENDING = 'pending',
  UPLOADING = 'uploading',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

// ============================================================================
// CORE TYPES
// ============================================================================

/**
 * FFmpeg parameters for video processing
 */
export interface FFmpegParameters {
  video_codec?: FFmpegVideoCodec;
  audio_codec?: FFmpegAudioCodec;
  video_bitrate?: string;
  audio_bitrate?: string;
  resolution?: string;
  fps?: number;
  preset?: string;
  crf?: number;
  custom_filters?: string[];
}

/**
 * Input file for merge operation
 */
export interface MergeInputFile {
  url: string;
  type: 'video' | 'audio' | 'image';
  duration?: number;
  start_time?: number;
  end_time?: number;
  volume?: number;
  fade_in?: number;
  fade_out?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Input source configuration
 */
export interface MergeInputSource {
  type: MergeInputSourceType;
  video_generation_id?: string;
  files: MergeInputFile[];
  metadata?: Record<string, unknown>;
}

// ============================================================================
// REQUEST TYPES
// ============================================================================

/**
 * Parameters for starting a manual merge operation
 */
export interface MergeManualRequest {
  video_generation_id?: string;
  input_sources: MergeInputFile[];
  quality_tier: MergeQualityTier;
  output_format: MergeOutputFormat;
  ffmpeg_params?: FFmpegParameters;
  merge_name?: string;
  add_transitions?: boolean;
  normalize_audio?: boolean;
  processing_mode?: MergeProcessingMode;
}

/**
 * Parameters for generating a merge preview
 */
export interface MergePreviewRequest {
  input_sources: MergeInputFile[];
  quality_tier: MergeQualityTier;
  preview_duration?: number;
  ffmpeg_params?: FFmpegParameters;
  processing_mode?: MergeProcessingMode;
}

// ============================================================================
// RESPONSE TYPES
// ============================================================================

/**
 * Response for manual merge operation start
 */
export interface MergeManualResponse {
  merge_id: string;
  status: MergeStatus;
  message: string;
  estimated_duration?: number;
  queue_position?: number;
}

/**
 * Response for merge status check
 */
export interface MergeStatusResponse {
  merge_id: string;
  status: MergeStatus;
  progress_percentage?: number;
  current_step?: string;
  output_url?: string;
  error_message?: string;
  processing_stats?: Record<string, unknown>;
  created_at: Date;
  updated_at: Date;
  queue_position?: number;
  retry_count?: number;
  estimated_time_remaining?: number;
}

/**
 * Response for merge preview generation
 */
export interface MergePreviewResponse {
  preview_url: string;
  preview_duration: number;
  status: string;
  message: string;
  expires_at?: Date;
}

/**
 * Response for merge download
 */
export interface MergeDownloadResponse {
  download_url: string;
  file_size_bytes?: number;
  content_type: string;
  filename: string;
  expires_at?: Date;
}

// ============================================================================
// OPERATION TYPES
// ============================================================================

/**
 * Complete merge operation data
 */
export interface MergeOperation {
  id: string;
  user_id: string;
  video_generation_id?: string;
  status: MergeStatus;
  input_sources: MergeInputFile[];
  quality_tier: MergeQualityTier;
  output_format: MergeOutputFormat;
  ffmpeg_params?: FFmpegParameters;
  merge_name?: string;
  output_url?: string;
  preview_url?: string;
  error_message?: string;
  processing_stats?: Record<string, unknown>;
  created_at: Date;
  updated_at: Date;
  progress_percentage?: number;
  current_step?: string;
  queue_position?: number;
  retry_count?: number;
  estimated_completion_time?: Date;
}

/**
 * Preview operation data
 */
export interface MergePreviewOperation {
  id: string;
  status: MergeStatus;
  preview_url?: string;
  preview_duration: number;
  error_message?: string;
  created_at: Date;
  updated_at: Date;
  expires_at?: Date;
}

// ============================================================================
// PROGRESS AND STATUS TYPES
// ============================================================================

/**
 * Progress tracking information
 */
export interface MergeProgressInfo {
  merge_id: string;
  status: MergeStatus;
  progress_percentage: number;
  current_step: string;
  queue_position?: number;
  estimated_time_remaining?: number;
  processing_stats?: {
    total_scenes_merged?: number;
    total_duration?: number;
    audio_tracks_mixed?: number;
    file_size_mb?: number;
    processing_time_seconds?: number;
    sync_accuracy?: string;
    [key: string]: unknown;
  };
}

/**
 * Error information for merge operations
 */
export interface MergeError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  timestamp: Date;
  retryable?: boolean;
  suggested_action?: string;
}

/**
 * Retry information
 */
export interface MergeRetryInfo {
  attempt_count: number;
  max_attempts: number;
  last_error?: MergeError;
  next_retry_at?: Date;
  backoff_delay_ms?: number;
}

// ============================================================================
// FILE UPLOAD TYPES
// ============================================================================

/**
 * File upload metadata
 */
export interface FileUploadMetadata {
  filename: string;
  file_size_bytes: number;
  content_type: string;
  duration?: number;
  width?: number;
  height?: number;
  bitrate?: string;
  codec?: string;
  checksum?: string;
}

/**
 * File upload progress
 */
export interface FileUploadProgress {
  upload_id: string;
  status: FileUploadStatus;
  progress_percentage: number;
  bytes_uploaded: number;
  total_bytes: number;
  estimated_time_remaining?: number;
  error_message?: string;
}

/**
 * File upload result
 */
export interface FileUploadResult {
  upload_id: string;
  status: FileUploadStatus;
  url?: string;
  metadata?: FileUploadMetadata;
  error_message?: string;
  expires_at?: Date;
}

/**
 * File validation result
 */
export interface FileValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  metadata?: FileUploadMetadata;
  suggested_actions?: string[];
}

// ============================================================================
// HOOK RETURN TYPES
// ============================================================================

/**
 * Return type for useMergeOperations hook
 */
export interface UseMergeOperationsReturn {
  // Current state
  currentMerge: MergeOperation | null;
  currentPreview: MergePreviewOperation | null;
  isMerging: boolean;
  isGeneratingPreview: boolean;
  mergeProgress: number;
  mergeStatus: string;
  retryCount: number;
  queuePosition: number | null;
  lastError?: MergeError;

  // Actions
  startMerge: (params: MergeManualRequest) => Promise<string | null>;
  generatePreview: (params: MergePreviewRequest) => Promise<string | null>;
  cancelMerge: () => Promise<void>;
  downloadMergeResult: (mergeId: string) => Promise<void>;
  cleanupPreview: () => void;
  reset: () => void;

  // Utilities
  cleanup: () => void;
  getMergeStatus: (mergeId: string) => Promise<MergeStatusResponse>;
  retryMerge: (mergeId: string) => Promise<boolean>;
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

/**
 * Quality tier configuration
 */
export interface QualityTierConfig {
  id: MergeQualityTier;
  name: string;
  description: string;
  resolution: string;
  bitrate: string;
  features: string[];
  processing_time_multiplier: number;
  cost_multiplier: number;
}

/**
 * Processing mode configuration
 */
export interface ProcessingModeConfig {
  id: MergeProcessingMode;
  name: string;
  description: string;
  capabilities: string[];
  limitations: string[];
  recommended_use_case: string;
}

/**
 * Merge operation summary for UI display
 */
export interface MergeOperationSummary {
  id: string;
  name?: string;
  status: MergeStatus;
  progress_percentage: number;
  created_at: Date;
  estimated_completion?: Date;
  output_format: MergeOutputFormat;
  quality_tier: MergeQualityTier;
  input_count: number;
  total_duration?: number;
  file_size_mb?: number;
}
