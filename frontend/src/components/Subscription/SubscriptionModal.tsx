import React, { useState, useEffect } from "react";
import { X, Loader2 } from "lucide-react";
import { toast } from "react-hot-toast";
import SubscriptionTierCard from "./SubscriptionTierCard";
import { SubscriptionTier, subscriptionService } from "../../services/subscriptionService";

interface SubscriptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTier?: string;
}

export default function SubscriptionModal({
  isOpen,
  onClose,
  currentTier,
}: SubscriptionModalProps) {
  const [tiers, setTiers] = useState<SubscriptionTier[]>([]);
  const [loading, setLoading] = useState(false);
  const [upgrading, setUpgrading] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadTiers();
    }
  }, [isOpen]);

  const loadTiers = async () => {
    try {
      setLoading(true);
      const availableTiers = await subscriptionService.getSubscriptionTiers();
      setTiers(availableTiers);
    } catch (error) {
      toast.error("Failed to load subscription options");
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (tier: SubscriptionTier) => {
    if (tier.tier === currentTier) return;

    try {
      setUpgrading(tier.tier);

      // Create checkout session
      const checkoutData = {
        tier: tier.tier,
        success_url: `${window.location.origin}/dashboard?payment=success`,
        cancel_url: `${window.location.origin}/subscription?payment=cancelled`,
      };

      const session = await subscriptionService.createCheckoutSession(checkoutData);

      // Redirect to Stripe checkout
      window.location.href = session.checkout_url;
    } catch (error) {
      toast.error("Failed to start checkout process");
    } finally {
      setUpgrading(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-6xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Choose Your Plan
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                Upgrade to unlock more features and higher limits
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors"
            >
              <X className="h-6 w-6 text-gray-500 dark:text-gray-400" />
            </button>
          </div>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
              <span className="ml-2 text-gray-600 dark:text-gray-400">Loading plans...</span>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {tiers.map((tier) => (
                <SubscriptionTierCard
                  key={tier.tier}
                  tier={tier}
                  currentTier={currentTier}
                  onSelect={handleUpgrade}
                  isLoading={upgrading === tier.tier}
                />
              ))}
            </div>
          )}

          <div className="mt-8 text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              All plans include secure payment processing by Stripe
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              You can cancel or change your plan at any time. Refunds are processed according to our refund policy.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}