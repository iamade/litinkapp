import React, { useState } from 'react';
import { CheckCircle, Download, Share2, Play, Pause, Volume2, VolumeX, Maximize, Clock, HardDrive } from 'lucide-react';
import { useVideoGeneration } from '../../../contexts/VideoGenerationContext';

export const CompletedStep: React.FC = () => {
  const { state } = useVideoGeneration();
  const generation = state.currentGeneration;
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  if (!generation) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading completion status...</div>
      </div>
    );
  }

  const finalVideoUrl = generation.merge_data?.final_video_url || generation.video_url;
  const mergeStats = generation.merge_data?.merge_statistics;

  const handleShare = async () => {
    if (navigator.share && finalVideoUrl) {
      try {
        await navigator.share({
          title: 'My Generated Video',
          text: 'Check out this video I created!',
          url: finalVideoUrl,
        });
      } catch (error) {
        console.log('Error sharing:', error);
        // Fallback to copying URL to clipboard
        navigator.clipboard.writeText(finalVideoUrl);
        alert('Video URL copied to clipboard!');
      }
    } else if (finalVideoUrl) {
      // Fallback for browsers without Web Share API
      navigator.clipboard.writeText(finalVideoUrl);
      alert('Video URL copied to clipboard!');
    }
  };

  return (
    <div className="space-y-6">
      {/* Success Header */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-4">
          <CheckCircle className="w-12 h-12 text-green-600" />
          <div>
            <h3 className="text-3xl font-bold text-gray-900">Video Generation Complete!</h3>
            <p className="text-gray-600 mt-2">Your video has been successfully generated and is ready to view</p>
          </div>
        </div>
      </div>

      {/* Video Player */}
      {finalVideoUrl && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="relative">
            <video
              className="w-full aspect-video bg-black"
              controls
              poster={generation.merge_data?.quality_versions?.[0]?.thumbnail_url}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onVolumeChange={(e) => setIsMuted((e.target as HTMLVideoElement).muted)}
            >
              <source src={finalVideoUrl} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
            
            {/* Custom overlay controls (optional) */}
            <div className="absolute top-4 right-4 flex gap-2">
              <button
                onClick={handleShare}
                className="p-2 bg-black bg-opacity-50 text-white rounded-full hover:bg-opacity-70 transition-opacity"
                title="Share video"
              >
                <Share2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Video Controls Footer */}
          <div className="p-4 bg-gray-50 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium text-gray-900">Final Video</span>
              {mergeStats && (
                <div className="flex items-center gap-4 text-sm text-gray-600">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {mergeStats.total_duration.toFixed(1)}s
                  </span>
                  <span className="flex items-center gap-1">
                    <HardDrive className="w-3 h-3" />
                    {mergeStats.file_size_mb.toFixed(1)} MB
                  </span>
                </div>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <a
                href={finalVideoUrl}
                download="generated-video.mp4"
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Download className="w-4 h-4" />
                Download
              </a>
              
              <button
                onClick={handleShare}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <Share2 className="w-4 h-4" />
                Share
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Generation Summary */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Generation Summary</h4>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {/* Processing Time */}
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-blue-50 flex items-center justify-center">
              <Clock className="w-6 h-6 text-blue-600" />
            </div>
            <div className="text-xl font-bold text-gray-900">
              {mergeStats?.processing_time ? `${mergeStats.processing_time.toFixed(1)}s` : 'N/A'}
            </div>
            <div className="text-sm text-gray-500">Processing Time</div>
          </div>

          {/* File Size */}
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-green-50 flex items-center justify-center">
              <HardDrive className="w-6 h-6 text-green-600" />
            </div>
            <div className="text-xl font-bold text-gray-900">
              {mergeStats?.file_size_mb ? `${mergeStats.file_size_mb.toFixed(1)} MB` : 'N/A'}
            </div>
            <div className="text-sm text-gray-500">File Size</div>
          </div>

          {/* Quality */}
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-purple-50 flex items-center justify-center">
              <div className="text-purple-600 font-bold">HD</div>
            </div>
            <div className="text-xl font-bold text-gray-900">1080p</div>
            <div className="text-sm text-gray-500">Quality</div>
          </div>

          {/* Sync Accuracy */}
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-orange-50 flex items-center justify-center">
              <Volume2 className="w-6 h-6 text-orange-600" />
            </div>
            <div className="text-xl font-bold text-gray-900">
              {mergeStats?.sync_accuracy || '95%'}
            </div>
            <div className="text-sm text-gray-500">Sync Accuracy</div>
          </div>
        </div>
      </div>

      {/* Quality Versions (if available) */}
      {generation.merge_data?.quality_versions && generation.merge_data.quality_versions.length > 1 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">Available Quality Versions</h4>
          <div className="space-y-3">
            {generation.merge_data.quality_versions.map((version: any, index: number) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <div className="font-medium text-gray-900">{version.quality}</div>
                  <div className="text-sm text-gray-600">
                    {version.resolution} • {version.file_size} MB
                  </div>
                </div>
                <a
                  href={version.video_url}
                  download={`video-${version.quality}.mp4`}
                  className="flex items-center gap-2 px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                  <Download className="w-3 h-3" />
                  Download
                </a>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Success Actions */}
      <div className="text-center py-4">
        <div className="flex items-center justify-center gap-2 text-green-600 mb-4">
          <CheckCircle className="w-5 h-5" />
          <span className="font-medium">Video generation completed successfully!</span>
        </div>
        <p className="text-sm text-gray-600">
          Your video is ready to download, share, or use in your projects.
        </p>
      </div>
    </div>
  );
};