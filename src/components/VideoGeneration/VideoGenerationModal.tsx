import React, { useState, useEffect } from "react";
import { X, AlertCircle } from "lucide-react";
import {
  useVideoGeneration,
} from "../../contexts/VideoGenerationContext";
import { useVideoGenerationStatus } from "../../hooks/useVideoGenerationStatus";
import { QualityTierSelector } from "./QualityTierSelector";
import { ProgressIndicators } from "./ProgressIndicators";
import { AudioGenerationStep } from "./steps/AudioGenerationStep";
import { ImageGenerationStep } from "./steps/ImageGenerationStep";
import { VideoGenerationStep } from "./steps/VideoGenerationStep";
import { MergeStep } from "./steps/MergeStep";
import { LipSyncStep } from "./steps/LipSyncStep";
import { CompletedStep } from "./steps/CompletedStep";
import { GenerationStatus } from "../../lib/videoGenerationApi";

interface VideoGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  scriptId: string;
  chapterId: string;
  initialQualityTier?: "free" | "premium" | "professional";
}

export const VideoGenerationModal: React.FC<VideoGenerationModalProps> = ({
  isOpen,
  onClose,
  scriptId,
  chapterId,
  initialQualityTier = "free",
}) => {
  const { state, startGeneration, resetGeneration, clearError } =
    useVideoGeneration();
  const {
    status,
    progress
  } = useVideoGenerationStatus(state.currentGeneration?.id);

  const [selectedQualityTier, setSelectedQualityTier] = useState<
    "free" | "premium" | "professional"
  >(initialQualityTier);
  const [hasStarted, setHasStarted] = useState(false);

  // Reset when modal opens/closes
  useEffect(() => {
    if (isOpen && !hasStarted) {
      resetGeneration();
      clearError();
    }
    if (!isOpen) {
      setHasStarted(false);
    }
  }, [isOpen, hasStarted, resetGeneration, clearError]);

  const handleStartGeneration = async () => {
    try {
      await startGeneration(scriptId, chapterId, selectedQualityTier);
      setHasStarted(true);
    } catch (error) {
      console.error("Failed to start generation:", error);
    }
  };

  const handleClose = () => {
    if (state.isGenerating) {
      const confirmClose = window.confirm(
        "Video generation is in progress. Are you sure you want to close?"
      );
      if (!confirmClose) return;
    }
    onClose();
  };

  const getCurrentStepNumber = (status: GenerationStatus | null): number => {
    if (!status) return 0;
    switch (status) {
      case "generating_audio":
      case "audio_completed":
        return 1;
      case "generating_images":
      case "images_completed":
        return 2;
      case "generating_video":
      case "video_completed":
        return 3;
      case "merging_audio":
        return 4;
      case "applying_lipsync":
      case "lipsync_completed":
        return 5;
      case "completed":
        return 6;
      case "failed":
      case "lipsync_failed":
        return -1;
      default:
        return 0;
    }
  };

  const renderCurrentStep = () => {
    if (!hasStarted || !status) {
      return (
        <QualityTierSelector
          selectedTier={selectedQualityTier}
          onSelect={setSelectedQualityTier}
          onStartGeneration={handleStartGeneration}
          scriptId={scriptId}
        />
      );
    }

    switch (status) {
      case "generating_audio":
      case "audio_completed":
        return <AudioGenerationStep />;
      case "generating_images":
      case "images_completed":
        return <ImageGenerationStep />;
      case "generating_video":
      case "video_completed":
        return <VideoGenerationStep />;
      case "merging_audio":
        return <MergeStep />;
      case "applying_lipsync":
      case "lipsync_completed":
        return <LipSyncStep />;
      case "completed":
        return <CompletedStep />;
      case "failed":
      case "lipsync_failed":
        return (
          <div className="text-center py-8">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-red-600 mb-2">
              Generation Failed
            </h3>
            <p className="text-gray-600 mb-4">
              {state.error || "An error occurred during video generation"}
            </p>
            <button
              onClick={() => {
                resetGeneration();
                setHasStarted(false);
              }}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        );
      default:
        return null;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              {hasStarted ? "Generating Video" : "Generate Video"}
            </h2>
            <p className="text-gray-600 mt-1">
              {hasStarted
                ? "Please wait while we create your video..."
                : "Choose your quality tier and start generation"}
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-gray-500" />
          </button>
        </div>

        {/* Progress Indicators */}
        {hasStarted && (
          <div className="p-6 border-b border-gray-200">
            <ProgressIndicators
              currentStep={getCurrentStepNumber(status)}
              overallProgress={progress?.overall || 0}
              status={status}
              stepProgress={progress?.stepProgress}
              currentStepName={progress?.currentStep}
            />
          </div>
        )}

        {/* Error Display */}
        {state.error && (
          <div className="p-4 mx-6 mt-6 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <h4 className="text-red-800 font-medium">Generation Error</h4>
                <p className="text-red-700 text-sm mt-1">{state.error}</p>
                
                {/* Actionable error suggestions */}
                {state.error.toLowerCase().includes('generation_failed') && (
                  <div className="mt-2 p-2 bg-red-100 rounded text-xs text-red-800">
                    <strong>Suggested Action:</strong> Try generating with a shorter script or different quality tier.
                  </div>
                )}
                
                {state.error.toLowerCase().includes('timeout') && (
                  <div className="mt-2 p-2 bg-orange-100 rounded text-xs text-orange-800">
                    <strong>Suggested Action:</strong> This can happen with longer videos. Try a shorter version first.
                  </div>
                )}
                
                {state.error.toLowerCase().includes('retrieval') && (
                  <div className="mt-2 p-2 bg-blue-100 rounded text-xs text-blue-800">
                    <strong>Suggested Action:</strong> The system is automatically trying alternative methods. Please wait.
                  </div>
                )}
              </div>
              <button
                onClick={clearError}
                className="p-1 hover:bg-red-100 rounded transition-colors"
              >
                <X className="w-4 h-4 text-red-500" />
              </button>
            </div>
            
            {/* Retry button for errors */}
            <div className="mt-3 flex gap-2">
              <button
                onClick={() => {
                  clearError();
                  resetGeneration();
                  setHasStarted(false);
                }}
                className="px-4 py-2 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
              >
                Start Over
              </button>
              <button
                onClick={() => {
                  clearError();
                  handleStartGeneration();
                }}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
              >
                Retry Generation
              </button>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="p-6 min-h-[400px]">{renderCurrentStep()}</div>

        {/* Footer with enhanced status */}
        {hasStarted && (
          <div className="p-6 border-t border-gray-200 bg-gray-50 rounded-b-xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {/* Status indicator with dynamic color */}
                <div className={`w-3 h-3 rounded-full ${
                  state.error ? 'bg-red-500' :
                  status === 'completed' ? 'bg-green-500' :
                  'bg-blue-500 animate-pulse'
                }`} />
                
                <div className="text-sm">
                  {state.error ? (
                    <span className="text-red-600 font-medium">Generation Failed</span>
                  ) : status === 'completed' ? (
                    <span className="text-green-600 font-medium">Generation Complete</span>
                  ) : (
                    <span className="text-blue-600">Processing... This may take several minutes.</span>
                  )}
                </div>
              </div>
              
              <div className="text-sm text-gray-500">
                Last updated:{" "}
                {state.lastUpdated?.toLocaleTimeString() || "Never"}
              </div>
            </div>
            
            {/* Additional status info for polling */}
            {status === 'generating_video' && state.currentGeneration && (
              <div className="mt-2 text-xs text-gray-600">
                Polling for video completion - Scene {state.currentGeneration.video_progress?.scenes_completed || 0} of {state.currentGeneration.video_progress?.total_scenes || 0}
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        {hasStarted &&
          status &&
          !["completed", "failed", "lipsync_failed"].includes(status) && (
            <div className="p-6 border-t border-gray-200 bg-gray-50 rounded-b-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  Processing... This may take several minutes.
                </div>
                <div className="text-sm text-gray-500">
                  Last updated:{" "}
                  {state.lastUpdated?.toLocaleTimeString() || "Never"}
                </div>
              </div>
            </div>
          )}
      </div>
    </div>
  );
};
