import React, { useState } from "react";
import { Check, Star } from "lucide-react";
import { SubscriptionTier } from "../../services/subscriptionService";

interface TierFeatures {
  max_file_size_mb?: number;
  support_level?: string;
  export_formats?: string[];
  custom_voices?: boolean;
  api_access?: boolean;
  team_collaboration?: boolean;
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

        {/* Billing Period Toggle */}
        {tier.tier !== "free" && (
          <div className="flex items-center justify-center bg-gray-100 rounded-lg p-1 mb-4 max-w-fit mx-auto">
            <button
              onClick={() => setBillingPeriod('monthly')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                billingPeriod === 'monthly'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingPeriod('annual')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                billingPeriod === 'annual'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Annual
              <span className="ml-1 text-xs bg-green-100 text-green-700 px-1 py-0.5 rounded">
                Save 20%
              </span>
            </button>
          </div>
        )}

        <div className="flex items-center justify-center gap-1 mb-4">
          <span className="text-4xl font-bold text-gray-900">
            ${displayPrice}
          </span>
          <span className="text-gray-600">{periodLabel}</span>
        </div>
        {tier.description && (
          <p className="text-gray-600 text-sm">{tier.description}</p>
        )}
      </div>

      <div className="space-y-4 mb-6">
        {/* Video Generation Limits */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">Video Generation</h4>
          <div className="flex items-center gap-3">
            <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
            <span className="text-sm text-gray-700">
              {tier.monthly_video_limit === -1
                ? "Unlimited video generations per month"
                : `${tier.monthly_video_limit} video${tier.monthly_video_limit !== 1 ? 's' : ''} per month`}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
            <span className="text-sm text-gray-700">
              {tier.video_quality} video resolution for crisp, professional output
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
            <span className="text-sm text-gray-700">
              {tier.has_watermark ? "Watermark-free videos" : "No watermark on your content"}
            </span>
          </div>

          {tier.max_video_duration && (
            <div className="flex items-center gap-3">
              <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
              <span className="text-sm text-gray-700">
                Videos up to {tier.max_video_duration} seconds in length
              </span>
            </div>
          )}

          {tier.priority_processing && (
            <div className="flex items-center gap-3">
              <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
              <span className="text-sm text-gray-700">
                Priority processing - your videos are generated faster
              </span>
            </div>
          )}
        </div>

        {/* File and Export Features */}
        {tier.features && Object.keys(tier.features).length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">File & Export Options</h4>
            {(tier.features as TierFeatures).max_file_size_mb && (
              <div className="flex items-center gap-3">
                <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
                <span className="text-sm text-gray-700">
                  Upload files up to {(tier.features as TierFeatures).max_file_size_mb}MB
                </span>
              </div>
            )}

            {(tier.features as TierFeatures).export_formats && Array.isArray((tier.features as TierFeatures).export_formats) && (
              <div className="flex items-center gap-3">
                <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
                <span className="text-sm text-gray-700">
                  Export in {(tier.features as TierFeatures).export_formats!.join(', ').toUpperCase()} formats
                </span>
              </div>
            )}
          </div>
        )}

        {/* Voice and Audio Features */}
        {tier.features && ((tier.features as TierFeatures).custom_voices) && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">Voice & Audio</h4>
            {(tier.features as TierFeatures).custom_voices && (
              <div className="flex items-center gap-3">
                <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
                <span className="text-sm text-gray-700">
                  Access to premium voice library and custom voice options
                </span>
              </div>
            )}
          </div>
        )}

        {/* Advanced Features */}
        {tier.features && ((tier.features as TierFeatures).api_access || (tier.features as TierFeatures).team_collaboration) && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">Advanced Features</h4>
            {(tier.features as TierFeatures).api_access && (
              <div className="flex items-center gap-3">
                <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
                <span className="text-sm text-gray-700">
                  API access for programmatic video generation
                </span>
              </div>
            )}

            {(tier.features as TierFeatures).team_collaboration && (
              <div className="flex items-center gap-3">
                <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
                <span className="text-sm text-gray-700">
                  Team collaboration tools and shared workspaces
                </span>
              </div>
            )}
          </div>
        )}

        {/* Support */}
        {tier.features && (tier.features as TierFeatures).support_level && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">Support</h4>
            <div className="flex items-center gap-3">
              <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
              <span className="text-sm text-gray-700">
                {(tier.features as TierFeatures).support_level === 'priority' && 'Priority email support with fast response times'}
                {(tier.features as TierFeatures).support_level === 'email' && 'Email support for assistance'}
                {(tier.features as TierFeatures).support_level === 'community' && 'Community forum access and documentation'}
              </span>
            </div>
          </div>
        )}
      </div>

      <button
        onClick={() => onSelect(tier, billingPeriod)}
        disabled={isCurrentTier || isLoading || tier.tier === "pro"}
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
        ) : tier.tier === "pro" ? (
          "Coming Soon"
        ) : (
          "Upgrade Now"
        )}
      </button>
    </div>
  );
}