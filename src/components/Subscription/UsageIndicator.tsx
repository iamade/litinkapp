import React from "react";
import { Video, AlertTriangle, CheckCircle } from "lucide-react";
import { SubscriptionUsageStats } from "../../services/subscriptionService";

interface UsageIndicatorProps {
  usage: SubscriptionUsageStats;
  className?: string;
  compact?: boolean;
}

export default function UsageIndicator({
  usage,
  className = "",
  compact = false,
}: UsageIndicatorProps) {
  const usagePercentage = (usage.current_period_videos / usage.period_limit) * 100;
  const isNearLimit = usagePercentage >= 80;
  const isAtLimit = usagePercentage >= 100;

  const getProgressColor = () => {
    if (isAtLimit) return "bg-red-500";
    if (isNearLimit) return "bg-yellow-500";
    return "bg-green-500";
  };

  const getStatusIcon = () => {
    if (isAtLimit) return <AlertTriangle className="h-4 w-4 text-red-500" />;
    if (isNearLimit) return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
    return <CheckCircle className="h-4 w-4 text-green-500" />;
  };

  const getStatusText = () => {
    if (isAtLimit) return "Limit reached";
    if (isNearLimit) return "Approaching limit";
    return "Within limits";
  };

  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Video className="h-4 w-4 text-gray-600" />
        <span className="text-sm text-gray-700">
          {usage.current_period_videos} / {usage.period_limit === -1 ? "∞" : usage.period_limit}
        </span>
        {getStatusIcon()}
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Video className="h-5 w-5 text-purple-600" />
          <h3 className="font-semibold text-gray-900">Video Usage</h3>
        </div>
        {getStatusIcon()}
      </div>

      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">This month</span>
          <span className="font-medium text-gray-900">
            {usage.current_period_videos} / {usage.period_limit === -1 ? "∞" : usage.period_limit}
          </span>
        </div>

        {usage.period_limit !== -1 && (
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${getProgressColor()}`}
              style={{ width: `${Math.min(usagePercentage, 100)}%` }}
            ></div>
          </div>
        )}

        <div className="flex justify-between items-center">
          <span className={`text-sm font-medium ${isAtLimit ? "text-red-600" : isNearLimit ? "text-yellow-600" : "text-green-600"}`}>
            {getStatusText()}
          </span>
          {usage.remaining_videos !== -1 && (
            <span className="text-sm text-gray-600">
              {usage.remaining_videos} remaining
            </span>
          )}
        </div>

        {usage.period_end && (
          <div className="text-xs text-gray-500 mt-2">
            Resets on {new Date(usage.period_end).toLocaleDateString()}
          </div>
        )}
      </div>

      {!usage.can_generate_video && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            <span className="text-sm text-red-700">
              You've reached your monthly video limit. Upgrade to continue generating videos.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}