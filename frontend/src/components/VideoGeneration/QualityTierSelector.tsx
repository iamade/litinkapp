import React from 'react';
import { Star, Zap, Crown, Play } from 'lucide-react';

interface QualityTierOption {
  id: 'free' | 'premium' | 'professional';
  name: string;
  description: string;
  features: string[];
  price: string;
  recommended?: boolean;
  icon: React.ReactNode;
}

interface QualityTierSelectorProps {
  selectedTier: 'free' | 'premium' | 'professional';
  onSelect: (tier: 'free' | 'premium' | 'professional') => void;
  onStartGeneration: () => void;
  scriptId: string;
}

const qualityTiers: QualityTierOption[] = [
  {
    id: 'free',
    name: 'Free',
    description: 'Basic video generation',
    price: 'Free',
    icon: <Star className="w-6 h-6" />,
    features: [
      'Up to 2 minutes duration',
      'Standard quality (720p)',
      'Basic character voices',
      'Limited scene complexity',
      'Watermark included'
    ]
  },
  {
    id: 'premium',
    name: 'Premium',
    description: 'Enhanced video quality',
    price: '$9.99',
    recommended: true,
    icon: <Zap className="w-6 h-6" />,
    features: [
      'Up to 10 minutes duration',
      'High quality (1080p)',
      'Advanced character voices',
      'Multiple scene types',
      'No watermark',
      'Background music'
    ]
  },
  {
    id: 'professional',
    name: 'Professional',
    description: 'Maximum quality & features',
    price: '$24.99',
    icon: <Crown className="w-6 h-6" />,
    features: [
      'Up to 30 minutes duration',
      'Ultra quality (4K)',
      'Premium character voices',
      'Complex scene generation',
      'Advanced lip sync',
      'Custom sound effects',
      'Priority processing'
    ]
  }
];

export const QualityTierSelector: React.FC<QualityTierSelectorProps> = ({
  selectedTier,
  onSelect,
  onStartGeneration
}) => {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-xl font-semibold text-gray-900 mb-2">
          Choose Your Video Quality
        </h3>
        <p className="text-gray-600">
          Select the quality tier that best fits your needs
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {qualityTiers.map((tier) => (
          <div
            key={tier.id}
            onClick={() => onSelect(tier.id)}
            className={`relative cursor-pointer rounded-xl border-2 p-6 transition-all hover:shadow-lg ${
              selectedTier === tier.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            {tier.recommended && (
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <span className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-3 py-1 rounded-full text-xs font-medium">
                  Recommended
                </span>
              </div>
            )}

            <div className="flex items-center gap-3 mb-4">
              <div className={`p-2 rounded-lg ${
                selectedTier === tier.id ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
              }`}>
                {tier.icon}
              </div>
              <div>
                <h4 className="font-semibold text-lg">{tier.name}</h4>
                <p className="text-gray-600 text-sm">{tier.description}</p>
              </div>
            </div>

            <div className="text-2xl font-bold text-gray-900 mb-4">
              {tier.price}
            </div>

            <ul className="space-y-2">
              {tier.features.map((feature, index) => (
                <li key={index} className="flex items-start gap-2 text-sm">
                  <div className={`w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0 ${
                    selectedTier === tier.id ? 'bg-blue-500' : 'bg-gray-400'
                  }`} />
                  <span className="text-gray-700">{feature}</span>
                </li>
              ))}
            </ul>

            {selectedTier === tier.id && (
              <div className="absolute inset-0 border-2 border-blue-500 rounded-xl pointer-events-none">
                <div className="absolute top-2 right-2">
                  <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                    <div className="w-2 h-2 bg-white rounded-full"></div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="flex justify-center pt-4">
        <button
          onClick={onStartGeneration}
          className="flex items-center gap-3 px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-lg hover:shadow-lg transform hover:scale-105 transition-all duration-200"
        >
          <Play className="w-5 h-5" />
          Start Video Generation
        </button>
      </div>

      <div className="text-center text-sm text-gray-500">
        <p>Generation time varies by complexity: 3-15 minutes typical</p>
      </div>
    </div>
  );
};