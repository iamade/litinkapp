import React, { useEffect, useRef, useState } from "react";
import { Loader2, CheckCircle, AlertCircle, RefreshCw } from "lucide-react";
import { projectService, Project, ProjectUploadStatus } from "../../services/projectService";

const STAGES = [
  { key: "parsing", label: "Parsing Text" },
  { key: "structuring", label: "Structuring Chapters" },
  { key: "embeddings", label: "Generating AI Context" },
  { key: "finalizing", label: "Finalizing" },
];

// "uploading" is the implicit first stage (project shell just created)
const ALL_STAGES = [{ key: "uploading", label: "Uploading" }, ...STAGES];

function getStageIndex(stage: string | undefined): number {
  if (!stage) return 0;
  const idx = ALL_STAGES.findIndex((s) => s.key === stage);
  return idx === -1 ? 0 : idx;
}

interface UploadProgressProps {
  projectId: string;
  onComplete: (project: Project) => void;
  onError: (error: string) => void;
}

const UploadProgress: React.FC<UploadProgressProps> = ({
  projectId,
  onComplete,
  onError,
}) => {
  const [statusData, setStatusData] = useState<ProjectUploadStatus>({
    status: "processing",
    stage: "uploading",
    progress: 5,
  });
  const [networkError, setNetworkError] = useState(false);
  const pollIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const backoffRef = useRef(2500);
  const completedRef = useRef(false);

  const poll = async () => {
    try {
      const data = await projectService.getProjectUploadStatus(projectId);
      setStatusData(data);
      setNetworkError(false);
      backoffRef.current = 2500; // reset backoff on success

      if (data.status === "completed") {
        completedRef.current = true;
        if (data.project) {
          onComplete(data.project);
        }
        return;
      }

      if (data.status === "failed") {
        completedRef.current = true;
        return;
      }

      // Schedule next poll
      pollIntervalRef.current = setTimeout(poll, 2500);
    } catch {
      setNetworkError(true);
      // Exponential backoff on network errors
      const delay = Math.min(backoffRef.current * 2, 30000);
      backoffRef.current = delay;
      pollIntervalRef.current = setTimeout(poll, delay);
    }
  };

  useEffect(() => {
    pollIntervalRef.current = setTimeout(poll, 1000);
    return () => {
      if (pollIntervalRef.current) clearTimeout(pollIntervalRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const handleRetry = () => {
    onError(statusData.error || "Upload failed. Please try again.");
  };

  const currentStageIdx = getStageIndex(statusData.stage);
  const isFailed = statusData.status === "failed";
  const isCompleted = statusData.status === "completed";

  const progressBarColor = isFailed
    ? "bg-red-500"
    : isCompleted
    ? "bg-green-500"
    : "bg-purple-600";

  return (
    <div className="bg-white dark:bg-gray-800/50 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-700 p-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        {isFailed ? (
          <AlertCircle className="w-7 h-7 text-red-500 flex-shrink-0" />
        ) : isCompleted ? (
          <CheckCircle className="w-7 h-7 text-green-500 flex-shrink-0" />
        ) : (
          <Loader2 className="w-7 h-7 text-purple-600 animate-spin flex-shrink-0" />
        )}
        <div>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">
            {isFailed
              ? "Upload Failed"
              : isCompleted
              ? "Project Ready!"
              : "Processing Your Project"}
          </h3>
          {!isFailed && !isCompleted && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              This may take a minute for large files.
            </p>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
          <span>
            {statusData.stage === "embeddings" &&
            statusData.chapters_processed !== undefined &&
            statusData.total_chapters
              ? `Processing chapter ${statusData.chapters_processed} of ${statusData.total_chapters}`
              : ALL_STAGES[currentStageIdx]?.label ?? "Processing..."}
          </span>
          <span>{statusData.progress}%</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${progressBarColor}`}
            style={{ width: `${statusData.progress}%` }}
          >
            {!isFailed && !isCompleted && (
              <div className="h-full bg-white/20 animate-pulse" />
            )}
          </div>
        </div>
      </div>

      {/* Stage Stepper */}
      <div className="space-y-3 mb-6">
        {ALL_STAGES.map((stage, idx) => {
          const isDone = isCompleted || idx < currentStageIdx;
          const isActive = !isCompleted && idx === currentStageIdx;
          return (
            <div key={stage.key} className="flex items-center gap-3">
              <div
                className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                  isDone
                    ? "border-green-500 bg-green-500"
                    : isActive
                    ? "border-purple-600 bg-purple-600"
                    : "border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
                }`}
              >
                {isDone ? (
                  <svg
                    className="w-3 h-3 text-white"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                ) : isActive ? (
                  <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
                ) : null}
              </div>
              <span
                className={`text-sm ${
                  isDone
                    ? "text-gray-900 dark:text-white font-medium"
                    : isActive
                    ? "text-purple-700 dark:text-purple-300 font-medium"
                    : "text-gray-400 dark:text-gray-500"
                }`}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Network error notice */}
      {networkError && !isFailed && (
        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg mb-4">
          <p className="text-sm text-yellow-800 dark:text-yellow-300">
            Connection issue — retrying automatically...
          </p>
        </div>
      )}

      {/* Success message */}
      {isCompleted && (
        <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg">
          <p className="text-sm text-green-800 dark:text-green-300">
            Your project has been processed and is ready to use!
          </p>
        </div>
      )}

      {/* Error message + retry */}
      {isFailed && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-300 mb-3">
            {statusData.error || "An unexpected error occurred during processing."}
          </p>
          <button
            onClick={handleRetry}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>
        </div>
      )}
    </div>
  );
};

export default UploadProgress;
