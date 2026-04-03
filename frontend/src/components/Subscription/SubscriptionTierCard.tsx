import { useState } from "react";
import { Check, Star, Zap } from "lucide-react";
import { SubscriptionTier } from "../../services/subscriptionService";

interface TierFeatures {
  max_file_size_mb?: number;
  support_level?: string;
  export_formats?: string[];
  custom_voices?: boolean;
  api_access?: boolean;
  team_collaboration?: boolean;
  books_upload_limit?: number | string;
  video_books_limit?: number;
  chapters_per_book?: number | string;
  model_selection?: boolean;
  voice_cloning?: boolean;
  images_per_month?: number | string;
  audio_per_month?: number | string;
  scripts_per_month?: number | string;
  plots_per_month?: number | string;
  ai_assists_per_month?: number | string;
  videos_per_month?: number | string;
  max_resolution?: string;
  watermark?: boolean;
  priority?: number;
  support?: string;
  price_monthly?: number;
}

interface SubscriptionTierCardProps {
  tier: SubscriptionTier;
  currentTier?: string;
  onSelect: (tier: SubscriptionTier, billingPeriod: "monthly" | "annual") => void;
  isLoading?: boolean;
  compact?: boolean;
}

// Credit estimates per tier (matches backend TIER_LIMITS)
const TIER_CREDITS: Record<string, { label: string; amount: string }> = {
  free: { label: "Credits included", amount: "100" },
  basic: { label: "Credits/month", amount: "1,500" },
  pro: { label: "Credits/month", amount: "5,000" },
  premium: { label: "Credits/month", amount: "15,000" },
  professional: { label: "Credits/month", amount: "50,000" },
  enterprise: { label: "Credits", amount: "Unlimited" },
};

export default function SubscriptionTierCard({
  tier,
  currentTier,
  onSelect,
  isLoading = false,
  compact = false,
}: SubscriptionTierCardProps) {
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "annual">("monthly");
  const isCurrentTier = currentTier === tier.tier;
  const isPopular = tier.tier === "pro";
  const isEnterprise = tier.tier === "enterprise";

  const annualPrice = Math.round(tier.monthly_price * 12 * 0.8);
  const displayPrice = billingPeriod === "monthly" ? tier.monthly_price : annualPrice;
  const periodLabel = billingPeriod === "monthly" ? "/mo" : "/yr";

  const credits = TIER_CREDITS[tier.tier] || { label: "Credits", amount: "—" };

  const getTierColor = (tierName: string) => {
    switch (tierName) {
      case "free":
        return "border-gray-200 dark:border-gray-700";
      case "basic":
        return "border-blue-200 dark:border-blue-800";
      case "pro":
        return "border-purple-400 dark:border-purple-600 ring-1 ring-purple-200 dark:ring-purple-800";
      case "premium":
        return "border-amber-200 dark:border-amber-800";
      case "professional":
        return "border-rose-200 dark:border-rose-800";
      case "enterprise":
        return "border-indigo-200 dark:border-indigo-800";
      default:
        return "border-gray-200 dark:border-gray-700";
    }
  };

  const getButtonStyle = (tierName: string) => {
    if (tierName === "pro") {
      return "bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white shadow-lg shadow-purple-500/25";
    }
    if (tierName === "enterprise") {
      return "bg-indigo-600 hover:bg-indigo-700 text-white";
    }
    return "bg-gray-900 dark:bg-white hover:bg-gray-800 dark:hover:bg-gray-100 text-white dark:text-gray-900";
  };

  const getAccentColor = (tierName: string) => {
    switch (tierName) {
      case "free": return "text-gray-600 dark:text-gray-400";
      case "basic": return "text-blue-600 dark:text-blue-400";
      case "pro": return "text-purple-600 dark:text-purple-400";
      case "premium": return "text-amber-600 dark:text-amber-400";
      case "professional": return "text-rose-600 dark:text-rose-400";
      case "enterprise": return "text-indigo-600 dark:text-indigo-400";
      default: return "text-gray-600 dark:text-gray-400";
    }
  };

  const features = tier.features as TierFeatures;

  // Build feature list
  const featureList: string[] = [];

  // Credits (most important)
  featureList.push(`${credits.amount} credits${tier.tier === "free" ? "" : "/month"}`);

  // Generation limits
  if (features?.videos_per_month) {
    featureList.push(
      features.videos_per_month === "unlimited"
        ? "Unlimited video generations"
        : `${features.videos_per_month} video generations/mo`
    );
  }
  if (features?.images_per_month) {
    featureList.push(
      features.images_per_month === "unlimited"
        ? "Unlimited image generations"
        : `${features.images_per_month} image generations/mo`
    );
  }
  if (features?.audio_per_month) {
    featureList.push(
      features.audio_per_month === "unlimited"
        ? "Unlimited audio generations"
        : `${features.audio_per_month} audio generations/mo`
    );
  }

  // Resolution
  if (features?.max_resolution) {
    featureList.push(`${features.max_resolution} resolution`);
  }

  // Watermark + download policy (updated)
  if (tier.tier === "free") {
    featureList.push("Watermark on by default");
    featureList.push("No individual asset downloads");
  } else {
    featureList.push("Watermark on by default");
    featureList.push("Remove watermark at download");
  }

  // Books
  if (features?.books_upload_limit) {
    featureList.push(
      features.books_upload_limit === "unlimited"
        ? "Unlimited book uploads"
        : `${features.books_upload_limit} book uploads`
    );
  }

  // AI features
  if (features?.model_selection) featureList.push("AI model selection");
  if (features?.voice_cloning) featureList.push("Voice cloning");
  if (features?.api_access) featureList.push("API access");

  // Priority
  if (features?.priority && features.priority >= 2) {
    featureList.push("Priority processing");
  }

  // Support
  if (features?.support === "dedicated_rep" || features?.support === "24/7_dedicated") {
    featureList.push("Dedicated support");
  } else if (features?.support === "priority_email") {
    featureList.push("Priority email support");
  }

  return (
    <div
      className={`relative rounded-2xl border-2 bg-white dark:bg-gray-800/50 p-6 transition-all hover:shadow-xl dark:hover:shadow-purple-900/10 flex flex-col ${getTierColor(
        tier.tier
      )} ${isCurrentTier ? "ring-2 ring-green-500" : ""}`}
    >
      {/* Badges */}
      {isPopular && !isCurrentTier && (
        <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
          <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-1 rounded-full text-xs font-bold flex items-center gap-1 shadow-lg uppercase tracking-wide">
            <Star className="h-3 w-3" />
            Most Popular
          </div>
        </div>
      )}

      {isCurrentTier && (
        <div className="absolute -top-3 right-4">
          <div className="bg-green-500 text-white px-3 py-1 rounded-full text-xs font-bold shadow-lg uppercase tracking-wide">
            Current Plan
          </div>
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white capitalize">
          {tier.display_name}
        </h3>
        {tier.description && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {tier.description}
          </p>
        )}
      </div>

      {/* Price */}
      <div className="mb-6">
        {isEnterprise ? (
          <div>
            <span className="text-3xl font-bold text-gray-900 dark:text-white">
              Custom
            </span>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Tailored to your needs
            </p>
          </div>
        ) : (
          <>
            {/* Billing Toggle */}
            {tier.tier !== "free" && (
              <div className="flex items-center bg-gray-100 dark:bg-gray-700/50 rounded-lg p-0.5 mb-3 w-fit">
                <button
                  onClick={() => setBillingPeriod("monthly")}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    billingPeriod === "monthly"
                      ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm"
                      : "text-gray-500 dark:text-gray-400"
                  }`}
                >
                  Monthly
                </button>
                <button
                  onClick={() => setBillingPeriod("annual")}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    billingPeriod === "annual"
                      ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm"
                      : "text-gray-500 dark:text-gray-400"
                  }`}
                >
                  Annual
                  <span className="ml-1 text-[10px] text-green-600 dark:text-green-400 font-bold">
                    -20%
                  </span>
                </button>
              </div>
            )}

            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-bold text-gray-900 dark:text-white">
                ${displayPrice}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {tier.tier === "free" ? "" : periodLabel}
              </span>
            </div>
          </>
        )}
      </div>

      {/* Credits Highlight */}
      <div className={`flex items-center gap-2 mb-6 px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-700/30 border border-gray-100 dark:border-gray-700`}>
        <Zap className={`h-4 w-4 flex-shrink-0 ${getAccentColor(tier.tier)}`} />
        <div>
          <span className={`text-lg font-bold ${getAccentColor(tier.tier)}`}>
            {credits.amount}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400 ml-1.5">
            {credits.label}
          </span>
        </div>
      </div>

      {/* Features */}
      <div className="space-y-2.5 mb-6 flex-1">
        {featureList.slice(1).map((feature, index) => (
          <div key={index} className="flex items-start gap-2.5">
            <Check className="h-4 w-4 text-green-500 dark:text-green-400 flex-shrink-0 mt-0.5" />
            <span className="text-sm text-gray-600 dark:text-gray-300">
              {feature}
            </span>
          </div>
        ))}
      </div>

      {/* CTA Button */}
      <button
        onClick={() => {
          if (isEnterprise) {
            window.location.href = "mailto:sales@litink.ai?subject=Enterprise%20Plan%20Inquiry";
            return;
          }
          onSelect(tier, billingPeriod);
        }}
        disabled={isCurrentTier || (isLoading && !isEnterprise)}
        className={`w-full py-3 px-6 rounded-xl font-semibold transition-all transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none ${getButtonStyle(
          tier.tier
        )}`}
      >
        {isLoading && !isEnterprise ? (
          <div className="flex items-center justify-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
            Processing...
          </div>
        ) : isCurrentTier ? (
          "Current Plan"
        ) : isEnterprise ? (
          "Contact Sales"
        ) : tier.tier === "free" ? (
          "Get Started Free"
        ) : (
          "Upgrade"
        )}
      </button>
    </div>
  );
}
