import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "../lib/api";
import {
  CREDITS_POLLING_END_EVENT,
  CREDITS_POLLING_START_EVENT,
} from "../lib/activeGeneration";
import {
  CREDITS_REFRESH_EVENT,
  CreditBalanceResponse,
} from "../lib/credits";

interface UseCreditBalanceOptions {
  enabled?: boolean;
  refreshIntervalMs?: number;
}

export function useCreditBalance(options: UseCreditBalanceOptions = {}) {
  const { enabled = true, refreshIntervalMs = 45000 } = options;
  const [balance, setBalance] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef<number | null>(null);
  const pendingRef = useRef(false);

  const refreshBalance = useCallback(async () => {
    if (!enabled || pendingRef.current) return;

    pendingRef.current = true;
    try {
      setLoading(true);
      const response = await apiClient.get<CreditBalanceResponse>("/credits/balance");
      setBalance(response.total_credits || 0);
    } catch {
      // Silently fail to avoid noisy toasts in global UI surfaces.
    } finally {
      setLoading(false);
      pendingRef.current = false;
    }
  }, [enabled]);

  const startInterval = useCallback(() => {
    if (intervalRef.current) return;
    intervalRef.current = window.setInterval(() => {
      refreshBalance();
    }, refreshIntervalMs);
  }, [refreshBalance, refreshIntervalMs]);

  const stopInterval = useCallback(() => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;

    refreshBalance();

    // Coalesce rapid refresh events: if a request is already in flight, the
    // burst of CREDITS_REFRESH_EVENT dispatches during a generation does not
    // create additional GET /credits/balance calls (KAN-436).
    const onRefresh = () => {
      refreshBalance();
    };

    const onFocus = () => {
      refreshBalance();
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
