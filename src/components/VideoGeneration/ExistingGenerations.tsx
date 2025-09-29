import React, { useState, useEffect } from "react";
import {
  Play,
  RotateCcw,
  Calendar,
  Clock,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import { toast } from "react-hot-toast";
import { PipelineStatus } from "./PipelineStatus";
import videoGenerationAPI from "../../lib/videoGenerationApi";

interface ExistingGenerationsProps {
  chapterId: string;
  onContinueGeneration: (videoGenId: string) => void;
  onWatchVideo: (videoUrl: string) => void;
  className?: string;
}

export const ExistingGenerations: React.FC<ExistingGenerationsProps> = ({
  chapterId,
  onContinueGeneration,
  onWatchVideo,
  className = "",
}) => {
  const [generations, setGenerations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedGeneration, setExpandedGeneration] = useState<string | null>(
    null
  );

  useEffect(() => {
    loadGenerations();
  }, [chapterId]);

  const loadGenerations = async () => {
    try {
      setLoading(true);
      const data = await videoGenerationAPI.getChapterVideoGenerations(
        chapterId
      );
      setGenerations(data.generations);
    } catch (error) {
      console.error("Failed to load generations:", error);
      toast.error("Failed to load video generations");
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-green-600 bg-green-50 border-green-200";
      case "failed":
        return "text-red-600 bg-red-50 border-red-200";
      case "generating_audio":
      case "generating_images":
      case "generating_video":
      case "merging_audio":
      case "applying_lipsync":
        return "text-blue-600 bg-blue-50 border-blue-200";
      case "pending":
        return "text-gray-600 bg-gray-50 border-gray-200";
      default:
        return "text-gray-600 bg-gray-50 border-gray-200";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-4 h-4" />;
      case "failed":
        return <AlertCircle className="w-4 h-4" />;
      case "generating_audio":
      case "generating_images":
      case "generating_video":
      case "merging_audio":
      case "applying_lipsync":
        return <Clock className="w-4 h-4 animate-spin" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const canResume = (generation: any) => {
    return (
      generation.can_resume ||
      (generation.pipeline_status && generation.pipeline_status.can_resume) ||
      generation.generation_status === "failed"
    );
  };

  if (loading) {
    return (
      <div className={`bg-white rounded-lg border p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-16 bg-gray-200 rounded"></div>
            <div className="h-16 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (generations.length === 0) {
    return (
      <div
        className={`bg-white rounded-lg border p-6 text-center ${className}`}
      >
        <Play className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No Video Generations
        </h3>
        <p className="text-gray-500">
          No video generations found for this chapter. Start by generating a
          script and creating your first video.
        </p>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border ${className}`}>
      <div className="p-6 border-b">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Video Generations
          </h3>
          <span className="text-sm text-gray-500">
            {generations.length} generation{generations.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      <div className="divide-y divide-gray-200">
        {generations.map((generation) => (
          <div key={generation.id} className="p-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-3">
                <div
                  className={`
                  flex items-center space-x-2 px-3 py-1 rounded-full text-sm font-medium border
                  ${getStatusColor(generation.generation_status)}
                `}
                >
                  {getStatusIcon(generation.generation_status)}
                  <span className="capitalize">
                    {generation.generation_status.replace(/_/g, " ")}
                  </span>
                </div>

                <div className="text-sm text-gray-500">
                  {generation.quality_tier} quality
                </div>

                {generation.retry_count > 0 && (
                  <div className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full">
                    {generation.retry_count} retries
                  </div>
                )}
              </div>

              <div className="flex items-center space-x-2">
                {/* Show video if completed */}
                {generation.generation_status === "completed" &&
                  generation.video_url && (
                    <button
                      onClick={() => onWatchVideo(generation.video_url)}
                      className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                    >
                      <Play className="w-3 h-3" />
                      <span>Watch</span>
                    </button>
                  )}

                {/* Show resume if failed or resumable */}
                {canResume(generation) && (
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => onContinueGeneration(generation.id)}
                      className="flex items-center space-x-1 px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span>Smart Resume</span>
                    </button>

                    {/* Show progress info */}
                    {generation.pipeline_status?.progress && (
                      <div className="text-xs text-gray-500">
                        (
                        {generation.pipeline_status.progress.percentage?.toFixed(
                          0
                        ) || 0}
                        % complete)
                      </div>
                    )}

                    {/* Show what exists */}
                    {(generation.audio_files ||
                      generation.image_data ||
                      generation.video_data) && (
                      <div className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
                        ✓ Has progress
                      </div>
                    )}
                  </div>
                )}

                {/* Toggle details */}
                <button
                  onClick={() =>
                    setExpandedGeneration(
                      expandedGeneration === generation.id
                        ? null
                        : generation.id
                    )
                  }
                  className="text-gray-400 hover:text-gray-600"
                >
                  {expandedGeneration === generation.id ? "▼" : "▶"}
                </button>
              </div>
            </div>

            {/* Generation Info */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
              <div>
                <span className="font-medium">Created:</span>
                <div className="flex items-center space-x-1">
                  <Calendar className="w-3 h-3" />
                  <span>{formatDate(generation.created_at)}</span>
                </div>
              </div>

              <div>
                <span className="font-medium">Script Style:</span>
                <div>{generation.script_data?.script_style || "Unknown"}</div>
              </div>

              <div>
                <span className="font-medium">Video Style:</span>
                <div>{generation.script_data?.video_style || "Unknown"}</div>
              </div>

              <div>
                <span className="font-medium">Progress:</span>
                <div>
                  {generation.pipeline_status
                    ? `${
                        generation.pipeline_status.progress?.percentage?.toFixed(
                          0
                        ) || 0
                      }%`
                    : "Unknown"}
                </div>
              </div>
            </div>

            {/* Error Message */}
            {generation.error_message && (
              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">
                  <strong>Error:</strong> {generation.error_message}
                </p>
              </div>
            )}

            {/* Expanded Details */}
            {expandedGeneration === generation.id &&
              generation.pipeline_status && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <PipelineStatus
                    pipelineStatus={generation.pipeline_status}
                    isLoading={false}
                    onRetry={() => onContinueGeneration(generation.id)}
                    className="border-none shadow-none p-0"
                  />
                </div>
              )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ExistingGenerations;
