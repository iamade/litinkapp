import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import {
  Video,
  Download,
  Settings,
  Play,
  Pause,
  Film,
  Layers,
  Sliders,
  Monitor,
  Loader2,
  Upload,
  Eye,
  SplitSquareHorizontal,
  CheckCircle,
  AlertCircle,
  X,
  RotateCcw
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

interface MergePanelProps {
  chapterId?: string;
  scriptId?: string;
  videoGenerationId?: string;
}

const MergePanel: React.FC<MergePanelProps> = () => {
  // State management
  const { state: generationState } = useVideoGeneration();
  const mergeOps = useMergeOperations();

  const [activeView, setActiveView] = useState<'sources' | 'controls' | 'preview'>('sources');
  const [sourceType, setSourceType] = useState<'pipeline' | 'custom'>('pipeline');
  const [inputFiles, setInputFiles] = useState<MergeInputFile[]>([]);
  const [qualityTier, setQualityTier] = useState<MergeQualityTier>(MergeQualityTier.WEB);
  const [outputFormat, setOutputFormat] = useState<MergeOutputFormat>(MergeOutputFormat.MP4);
  const [processingMode, setProcessingMode] = useState<MergeProcessingMode>(MergeProcessingMode.FFMPEG_ONLY);
  const [customFFmpeg, setCustomFFmpeg] = useState(false);
  const [ffmpegParams, setFFmpegParams] = useState<FFmpegParameters>({
    fps: 30,
    preset: 'medium',
    crf: 23
  });

  // Preview and timeline state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [splitScreen, setSplitScreen] = useState(false);

  // Auto-populate from pipeline output
  useEffect(() => {
    if (sourceType === 'pipeline' && generationState.currentGeneration) {
      const generation = generationState.currentGeneration;
      const sources: MergeInputFile[] = [];

      // Add scene videos if available
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

      // Add audio files if available
      if (generation.audio_files) {
        // Add narrator audio
        if (generation.audio_files.narrator && generation.audio_files.narrator.length > 0) {
          generation.audio_files.narrator.forEach((audio: { url?: string; duration?: number }) => {
            if (audio.url) {
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

        // Add character audio
        if (generation.audio_files.characters && generation.audio_files.characters.length > 0) {
          generation.audio_files.characters.forEach((audio: { url?: string; duration?: number }) => {
            if (audio.url) {
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
      }

      setInputFiles(sources);
    }
  }, [sourceType, generationState.currentGeneration]);

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
  }, []);

  const removeInputFile = useCallback((index: number) => {
    setInputFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const startMerge = useCallback(async () => {
    if (!inputFiles.length) {
      toast.error('Please add at least one input file');
      return;
    }

    const params: MergeManualRequest = {
      video_generation_id: generationState.currentGeneration?.id,
      input_sources: inputFiles,
      quality_tier: qualityTier,
      output_format: outputFormat,
      ffmpeg_params: customFFmpeg ? ffmpegParams : undefined,
      merge_name: `Merge_${Date.now()}`
    };

    await mergeOps.startMerge(params);
  }, [inputFiles, generationState.currentGeneration?.id, qualityTier, outputFormat, customFFmpeg, ffmpegParams, mergeOps]);

  const generatePreview = useCallback(async () => {
    if (inputFiles.length < 1 || inputFiles.length > 2) {
      toast.error('Preview requires 1-2 input files');
      return;
    }

    const params: MergePreviewRequest = {
      input_sources: inputFiles.slice(0, 2),
      quality_tier: qualityTier,
      preview_duration: 30, // 30 seconds as specified
      ffmpeg_params: customFFmpeg ? ffmpegParams : undefined
    };

    await mergeOps.generatePreview(params);
  }, [inputFiles, qualityTier, customFFmpeg, ffmpegParams, mergeOps]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-gray-900">
            Video Merge Studio
          </h3>
          <p className="text-gray-600">
            Combine and process your video/audio content with professional results
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={generatePreview}
            disabled={!inputFiles.length || mergeOps.isMerging || mergeOps.isGeneratingPreview}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
            title="Generate a quick preview of your merged content (recommended before full merge)"
          >
            {mergeOps.isGeneratingPreview ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Eye className="w-4 h-4" />
            )}
            <span>{mergeOps.isGeneratingPreview ? 'Generating Preview...' : 'Preview'}</span>
          </button>
          <button
            onClick={startMerge}
            disabled={!inputFiles.length || mergeOps.isMerging}
            className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 transition-colors"
            title="Start the full merge operation (may take several minutes)"
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
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-xs font-bold text-blue-600">i</span>
            </div>
          </div>
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">How to use Video Merge Studio:</p>
            <ol className="list-decimal list-inside space-y-1 text-blue-700">
              <li>Add your video and audio files using the Sources tab</li>
              <li>Configure quality and format settings in the Controls tab</li>
              <li>Generate a preview to check your settings</li>
              <li>Start the full merge when ready</li>
            </ol>
          </div>
        </div>
      </div>

      {/* View Tabs */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="border-b">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            <button
              onClick={() => setActiveView('sources')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'sources'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Upload className="w-4 h-4" />
                <span>Sources</span>
              </div>
            </button>
            <button
              onClick={() => setActiveView('controls')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'controls'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Settings className="w-4 h-4" />
                <span>Controls</span>
              </div>
            </button>
            <button
              onClick={() => setActiveView('preview')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'preview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
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
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                  <span className="text-sm font-medium text-blue-800">
                    {mergeOps.mergeStatus || mergeOps.currentMerge.current_step || 'Processing merge...'}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-blue-600 font-medium">
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
              <div className="w-full bg-blue-200 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${mergeOps.mergeProgress}%` }}
                />
              </div>
              <div className="flex items-center justify-between mt-2">
                {mergeOps.queuePosition && mergeOps.queuePosition > 1 && (
                  <div className="text-xs text-blue-600 flex items-center space-x-1">
                    <span>Queue position: {mergeOps.queuePosition}</span>
                  </div>
                )}
                <div className="text-xs text-blue-500 ml-auto">
                  {mergeOps.mergeProgress < 25 && 'Preparing files...'}
                  {mergeOps.mergeProgress >= 25 && mergeOps.mergeProgress < 50 && 'Processing content...'}
                  {mergeOps.mergeProgress >= 50 && mergeOps.mergeProgress < 85 && 'Merging streams...'}
                  {mergeOps.mergeProgress >= 85 && 'Finalizing...'}
                </div>
              </div>
            </div>
          )}

          {/* Preview Generation Progress */}
          {mergeOps.isGeneratingPreview && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center space-x-2 mb-2">
                <Loader2 className="w-4 h-4 animate-spin text-green-600" />
                <span className="text-sm font-medium text-green-800">
                  Generating preview...
                </span>
              </div>
              <div className="w-full bg-green-200 rounded-full h-2">
                <div className="bg-green-600 h-2 rounded-full animate-pulse w-full"></div>
              </div>
              <div className="mt-2 text-xs text-green-600">
                This may take a few moments...
              </div>
            </div>
          )}

          {/* Sources Tab */}
          {activeView === 'sources' && (
            <div className="space-y-6">
              {/* Source Type Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Source Type
                </label>
                <div className="flex space-x-4">
                  <button
                    onClick={() => setSourceType('pipeline')}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg border ${
                      sourceType === 'pipeline'
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <Film className="w-4 h-4" />
                    <span>AI Pipeline Output</span>
                  </button>
                  <button
                    onClick={() => setSourceType('custom')}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg border ${
                      sourceType === 'custom'
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <Upload className="w-4 h-4" />
                    <span>Custom Videos</span>
                  </button>
                </div>
              </div>

              {/* File Upload for Custom Sources */}
              {sourceType === 'custom' && (
                <FileUpload onFilesUploaded={handleFilesUploaded} />
              )}

              {/* Input Files List */}
              {inputFiles.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-sm font-medium text-gray-700">Input Files</h4>
                  {inputFiles.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center">
                          {file.type === 'video' ? (
                            <Video className="w-4 h-4 text-blue-600" />
                          ) : (
                            <Layers className="w-4 h-4 text-blue-600" />
                          )}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {file.type === 'video' ? 'Video' : 'Audio'} {index + 1}
                          </p>
                          <p className="text-xs text-gray-500">
                            Duration: {file.duration ? `${file.duration}s` : 'Unknown'}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => removeInputFile(index)}
                        className="p-1 text-gray-400 hover:text-red-500"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Controls Tab */}
          {activeView === 'controls' && (
            <div className="space-y-6">
              {/* Quality and Format */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Quality Tier
                  </label>
                  <select
                    value={qualityTier}
                    onChange={(e) => setQualityTier(e.target.value as MergeQualityTier)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value={MergeQualityTier.WEB}>Web (480p)</option>
                    <option value={MergeQualityTier.MEDIUM}>Medium (720p)</option>
                    <option value={MergeQualityTier.HIGH}>High (1080p)</option>
                    <option value={MergeQualityTier.CUSTOM}>Custom</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Output Format
                  </label>
                  <select
                    value={outputFormat}
                    onChange={(e) => setOutputFormat(e.target.value as MergeOutputFormat)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value={MergeOutputFormat.MP4}>MP4</option>
                    <option value={MergeOutputFormat.WEBM}>WebM</option>
                    <option value={MergeOutputFormat.MOV}>MOV</option>
                  </select>
                </div>
              </div>

              {/* Processing Mode */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Processing Mode
                </label>
                <div className="flex space-x-4">
                  <button
                    onClick={() => setProcessingMode(MergeProcessingMode.FFMPEG_ONLY)}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg border ${
                      processingMode === MergeProcessingMode.FFMPEG_ONLY
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <Sliders className="w-4 h-4" />
                    <span>FFmpeg Only</span>
                  </button>
                  <button
                    onClick={() => setProcessingMode(MergeProcessingMode.FFMPEG_OPENSHOT)}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg border ${
                      processingMode === MergeProcessingMode.FFMPEG_OPENSHOT
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <Layers className="w-4 h-4" />
                    <span>FFmpeg + OpenShot</span>
                  </button>
                </div>
              </div>

              {/* Custom FFmpeg Options */}
              {qualityTier === 'custom' && (
                <div className="border-t pt-6">
                  <div className="flex items-center space-x-2 mb-4">
                    <input
                      type="checkbox"
                      id="custom-ffmpeg"
                      checked={customFFmpeg}
                      onChange={(e) => setCustomFFmpeg(e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <label htmlFor="custom-ffmpeg" className="text-sm font-medium text-gray-700">
                      Advanced FFmpeg Options
                    </label>
                  </div>

                  {customFFmpeg && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Video Codec
                        </label>
                        <select
                          value={ffmpegParams.video_codec || ''}
                          onChange={(e) => setFFmpegParams(prev => ({ ...prev, video_codec: e.target.value ? e.target.value as FFmpegVideoCodec : undefined }))}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="">Default</option>
                          <option value={FFmpegVideoCodec.LIBX264}>H.264</option>
                          <option value={FFmpegVideoCodec.LIBX265}>H.265</option>
                          <option value={FFmpegVideoCodec.LIBVPX_VP9}>VP9</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Audio Codec
                        </label>
                        <select
                          value={ffmpegParams.audio_codec || ''}
                          onChange={(e) => setFFmpegParams(prev => ({ ...prev, audio_codec: e.target.value ? e.target.value as FFmpegAudioCodec : undefined }))}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="">Default</option>
                          <option value={FFmpegAudioCodec.AAC}>AAC</option>
                          <option value={FFmpegAudioCodec.MP3}>MP3</option>
                          <option value={FFmpegAudioCodec.OPUS}>Opus</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Resolution
                        </label>
                        <input
                          type="text"
                          placeholder="1920x1080"
                          value={ffmpegParams.resolution}
                          onChange={(e) => setFFmpegParams(prev => ({ ...prev, resolution: e.target.value }))}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          FPS
                        </label>
                        <input
                          type="number"
                          min="1"
                          max="120"
                          value={ffmpegParams.fps}
                          onChange={(e) => setFFmpegParams(prev => ({ ...prev, fps: parseInt(e.target.value) || 30 }))}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Preview Tab */}
          {activeView === 'preview' && (
            <div className="space-y-6">
              {/* Preview Status */}
              {mergeOps.currentPreview && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <span className="text-sm font-medium text-green-800">
                      Preview Generated
                    </span>
                    <span className="text-xs text-green-600">
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

                  <button
                    onClick={() => setSplitScreen(!splitScreen)}
                    className={`flex items-center space-x-2 px-3 py-1 rounded text-sm transition-colors ${
                      splitScreen
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                    disabled={!mergeOps.currentPreview?.preview_url}
                  >
                    <SplitSquareHorizontal className="w-3 h-3" />
                    <span>Split Screen</span>
                  </button>
                </div>

                {mergeOps.currentPreview?.preview_url && (
                  <div className="text-sm text-gray-600 font-mono">
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
                    poster="/api/placeholder/640/360" // Placeholder while loading
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
                  <div className="w-full bg-gray-200 rounded-full h-2 cursor-pointer" onClick={(e) => {
                    // Allow clicking on timeline to seek
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
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>0:00</span>
                    <span>{Math.floor(mergeOps.currentPreview.preview_duration / 60)}:{(mergeOps.currentPreview.preview_duration % 60).toFixed(0).padStart(2, '0')}</span>
                  </div>
                </div>
              )}

              {/* Preview Info */}
              {mergeOps.currentPreview?.preview_url && (
                <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Preview Information</h4>
                  <div className="text-xs text-gray-600 space-y-1">
                    <p>• This is a {mergeOps.currentPreview.preview_duration}-second preview of your merge</p>
                    <p>• Quality and duration may differ in the final merge</p>
                    <p>• Use this to verify your settings before starting the full merge</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Completed Merge Display */}
      {mergeOps.currentMerge?.status === 'completed' && mergeOps.currentMerge.output_url && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <CheckCircle className="w-6 h-6 text-green-500" />
              <div>
                <h4 className="text-lg font-semibold text-gray-900">
                  Merge Completed Successfully
                </h4>
                <p className="text-sm text-gray-600">
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
              poster="/api/placeholder/640/360"
            />
          </div>

          {/* File Information */}
          <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
            <h5 className="text-sm font-medium text-gray-700 mb-2">File Information</h5>
            <div className="text-xs text-gray-600 space-y-1">
              <p><strong>Merge ID:</strong> {mergeOps.currentMerge.id}</p>
              <p><strong>Quality:</strong> {mergeOps.currentMerge.quality_tier}</p>
              <p><strong>Format:</strong> {mergeOps.currentMerge.output_format.toUpperCase()}</p>
              <p><strong>Completed:</strong> {mergeOps.currentMerge.updated_at.toLocaleString()}</p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
            <button
              onClick={() => mergeOps.reset()}
              className="flex items-center space-x-2 px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700 transition-colors"
            >
              <span>Start New Merge</span>
            </button>
            <div className="text-xs text-gray-500">
              File will be available for download for 24 hours
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {mergeOps.currentMerge?.status === 'failed' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h4 className="text-red-800 font-medium">Merge Operation Failed</h4>
              <p className="text-red-700 text-sm mt-1">
                {mergeOps.currentMerge.error_message || 'An unexpected error occurred during the merge process'}
              </p>

              {/* Error Details */}
              <div className="mt-3 p-2 bg-red-100 rounded text-xs text-red-800 font-mono">
                {mergeOps.currentMerge.error_message || 'Unknown error'}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center space-x-2 mt-3">
                <button
                  onClick={async () => {
                    const success = await mergeOps.retryMerge(mergeOps.currentMerge!.id);
                    if (!success) {
                      mergeOps.reset();
                    }
                  }}
                  disabled={mergeOps.retryCount >= 3}
                  className="flex items-center space-x-1 px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:bg-gray-400 transition-colors"
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
                  <span className="text-xs text-red-600 ml-2">
                    Attempt {mergeOps.retryCount + 1}/3
                  </span>
                )}
              </div>

              {/* Help Text */}
              <div className="mt-3 text-xs text-red-600">
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
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h4 className="text-yellow-800 font-medium">Preview Generation Failed</h4>
              <p className="text-yellow-700 text-sm mt-1">
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