import React from "react";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SubscriptionPage from "./SubscriptionPage";

const api = vi.hoisted(() => ({
  getSubscriptionTiers: vi.fn(), getSubscriptionStatus: vi.fn(), getUsageStats: vi.fn(), user: { id: "owner" },
}));
vi.mock("../services/subscriptionService", () => ({ subscriptionService: api }));
vi.mock("../contexts/AuthContext", () => ({ useAuth: () => ({ user: api.user, loading: false }) }));
vi.mock("../components/Subscription/SubscriptionTierCard", () => ({ default: () => null }));
vi.mock("../components/Subscription/UsageIndicator", () => ({ default: () => null }));
vi.mock("../components/Subscription/PromoCodeInput", () => ({ default: () => null }));
vi.mock("../components/Subscription/CancelSubscriptionModal", () => ({ default: () => null }));

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  api.getSubscriptionTiers.mockResolvedValue([
    { tier: "professional", display_name: "Pro" },
    { tier: "standard", display_name: "Standard" },
  ]);
  api.getUsageStats.mockResolvedValue(null);
});

describe("KAN-179 Current Plan uses canonical catalogue display names", () => {
  it.each([
    ["professional", "professional", "Pro"],
    ["pro", "pro", "Standard"],
    [undefined, "professional", "Pro"],
  ])("renders plan %s and tier %s as %s", async (plan, tier, expected) => {
    api.getSubscriptionStatus.mockResolvedValue({ plan, tier, status: "active", cancel_at_period_end: false });
    render(<MemoryRouter><SubscriptionPage /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText("Plan", { exact: true }).nextElementSibling?.textContent).toBe(expected);
      expect(screen.getByText("Tier", { exact: true }).nextElementSibling?.textContent).toBe(expected);
    });
    expect(api.getSubscriptionStatus).toHaveBeenCalled();
  });
});
