// @vitest-environment jsdom
/**
 * KAN-489 / KAN-490 / KAN-491 — a brand-new account must not be shown
 * fabricated achievements on /profile.
 *
 * Regression lock for the placeholder data that shipped in Profile.tsx:
 * a new account rendered a 15-day streak (KAN-489), 8 earned badges
 * (KAN-490) and an activity timeline dated January 2024 (KAN-491), plus
 * hardcoded Progress Goals fractions. None of it came from an API call.
 *
 * These assertions are written against the *rendered output* rather than
 * component internals, so they fail on the placeholder literals and pass
 * once the page shows real zeros / empty states.
 */
import { cleanup, render, screen } from "@testing-library/react";
import * as matchers from "@testing-library/jest-dom/matchers";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

expect.extend(matchers);

// A brand-new account: authenticated, but with no roles and no progress.
vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: "00000000-0000-0000-0000-000000000001",
      display_name: "New Reader",
      email: "new.reader@example.com",
      roles: [],
    },
  }),
  hasRole: () => false,
}));

// Heavy siblings that fetch or manage state; irrelevant to these assertions.
vi.mock("../components/Profile/RoleManagement", () => ({ default: () => null }));
vi.mock("../components/Credits/CreditHistory", () => ({ default: () => null }));
vi.mock("../hooks/useUserMode", () => ({
  useUserMode: () => ({ mode: "explorer", switchMode: vi.fn() }),
}));

import Profile from "./Profile";

describe("Profile — new account shows no fabricated achievements", () => {
  beforeEach(() => {
    render(<Profile />);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("KAN-489: renders no streak chip and no 15-day streak for a new account", () => {
    // The old page hardcoded streakDays: 15 and always rendered a chip
    // reading "15 day streak"; the chip is now conditional on > 0.
    // Note: the "Day Streak" *stat card label* is legitimate UI and must
    // still render - only the numeric chip is conditional. Assert on the
    // quantified text, not the label.
    expect(screen.queryByText(/\d+\s*day streak/i)).toBeNull();
    expect(screen.getByText(/day streak/i)).toBeInTheDocument();
    expect(screen.queryByText("15")).toBeNull();
  });

  it("KAN-490: shows an empty badge state instead of 8 earned badges", () => {
    expect(screen.getByText(/no badges earned yet/i)).toBeInTheDocument();
    // The fabricated badge identities must be gone entirely.
    expect(screen.queryByText("First Steps")).toBeNull();
    expect(screen.queryByText("Bookworm")).toBeNull();
    expect(screen.queryByText("Story Master")).toBeNull();
    expect(screen.queryByText(/achievement badges/i)).toBeInTheDocument();
  });

  it("KAN-491: shows an empty activity state with no 2024-dated entries", () => {
    expect(screen.getByText(/no activity yet/i)).toBeInTheDocument();
    // Every earnedDate placeholder was a 2024 date; none may render.
    expect(screen.queryByText(/2024/)).toBeNull();
    expect(screen.queryByText(/introduction to machine learning/i)).toBeNull();
    expect(screen.queryByText(/the crystal chronicles/i)).toBeNull();
    expect(screen.queryByText(/earned on/i)).toBeNull();
  });

  it("renders zeroed counters rather than someone else's progress", () => {
    // booksRead 12, booksUploaded 3, hoursSpent 45, badgesEarned 8 and
    // streakDays 15 were all hardcoded; each must now read 0.
    expect(screen.getAllByText("0").length).toBeGreaterThanOrEqual(4);
    expect(screen.getByText(/books read/i)).toBeInTheDocument();
    expect(screen.getByText(/books uploaded/i)).toBeInTheDocument();
    expect(screen.getByText(/hours spent/i)).toBeInTheDocument();
  });

  it("renders zeroed progress goals instead of hardcoded fractions", () => {
    expect(screen.getByText("0/5 books")).toBeInTheDocument();
    expect(screen.getByText("0/12 earned")).toBeInTheDocument();
    expect(screen.getByText("0/30 days")).toBeInTheDocument();
    // The original hardcoded fractions must not survive.
    expect(screen.queryByText("3/5 books")).toBeNull();
    expect(screen.queryByText("8/12 earned")).toBeNull();
    expect(screen.queryByText("15/30 days")).toBeNull();
  });
});
