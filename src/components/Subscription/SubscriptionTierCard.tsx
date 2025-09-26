import React from "react";
import { Check, Star } from "lucide-react";
import { SubscriptionTier } from "../../services/subscriptionService";

interface SubscriptionTierCardProps {
  tier: SubscriptionTier;
  currentTier?: string;
  onSelect: (tier: SubscriptionTier) => void;
  isLoading?: boolean;
}

export default function SubscriptionTierCard({
  tier,
  currentTier,
  onSelect,
  isLoading = false,
}: SubscriptionTierCardProps) {
  const isCurrentTier = currentTier === tier.tier;
  const isPopular = tier.tier === "pro"; // Mark pro as popular

  const getTierColor = (tierName: string) => {
    switch (tierName) {
      case "free":
        return "border-gray-200 bg-gray-50";
      case "basic":
        return "border-blue-200 bg-blue-50";
      case "pro":
        return "border-purple-200 bg-purple-50";
      default:
        return "border-gray-200 bg-gray-50";
    }
  };

  const getButtonColor = (tierName: string) => {
    switch (tierName) {
      case "free":
        return "bg-gray-600 hover:bg-gray-700";
      case "basic":
        return "bg-blue-600 hover:bg-blue-700";
      case "pro":
        return "bg-purple-600 hover:bg-purple-700";
      default:
        return "bg-gray-600 hover:bg-gray-700";
    }
  };

  return (
    <div
      className={`relative rounded-2xl border-2 p-6 transition-all hover:shadow-lg ${
        getTierColor(tier.tier)
      } ${isCurrentTier ? "ring-2 ring-purple-500" : ""}`}
    >
      {isPopular && (
        <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
          <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-1 rounded-full text-sm font-medium flex items-center gap-1">
            <Star className="h-3 w-3" />
            Most Popular
          </div>
        </div>
      )}

      {isCurrentTier && (
        <div className="absolute -top-3 right-4">
          <div className="bg-green-500 text-white px-3 py-1 rounded-full text-sm font-medium">
            Current Plan
          </div>
        </div>
      )}

      <div className="text-center mb-6">
        <h3 className="text-2xl font-bold text-gray-900 mb-2">
          {tier.display_name}
        </h3>
        <div className="flex items-center justify-center gap-1 mb-4">
          <span className="text-4xl font-bold text-gray-900">
            ${tier.monthly_price}
          </span>
          <span className="text-gray-600">/month</span>
        </div>
        {tier.description && (
          <p className="text-gray-600 text-sm">{tier.description}</p>
        )}
      </div>

      <div className="space-y-3 mb-6">
        <div className="flex items-center gap-3">
          <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
          <span className="text-sm text-gray-700">
            {tier.monthly_video_limit === -1
              ? "Unlimited videos"
              : `${tier.monthly_video_limit} videos per month`}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
          <span className="text-sm text-gray-700">
            {tier.video_quality} quality
          </span>
        </div>

        <div className="flex items-center gap-3">
          <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
          <span className="text-sm text-gray-700">
            {tier.has_watermark ? "Watermark included" : "No watermark"}
          </span>
        </div>

        {tier.max_video_duration && (
          <div className="flex items-center gap-3">
            <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
            <span className="text-sm text-gray-700">
              Up to {tier.max_video_duration} seconds per video
            </span>
          </div>
        )}

        {tier.priority_processing && (
          <div className="flex items-center gap-3">
            <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
            <span className="text-sm text-gray-700">Priority processing</span>
          </div>
        )}

        {/* Display additional features */}
        {tier.features &&
          Object.entries(tier.features).map(([key, value]) => (
            <div key={key} className="flex items-center gap-3">
              <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
              <span className="text-sm text-gray-700">
                {typeof value === "boolean" && value
                  ? key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())
                  : `${key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}: ${value}`}
              </span>
            </div>
          ))}
      </div>

      <button
        onClick={() => onSelect(tier)}
        disabled={isCurrentTier || isLoading}
        className={`w-full py-3 px-6 rounded-xl font-semibold text-white transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none ${
          getButtonColor(tier.tier)
        }`}
      >
        {isLoading ? (
          <div className="flex items-center justify-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            Processing...
          </div>
        ) : isCurrentTier ? (
          "Current Plan"
        ) : tier.tier === "free" ? (
          "Get Started"
        ) : (
          "Upgrade Now"
        )}
      </button>
    </div>
  );
}