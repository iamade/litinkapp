import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "react-hot-toast";
import { Loader2, CheckCircle, XCircle, Settings, CreditCard, Check } from "lucide-react";
import SubscriptionTierCard from "../components/Subscription/SubscriptionTierCard";
import UsageIndicator from "../components/Subscription/UsageIndicator";
import PromoCodeInput from "../components/Subscription/PromoCodeInput";
import {
  SubscriptionTier,
  UserSubscription,
  SubscriptionUsageStats,
  subscriptionService
} from "../services/subscriptionService";

import CancelSubscriptionModal from "../components/Subscription/CancelSubscriptionModal";

export default function SubscriptionPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [tiers, setTiers] = useState<SubscriptionTier[]>([]);
  const [currentSubscription, setCurrentSubscription] = useState<UserSubscription | null>(null);
  const [usage, setUsage] = useState<SubscriptionUsageStats | null>(null);
  const [loadingData, setLoadingData] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    // Wait for auth to finish loading before checking if user exists
    if (loading) {
      return; // Still loading auth, don't redirect yet
    }

    loadData();

    // Check for payment success/cancel from URL params
    const urlParams = new URLSearchParams(location.search);
    const paymentStatus = urlParams.get("payment");

    if (paymentStatus === "success") {
      toast.success("Payment successful! Your subscription has been upgraded.");
      loadData(); // Reload data to show updated subscription
    } else if (paymentStatus === "cancelled") {
      toast.error("Payment was cancelled. You can try again anytime.");
    }
  }, [user, loading, navigate, location.search]);

  const loadData = async () => {
    try {
      setLoadingData(true);
      const tiersPromise = subscriptionService.getSubscriptionTiers();
      
      let subscriptionData = null;
      let usageData = null;

      if (user) {
        const [sub, usage] = await Promise.all([
          subscriptionService.getCurrentSubscription().catch(() => null),
          subscriptionService.getUsageStats().catch(() => null),
        ]);
        subscriptionData = sub;
        usageData = usage;
      }

      const tiersData = await tiersPromise;

      setTiers(tiersData);
      setCurrentSubscription(subscriptionData);
      setUsage(usageData);
    } catch (error) {
      toast.error("Failed to load subscription information");
    } finally {
      setLoadingData(false);
    }
  };

  const handleUpgrade = async (tier: SubscriptionTier, billingPeriod: 'monthly' | 'annual') => {
    if (!user) {
      navigate('/auth?mode=register');
      return;
    }

    if (tier.tier === currentSubscription?.tier) return;

    try {
      setUpgrading(tier.tier);

      // Create checkout session
      const checkoutData = {
        tier: tier.tier,
        billing_period: billingPeriod,
        success_url: `${window.location.origin}/subscription?payment=success`,
        cancel_url: `${window.location.origin}/subscription?payment=cancelled`,
      };

      const session = await subscriptionService.createCheckoutSession(checkoutData);

      // Redirect to Stripe checkout
      window.location.href = session.checkout_url;
    } catch (error) {
      toast.error("Failed to start checkout process");
      setUpgrading(null);
    }
  };

  const handleCancelSubscription = async () => {
    if (!currentSubscription) return;
    
    setCancelling(true);
    try {
      await subscriptionService.cancelSubscription({ cancel_at_period_end: true });
      toast.success("Subscription cancelled. You'll retain access until the end of your billing period.");
      setShowCancelModal(false);
      loadData(); // Reload to show updated status
    } catch (error) {
      toast.error("Failed to cancel subscription");
    } finally {
      setCancelling(false);
    }
  };

  const handleReactivateSubscription = async () => {
    try {
      await subscriptionService.reactivateSubscription();
      toast.success("Subscription reactivated successfully!");
      loadData(); // Reload to show updated status
    } catch (error) {
      toast.error("Failed to reactivate subscription");
    }
  };



  const handlePromoRedeemed = async () => {
    await loadData();
  };

  if (loading || loadingData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-[#0F0F23]">
        <div className="flex items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
          <span className="text-gray-600 dark:text-gray-400">Loading subscription details...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-8 bg-gray-50 dark:bg-[#0F0F23] transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-3">
            Plans &amp; Pricing
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Start free. Scale as you grow. Every plan includes AI-powered video generation, image creation, and voiceover synthesis.
          </p>
        </div>

        {/* Current Subscription Status */}
        {currentSubscription && (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Current Plan</h2>
              <div className="flex items-center gap-2">
                {currentSubscription.status === "active" ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : currentSubscription.status === "cancelled" ? (
                  <XCircle className="h-5 w-5 text-red-500" />
                ) : (
                  <Settings className="h-5 w-5 text-yellow-500" />
                )}
                <span className={`text-sm font-medium capitalize ${
                  currentSubscription.status === "active" ? "text-green-600" :
                  currentSubscription.status === "cancelled" ? "text-red-600" :
                  "text-yellow-600"
                }`}>
                  {currentSubscription.status.replace("_", " ")}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <span className="text-sm text-gray-600 dark:text-gray-400">Plan</span>
                <p className="font-semibold text-gray-900 dark:text-white capitalize">
                  {currentSubscription.tier}
                </p>
              </div>
              <div>
                <span className="text-sm text-gray-600 dark:text-gray-400">Quality</span>
                <p className="font-semibold text-gray-900 dark:text-white">
                  {currentSubscription.video_quality}
                </p>
              </div>
            </div>

            {/* Usage Indicator */}
            {usage && (
              <div className="mb-4">
                <UsageIndicator usage={usage} />
              </div>
            )}

            {/* Subscription Actions */}
            {currentSubscription.tier !== "free" && (
              <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                {currentSubscription.cancel_at_period_end ? (
                  <button
                    onClick={handleReactivateSubscription}
                    className="bg-green-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700 transition-colors"
                  >
                    Reactivate Subscription
                  </button>
                ) : (
                  <button
                    onClick={() => setShowCancelModal(true)}
                    className="bg-red-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-red-700 transition-colors"
                  >
                    Cancel Subscription
                  </button>
                )}
                {currentSubscription.current_period_end && (
                  <div className="text-sm text-gray-600 dark:text-gray-400 flex items-center">
                    {currentSubscription.cancel_at_period_end ? "Ends" : "Renews"} on{" "}
                    {new Date(currentSubscription.current_period_end).toLocaleDateString()}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Main Subscription Tiers (excluding Enterprise) */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {tiers
            .filter((t) => t.tier !== "enterprise")
            .map((tier) => (
              <SubscriptionTierCard
                key={tier.tier}
                tier={tier}
                currentTier={currentSubscription?.tier}
                onSelect={handleUpgrade}
                isLoading={upgrading === tier.tier}
              />
            ))}
        </div>

        {/* Enterprise Tier — Separate Section */}
        {tiers.find((t) => t.tier === "enterprise") && (
          <div className="mt-8 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30 rounded-2xl border border-indigo-200 dark:border-indigo-800 p-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div>
                <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                  Enterprise
                </h3>
                <p className="text-gray-600 dark:text-gray-400 max-w-lg">
                  Need unlimited generations, dedicated support, custom SLAs, or team collaboration? 
                  We'll build a plan tailored to your organization.
                </p>
                <div className="flex flex-wrap gap-4 mt-4 text-sm text-gray-700 dark:text-gray-300">
                  <span className="flex items-center gap-1.5">
                    <Check className="h-4 w-4 text-green-500" /> Unlimited credits
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Check className="h-4 w-4 text-green-500" /> 8K resolution
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Check className="h-4 w-4 text-green-500" /> API access
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Check className="h-4 w-4 text-green-500" /> 24/7 dedicated support
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Check className="h-4 w-4 text-green-500" /> Custom SLA
                  </span>
                </div>
              </div>
              <a
                href="mailto:contact@peopleprotocol.ca?subject=Enterprise%20Plan%20Inquiry"
                className="flex-shrink-0 bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3 rounded-xl font-semibold transition-all transform hover:scale-[1.02] shadow-lg"
              >
                Contact Sales
              </a>
            </div>
          </div>
        )}

        <div className="mt-8 max-w-2xl mx-auto">
          <PromoCodeInput
            title="Have a promo code?"
            onRedeemed={handlePromoRedeemed}
          />
        </div>

        {/* FAQ Section */}
        <div className="mt-12 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 text-center">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Can I change my plan anytime?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately for upgrades, or at the next billing cycle for downgrades.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                What happens to my videos if I cancel?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Your videos remain accessible even after cancellation. You'll just be limited to free tier features and won't be able to generate new videos beyond the free limit.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                How do credits work?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Credits are consumed when you use AI features — image generation, video generation, voiceover synthesis, and script analysis. Each feature has a credit cost shown before generation. Your credits refresh monthly with your subscription.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Is there a free plan?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Yes! Our Free plan includes 100 credits so you can try AI video generation, image creation, and voiceover before upgrading. No credit card required.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                How does billing work?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Plans are billed monthly or annually (save 20% with annual). You can cancel anytime and retain access until the end of your billing period.
              </p>
            </div>
          </div>
        </div>

        {/* Contact Support */}
        <div className="mt-8 text-center">
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Need help choosing the right plan?
          </p>
          <a
            href="mailto:contact@peopleprotocol.ca"
            className="inline-flex items-center gap-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-6 py-3 rounded-lg font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            <CreditCard className="h-4 w-4" />
            Contact Support
          </a>
        </div>

        {/* Cancel Subscription Modal */}
        <CancelSubscriptionModal
          isOpen={showCancelModal}
          onClose={() => setShowCancelModal(false)}
          onConfirm={handleCancelSubscription}
          tier={currentSubscription?.tier || ""}
          periodEnd={currentSubscription?.current_period_end ? new Date(currentSubscription.current_period_end).toLocaleDateString() : undefined}
          isLoading={cancelling}
        />
      </div>
    </div>
  );
}