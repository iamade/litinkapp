import { apiClient } from "../lib/api";

export interface SubscriptionTier {
  tier: "free" | "basic" | "pro" | "premium" | "professional" | "enterprise";
  display_name: string;
  description?: string;
  monthly_price: number;
  stripe_price_id?: string;
  stripe_product_id?: string;
  monthly_video_limit: number | "unlimited";
  video_quality: string;
  has_watermark: boolean;
  max_video_duration?: number | "unlimited";
  priority_processing: boolean;
  features: Record<string, unknown>;
  feature_highlights?: string[];
  display_order: number;
  is_active: boolean;
}

export interface UserSubscription {
  id: string;
  user_id: string;
  tier: "free" | "basic" | "pro" | "premium" | "professional" | "enterprise";
  status: "active" | "cancelled" | "expired" | "past_due" | "trialing";
  stripe_customer_id?: string;
  stripe_subscription_id?: string;
  stripe_price_id?: string;
  monthly_video_limit: number | "unlimited";
  video_quality: string;
  has_watermark: boolean;
  current_period_start?: string;
  current_period_end?: string;
  videos_generated_this_period: number;
  next_billing_date?: string;
  cancel_at_period_end: boolean;
  cancelled_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CheckoutSessionCreate {
  tier: "free" | "basic" | "pro" | "premium" | "professional" | "enterprise";
  billing_period?: "monthly" | "annual";
  success_url: string;
  cancel_url: string;
}

export interface CheckoutSessionResponse {
  session_id: string;
  checkout_url: string;
}

export interface SubscriptionUsageStats {
  current_period_videos: number;
  period_limit: number;
  remaining_videos: number;
  period_start?: string;
  period_end?: string;
  can_generate_video: boolean;
}

export interface SubscriptionCancelRequest {
  cancel_at_period_end?: boolean;
}

export interface SubscriptionCancelResponse {
  subscription_id: string;
  status: string;
  cancel_at_period_end: boolean;
  current_period_end?: number;
}

export const subscriptionService = {
  // Get current user's subscription
  getCurrentSubscription: async (): Promise<UserSubscription> => {
    return apiClient.get<UserSubscription>("/subscriptions/current");
  },

  // Create Stripe checkout session
  createCheckoutSession: async (data: CheckoutSessionCreate): Promise<CheckoutSessionResponse> => {
    return apiClient.post<CheckoutSessionResponse>("/subscriptions/checkout", data);
  },

  // Get usage statistics
  getUsageStats: async (): Promise<SubscriptionUsageStats> => {
    return apiClient.get<SubscriptionUsageStats>("/subscriptions/usage");
  },

  // Get available subscription tiers
  getSubscriptionTiers: async (): Promise<SubscriptionTier[]> => {
    return apiClient.get<SubscriptionTier[]>("/subscriptions/tiers");
  },

  // Cancel subscription
  cancelSubscription: async (data?: SubscriptionCancelRequest): Promise<SubscriptionCancelResponse> => {
    return apiClient.post<SubscriptionCancelResponse>("/subscriptions/cancel", data || {});
  },

  // Reactivate subscription
  reactivateSubscription: async (): Promise<{ message: string }> => {
    return apiClient.post<{ message: string }>("/subscriptions/reactivate", {});
  },

  // Check if user can generate video based on limits
  canGenerateVideo: async (): Promise<boolean> => {
    try {
      const usage = await subscriptionService.getUsageStats();
      return usage.can_generate_video;
    } catch (error) {
      return false;
    }
  },

  // Get remaining videos for current period
  getRemainingVideos: async (): Promise<number> => {
    try {
      const usage = await subscriptionService.getUsageStats();
      return usage.remaining_videos;
    } catch (error) {
      return 0;
    }
  }
};