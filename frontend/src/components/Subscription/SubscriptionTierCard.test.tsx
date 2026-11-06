import React from "react";
import { render } from "@testing-library/react";
import "@testing-library/jest-dom";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import SubscriptionTierCard from "./SubscriptionTierCard";
import type { SubscriptionTier } from "../../services/subscriptionService";

/**
 * KAN-310: the pricing card renders credit counts served by the backend.
 *
 * The expected values are parsed out of backend/app/credits/constants.py, so this
 * test fails if the card and the constants disagree. The component no longer has
 * a hardcoded tier -> credits map.
 */
const CONSTANTS_PATH = resolve(
  __dirname,
  "../../../../backend/app/credits/constants.py"
);

const CARD_PATH = resolve(__dirname, "./SubscriptionTierCard.tsx");

function parseTierCreditGrants(): Record<string, number> {
  const source = readFileSync(CONSTANTS_PATH, "utf8");
  const block = source.match(/TIER_CREDIT_GRANTS_BY_ENUM\s*=\s*\{([\s\S]*?)\}/);
  if (!block) {
    throw new Error("TIER_CREDIT_GRANTS_BY_ENUM not found in constants.py");
  }
  const grants: Record<string, number> = {};
  const entry = /"([a-z_]+)"\s*:\s*(\d+)/g;
  let match: RegExpExecArray | null;
  while ((match = entry.exec(block[1])) !== null) {
    grants[match[1]] = Number(match[2]);
  }
  return grants;
}

const TIER_CREDIT_GRANTS = parseTierCreditGrants();

function makeTier(tier: string, monthlyCredits: number | null): SubscriptionTier {
  return {
    tier: tier as SubscriptionTier["tier"],
    display_name: tier,
    description: tier + " tier",
    monthly_price: 10,
    monthly_credits: monthlyCredits,
    monthly_video_limit: "unlimited",
    video_quality: "1080p",
    has_watermark: false,
    priority_processing: false,
    features: {},
    feature_highlights: [],
    display_order: 0,
    is_active: true,
  };
}

function renderTier(tier: string, monthlyCredits: number | null) {
  return render(
    <SubscriptionTierCard
      tier={makeTier(tier, monthlyCredits)}
      onSelect={() => undefined}
    />
  );
}

describe("SubscriptionTierCard credit counts (KAN-310)", () => {
  it("parses the backend constants", () => {
    expect(Object.keys(TIER_CREDIT_GRANTS).length).toBeGreaterThan(0);
    expect(TIER_CREDIT_GRANTS.free).toBe(300);
  });

  it.each(Object.entries(TIER_CREDIT_GRANTS))(
    "renders the credit count served for tier %s",
    (tier, amount) => {
      const { container } = renderTier(tier, amount);
      expect(container.textContent).toContain(amount.toLocaleString("en-US"));
      // The card renders the label ("Credits included" / "Credits/month").
      expect(container.textContent).toMatch(/credits/i);
    }
  );

  it("renders whatever count the backend serves, not a hardcoded map", () => {
    // 12345 is not in constants.py. If the card still had its own map, this
    // would render the old hardcoded number instead.
    const { container } = renderTier("standard", 12345);
    expect(container.textContent).toContain("12,345");
    expect(container.textContent).not.toContain("4,800");
  });

  it("shows Unlimited for enterprise, which has no monthly credit grant", () => {
    const { container } = renderTier("enterprise", null);
    expect(container.textContent).toContain("Unlimited");
  });

  it("shows no invented number when the backend serves no credit count", () => {
    const { container } = renderTier("basic", null);
    expect(container.textContent).not.toContain("1,500");
    expect(container.textContent).toContain("\u2014");
  });

  it("has no hardcoded credit amount literal in its source", () => {
    const source = readFileSync(CARD_PATH, "utf8");
    expect(source).not.toContain("TIER_CREDITS");
    expect(source).not.toMatch(/amount:\s*"[\d,]+"/);
  });
});
