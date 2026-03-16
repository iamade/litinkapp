import { useCallback, useEffect, useState } from "react";
import { apiClient } from "../lib/api";
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

  const refreshBalance = useCallback(async () => {
    if (!enabled) return;

    try {
      setLoading(true);
      const response = await apiClient.get<CreditBalanceResponse>("/credits/balance");
      setBalance(response.total_credits || 0);
    } catch {
      // Silently fail to avoid noisy toasts in global UI surfaces.
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;

    refreshBalance();

    const onRefresh = () => {
      refreshBalance();
    };

    const onFocus = () => {
      refreshBalance();
    };

    window.addEventListener(CREDITS_REFRESH_EVENT, onRefresh);
    window.addEventListener("focus", onFocus);

    const intervalId = window.setInterval(() => {
      refreshBalance();
    }, refreshIntervalMs);

    return () => {
      window.removeEventListener(CREDITS_REFRESH_EVENT, onRefresh);
      window.removeEventListener("focus", onFocus);
      window.clearInterval(intervalId);
    };
  }, [enabled, refreshBalance, refreshIntervalMs]);

  return {
    balance,
    loading,
    refreshBalance,
  };
}
