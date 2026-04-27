import React from "react";
import { Video, AlertTriangle, CheckCircle, Coins } from "lucide-react";
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
  const hasCredits = usage.available_credits > 0;
  const isNearZero = usage.available_credits > 0 && usage.available_credits <= 5;
  const isOutOfCredits = usage.available_credits <= 0;

  const getCreditColor = () => {
    if (isOutOfCredits) return "text-red-600";
    if (isNearZero) return "text-yellow-600";
    return "text-green-600";
  };

  const getStatusIcon = () => {
    if (isOutOfCredits) return <AlertTriangle className="h-4 w-4 text-red-500" />;
    if (isNearZero) return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
    return <CheckCircle className="h-4 w-4 text-green-500" />;
  };

  const getStatusText = () => {
    if (isOutOfCredits) return "No credits remaining";
    if (isNearZero) return "Low credits";
    return "Credits available";
  };

  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Coins className="h-4 w-4 text-gray-600" />
        <span className="text-sm text-gray-700">
          {usage.available_credits} credits
        </span>
        {getStatusIcon()}
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Coins className="h-5 w-5 text-purple-600" />
          <h3 className="font-semibold text-gray-900">Credits</h3>
        </div>
        {getStatusIcon()}
      </div>

      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Available credits</span>
          <span className={`font-medium ${getCreditColor()}`}>
            {usage.available_credits}
          </span>
        </div>

        {usage.current_period_videos > 0 && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Videos this month</span>
            <span className="text-gray-700">{usage.current_period_videos}</span>
          </div>
        )}

        <div className="flex justify-between items-center">
          <span className={`text-sm font-medium ${getCreditColor()}`}>
            {getStatusText()}
          </span>
        </div>

        {usage.period_end && (
          <div className="text-xs text-gray-500 mt-2">
            Period ends {new Date(usage.period_end).toLocaleDateString()}
          </div>
        )}
      </div>

      {isOutOfCredits && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            <span className="text-sm text-red-700">
              You have no credits remaining. Purchase credits or upgrade to continue generating content.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}