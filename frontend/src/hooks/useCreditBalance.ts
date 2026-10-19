import { useCallback, useEffect, useRef, useSyncExternalStore } from "react";
import {
  CREDITS_POLLING_END_EVENT,
  CREDITS_POLLING_START_EVENT,
} from "../lib/activeGeneration";
import { CREDITS_REFRESH_EVENT } from "../lib/credits";
import { creditBalanceStore } from "../lib/creditBalanceStore";

interface UseCreditBalanceOptions {
  enabled?: boolean;
  refreshIntervalMs?: number;
}

/**
 * KAN-216: read the shared balance instead of fetching per hook instance.
 *
 * Previously each mount (Navbar, ProjectView, VideoProductionPanel,
 * ScriptGenerationPanel, ImagesPanel, AudioPanel) issued its own
 * GET /credits/balance, so one page render produced up to 6 identical calls.
 * The store owns the fetch and coalesces concurrent requests; this hook keeps
 * the same return shape ({ balance, loading, refreshBalance }) so callers are
 * unchanged.
 */
export function useCreditBalance(options: UseCreditBalanceOptions = {}) {
  const { enabled = true, refreshIntervalMs = 45000 } = options;
  const intervalRef = useRef<number | null>(null);

  const balance = useSyncExternalStore(
    creditBalanceStore.subscribe,
    creditBalanceStore.getBalance,
    creditBalanceStore.getBalance
  );
  const loading = useSyncExternalStore(
    creditBalanceStore.subscribe,
    creditBalanceStore.getLoading,
    creditBalanceStore.getLoading
  );

  const refreshBalance = useCallback(async () => {
    if (!enabled) return;
    // Store-level coalescing replaces the old per-hook pendingRef guard, which
    // only stopped duplicate calls from the same component instance.
    await creditBalanceStore.refresh();
  }, [enabled]);

  const stopInterval = useCallback(() => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startInterval = useCallback(() => {
    if (intervalRef.current) return;
    intervalRef.current = window.setInterval(() => {
      creditBalanceStore.refresh();
    }, refreshIntervalMs);
  }, [refreshIntervalMs]);

  useEffect(() => {
    if (!enabled) return;

    creditBalanceStore.refresh();

    // Coalesced by the store: the burst of CREDITS_REFRESH_EVENT dispatches
    // during a generation collapses into one in-flight request (KAN-436).
    const onRefresh = () => {
      creditBalanceStore.refresh();
    };

    const onFocus = () => {
      creditBalanceStore.refresh();
    };

    // Suspend the background interval while long-running generation jobs are
    // actively polling; rely on completion/focus/events instead (KAN-436).
    const onPollingStart = () => stopInterval();
    const onPollingEnd = () => startInterval();

    window.addEventListener(CREDITS_REFRESH_EVENT, onRefresh);
    window.addEventListener("focus", onFocus);
    window.addEventListener(CREDITS_POLLING_START_EVENT, onPollingStart);
    window.addEventListener(CREDITS_POLLING_END_EVENT, onPollingEnd);

    startInterval();

    return () => {
      window.removeEventListener(CREDITS_REFRESH_EVENT, onRefresh);
      window.removeEventListener("focus", onFocus);
      window.removeEventListener(CREDITS_POLLING_START_EVENT, onPollingStart);
      window.removeEventListener(CREDITS_POLLING_END_EVENT, onPollingEnd);
      stopInterval();
    };
  }, [enabled, refreshBalance, refreshIntervalMs, startInterval, stopInterval]);

  return {
    balance,
    loading,
    refreshBalance,
  };
}
