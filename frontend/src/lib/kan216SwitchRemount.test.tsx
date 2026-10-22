/**
 * @vitest-environment jsdom
 *
 * KAN-216 follow-up regression: a component mounted AFTER switchMode() must
 * see the new mode. Before the fix, switchMode() only PUT /users/me and set
 * local state, while useUserMode trusted AuthContext's user.preferred_mode and
 * no longer re-fetched — so a later mount read the stale mode until a reload.
 *
 * Reproduces PSQ's probe (qa-20261020-kan216-456tp-488-453):
 *   base:       later mount reads "creator" (or stale "explorer"), 0 GETs -> fail
 *   after fix:  later mount reads the switched mode                      -> pass
 *
 * The AuthContext double below models the real one after the fix: it holds a
 * user object and exposes updateUser(patch) which merges into it. A mount that
 * happens later reads the merged value without any network call.
 */
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

let serverMode = "creator";
const apiGet = vi.fn(async (url: string) =>
  String(url).includes("/users/me") ? { preferred_mode: serverMode } : {}
);
const apiPut = vi.fn(
  async (_url: string, body: { preferred_mode: string }) => {
    serverMode = body.preferred_mode;
    return {};
  }
);

vi.mock("../lib/api", () => ({
  apiClient: {
    get: (...a: unknown[]) => apiGet(...(a as [string])),
    put: (...a: unknown[]) =>
      apiPut(...(a as [string, { preferred_mode: string }])),
  },
}));

// Mutable auth state, shared across every hook instance in a test — this is
// what makes "a component mounted later" see the same auth value.
const authState: { user: Record<string, unknown> | null } = { user: null };

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: authState.user,
    updateUser: (patch: Record<string, unknown>) => {
      if (authState.user) authState.user = { ...authState.user, ...patch };
    },
  }),
}));

vi.mock("../lib/explorerMode", () => ({ isExplorerModeEnabled: () => true }));

const dualRoleUser = (mode: string) => ({
  id: "u1",
  roles: ["creator", "explorer"],
  preferred_mode: mode,
});

beforeEach(() => {
  serverMode = "creator";
  apiGet.mockClear();
  apiPut.mockClear();
  authState.user = dualRoleUser("creator");
});

describe("KAN-216 mode switch then a later mount", () => {
  it("later mount reports explorer after switchMode('explorer')", async () => {
    vi.resetModules();
    const { useUserMode } = await import("../hooks/useUserMode");

    const navbar = renderHook(() => useUserMode());
    await waitFor(() => expect(navbar.result.current.isLoading).toBe(false));
    expect(navbar.result.current.mode).toBe("creator");

    await act(async () => {
      await navbar.result.current.switchMode("explorer");
    });
    expect(navbar.result.current.mode).toBe("explorer");
    expect(serverMode).toBe("explorer");

    // Component that navigates in after the switch (e.g. Profile).
    const late = renderHook(() => useUserMode());
    await waitFor(() => expect(late.result.current.isLoading).toBe(false));
    expect(late.result.current.mode).toBe("explorer");

    // No re-fetch was needed: the auth value carried it.
    expect(apiGet.mock.calls.filter((c) => String(c[0]).includes("/users/me")).length).toBe(0);

    navbar.unmount();
    late.unmount();
  });

  it("later mount reports creator after switching back", async () => {
    vi.resetModules();
    const { useUserMode } = await import("../hooks/useUserMode");

    const first = renderHook(() => useUserMode());
    await waitFor(() => expect(first.result.current.isLoading).toBe(false));
    await act(async () => {
      await first.result.current.switchMode("explorer");
    });
    await act(async () => {
      await first.result.current.switchMode("creator");
    });

    const late = renderHook(() => useUserMode());
    await waitFor(() => expect(late.result.current.isLoading).toBe(false));
    expect(late.result.current.mode).toBe("creator");

    first.unmount();
    late.unmount();
  });

  it("KAN-216 dedupe intact: several mounts share one GET, not one each", async () => {
    vi.resetModules();
    // preferred_mode absent -> the hook must fetch, and share the request.
    authState.user = { id: "u2", roles: ["creator", "explorer"] };
    const { useUserMode } = await import("../hooks/useUserMode");

    const a = renderHook(() => useUserMode());
    const b = renderHook(() => useUserMode());
    const c = renderHook(() => useUserMode());
    await waitFor(() => expect(a.result.current.isLoading).toBe(false));
    await waitFor(() => expect(b.result.current.isLoading).toBe(false));
    await waitFor(() => expect(c.result.current.isLoading).toBe(false));

    const userMeCalls = apiGet.mock.calls.filter((call) =>
      String(call[0]).includes("/users/me")
    ).length;
    // Coalesced: one in-flight request shared across three mounts.
    expect(userMeCalls).toBe(1);

    a.unmount();
    b.unmount();
    c.unmount();
  });
});
