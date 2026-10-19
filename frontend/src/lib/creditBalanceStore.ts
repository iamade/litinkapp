/**
 * KAN-216: shared credit-balance store.
 *
 * Before this, every `useCreditBalance` instance (Navbar, ProjectView,
 * VideoProductionPanel, ScriptGenerationPanel, ImagesPanel, AudioPanel) fired
 * its own GET /credits/balance on mount, so a single page render produced up
 * to 6 identical requests. This module owns the balance and the in-flight
 * request, so concurrent readers share one fetch and one cached value.
 *
 * Returned data is unchanged: still `total_credits` (0 when absent).
 */
import { apiClient } from "./api";
import { CreditBalanceResponse } from "./credits";

type Listener = () => void;

// NOTE: getSnapshot getters must return primitives so useSyncExternalStore
// does not re-render forever on a fresh object identity.
let currentBalance = 0;
let currentLoading = false;
let inflight: Promise<void> | null = null;

const listeners = new Set<Listener>();

function notify() {
  listeners.forEach((listener) => listener());
}

async function fetchBalance(): Promise<void> {
  currentLoading = true;
  notify();
  try {
    const response = await apiClient.get<CreditBalanceResponse>("/credits/balance");
    currentBalance = response.total_credits || 0;
  } catch {
    // Silently fail to avoid noisy toasts in global UI surfaces.
  } finally {
    currentLoading = false;
    notify();
  }
}

export const creditBalanceStore = {
  getBalance: () => currentBalance,
  getLoading: () => currentLoading,

  subscribe(listener: Listener) {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },

  /**
   * Coalesce: any refresh requested while a fetch is in flight joins that
   * fetch instead of starting a second one. This is what collapses the
   * mount burst (and the CREDITS_REFRESH_EVENT fan-out) to a single call.
   */
  refresh(): Promise<void> {
    if (inflight) return inflight;
    inflight = fetchBalance().finally(() => {
      inflight = null;
    });
    return inflight;
  },

  /** Test-only: drop cached state so call counts start from zero. */
  __resetForTests() {
    currentBalance = 0;
    currentLoading = false;
    inflight = null;
    listeners.clear();
  },
};
