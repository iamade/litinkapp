import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "react-hot-toast";
import { Loader2, CheckCircle, XCircle, Settings, CreditCard } from "lucide-react";
import SubscriptionTierCard from "../components/Subscription/SubscriptionTierCard";
import UsageIndicator from "../components/Subscription/UsageIndicator";
import {
  SubscriptionTier,
  UserSubscription,
  SubscriptionUsageStats,
  subscriptionService
} from "../services/subscriptionService";

export default function SubscriptionPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [tiers, setTiers] = useState<SubscriptionTier[]>([]);
  const [currentSubscription, setCurrentSubscription] = useState<UserSubscription | null>(null);
  const [usage, setUsage] = useState<SubscriptionUsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      navigate("/auth");
      return;
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
  }, [user, navigate, location.search]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [tiersData, subscriptionData, usageData] = await Promise.all([
        subscriptionService.getSubscriptionTiers(),
        subscriptionService.getCurrentSubscription().catch(() => null), // Handle free tier gracefully
        subscriptionService.getUsageStats().catch(() => null),
      ]);

      setTiers(tiersData);
      setCurrentSubscription(subscriptionData);
      setUsage(usageData);
    } catch (error) {
      console.error("Error loading subscription data:", error);
      toast.error("Failed to load subscription information");
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (tier: SubscriptionTier, billingPeriod: 'monthly' | 'annual') => {
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
      window.location.href = session.url;
    } catch (error) {
      console.error("Error creating checkout session:", error);
      toast.error("Failed to start checkout process");
      setUpgrading(null);
    }
  };

  const handleCancelSubscription = async () => {
    if (!currentSubscription) return;

    const confirmed = window.confirm(
      "Are you sure you want to cancel your subscription? You'll lose access to premium features at the end of your billing period."
    );

    if (!confirmed) return;

    try {
      await subscriptionService.cancelSubscription({ cancel_at_period_end: true });
      toast.success("Subscription cancelled. You'll retain access until the end of your billing period.");
      loadData(); // Reload to show updated status
    } catch (error) {
      console.error("Error cancelling subscription:", error);
      toast.error("Failed to cancel subscription");
    }
  };

  const handleReactivateSubscription = async () => {
    try {
      await subscriptionService.reactivateSubscription();
      toast.success("Subscription reactivated successfully!");
      loadData(); // Reload to show updated status
    } catch (error) {
      console.error("Error reactivating subscription:", error);
      toast.error("Failed to reactivate subscription");
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-gray-600 mb-4">Sign in required</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
          <span className="text-gray-600">Loading subscription details...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Subscription Plans
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Choose the perfect plan for your creative needs. Upgrade or downgrade at any time.
          </p>
        </div>

        {/* Current Subscription Status */}
        {currentSubscription && (
          <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Current Plan</h2>
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
                <span className="text-sm text-gray-600">Plan</span>
                <p className="font-semibold text-gray-900 capitalize">
                  {currentSubscription.tier}
                </p>
              </div>
              <div>
                <span className="text-sm text-gray-600">Monthly Limit</span>
                <p className="font-semibold text-gray-900">
                  {currentSubscription.monthly_video_limit} videos
                </p>
              </div>
              <div>
                <span className="text-sm text-gray-600">Quality</span>
                <p className="font-semibold text-gray-900">
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
              <div className="flex gap-3 pt-4 border-t border-gray-200">
                {currentSubscription.cancel_at_period_end ? (
                  <button
                    onClick={handleReactivateSubscription}
                    className="bg-green-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700 transition-colors"
                  >
                    Reactivate Subscription
                  </button>
                ) : (
                  <button
                    onClick={handleCancelSubscription}
                    className="bg-red-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-red-700 transition-colors"
                  >
                    Cancel Subscription
                  </button>
                )}
                {currentSubscription.current_period_end && (
                  <div className="text-sm text-gray-600 flex items-center">
                    {currentSubscription.cancel_at_period_end ? "Ends" : "Renews"} on{" "}
                    {new Date(currentSubscription.current_period_end).toLocaleDateString()}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Subscription Tiers */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {tiers.map((tier) => (
            <SubscriptionTierCard
              key={tier.tier}
              tier={tier}
              currentTier={currentSubscription?.tier}
              onSelect={handleUpgrade}
              isLoading={upgrading === tier.tier}
            />
          ))}
        </div>

        {/* FAQ Section */}
        <div className="mt-12 bg-white rounded-xl shadow-lg border border-gray-200 p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Can I change my plan anytime?
              </h3>
              <p className="text-gray-600">
                Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately for upgrades, or at the next billing cycle for downgrades.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                What happens to my videos if I cancel?
              </h3>
              <p className="text-gray-600">
                Your videos remain accessible even after cancellation. You'll just be limited to free tier features and won't be able to generate new videos beyond the free limit.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Is there a free trial?
              </h3>
              <p className="text-gray-600">
                Our free tier allows you to upload 2 books and generate 2 videos per month. This gives you a great way to try our platform before upgrading.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                How does billing work?
              </h3>
              <p className="text-gray-600">
                All plans are billed monthly. You can cancel anytime, and you'll retain access until the end of your billing period. Refunds are processed according to our refund policy.
              </p>
            </div>
          </div>
        </div>

        {/* Contact Support */}
        <div className="mt-8 text-center">
          <p className="text-gray-600 mb-4">
            Need help choosing the right plan?
          </p>
          <a
            href="mailto:support@litink.ai"
            className="inline-flex items-center gap-2 bg-gray-100 text-gray-700 px-6 py-3 rounded-lg font-medium hover:bg-gray-200 transition-colors"
          >
            <CreditCard className="h-4 w-4" />
            Contact Support
          </a>
        </div>
      </div>
    </div>
  );
}