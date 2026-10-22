/**
 * @vitest-environment jsdom
 *
 * KAN-216: duplicate user/credits API calls on a page render.
 *
 * The app mounts several independent consumers of the same data:
 *   useCreditBalance -> Navbar, ProjectView, VideoProductionPanel,
 *                       ScriptGenerationPanel, ImagesPanel, AudioPanel (6)
 *   useUserMode      -> Navbar, Profile, BookViewForEntertainment (3)
 *
 * Before the fix each instance fetched on mount, so one render produced 6x
 * GET /credits/balance and 3x GET /users/me. This test counts the actual
 * requests for the real number of concurrent consumers.
 */
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.fn();

vi.mock("../lib/api", () => ({
  apiClient: {
    get: (...args: unknown[]) => apiGet(...args),
    put: vi.fn(async () => ({})),
  },
}));

const authState: { user: Record<string, unknown> | null } = { user: null };

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({ user: authState.user }),
}));

vi.mock("../lib/explorerMode", () => ({
  isExplorerModeEnabled: () => true,
  CREATOR_HOME_PATH: "/creator",
  EXPLORER_HOME_PATH: "/dashboard",
  getPostAuthRedirect: () => "/creator",
  getExplorerHomePath: () => "/creator",
}));

function countCalls(endpoint: string) {
  return apiGet.mock.calls.filter(([url]) => String(url).includes(endpoint)).length;
}

/** Mount the hook N times, the way the app really mounts it. */
async function mountMany<T>(useHook: () => T, times: number) {
  const hooks = [];
  for (let i = 0; i < times; i += 1) {
    const rendered = renderHook(() => useHook());
    hooks.push(rendered);
  }
  await waitFor(() => {
    expect(apiGet).toHaveBeenCalled();
  });
  return hooks;
}

beforeEach(() => {
  apiGet.mockReset();
  apiGet.mockImplementation(async (endpoint: string) => {
    if (String(endpoint).includes("/credits/balance")) {
      return { total_credits: 120 };
    }
    if (String(endpoint).includes("/users/me")) {
      return { preferred_mode: "explorer" };
    }
    return {};
  });
  authState.user = {
    id: "u-1",
    email: "a@b.c",
    display_name: "Test",
    roles: ["creator", "explorer"],
    preferred_mode: "explorer",
    onboarding_completed: true,
  };
});

afterEach(() => {
  vi.clearAllTimers();
});

describe("KAN-216 duplicate API calls on render", () => {
  it("6 concurrent useCreditBalance consumers issue one GET /credits/balance", async () => {
    vi.resetModules();
    const { useCreditBalance } = await import("../hooks/useCreditBalance");

    const hooks = await mountMany(() => useCreditBalance({ enabled: true }), 6);

    // Before the fix this was 6 (one per mounted consumer).
    expect(countCalls("/credits/balance")).toBe(1);

    // Same value reaches every consumer, so behaviour did not change.
    hooks.forEach(({ result }) => {
      expect(result.current.balance).toBe(120);
    });

    hooks.forEach(({ unmount }) => unmount());
  });

  it("3 concurrent useUserMode consumers issue no extra GET /users/me when auth already has preferred_mode", async () => {
    vi.resetModules();
    const { useUserMode } = await import("../hooks/useUserMode");

    const hooks: Array<{ result: { current: { mode: string } }; unmount: () => void }> = [];
    for (let i = 0; i < 3; i += 1) {
      hooks.push(renderHook(() => useUserMode()) as never);
    }
    await waitFor(() => {
      expect(hooks[0].result.current.mode).toBe("explorer");
    });

    // Before the fix this was 3 duplicate /users/me calls (AuthContext already
    // loaded the same payload at startup).
    expect(countCalls("/users/me")).toBe(0);
    hooks.forEach(({ result }) => expect(result.current.mode).toBe("explorer"));
    hooks.forEach(({ unmount }) => unmount());
  });

  it("a burst of CREDITS_REFRESH_EVENT collapses into a single in-flight request", async () => {
    vi.resetModules();
    const { useCreditBalance } = await import("../hooks/useCreditBalance");
    const { CREDITS_REFRESH_EVENT } = await import("./credits");

    const { unmount } = renderHook(() => useCreditBalance({ enabled: true }));
    await waitFor(() => expect(countCalls("/credits/balance")).toBe(1));

    await act(async () => {
      for (let i = 0; i < 8; i += 1) {
        window.dispatchEvent(new Event(CREDITS_REFRESH_EVENT));
      }
    });

    // The mount call plus exactly one coalesced refresh, not nine.
    expect(countCalls("/credits/balance")).toBe(2);
    unmount();
  });
});
