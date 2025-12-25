import React, { useState } from 'react';
import { Sparkles, ArrowRight, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface UpgradeBannerProps {
  onDismiss?: () => void;
}

export default function UpgradeBanner({ onDismiss }: UpgradeBannerProps) {
  const [isDismissed, setIsDismissed] = useState(false);
  const navigate = useNavigate();

  if (isDismissed) return null;

  const handleDismiss = () => {
    setIsDismissed(true);
    onDismiss?.();
  };

  return (
    <div className="relative bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-600 rounded-2xl p-6 text-white overflow-hidden">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-0 left-0 w-32 h-32 bg-white rounded-full -translate-x-16 -translate-y-16"></div>
        <div className="absolute bottom-0 right-0 w-40 h-40 bg-white rounded-full translate-x-20 translate-y-20"></div>
      </div>

      {/* Content */}
      <div className="relative">
        <button
          onClick={handleDismiss}
          className="absolute top-0 right-0 p-1 hover:bg-white/20 rounded-lg transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-start space-x-4 mb-4">
          <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center flex-shrink-0">
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-bold mb-2">
              Unlock Your Creative Potential
            </h3>
            <p className="text-blue-100 mb-4">
              Add Creator Mode to your account for free and start creating amazing content with AI-powered tools. Generate books, scripts, and videos in minutes!
            </p>
            <button
              onClick={() => navigate('/profile')}
              className="inline-flex items-center space-x-2 bg-white text-blue-600 px-6 py-2.5 rounded-lg font-medium hover:bg-blue-50 transition-all transform hover:scale-105 shadow-lg"
            >
              <span>Upgrade to Creator</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-white/20">
          <div className="text-center">
            <p className="text-2xl font-bold mb-1">Free</p>
            <p className="text-xs text-blue-100">No credit card needed</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold mb-1">AI Tools</p>
            <p className="text-xs text-blue-100">Advanced generation</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold mb-1">Unlimited</p>
            <p className="text-xs text-blue-100">Keep both roles</p>
          </div>
        </div>
      </div>
    </div>
  );
}
