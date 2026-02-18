// src/types/videoProduction.ts
export interface VideoScene {
  id: string;
  sceneNumber: number;
  shotType?: 'key_scene' | 'suggested_shot'; // Shot type from storyboard
  shotIndex?: number; // Shot index within scene
  imageUrl: string;
  video_url?: string;
  audioFiles: string[];
  duration: number;
  transitions: Transition[];
  thumbnailUrl?: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
}

export interface Transition {
  type: 'fade' | 'dissolve' | 'wipe' | 'slide' | 'zoom' | 'none';
  duration: number;
  easing?: 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';
}

export interface EditorSettings {
  resolution: '720p' | '1080p' | '4k';
  fps: 24 | 30 | 60;
  aspectRatio: '16:9' | '4:3' | '1:1' | '9:16';
  outputFormat: 'mp4' | 'webm' | 'mov';
  quality: 'low' | 'medium' | 'high' | 'ultra';
  watermark?: {
    enabled: boolean;
    text?: string;
    imageUrl?: string;
    position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
  };
}

export interface VideoProduction {
  id: string;
  chapterId: string;
  scenes: VideoScene[];
  finalVideoUrl?: string | null;
  renderingProgress: number;
  editorSettings: EditorSettings;
  status: 'idle' | 'rendering' | 'processing' | 'completed' | 'error';
  createdAt: string;
  updatedAt: string;
  metadata?: {
    totalDuration: number;
    fileSize?: number;
    exportedAt?: string;
  };
  scriptId?: string;
}

export interface OpenShotProject {
  id: string;
  name: string;
  width: number;
  height: number;
  fps: number;
  sample_rate: number;
  channels: number;
  json?: any;
}

export interface FFmpegOptions {
  inputFiles: string[];
  outputFile: string;
  videoCodec?: string;
  audioCodec?: string;
  bitrate?: string;
  preset?: 'ultrafast' | 'fast' | 'medium' | 'slow' | 'veryslow';
}
