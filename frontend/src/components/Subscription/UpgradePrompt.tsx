import React from "react";
import { ArrowRight, Zap, Video, Crown } from "lucide-react";

interface UpgradePromptProps {
  title?: string;
  message?: string;
  feature?: "video" | "book" | "general";
  onUpgrade: () => void;
  className?: string;
}

export default function UpgradePrompt({
  title,
  message,
  feature = "general",
  onUpgrade,
  className = "",
}: UpgradePromptProps) {
  const getIcon = () => {
    switch (feature) {
      case "video":
        return <Video className="h-6 w-6 text-purple-600" />;
      case "book":
        return <Zap className="h-6 w-6 text-purple-600" />;
      default:
        return <Crown className="h-6 w-6 text-purple-600" />;
    }
  };

  const getDefaultTitle = () => {
    switch (feature) {
      case "video":
        return "Ready to Create More Videos?";
      case "book":
        return "Unlock Unlimited Books";
      default:
        return "Upgrade Your Experience";
    }
  };

  const getDefaultMessage = () => {
    switch (feature) {
      case "video":
        return "You've reached your monthly video limit. Upgrade now to continue creating amazing content.";
      case "book":
        return "You've uploaded multiple books! Upgrade to keep creating without limits.";
      default:
        return "Unlock premium features and higher limits with a subscription upgrade.";
    }
  };

  return (
    <div className={`bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-xl p-6 ${className}`}>
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0">
          {getIcon()}
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {title || getDefaultTitle()}
          </h3>
          <p className="text-gray-700 mb-4">
            {message || getDefaultMessage()}
          </p>
          <button
            onClick={onUpgrade}
            className="inline-flex items-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition-all transform hover:scale-105"
          >
            Upgrade Now
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}