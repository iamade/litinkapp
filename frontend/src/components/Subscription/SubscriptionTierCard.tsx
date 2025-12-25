import { useState } from "react";
import { Check, Star } from "lucide-react";
import { SubscriptionTier } from "../../services/subscriptionService";

interface TierFeatures {
  max_file_size_mb?: number;
  support_level?: string;
  export_formats?: string[];
  custom_voices?: boolean;
  api_access?: boolean;
  team_collaboration?: boolean;
  books_upload_limit?: number;
  video_books_limit?: number;
  chapters_per_book?: number | string;
  model_selection?: boolean;
  voice_cloning?: boolean;
}

interface SubscriptionTierCardProps {
  tier: SubscriptionTier;
  currentTier?: string;
  onSelect: (tier: SubscriptionTier, billingPeriod: 'monthly' | 'annual') => void;
  isLoading?: boolean;
}

export default function SubscriptionTierCard({
  tier,
  currentTier,
  onSelect,
  isLoading = false,
}: SubscriptionTierCardProps) {
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'annual'>('monthly');
  const isCurrentTier = currentTier === tier.tier;
  const isPopular = tier.tier === "pro"; // Mark pro as popular

  const annualPrice = Math.round(tier.monthly_price * 12 * 0.8); // 20% discount for annual
  const displayPrice = billingPeriod === 'monthly' ? tier.monthly_price : annualPrice;
  const periodLabel = billingPeriod === 'monthly' ? '/month' : '/year';

  const getTierColor = (tierName: string) => {
    switch (tierName) {
      case "free":
        return "border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50";
      case "basic":
        return "border-blue-200 dark:border-blue-900/50 bg-blue-50 dark:bg-blue-900/20";
      case "pro":
        return "border-purple-200 dark:border-purple-900/50 bg-purple-50 dark:bg-purple-900/20";
      case "team":
        return "border-pink-200 dark:border-pink-900/50 bg-pink-50 dark:bg-pink-900/20";
      default:
        return "border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50";
    }
  };

  const getButtonColor = (tierName: string) => {
    switch (tierName) {
      case "free":
        return "bg-gray-600 hover:bg-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600";
      case "basic":
        return "bg-blue-600 hover:bg-blue-700";
      case "pro":
        return "bg-purple-600 hover:bg-purple-700";
      case "team":
        return "bg-pink-600 hover:bg-pink-700";
      default:
        return "bg-gray-600 hover:bg-gray-700";
    }
  };

  return (
    <div
      className={`relative rounded-2xl border-2 p-6 transition-all hover:shadow-lg dark:hover:shadow-purple-900/20 ${
        getTierColor(tier.tier)
      } ${isCurrentTier ? "ring-2 ring-purple-500" : ""}`}
    >
      {isPopular && (
        <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
          <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-1 rounded-full text-sm font-medium flex items-center gap-1 shadow-lg">
            <Star className="h-3 w-3" />
            Most Popular
          </div>
        </div>
      )}

      {isCurrentTier && (
        <div className="absolute -top-3 right-4">
          <div className="bg-green-500 text-white px-3 py-1 rounded-full text-sm font-medium shadow-lg">
            Current Plan
          </div>
        </div>
      )}

      <div className="text-center mb-6">
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2 capitalize">
          {tier.display_name}
        </h3>

        {/* Billing Period Toggle */}
        {tier.tier !== "free" && (
          <div className="flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-lg p-1 mb-4 max-w-fit mx-auto">
            <button
              onClick={() => setBillingPeriod('monthly')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                billingPeriod === 'monthly'
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingPeriod('annual')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                billingPeriod === 'annual'
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Annual
              <span className="ml-1 text-xs bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 px-1 py-0.5 rounded">
                -20%
              </span>
            </button>
          </div>
        )}

        <div className="flex items-center justify-center gap-1 mb-4">
          <span className="text-4xl font-bold text-gray-900 dark:text-white">
            ${displayPrice}
          </span>
          <span className="text-gray-600 dark:text-gray-400">{periodLabel}</span>
        </div>
        {tier.description && (
          <p className="text-gray-600 dark:text-gray-400 text-sm">{tier.description}</p>
        )}
      </div>

      <div className="space-y-4 mb-6">
        {/* Video Generation Limits */}
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-gray-900 dark:text-gray-200 uppercase tracking-wide opacity-70">Video Generation</h4>
          <div className="flex items-center gap-3">
            <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {tier.monthly_video_limit === -1
                ? "Unlimited video generations per month"
                : `${tier.monthly_video_limit} video${tier.monthly_video_limit !== 1 ? 's' : ''} per month`}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {tier.video_quality} video resolution
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {tier.has_watermark ? "Videos include watermark" : "No watermark"}
            </span>
          </div>

          {tier.max_video_duration && (
            <div className="flex items-center gap-3">
              <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
              <span className="text-sm text-gray-700 dark:text-gray-300">
               Max {Math.round(tier.max_video_duration / 60)} mins per video
              </span>
            </div>
          )}

          {tier.priority_processing && (
            <div className="flex items-center gap-3">
              <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                🚀 Priority processing
              </span>
            </div>
          )}
        </div>

        {/* Book & Content Limits */}
        {tier.features && (
          <div className="space-y-2">
             <h4 className="text-xs font-semibold text-gray-900 dark:text-gray-200 uppercase tracking-wide opacity-70">Content Limits</h4>
            {(tier.features as TierFeatures).books_upload_limit && (
              <div className="flex items-center gap-3">
                <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Upload up to {(tier.features as TierFeatures).books_upload_limit} books
                </span>
              </div>
            )}
            {(tier.features as TierFeatures).chapters_per_book && (
              <div className="flex items-center gap-3">
                <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {(tier.features as TierFeatures).chapters_per_book === 'unlimited' 
                    ? 'All chapters included' 
                    : `${(tier.features as TierFeatures).chapters_per_book} chapters/book`}
                </span>
              </div>
            )}
          </div>
        )}

        {/* AI Features */}
        {tier.features && ((tier.features as TierFeatures).model_selection || (tier.features as TierFeatures).voice_cloning) && (
          <div className="space-y-2">
             <h4 className="text-xs font-semibold text-gray-900 dark:text-gray-200 uppercase tracking-wide opacity-70">AI Features</h4>
            {(tier.features as TierFeatures).model_selection && (
              <div className="flex items-center gap-3">
                <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Select AI Model
                </span>
              </div>
            )}
            {(tier.features as TierFeatures).voice_cloning && (
              <div className="flex items-center gap-3">
                <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Voice cloning included
                </span>
              </div>
            )}
            {(tier.features as TierFeatures).custom_voices && (
               <div className="flex items-center gap-3">
                <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Premium voice library
                </span>
              </div>
            )}
          </div>
        )}

        <div className="pt-4 mt-auto">
             <button
              onClick={() => onSelect(tier, billingPeriod)}
              disabled={isCurrentTier || isLoading}
              className={`w-full py-3 px-6 rounded-xl font-semibold text-white transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none shadow-md ${
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
      </div>
    </div>
  );
}