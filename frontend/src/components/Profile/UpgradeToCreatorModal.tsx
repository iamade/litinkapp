import React from 'react';
import { X, Sparkles, BookOpen, Film, Music, Wand2, Check } from 'lucide-react';

interface UpgradeToCreatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading?: boolean;
}

export default function UpgradeToCreatorModal({
  isOpen,
  onClose,
  onConfirm,
  isLoading = false,
}: UpgradeToCreatorModalProps) {
  if (!isOpen) return null;

  const features = [
    {
      icon: BookOpen,
      title: 'AI Book Generation',
      description: 'Create interactive books with AI assistance',
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      icon: Film,
      title: 'Script Writing',
      description: 'Write movie and entertainment scripts powered by AI',
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      icon: Music,
      title: 'Video Production',
      description: 'Produce film and music videos with AI tools',
      color: 'text-pink-600',
      bgColor: 'bg-pink-100',
    },
    {
      icon: Wand2,
      title: 'Advanced AI Tools',
      description: 'Access to plot generation, character creation, and more',
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-100',
    },
  ];

  const benefits = [
    'Free to add Creator role to your account',
    'Keep your Explorer access - have both roles',
    'Pay only for what you use with flexible pricing',
    'Access premium features with subscription tiers',
    'Create unlimited content with higher tiers',
    'Priority support and faster processing',
  ];

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6 rounded-t-2xl">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-2xl font-bold flex items-center">
              <Sparkles className="h-7 w-7 mr-3" />
              Upgrade to Creator Mode
            </h2>
            <button
              onClick={onClose}
              disabled={isLoading}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors disabled:opacity-50"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          <p className="text-blue-100">
            Unlock powerful AI tools to create amazing content
          </p>
        </div>

        <div className="p-6">
          {/* Features Grid */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              What You'll Get
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {features.map((feature, index) => (
                <div
                  key={index}
                  className="p-4 border border-gray-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all"
                >
                  <div className="flex items-start space-x-3">
                    <div className={`w-10 h-10 ${feature.bgColor} rounded-lg flex items-center justify-center flex-shrink-0`}>
                      <feature.icon className={`h-5 w-5 ${feature.color}`} />
                    </div>
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-1">
                        {feature.title}
                      </h4>
                      <p className="text-sm text-gray-600">
                        {feature.description}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Benefits List */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Pricing & Benefits
            </h3>
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6">
              <div className="space-y-3">
                {benefits.map((benefit, index) => (
                  <div key={index} className="flex items-start space-x-3">
                    <Check className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                    <p className="text-gray-700">{benefit}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* How It Works */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              How It Works
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-xl font-bold text-blue-600">1</span>
                </div>
                <h4 className="font-semibold text-gray-900 mb-1">Add Role</h4>
                <p className="text-sm text-gray-600">
                  Free to add Creator role to your account
                </p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-xl font-bold text-green-600">2</span>
                </div>
                <h4 className="font-semibold text-gray-900 mb-1">Start Creating</h4>
                <p className="text-sm text-gray-600">
                  Access all creator tools immediately
                </p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-xl font-bold text-indigo-600">3</span>
                </div>
                <h4 className="font-semibold text-gray-900 mb-1">Choose Plan</h4>
                <p className="text-sm text-gray-600">
                  Upgrade subscription for more features
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={onClose}
              disabled={isLoading}
              className="flex-1 px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              Maybe Later
            </button>
            <button
              onClick={onConfirm}
              disabled={isLoading}
              className="flex-1 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-medium hover:from-blue-700 hover:to-indigo-700 transition-all transform hover:scale-105 disabled:opacity-50 disabled:transform-none"
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <Sparkles className="h-4 w-4 mr-2 animate-spin" />
                  Adding Role...
                </span>
              ) : (
                'Add Creator Role'
              )}
            </button>
          </div>

          {/* Fine Print */}
          <p className="text-xs text-gray-500 text-center mt-4">
            No credit card required. You can remove the role at any time from your profile settings.
          </p>
        </div>
      </div>
    </div>
  );
}
