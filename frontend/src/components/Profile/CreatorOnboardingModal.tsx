import React, { useState } from 'react';
import { X, ChevronRight, ChevronLeft, Sparkles, BookOpen, Film, Wand2, Zap, Check } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../lib/api';

interface CreatorOnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CreatorOnboardingModal({
  isOpen,
  onClose,
}: CreatorOnboardingModalProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const navigate = useNavigate();

  if (!isOpen) return null;

  const steps = [
    {
      title: 'Welcome to Creator Mode!',
      icon: Sparkles,
      iconColor: 'text-blue-600',
      iconBg: 'bg-blue-100',
      content: (
        <div className="space-y-4">
          <p className="text-gray-700 text-lg">
            Congratulations! You now have access to powerful AI tools to create amazing content.
          </p>
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6">
            <h4 className="font-semibold text-gray-900 mb-3">What you can do:</h4>
            <ul className="space-y-2 text-gray-700">
              <li className="flex items-start space-x-2">
                <Check className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <span>Upload your books, articles, and documents</span>
              </li>
              <li className="flex items-start space-x-2">
                <Check className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <span>Generate quizzes, summaries, and study materials from your content</span>
              </li>
              <li className="flex items-start space-x-2">
                <Check className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <span>Create interactive learning experiences with AI</span>
              </li>
              <li className="flex items-start space-x-2">
                <Check className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <span>Manage and organize your content library</span>
              </li>
            </ul>
          </div>
        </div>
      ),
    },
    {
      title: 'The Creator Dashboard',
      icon: Wand2,
      iconColor: 'text-indigo-600',
      iconBg: 'bg-indigo-100',
      content: (
        <div className="space-y-4">
          <p className="text-gray-700">
            Your main hub for content creation. Access it anytime from the navigation menu.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white border-2 border-blue-200 rounded-xl p-4 text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <BookOpen className="h-6 w-6 text-blue-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">Books & Docs</h4>
              <p className="text-sm text-gray-600">
                Upload and manage your books, articles, and documents
              </p>
            </div>
            <div className="bg-white border-2 border-green-200 rounded-xl p-4 text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <Film className="h-6 w-6 text-green-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">Content</h4>
              <p className="text-sm text-gray-600">
                Generate quizzes, summaries, and study guides
              </p>
            </div>
            <div className="bg-white border-2 border-pink-200 rounded-xl p-4 text-center">
              <div className="w-12 h-12 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <Sparkles className="h-6 w-6 text-pink-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">AI Tools</h4>
              <p className="text-sm text-gray-600">
                Use AI to analyze and enhance your content
              </p>
            </div>
          </div>
        </div>
      ),
    },
    {
      title: 'AI Generation Features',
      icon: Zap,
      iconColor: 'text-amber-600',
      iconBg: 'bg-amber-100',
      content: (
        <div className="space-y-4">
          <p className="text-gray-700">
            Our AI tools help you create professional content quickly and easily.
          </p>
          <div className="space-y-3">
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <h4 className="font-semibold text-gray-900 mb-2">Plot Generation</h4>
              <p className="text-sm text-gray-600">
                Generate comprehensive plot overviews, character profiles, and story arcs with AI
              </p>
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <h4 className="font-semibold text-gray-900 mb-2">Scene Creation</h4>
              <p className="text-sm text-gray-600">
                Create detailed scenes with dialogue, descriptions, and character interactions
              </p>
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <h4 className="font-semibold text-gray-900 mb-2">Image & Video Generation</h4>
              <p className="text-sm text-gray-600">
                Generate images for characters and scenes, and produce complete video content
              </p>
            </div>
          </div>
        </div>
      ),
    },
    {
      title: 'Subscription Tiers',
      icon: Sparkles,
      iconColor: 'text-green-600',
      iconBg: 'bg-green-100',
      content: (
        <div className="space-y-4">
          <p className="text-gray-700">
            You're currently on the Free tier. Upgrade anytime to unlock more features and higher limits.
          </p>
          <div className="space-y-3">
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 border-2 border-gray-300 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold text-gray-900">Free Tier</h4>
                <span className="px-3 py-1 bg-gray-200 text-gray-700 text-sm rounded-full font-medium">
                  Current
                </span>
              </div>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Limited AI generations per month</li>
                <li>• Basic quality video output</li>
                <li>• Standard processing speed</li>
              </ul>
            </div>
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-300 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold text-gray-900">Pro & Premium Tiers</h4>
                <span className="px-3 py-1 bg-blue-600 text-white text-sm rounded-full font-medium">
                  Upgrade
                </span>
              </div>
              <ul className="text-sm text-gray-700 space-y-1">
                <li>• Unlimited AI generations</li>
                <li>• High-quality & 4K video output</li>
                <li>• Priority processing & support</li>
                <li>• Advanced customization options</li>
              </ul>
            </div>
          </div>
          <p className="text-sm text-gray-600 text-center">
            Visit the Subscription page to view all available plans
          </p>
        </div>
      ),
    },
  ];

  const currentStepData = steps[currentStep];

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleFinish = async () => {
    try {
      await apiClient.put('/users/me', {
        onboarding_completed: { creator: true },
      });
    } catch (error) {
      console.error('Failed to mark onboarding as completed:', error);
    }
    onClose();
    navigate('/creator');
  };

  const handleSkip = async () => {
    try {
      await apiClient.put('/users/me', {
        onboarding_completed: { creator: true },
      });
    } catch (error) {
      console.error('Failed to mark onboarding as completed:', error);
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6 rounded-t-2xl">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-3">
              <div className={`w-12 h-12 ${currentStepData.iconBg} rounded-full flex items-center justify-center`}>
                <currentStepData.icon className={`h-6 w-6 ${currentStepData.iconColor}`} />
              </div>
              <h2 className="text-2xl font-bold">
                {currentStepData.title}
              </h2>
            </div>
            <button
              onClick={handleSkip}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          <div className="flex items-center space-x-2 mt-4">
            {steps.map((_, index) => (
              <div
                key={index}
                className={`h-2 flex-1 rounded-full transition-all ${
                  index === currentStep
                    ? 'bg-white'
                    : index < currentStep
                    ? 'bg-white/70'
                    : 'bg-white/30'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {currentStepData.content}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 bg-gray-50 rounded-b-2xl">
          <div className="flex justify-between items-center">
            <button
              onClick={handleSkip}
              className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
            >
              Skip Tour
            </button>
            <div className="flex space-x-3">
              {currentStep > 0 && (
                <button
                  onClick={handlePrevious}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors flex items-center space-x-2"
                >
                  <ChevronLeft className="h-4 w-4" />
                  <span>Previous</span>
                </button>
              )}
              {currentStep < steps.length - 1 ? (
                <button
                  onClick={handleNext}
                  className="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all flex items-center space-x-2"
                >
                  <span>Next</span>
                  <ChevronRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  onClick={handleFinish}
                  className="px-6 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 transition-all flex items-center space-x-2"
                >
                  <span>Start Creating</span>
                  <Sparkles className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
