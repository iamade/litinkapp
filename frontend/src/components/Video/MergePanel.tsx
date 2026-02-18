import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import {
  Video,
  Download,
  Play,
  Pause,
  Film,
  Layers,
  Sliders,
  Monitor,
  Loader2,
  Upload,
  Eye,
  CheckCircle,
  AlertCircle,
  X,
  RotateCcw,
  Lock,
  Music,
  Volume2,
  VolumeX
} from 'lucide-react';
import { useVideoGeneration } from '../../contexts/VideoGenerationContext';
import { useMergeOperations } from '../../hooks/useMergeOperations';
import FileUpload from './FileUpload';
import {
  MergeInputFile,
  MergeQualityTier,
  MergeOutputFormat,
  MergeProcessingMode,
  FFmpegParameters,
  FFmpegVideoCodec,
  FFmpegAudioCodec,
  MergeManualRequest,
  MergePreviewRequest
} from '../../types/merge';
import type { VideoScene, EditorSettings } from '../../types/videoProduction';

interface MergePanelProps {
  chapterId?: string;
  scriptId?: string;
  videoGenerationId?: string;
  videoGenerations?: any[];
  audioFiles?: string[];
  scenes?: VideoScene[];
  editorSettings?: EditorSettings;
  userTier?: 'free' | 'basic' | 'pro' | 'enterprise';
}

// Track types for the multi-track view
interface AudioTrack {
  id: string;
  label: string;
  type: 'primary' | 'music' | 'effects' | 'ambiance' | 'custom';
  url: string;
  duration?: number;
  volume: number;
  locked: boolean;
}

const MergePanel: React.FC<MergePanelProps> = ({
  videoGenerations = [],
  editorSettings,
  userTier = 'free'
}) => {
  const { state: generationState } = useVideoGeneration();
  const mergeOps = useMergeOperations();
  const isPaidTier = userTier !== 'free';

  const [activeView, setActiveView] = useState<'tracks' | 'controls' | 'preview'>('tracks');
  const [inputFiles, setInputFiles] = useState<MergeInputFile[]>([]);
  const [audioTracks, setAudioTracks] = useState<AudioTrack[]>([]);
  const [qualityTier, setQualityTier] = useState<MergeQualityTier>(
    editorSettings?.quality === 'high' || editorSettings?.quality === 'ultra'
      ? MergeQualityTier.HIGH
      : editorSettings?.quality === 'medium'
        ? MergeQualityTier.MEDIUM
        : MergeQualityTier.WEB
  );
  const [outputFormat, setOutputFormat] = useState<MergeOutputFormat>(
    editorSettings?.outputFormat === 'webm'
      ? MergeOutputFormat.WEBM
      : editorSettings?.outputFormat === 'mov'
        ? MergeOutputFormat.MOV
        : MergeOutputFormat.MP4
  );
  const [processingMode, setProcessingMode] = useState<MergeProcessingMode>(MergeProcessingMode.FFMPEG_ONLY);
  const [customFFmpeg, setCustomFFmpeg] = useState(false);
  const [ffmpegParams, setFFmpegParams] = useState<FFmpegParameters>({
    fps: editorSettings?.fps || 30,
    preset: 'medium',
    crf: 23
  });

  // Preview and timeline state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  // Auto-populate from video generations and audio files
  useEffect(() => {
    const sources: MergeInputFile[] = [];
    const tracks: AudioTrack[] = [];
    let trackIndex = 0;

    // 1. Video tracks from generations
    if (videoGenerations.length > 0) {
      videoGenerations.forEach((gen: any) => {
        if (gen.scene_videos && Array.isArray(gen.scene_videos)) {
          gen.scene_videos.forEach((scene: any) => {
            if (scene.video_url) {
              sources.push({
                url: scene.video_url,
                type: 'video',
                duration: scene.duration || 10,
                start_time: 0,
                volume: 1.0
              });
            }
          });
        }

        // Primary audio (already merged with video during generation)
        if (gen.audio_files) {
          // Narrator audio = primary track (locked/informational)
          if (gen.audio_files.narrator && Array.isArray(gen.audio_files.narrator)) {
            gen.audio_files.narrator.forEach((audio: any, idx: number) => {
              if (audio.url) {
                tracks.push({
                  id: `narrator-${trackIndex++}`,
                  label: `Narrator ${idx + 1}`,
                  type: 'primary',
                  url: audio.url,
                  duration: audio.duration || 30,
                  volume: 1.0,
                  locked: true
                });
                sources.push({
                  url: audio.url,
                  type: 'audio',
                  duration: audio.duration || 30,
                  start_time: 0,
                  volume: 1.0
                });
              }
            });
          }

          // Character audio = primary track (locked/informational)
          if (gen.audio_files.characters && Array.isArray(gen.audio_files.characters)) {
            gen.audio_files.characters.forEach((audio: any, idx: number) => {
              if (audio.url) {
                tracks.push({
                  id: `character-${trackIndex++}`,
                  label: `Character ${idx + 1}`,
                  type: 'primary',
                  url: audio.url,
                  duration: audio.duration || 15,
                  volume: 1.0,
                  locked: true
                });
                sources.push({
                  url: audio.url,
                  type: 'audio',
                  duration: audio.duration || 15,
                  start_time: 0,
                  volume: 1.0
                });
              }
            });
          }

          // Background music = additional track (adjustable)
          if (gen.audio_files.background_music && Array.isArray(gen.audio_files.background_music)) {
            gen.audio_files.background_music.forEach((audio: any, idx: number) => {
              if (audio.url) {
                tracks.push({
                  id: `music-${trackIndex++}`,
                  label: `Background Music ${idx + 1}`,
                  type: 'music',
                  url: audio.url,
                  duration: audio.duration || 60,
                  volume: 0.3,
                  locked: false
                });
              }
            });
          }

          // Sound effects = additional track (adjustable)
          if (gen.audio_files.sound_effects && Array.isArray(gen.audio_files.sound_effects)) {
            gen.audio_files.sound_effects.forEach((audio: any, idx: number) => {
              if (audio.url) {
                tracks.push({
                  id: `effects-${trackIndex++}`,
                  label: `Sound Effect ${idx + 1}`,
                  type: 'effects',
                  url: audio.url,
                  duration: audio.duration || 5,
                  volume: 0.5,
                  locked: false
                });
              }
            });
          }

          // Ambiance = additional track (adjustable)
          if (gen.audio_files.ambiance && Array.isArray(gen.audio_files.ambiance)) {
            gen.audio_files.ambiance.forEach((audio: any, idx: number) => {
              if (audio.url) {
                tracks.push({
                  id: `ambiance-${trackIndex++}`,
                  label: `Ambiance ${idx + 1}`,
                  type: 'ambiance',
                  url: audio.url,
                  duration: audio.duration || 30,
                  volume: 0.2,
                  locked: false
                });
              }
            });
          }
        }
      });
    }

    // 2. Fallback: auto-populate from pipeline state
    if (sources.length === 0 && generationState.currentGeneration) {
      const generation = generationState.currentGeneration;
      if (generation.scene_videos && generation.scene_videos.length > 0) {
        generation.scene_videos.forEach((scene: { video_url?: string; duration?: number }) => {
          if (scene.video_url) {
            sources.push({
              url: scene.video_url,
              type: 'video',
              duration: scene.duration || 10,
              start_time: 0,
              volume: 1.0
            });
          }
        });
      }
    }

    if (sources.length > 0) setInputFiles(sources);
    if (tracks.length > 0) setAudioTracks(tracks);
  }, [videoGenerations, generationState.currentGeneration]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mergeOps.cleanupPreview();
    };
  }, [mergeOps]);

  const handleFilesUploaded = useCallback((uploadedFiles: { status: string; url?: string; type: string; duration?: number }[]) => {
    const newFiles: MergeInputFile[] = uploadedFiles
      .filter(f => f.status === 'completed' && f.url)
      .map(f => ({
        url: f.url!,
        type: f.type.startsWith('video/') ? 'video' : 'audio',
        duration: f.duration,
        start_time: 0,
        volume: 1.0
      }));

    setInputFiles(prev => [...prev, ...newFiles]);

    // Also add as custom audio tracks
    const newTracks: AudioTrack[] = newFiles
      .filter(f => f.type === 'audio')
      .map((f, idx) => ({
        id: `custom-${Date.now()}-${idx}`,
        label: `Custom Audio ${idx + 1}`,
        type: 'custom' as const,
        url: f.url,
        duration: f.duration,
        volume: 1.0,
        locked: false
      }));
    if (newTracks.length > 0) {
      setAudioTracks(prev => [...prev, ...newTracks]);
    }
  }, []);


  const removeAudioTrack = useCallback((trackId: string) => {
    setAudioTracks(prev => prev.filter(t => t.id !== trackId));
  }, []);

  const updateTrackVolume = useCallback((trackId: string, volume: number) => {
    setAudioTracks(prev => prev.map(t =>
      t.id === trackId ? { ...t, volume } : t
    ));
  }, []);

  const startMerge = useCallback(async () => {
    if (!inputFiles.length) {
      toast.error('No video or audio files available for merge');
      return;
    }

    // Build merge request with audio track volumes applied
    const allSources = [...inputFiles];
    // Add additional audio tracks that aren't already in inputFiles
    audioTracks.filter(t => !t.locked && t.type !== 'primary').forEach(track => {
      const exists = allSources.some(s => s.url === track.url);
      if (!exists) {
        allSources.push({
          url: track.url,
          type: 'audio',
          duration: track.duration,
          start_time: 0,
          volume: track.volume
        });
      }
    });

    const params: MergeManualRequest = {
      video_generation_id: generationState.currentGeneration?.id,
      input_sources: allSources,
      quality_tier: qualityTier,
      output_format: outputFormat,
      ffmpeg_params: customFFmpeg ? ffmpegParams : undefined,
      merge_name: `Merge_${Date.now()}`
    };

    await mergeOps.startMerge(params);
  }, [inputFiles, audioTracks, generationState.currentGeneration?.id, qualityTier, outputFormat, customFFmpeg, ffmpegParams, mergeOps]);

  const generatePreview = useCallback(async () => {
    if (inputFiles.length < 1) {
      toast.error('No files available for preview');
      return;
    }

    const params: MergePreviewRequest = {
      input_sources: inputFiles.slice(0, 2),
      quality_tier: qualityTier,
      preview_duration: 30,
      ffmpeg_params: customFFmpeg ? ffmpegParams : undefined
    };

    await mergeOps.generatePreview(params);
  }, [inputFiles, qualityTier, customFFmpeg, ffmpegParams, mergeOps]);

  const videoCount = inputFiles.filter(f => f.type === 'video').length;
  const primaryAudioCount = audioTracks.filter(t => t.locked).length;
  const additionalAudioCount = audioTracks.filter(t => !t.locked).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Merge Studio
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Combine your generated videos with audio tracks into a final production
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={generatePreview}
            disabled={!inputFiles.length || mergeOps.isMerging || mergeOps.isGeneratingPreview}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 dark:disabled:bg-gray-600 transition-colors"
            title="Generate a quick preview of your merged content"
          >
            {mergeOps.isGeneratingPreview ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Eye className="w-4 h-4" />
            )}
            <span>{mergeOps.isGeneratingPreview ? 'Generating...' : 'Preview'}</span>
          </button>
          <button
            onClick={startMerge}
            disabled={!inputFiles.length || mergeOps.isMerging}
            className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 dark:disabled:bg-gray-600 transition-colors"
            title="Start the full merge operation"
          >
            {mergeOps.isMerging ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Video className="w-4 h-4" />
            )}
            <span>{mergeOps.isMerging ? 'Merging...' : 'Start Merge'}</span>
          </button>
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <div className="w-6 h-6 bg-blue-100 dark:bg-blue-800 rounded-full flex items-center justify-center">
              <span className="text-xs font-bold text-blue-600 dark:text-blue-300">i</span>
            </div>
          </div>
          <div className="text-sm text-blue-800 dark:text-blue-200">
            <p className="font-medium mb-1">How to use Merge Studio:</p>
            <ol className="list-decimal list-inside space-y-1 text-blue-700 dark:text-blue-300">
              <li>Your generated scene videos and primary audio are auto-loaded from Timeline</li>
              <li>Arrange additional audio tracks (music, effects, ambiance) on the timeline</li>
              <li>Adjust volume levels for each audio track</li>
              <li>Preview the merge to check your mix</li>
              <li>Start the full merge to create your final video</li>
            </ol>
          </div>
        </div>
      </div>

      {/* View Tabs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border dark:border-gray-700">
        <div className="border-b dark:border-gray-700">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            <button
              onClick={() => setActiveView('tracks')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'tracks'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Film className="w-4 h-4" />
                <span>Tracks</span>
                <span className="text-xs bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-gray-600 dark:text-gray-300">
                  {videoCount}V · {primaryAudioCount + additionalAudioCount}A
                </span>
              </div>
            </button>
            <button
              onClick={() => setActiveView('controls')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'controls'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Sliders className="w-4 h-4" />
                <span>Controls</span>
              </div>
            </button>
            <button
              onClick={() => setActiveView('preview')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'preview'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Monitor className="w-4 h-4" />
                <span>Preview</span>
              </div>
            </button>
          </nav>
        </div>

        {/* Content Area */}
        <div className="p-6">
          {/* Progress Display */}
          {mergeOps.isMerging && mergeOps.currentMerge && (
            <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-600 dark:text-blue-400" />
                  <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                    {mergeOps.mergeStatus || mergeOps.currentMerge.current_step || 'Processing merge...'}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-blue-600 dark:text-blue-400 font-medium">
                    {mergeOps.mergeProgress}%
                  </span>
                  <button
                    onClick={mergeOps.cancelMerge}
                    className="px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600 transition-colors"
                    title="Cancel merge operation"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              </div>
              <div className="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${mergeOps.mergeProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Preview Generation Progress */}
          {mergeOps.isGeneratingPreview && (
            <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <div className="flex items-center space-x-2 mb-2">
                <Loader2 className="w-4 h-4 animate-spin text-green-600 dark:text-green-400" />
                <span className="text-sm font-medium text-green-800 dark:text-green-200">
                  Generating preview...
                </span>
              </div>
              <div className="w-full bg-green-200 dark:bg-green-800 rounded-full h-2">
                <div className="bg-green-600 h-2 rounded-full animate-pulse w-full"></div>
              </div>
            </div>
          )}

          {/* ==================== TRACKS TAB ==================== */}
          {activeView === 'tracks' && (
            <div className="space-y-6">
              {/* Video Track */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                  <Video className="w-4 h-4 text-blue-500" />
                  Video Tracks
                  <span className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded-full">
                    {videoCount} {videoCount === 1 ? 'clip' : 'clips'}
                  </span>
                </h4>
                {inputFiles.filter(f => f.type === 'video').length > 0 ? (
                  <div className="space-y-2">
                    {inputFiles.filter(f => f.type === 'video').map((file, index) => (
                      <div key={`video-${index}`} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-blue-500/10 dark:bg-blue-400/10 rounded-lg flex items-center justify-center">
                            <Film className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              Scene {index + 1}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              Duration: {file.duration ? `${file.duration}s` : 'Unknown'}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            Auto-loaded
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 text-center text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/30 rounded-lg border border-dashed border-gray-300 dark:border-gray-600">
                    <Film className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    <p className="text-sm">No generated videos available yet</p>
                    <p className="text-xs mt-1">Generate videos in the Timeline tab first</p>
                  </div>
                )}
              </div>

              {/* Primary Audio Tracks (Locked) */}
              {audioTracks.filter(t => t.locked).length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                    <Volume2 className="w-4 h-4 text-purple-500" />
                    Primary Audio
                    <span className="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded-full">
                      Merged with video
                    </span>
                  </h4>
                  <div className="space-y-2">
                    {audioTracks.filter(t => t.locked).map(track => (
                      <div key={track.id} className="flex items-center justify-between p-3 bg-purple-50 dark:bg-purple-900/10 rounded-lg border border-purple-200 dark:border-purple-800/40">
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-purple-500/10 dark:bg-purple-400/10 rounded-lg flex items-center justify-center">
                            <Volume2 className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {track.label}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              Duration: {track.duration ? `${track.duration}s` : 'Unknown'} · Volume: {Math.round(track.volume * 100)}%
                            </p>
                          </div>
                        </div>
                        <Lock className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Additional Audio Tracks (Adjustable) */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                  <Music className="w-4 h-4 text-green-500" />
                  Additional Audio
                  <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 rounded-full">
                    {additionalAudioCount} {additionalAudioCount === 1 ? 'track' : 'tracks'}
                  </span>
                </h4>
                {audioTracks.filter(t => !t.locked).length > 0 ? (
                  <div className="space-y-2">
                    {audioTracks.filter(t => !t.locked).map(track => (
                      <div key={track.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                        <div className="flex items-center space-x-3">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                            track.type === 'music' ? 'bg-green-500/10 dark:bg-green-400/10' :
                            track.type === 'effects' ? 'bg-orange-500/10 dark:bg-orange-400/10' :
                            track.type === 'ambiance' ? 'bg-cyan-500/10 dark:bg-cyan-400/10' :
                            'bg-gray-500/10 dark:bg-gray-400/10'
                          }`}>
                            <Music className={`w-5 h-5 ${
                              track.type === 'music' ? 'text-green-600 dark:text-green-400' :
                              track.type === 'effects' ? 'text-orange-600 dark:text-orange-400' :
                              track.type === 'ambiance' ? 'text-cyan-600 dark:text-cyan-400' :
                              'text-gray-600 dark:text-gray-400'
                            }`} />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {track.label}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {track.type.charAt(0).toUpperCase() + track.type.slice(1)} · {track.duration ? `${track.duration}s` : 'Unknown'}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          {/* Volume slider */}
                          <div className="flex items-center gap-2">
                            <VolumeX className="w-3 h-3 text-gray-400" />
                            <input
                              type="range"
                              min="0"
                              max="100"
                              value={Math.round(track.volume * 100)}
                              onChange={(e) => updateTrackVolume(track.id, parseInt(e.target.value) / 100)}
                              className="w-20 h-1 accent-blue-600"
                            />
                            <span className="text-xs text-gray-500 dark:text-gray-400 w-8 text-right">
                              {Math.round(track.volume * 100)}%
                            </span>
                          </div>
                          <button
                            onClick={() => removeAudioTrack(track.id)}
                            className="p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 text-center text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/30 rounded-lg border border-dashed border-gray-300 dark:border-gray-600">
                    <Music className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    <p className="text-sm">No additional audio tracks</p>
                    <p className="text-xs mt-1">Music, effects, and ambiance will appear here when available</p>
                  </div>
                )}
              </div>

              {/* Custom Upload (Paid Tiers Only) */}
              {isPaidTier ? (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                  <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                    <Upload className="w-4 h-4 text-indigo-500" />
                    Custom Files
                  </h4>
                  <FileUpload onFilesUploaded={handleFilesUploaded} />
                </div>
              ) : (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                  <div className="p-4 bg-amber-50 dark:bg-amber-900/10 rounded-lg border border-amber-200 dark:border-amber-800/40 flex items-center gap-3">
                    <Lock className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                        Custom file upload requires a paid plan
                      </p>
                      <p className="text-xs text-amber-600 dark:text-amber-400 mt-0.5">
                        Upgrade to upload your own video and audio files for merging
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ==================== CONTROLS TAB ==================== */}
          {activeView === 'controls' && (
            <div className="space-y-6">
              {/* Quality and Format */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Quality Tier
                  </label>
                  <select
                    value={qualityTier}
                    onChange={(e) => setQualityTier(e.target.value as MergeQualityTier)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value={MergeQualityTier.WEB}>Web (480p)</option>
                    <option value={MergeQualityTier.MEDIUM}>Medium (720p)</option>
                    <option value={MergeQualityTier.HIGH}>High (1080p)</option>
                    <option value={MergeQualityTier.CUSTOM}>Custom</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Output Format
                  </label>
                  <select
                    value={outputFormat}
                    onChange={(e) => setOutputFormat(e.target.value as MergeOutputFormat)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value={MergeOutputFormat.MP4}>MP4</option>
                    <option value={MergeOutputFormat.WEBM}>WebM</option>
                    <option value={MergeOutputFormat.MOV}>MOV</option>
                  </select>
                </div>
              </div>

              {/* Processing Mode */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Processing Mode
                </label>
                <div className="flex space-x-4">
                  <button
                    onClick={() => setProcessingMode(MergeProcessingMode.FFMPEG_ONLY)}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg border ${
                      processingMode === MergeProcessingMode.FFMPEG_ONLY
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                        : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    <Sliders className="w-4 h-4" />
                    <span>FFmpeg Only</span>
                  </button>
                  <button
                    onClick={() => setProcessingMode(MergeProcessingMode.FFMPEG_OPENSHOT)}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg border ${
                      processingMode === MergeProcessingMode.FFMPEG_OPENSHOT
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                        : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    <Layers className="w-4 h-4" />
                    <span>FFmpeg + OpenShot</span>
                  </button>
                </div>
              </div>

              {/* Custom FFmpeg Options */}
              {qualityTier === 'custom' && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
                  <div className="flex items-center space-x-2 mb-4">
                    <input
                      type="checkbox"
                      id="custom-ffmpeg"
                      checked={customFFmpeg}
                      onChange={(e) => setCustomFFmpeg(e.target.checked)}
                      className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
                    />
                    <label htmlFor="custom-ffmpeg" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Advanced FFmpeg Options
                    </label>
                  </div>

                  {customFFmpeg && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          Video Codec
                        </label>
                        <select
                          value={ffmpegParams.video_codec || ''}
                          onChange={(e) => setFFmpegParams(prev => ({ ...prev, video_codec: e.target.value ? e.target.value as FFmpegVideoCodec : undefined }))}
                          className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="">Default</option>
                          <option value={FFmpegVideoCodec.LIBX264}>H.264</option>
                          <option value={FFmpegVideoCodec.LIBX265}>H.265</option>
                          <option value={FFmpegVideoCodec.LIBVPX_VP9}>VP9</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          Audio Codec
                        </label>
                        <select
                          value={ffmpegParams.audio_codec || ''}
                          onChange={(e) => setFFmpegParams(prev => ({ ...prev, audio_codec: e.target.value ? e.target.value as FFmpegAudioCodec : undefined }))}
                          className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="">Default</option>
                          <option value={FFmpegAudioCodec.AAC}>AAC</option>
                          <option value={FFmpegAudioCodec.MP3}>MP3</option>
                          <option value={FFmpegAudioCodec.OPUS}>Opus</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          Resolution
                        </label>
                        <input
                          type="text"
                          placeholder="1920x1080"
                          value={ffmpegParams.resolution}
                          onChange={(e) => setFFmpegParams(prev => ({ ...prev, resolution: e.target.value }))}
                          className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-1 focus:ring-blue-500"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                          FPS
                        </label>
                        <input
                          type="number"
                          min="1"
                          max="120"
                          value={ffmpegParams.fps}
                          onChange={(e) => setFFmpegParams(prev => ({ ...prev, fps: parseInt(e.target.value) || 30 }))}
                          className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-1 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ==================== PREVIEW TAB ==================== */}
          {activeView === 'preview' && (
            <div className="space-y-6">
              {/* Preview Status */}
              {mergeOps.currentPreview && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                    <span className="text-sm font-medium text-green-800 dark:text-green-200">
                      Preview Generated
                    </span>
                    <span className="text-xs text-green-600 dark:text-green-400">
                      ({mergeOps.currentPreview.preview_duration}s)
                    </span>
                  </div>
                </div>
              )}

              {/* Preview Controls */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  {mergeOps.currentPreview?.preview_url && (
                    <button
                      onClick={() => setIsPlaying(!isPlaying)}
                      className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                    >
                      {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
                      <span>{isPlaying ? 'Pause' : 'Play'}</span>
                    </button>
                  )}
                </div>

                {mergeOps.currentPreview?.preview_url && (
                  <div className="text-sm text-gray-600 dark:text-gray-400 font-mono">
                    {Math.floor(currentTime / 60)}:{(currentTime % 60).toFixed(0).padStart(2, '0')} / {mergeOps.currentPreview.preview_duration}s
                  </div>
                )}
              </div>

              {/* Video Preview */}
              <div className="bg-black rounded-lg overflow-hidden shadow-lg">
                {mergeOps.currentPreview?.preview_url ? (
                  <video
                    src={mergeOps.currentPreview.preview_url}
                    controls
                    className="w-full h-auto max-h-96"
                    onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                  />
                ) : (
                  <div className="flex items-center justify-center h-48 text-gray-400">
                    <div className="text-center">
                      <Monitor className="mx-auto h-12 w-12 mb-4 opacity-50" />
                      <p className="text-lg font-medium mb-2">No Preview Available</p>
                      <p className="text-sm mb-4">Generate a preview to see how your merged content will look</p>
                      <div className="text-xs text-gray-500">
                        <p>• Previews are generated quickly for review</p>
                        <p>• Full merge operations take longer but produce final results</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Timeline Scrubber */}
              {mergeOps.currentPreview?.preview_url && (
                <div className="space-y-2">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 cursor-pointer" onClick={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const clickX = e.clientX - rect.left;
                    const percentage = clickX / rect.width;
                    const video = document.querySelector('video');
                    if (video) {
                      video.currentTime = percentage * mergeOps.currentPreview!.preview_duration;
                    }
                  }}>
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-100"
                      style={{ width: `${mergeOps.currentPreview ? (currentTime / mergeOps.currentPreview.preview_duration) * 100 : 0}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>0:00</span>
                    <span>{Math.floor(mergeOps.currentPreview.preview_duration / 60)}:{(mergeOps.currentPreview.preview_duration % 60).toFixed(0).padStart(2, '0')}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Completed Merge Display */}
      {mergeOps.currentMerge?.status === 'completed' && mergeOps.currentMerge.output_url && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <CheckCircle className="w-6 h-6 text-green-500" />
              <div>
                <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Merge Completed Successfully
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Your merged video is ready for download
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => window.open(mergeOps.currentMerge!.output_url, '_blank')}
                className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                title="Open video in new tab"
              >
                <Eye className="w-3 h-3" />
                <span>View</span>
              </button>
              <button
                onClick={() => mergeOps.downloadMergeResult(mergeOps.currentMerge!.id)}
                className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition-colors"
                title="Download merged video file"
              >
                <Download className="w-4 h-4" />
                <span>Download</span>
              </button>
            </div>
          </div>

          {/* Video Preview */}
          <div className="mb-4">
            <video
              src={mergeOps.currentMerge.output_url}
              controls
              className="w-full rounded-lg shadow-md"
            />
          </div>

          {/* File Information */}
          <div className="p-3 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg">
            <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">File Information</h5>
            <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
              <p><strong>Merge ID:</strong> {mergeOps.currentMerge.id}</p>
              <p><strong>Quality:</strong> {mergeOps.currentMerge.quality_tier}</p>
              <p><strong>Format:</strong> {mergeOps.currentMerge.output_format.toUpperCase()}</p>
              <p><strong>Completed:</strong> {mergeOps.currentMerge.updated_at.toLocaleString()}</p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={() => mergeOps.reset()}
              className="flex items-center space-x-2 px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700 transition-colors"
            >
              <span>Start New Merge</span>
            </button>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              File will be available for download for 24 hours
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {mergeOps.currentMerge?.status === 'failed' && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-red-500 dark:text-red-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h4 className="text-red-800 dark:text-red-200 font-medium">Merge Operation Failed</h4>
              <p className="text-red-700 dark:text-red-300 text-sm mt-1">
                {mergeOps.currentMerge.error_message || 'An unexpected error occurred during the merge process'}
              </p>

              <div className="flex items-center space-x-2 mt-3">
                <button
                  onClick={async () => {
                    const success = await mergeOps.retryMerge(mergeOps.currentMerge!.id);
                    if (!success) {
                      mergeOps.reset();
                    }
                  }}
                  disabled={mergeOps.retryCount >= 3}
                  className="flex items-center space-x-1 px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:bg-gray-400 dark:disabled:bg-gray-600 transition-colors"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Retry Merge</span>
                </button>

                <button
                  onClick={() => mergeOps.reset()}
                  className="px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700 transition-colors"
                >
                  Start Over
                </button>

                {mergeOps.retryCount > 0 && (
                  <span className="text-xs text-red-600 dark:text-red-400 ml-2">
                    Attempt {mergeOps.retryCount + 1}/3
                  </span>
                )}
              </div>

              <div className="mt-3 text-xs text-red-600 dark:text-red-400">
                <p>• Check your input files are valid and accessible</p>
                <p>• Try different quality settings if the issue persists</p>
                <p>• Contact support if the problem continues</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Preview Error Display */}
      {mergeOps.currentPreview?.status === 'failed' && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-yellow-500 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h4 className="text-yellow-800 dark:text-yellow-200 font-medium">Preview Generation Failed</h4>
              <p className="text-yellow-700 dark:text-yellow-300 text-sm mt-1">
                {mergeOps.currentPreview.error_message || 'Failed to generate preview'}
              </p>
              <div className="flex items-center space-x-2 mt-2">
                <button
                  onClick={generatePreview}
                  className="px-3 py-1 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700 transition-colors"
                >
                  Retry Preview
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MergePanel;