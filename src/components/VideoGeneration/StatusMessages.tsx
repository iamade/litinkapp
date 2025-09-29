import React from 'react';
import { Mic, Image, Video, Music, Users, CheckCircle, AlertTriangle } from 'lucide-react';
import { useGenerationMessages } from '../../hooks/useVideoGenerationStatus';
import { GenerationStatus } from '../../lib/videoGenerationApi';

interface StatusMessagesProps {
  videoGenId?: string;
  showDetails?: boolean;
  className?: string;
}

export const StatusMessages: React.FC<StatusMessagesProps> = ({
  videoGenId,
  showDetails = true,
  className = ''
}) => {
  const { currentMessage, generation, status } = useGenerationMessages(videoGenId);

  const getStatusIcon = (currentStatus: GenerationStatus | null) => {
    const iconClass = "w-5 h-5 flex-shrink-0";
    
    switch (currentStatus) {
      case 'generating_audio':
      case 'audio_completed':
        return <Mic className={`${iconClass} text-blue-500`} />;
      case 'generating_images':
      case 'images_completed':
        return <Image className={`${iconClass} text-green-500`} />;
      case 'generating_video':
      case 'video_completed':
        return <Video className={`${iconClass} text-purple-500`} />;
      case 'merging_audio':
        return <Music className={`${iconClass} text-orange-500`} />;
      case 'applying_lipsync':
      case 'lipsync_completed':
        return <Users className={`${iconClass} text-pink-500`} />;
      case 'completed':
        return <CheckCircle className={`${iconClass} text-green-600`} />;
      case 'failed':
      case 'lipsync_failed':
        return <AlertTriangle className={`${iconClass} text-red-500`} />;
      default:
        return <div className={`${iconClass} bg-gray-300 rounded-full animate-pulse`} />;
    }
  };

  const getDetailedProgress = () => {
    if (!generation || !showDetails) return null;

    const details = [];
    
    // Audio progress details
    if (generation.audio_progress) {
      const audio = generation.audio_progress;
      const totalFiles = audio.narrator_files + audio.character_files + audio.sound_effects + audio.background_music;
      if (totalFiles > 0) {
        details.push({
          label: 'Audio Files Generated',
          value: totalFiles,
          breakdown: [
            { label: 'Narrator', count: audio.narrator_files },
            { label: 'Characters', count: audio.character_files },
            { label: 'Sound Effects', count: audio.sound_effects },
            { label: 'Background Music', count: audio.background_music }
          ].filter(item => item.count > 0)
        });
      }
    }

    // Image progress details
    if (generation.image_progress) {
      const images = generation.image_progress;
      details.push({
        label: 'Character Images',
        value: `${images.characters_completed}/${images.total_characters}`,
        progress: images.total_characters > 0 ? (images.characters_completed / images.total_characters) * 100 : 0
      });
      
      if (images.scenes_completed > 0) {
        details.push({
          label: 'Scene Images',
          value: `${images.scenes_completed}/${images.total_scenes}`,
          progress: images.total_scenes > 0 ? (images.scenes_completed / images.total_scenes) * 100 : 0
        });
      }
    }

    // Video progress details
    if (generation.video_progress) {
      const video = generation.video_progress;
      details.push({
        label: 'Video Scenes',
        value: `${video.scenes_completed}/${video.total_scenes}`,
        progress: video.total_scenes > 0 ? (video.scenes_completed / video.total_scenes) * 100 : 0,
        extra: video.success_rate > 0 ? `${Math.round(video.success_rate)}% success rate` : undefined
      });
    }

    // Merge progress details
    if (generation.merge_progress) {
      const merge = generation.merge_progress;
      if (merge.total_duration > 0) {
        details.push({
          label: 'Video Duration',
          value: `${merge.total_duration.toFixed(1)} seconds`,
          extra: `${merge.file_size_mb.toFixed(1)} MB`
        });
      }
    }

    // Lip sync progress details
    if (generation.lipsync_progress) {
      const lipSync = generation.lipsync_progress;
      if (lipSync.characters_lip_synced > 0) {
        details.push({
          label: 'Characters with Lip Sync',
          value: lipSync.characters_lip_synced,
          extra: `${lipSync.scenes_processed} scenes processed`
        });
      }
    }

    return details;
  };

  if (!status) return null;

  const progressDetails = getDetailedProgress();

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Main Status Message */}
      <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
        {getStatusIcon(status)}
        <div className="flex-1">
          <p className="font-medium text-gray-900">{currentMessage}</p>
          {generation?.error_message && (
            <p className="text-sm text-red-600 mt-1">{generation.error_message}</p>
          )}
        </div>
        {status && !['completed', 'failed', 'lipsync_failed'].includes(status) && (
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse delay-75"></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse delay-150"></div>
          </div>
        )}
      </div>

      {/* Detailed Progress */}
      {progressDetails && progressDetails.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-700">Progress Details</h4>
          <div className="space-y-2">
            {progressDetails.map((detail, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">{detail.label}</span>
                    <span className="text-sm font-semibold text-gray-900">{detail.value}</span>
                  </div>
                  {detail.extra && (
                    <p className="text-xs text-gray-500 mt-1">{detail.extra}</p>
                  )}
                  {detail.progress !== undefined && (
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div
                          className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                          style={{ width: `${Math.min(100, Math.max(0, detail.progress))}%` }}
                        />
                      </div>
                    </div>
                  )}
                  {detail.breakdown && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {detail.breakdown.map((item, i) => (
                        <span key={i} className="text-xs bg-gray-100 px-2 py-1 rounded">
                          {item.label}: {item.count}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Simplified status message component for inline use
export const InlineStatusMessage: React.FC<{ videoGenId?: string }> = ({ videoGenId }) => {
  const { currentMessage, status } = useGenerationMessages(videoGenId);
  
  if (!status || !currentMessage) return null;
  
  return (
    <div className="flex items-center gap-2 text-sm text-gray-600">
      <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
      {currentMessage}
    </div>
  );
};